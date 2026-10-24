"""Full-carrier cache miss/hit/rejection/rebuild measurements, separately owned."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter

from .benchmark import controlled_environment, machine_identity, parse_sample
from .prepared_cache import CRATE, ROOT, build_cache, cache_binary
from .protocol import canonical_bytes, sha256_file
from .replay import rust_binary


BASELINE = ROOT / "applications/malecns_profile_census/results/full-carrier-somaside.v1"
PLAN = ROOT / "applications/malecns_profile_census/CACHE_BENCHMARK_PLAN_V1.md"


def bindings() -> dict[str, str]:
    names = [
        "applications/malecns_profile_census/PREPARED_INPUT_CACHE_V1.md",
        "applications/malecns_profile_census/CACHE_BENCHMARK_PLAN_V1.md",
        "applications/malecns_profile_census/prepared_cache.py",
        "applications/malecns_profile_census/cache_benchmark.py",
        "applications/malecns_profile_census/prepare_input.py",
        "applications/malecns_profile_census/protocol.py",
        "plugins/rust/prepared-input-cache/src/main.rs",
        "plugins/rust/prepared-input-cache/Cargo.toml",
        "plugins/rust/prepared-input-cache/Cargo.lock",
        "tests/cache_fixture_preparer.py",
        "tests/cross_language/test_prepared_input_cache.py",
    ]
    result = {name: sha256_file(ROOT / name) for name in names}
    result["cache_binary"] = sha256_file(cache_binary())
    result["census_binary"] = sha256_file(rust_binary())
    result["original_baseline_receipt"] = sha256_file(BASELINE / "benchmark.v1.json")
    result["original_semantic_result"] = sha256_file(BASELINE / "semantic-result.json")
    return result


def execute(edges: Path, nodes: Path, output: Path) -> dict:
    started_utc = datetime.now(timezone.utc).isoformat()
    output.mkdir(parents=True, exist_ok=False)
    build_cache()
    before = bindings()
    baseline = json.loads((BASELINE / "benchmark.v1.json").read_text())
    golden = canonical_bytes(json.loads((BASELINE / "semantic-result.json").read_text()))
    if hashlib.sha256(golden).hexdigest() != baseline["semantic_result"]["sha256_canonical_json"]:
        raise ValueError("original semantic-result binding is invalid")
    cache = output / "cache"
    observations = []
    key = None

    def attempt(name: str, expected: str, policy="reject") -> dict:
        nonlocal key
        command = [sys.executable, "-B", "-m", "applications.malecns_profile_census.prepared_cache",
                   "--cache-root", str(cache), "--edges-npz", str(edges), "--nodes-parquet", str(nodes),
                   "--invalid-policy", policy, "--execute"]
        started = perf_counter()
        child = subprocess.run(command, cwd=ROOT, env=controlled_environment(), capture_output=True, timeout=1200)
        process_seconds = perf_counter() - started
        if child.stderr:
            raise ValueError("unexpected cache CLI stderr: " + child.stderr.decode("utf-8"))
        wrapper = json.loads(child.stdout)
        result = wrapper.get("result", wrapper)
        if result["status"] != expected:
            raise ValueError(f"{name}: expected {expected}, received {result}")
        if child.returncode != (2 if expected == "CACHE_INVALID_REJECTED" else 0):
            raise ValueError("status/exit mismatch")
        row = {"scenario": name, "status": expected, "complete_process_wall_seconds": process_seconds,
               **{item: wrapper[item] for item in (
                   "identity_construction_seconds", "cache_process_wall_seconds", "workflow_wall_seconds")}}
        if child.returncode == 0:
            if key is not None and result["key"] != key:
                raise ValueError("identity changed between cache attempts")
            key = result["key"]
            packet = result["packet"]
            if packet["sha256"] != baseline["input"]["sha256"] or packet["size"] != baseline["input"]["size"]:
                raise ValueError("cached packet differs from the unchanged serial baseline")
            consumer = result["consumer"]
            semantic, metrics, digest = parse_sample(
                consumer["stdout"].encode(), consumer["stderr"].encode(), packet["header"], baseline["input"]["known_edges"])
            if canonical_bytes(semantic) != golden:
                raise ValueError("cached execution differs from the original complete semantic result")
            if expected == "CACHE_HIT_VALIDATED" and "preparation_seconds" in result["timings"]:
                raise ValueError("hit silently prepared input again")
            row.update({"key": key, "packet_sha256": packet["sha256"], "timings": result["timings"],
                        "semantic_sha256": digest, "consumer_metrics": metrics,
                        "quarantined_invalid_entry": result["quarantine"] is not None})
        else:
            if result.get("consumer") is not None:
                raise ValueError("rejected cache ran a consumer")
            row["detail"] = result["detail"]
        observations.append(row)
        print(f"{name}: {expected}, {process_seconds:.3f}s", file=sys.stderr, flush=True)
        return result

    first = attempt("first_miss", "CACHE_MISS_PREPARED")
    for index in range(5):
        attempt(f"hit_{index+1}", "CACHE_HIT_VALIDATED")
    packet = (cache / "entries" / key / "packet.bin").resolve(strict=True)
    if not packet.is_relative_to(cache.resolve() / "entries"):
        raise ValueError("refusing to corrupt any file outside this new cache")
    with packet.open("r+b") as handle:
        handle.write(b"X")
        handle.flush()
        os.fsync(handle.fileno())
    attempt("corrupt_default_reject", "CACHE_INVALID_REJECTED")
    attempt("explicit_rebuild", "CACHE_INVALID_REBUILT", policy="rebuild")
    attempt("post_rebuild_hit", "CACHE_HIT_VALIDATED")
    if bindings() != before:
        raise ValueError("baseline, cache sources or executable changed during measurements")
    hits = [row for row in observations if row["scenario"].startswith("hit_")]
    statistics_fields = ("complete_process_wall_seconds", "identity_construction_seconds", "cache_process_wall_seconds")
    summary = {
        field: {"minimum": min(row[field] for row in hits), "median": statistics.median(row[field] for row in hits),
                "maximum": max(row[field] for row in hits)}
        for field in statistics_fields
    }
    for field in first["timings"]:
        values = [row["timings"][field] for row in hits if field in row["timings"]]
        if len(values) == 5:
            summary[field] = {"minimum": min(values), "median": statistics.median(values), "maximum": max(values)}
    result = {
        "schema": "sof-runtime.prepared-input-cache-benchmark.v1", "status": "PASS_CACHE_BASELINE",
        "started_utc": started_utc, "completed_utc": datetime.now(timezone.utc).isoformat(),
        "identity_key": key, "packet": first["packet"], "observations": observations,
        "five_hit_summary": summary, "environment": machine_identity(), "implementation_sha256": before,
        "semantic_sha256": baseline["semantic_result"]["sha256_canonical_json"],
        "original_baseline_unchanged": True, "successful_outputs_match_baseline": 8,
        "claim_boundary": {"scope": "trusted local cache, full somaSide carrier, serial Rust consumer",
                           "old_and_new_execution_obligations_equal": False,
                           "power_loss_or_distributed_guarantee": False, "parallel_scaling_claim": False,
                           "independent_scientific_validation": False, "solana_workload": False,
                           "exclusive_machine_reservation": False, "cold_cache_claim": False},
    }
    (output / "cache-benchmark.v1.json").write_bytes(canonical_bytes(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges-npz", type=Path, required=True)
    parser.add_argument("--nodes-parquet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = execute(args.edges_npz.resolve(strict=True), args.nodes_parquet.resolve(strict=True),
                         args.output_dir.resolve())
        print(json.dumps({"status": result["status"], "five_hit_summary": result["five_hit_summary"]}, indent=2))
        return 0
    except Exception as error:
        print(f"cache-benchmark FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
