"""Process isolation and exact file-state observations for the narrow probe."""
import os
from pathlib import Path
import stat
import subprocess
import sys
from time import perf_counter, sleep

import psutil

from applications.solana_offchain_slice.common import file_sha, parse
from applications.solana_incremental_replay.runner import binary as replay_binary, bindings as replay_bindings

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CRATE = ROOT/"plugins/rust/solana-prefix-integrity"


def binary():
    return CRATE/"target/release"/("solana-prefix-integrity.exe" if os.name == "nt" else "solana-prefix-integrity")


def build():
    subprocess.run(["cargo", "build", "--release", "--locked", "--manifest-path", str(CRATE/"Cargo.toml")], cwd=ROOT, check=True)


def bindings():
    paths = list(HERE.glob("*.py"))+[HERE/"CONTRACT.md", HERE/"plan.v1.json", CRATE/"Cargo.toml", CRATE/"Cargo.lock", CRATE/"src/main.rs",
            ROOT/"tests/cross_language/test_solana_prefix_integrity.py"]
    return {"frozen_replay": replay_bindings(), "probe": {
        **{p.relative_to(ROOT).as_posix(): file_sha(p) for p in sorted(paths)},
        "binary_sha256": file_sha(binary()), "python_executable_sha256": file_sha(sys.executable)}}


def file_state(path):
    path = Path(path)
    s = path.stat(follow_symlinks=False)
    if path.is_symlink() or not stat.S_ISREG(s.st_mode):
        raise ValueError("not a regular observed file")
    return {"size": s.st_size, "device": s.st_dev, "inode": s.st_ino, "mode": s.st_mode,
            "mtime_ns": s.st_mtime_ns, "ctime_ns": s.st_ctime_ns, "atime_ns": s.st_atime_ns,
            "birthtime_ns": getattr(s, "st_birthtime_ns", None), "file_attributes": getattr(s, "st_file_attributes", None),
            "reparse_tag": getattr(s, "st_reparse_tag", None)}


def observed_files(manifest, state, prefix):
    manifest = Path(manifest); state = Path(state)
    m = parse(manifest.read_bytes())
    sources = {f"capture/{b['role']}": manifest.parent/m["rpc"][b["role"]]["response"]
               for b in m["listed_blocks"] if b["slot"] < m["start_slot"]+prefix}
    return {**sources, **{f"state/{p.name}": p for p in sorted(state.iterdir()) if p.is_file()}}


def warm(files):
    start = perf_counter(); cpu = time_cpu(); count = 0
    for path in files.values():
        with Path(path).open("rb") as stream:
            while block := stream.read(65536):
                count += len(block)
    return {"logical_read_bytes": count, "file_count": len(files), "wall_seconds": perf_counter()-start,
            "cpu_seconds": time_cpu()-cpu, "kind": "EXPLICIT_READ_ONLY_NOT_VALIDATION", "os_cache_guarantee": False}


def time_cpu():
    return sum(os.times()[:2])


def invoke(manifest, state, anchor, output, prefix, directory, name, timeout=120):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    stdout_path, stderr_path = directory/f"{name}.stdout.json", directory/f"{name}.stderr.txt"
    args = [str(binary()), str(Path(manifest).resolve()), str(Path(state).resolve()), str(replay_binary()), anchor,
            str(Path(output).resolve()), str(prefix)]
    start = perf_counter(); rss = peak = observations = 0
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        child = subprocess.Popen(args, cwd=ROOT, stdout=stdout, stderr=stderr)
        process = psutil.Process(child.pid)
        try:
            while child.poll() is None:
                try:
                    m = process.memory_info(); rss = max(rss, m.rss); peak = max(peak, getattr(m, "peak_wset", 0)); observations += 1
                except psutil.NoSuchProcess:
                    pass
                if perf_counter()-start > timeout or rss > 1024**3:
                    raise RuntimeError("probe time/RSS exceeded: UNRESOLVED")
                sleep(.002)
            code = child.wait()
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
    if stderr_path.stat().st_size:
        raise RuntimeError(stderr_path.read_text()[:1000])
    result = parse(stdout_path.read_bytes())
    if (code == 0 and result.get("status") != "MEASURED_VERIFIED_PREFIX") or (code != 0 and result.get("status") != "UNRESOLVED"):
        raise ValueError("probe exit/result protocol")
    return result, {"returncode": code, "process_wall_seconds": perf_counter()-start,
                    "max_observed_rss_bytes": rss or None, "observed_os_peak_working_set_bytes": peak or None,
                    "resource_observations": observations, "stdout_sha256": file_sha(stdout_path), "stderr_sha256": file_sha(stderr_path)}
