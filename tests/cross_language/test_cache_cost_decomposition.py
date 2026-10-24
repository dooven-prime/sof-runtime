from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from applications.malecns_profile_census.cache_cost_decomposition import (
    ROOT, Worker, build_probe, check_session_environment, envelope, probe_binary, session_batch,
)
from applications.malecns_profile_census.prepared_cache import cache_key, call_cache, make_request
from applications.malecns_profile_census.protocol import canonical_bytes


class CacheCostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_probe()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = self.root / "fixture.json"
        shutil.copyfile(ROOT / "examples/malecns_profile_census/tiny-fixture.json", self.fixture)
        self.request = make_request(self.root / "cache", fixture=self.fixture, execute=True)
        self.entry = self.root / "cache/entries" / cache_key(self.request["identity"])

    def run_worker(self, worker, status, request=None):
        wrapper, _ = worker.call("execute", request or self.request)
        self.assertEqual(wrapper["result"]["status"], status, wrapper)
        return wrapper["result"]

    def test_reference_parity_and_every_call_validates(self):
        before = canonical_bytes(self.request)
        with Worker() as worker:
            first = self.run_worker(worker, "CACHE_MISS_PREPARED")
            second = self.run_worker(worker, "CACHE_HIT_VALIDATED")
            direct, _, code = call_cache(self.request)
            self.assertEqual(code, 0)
            for value in (second, direct):
                self.assertEqual(first["packet"], value["packet"])
                self.assertEqual(first["consumer"]["stdout"], value["consumer"]["stdout"])
                self.assertIn("initial_source_preparer_verification_seconds", value["timings"])
                self.assertIn("final_integrity_source_verification_seconds", value["timings"])
            probed, _ = worker.call("probe", self.request)
            self.assertEqual(probed["result"]["status"], "PROBED_NOT_CONSUMED")
            self.assertEqual(probed["result"]["packet"], first["packet"])
            self.assertNotIn("consumer", probed["result"])
        self.assertEqual(before, canonical_bytes(self.request))

    def test_same_length_same_mtime_source_change_rejected_then_recovery(self):
        with Worker() as worker:
            self.run_worker(worker, "CACHE_MISS_PREPARED")
            original = self.fixture.read_bytes()
            metadata = self.fixture.stat()
            changed = original.replace(b"tiny", b"TINY", 1)
            if changed == original:
                changed = bytes([original[0] ^ 1]) + original[1:]
            self.fixture.write_bytes(changed)
            os.utime(self.fixture, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            self.run_worker(worker, "SOURCE_IDENTITY_REJECTED")
            self.fixture.write_bytes(original)
            self.run_worker(worker, "CACHE_HIT_VALIDATED")

    def test_same_length_same_mtime_packet_change_rejected_then_recovery(self):
        with Worker() as worker:
            self.run_worker(worker, "CACHE_MISS_PREPARED")
            path = self.entry / "packet.bin"
            original, metadata = path.read_bytes(), path.stat()
            path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            self.run_worker(worker, "CACHE_INVALID_REJECTED")
            path.write_bytes(original)
            self.run_worker(worker, "CACHE_HIT_VALIDATED")

    def test_preparer_and_consumer_still_checked_on_worker_hit(self):
        with Worker() as worker:
            self.run_worker(worker, "CACHE_MISS_PREPARED")
            bad = copy.deepcopy(self.request)
            bad["identity"]["preparer"]["executable_sha256"] = "0" * 64
            self.run_worker(worker, "PREPARER_IDENTITY_REJECTED", bad)
            bad = copy.deepcopy(self.request)
            bad["consumer"]["sha256"] = "0" * 64
            self.run_worker(worker, "CACHE_EXECUTION_FAILED", bad)
            self.run_worker(worker, "CACHE_HIT_VALIDATED")

    def test_restart_has_no_in_memory_validation_credential(self):
        with Worker() as worker:
            self.run_worker(worker, "CACHE_MISS_PREPARED")
        manifest = self.entry / "manifest.json"
        manifest.unlink()
        with Worker() as worker:
            self.run_worker(worker, "CACHE_INVALID_REJECTED")

    def test_environment_change_requires_readmission(self):
        check_session_environment(self.request)
        bad = copy.deepcopy(self.request)
        bad["identity"]["preparer"]["runtime"]["python"] = "different"
        with self.assertRaisesRegex(ValueError, "Python version"):
            check_session_environment(bad)
        bad = copy.deepcopy(self.request)
        bad["identity"]["preparer"]["runtime"]["dependencies"] = {"numpy": "different"}
        with patch("importlib.metadata.version", return_value="actual"):
            with self.assertRaisesRegex(ValueError, "dependency"):
                check_session_environment(bad)

    def test_bounded_worker_session_and_clean_eof(self):
        with Worker() as worker:
            for ident in range(64):
                value, _ = worker.call("ping")
                self.assertEqual(value["id"], ident)
                self.assertEqual(value["result"]["status"], "PONG")
            with self.assertRaisesRegex(ValueError, "session exhausted"):
                worker.call("ping")
        self.assertEqual(worker.process.returncode, 0)

    def test_bad_frame_schema_id_and_size_end_session(self):
        cases = [b"not json\n", canonical_bytes(envelope("ping", None, 1)) + b"\n",
                 canonical_bytes({**envelope("ping", None), "schema": "wrong"}) + b"\n",
                 b"x" * 1_000_001 + b"\n", canonical_bytes(envelope("ping", None))]
        for raw in cases:
            with self.subTest(length=len(raw)):
                child = subprocess.run([str(probe_binary())], cwd=ROOT, input=raw,
                                       capture_output=True, timeout=15)
                self.assertEqual(child.returncode, 2)
                self.assertFalse(child.stderr)
                messages = [json.loads(line) for line in child.stdout.splitlines()]
                self.assertEqual(messages[0]["status"], "READY")
                self.assertEqual(messages[-1]["status"], "PROTOCOL_REJECTED")

    def test_once_probe_and_unknown_action_rejection(self):
        path = self.root / "envelope.json"
        for action, code in (("ping", 0), ("unexpected", 2)):
            path.write_bytes(canonical_bytes(envelope(action, None)))
            child = subprocess.run([str(probe_binary()), "--once", str(path)], cwd=ROOT,
                                   capture_output=True, timeout=15)
            self.assertEqual(child.returncode, code)
            result = json.loads(child.stdout)
            self.assertEqual(result.get("result", result)["status"], "PONG" if not code else "PROTOCOL_REJECTED")

    def test_parent_timeout_reaps_worker(self):
        worker = Worker()
        worker.timeout = 0.01
        with self.assertRaises(TimeoutError):
            worker._receive()
        worker.close(abort=True)
        self.assertIsNotNone(worker.process.poll())

    def test_end_to_end_batch_reuses_one_request_but_revalidates_five_times(self):
        first, _, code = call_cache(self.request)
        self.assertEqual(code, 0)
        for mode in ("fixed_request_fresh_rust", "fixed_request_worker"):
            with patch("applications.malecns_profile_census.prepared_cache.make_request",
                       return_value=self.request) as factory:
                value = session_batch(self.root / "cache", self.fixture, self.fixture, mode)
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(len(value["calls"]), 5)
            for call in value["calls"]:
                self.assertEqual(call["result"]["status"], "CACHE_HIT_VALIDATED")
                self.assertEqual(call["result"]["consumer"]["stdout"], first["consumer"]["stdout"])
                self.assertIn("final_integrity_source_verification_seconds", call["result"]["timings"])
            self.assertGreater(value["whole_session_wall_seconds"], value["identity_construction_seconds"])


if __name__ == "__main__":
    unittest.main()
