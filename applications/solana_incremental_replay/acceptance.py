"""Correctness-gated paired recovery curves on the predeclared 64-slot capture."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from .capture import PLAN
from .reference import coverage, load, segments
from .runner import HERE, POINTS, ROOT, bindings, build, invoke
from .validation import check_result, check_state, expected_entries


def run(manifest_path, directory):
    build()
    manifest_path = Path(manifest_path).resolve(strict=True)
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=False)
    plan = parse(PLAN.read_bytes())
    m, msha = load(manifest_path)
    if m["plan_sha256"] != file_sha(PLAN) or m["start_slot"] != plan["start_slot"] or m["end_slot"] != plan["start_slot"]+plan["count"]-1 or m["source"] != plan["endpoint"] or m["capture_kind"] != "rpc_capture":
        raise ValueError("capture is not the predeclared larger real sample")
    before = bindings()
    source_files = {p.name: file_sha(p) for p in sorted(manifest_path.parent.iterdir()) if p.is_file()}
    projected = list(segments(manifest_path))
    expected = b"".join(s["bytes"] for s in projected)
    (root/"reference.jsonl").write_bytes(expected)
    entries = expected_entries(manifest_path, projected)
    identity = {"manifest_sha256": msha, "projection": m["projection"], "executable_sha256": before["rust_binary"]}
    attempts, complete = [], set()

    def call(name, state, mode="incremental", initial=0, anchor=None, pause=None):
        result, resource = invoke(manifest_path, root/state, root/"logs", name, mode=mode, anchor=anchor,
                                  pause=pause, forbid_prefix=mode=="incremental", timeout=plan["process_timeout_seconds"])
        record = {"name": name, "state": state, "mode": mode, "initial_committed_slots": initial,
                  "checkpoint_anchor_sha256": anchor, "fault_boundary": list(pause) if pause else None,
                  "result": result, "process": resource}
        attempts.append(record)
        if not pause:
            check_result(result, m, initial, mode, manifest_path.parent)
            check_state(root/state, identity, entries, expected)
            complete.add(state)
        return record

    # Tests run before timing and are retained as local controls, not attestations.
    for optimized in (False, True):
        args = [sys.executable, "-B"] + (["-O"] if optimized else []) + ["-m", "unittest", "discover", "-s", "tests/cross_language", "-p", "test_solana_incremental_replay.py", "-v"]
        env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
        name = "controls-optimized" if optimized else "controls"
        with (root/f"{name}.stdout.txt").open("xb") as out, (root/f"{name}.stderr.txt").open("xb") as err:
            subprocess.run(args, cwd=ROOT, env=env, stdout=out, stderr=err, check=True, timeout=120)

    clean = []
    for rep in range(plan["clean_repetitions"]):
        record = call(f"clean-{rep}", f"clean-{rep}")
        clean.append(record["name"])
    anchor = attempts[-1]["result"]["checkpoint_sha256"]
    repeat = call("complete-repeat", f"clean-{plan['clean_repetitions']-1}", initial=plan["count"], anchor=anchor)
    if repeat["result"]["work"]["prefix_decode_bytes"] or repeat["result"]["work"]["suffix_decode_bytes"]:
        raise ValueError("complete replay decoded input blocks")
    recoveries = []
    for point in POINTS:
        state = f"boundary-{point}"
        slot = m["end_slot"] if "projection" in point else m["start_slot"]+1
        call(point+"-kill", state, pause=(point, slot))
        initial = parse((root/state/"checkpoint.json").read_bytes())["body"]["next_index"]
        anchor = file_sha(root/state/"checkpoint.json")
        call(point+"-resume", state, initial=initial, anchor=anchor)
        recoveries.append({"point": point, "initial_committed_slots": initial, "complete_output_matches_reference": True})

    curves = []
    for prefix in plan["prefix_slots"]:
        snapshot = f"snapshot-{prefix}"
        call(f"curve-{prefix}-kill", snapshot, pause=("checkpoint_publish", m["start_slot"]+prefix-1))
        anchor = file_sha(root/snapshot/"checkpoint.json")
        if parse((root/snapshot/"checkpoint.json").read_bytes())["body"]["next_index"] != prefix:
            raise ValueError("interruption cursor")
        pairs = []
        for rep in range(plan["paired_repetitions"]):
            order = ("incremental", "full_reproject") if rep % 2 == 0 else ("full_reproject", "incremental")
            measurements = {}
            for mode in order:
                name = f"curve-{prefix}-{rep}-{mode}"
                shutil.copytree(root/snapshot, root/name)
                rec = call(name, name, mode=mode, initial=prefix, anchor=anchor)
                measurements[mode] = {"attempt": name, "wall_seconds": rec["process"]["process_wall_seconds"],
                    "prefix_decode_blocks": len(rec["result"]["work"]["prefix_decoded_slots"]),
                    "suffix_decode_blocks": len(rec["result"]["work"]["suffix_decoded_slots"]),
                    "work": rec["result"]["work"], "resources": rec["process"]}
            pairs.append({"rep": rep, "order": list(order), "measurements": measurements})
        curves.append({"committed_slots": prefix, "checkpoint_anchor_sha256": anchor, "pairs": pairs,
            "median_wall_seconds": {mode: statistics.median(p["measurements"][mode]["wall_seconds"] for p in pairs) for mode in ("incremental", "full_reproject")}})
    if before != bindings() or source_files != {p.name: file_sha(p) for p in sorted(manifest_path.parent.iterdir()) if p.is_file()}:
        raise ValueError("source/code changed during acceptance")
    record = {"schema": "sof-runtime.solana-incremental-acceptance.v1", "status": "PASS_LOCAL_INCREMENTAL_CONTROLS",
        "created_utc": datetime.now(timezone.utc).isoformat(), "implementation_sha256": before, "plan": plan,
        "capture": {"path_local": str(manifest_path), "manifest_sha256": msha, "files": source_files,
                    "server_version": m["server_version"], "coverage": coverage(manifest_path), "independent_finality_verification": False},
        "projection": {"sha256": sha(expected), "bytes": len(expected), "records": sum(len(s["records"]) for s in projected)},
        "environment": {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
                        "logical_cpus": os.cpu_count(), "cargo": subprocess.check_output(["cargo", "--version"], text=True).strip(),
                        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip()},
        "controls": {"ordinary_and_optimized_unittest": "PASS", "separate_python_full_projection": "PASS", "complete_repeat_zero_decode": "PASS"},
        "clean_attempts": clean, "recoveries": recoveries, "recovery_curves": curves, "attempts": attempts,
        "completed_states": sorted(complete), "scope": "LOCAL_BOUNDED_REPLAY_NOT_INDEPENDENT_ATTESTATION",
        "files": {p.relative_to(root).as_posix(): file_sha(p) for p in sorted(root.rglob("*")) if p.is_file()}}
    (root/"acceptance.v1.json").write_bytes(canonical(record))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = run(args.manifest, args.directory)
    print(canonical({"status": result["status"], "coverage": result["capture"]["coverage"],
                     "projection": result["projection"], "curves": [{"prefix": c["committed_slots"], "median_wall_seconds": c["median_wall_seconds"]} for c in result["recovery_curves"]]}).decode())
