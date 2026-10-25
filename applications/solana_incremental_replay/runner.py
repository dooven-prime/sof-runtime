"""Fresh Rust processes with recorded work, fault boundaries and local resources."""
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter, sleep

import psutil

from applications.solana_offchain_slice.common import file_sha, parse

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CRATE = ROOT / "plugins/rust/solana-incremental-replay"
POINTS = ("partial_segment", "segment_publish", "partial_checkpoint", "checkpoint_publish", "partial_projection", "projection_publish")


def binary():
    return CRATE / "target/release" / ("solana-incremental-replay.exe" if os.name == "nt" else "solana-incremental-replay")


def build():
    subprocess.run(["cargo", "build", "--release", "--locked", "--manifest-path", str(CRATE / "Cargo.toml")], cwd=ROOT, check=True)


def bindings():
    paths = list(HERE.glob("*.py")) + [HERE / "CONTRACT.md", HERE / "plan.v1.json", CRATE / "src/main.rs", CRATE / "Cargo.toml", CRATE / "Cargo.lock",
            ROOT / "tests/cross_language/test_solana_incremental_replay.py"]
    paths += [ROOT / "applications/solana_offchain_slice" / name for name in ("common.py", "reference.py", "fixtures.py")]
    paths += [ROOT / "plugins/rust/solana-offchain-slice/src/main.rs"]
    return {**{p.relative_to(ROOT).as_posix(): file_sha(p) for p in sorted(paths)},
            "rust_binary": file_sha(binary()), "python_executable": file_sha(sys.executable)}


def invoke(manifest, state, directory, name, mode="incremental", anchor=None, pause=None, forbid_prefix=False, timeout=120):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    out, err = directory / f"{name}.stdout.json", directory / f"{name}.stderr.txt"
    args = [str(binary()), str(Path(manifest).resolve()), str(Path(state).resolve()), mode]
    if anchor is not None:
        args += ["--checkpoint-sha256", anchor]
    if pause:
        args += ["--pause", pause[0], str(pause[1])]
    if forbid_prefix:
        args += ["--forbid-prefix-decode"]
    start = perf_counter()
    rss = peak = observations = 0
    cpu = 0.
    killed = False
    with out.open("xb") as stdout, err.open("xb") as stderr:
        child = subprocess.Popen(args, cwd=ROOT, stdout=stdout, stderr=stderr)
        process = psutil.Process(child.pid)
        try:
            while child.poll() is None:
                try:
                    memory = process.memory_info()
                    rss = max(rss, memory.rss)
                    peak = max(peak, getattr(memory, "peak_wset", 0))
                    times = process.cpu_times()
                    cpu = max(cpu, times.user+times.system)
                    observations += 1
                except psutil.NoSuchProcess:
                    pass
                if pause and b'"FAULT_REACHED"' in out.read_bytes():
                    if parse(out.read_bytes()) != {"status": "FAULT_REACHED", "point": pause[0], "slot": pause[1]}:
                        raise ValueError("wrong fault boundary")
                    child.kill()
                    killed = True
                    break
                if perf_counter()-start > timeout or rss > 1024**3:
                    raise RuntimeError("time/RSS limit: UNRESOLVED")
                sleep(.002)
            code = child.wait()
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
    if err.stat().st_size:
        raise RuntimeError(err.read_text()[:1000])
    result = parse(out.read_bytes())
    if pause:
        if not killed or code == 0:
            raise ValueError("live process not killed at fault")
    elif code == 0 and result.get("status") != "COMPLETED_LOCAL_CAPTURE":
        raise ValueError("completion protocol")
    elif code != 0 and result.get("status") != "UNRESOLVED":
        raise ValueError("failure protocol")
    return result, {"returncode": code, "terminated_at_boundary": killed, "process_wall_seconds": perf_counter()-start,
                    "max_observed_rss_bytes": rss or None, "observed_os_peak_working_set_bytes": peak or None,
                    "sampled_cpu_seconds_lower_bound": cpu, "resource_observations": observations,
                    "stdout_sha256": file_sha(out), "stderr_sha256": file_sha(err)}


def check_work(result, manifest, initial, mode):
    start, end = manifest["start_slot"], manifest["end_slot"]
    slots = [b["slot"] for b in manifest["listed_blocks"]]
    expected_prefix = [s for s in slots if s < start+initial] if mode == "full_reproject" else []
    expected_suffix = [s for s in slots if s >= start+initial]
    work = result["work"]
    if result["initial_committed_slots"] != initial or work["prefix_decoded_slots"] != expected_prefix or work["suffix_decoded_slots"] != expected_suffix:
        raise ValueError("decode trace is not exactly the declared work")
    if work["newly_committed_slots"] != end-start+1-initial:
        raise ValueError("new commit count")
