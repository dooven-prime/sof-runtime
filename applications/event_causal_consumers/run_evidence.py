"""Replay the declared controls and all 30 tests from an offline source snapshot."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest


HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_source():
    manifest_path = HERE / "source-manifest.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    require(manifest["schema"] == "rime.paper40.q2-source.v1", "wrong source manifest")
    expected = {item["path"] for item in manifest["files"]}
    require(len(expected) == len(manifest["files"]), "duplicate source path")
    actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob("*") if p.is_file()}
    require(actual == expected | {"source-manifest.json"}, "snapshot inventory drift")
    for item in manifest["files"]:
        path = HERE / item["path"]
        require(path.resolve().is_relative_to(HERE), "source path escapes snapshot")
        require(not path.is_symlink(), "source symlink is not admitted")
        data = path.read_bytes()
        require(len(data) == item["size"] and hashlib.sha256(data).hexdigest() == item["sha256"],
                "source drift: " + item["path"])
    return hashlib.sha256(raw).hexdigest()


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_ids = []

    def startTest(self, test):
        self.test_ids.append(test.id())
        super().startTest(test)


def replay():
    from fixed_controls import frozen_models, run
    from q2 import check, verify_rejection
    from q2_examples import controls

    before = verify_source()
    cases = []
    for name, request in controls().items():
        decision = check(request)
        require(decision["status"] in {"PASS_EXACT", "FAIL_READ", "FAIL_GUARD", "FAIL_SUCCESSOR"},
                "control did not complete: " + name)
        verification = verify_rejection(request, decision) if "witness" in decision else None
        cases.append({"name": name, "request": request, "decision": decision,
                      "rejection_replay": verification})
    with frozen_models(source_dir=HERE / "frozen" / "paper39") as models:
        fixed = run(models)
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    tested = unittest.TextTestRunner(stream=stream, resultclass=RecordingResult).run(suite)
    require(tested.wasSuccessful() and not tested.skipped and tested.testsRun == 30,
            "full unskipped test replay failed:\n" + stream.getvalue())
    require(verify_source() == before, "replay changed snapshot bytes")
    return {
        "schema": "rime.paper40.q2-controls.v1",
        "validation_mode": "LOCAL_CLOSURE_VERIFICATION",
        "source_manifest_sha256": before,
        "cases": cases,
        "fixed_controls": fixed,
        "tests": {"run": tested.testsRun, "skipped": 0, "failures": 0, "errors": 0,
                  "ids": sorted(tested.test_ids)},
        "independent_validation": False,
        "implementation_correctness_proved": False,
        "canonical_compiler_admission": False,
    }


def clean_environment():
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith("PYTHON") and key not in
           {"RIME_LITE_UPSTREAM", "RIME_PAPER39_SNAPSHOT"}}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0", PYTHONUTF8="1",
               RIME_PAPER39_SNAPSHOT=str(HERE / "frozen" / "paper39"))
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the bounded result; default stdout")
    parser.add_argument("--environment", type=Path, help="also record the observed replay environment")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker:
        # A fresh interpreter removes inherited optimization and fixes hash ordering.
        result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker"],
                                cwd=HERE, env=clean_environment(), check=True,
                                capture_output=True, text=True, encoding="utf-8", timeout=180)
        payload = json.loads(result.stdout)
        text = json.dumps(payload["record"], indent=2, sort_keys=True) + "\n"
        if args.output:
            require(not args.output.resolve().is_relative_to(HERE), "output must be outside snapshot")
            args.output.write_text(text, encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(text)
        if args.environment:
            require(not args.environment.resolve().is_relative_to(HERE), "environment must be outside snapshot")
            args.environment.write_text(json.dumps(payload["environment"], indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8", newline="\n")
        return 0
    require(sys.version_info >= (3, 11) and sys.flags.optimize == 0, "Python 3.11+ without -O required")
    payload = {"record": replay(), "environment": {
        "schema": "rime.paper40.replay-environment.v1", "python": platform.python_version(),
        "implementation": platform.python_implementation(), "platform": platform.platform(),
        "dependencies": "Python standard library only", "python_optimize": 0,
        "python_hash_seed": "0", "network_required": False, "git_required": False,
    }}
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
