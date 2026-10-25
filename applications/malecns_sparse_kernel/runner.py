"""Fresh-process Rust kernel invocation with separate resource observations."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter,sleep

import psutil

from .protocol import canonical,file_sha

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CRATE=ROOT/"plugins/rust/malecns-spmv"


def binary():
    return CRATE/"target/release"/("malecns-spmv.exe" if os.name=="nt" else "malecns-spmv")


def build():
    subprocess.run(["cargo","build","--release","--locked","--manifest-path",str(CRATE/"Cargo.toml")],cwd=ROOT,check=True)


def bindings():
    paths=list(HERE.glob("*.py"))+[HERE/"CONTRACT.md",HERE/"BENCHMARK_PLAN.md",
            CRATE/"Cargo.toml",CRATE/"Cargo.lock",CRATE/"src/main.rs",
            ROOT/"tests/cross_language/test_malecns_spmv.py",
            ROOT/"applications/malecns_profile_census/prepare_input.py"]
    return {**{p.relative_to(ROOT).as_posix():file_sha(p) for p in sorted(paths)},
            "rust_binary":file_sha(binary()),"python_executable":file_sha(sys.executable)}


def request(packet,digest,vector,mode="numerical",operation="spmv",threads=1,iterations=1,repeats=1,warmups=0):
    return {"schema":"sof-runtime.malecns-spmv.request.v0","packet":str(Path(packet).resolve()),
            "packet_sha256":digest,"mode":mode,"operation":operation,"threads":threads,
            "iterations":iterations,"repeats":repeats,"warmups":warmups,"vector":vector}


def run(raw,directory,name,timeout=300,rss_limit=8*1024**3):
    directory=Path(directory); path=directory/f"{name}.request.json"
    with path.open("xb") as out: out.write(canonical(raw))
    stdout=directory/f"{name}.result.json"; stderr=directory/f"{name}.stderr.txt"
    started=perf_counter(); max_rss=0; os_peak=0; max_cpu=0.; observations=0
    with stdout.open("xb") as out,stderr.open("xb") as err:
        child=subprocess.Popen([str(binary()),str(path)],cwd=ROOT,stdout=out,stderr=err)
        process=psutil.Process(child.pid)
        try:
            while child.poll() is None:
                try:
                    memory=process.memory_info(); max_rss=max(max_rss,memory.rss)
                    os_peak=max(os_peak,getattr(memory,"peak_wset",0))
                    cpu=process.cpu_times(); max_cpu=max(max_cpu,cpu.user+cpu.system); observations+=1
                except psutil.NoSuchProcess:
                    pass
                if perf_counter()-started>timeout or max_rss>rss_limit:
                    raise RuntimeError("worker time/RSS limit exceeded; no acceptance")
                sleep(.01)
            code=child.wait()
        finally:
            if child.poll() is None: child.kill()
            child.wait()
    elapsed=perf_counter()-started
    if code or stderr.stat().st_size:
        raise RuntimeError(f"Rust worker failed: {stdout.read_text()[:500]} {stderr.read_text()[:500]}")
    result=json.loads(stdout.read_bytes())
    if result["status"]!="COMPLETED_LOCAL": raise ValueError("incomplete worker")
    return result,{"process_wall_seconds":elapsed,"sampled_cpu_seconds_lower_bound":max_cpu,
                   "max_observed_rss_bytes":max_rss,"observed_os_peak_working_set_bytes":os_peak or None,
                   "resource_observations":observations,"poll_interval_seconds":.01,
                   "request_sha256":file_sha(path),"result_file_sha256":file_sha(stdout)}
