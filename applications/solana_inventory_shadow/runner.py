"""Test-local controller, not a shared process API or application decision engine."""
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic, sleep

from applications.solana_offchain_slice.common import canonical, file_sha, parse
from applications.solana_publication_recovery.runner import bindings as original_bindings
from .reference import inspect

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CRATE = ROOT/"plugins/rust/a0-inventory-inspector"
CORE = ROOT/"plugins/rust/a0-mechanical-core"


def binary(): return CRATE/"target/release"/("a0-inventory-inspector.exe" if os.name == "nt" else "a0-inventory-inspector")


def build():
    subprocess.run(["cargo", "build", "--release", "--locked", "--offline", "--manifest-path", str(CRATE/"Cargo.toml")], cwd=ROOT, check=True)


def bindings():
    files = list(HERE.glob("*.py"))+list((CRATE/"src").glob("*.rs"))+[HERE/"CONTRACT.md", HERE/"plan.v0.json", CRATE/"Cargo.toml", CRATE/"Cargo.lock",
        ROOT/"tests/cross_language/test_a0_inventory_shadow.py"]
    files += list((CORE/"src").rglob("*.rs"))+[CORE/"Cargo.toml", CORE/"Cargo.lock"]
    return {"original_producer": original_bindings(), "shadow": {**{p.relative_to(ROOT).as_posix(): file_sha(p) for p in sorted(files)},
            "rust_binary": file_sha(binary()), "python_executable": file_sha(sys.executable)}}


def absolute(path):
    p = Path(path)
    return str(p if p.is_absolute() else ROOT/p)


def invoke(data, manifest, expected, directory, name, pause=None, change=None, timeout=60):
    directory = Path(directory)
    if directory.resolve().is_relative_to(Path(data).resolve()):
        raise ValueError("detached shadow output directory required")
    directory.mkdir(parents=True, exist_ok=True)
    out, err, marker = (directory/f"{name}.{s}" for s in ("stdout.json", "stderr.txt", "marker.json"))
    argv = [str(binary()), absolute(data), absolute(manifest), absolute(expected)]
    if pause: argv += ["--pause", pause, absolute(marker)]
    env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
    started = monotonic(); killed = False; altered = False; mark = None
    with out.open("xb") as stdout, err.open("xb") as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        try:
            while child.poll() is None:
                if marker.exists() and not mark:
                    try: mark = parse(marker.read_bytes())
                    except ValueError: mark = None
                    if mark:
                        if mark != {"point": pause, "pid": child.pid}: raise ValueError("wrong actual-process marker")
                        if change:
                            change(); altered = True
                            with Path(str(marker)+".continue").open("xb") as f: f.write(b"continue")
                        else: child.kill(); killed = True; break
                if monotonic()-started > timeout: raise RuntimeError("shadow timeout; no matching observation")
                sleep(.004)
            code = child.wait()
        finally:
            if child.poll() is None: child.kill()
            child.wait()
    if pause and mark is None: raise ValueError(f"hook not reached: {pause}: {out.read_text()[:500]} {err.read_text()[:500]}")
    result = None
    if not killed and not err.stat().st_size:
        try: result = parse(out.read_bytes())
        except ValueError: pass
    if result is not None and result.get("status") == "INTEGRITY_MATCHES":
        if code != 0 or result["observer_identity"] != {"role": "ShadowObserverExecution", "sha256": file_sha(binary())}:
            raise ValueError("observer identity / process completion mismatch")
        if result["source_trust"] != "NOT_ASSESSED" or result["application_decision"] != "NOT_ASSESSED" or result["validity"] != "OBSERVED_INTERVAL_ONLY":
            raise ValueError("semantic/lifetime boundary changed")
        status = "MATCHED_BYTES"
    elif result and code != 0 and result.get("status") == "REJECTED": status = "REJECTED"
    else: status = "INCOMPLETE"
    record = {"schema": "sof-runtime.solana-inventory-shadow.observation.v0", "status": status,
        "matching_observation_admissible": status == "MATCHED_BYTES", "application_decision": "NOT_ASSESSED",
        "observer_executable_sha256": file_sha(binary()), "root_local": absolute(data), "manifest_local": absolute(manifest),
        "bindings_local": absolute(expected), "manifest_sha256": file_sha(manifest), "bindings_sha256": file_sha(expected),
        "result": result, "process": {"returncode": code, "actually_killed": killed, "changed_during_observation": altered,
            "marker": mark, "wall_seconds": monotonic()-started, "stdout_sha256": file_sha(out), "stderr_sha256": file_sha(err)},
        "observation_file": name+".observation.json"}
    with (directory/record["observation_file"]).open("xb") as stream: stream.write(canonical(record))
    return record


def compare(data, manifest, expected, observation):
    reference = inspect(data, manifest, expected)
    result = observation["result"]
    mapped = {"INTEGRITY_MATCHES": "MATCHED_BYTES", "REJECTED": "REJECTED", "INCOMPLETE": "INCOMPLETE"}[reference["status"]]
    if observation["status"] != mapped: raise ValueError(f"Rust/Python decision mismatch: {observation}, {reference}")
    if mapped == "MATCHED_BYTES":
        for key in ("entries", "manifest_utf8", "manifest_sha256", "bindings_sha256", "byte_passes"):
            if result["inspection"][key] != reference[key]: raise ValueError("Rust/Python complete inventory mismatch: "+key)
    return reference
