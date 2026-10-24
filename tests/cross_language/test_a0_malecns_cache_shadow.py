import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from applications.malecns_cache_inventory_shadow.fixtures import tiny
from applications.malecns_cache_inventory_shadow.reference import encode, decode, declarations, SCHEMA
from applications.malecns_cache_inventory_shadow.runner import build, invoke, compare


@unittest.skipUnless(os.name == "nt", "A0 v0 requires local Windows NTFS")
class CacheShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): build()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a0-cache-shadow-")
        self.root = Path(self.temp.name).resolve()
        self.data, self.manifest, self.expected = tiny(self.root)

    def tearDown(self): self.temp.cleanup()

    def check(self, label, expected="MATCHED_BYTES", **kwargs):
        o = invoke(self.data, self.manifest, self.expected, self.root/"logs", label, **kwargs)
        if not kwargs: compare(self.data, self.manifest, self.expected, o)
        self.assertEqual(o["status"], expected)
        self.assertEqual(o["cache_hit_permission"], "NOT_GRANTED")
        self.assertEqual(o["cache_policy"], "NOT_INVOKED")
        return o

    def test_normal_and_identity_roles(self):
        o = self.check("normal")
        self.assertEqual(o["result"]["inspection"]["byte_passes"], 2)
        self.assertNotEqual(o["observer_executable_sha256"], "0"*64)
        d = decode(self.manifest.read_bytes())["declarations"]["identities"]
        self.assertEqual(set(d), {"source", "execution", "cache"})
        self.assertEqual(len({v["sha256"] for v in d.values()}), 1)

    def test_roles_not_interchangeable_even_when_both_declarations_agree(self):
        raw, expected = self.manifest.read_bytes(), self.expected.read_bytes()
        for name in ("source", "execution", "cache"):
            with self.subTest(name=name):
                m, b = decode(raw), decode(expected)
                for value in (m, b): value["declarations"]["identities"][name]["role"] = "CheckpointIdentity"
                self.manifest.write_bytes(encode(m)); self.expected.write_bytes(encode(b))
                self.check("role-"+name, "REJECTED")

    def test_cache_profile_cannot_use_checkpoint_slot(self):
        m, b = decode(self.manifest.read_bytes()), decode(self.expected.read_bytes())
        for value in (m, b):
            ids = value["declarations"]["identities"]
            ids["checkpoint"] = ids.pop("cache"); ids["checkpoint"]["role"] = "CheckpointIdentity"
        self.manifest.write_bytes(encode(m)); self.expected.write_bytes(encode(b))
        self.check("wrong-slot", "REJECTED")

    def test_binding_mismatch(self):
        m = decode(self.manifest.read_bytes()); m["declarations"]["identities"]["cache"]["sha256"] = "1"*64
        self.manifest.write_bytes(encode(m)); self.check("binding", "REJECTED")

    def test_exact_membership_and_noncanonical(self):
        p = self.data/"extra.bin"; p.write_bytes(b"extra")
        self.check("extra", "REJECTED"); p.unlink()
        self.manifest.write_bytes(self.manifest.read_bytes()+b"\n")
        self.check("noncanonical", "REJECTED")

    def test_missing_damage_and_wrong_type(self):
        p = self.data/"packet.bin"; raw = p.read_bytes()
        p.write_bytes(raw[:-1]); self.check("truncated", "REJECTED")
        p.unlink(); self.check("missing", "REJECTED")
        p.mkdir(); self.check("directory", "REJECTED")

    def test_no_cache_permission_after_actual_kill(self):
        for point in ("enumerated", "hashing", "result_partial"):
            with self.subTest(point=point):
                o = self.check("kill-"+point, "INCOMPLETE", pause=point)
                self.assertTrue(o["process"]["actually_killed"])
                self.assertFalse(o["matching_observation_admissible"])
                self.check("fresh-"+point)

    def test_same_byte_replacement_invalidates_interval(self):
        p = self.data/"packet.bin"
        def change():
            raw = p.read_bytes(); p.rename(self.root/"retired.bin"); p.write_bytes(raw)
        o = self.check("replace", "INCOMPLETE", pause="after_hash", change=change)
        self.assertEqual(o["result"]["error"]["code"], "INPUT_CHANGED")
        self.check("fresh")

    def test_manifest_is_detached(self):
        p = self.data/"inventory.json"; p.write_bytes(self.manifest.read_bytes()); self.manifest = p
        self.check("self-reference", "REJECTED")

    def test_observation_does_not_parse_packet(self):
        # tiny() deliberately contains invalid packet bytes. Integrity is not grammar.
        self.check("opaque-invalid")

    def test_codec_is_identical_to_first_shadow(self):
        from applications.solana_inventory_shadow.reference import encode as old_encode
        for value in ({}, {"b": 2, "a": 1}, [2, 1], {"s": '"\\/'}, {"n": 2**64-1}, [False, None, 1, "1"]):
            self.assertEqual(encode(value), old_encode(value))
        m = decode(self.manifest.read_bytes())
        self.assertEqual(declarations(encode(m), self.expected.read_bytes())["schema"], SCHEMA)


if __name__ == "__main__": unittest.main()
