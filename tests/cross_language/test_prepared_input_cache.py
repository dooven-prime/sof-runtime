from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

import psutil

from applications.malecns_profile_census.prepared_cache import (
    ROOT, build_cache, cache_binary, cache_key, call_cache, make_request,
)
from applications.malecns_profile_census.protocol import canonical_bytes, sha256_file


class PreparedInputCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_cache()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = self.root / "fixture.json"
        shutil.copyfile(ROOT / "examples/malecns_profile_census/tiny-fixture.json", self.fixture)
        self.request = make_request(self.root / "cache", fixture=self.fixture)

    def result(self, request=None, status=None):
        value, _, code = call_cache(request or self.request)
        if status:
            self.assertEqual(value["status"], status, value)
            self.assertEqual(code, 0 if status in (
                "CACHE_MISS_PREPARED", "CACHE_HIT_VALIDATED", "CACHE_INVALID_REBUILT"
            ) else 2)
        return value

    def entry(self):
        return self.root / "cache/entries" / cache_key(self.request["identity"])

    def fault_builder(self, *, mode="normal", marker=None, delay=0):
        request = copy.deepcopy(self.request)
        command = ["-B", "-m", "tests.cache_fixture_preparer", "--fixture", "{source:CASE_FIXTURE}",
                   "--output", "{output}", "--mode", mode, "--delay", str(delay)]
        if marker is not None:
            command += ["--marker", str(marker)]
        request["identity"]["preparer"]["command"] = command
        name = "tests/cache_fixture_preparer.py"
        request["identity"]["preparer"]["sources_sha256"][name] = sha256_file(ROOT / name)
        request["preparer_paths"][name] = str(ROOT / name)
        return request

    def start(self, request, name="request.json"):
        path = self.root / name
        path.write_bytes(canonical_bytes(request))
        return subprocess.Popen([str(cache_binary()), str(path)], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def wait_marker(self, marker):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if marker.is_file():
                return json.loads(marker.read_text())["pid"]
            time.sleep(.01)
        self.fail("preparer did not reach its actual fault point")

    def test_miss_then_fully_validated_hit(self):
        first = self.result(status="CACHE_MISS_PREPARED")
        second = self.result(status="CACHE_HIT_VALIDATED")
        self.assertEqual(first["packet"], second["packet"])
        self.assertIn("preparation_seconds", first["timings"])
        self.assertNotIn("preparation_seconds", second["timings"])
        self.assertEqual(first["key"], cache_key(self.request["identity"]))

    def test_each_declared_identity_component_changes_the_key(self):
        original = self.request["identity"]
        variants = []
        for component in ("sector_policy", "sign_policy", "preparer"):
            changed = copy.deepcopy(original)
            changed[component]["version"] = "next"
            variants.append(changed)
        changed = copy.deepcopy(original)
        changed["packet_format"]["version"] = 2
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["sources"][0]["sha256"] = "0" * 64
        variants.append(changed)
        for changed in variants:
            self.assertNotEqual(cache_key(original), cache_key(changed))
        self.result(status="CACHE_MISS_PREPARED")
        changed_request = copy.deepcopy(self.request)
        changed_request["identity"]["preparer"]["version"] = "next"
        self.result(changed_request, "CACHE_MISS_PREPARED")

    def test_source_drift_is_rejected_and_fresh_identity_does_not_alias(self):
        first = self.result(status="CACHE_MISS_PREPARED")
        self.fixture.write_bytes(self.fixture.read_bytes() + b"\n")
        self.result(status="SOURCE_IDENTITY_REJECTED")
        fresh = make_request(self.root / "cache", fixture=self.fixture)
        second = self.result(fresh, "CACHE_MISS_PREPARED")
        self.assertNotEqual(first["key"], second["key"])

    def test_preparer_hash_and_required_version_are_checked(self):
        bad = copy.deepcopy(self.request)
        bad["identity"]["preparer"]["executable_sha256"] = "0" * 64
        self.result(bad, "PREPARER_IDENTITY_REJECTED")
        bad = copy.deepcopy(self.request)
        del bad["identity"]["preparer"]["version"]
        self.result(bad, "INVALID_REQUEST")
        bad = copy.deepcopy(self.request)
        bad["identity"]["packet_format"]["version"] = 2
        self.result(bad, "INVALID_REQUEST")

    def test_packet_damage_rejected_without_silent_rebuild(self):
        self.result(status="CACHE_MISS_PREPARED")
        packet = self.entry() / "packet.bin"
        original = packet.read_bytes()
        for damage in (original[:-1], original + b"x", b"BADMAGIC" + original[8:]):
            with self.subTest(size=len(damage)):
                packet.write_bytes(damage)
                self.result(status="CACHE_INVALID_REJECTED")
                self.assertEqual(packet.read_bytes(), damage)
        request = copy.deepcopy(self.request)
        request["invalid_policy"] = "rebuild"
        rebuilt = self.result(request, "CACHE_INVALID_REBUILT")
        self.assertEqual(packet.read_bytes(), original)
        self.assertTrue(rebuilt["invalid_reason"])
        self.assertTrue((self.root / "cache/quarantine" / rebuilt["quarantine"]).is_dir())

    def test_manifest_length_digest_header_and_partial_entry_rejected(self):
        self.result(status="CACHE_MISS_PREPARED")
        manifest_path = self.entry() / "manifest.json"
        original = json.loads(manifest_path.read_text())
        for field, value in (("size", 1), ("sha256", "0" * 64), ("record_count", 1)):
            changed = copy.deepcopy(original)
            changed["packet"][field] = value
            manifest_path.write_bytes(canonical_bytes(changed))
            self.result(status="CACHE_INVALID_REJECTED")
        changed = copy.deepcopy(original)
        changed["identity"]["expected_header"]["source_field"] = "other"
        manifest_path.write_bytes(canonical_bytes(changed))
        self.result(status="CACHE_INVALID_REJECTED")
        manifest_path.unlink()
        self.result(status="CACHE_INVALID_REJECTED")

    def test_failed_or_source_mutating_build_never_publishes(self):
        for mode, status in (("fail", "CACHE_BUILD_FAILED"), ("source-drift", "SOURCE_IDENTITY_REJECTED")):
            request = self.fault_builder(mode=mode)
            self.result(request, status)
            self.assertFalse((self.root / "cache/entries" / cache_key(request["identity"])).exists())

    def test_concurrent_same_key_builds_have_one_publisher(self):
        request = self.fault_builder(delay=.2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: call_cache(request), range(2)))
        self.assertEqual(sorted(value["status"] for value, _, code in results if code == 0),
                         ["CACHE_HIT_VALIDATED", "CACHE_MISS_PREPARED"])
        self.assertEqual(len(list((self.root / "cache/entries").iterdir())), 1)

    def test_process_interruption_leaves_no_committed_partial_packet(self):
        marker = self.root / "paused.json"
        request = self.fault_builder(mode="pause-once", marker=marker)
        child = self.start(request)
        preparer_pid = None
        try:
            preparer_pid = self.wait_marker(marker)
            child.kill()
            child.wait(timeout=5)
        finally:
            if child.poll() is None:
                child.kill(); child.wait(timeout=5)
            if preparer_pid is not None:
                try:
                    preparer = psutil.Process(preparer_pid)
                    preparer.kill()
                    preparer.wait(timeout=5)
                except psutil.NoSuchProcess:
                    pass
            child.communicate(timeout=5)
        self.assertFalse((self.root / "cache/entries" / cache_key(request["identity"])).exists())
        self.assertTrue(list((self.root / "cache/staging").iterdir()))
        self.result(request, "CACHE_MISS_PREPARED")
        self.result(request, "CACHE_HIT_VALIDATED")

    def test_lock_timeout_has_a_distinct_result(self):
        marker = self.root / "building.json"
        request = self.fault_builder(marker=marker, delay=2)
        first = self.start(request)
        try:
            self.wait_marker(marker)
            second = copy.deepcopy(request)
            second["lock_timeout_seconds"] = 1
            self.result(second, "CACHE_LOCK_TIMEOUT")
            stdout, stderr = first.communicate(timeout=10)
            self.assertEqual(first.returncode, 0, stderr)
            self.assertEqual(json.loads(stdout)["status"], "CACHE_MISS_PREPARED")
        finally:
            if first.poll() is None:
                first.kill(); first.communicate(timeout=5)

    def test_consumer_binary_identity_is_not_cache_identity(self):
        request = copy.deepcopy(self.request)
        request["consumer"] = {"program": request["builder_program"], "sha256": "0" * 64,
                               "args": ["{packet}"], "timeout_seconds": 5}
        self.result(request, "CACHE_EXECUTION_FAILED")
        self.result(status="CACHE_HIT_VALIDATED")

    def test_malformed_protocol_header_cannot_become_a_cache_contract(self):
        for change in ("duplicate", "extra"):
            request = copy.deepcopy(self.request)
            if change == "duplicate":
                request["identity"]["expected_header"]["sector_labels"] = ["L", "L"]
            else:
                request["identity"]["expected_header"]["unexpected"] = True
            self.result(request, "INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()
