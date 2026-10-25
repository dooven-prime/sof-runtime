"""Execute the predeclared attribution schedule; never optimize or extend it."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
from time import perf_counter

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from applications.solana_incremental_replay.reference import load, segments
from applications.solana_incremental_replay.runner import invoke as replay, HERE as REPLAY_HERE
from applications.solana_incremental_replay.validation import expected_entries
from .runner import HERE, ROOT, bindings, build, file_state, invoke, observed_files, warm


def classify(attempts, plan):
    cfg = plan["classification"]
    evidence = []
    for pair in range(plan["pairs"]):
        initial = next(a for a in attempts if a["pair"] == pair and a["state_kind"] == "copied" and a["condition"] == "initial")
        warmed = [a for a in attempts if a["pair"] == pair and a["state_kind"] == "copied" and a["condition"] == "read_warmed"]
        # Both timings cover input hashes plus segment validation on this prefix.
        def costs(a):
            phases = a["result"]["phases"]
            return tuple(sum(phases[p][k] for p in ("raw_input_hash", "segment_validation")) for k in ("wall_seconds", "cpu_seconds"))
        iw, ic = costs(initial)
        ww = statistics.median(costs(a)[0] for a in warmed)
        ratio = iw/max(ic, cfg["cpu_floor_seconds"])
        warm_ratio = iw/max(ww, 1e-9)
        evidence.append({"pair": pair, "initial_copy_wall_seconds": iw, "initial_copy_cpu_seconds": ic,
            "warmed_copy_wall_seconds_median": ww, "wall_cpu_ratio_with_1ms_floor": ratio, "initial_warm_ratio": warm_ratio,
            "non_cpu_and_file_state_sensitive": ratio >= cfg["non_cpu_wall_cpu_ratio_min"] and warm_ratio >= cfg["copy_initial_warm_ratio_min"]})
    votes = sum(e["non_cpu_and_file_state_sensitive"] for e in evidence)
    shares = []
    for a in attempts:
        ps = a["result"]["phases"]
        wall = sum(ps[p]["wall_seconds"] for p in ("raw_input_hash", "segment_validation"))
        cpu = sum(ps[p]["cpu_seconds"] for p in ("raw_input_hash", "segment_validation"))
        shares.append(cpu/max(wall, 1e-9))
    if votes >= cfg["required_pairs"]:
        status = "NON_CPU_FILE_STATE_SENSITIVE_COST"
        action = "STOP_FIXED_CAPTURE_ACCELERATION"
    elif statistics.median(shares) >= cfg["cpu_share_candidate_min"]:
        status = "BOUNDED_CPU_CANDIDATE_ONLY"
        action = "STOP_THIS_EXPERIMENT_NO_TUNING"
    else:
        status = "ATTRIBUTION_UNRESOLVED"
        action = "STOP_NO_AUTOMATIC_EXPANSION"
    return {"classification": status, "action": action, "qualifying_pairs": votes,
            "median_prefix_cpu_share": statistics.median(shares), "evidence": evidence,
            "specific_storage_or_security_mechanism_identified": False}


def run(manifest_path, directory):
    build()
    manifest_path = Path(manifest_path).resolve(strict=True)
    root = Path(directory).resolve(); root.mkdir(parents=True, exist_ok=False)
    (root/"aggregates").mkdir()
    plan = parse((HERE/"plan.v1.json").read_bytes())
    m, msha = load(manifest_path)
    if msha != plan["capture_manifest_sha256"]:
        raise ValueError("not the predeclared capture")
    frozen = parse((REPLAY_HERE/"results/acceptance.v1.json").read_bytes())
    if frozen["implementation_sha256"] != bindings()["frozen_replay"]:
        raise ValueError("frozen replay identity changed")
    before = bindings()
    source_files = {p.name: file_sha(p) for p in sorted(manifest_path.parent.iterdir()) if p.is_file()}
    # Controls run before measuring; no capture or state in a timed pair is used by them.
    for optimized in (False, True):
        args = [sys.executable, "-B"]+(["-O"] if optimized else [])+["-m", "unittest", "discover", "-s", "tests/cross_language", "-p", "test_solana_prefix_integrity.py", "-v"]
        env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
        name = "controls-optimized" if optimized else "controls"
        with (root/f"{name}.stdout.txt").open("xb") as out, (root/f"{name}.stderr.txt").open("xb") as err:
            subprocess.run(args, cwd=ROOT, env=env, stdout=out, stderr=err, check=True, timeout=120)
    prefix = plan["prefix_slots"]
    attempts, preparations = [], []

    def measure(pair, kind, condition, round_index, state, anchor, prewarm=None):
        name = f"pair-{pair}-{kind}-{condition}-{round_index}"
        files = observed_files(manifest_path, state, prefix)
        before_state = {key: file_state(path) for key, path in files.items()}
        result, process = invoke(manifest_path, state, anchor, root/"aggregates"/f"{name}.jsonl", prefix, root/"logs", name,
                                 timeout=plan["process_timeout_seconds"])
        after_state = {key: file_state(path) for key, path in files.items()}
        if result["status"] != "MEASURED_VERIFIED_PREFIX" or result["block_decodes"] or result["new_commits"]:
            raise ValueError(f"probe did not preserve declared work: {result}")
        attempts.append({"name": name, "pair": pair, "state_kind": kind, "state": state.relative_to(root).as_posix(),
            "condition": condition, "round": round_index, "checkpoint_anchor_sha256": anchor, "prewarm": prewarm,
            "file_state_before": before_state, "file_state_after": after_state, "result": result, "process": process})

    for pair, schedule in enumerate(plan["copy_schedules"]):
        fresh, copied = root/f"pair-{pair}-fresh", root/f"pair-{pair}-copied"
        result, process = replay(manifest_path, fresh, root/"logs", f"pair-{pair}-generate",
                                 pause=("checkpoint_publish", m["start_slot"]+prefix-1), forbid_prefix=True)
        anchor = file_sha(fresh/"checkpoint.json")
        if parse((fresh/"checkpoint.json").read_bytes())["body"]["next_index"] != prefix or not process["terminated_at_boundary"]:
            raise ValueError("fresh prefix was not produced at the actual declared boundary")
        prep = {"pair": pair, "schedule": schedule, "generation": {"result": result, "process": process}, "checkpoint_anchor_sha256": anchor}
        if schedule == "fresh_first":
            measure(pair, "fresh", "initial", 0, fresh, anchor)
        start = perf_counter()
        shutil.copytree(fresh, copied)
        prep["copy_wall_seconds_outside_probe"] = perf_counter()-start
        measure(pair, "copied", "initial", 0, copied, anchor)
        if schedule == "copy_first":
            measure(pair, "fresh", "initial", 0, fresh, anchor)
        preparations.append(prep)
        for round_index in range(plan["explicit_read_warm_rounds"]):
            order = (("fresh", fresh), ("copied", copied)) if (pair+round_index) % 2 == 0 else (("copied", copied), ("fresh", fresh))
            for kind, state in order:
                prewarm = warm(observed_files(manifest_path, state, prefix))
                measure(pair, kind, "read_warmed", round_index, state, anchor, prewarm)

    # Whole Python reconstruction and full content scans occur after all timed probes.
    projected = list(segments(manifest_path))
    entries = expected_entries(manifest_path, projected)[:prefix]
    expected = b"".join(s["bytes"] for s in projected[:prefix])
    (root/"reference-prefix.jsonl").write_bytes(expected)
    identity = {"manifest_sha256": msha, "projection": m["projection"], "executable_sha256": before["frozen_replay"]["rust_binary"]}
    expected_body = {"schema": "sof-runtime.solana-checkpoint.v1", "identity": identity, "next_index": prefix, "committed": entries}
    frame = canonical({"body": expected_body, "body_sha256": sha(canonical(expected_body))})
    for attempt in attempts:
        result = attempt["result"]
        state = root/attempt["state"]
        if (state/"checkpoint.json").read_bytes() != frame or (state/"identity.json").read_bytes() != canonical(identity):
            raise ValueError("state changed or does not match full Python reference")
        if (root/"aggregates"/f"{attempt['name']}.jsonl").read_bytes() != expected or result["aggregate_sha256"] != sha(expected):
            raise ValueError("streamed prefix differs from Python")
        for item, segment in zip(entries, projected):
            if (state/f"slot-{item['slot']}.jsonl").read_bytes() != segment["bytes"]:
                raise ValueError("state segment differs from Python")
        ps = result["phases"]
        raw_count = sum((manifest_path.parent/m["rpc"][f"block-{b['slot']}"]["response"]).stat().st_size
                        for b in m["listed_blocks"] if b["slot"] < m["start_slot"]+prefix)
        if ps["raw_input_hash"]["logical_read_bytes"] != raw_count or ps["segment_validation"]["logical_read_bytes"] != len(expected) or ps["aggregate_stream"]["logical_read_bytes"] != len(expected) or ps["aggregate_stream"]["logical_written_bytes"] != len(expected):
            raise ValueError("probe read/write byte accounting")
    if before != bindings() or source_files != {p.name: file_sha(p) for p in sorted(manifest_path.parent.iterdir()) if p.is_file()}:
        raise ValueError("code/capture changed")
    if len(attempts) != plan["pairs"]*2*(1+plan["explicit_read_warm_rounds"]):
        raise ValueError("probe schedule incomplete")
    record = {"schema": "sof-runtime.prefix-integrity-attribution.v1", "status": "PASS_LOCAL_ATTRIBUTION_CONTROLS",
        "created_utc": datetime.now(timezone.utc).isoformat(), "implementation_sha256": before, "plan": plan,
        "capture": {"manifest_sha256": msha, "files": source_files, "path_local": str(manifest_path)},
        "environment": {"platform": platform.platform(), "python": sys.version, "logical_cpus": os.cpu_count(), "cwd": str(ROOT)},
        "prefix": {"slots": prefix, "aggregate_bytes": len(expected), "aggregate_sha256": sha(expected)},
        "preparations": preparations, "attempts": attempts, "disposition": classify(attempts, plan),
        "controls": {"ordinary_and_optimized": "PASS", "full_python_prefix_comparison": "PASS", "state_read_only": "PASS"},
        "scope": "LOCAL_BOUNDED_ATTRIBUTION_NOT_PHYSICAL_DISK_OR_EXECUTION_ATTESTATION",
        "files": {p.relative_to(root).as_posix(): file_sha(p) for p in sorted(root.rglob("*")) if p.is_file()}}
    (root/"attribution.v1.json").write_bytes(canonical(record))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); result = run(args.manifest, args.directory)
    print(canonical({"status": result["status"], "probes": len(result["attempts"]), "disposition": result["disposition"]}).decode())
