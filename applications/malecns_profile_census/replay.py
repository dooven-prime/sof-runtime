from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from .oracle import run as run_python
from .protocol import canonical_bytes, sha256_file


ROOT = Path(__file__).resolve().parents[2]
CRATE = ROOT / "plugins" / "rust" / "malecns-profile-census"


def find_cargo() -> str:
    configured = os.environ.get("CARGO")
    cargo = configured or shutil.which("cargo")
    if cargo:
        return cargo
    candidate = Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    if candidate.is_file():
        return str(candidate)
    raise RuntimeError("Cargo was not found; set CARGO to the cargo executable")


def find_rustc() -> str:
    rustc = shutil.which("rustc")
    if rustc:
        return rustc
    cargo = Path(find_cargo())
    candidate = cargo.with_name("rustc.exe" if os.name == "nt" else "rustc")
    if candidate.is_file():
        return str(candidate)
    return "rustc"


def rust_binary() -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return CRATE / "target" / "release" / f"malecns-profile-census{suffix}"


def ensure_binary() -> Path:
    binary = rust_binary()
    if not binary.is_file():
        subprocess.run(
            [find_cargo(), "build", "--release", "--locked", "--manifest-path", str(CRATE / "Cargo.toml")],
            cwd=ROOT,
            check=True,
        )
    if not binary.is_file():
        raise RuntimeError(f"Rust binary was not produced: {binary}")
    return binary


def timed_python(input_path: Path) -> tuple[dict, float]:
    started = time.perf_counter()
    result = run_python(input_path)
    return result, time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(description="Exact Python/Rust offline profile-census replay")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        input_path = args.input.resolve(strict=True)
        input_digest_before = sha256_file(input_path)
        python_result, python_seconds = timed_python(input_path)
        binary = ensure_binary()
        started = time.perf_counter()
        rust = subprocess.run(
            [str(binary), str(input_path)],
            cwd=ROOT,
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
        )
        rust_seconds = time.perf_counter() - started
        rust_result = json.loads(rust.stdout)
        python_bytes = canonical_bytes(python_result)
        rust_bytes = canonical_bytes(rust_result)
        input_digest_after = sha256_file(input_path)
        match = python_bytes == rust_bytes
        receipt = {
            "schema": "sof-runtime.malecns-profile-census-replay.v1",
            "status": "PASS_EXACT_REPLAY" if match and input_digest_before == input_digest_after else "FAIL",
            "input": {
                "path_name": input_path.name,
                "size": input_path.stat().st_size,
                "sha256_before": input_digest_before,
                "sha256_after": input_digest_after,
                "unchanged": input_digest_before == input_digest_after,
            },
            "result": {
                "schema": python_result["schema"],
                "source_field": python_result["source_field"],
                "source_identity": python_result["source_identity"],
                "sha256": hashlib.sha256(python_bytes).hexdigest(),
                "python_rust_canonical_bytes_equal": match,
                "eligible_sources": python_result["eligible_sources"],
                "profile_classes": python_result["profile_classes"],
            },
            "implementations": {
                "python_oracle_sha256": sha256_file(Path(__file__).with_name("oracle.py")),
                "python_protocol_sha256": sha256_file(Path(__file__).with_name("protocol.py")),
                "python_preparer_sha256": sha256_file(Path(__file__).with_name("prepare_input.py")),
                "rust_source_sha256": sha256_file(CRATE / "src" / "main.rs"),
                "cargo_manifest_sha256": sha256_file(CRATE / "Cargo.toml"),
                "cargo_lock_sha256": sha256_file(CRATE / "Cargo.lock"),
                "rust_binary_sha256": sha256_file(binary),
            },
            "environment": {
                "python": platform.python_version(),
                "rustc": subprocess.run(
                    [find_rustc(), "--version"],
                    cwd=ROOT, capture_output=True, text=True, check=False,
                ).stdout.strip(),
                "platform": platform.platform(),
            },
            "timing_observation": {
                "python_seconds": python_seconds,
                "rust_process_seconds": rust_seconds,
                "benchmark_claim": False,
            },
            "claim_boundary": {
                "full_malecns_replay": False,
                "solana_workload": False,
                "paper_claim_admission": False,
                "performance_claim": False,
                "scope": "offline implementation parity on the supplied source-addressed packet",
            },
        }
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if receipt["status"] == "PASS_EXACT_REPLAY" else 1
    except Exception as error:
        print(f"profile-census-replay: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
