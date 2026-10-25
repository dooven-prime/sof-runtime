"""Probe accounting, immutable-state behavior and retained rejection paths."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from time import perf_counter, sleep
import unittest

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from applications.solana_incremental_replay.fixtures import synthetic
from applications.solana_incremental_replay.reference import segments
from applications.solana_incremental_replay.runner import binary as replay_binary, invoke as replay
from applications.solana_prefix_integrity.runner import build, invoke, observed_files, warm, HERE
from applications.solana_prefix_integrity.experiment import classify


class PrefixIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def prefix(self, root):
        manifest = synthetic(root/"capture")
        state = root/"state"
        replay(manifest, state, root/"logs", "generate", pause=("checkpoint_publish", 100))
        return manifest, state, file_sha(state/"checkpoint.json")

    def test_read_only_full_validation_and_exact_phase_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest, state, anchor = self.prefix(root)
            before = {p.name: p.read_bytes() for p in state.iterdir()}
            result, process = invoke(manifest, state, anchor, root/"aggregate.jsonl", 1, root/"logs", "probe")
            self.assertEqual(result["status"], "MEASURED_VERIFIED_PREFIX")
            self.assertEqual(process["returncode"], 0)
            self.assertEqual(result["block_decodes"], 0)
            self.assertEqual(result["new_commits"], 0)
            expected = next(segments(manifest))["bytes"]
            self.assertEqual((root/"aggregate.jsonl").read_bytes(), expected)
            self.assertEqual(result["aggregate_sha256"], sha(expected))
            self.assertEqual(before, {p.name: p.read_bytes() for p in state.iterdir()})
            m = parse(manifest.read_bytes()); raw = manifest.parent/m["rpc"]["block-100"]["response"]
            ps = result["phases"]
            self.assertEqual(ps["raw_input_hash"]["logical_read_bytes"], raw.stat().st_size)
            self.assertEqual(ps["segment_validation"]["logical_read_bytes"], len(expected))
            self.assertEqual(ps["aggregate_stream"]["logical_read_bytes"], len(expected))
            self.assertEqual(ps["aggregate_stream"]["logical_written_bytes"], len(expected))
            for phase in ps.values():
                self.assertGreaterEqual(phase["wall_seconds"], 0)
                self.assertAlmostEqual(phase["cpu_seconds"], phase["kernel_cpu_seconds"]+phase["user_cpu_seconds"])
                self.assertGreaterEqual(phase["os_process_io"]["read_operations"], 0)

    def test_copied_state_matches_and_prewarm_does_not_change_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest, state, anchor = self.prefix(root)
            copied = root/"copied"; shutil.copytree(state, copied)
            results = []
            for name, candidate in (("fresh", state), ("copied", copied)):
                warmup = warm(observed_files(manifest, candidate, 1))
                self.assertEqual(warmup["kind"], "EXPLICIT_READ_ONLY_NOT_VALIDATION")
                result, _ = invoke(manifest, candidate, anchor, root/f"{name}.jsonl", 1, root/"logs", name)
                self.assertEqual(result["status"], "MEASURED_VERIFIED_PREFIX")
                results.append(result)
            self.assertEqual(results[0]["aggregate_sha256"], results[1]["aggregate_sha256"])
            for phase in ("checkpoint_anchor", "raw_input_hash", "segment_validation", "aggregate_stream", "post_consumption_integrity"):
                self.assertEqual(results[0]["phases"][phase]["logical_read_bytes"], results[1]["phases"][phase]["logical_read_bytes"])

    def test_corruptions_and_false_cursor_fail_closed(self):
        for kind in ("anchor", "checkpoint", "cursor", "identity", "input", "segment", "future-orphan", "uncommitted-input"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); manifest, state, anchor = self.prefix(root)
                if kind == "anchor": anchor = "0"*64
                elif kind == "identity": (state/"identity.json").write_bytes(b"{}")
                elif kind in ("checkpoint", "cursor"):
                    target = state/"checkpoint.json"; frame = parse(target.read_bytes())
                    if kind == "checkpoint": frame["body_sha256"] = "0"*64
                    else:
                        frame["body"]["next_index"] = True
                        frame["body_sha256"] = sha(canonical(frame["body"]))
                    target.write_bytes(canonical(frame))
                    # Test-only supplied hash reaches the frame/cursor rejection, not an admission claim.
                    anchor = file_sha(target)
                elif kind in ("input", "uncommitted-input"):
                    m = parse(manifest.read_bytes()); slot = 100 if kind == "input" else 102
                    target = manifest.parent/m["rpc"][f"block-{slot}"]["response"]
                    target.write_bytes(target.read_bytes()+b" ")
                elif kind == "segment": (state/"slot-100.jsonl").write_bytes(b"broken\n")
                else: (state/"slot-102.jsonl").write_bytes(b"orphan\n")
                result, _ = invoke(manifest, state, anchor, root/"output.jsonl", 1, root/"logs", "bad")
                self.assertEqual(result["status"], "UNRESOLVED")
                if kind == "uncommitted-input":
                    self.assertIn("input changed during consumption", result["error"])

    def test_mtime_is_neither_acceptance_credential_nor_rejection_basis(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest, state, anchor = self.prefix(root)
            target = state/"slot-100.jsonl"; s = target.stat()
            os.utime(target, ns=(s.st_atime_ns, s.st_mtime_ns-1000000000))
            good, _ = invoke(manifest, state, anchor, root/"good.jsonl", 1, root/"logs", "good")
            self.assertEqual(good["status"], "MEASURED_VERIFIED_PREFIX")
            s = target.stat(); data = target.read_bytes()
            target.write_bytes(b"x"+data[1:]); os.utime(target, ns=(s.st_atime_ns, s.st_mtime_ns))
            warm(observed_files(manifest, state, 1))
            bad, _ = invoke(manifest, state, anchor, root/"bad.jsonl", 1, root/"logs", "bad")
            self.assertEqual(bad["status"], "UNRESOLVED")
            self.assertIn("segment corruption", bad["error"])

    def test_no_output_inside_state_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest, state, anchor = self.prefix(root)
            bad, _ = invoke(manifest, state, anchor, state/"scratch.jsonl", 1, root/"logs", "inside")
            self.assertEqual(bad["status"], "UNRESOLVED")
            output = root/"existing.jsonl"; output.write_bytes(b"retain")
            bad, _ = invoke(manifest, state, anchor, output, 1, root/"logs", "overwrite")
            self.assertEqual(bad["status"], "UNRESOLVED")
            self.assertEqual(output.read_bytes(), b"retain")

    def test_complete_state_published_aggregate_still_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = synthetic(root/"capture"); state = root/"state"
            result, _ = replay(manifest, state, root/"logs", "complete")
            anchor = result["checkpoint_sha256"]
            good, _ = invoke(manifest, state, anchor, root/"good.jsonl", 3, root/"logs", "good")
            self.assertEqual(good["status"], "MEASURED_VERIFIED_PREFIX")
            (state/"projection.jsonl").write_bytes(b"broken\n")
            bad, _ = invoke(manifest, state, anchor, root/"bad.jsonl", 3, root/"logs", "bad")
            self.assertEqual(bad["status"], "UNRESOLVED")
            self.assertIn("aggregate corruption", bad["error"])

    def test_actual_writer_lock_is_not_bypassed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = synthetic(root/"capture"); state = root/"state"
            with (root/"held.txt").open("wb") as stream:
                child = subprocess.Popen([str(replay_binary()), str(manifest), str(state), "incremental", "--pause", "checkpoint_publish", "100"], stdout=stream, stderr=subprocess.PIPE)
                try:
                    start = perf_counter()
                    while b"FAULT_REACHED" not in (root/"held.txt").read_bytes():
                        if child.poll() is not None or perf_counter()-start > 15: self.fail("writer did not pause")
                        sleep(.01)
                    anchor = file_sha(state/"checkpoint.json")
                    bad, _ = invoke(manifest, state, anchor, root/"bad.jsonl", 1, root/"logs", "bad")
                    self.assertEqual(bad["status"], "UNRESOLVED")
                    self.assertIn("writer conflict", bad["error"])
                finally:
                    if child.poll() is None: child.kill()
                    child.communicate(timeout=5)

    def test_classification_respects_frozen_threshold_and_stop_rule(self):
        plan = parse((HERE/"plan.v1.json").read_bytes()); attempts = []
        for pair in range(4):
            for condition in ("initial", "read_warmed", "read_warmed"):
                phase = {"wall_seconds": .5 if condition == "initial" else .01, "cpu_seconds": .005}
                attempts.append({"pair": pair, "state_kind": "copied", "condition": condition,
                                 "result": {"phases": {"raw_input_hash": phase, "segment_validation": phase}}})
        result = classify(attempts, plan)
        self.assertEqual(result["classification"], "NON_CPU_FILE_STATE_SENSITIVE_COST")
        self.assertEqual(result["action"], "STOP_FIXED_CAPTURE_ACCELERATION")
        for a in attempts:
            for p in a["result"]["phases"].values(): p["cpu_seconds"] = p["wall_seconds"]
        self.assertEqual(classify(attempts, plan)["classification"], "BOUNDED_CPU_CANDIDATE_ONLY")


if __name__ == "__main__":
    unittest.main()
