from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

from applications.malecns_profile_census.fused_validation_benchmark import (
    ROOT, build_fusion, run_attempt,
)
from applications.malecns_profile_census.prepared_cache import make_request, call_cache, cache_key
from applications.malecns_profile_census.protocol import canonical_bytes


class FusedPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_fusion()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = self.root / "fixture.json"
        shutil.copyfile(ROOT / "examples/malecns_profile_census/tiny-fixture.json", self.fixture)
        self.request = make_request(self.root / "cache", fixture=self.fixture, execute=True)
        self.prepared, _, code = call_cache(self.request)
        self.assertEqual(code, 0)
        self.entry = self.root / "cache/entries" / cache_key(self.request["identity"])
        self.packet = self.entry / "packet.bin"
        self.manifest = self.entry / "manifest.json"
        self.original_packet = self.packet.read_bytes()
        self.original_manifest = self.manifest.read_bytes()

    def attempt(self, mode, status, request=None, action="execute"):
        request_path = self.root / f"request-{mode}.json"
        request_path.write_bytes(canonical_bytes(request or self.request))
        value, _, code = run_attempt(mode, action, request_path, timeout=15)
        self.assertEqual(value["result"]["status"], status, value)
        self.assertEqual(code, 0 if status in ("CACHE_HIT_VALIDATED", "CACHE_MISS_PREPARED",
            "CACHE_INVALID_REBUILT", "ENTRY_VALIDATED_NOT_CONSUMED") else 2)
        return value

    def restore(self):
        self.packet.write_bytes(self.original_packet)
        self.manifest.write_bytes(self.original_manifest)

    def damage(self, raw, *, update_manifest=False):
        self.packet.write_bytes(raw)
        if update_manifest:
            manifest = json.loads(self.original_manifest)
            manifest["packet"]["sha256"] = hashlib.sha256(raw).hexdigest()
            manifest["packet"]["size"] = len(raw)
            self.manifest.write_bytes(canonical_bytes(manifest))

    def test_full_output_and_observed_validation_reads(self):
        for mode, passes in (("reference", 2), ("fused", 1)):
            for action, calls in (("validate", 1), ("execute", 2)):
                expected = "ENTRY_VALIDATED_NOT_CONSUMED" if action == "validate" else "CACHE_HIT_VALIDATED"
                value = self.attempt(mode, expected, action=action)
                self.assertEqual(value["result"]["packet"], self.prepared["packet"])
                if action == "execute":
                    self.assertEqual(value["result"]["consumer"]["stdout"], self.prepared["consumer"]["stdout"])
                    io = value["read_io"][str(self.fixture)]
                    self.assertEqual(io["opens"], 2)
                    self.assertEqual(io["bytes"], 2 * self.fixture.stat().st_size)
                packet_io = [item for path, item in value["read_io"].items() if Path(path).name == "packet.bin"]
                self.assertEqual(len(packet_io), 1)
                io = packet_io[0]
                self.assertEqual(io["opens"], calls * passes)
                self.assertEqual(io["bytes"], calls * passes * len(self.original_packet))
                self.assertEqual(len(value["validation_calls"]), calls)
                self.assertTrue(all(item["accepted"] for item in value["validation_calls"]))
                if os.name == "nt":
                    self.assertIsNotNone(value["operation_cpu_seconds_excludes_children"])

    def test_truncation_damage_tail_and_wrong_header_rejected(self):
        raw = self.original_packet
        length = struct.unpack_from("<I", raw, 8)[0]
        wrong = raw[:12] + raw[12:12+length].replace(b"source_field", b"source_FiEld", 1) + raw[12+length:]
        noncanonical = raw[:8] + struct.pack("<I", length+1) + b" " + raw[12:]
        cases = [b"", raw[:9], raw[:12+length-1], raw[:-1], raw+b"x", b"BADMAGIC"+raw[8:], wrong, noncanonical]
        for changed in cases:
            for mode in ("reference", "fused"):
                with self.subTest(mode=mode, size=len(changed)):
                    self.restore()
                    self.damage(changed, update_manifest=True)
                    self.attempt(mode, "CACHE_INVALID_REJECTED")
                    self.assertEqual(self.packet.read_bytes(), changed)

    def test_structure_checks_not_replaced_by_manifest_digest(self):
        raw = self.original_packet
        offset = 12 + struct.unpack_from("<I", raw, 8)[0]
        edge_count = struct.unpack_from("<I", raw, offset+11)[0]
        self.assertGreaterEqual(edge_count, 2)
        sector_count = len(self.request["identity"]["expected_header"]["sector_labels"])
        changes = [("<Q", offset, 2**63), ("<H", offset+8, sector_count),
                   ("<b", offset+10, 0), ("<I", offset+11, 0),
                   ("<H", offset+15, sector_count), ("<Q", offset+17, 0),
                   ("<Q", offset+17, 2**63)]
        second = offset + 15 + edge_count * 10
        if second < len(raw):
            changes.append(("<Q", second, struct.unpack_from("<Q", raw, offset)[0]))
        cases = []
        for kind, position, value in changes:
            changed = bytearray(raw)
            struct.pack_into(kind, changed, position, value)
            cases.append(changed)
        changed = bytearray(raw)
        struct.pack_into("<Q", changed, offset+17, 2**63-1)
        struct.pack_into("<Q", changed, offset+27, 1)
        cases.append(changed)
        for index, changed in enumerate(cases):
            for mode in ("reference", "fused"):
                with self.subTest(index=index, mode=mode):
                    self.restore()
                    self.damage(changed, update_manifest=True)
                    self.attempt(mode, "CACHE_INVALID_REJECTED")

    def test_valid_structure_changed_digest_is_rejected(self):
        changed = bytearray(self.original_packet)
        weight = struct.unpack_from("<Q", changed, len(changed)-8)[0]
        struct.pack_into("<Q", changed, len(changed)-8, weight+1)
        for mode in ("reference", "fused"):
            self.restore()
            self.damage(changed)
            self.attempt(mode, "CACHE_INVALID_REJECTED")
            self.damage(changed, update_manifest=True)
            self.attempt(mode, "ENTRY_VALIDATED_NOT_CONSUMED", action="validate")

    def test_source_identity_is_checked_before_consumer(self):
        original = self.fixture.read_bytes()
        metadata = self.fixture.stat()
        self.fixture.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        os.utime(self.fixture, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
        for mode in ("reference", "fused"):
            value = self.attempt(mode, "SOURCE_IDENTITY_REJECTED")
            self.assertFalse(value["validation_calls"])

    def test_post_consumption_source_and_packet_mutation_are_rejected(self):
        original_source = self.fixture.read_bytes()
        for fault, status in (("source", "SOURCE_IDENTITY_REJECTED"),
                              ("packet", "CACHE_INVALID_REJECTED"), ("packet-valid", "CACHE_INVALID_REJECTED")):
            for mode in ("reference", "fused"):
                with self.subTest(fault=fault, mode=mode):
                    self.restore()
                    self.fixture.write_bytes(original_source)
                    request = copy.deepcopy(self.request)
                    request["consumer"] = {"program": request["builder_program"],
                        "sha256": request["identity"]["preparer"]["executable_sha256"],
                        "args": ["-B", "-m", "tests.cache_fusion_consumer", "--mode", fault,
                                 "--packet", "{packet}", "--source", str(self.fixture)], "timeout_seconds": 10}
                    value = self.attempt(mode, status, request)
                    self.assertEqual(len(value["validation_calls"]), 2)
                    if fault == "source":
                        self.assertEqual(value["read_io"][str(self.fixture)]["opens"], 2)
                    if fault == "packet-valid":
                        self.assertTrue(value["validation_calls"][1]["accepted"])
                        self.assertNotEqual(self.packet.read_bytes(), self.original_packet)

    def test_preparer_consumer_and_header_declarations_still_checked(self):
        variants = []
        bad = copy.deepcopy(self.request)
        bad["identity"]["preparer"]["executable_sha256"] = "0"*64
        variants.append((bad, "PREPARER_IDENTITY_REJECTED"))
        bad = copy.deepcopy(self.request)
        bad["consumer"]["sha256"] = "0"*64
        variants.append((bad, "CACHE_EXECUTION_FAILED"))
        bad = copy.deepcopy(self.request)
        bad["identity"]["expected_header"]["sector_labels"] *= 2
        variants.append((bad, "INVALID_REQUEST"))
        for request, status in variants:
            for mode in ("reference", "fused"):
                self.attempt(mode, status, request)

    def test_explicit_rebuild_only_and_same_key_publication_lock(self):
        self.damage(self.original_packet[:-1])
        self.attempt("fused", "CACHE_INVALID_REJECTED")
        request = copy.deepcopy(self.request)
        request["invalid_policy"] = "rebuild"
        value = self.attempt("fused", "CACHE_INVALID_REBUILT", request)
        self.assertEqual(value["result"]["packet"], self.prepared["packet"])
        self.assertIsNotNone(value["result"]["quarantine"])
        request["cache_root"] = str(self.root / "concurrent-cache")
        paths = []
        for index in range(2):
            path = self.root / f"concurrent-{index}.json"
            path.write_bytes(canonical_bytes(request))
            paths.append(path)
        def run(path):
            return run_attempt("fused", "execute", path, timeout=15)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, paths))
        self.assertEqual(sorted(value["result"]["status"] for value, _, code in results if code == 0),
                         ["CACHE_HIT_VALIDATED", "CACHE_MISS_PREPARED"])


if __name__ == "__main__":
    unittest.main()
