"""Application-local process lifecycle and source-bound implementation identity."""
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter,sleep

import psutil

from .common import file_sha,parse

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CRATE=ROOT/"plugins/rust/solana-offchain-slice"
POINTS=("partial_segment","segment_publish","partial_checkpoint","checkpoint_publish","partial_projection","projection_publish")


def binary(): return CRATE/"target/release"/("solana-offchain-slice.exe" if os.name=="nt" else "solana-offchain-slice")


def build():
    subprocess.run(["cargo","build","--release","--locked","--manifest-path",str(CRATE/"Cargo.toml")],cwd=ROOT,check=True)


def bindings():
    paths=list(HERE.glob("*.py"))+[HERE/"CONTRACT.md",HERE/"ACCEPTANCE_PLAN.md",
            CRATE/"src/main.rs",CRATE/"Cargo.toml",CRATE/"Cargo.lock",ROOT/"tests/cross_language/test_solana_offchain_slice.py"]
    return {**{p.relative_to(ROOT).as_posix():file_sha(p) for p in sorted(paths)},
            "rust_binary":file_sha(binary()),"python_executable":file_sha(sys.executable)}


def invoke(manifest,state,directory,name,pause=None,timeout=60):
    out=Path(directory)/f"{name}.stdout.json";err=Path(directory)/f"{name}.stderr.txt"
    args=[str(binary()),str(Path(manifest).resolve()),str(Path(state).resolve())]
    if pause: args += ["--pause",pause[0],str(pause[1])]
    start=perf_counter();rss=peak=observations=0;cpu=0.;killed=False
    with out.open("xb") as stdout,err.open("xb") as stderr:
        child=subprocess.Popen(args,cwd=ROOT,stdout=stdout,stderr=stderr)
        process=psutil.Process(child.pid)
        try:
            while child.poll() is None:
                try:
                    memory=process.memory_info();rss=max(rss,memory.rss);peak=max(peak,getattr(memory,"peak_wset",0))
                    times=process.cpu_times();cpu=max(cpu,times.user+times.system);observations+=1
                except psutil.NoSuchProcess: pass
                if pause and b'"FAULT_REACHED"' in out.read_bytes():
                    marker=parse(out.read_bytes().splitlines()[0])
                    if marker!={"status":"FAULT_REACHED","point":pause[0],"slot":pause[1]}: raise ValueError("wrong fault boundary")
                    child.kill();killed=True;break
                if perf_counter()-start>timeout or rss>1024**3: raise RuntimeError("child time/RSS limit; no acceptance")
                sleep(.01)
            code=child.wait()
        finally:
            if child.poll() is None: child.kill()
            child.wait()
    elapsed=perf_counter()-start
    if err.stat().st_size: raise RuntimeError(err.read_text()[:1000])
    result=parse(out.read_bytes())
    if pause:
        if not killed or code==0: raise ValueError("fault did not terminate a live process")
    elif code==0 and result.get("status")!="COMPLETED_LOCAL_CAPTURE": raise ValueError("success exit without completion")
    elif code!=0 and result.get("status")!="UNRESOLVED": raise ValueError("unexpected failure response")
    return result,{"returncode":code,"terminated_at_boundary":killed,"process_wall_seconds":elapsed,
                   "max_observed_rss_bytes":rss or None,"observed_os_peak_working_set_bytes":peak or None,
                   "sampled_cpu_seconds_lower_bound":cpu,"resource_observations":observations,
                   "stdout_sha256":file_sha(out),"stderr_sha256":file_sha(err)}
