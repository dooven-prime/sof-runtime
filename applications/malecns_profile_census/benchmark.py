"""Serial full-carrier parity and cache-warm fresh-process measurements."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

import psutil

from .prepare_input import PUBLISHED_CARRIER
from .protocol import canonical_bytes, read_header, sha256_file
from .replay import CRATE, ROOT, find_cargo, find_rustc, rust_binary


PLAN = ROOT / "applications/malecns_profile_census/BENCHMARK_PLAN.md"
PHASES = (
    "header_decode_seconds", "stream_decode_validate_aggregate_seconds",
    "classify_report_seconds", "serialize_seconds",
)
MEASURED_PAIRS = 5


def controlled_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONOPTIMIZE", None)
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key in (
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "RAYON_NUM_THREADS",
    ):
        env[key] = "1"
    return env


def run_child(
    command: list[str], *, timeout: float = 300, rss_limit: int = 4 * 1024**3,
) -> tuple[bytes, bytes, dict]:
    started = time.perf_counter()
    child = subprocess.Popen(
        command, cwd=ROOT, env=controlled_environment(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    observed_rss = 0
    observed_os_peak = None
    observations = 0
    try:
        process = psutil.Process(child.pid)
        while True:
            try:
                info = process.memory_info()
                observed_rss = max(observed_rss, info.rss)
                peak = getattr(info, "peak_wset", None)
                if peak is not None:
                    observed_os_peak = max(observed_os_peak or 0, peak)
                observations += 1
                if info.rss > rss_limit:
                    raise RuntimeError("child observed-RSS limit exceeded")
            except psutil.NoSuchProcess:
                pass
            if time.perf_counter() - started > timeout:
                raise TimeoutError("child wall-time limit exceeded")
            try:
                stdout, stderr = child.communicate(timeout=0.01)
                break
            except subprocess.TimeoutExpired:
                continue
        elapsed = time.perf_counter() - started
        if child.returncode:
            raise RuntimeError(
                f"child exited {child.returncode}: {stderr.decode('utf-8', errors='replace')}"
            )
        return stdout, stderr, {
            "process_wall_seconds": elapsed,
            "max_observed_rss_bytes": observed_rss,
            "max_observed_os_peak_working_set_bytes": observed_os_peak,
            "memory_observations": observations,
            "memory_poll_interval_seconds": 0.01,
        }
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate()


def parse_sample(stdout: bytes, stderr: bytes, header: dict, edge_count: int) -> tuple[dict, dict, str]:
    result = json.loads(stdout)
    lines = stderr.decode("utf-8").splitlines()
    prefix = "SOF_PROFILE_METRICS "
    if len(lines) != 1 or not lines[0].startswith(prefix):
        raise ValueError("missing or unexpected worker diagnostics")
    metrics = json.loads(lines[0][len(prefix):])
    if set(metrics) != {*PHASES, "record_count", "edge_count"}:
        raise ValueError("unexpected worker metric fields")
    if any(type(metrics[key]) not in (int, float) or not math.isfinite(metrics[key])
           or metrics[key] < 0 for key in PHASES):
        raise ValueError("invalid worker duration")
    if metrics["record_count"] != header["record_count"] or metrics["edge_count"] != edge_count:
        raise ValueError("worker did not consume the complete declared domain")
    if result["status"] != "EXACT_CENSUS" or result["eligible_sources"] != header["record_count"]:
        raise ValueError("incomplete census result")
    for key in ("source_field", "source_identity", "sign_semantics", "sector_labels", "source_artifacts"):
        if result[key] != header[key]:
            raise ValueError(f"result/header mismatch: {key}")
    digest = hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result, metrics, digest


def summarize(samples: list[dict]) -> dict:
    summary = {}
    for implementation in ("python", "rust"):
        rows = [row for row in samples if row["implementation"] == implementation]
        if not rows:
            raise ValueError("missing implementation samples")
        fields = ("process_wall_seconds", *PHASES, "max_observed_rss_bytes")
        values = {
            key: {
                "minimum": min(row[key] for row in rows),
                "median": statistics.median(row[key] for row in rows),
                "maximum": max(row[key] for row in rows),
            }
            for key in fields
        }
        peaks = [row["max_observed_os_peak_working_set_bytes"] for row in rows]
        values["maximum_observed_os_peak_working_set_bytes"] = (
            max(peaks) if all(value is not None for value in peaks) else None
        )
        values["measured_processes"] = len(rows)
        summary[implementation] = values
    summary["python_over_rust_median_process_wall_ratio"] = (
        summary["python"]["process_wall_seconds"]["median"]
        / summary["rust"]["process_wall_seconds"]["median"]
    )
    return summary


def implementation_binding() -> dict[str, str]:
    relative = [
        "applications/malecns_profile_census/benchmark.py",
        "applications/malecns_profile_census/BENCHMARK_PLAN.md",
        "applications/malecns_profile_census/prepare_input.py",
        "applications/malecns_profile_census/protocol.py",
        "applications/malecns_profile_census/oracle.py",
        "applications/malecns_profile_census/replay.py",
        "tests/cross_language/test_malecns_profile_census.py",
        "tests/cross_language/test_malecns_profile_benchmark.py",
        "plugins/rust/malecns-profile-census/src/main.rs",
        "plugins/rust/malecns-profile-census/Cargo.toml",
        "plugins/rust/malecns-profile-census/Cargo.lock",
    ]
    binding = {name: sha256_file(ROOT / name) for name in relative}
    binding["rust_binary"] = sha256_file(rust_binary())
    binding["python_executable"] = sha256_file(sys.executable)
    return binding


def machine_identity() -> dict:
    cpu_name = platform.processor()
    if sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    memory = psutil.virtual_memory()
    process = psutil.Process()
    dependencies = {
        name: importlib.metadata.version(name)
        for name in ("numpy", "pandas", "scipy", "pyarrow", "psutil")
    }
    return {
        "platform": platform.platform(), "machine": platform.machine(),
        "cpu": cpu_name, "logical_cpus": psutil.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False),
        "controller_cpu_affinity": process.cpu_affinity() if hasattr(process, "cpu_affinity") else None,
        "memory_total_bytes": memory.total, "memory_available_at_start_bytes": memory.available,
        "python": platform.python_version(), "dependencies": dependencies,
        "rustc": subprocess.check_output([find_rustc(), "--version", "--verbose"], text=True).strip(),
        "cargo": subprocess.check_output([find_cargo(), "--version"], text=True).strip(),
        "exclusive_machine_reservation": False,
    }


def execute(edges: Path, nodes: Path, output: Path) -> dict:
    started_utc = datetime.now(timezone.utc).isoformat()
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run(
        [find_cargo(), "build", "--release", "--locked", "--manifest-path", str(CRATE / "Cargo.toml")],
        cwd=ROOT, check=True,
    )
    binding = implementation_binding()
    environment = machine_identity()
    source_files = {"edges": edges, "nodes": nodes}
    for role, path in source_files.items():
        expected = PUBLISHED_CARRIER[role]
        if path.stat().st_size != expected["size"] or sha256_file(path) != expected["sha256"]:
            raise ValueError(f"{role} source does not match the release anchor")

    packet = output / "somaside.input.bin"
    print("Preparing complete release-anchored carrier packet", file=sys.stderr, flush=True)
    stdout, stderr, preparation = run_child([
        sys.executable, "-B", "-m", "applications.malecns_profile_census.prepare_input",
        "--edges-npz", str(edges), "--nodes-parquet", str(nodes),
        "--field", "somaSide", "--output", str(packet),
    ], timeout=600, rss_limit=12 * 1024**3)
    if stderr:
        raise ValueError("unexpected preparation diagnostics: " + stderr.decode("utf-8"))
    prepared = json.loads(stdout)
    packet_digest = sha256_file(packet)
    if prepared["status"] != "INPUT_PREPARED" or prepared["sha256"] != packet_digest:
        raise ValueError("preparation receipt mismatch")
    with packet.open("rb") as stream:
        header = read_header(stream)
    expected_sources = PUBLISHED_CARRIER["eligible_source_count"]
    if header["record_count"] != expected_sources or header["source_field"] != "somaSide":
        raise ValueError("unexpected full-carrier packet scope")
    if header["source_identity"] != "paper16-carrier-index.v1":
        raise ValueError("not the declared carrier basis")
    expected_refs = [
        {"role": role, "name": path.name, "size": path.stat().st_size, "sha256": sha256_file(path)}
        for role, path in (("CARRIER_EDGES", edges), ("CARRIER_NODES", nodes))
    ]
    if header["source_artifacts"] != expected_refs:
        raise ValueError("packet does not bind both complete source artifacts")

    commands = {
        "python": [sys.executable, "-B", "-m", "applications.malecns_profile_census.oracle", str(packet), "--metrics"],
        "rust": [str(rust_binary()), str(packet), "--metrics"],
    }
    reference_bytes = None
    warmups, samples = [], []

    def attempt(implementation: str, pair: int | None) -> dict:
        nonlocal reference_bytes
        # This binding read also defines the cache-warming operation, outside timing.
        if sha256_file(packet) != packet_digest:
            raise ValueError("packet changed before child execution")
        stdout, stderr, observed = run_child(commands[implementation])
        result, metrics, digest = parse_sample(stdout, stderr, header, PUBLISHED_CARRIER["known_edge_count"])
        encoded = canonical_bytes(result)
        if reference_bytes is None:
            reference_bytes = encoded
            (output / "semantic-result.json").write_bytes(encoded + b"\n")
        elif encoded != reference_bytes:
            raise ValueError("complete Python/Rust semantic outputs differ")
        row = {"implementation": implementation, "pair": pair, **observed, **metrics,
               "semantic_result_sha256": digest}
        print(f"{implementation} {'warmup' if pair is None else 'pair '+str(pair)}: "
              f"{observed['process_wall_seconds']:.3f}s, exact output PASS", file=sys.stderr, flush=True)
        return row

    for implementation in ("python", "rust"):
        warmups.append(attempt(implementation, None))
    for pair in range(MEASURED_PAIRS):
        order = ("python", "rust") if pair % 2 == 0 else ("rust", "python")
        for implementation in order:
            samples.append(attempt(implementation, pair + 1))

    if sha256_file(packet) != packet_digest or implementation_binding() != binding:
        raise ValueError("input or implementation bytes changed during the benchmark")
    for role, path in source_files.items():
        if sha256_file(path) != PUBLISHED_CARRIER[role]["sha256"]:
            raise ValueError("upstream source changed during the benchmark")
    semantic = json.loads(reference_bytes)
    result = {
        "schema": "sof-runtime.malecns-profile-census-benchmark.v1",
        "status": "PASS_EXACT_BENCHMARK",
        "protocol": "malecns-profile-census-baseline.v1",
        "started_utc": started_utc,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "input": {"name": packet.name, "size": packet.stat().st_size, "sha256": packet_digest,
                  "source_artifacts": expected_refs, "source_field": "somaSide",
                  "node_count": PUBLISHED_CARRIER["node_count"], "eligible_sources": expected_sources,
                  "known_edges": PUBLISHED_CARRIER["known_edge_count"], "unchanged_after_run": True},
        "semantic_result": {"file": "semantic-result.json",
                            "sha256_canonical_json": hashlib.sha256(reference_bytes).hexdigest(),
                            "profile_classes": semantic["profile_classes"],
                            "profile_classes_sha256": semantic["profile_classes_sha256"],
                            "all_12_outputs_canonical_equal": True},
        "preparation": preparation, "warmups_excluded": warmups, "samples": samples,
        "summary": summarize(samples), "environment": environment,
        "execution_policy": {
            "native_thread_environment": {key: value for key, value in controlled_environment().items()
                                          if key.endswith("NUM_THREADS") or key in ("PYTHONHASHSEED", "VECLIB_MAXIMUM_THREADS")},
            "cache": "packet read/hash before each child, outside process interval; no cache eviction",
            "mode": "serial fresh-process streaming; no persistent worker or decoded-data residency",
            "measured_pairs": MEASURED_PAIRS, "warmups_per_implementation": 1,
            "child_timeout_seconds": 300, "child_observed_rss_limit_bytes": 4 * 1024**3,
            "preparation_timeout_seconds": 600, "preparation_observed_rss_limit_bytes": 12 * 1024**3,
            "limits_are_cooperative": True,
        },
        "implementation_sha256": binding,
        "claim_boundary": {
            "local_exact_implementation_parity": True,
            "performance_scope": "recorded serial streaming implementations, packet and shared machine only",
            "independent_scientific_validation": False, "paper_claim_admission": False,
            "solana_workload": False, "parallel_scaling": False, "distributed_execution": False,
            "cold_cache_claim": False, "compute_only_kernel_claim": False,
            "p99_or_significance_claim": False, "production_slo_claim": False,
        },
    }
    (output / "benchmark.v1.json").write_bytes(canonical_bytes(result) + b"\n")
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
        print(json.dumps({"status": result["status"], "summary": result["summary"]}, indent=2))
        return 0
    except Exception as error:
        print(f"profile-census-benchmark FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
