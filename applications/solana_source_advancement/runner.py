"""Fresh Rust transition processes and source-addressed local evidence."""
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter, sleep

import psutil

from applications.solana_offchain_slice.common import canonical, file_sha, parse
from applications.solana_incremental_replay.runner import bindings as frozen_bindings

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CRATE = ROOT/"plugins/rust/solana-source-advancement"


def binary():
    return CRATE/"target/release"/("solana-source-advancement.exe" if os.name == "nt" else "solana-source-advancement")


def build():
    subprocess.run(["cargo", "build", "--release", "--locked", "--manifest-path", str(CRATE/"Cargo.toml")], cwd=ROOT, check=True)


def bindings():
    files = list(HERE.glob("*.py"))+[HERE/"CONTRACT.md", HERE/"plan.v0.json", CRATE/"Cargo.toml", CRATE/"Cargo.lock", CRATE/"src/main.rs",
            ROOT/"tests/cross_language/test_solana_source_advancement.py"]
    return {"frozen_replay": frozen_bindings(), "advancement": {**{p.relative_to(ROOT).as_posix(): file_sha(p) for p in sorted(files)},
            "rust_binary": file_sha(binary()), "python_executable": file_sha(sys.executable)}}


def tree_hashes(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): file_sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def invoke(req, destination, directory, name, timeout=120):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    request_path = directory/f"{name}.request.json"
    with request_path.open("xb") as stream: stream.write(canonical(req))
    out, err = directory/f"{name}.stdout.json", directory/f"{name}.stderr.txt"
    start = perf_counter(); rss = peak = observations = 0
    with out.open("xb") as stdout, err.open("xb") as stderr:
        child = subprocess.Popen([str(binary()), str(request_path.resolve()), str(Path(destination).resolve())], cwd=ROOT, stdout=stdout, stderr=stderr)
        process = psutil.Process(child.pid)
        try:
            while child.poll() is None:
                try:
                    m = process.memory_info(); rss = max(rss, m.rss); peak = max(peak, getattr(m, "peak_wset", 0)); observations += 1
                except psutil.NoSuchProcess:
                    pass
                if perf_counter()-start > timeout or rss > 1024**3:
                    raise RuntimeError("transition resource limit: UNRESOLVED")
                sleep(.002)
            code = child.wait()
        finally:
            if child.poll() is None: child.kill()
            child.wait()
    if err.stat().st_size: raise RuntimeError(err.read_text()[:1000])
    result = parse(out.read_bytes())
    if code == 0:
        if result.get("status") != "COMPLETED_OFFLINE_ADVANCEMENT" or result.get("published") is not True:
            raise ValueError("success protocol")
    elif result.get("status") not in ("UNRESOLVED", "REJECTED_PREFIX_CONFLICT") or result.get("published") is not False:
        raise ValueError("refusal protocol")
    return result, {"returncode": code, "process_wall_seconds": perf_counter()-start, "max_observed_rss_bytes": rss or None,
                    "observed_os_peak_working_set_bytes": peak or None, "resource_observations": observations,
                    "request_sha256": file_sha(request_path), "stdout_sha256": file_sha(out), "stderr_sha256": file_sha(err)}
