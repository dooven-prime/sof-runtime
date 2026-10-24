"""Independent, source-bound comparison of reference and fused packet checks."""
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
import tempfile
from time import perf_counter

import psutil

from .benchmark import controlled_environment, machine_identity, parse_sample
from .cache_benchmark import BASELINE
from .cache_cost_decomposition import old_bindings, new_bindings as cost_bindings
from .prepared_cache import call_cache, cache_key, make_request
from .protocol import canonical_bytes, sha256_file
from .replay import ROOT, find_cargo

HERE = ROOT / "applications/malecns_profile_census"
CRATE = ROOT / "plugins/rust/packet-validation-fusion"


def fusion_binary() -> Path:
    return CRATE / "target/release" / ("packet-validation-fusion.exe" if os.name == "nt" else "packet-validation-fusion")


def build_fusion() -> None:
    subprocess.run([find_cargo(), "build", "--release", "--locked", "--manifest-path", str(CRATE / "Cargo.toml")],
                   cwd=ROOT, check=True)


def historical_bindings() -> dict:
    path = HERE / "results/cache-cost.v1/cost-decomposition.v1.json"
    cost = json.loads(path.read_text())
    old, probe = old_bindings(), cost_bindings()
    if cost["historical_bindings"] != old or cost["implementation_sha256"] != probe:
        raise ValueError("previous cost experiment closure changed")
    return {"old": old, "cost": probe, "cost_receipt_sha256": sha256_file(path)}


def bindings() -> dict:
    names = ["applications/malecns_profile_census/FUSED_VALIDATION_PLAN_V1.md",
             "applications/malecns_profile_census/fused_validation_benchmark.py",
             "plugins/rust/packet-validation-fusion/src/main.rs", "plugins/rust/packet-validation-fusion/build.rs",
             "plugins/rust/packet-validation-fusion/Cargo.toml", "plugins/rust/packet-validation-fusion/Cargo.lock",
             "tests/cross_language/test_fused_packet_validation.py", "tests/cache_fusion_consumer.py"]
    return {**{name: sha256_file(ROOT / name) for name in names}, "fusion_binary": sha256_file(fusion_binary())}


def run_attempt(mode: str, action: str, request_path: Path, timeout=300, rss_limit=4 * 1024**3) -> tuple[dict, dict, int]:
    started = perf_counter()
    child = subprocess.Popen([str(fusion_binary()), mode, action, str(request_path)], cwd=ROOT,
                             env=controlled_environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    root = psutil.Process(child.pid)
    root_rss = tree_rss = observations = 0
    root_os_peak = None
    try:
        while True:
            try:
                memory = root.memory_info()
                root_rss = max(root_rss, memory.rss)
                peak = getattr(memory, "peak_wset", None)
                if peak is not None:
                    root_os_peak = max(root_os_peak or 0, peak)
                current_tree = memory.rss
                for descendant in root.children(recursive=True):
                    try:
                        current_tree += descendant.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
                tree_rss = max(tree_rss, current_tree)
                observations += 1
                if current_tree > rss_limit:
                    raise RuntimeError("observed process-tree RSS limit")
            except psutil.NoSuchProcess:
                pass
            if perf_counter() - started > timeout:
                raise TimeoutError("fusion attempt timed out")
            try:
                stdout, stderr = child.communicate(timeout=0.005)
                break
            except subprocess.TimeoutExpired:
                continue
        elapsed = perf_counter() - started
        if stderr:
            raise ValueError(f"unexpected experiment stderr: {stderr!r}")
        result = json.loads(stdout)
        if result.get("schema") != "sof-runtime.packet-validation-fusion.v1" or result["mode"] != mode or result["action"] != action:
            raise ValueError("wrong experiment envelope")
        return result, {"process_wall_seconds": elapsed, "max_observed_root_rss_bytes": root_rss,
                        "max_observed_root_os_peak_working_set_bytes": root_os_peak,
                        "max_observed_tree_rss_bytes": tree_rss, "memory_observations": observations,
                        "requested_poll_interval_seconds": 0.005}, child.returncode
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate()


def stats(values: list[float]) -> dict:
    return {"minimum": min(values), "median": statistics.median(values), "maximum": max(values)}


def execute(edges: Path, nodes: Path, output: Path) -> dict:
    started_utc = datetime.now(timezone.utc).isoformat()
    output.mkdir(parents=True, exist_ok=False)
    build_fusion()
    old, new = historical_bindings(), bindings()
    baseline = json.loads((BASELINE / "benchmark.v1.json").read_text())
    golden = canonical_bytes(json.loads((BASELINE / "semantic-result.json").read_text()))
    golden_digest = hashlib.sha256(golden).hexdigest()
    if golden_digest != baseline["semantic_result"]["sha256_canonical_json"]:
        raise ValueError("golden binding differs")
    started = perf_counter()
    request = make_request(output / "cache", edges=edges, nodes=nodes, execute=True)
    identity_seconds = perf_counter() - started
    started = perf_counter()
    prepared, _, code = call_cache(request)
    preparation_workflow_seconds = perf_counter() - started
    if code or prepared["status"] != "CACHE_MISS_PREPARED":
        raise ValueError(prepared)
    packet = prepared["packet"]
    if packet["sha256"] != baseline["input"]["sha256"] or packet["size"] != baseline["input"]["size"]:
        raise ValueError("new cache packet differs from frozen baseline")

    def check_semantic(consumer):
        result, metrics, digest = parse_sample(consumer["stdout"].encode(), consumer["stderr"].encode(),
                                               packet["header"], baseline["input"]["known_edges"])
        if canonical_bytes(result) != golden or digest != golden_digest:
            raise ValueError("complete census output differs")
        return metrics

    check_semantic(prepared["consumer"])
    request_path = output / "request.json"
    request_path.write_bytes(canonical_bytes(request))
    request_digest = sha256_file(request_path)
    samples, warmups = [], []

    def attempt(mode, action, pair):
        value, resources, code = run_attempt(mode, action, request_path)
        result = value["result"]
        expected = "CACHE_HIT_VALIDATED" if action == "execute" else "ENTRY_VALIDATED_NOT_CONSUMED"
        if code or result["status"] != expected or result["packet"] != packet:
            raise ValueError(value)
        metrics = check_semantic(result["consumer"]) if action == "execute" else None
        if value["operation_cpu_seconds_excludes_children"] is None:
            raise ValueError("CPU time unavailable on this measurement platform")
        count = 2 if action == "execute" else 1
        if len(value["validation_calls"]) != count or not all(item["accepted"] for item in value["validation_calls"]):
            raise ValueError("validation call coverage differs")
        packet_io = [item for name, item in value["read_io"].items() if Path(name).name == "packet.bin"]
        if len(packet_io) != 1:
            raise ValueError("packet I/O path coverage differs")
        reads = count * (2 if mode == "reference" else 1)
        if packet_io[0]["opens"] != reads or packet_io[0]["bytes"] != reads * packet["size"]:
            raise ValueError("packet read count/bytes differ from expected passes")
        if action == "execute":
            for source in request["identity"]["sources"]:
                path = request["source_paths"][source["role"]]
                io = value["read_io"][path]
                if io["opens"] != 2 or io["bytes"] != 2 * source["size"]:
                    raise ValueError("pre/post source content verification not observed")
            if "final_integrity_source_verification_seconds" not in result["timings"]:
                raise ValueError("missing post-consumption integrity check")
        row = {"pair": pair, "mode": mode, "action": action, **resources,
               "operation_wall_seconds": value["operation_wall_seconds"],
               "operation_cpu_seconds_excludes_children": value["operation_cpu_seconds_excludes_children"],
               "validation_calls": value["validation_calls"], "read_io": value["read_io"],
               "packet_validation_io": packet_io[0], "consumer_logical_packet_passes": int(action == "execute"),
               "consumer_metrics": metrics, "semantic_sha256": golden_digest if metrics else None,
               "cache_timings": result.get("timings")}
        (warmups if pair is None else samples).append(row)
        print(f"{action} {mode} {'warmup' if pair is None else 'pair '+str(pair)}: "
              f"{resources['process_wall_seconds']:.4f}s, CPU {value['operation_cpu_seconds_excludes_children']:.4f}s",
              file=sys.stderr, flush=True)

    for action in ("validate", "execute"):
        for mode in ("reference", "fused"):
            attempt(mode, action, None)
        for pair in range(1, 6):
            order = ("reference", "fused") if pair % 2 else ("fused", "reference")
            for mode in order:
                attempt(mode, action, pair)

    if historical_bindings() != old or bindings() != new or sha256_file(request_path) != request_digest:
        raise ValueError("historical/new implementation or request changed during measurement")
    if sha256_file(Path(prepared["packet_path"])) != packet["sha256"]:
        raise ValueError("packet changed during measurement")
    summaries = {}
    for action in ("validate", "execute"):
        summaries[action] = {}
        for mode in ("reference", "fused"):
            rows = [row for row in samples if row["action"] == action and row["mode"] == mode]
            fields = ("process_wall_seconds", "operation_cpu_seconds_excludes_children", "operation_wall_seconds",
                      "max_observed_root_rss_bytes", "max_observed_tree_rss_bytes")
            summaries[action][mode] = {field: stats([row[field] for row in rows]) for field in fields}
            summaries[action][mode]["maximum_observed_root_os_peak_working_set_bytes"] = max(
                row["max_observed_root_os_peak_working_set_bytes"] for row in rows)
            summaries[action][mode]["packet_validation_opens_each"] = sorted({row["packet_validation_io"]["opens"] for row in rows})
            summaries[action][mode]["packet_validation_bytes_each"] = sorted({row["packet_validation_io"]["bytes"] for row in rows})
    receipt = {"schema": "sof-runtime.fused-packet-validation-benchmark.v1", "status": "PASS_FUSION_COMPARISON",
               "started_utc": started_utc, "completed_utc": datetime.now(timezone.utc).isoformat(),
               "identity_key": cache_key(request["identity"]), "request_sha256": request_digest,
               "packet": packet, "semantic_sha256": golden_digest, "complete_output_comparisons": 13,
               "identity_admission_seconds": identity_seconds,
               "untimed_setup_workflow_measured_separately_seconds": preparation_workflow_seconds,
               "setup_cache_timings": prepared["timings"], "warmups": warmups, "samples": samples,
               "summary": summaries, "historical_bindings": old, "implementation_sha256": new,
               "environment": machine_identity(), "boundary": {
                   "historical_closures_unchanged": True, "same_default_parse_buffer": True,
                   "pre_post_source_checks": True, "post_consumption_packet_check": True,
                   "validation_credentials": False, "worker": False, "cold_io_claim": False,
                   "physical_io_measurement": False, "cpu_includes_census_child": False,
                   "memory_tree_sampled": True, "exclusive_machine": False, "solana_workload": False}}
    (output / "fusion-benchmark.v1.json").write_bytes(canonical_bytes(receipt) + b"\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges-npz", type=Path, required=True)
    parser.add_argument("--nodes-parquet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = execute(args.edges_npz.resolve(strict=True), args.nodes_parquet.resolve(strict=True), args.output_dir.resolve())
        print(json.dumps({"status": result["status"], "summary": result["summary"]}, indent=2))
        return 0
    except Exception as error:
        print(f"fused validation FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
