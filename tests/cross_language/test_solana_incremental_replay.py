"""Incremental work avoidance, anchored integrity and continuous crash recovery."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from time import perf_counter, sleep
import unittest

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from applications.solana_offchain_slice.fixtures import change_response, b58
from applications.solana_incremental_replay.fixtures import synthetic
from applications.solana_incremental_replay.reference import load, projection
from applications.solana_incremental_replay.runner import POINTS, binary, build, check_work, invoke


class IncrementalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def test_clean_and_complete_reuse_without_any_block_decode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = synthetic(root/"capture"); state = root/"state"
            m, _ = load(manifest)
            first, _ = invoke(manifest, state, root, "first")
            self.assertEqual(first["status"], "COMPLETED_LOCAL_CAPTURE")
            check_work(first, m, 0, "incremental")
            self.assertEqual((state/"projection.jsonl").read_bytes(), projection(manifest))
            before = {p.name: p.read_bytes() for p in state.iterdir()}
            repeat, _ = invoke(manifest, state, root, "repeat", anchor=first["checkpoint_sha256"], forbid_prefix=True)
            self.assertEqual(repeat["status"], "COMPLETED_LOCAL_CAPTURE")
            check_work(repeat, m, 3, "incremental")
            self.assertEqual(repeat["work"]["prefix_decode_bytes"], 0)
            self.assertEqual(repeat["work"]["suffix_decode_bytes"], 0)
            self.assertGreater(repeat["work"]["prefix_verified_input_bytes"], 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in state.iterdir()})

    def test_all_six_actual_kills_resume_exact_uncommitted_suffix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = synthetic(root/"capture"); m, _ = load(manifest)
            for point in POINTS:
                with self.subTest(point=point):
                    state = root/point
                    _, resource = invoke(manifest, state, root, point+"-kill", pause=(point, 102 if "projection" in point else 100))
                    self.assertTrue(resource["terminated_at_boundary"])
                    body = parse((state/"checkpoint.json").read_bytes())["body"]
                    initial = body["next_index"]
                    result, _ = invoke(manifest, state, root, point+"-resume", anchor=file_sha(state/"checkpoint.json"), forbid_prefix=True)
                    self.assertEqual(result["status"], "COMPLETED_LOCAL_CAPTURE")
                    check_work(result, m, initial, "incremental")
                    self.assertEqual((state/"projection.jsonl").read_bytes(), projection(manifest))
                    if point in ("segment_publish", "partial_checkpoint"):
                        self.assertEqual(result["work"]["adopted_orphans"], 1)

    def test_matched_prefix_full_and_incremental_modes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = synthetic(root/"capture"); m, _ = load(manifest)
            invoke(manifest, root/"snapshot", root, "kill", pause=("checkpoint_publish", 100))
            anchor = file_sha(root/"snapshot/checkpoint.json")
            for mode in ("incremental", "full_reproject"):
                state = root/mode; shutil.copytree(root/"snapshot", state)
                result, _ = invoke(manifest, state, root, mode, mode=mode, anchor=anchor, forbid_prefix=mode=="incremental")
                self.assertEqual(result["status"], "COMPLETED_LOCAL_CAPTURE")
                check_work(result, m, 1, mode)
                self.assertEqual((state/"projection.jsonl").read_bytes(), projection(manifest))
            self.assertEqual((root/"incremental/checkpoint.json").read_bytes(), (root/"full_reproject/checkpoint.json").read_bytes())

    def test_unanchored_resume_refused_full_reproject_can_admit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = synthetic(root/"capture"); state = root/"state"
            first, _ = invoke(manifest, state, root, "first")
            for name, anchor in (("absent", None), ("wrong", "0"*64)):
                result, _ = invoke(manifest, state, root, name, anchor=anchor)
                self.assertEqual(result["status"], "UNRESOLVED")
                self.assertIn("anchor", result["error"])
            admitted, _ = invoke(manifest, state, root, "admit", mode="full_reproject")
            self.assertEqual(admitted["checkpoint_sha256"], first["checkpoint_sha256"])
            trapped, _ = invoke(manifest, state, root, "trap", mode="full_reproject", forbid_prefix=True)
            self.assertEqual(trapped["status"], "UNRESOLVED")
            self.assertIn("decode trap", trapped["error"])

    def test_committed_corruption_is_not_hidden_or_repaired(self):
        for kind in ("input", "segment", "aggregate", "checkpoint", "cursor", "coordinated", "foreign", "identity", "plan"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); manifest = synthetic(root/"capture"); state = root/"state"
                first, _ = invoke(manifest, state, root, "first")
                target = None
                if kind == "input":
                    m = parse(manifest.read_bytes()); target = manifest.parent/m["rpc"]["block-100"]["response"]
                    target.write_bytes(target.read_bytes()+b" ")
                elif kind in ("segment", "aggregate", "foreign", "identity", "plan"):
                    target = {"segment": state/"slot-100.jsonl", "aggregate": state/"projection.jsonl",
                              "foreign": state/"unexpected.json", "identity": state/"identity.json", "plan": manifest.parent/"plan.json"}[kind]
                    target.write_bytes(b"damaged\n")
                else:
                    target = state/"checkpoint.json"; frame = parse(target.read_bytes())
                    if kind == "checkpoint":
                        frame["body_sha256"] = "0"*64
                    elif kind == "cursor":
                        frame["body"]["next_index"] = True
                        frame["body_sha256"] = sha(canonical(frame["body"]))
                    else:
                        raw = b"invented output\n"; (state/"slot-100.jsonl").write_bytes(raw)
                        frame["body"]["committed"][0].update(sha256=sha(raw), bytes=len(raw), records=1)
                        frame["body_sha256"] = sha(canonical(frame["body"]))
                    target.write_bytes(canonical(frame))
                before = target.read_bytes()
                result, _ = invoke(manifest, state, root, "bad", anchor=first["checkpoint_sha256"], forbid_prefix=True)
                self.assertEqual(result["status"], "UNRESOLVED")
                self.assertEqual(target.read_bytes(), before)

    def test_full_reproject_rejects_self_consistent_but_false_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = synthetic(root/"capture"); state = root/"state"
            invoke(manifest, state, root, "first")
            target = state/"checkpoint.json"; frame = parse(target.read_bytes())
            raw = b"{}\n{}\n{}\n"; (state/"slot-100.jsonl").write_bytes(raw)
            frame["body"]["committed"][0].update(sha256=sha(raw), bytes=len(raw))
            frame["body_sha256"] = sha(canonical(frame["body"]))
            target.write_bytes(canonical(frame))
            result, _ = invoke(manifest, state, root, "bad", mode="full_reproject")
            self.assertEqual(result["status"], "UNRESOLVED")
            self.assertIn("full-reproject", result["error"])

    def test_suffix_compatibility_and_chain_errors_are_not_filtered(self):
        cases = [lambda r: r["result"]["transactions"][0].update(version=1),
                 lambda r: r.update(error={"code": -32015, "message": "unsupported"}),
                 lambda r: r.update(result=None),
                 lambda r: r["result"].update(previousBlockhash=b58(777)),
                 lambda r: r["result"]["transactions"][0]["transaction"]["message"]["instructions"][0].update(programIdIndex=250),
                 lambda r: r["result"]["transactions"][1]["meta"].pop("loadedAddresses")]
        for index, transform in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); manifest = synthetic(root/"capture")
                change_response(manifest, "block-100", transform)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    projection(manifest)
                result, _ = invoke(manifest, root/"state", root, "bad")
                self.assertEqual(result["status"], "UNRESOLVED")
                self.assertEqual(parse((root/"state/checkpoint.json").read_bytes())["body"]["next_index"], 0)

    def test_confined_capture_duplicate_keys_and_strict_types(self):
        for kind in ("path", "duplicate-json", "boolean-id", "boolean-config", "index", "range", "aliased-file"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); manifest = synthetic(root/"capture"); m = parse(manifest.read_bytes())
                if kind == "path": m["rpc"]["block-100"]["response"] = "../outside.json"
                elif kind == "boolean-id": m["rpc"]["version"]["id"] = True
                elif kind == "boolean-config": m["config"]["maxSupportedTransactionVersion"] = False
                elif kind == "index": m["listed_blocks"].reverse()
                elif kind == "range": m["end_slot"] = 356
                elif kind == "aliased-file": m["rpc"]["block-102"]["response"] = m["rpc"]["block-100"]["response"]
                else:
                    item = m["rpc"]["block-100"]; raw = b'{"id":9,"id":9,"jsonrpc":"2.0","result":null}'
                    (manifest.parent/item["response"]).write_bytes(raw); item["response_sha256"] = sha(raw)
                manifest.write_bytes(canonical(m))
                with self.assertRaises((ValueError, KeyError, TypeError, FileNotFoundError)):
                    projection(manifest)
                result, _ = invoke(manifest, root/"state", root, "bad")
                self.assertEqual(result["status"], "UNRESOLVED")

    def test_writer_conflict_and_future_orphan_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = synthetic(root/"capture"); state = root/"state"
            with (root/"held.txt").open("wb") as stream:
                child = subprocess.Popen([str(binary()), str(manifest), str(state), "incremental", "--pause", "segment_publish", "100"], stdout=stream, stderr=subprocess.PIPE)
                try:
                    start = perf_counter()
                    while b"FAULT_REACHED" not in (root/"held.txt").read_bytes():
                        if child.poll() is not None or perf_counter()-start > 15: self.fail("writer not paused")
                        sleep(.01)
                    result, _ = invoke(manifest, state, root, "conflict")
                    self.assertEqual(result["status"], "UNRESOLVED")
                    self.assertIn("writer", result["error"])
                finally:
                    if child.poll() is None: child.kill()
                    child.communicate(timeout=5)
            (state/"slot-102.jsonl").write_bytes(b"invented\n")
            result, _ = invoke(manifest, state, root, "orphan")
            self.assertEqual(result["status"], "UNRESOLVED")
            self.assertIn("orphan", result["error"])


if __name__ == "__main__":
    unittest.main()
