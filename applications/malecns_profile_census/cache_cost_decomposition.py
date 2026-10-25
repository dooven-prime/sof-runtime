"""Read-only v1 cost probes and bounded worker comparison; no validation reuse."""
from __future__ import annotations

import argparse
import builtins
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import queue
import statistics
import subprocess
import sys
import tempfile
import threading
from time import perf_counter

from . import prepared_cache
from .benchmark import controlled_environment, implementation_binding, machine_identity, parse_sample
from .cache_benchmark import BASELINE, bindings as cache_bindings
from .protocol import canonical_bytes, sha256_file
from .replay import ROOT, find_cargo

SCHEMA = "sof-runtime.cache-cost-probe.v1"
CRATE = ROOT / "plugins/rust/cache-cost-probe"
HERE = ROOT / "applications/malecns_profile_census"


def probe_binary() -> Path:
    return CRATE / "target/release" / ("cache-cost-probe.exe" if os.name == "nt" else "cache-cost-probe")


def build_probe() -> None:
    subprocess.run([find_cargo(), "build", "--release", "--locked", "--manifest-path", str(CRATE / "Cargo.toml")],
                   cwd=ROOT, check=True)


def envelope(action: str, request: dict | None, ident: int = 0) -> dict:
    return {"schema": SCHEMA, "id": ident, "action": action, "request": request}


def check_session_environment(request: dict) -> None:
    """Reusing intent is not permission to silently select a new Python runtime."""
    runtime = request["identity"]["preparer"]["runtime"]
    if runtime["python"] != platform.python_version():
        raise ValueError("session Python version changed; construct a new request")
    for name, version in runtime["dependencies"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f"session dependency changed: {name}; construct a new request")


class Worker:
    """Single caller, bounded session; every execute invokes the unchanged v1 code."""

    def __init__(self, timeout: float = 1000):
        self.timeout, self.ident = timeout, 0
        started = perf_counter()
        self.process = subprocess.Popen([str(probe_binary())], cwd=ROOT, env=controlled_environment(),
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.lines = queue.Queue()
        self.errors = bytearray()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.error_reader = threading.Thread(target=self._read_errors, daemon=True)
        self.reader.start()
        self.error_reader.start()
        try:
            ready = self._receive()
            if (ready.get("schema") != SCHEMA or ready.get("status") != "READY"
                    or ready.get("retained_validation_credentials") is not False
                    or ready.get("max_requests") != 64):
                raise ValueError("invalid worker readiness")
            self.ready = ready
            self.startup_seconds = perf_counter() - started
        except BaseException:
            self.close(abort=True)
            raise

    def _read(self):
        try:
            while raw := self.process.stdout.readline(1_000_001):
                self.lines.put(raw)
                if len(raw) > 1_000_000:
                    break
        finally:
            self.lines.put(None)

    def _read_errors(self):
        while chunk := self.process.stderr.read(8192):
            if len(self.errors) < 1_000_000:
                self.errors.extend(chunk[:1_000_000 - len(self.errors)])

    def _receive(self) -> dict:
        try:
            raw = self.lines.get(timeout=self.timeout)
        except queue.Empty as error:
            raise TimeoutError("worker response timed out") from error
        if raw is None or len(raw) > 1_000_000 or not raw.endswith(b"\n"):
            raise ValueError("worker exited or returned invalid framing")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("worker response is not an object")
        return result

    def call(self, action: str, request: dict | None = None) -> tuple[dict, float]:
        if self.ident >= 64:
            raise ValueError("worker session exhausted; restart explicitly")
        started = perf_counter()
        raw = canonical_bytes(envelope(action, request, self.ident)) + b"\n"
        if len(raw) > 1_000_000:
            raise ValueError("request frame exceeds 1 MB")
        try:
            self.process.stdin.write(raw)
            self.process.stdin.flush()
            result = self._receive()
            if result.get("schema") != SCHEMA or result.get("id") != self.ident:
                raise ValueError("worker response identity mismatch")
            self.ident += 1
            return result, perf_counter() - started
        except BaseException:
            self.close(abort=True)
            raise

    def close(self, *, abort=False):
        close_error = None
        if not self.process.stdin.closed:
            try:
                self.process.stdin.close()
            except OSError as error:
                close_error = str(error)
        if abort and self.process.poll() is None:
            self.process.kill()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            close_error = "worker did not exit at EOF; killed and reaped"
        self.reader.join(timeout=5)
        self.error_reader.join(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        if not abort and (close_error or self.process.returncode != 0 or self.errors):
            raise ValueError(f"worker shutdown failed: {close_error}, {self.process.returncode}, {bytes(self.errors)!r}")

    def __enter__(self):
        return self

    def __exit__(self, kind, value, trace):
        self.close(abort=kind is not None)


def profiled_identity(cache: Path, edges: Path, nodes: Path) -> dict:
    """Transparent single-thread instrumentation of the frozen request factory."""
    hashes, versions, events = [], [], []
    original_hash = prepared_cache.sha256_file
    original_version = importlib.metadata.version
    original_import = builtins.__import__
    parquet_module, original_table = None, None
    in_import = False

    def timed_hash(path):
        started = perf_counter()
        digest = original_hash(path)
        hashes.append({"path": str(path), "bytes": Path(path).stat().st_size,
                       "seconds": perf_counter() - started, "sha256": digest})
        return digest

    def timed_version(name):
        started = perf_counter()
        result = original_version(name)
        versions.append({"name": name, "seconds": perf_counter() - started})
        return result

    def timed_import(name, *args, **kwargs):
        nonlocal parquet_module, original_table, in_import
        if name != "pyarrow.parquet" or in_import:
            return original_import(name, *args, **kwargs)
        in_import = True
        started = perf_counter()
        try:
            module = original_import(name, *args, **kwargs)
        finally:
            in_import = False
        events.append({"phase": "pyarrow_import", "seconds": perf_counter() - started})
        parquet_module = sys.modules["pyarrow.parquet"]
        original_table = parquet_module.read_table

        def timed_table(*arguments, **options):
            started = perf_counter()
            result = original_table(*arguments, **options)
            events.append({"phase": "parquet_read_table", "seconds": perf_counter() - started})
            return result

        parquet_module.read_table = timed_table
        return module

    prepared_cache.sha256_file = timed_hash
    importlib.metadata.version = timed_version
    builtins.__import__ = timed_import
    started = perf_counter()
    try:
        request = prepared_cache.make_request(cache, edges=edges, nodes=nodes, execute=True)
        elapsed = perf_counter() - started
    finally:
        prepared_cache.sha256_file = original_hash
        importlib.metadata.version = original_version
        builtins.__import__ = original_import
        if parquet_module is not None:
            parquet_module.read_table = original_table
    measured = sum(row["seconds"] for row in hashes + versions + events)
    if measured > elapsed + 0.00001:
        raise ValueError("instrumentation spans overlap")
    return {"identity_construction_seconds": elapsed, "hashes": hashes, "versions": versions,
            "events": events, "unassigned_conversion_normalization_and_other_seconds": elapsed - measured,
            "request": request}


def old_bindings() -> dict:
    serial = json.loads((BASELINE / "benchmark.v1.json").read_text())
    cache_path = HERE / "results/prepared-cache.v1/cache-benchmark.v1.json"
    cache = json.loads(cache_path.read_text())
    current_serial, current_cache = implementation_binding(), cache_bindings()
    if serial["implementation_sha256"] != current_serial or cache["implementation_sha256"] != current_cache:
        raise ValueError("historical source/binary closure no longer matches")
    return {"serial": current_serial, "cache": current_cache,
            "cache_receipt_sha256": sha256_file(cache_path)}


def new_bindings() -> dict:
    names = ["applications/malecns_profile_census/CACHE_COST_PLAN_V1.md",
             "applications/malecns_profile_census/cache_cost_decomposition.py",
             "plugins/rust/cache-cost-probe/src/main.rs", "plugins/rust/cache-cost-probe/Cargo.toml",
             "plugins/rust/cache-cost-probe/Cargo.lock", "tests/cross_language/test_cache_cost_decomposition.py"]
    return {**{name: sha256_file(ROOT / name) for name in names},
            "probe_binary": sha256_file(probe_binary()), "python_executable": sha256_file(sys.executable)}


def summary(values: list[float]) -> dict:
    return {"minimum": min(values), "median": statistics.median(values), "maximum": max(values)}


def session_batch(cache: Path, edges: Path, nodes: Path, mode: str) -> dict:
    started = perf_counter()
    request = prepared_cache.make_request(cache, edges=edges, nodes=nodes, execute=True)
    admission = perf_counter() - started
    worker = Worker() if mode == "fixed_request_worker" else None
    calls = []
    try:
        for _ in range(5):
            call_started = perf_counter()
            check_session_environment(request)
            if worker is None:
                result, _, code = prepared_cache.call_cache(request)
                if code:
                    raise ValueError(result)
            else:
                value, _ = worker.call("execute", request)
                result = value["result"]
            if result["status"] != "CACHE_HIT_VALIDATED":
                raise ValueError(result)
            calls.append({"result": result, "wall_seconds": perf_counter() - call_started})
    except BaseException:
        if worker is not None:
            worker.close(abort=True)
        raise
    if worker is not None:
        worker.close()
    return {"calls": calls, "whole_session_wall_seconds": perf_counter() - started,
            "identity_construction_seconds": admission,
            "worker_startup_seconds": worker.startup_seconds if worker is not None else None}


def execute(edges: Path, nodes: Path, output: Path) -> dict:
    started_utc = datetime.now(timezone.utc).isoformat()
    output.mkdir(parents=True, exist_ok=False)
    build_probe()
    old, new = old_bindings(), new_bindings()
    baseline = json.loads((BASELINE / "benchmark.v1.json").read_text())
    golden = canonical_bytes(json.loads((BASELINE / "semantic-result.json").read_text()))
    digest = hashlib.sha256(golden).hexdigest()
    if digest != baseline["semantic_result"]["sha256_canonical_json"]:
        raise ValueError("invalid golden output")
    cache = output / "cache"
    observations, rounds, batches = [], [], []
    key = None

    def record(name, mode, result, wall, **extra):
        nonlocal key
        if result["status"] not in ("CACHE_MISS_PREPARED", "CACHE_HIT_VALIDATED"):
            raise ValueError(result)
        if (key is not None and key != result["key"]) or (name != "first_miss" and result["status"] != "CACHE_HIT_VALIDATED"):
            raise ValueError("unexpected key/status")
        key = result["key"]
        packet = result["packet"]
        if packet["sha256"] != baseline["input"]["sha256"] or packet["size"] != baseline["input"]["size"]:
            raise ValueError("packet changed from serial baseline")
        semantic, metrics, semantic_digest = parse_sample(result["consumer"]["stdout"].encode(),
            result["consumer"]["stderr"].encode(), packet["header"], baseline["input"]["known_edges"])
        if canonical_bytes(semantic) != golden or semantic_digest != digest:
            raise ValueError("complete semantic result differs")
        row = {"name": name, "mode": mode, "wall_seconds": wall, "status": result["status"],
               "timings": result["timings"], "semantic_sha256": semantic_digest,
               "consumer_metrics": metrics, **extra}
        observations.append(row)
        print(f"{name}: {mode} {wall:.4f}s", file=sys.stderr, flush=True)
        return row

    def cli(name):
        command = [sys.executable, "-B", "-m", "applications.malecns_profile_census.prepared_cache",
                   "--cache-root", str(cache), "--edges-npz", str(edges), "--nodes-parquet", str(nodes), "--execute"]
        started = perf_counter()
        child = subprocess.run(command, cwd=ROOT, env=controlled_environment(), capture_output=True, timeout=1200)
        wall = perf_counter() - started
        if child.returncode or child.stderr:
            raise ValueError(f"fresh CLI failed: {child.stdout!r} {child.stderr!r}")
        value = json.loads(child.stdout)
        return record(name, "fresh_python_cli", value["result"], wall,
                      identity_construction_seconds=value["identity_construction_seconds"],
                      cache_process_wall_seconds=value["cache_process_wall_seconds"],
                      workflow_wall_seconds=value["workflow_wall_seconds"])

    cli("first_miss")
    started = perf_counter()
    request = prepared_cache.make_request(cache, edges=edges, nodes=nodes, execute=True)
    admission_seconds = perf_counter() - started
    request_digest = hashlib.sha256(canonical_bytes(request)).hexdigest()
    if prepared_cache.cache_key(request["identity"]) != key:
        raise ValueError("fixed request changed identity")

    with Worker() as worker:
        def fixed(name, mode):
            started = perf_counter()
            check_session_environment(request)
            environment_seconds = perf_counter() - started
            if mode == "fixed_request_fresh_rust":
                value, ipc_seconds, code = prepared_cache.call_cache(request)
                if code:
                    raise ValueError(value)
                extra = {}
            else:
                wrapper, ipc_seconds = worker.call("execute", request)
                value = wrapper["result"]
                extra = {"worker_dispatch_seconds": wrapper["dispatch_seconds"]}
            wall = perf_counter() - started
            return record(name, mode, value, wall, environment_check_seconds=environment_seconds,
                          ipc_seconds=ipc_seconds, **extra)

        fixed("worker_first_hit", "fixed_request_worker")
        cli("excluded_cli_warmup")
        modes = ["fresh_python_cli", "fixed_request_fresh_rust", "fixed_request_worker"]
        for index in range(5):
            order = modes[index % 3:] + modes[:index % 3]
            started = perf_counter()
            for mode in order:
                name = f"round_{index + 1}"
                cli(name) if mode == modes[0] else fixed(name, mode)
            rounds.append({"round": index + 1, "order": order, "whole_round_wall_seconds": perf_counter() - started})
        for mode in modes[1:]:
            started = perf_counter()
            for index in range(5):
                fixed(f"batch_{index + 1}", mode)
            batches.append({"mode": mode, "calls": 5, "whole_batch_wall_seconds": perf_counter() - started,
                            "includes_output_checks": True, "includes_admission_or_startup": False})
        probes, worker_pings, fresh_pings = [], [], []
        for _ in range(5):
            value, wall = worker.call("probe", request)
            if value["result"]["status"] != "PROBED_NOT_CONSUMED" or value["result"]["key"] != key:
                raise ValueError(value)
            if value["result"]["packet"]["sha256"] != baseline["input"]["sha256"]:
                raise ValueError("probe packet differs")
            probes.append({**value["result"], "whole_probe_ipc_seconds": wall})
            pong, elapsed = worker.call("ping")
            if pong["result"]["status"] != "PONG":
                raise ValueError("invalid pong")
            worker_pings.append(elapsed)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ping.json"
            path.write_bytes(canonical_bytes(envelope("ping", None)))
            for _ in range(5):
                started = perf_counter()
                child = subprocess.run([str(probe_binary()), "--once", str(path)], cwd=ROOT,
                    env=controlled_environment(), capture_output=True, timeout=30)
                elapsed = perf_counter() - started
                if child.returncode or child.stderr or json.loads(child.stdout)["result"]["status"] != "PONG":
                    raise ValueError("fresh ping failed")
                fresh_pings.append(elapsed)
        worker_startup = worker.startup_seconds

    end_to_end_batches = []
    for mode in modes[1:]:
        started = perf_counter()
        child = subprocess.run([sys.executable, "-B", "-m", "applications.malecns_profile_census.cache_cost_decomposition",
                                "--session-batch", mode, "--cache-root", str(cache),
                                "--edges-npz", str(edges), "--nodes-parquet", str(nodes)], cwd=ROOT,
                               env=controlled_environment(), capture_output=True, timeout=1200)
        wall = perf_counter() - started
        if child.returncode or child.stderr:
            raise ValueError(f"end-to-end batch failed: {child.stdout!r} {child.stderr!r}")
        value = json.loads(child.stdout)
        calls = value.pop("calls")
        if len(calls) != 5:
            raise ValueError("end-to-end batch call count")
        for index, call in enumerate(calls):
            record(f"end_to_end_{index + 1}", mode, call["result"], call["wall_seconds"])
        end_to_end_batches.append({"mode": mode, "calls": 5, **value,
                                  "whole_fresh_python_process_wall_seconds": wall,
                                  "includes_admission_startup_shutdown": True,
                                  "includes_outer_golden_comparison": False})
    profiles = []
    for _ in range(3):
        started = perf_counter()
        child = subprocess.run([sys.executable, "-B", "-m", "applications.malecns_profile_census.cache_cost_decomposition",
                                "--identity-profile", "--cache-root", str(cache),
                                "--edges-npz", str(edges), "--nodes-parquet", str(nodes)], cwd=ROOT,
                               env=controlled_environment(), capture_output=True, timeout=60)
        wall = perf_counter() - started
        if child.returncode or child.stderr:
            raise ValueError(f"identity probe failed: {child.stdout!r} {child.stderr!r}")
        profile = json.loads(child.stdout)
        if canonical_bytes(profile.pop("request")) != canonical_bytes(request):
            raise ValueError("instrumented factory changed request")
        profiles.append({**profile, "whole_fresh_process_wall_seconds": wall})
    if old_bindings() != old or new_bindings() != new:
        raise ValueError("historical or new closure changed during measurements")
    if hashlib.sha256(canonical_bytes(request)).hexdigest() != request_digest:
        raise ValueError("fixed request mutated")
    mode_summary = {mode: summary([row["wall_seconds"] for row in observations
                    if row["name"].startswith("round_") and row["mode"] == mode]) for mode in modes}
    result = {"schema": "sof-runtime.cache-hit-cost-decomposition.v1", "status": "PASS_COST_DECOMPOSITION",
              "started_utc": started_utc, "completed_utc": datetime.now(timezone.utc).isoformat(),
              "identity_key": key, "fixed_request_sha256": request_digest, "semantic_sha256": digest,
              "successful_complete_output_comparisons": len(observations), "observations": observations,
              "five_round_hit_summary": mode_summary, "rounds": rounds, "consecutive_batches": batches,
              "end_to_end_batches": end_to_end_batches,
              "fixed_request_admission_seconds": admission_seconds, "worker_startup_to_ready_seconds": worker_startup,
              "identity_profiles": profiles, "isolated_verification_probes": probes,
              "noop_seconds": {"fresh_process": fresh_pings, "worker": worker_pings},
              "historical_bindings": old, "implementation_sha256": new, "environment": machine_identity(),
              "boundary": {"historical_closures_unchanged": True, "all_v1_execute_checks_retained": True,
                           "cached_validation_credentials": False, "resident_census_kernel": False,
                           "cold_filesystem_cache": False, "exclusive_machine": False,
                           "production_worker": False, "solana_workload": False,
                           "independent_scientific_validation": False}}
    (output / "cost-decomposition.v1.json").write_bytes(canonical_bytes(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges-npz", type=Path, required=True)
    parser.add_argument("--nodes-parquet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--identity-profile", action="store_true")
    parser.add_argument("--session-batch", choices=("fixed_request_fresh_rust", "fixed_request_worker"))
    parser.add_argument("--cache-root", type=Path)
    args = parser.parse_args()
    try:
        if args.identity_profile or args.session_batch:
            if args.cache_root is None:
                raise ValueError("--cache-root required for session/identity probe")
            result = (session_batch(args.cache_root, args.edges_npz, args.nodes_parquet, args.session_batch)
                      if args.session_batch else profiled_identity(args.cache_root, args.edges_npz, args.nodes_parquet))
        else:
            if args.output_dir is None:
                raise ValueError("--output-dir required")
            result = execute(args.edges_npz.resolve(strict=True), args.nodes_parquet.resolve(strict=True),
                             args.output_dir.resolve())
            result = {"status": result["status"], "five_round_hit_summary": result["five_round_hit_summary"]}
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(f"cost-decomposition FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
