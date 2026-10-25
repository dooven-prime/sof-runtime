"""Exact protected-byte guard and unchanged SOF test closure."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROTECTED_ROOTS = ("src/sof_runtime", "contracts", "profiles", "services", "workflows", "examples",
                   "tests/unit", "tests/conformance", "tests/golden", "tests/regression",
                   "evaluations/mcp-agent-blackbox-v1", "evaluations/mcp-agent-matrix-v1")
PROTECTED_FILES = ("pyproject.toml", "tools/verify_digests.py", "tools/check_service_implementation_closure.py",
                   "tools/validate_mcp_agent_evaluation.py", "tools/score_mcp_agent_matrix.py",
                   "tools/check_wheel_install.py")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def inventory():
    files = [ROOT/p for p in PROTECTED_FILES]
    for name in PROTECTED_ROOTS:
        files += [p for p in (ROOT/name).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    out = {}
    for p in sorted(set(files)):
        if p.is_symlink(): raise ValueError("protected source must not be a link")
        out[p.relative_to(ROOT).as_posix()] = {"length": p.stat().st_size, "sha256": sha(p)}
    return out


def tests(output):
    """This function runs in a fresh interpreter, not the A0 acceptance process."""
    import sof_runtime
    if not Path(sof_runtime.__file__).resolve().is_relative_to(ROOT/"src"):
        raise RuntimeError("compatibility test imports a different checkout")
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    loader = unittest.TestLoader(); suite = unittest.TestSuite()
    for name in ("unit", "conformance", "golden", "regression"):
        suite.addTests(loader.discover(str(ROOT/"tests"/name), top_level_dir=str(ROOT)))
    def ids(s):
        return [x.id() for x in s] if all(not isinstance(x, unittest.TestSuite) for x in s) else [v for x in s for v in (ids(x) if isinstance(x, unittest.TestSuite) else [x.id()])]
    declared = sorted(ids(suite))
    with (output/"unittest.log").open("x", encoding="utf-8") as f:
        result = unittest.TextTestRunner(stream=f, verbosity=2).run(suite)
    record = {"tests": declared, "count": result.testsRun, "skipped": sorted((t.id(), reason) for t, reason in result.skipped),
              "failures": [t.id() for t, _ in result.failures], "errors": [t.id() for t, _ in result.errors],
              "successful": result.wasSuccessful()}
    (output/"test-result.json").write_bytes(canonical(record))
    if not record["successful"]: raise RuntimeError("SOF compatibility tests failed; see unittest.log")
    return record


def command(directory, name, argv, timeout=600):
    directory = Path(directory); env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT/"src"), str(ROOT), env.get("PYTHONPATH", "")])
    # The unchanged wheel test uses a venv with system-site-packages. Pip must
    # install the wheel there, not treat this checkout's same-version metadata
    # on PYTHONPATH as an already-installed venv console script.
    env["PIP_FORCE_REINSTALL"] = "1"
    with (directory/(name+".stdout.txt")).open("xb") as out, (directory/(name+".stderr.txt")).open("xb") as err:
        subprocess.run(argv, cwd=ROOT, env=env, stdout=out, stderr=err, timeout=timeout, check=True)


def run(directory, wheel=False):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    before = inventory()
    command(directory, "tests", [sys.executable, "-B", "-m", "applications.shared_a0_extraction_review.sof_gate", str(directory/"tests")])
    checks = (("vendored", "tools/verify_digests.py", []),
              ("service", "tools/check_service_implementation_closure.py", ["evaluations/mcp-agent-matrix-v1/service-closure.current.json"]),
              ("evaluation", "tools/validate_mcp_agent_evaluation.py", ["evaluations/mcp-agent-blackbox-v1"]),
              ("matrix", "tools/score_mcp_agent_matrix.py", ["evaluations/mcp-agent-matrix-v1", "--check-summary"]))
    for name, script, args in checks: command(directory, name, [sys.executable, "-B", script, *args])
    if wheel: command(directory, "wheel", [sys.executable, "-B", "tools/check_wheel_install.py"], timeout=900)
    if inventory() != before: raise ValueError("SOF checks changed protected byte closure")
    return json.loads((directory/"tests/test-result.json").read_bytes())


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("directory", type=Path)
    print(json.dumps(tests(p.parse_args().directory), sort_keys=True))
