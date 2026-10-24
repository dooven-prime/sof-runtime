"""A0 only: exact membership, Windows objects, observation lifetime and actual kills."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from applications.solana_offchain_slice.common import canonical, parse, file_sha
from applications.solana_source_advancement.runner import tree_hashes
from applications.solana_inventory_shadow.fixtures import tiny, controls, copy_flat, state_declarations
from applications.solana_inventory_shadow.reference import decode, encode, inspect
from applications.solana_inventory_shadow.runner import ROOT, build, invoke, compare, binary


@unittest.skipUnless(os.name == "nt", "A0 v0 requires Windows NTFS")
class A0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): build()

    def observe(self, root, name, d, m, b, expected):
        r = invoke(d, m, b, root/"logs", name); compare(d, m, b, r)
        self.assertEqual(r["status"], expected, r)
        self.assertEqual(r["application_decision"], "NOT_ASSESSED")
        return r

    def test_normal_exact_manifest_and_opaque_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d, m, b = tiny(root); before = tree_hashes(root)
            r = self.observe(root, "normal", d, m, b, "MATCHED_BYTES")
            self.assertEqual(r["result"]["inspection"]["manifest_utf8"].encode(), m.read_bytes())
            self.assertEqual(r["result"]["observer_identity"]["sha256"], file_sha(binary()))
            for name, digest in before.items(): self.assertEqual(file_sha(root/name), digest)

    def test_missing_extra_damaged_truncated_wrong_type_and_case(self):
        for kind in ("missing", "extra", "damaged", "truncated", "directory", "actual-case"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root); p = d/"payload.bin"
                if kind == "missing": p.unlink()
                elif kind == "extra": (d/"unregistered.bin").write_bytes(b"extra")
                elif kind == "damaged": p.write_bytes(b"X"+p.read_bytes()[1:])
                elif kind == "truncated": p.write_bytes(p.read_bytes()[:-1])
                elif kind == "directory": p.unlink(); p.mkdir()
                else: p.rename(d/"PAYLOAD.bin")
                before = tree_hashes(d)
                self.observe(root, kind, d, m, b, "REJECTED")
                self.assertEqual(tree_hashes(d), before)

    def test_declared_aliases_devices_escape_ads_and_versions(self):
        names = ["../payload.bin", "x/y", "x\\y", "C:payload.bin", "C:\\payload.bin", "\\\\server\\x", "payload.bin:ads",
                 "NUL", "con.txt", "COM1.json", "LPT9", "name.", "name ", "ab\u00e9"]
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root); value = parse(m.read_bytes()); value["entries"][0]["name"] = name
                # Non-ASCII is deliberately outside the restricted codec.
                m.write_bytes(canonical(value))
                self.observe(root, "deny", d, m, b, "REJECTED")
        for kind in ("case-alias", "duplicate", "role", "producer", "schema", "version", "unknown", "order"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root); v = decode(m.read_bytes())
                if kind in ("case-alias", "duplicate"):
                    second = dict(v["entries"][0]); second["name"] = "PAYLOAD.bin" if kind == "case-alias" else second["name"]
                    v["entries"].append(second); v["entries"].sort(key=lambda e: e["name"])
                elif kind == "role": v["declarations"]["identities"]["source"]["role"] = "ExecutionIdentity"
                elif kind == "producer": v["declarations"]["producer"]["executable_sha256"] = file_sha(binary())
                elif kind == "schema": v["declarations"]["schemas"][0]["id"] = "another-schema"
                elif kind == "version": v["codec"] = "unknown.v999"
                elif kind == "unknown": v["unexpected"] = True
                else:
                    v["entries"].append({**v["entries"][0], "name": "aaa.bin"})
                m.write_bytes(encode(v)); self.observe(root, "deny", d, m, b, "REJECTED")

    def test_noncanonical_encoding_and_inexact_types(self):
        for kind in ("newline", "space", "duplicate", "float", "negative", "overflow", "bool-length"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root); raw = m.read_bytes()
                if kind == "newline": raw += b"\n"
                elif kind == "space": raw = b" "+raw
                elif kind == "duplicate": raw = raw.replace(b'"codec":', b'"codec":"ascii-json-u64.v0","codec":', 1)
                else:
                    v = parse(raw); value = {"float": 1.0, "negative": -1, "overflow": 2**64, "bool-length": True}[kind]
                    v["entries"][0]["byte_length"] = value; raw = canonical(v)
                m.write_bytes(raw); self.observe(root, "deny", d, m, b, "REJECTED")

    def test_self_reference_and_detached_controls(self):
        for selected in ("manifest", "bindings"):
            with self.subTest(selected=selected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root)
                source = m if selected == "manifest" else b; target = d/source.name; shutil.copyfile(source, target)
                r = self.observe(root, "deny", d, target if selected == "manifest" else m, target if selected == "bindings" else b, "REJECTED")
                self.assertEqual(r["result"]["error"]["code"], "CONTROL_INSIDE_ROOT")

    def test_actual_named_stream_and_hardlink(self):
        for kind in ("file-ads", "root-ads", "hardlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root); p = d/"payload.bin"
                if kind == "hardlink":
                    external = root/"same-bytes.bin"; external.write_bytes(p.read_bytes()); p.unlink(); os.link(external, p)
                else:
                    path = p if kind == "file-ads" else d
                    with open(str(path)+":hidden", "wb") as f: f.write(b"undeclared named stream")
                r = self.observe(root, "deny", d, m, b, "REJECTED")
                self.assertEqual(r["result"]["error"]["code"], "HARD_LINK" if kind == "hardlink" else "NAMED_STREAM")

    def test_actual_junction_reparse_roots_and_entries(self):
        for kind in ("root", "entry"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root); external = root/"external"; external.mkdir()
                (external/"retain.bin").write_bytes(b"must remain")
                link = root/"root-alias" if kind == "root" else d/"payload.bin"
                if kind == "entry": link.unlink()
                result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(external)], capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                observed = link if kind == "root" else d
                r = self.observe(root, "deny", observed, m, b, "REJECTED")
                self.assertEqual(r["result"]["error"]["code"], "REPARSE_POINT")
                self.assertEqual((external/"retain.bin").read_bytes(), b"must remain")

    def test_actual_kills_never_admit_partial_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d, m, b = tiny(root); before = tree_hashes(d)
            for point in ("enumerated", "hashing", "result_partial"):
                r = invoke(d, m, b, root/"logs", point, pause=point)
                self.assertEqual(r["status"], "INCOMPLETE"); self.assertTrue(r["process"]["actually_killed"])
                self.assertFalse(r["matching_observation_admissible"])
                self.assertEqual(tree_hashes(d), before)
                self.observe(root, point+"-fresh", d, m, b, "MATCHED_BYTES")

    def test_mutation_and_replacement_are_detected_in_the_same_window(self):
        for kind in ("content", "replacement", "extra-file", "named-stream"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root); p = d/"payload.bin"
                def change():
                    if kind == "content": p.write_bytes(b"X"+p.read_bytes()[1:])
                    elif kind == "replacement": raw = p.read_bytes(); p.rename(root/"retired.bin"); p.write_bytes(raw)
                    elif kind == "extra-file": (d/"extra.bin").write_bytes(b"extra")
                    else:
                        with open(str(p)+":hidden", "wb") as f: f.write(b"extra")
                r = invoke(d, m, b, root/"logs", "mutate", pause="after_hash", change=change)
                self.assertEqual(r["status"], "INCOMPLETE", r)
                self.assertTrue(r["process"]["changed_during_observation"])
                self.assertEqual(r["result"]["error"]["code"], "INPUT_CHANGED", r)
                self.observe(root, "fresh", d, m, b, "MATCHED_BYTES" if kind == "replacement" else "REJECTED")

    def test_success_is_not_a_future_snapshot_credential(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d, m, b = tiny(root)
            first = self.observe(root, "first", d, m, b, "MATCHED_BYTES")
            self.assertEqual(first["result"]["validity"], "OBSERVED_INTERVAL_ONLY")
            p = d/"payload.bin"; p.write_bytes(b"X"+p.read_bytes()[1:])
            self.observe(root, "new-observation", d, m, b, "REJECTED")

    def test_original_producer_identity_and_semantic_boundary(self):
        from applications.solana_incremental_replay.fixtures import synthetic
        from applications.solana_source_advancement.fixtures import corpus, request
        from applications.solana_publication_recovery.runner import invoke as original_invoke, build as original_build, binary as original_binary
        from applications.solana_publication_recovery.reference import predict
        from applications.solana_source_advancement.reference import check_success
        original_build()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); domain = corpus(synthetic(root/"upstream"), root/"corpus", small=True)
            req = self._request(root, request(domain["policy"], domain["captures"]["a-3"], "init"))
            original, _ = original_invoke(req, root/"producer", root/"original-logs", "original")
            expected = predict(req, root/"producer")
            old = tree_hashes(root/"producer"); producer_identity = file_sha(original_binary())
            d = copy_flat(root/"producer", root/"copy"); declared = state_declarations(d)
            self.assertEqual(declared["producer"]["executable_sha256"], producer_identity)
            self.assertNotEqual(producer_identity, file_sha(binary()))
            p = next(d.glob("slot-*.jsonl")); rows = [parse(line) for line in p.read_bytes().splitlines()]
            rows[1]["fee"] += 1; p.write_bytes(b"".join(canonical(row)+b"\n" for row in rows))
            m, b = controls(d, root/"controls", declared)
            r = self.observe(root, "opaque", d, m, b, "MATCHED_BYTES")
            with self.assertRaises(ValueError): check_success(expected, original["advancement"], d)
            self.assertEqual(r["result"]["application_decision"], "NOT_ASSESSED")
            self.assertEqual(tree_hashes(root/"producer"), old)

    def _request(self, root, value):
        p = root/"req.json"; p.write_bytes(canonical(value)); return p

    def test_common_invalid_metadata_is_not_hidden_by_matching_bindings(self):
        for kind in ("producer-int", "schema-int", "schemas-not-array", "entry-string-length"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d, m, b = tiny(root); value = decode(m.read_bytes()); expected = decode(b.read_bytes())
                if kind == "producer-int": value["declarations"]["producer"]["id"] = 1
                elif kind == "schema-int": value["declarations"]["schemas"][0]["id"] = 1
                elif kind == "schemas-not-array": value["declarations"]["schemas"] = {}
                else: value["entries"][0]["byte_length"] = "1400"
                expected["declarations"] = value["declarations"]
                m.write_bytes(encode(value)); b.write_bytes(encode(expected))
                self.observe(root, "deny", d, m, b, "REJECTED")


if __name__ == "__main__": unittest.main()
