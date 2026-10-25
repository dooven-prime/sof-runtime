"""Fresh processes, explicit kill hooks and separately bound recovery evidence."""
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter, sleep

import psutil

from applications.solana_offchain_slice.common import canonical, file_sha, parse
from applications.solana_source_advancement.runner import bindings as prior_bindings, tree_hashes

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CRATE = ROOT/"plugins/rust/solana-publication-recovery"
POINTS = tuple(parse((HERE/"plan.v0.json").read_bytes())["fault_points"])


def binary():
    return CRATE/"target/release"/("solana-publication-recovery.exe" if os.name == "nt" else "solana-publication-recovery")


def build():
    subprocess.run(["cargo", "build", "--release", "--locked", "--offline", "--manifest-path", str(CRATE/"Cargo.toml")], cwd=ROOT, check=True)


def bindings():
    files = list(HERE.glob("*.py"))+[HERE/"CONTRACT.md", HERE/"plan.v0.json", CRATE/"Cargo.toml", CRATE/"Cargo.lock", CRATE/"src/main.rs",
        ROOT/"tests/cross_language/test_solana_publication_recovery.py"]
    return {"source_advancement": prior_bindings(), "publication": {**{p.relative_to(ROOT).as_posix(): file_sha(p) for p in sorted(files)},
            "rust_binary": file_sha(binary()), "python_executable": file_sha(sys.executable)}}


def control(destination):
    p = Path(destination)
    return p.parent/f".{p.name}.publication-v0"


def invoke(request_path, destination, directory, name, pause=None, timeout=120):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    out, err, marker = (directory/f"{name}.{s}" for s in ("stdout.json", "stderr.txt", "marker.json"))
    args = [str(binary()), str(Path(request_path).resolve()), str(Path(destination).resolve())]
    if pause:
        if pause not in POINTS: raise ValueError("unknown pause point")
        args += ["--pause", pause, str(marker.resolve())]
    start = perf_counter(); rss = peak = 0; killed = False; mark = None
    env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
    with out.open("xb") as stdout, err.open("xb") as stderr:
        child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        process = psutil.Process(child.pid)
        try:
            while child.poll() is None:
                try:
                    m = process.memory_info(); rss = max(rss, m.rss); peak = max(peak, getattr(m, "peak_wset", 0))
                except psutil.NoSuchProcess:
                    pass
                if marker.exists():
                    try: mark = parse(marker.read_bytes())
                    except ValueError: mark = None
                    if mark:
                        if mark["pid"] != child.pid or mark["point"] != pause: raise ValueError("wrong kill marker")
                        child.kill(); killed = True; break
                if perf_counter()-start > timeout or rss > 1024**3:
                    raise RuntimeError("publication resource limit: UNRESOLVED")
                sleep(.003)
            code = child.wait()
            try: cpu = sum(process.cpu_times()[:2])
            except (psutil.NoSuchProcess, psutil.AccessDenied): cpu = None
        finally:
            if child.poll() is None: child.kill()
            child.wait()
    if err.stat().st_size: raise RuntimeError(err.read_text()[:2000])
    result = None if killed else parse(out.read_bytes())
    if pause and not killed: raise ValueError(f"fault point not reached: {pause}: {result}")
    if killed and out.stat().st_size: raise ValueError("killed attempt already returned a result")
    if not killed and ((code == 0) != (result.get("publication_confirmed") is True)):
        raise ValueError("result/exit mismatch")
    return result, {"returncode": code, "actually_killed": killed, "marker": mark,
        "wall_seconds": perf_counter()-start, "cpu_seconds_observed": cpu,
        "max_observed_rss_bytes": rss, "observed_os_peak_working_set_bytes": peak,
        "stdout_sha256": file_sha(out), "stderr_sha256": file_sha(err)}


def write_request(path, req):
    path = Path(path)
    with path.open("xb") as stream: stream.write(canonical(req))
    return path
