"""Actual process interruption and strict publication admission controls."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from time import monotonic, sleep
import unittest

from applications.solana_offchain_slice.common import canonical, parse
from applications.solana_incremental_replay.fixtures import synthetic
from applications.solana_source_advancement.fixtures import corpus, request
from applications.solana_source_advancement.runner import tree_hashes
from applications.solana_publication_recovery.runner import ROOT, POINTS, binary, build, control, invoke, write_request
from applications.solana_publication_recovery.reference import check, equal_state, predict


class PublicationRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): build()

    def domain(self, root):
        d = corpus(synthetic(root/"upstream"), root/"corpus", small=True)
        req = write_request(root/"init.json", request(d["policy"], d["captures"]["a-2"], "init"))
        initial, _ = invoke(req, root/"parent", root/"logs", "init")
        check(req, root/"parent", initial)
        d["parent"] = root/"parent"; d["anchor"] = initial["advancement"]["new_checkpoint_sha256"]
        return d

    def req(self, root, d, mode="append", name="request"):
        cap = "a-3" if mode == "append" else "b-full"
        return write_request(root/f"{name}.json", request(d["policy"], d["captures"][cap], mode,
            d["captures"]["a-2"], d["parent"], d["anchor"]))

    def test_all_kill_points_append_and_credential_reapproval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.domain(root)
            parent_before, captures_before = tree_hashes(d["parent"]), tree_hashes(root/"corpus")
            for mode in ("append", "reapprove"):
                req = self.req(root, d, mode, mode)
                clean = root/f"clean-{mode}"; result, _ = invoke(req, clean, root/"logs", f"clean-{mode}"); check(req, clean, result)
                for point in POINTS:
                    name = f"{mode}-{point}"; dest = root/name
                    _, process = invoke(req, dest, root/"logs", name+"-kill", point)
                    self.assertTrue(process["actually_killed"])
                    if point in ("after_publication", "receipt_partial", "receipt_published"):
                        self.assertTrue(dest.exists())
                    else: self.assertFalse(dest.exists())
                    recovered, _ = invoke(req, dest, root/"logs", name+"-resume"); check(req, dest, recovered)
                    equal_state(clean, dest)
                    receipt = (control(dest)/"receipt.json").read_bytes()
                    replay, _ = invoke(req, dest, root/"logs", name+"-retry"); check(req, dest, replay)
                    self.assertEqual(replay["recovery"], "REPLAYED_PUBLISHED")
                    self.assertEqual(receipt, (control(dest)/"receipt.json").read_bytes())
                    self.assertEqual(tree_hashes(d["parent"]), parent_before)
                    self.assertEqual(tree_hashes(root/"corpus"), captures_before)

    def test_repeated_interruption_from_same_concrete_operation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.domain(root); req = self.req(root, d); dest = root/"result"
            for i, point in enumerate(("transition_partial", "checkpoint_partial", "after_publication", "receipt_partial")):
                invoke(req, dest, root/"logs", str(i), point)
            result, _ = invoke(req, dest, root/"logs", "done"); check(req, dest, result)

    def test_concurrent_writer_cannot_confirm_or_modify_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.domain(root); req = self.req(root, d); dest = root/"result"
            marker = root/"held.json"; before = tree_hashes(d["parent"])
            child = subprocess.Popen([str(binary()), str(req), str(dest), "--pause", "stage_created", str(marker)], cwd=ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = monotonic()+30
                while not marker.exists() and child.poll() is None and monotonic() < deadline: sleep(.01)
                self.assertTrue(marker.exists())
                denied, _ = invoke(req, dest, root/"logs", "competitor")
                self.assertFalse(denied["publication_confirmed"])
                self.assertEqual(denied["reason"], "PUBLICATION_WRITER_CONFLICT")
            finally:
                if child.poll() is None: child.kill()
                child.communicate(timeout=10)
            result, _ = invoke(req, dest, root/"logs", "recovered"); check(req, dest, result)
            self.assertEqual(tree_hashes(d["parent"]), before)

    def test_changed_bound_request_policy_source_or_parent_refuses(self):
        for kind in ("request", "policy", "source", "parent", "intent-executable"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d = self.domain(root); req = self.req(root, d); dest = root/"result"
                invoke(req, dest, root/"logs", "kill", "stage_created")
                if kind == "request":
                    value = parse(req.read_bytes()); value["mode"] = "reapprove"; req.write_bytes(canonical(value))
                elif kind == "policy":
                    d["policy"].write_bytes(d["policy"].read_bytes()+b" ")
                elif kind == "source":
                    p = d["captures"]["a-3"].parent/"credential.json"; p.write_bytes(p.read_bytes()+b" ")
                elif kind == "parent":
                    (d["parent"]/"projection.jsonl").write_bytes(b"corrupt\n")
                else:
                    p = control(dest)/"intent.json"; v = parse(p.read_bytes()); v["executable_sha256"] = "0"*64; p.write_bytes(canonical(v))
                before = tree_hashes(d["parent"]); metadata = tree_hashes(control(dest))
                denied, _ = invoke(req, dest, root/"logs", "deny")
                self.assertFalse(denied["publication_confirmed"]); self.assertFalse(dest.exists())
                self.assertEqual(tree_hashes(d["parent"]), before)
                self.assertEqual(tree_hashes(control(dest)), metadata)

    def test_corrupt_staging_final_pending_and_foreign_file_refuse(self):
        for kind in ("final", "pending", "foreign", "ready"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d = self.domain(root); req = self.req(root, d); dest = root/"result"
                point = "segment_partial" if kind == "pending" else "ready_published" if kind == "ready" else "segment_published"
                invoke(req, dest, root/"logs", "kill", point)
                stage = control(dest)/"stage"
                if kind == "final": next(stage.glob("slot-*.jsonl")).write_bytes(b"corrupt")
                elif kind == "pending": next(stage.glob("*.pending")).write_bytes(b"not a prefix")
                elif kind == "foreign": (stage/"unknown.json").write_bytes(b"{}")
                else: (control(dest)/"ready.json").write_bytes(b"{}")
                stage_before = tree_hashes(stage)
                result, _ = invoke(req, dest, root/"logs", "deny")
                self.assertFalse(result["publication_confirmed"]); self.assertFalse(dest.exists())
                self.assertEqual(tree_hashes(stage), stage_before)

    def test_incomplete_or_corrupt_published_output_never_repaired_as_success(self):
        for kind in ("missing-checkpoint", "segment", "receipt", "foreign-destination"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d = self.domain(root); req = self.req(root, d); dest = root/"result"
                if kind == "foreign-destination":
                    dest.mkdir(); (dest/"retain.txt").write_text("retain")
                else:
                    result, _ = invoke(req, dest, root/"logs", "clean"); check(req, dest, result)
                    if kind == "missing-checkpoint": (dest/"checkpoint.json").unlink()
                    elif kind == "segment": next(dest.glob("slot-*.jsonl")).write_bytes(b"corrupt")
                    else: (control(dest)/"receipt.json").write_bytes(b"{}")
                before = tree_hashes(dest)
                result, _ = invoke(req, dest, root/"logs", "deny")
                self.assertFalse(result["publication_confirmed"])
                self.assertEqual(tree_hashes(dest), before)

    def test_source_semantic_refusals_remain_refusals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.domain(root); before = tree_hashes(d["parent"])
            for cap, mode in (("conflict", "reapprove"), ("listed-conflict", "reapprove"), ("unknown", "reapprove"), ("b-full", "append")):
                req = write_request(root/f"{cap}.json", request(d["policy"], d["captures"][cap], mode,
                    d["captures"]["a-2"], d["parent"], d["anchor"]))
                dest = root/cap; expected = predict(req, dest)
                actual, _ = invoke(req, dest, root/"logs", cap)
                self.assertEqual(actual["status"], expected["status"])
                self.assertFalse(actual["publication_confirmed"]); self.assertFalse(dest.exists())
                self.assertFalse((control(dest)/"receipt.json").exists())
            self.assertEqual(tree_hashes(d["parent"]), before)

    def test_output_and_fault_marker_do_not_pollute_protected_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.domain(root); req = self.req(root, d)
            paths = (d["parent"], d["captures"]["a-2"].parent, d["captures"]["a-3"].parent)
            before = {p: tree_hashes(p) for p in paths}
            for i, path in enumerate(paths):
                result, _ = invoke(req, path/"forbidden", root/"logs", str(i))
                self.assertFalse(result["publication_confirmed"])
                process = subprocess.run([str(binary()), str(req), str(root/f"output-{i}"), "--pause", "stage_created", str(path/"marker.json")],
                    cwd=ROOT, capture_output=True, check=False, timeout=10)
                self.assertEqual(parse(process.stdout)["reason"], "UNSAFE_FAULT_MARKER")
            for p in paths: self.assertEqual(tree_hashes(p), before[p])


if __name__ == "__main__": unittest.main()
