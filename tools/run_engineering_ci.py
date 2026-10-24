"""Explicit CI scopes; platform exclusions and skips never count as coverage."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT)]

NTFS_MODULES = ("tests.cross_language.test_a0_inventory_shadow", "tests.cross_language.test_a0_malecns_cache_shadow")
LOCAL_ONLY = ["full-carrier benchmarks and source-bound archived Solana captures",
              "historical 43/27-case full acceptance closures and executable digests",
              "remaining prototype/kernel/controller suites outside this selected CI profile"]


def command(out, name, argv, timeout=900):
    env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT/"src"), str(ROOT), env.get("PYTHONPATH", "")))
    env["PIP_FORCE_REINSTALL"] = "1"
    with (out/(name+".stdout.txt")).open("xb") as stdout, (out/(name+".stderr.txt")).open("xb") as stderr:
        subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=True, timeout=timeout)


def outcome(result):
    if not result.wasSuccessful(): return "FAILED"
    if result.skipped or result.testsRun == 0: return "UNRESOLVED_COVERAGE"
    return "PASS_SELECTED_CHECKS"


def test_suite(names, out, label):
    loader = unittest.TestLoader(); suite = unittest.TestSuite()
    for name in names: suite.addTests(loader.loadTestsFromName(name))
    with (out/(label+".unittest.log")).open("x", encoding="utf-8") as f:
        result = unittest.TextTestRunner(stream=f, verbosity=2).run(suite)
    record = {"status": outcome(result), "tests_run": result.testsRun,
              "skipped": [{"test": t.id(), "reason": r, "status": "NOT_EXECUTED"} for t, r in result.skipped],
              "failures": [t.id() for t, _ in result.failures], "errors": [t.id() for t, _ in result.errors]}
    (out/(label+".json")).write_text(json.dumps(record, indent=2)+"\n")
    if record["status"] != "PASS_SELECTED_CHECKS": raise RuntimeError("selected CI tests incomplete/failed: "+label)
    return record


@contextmanager
def fixture_temp_root(out):
    # Hosted Windows TEMP may contain RUNNER~1. That is correctly rejected by
    # A0; normal fixtures must start under an explicitly canonical job path.
    previous = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix="ntfs-fixtures-", dir=out.resolve()) as directory:
        tempfile.tempdir = str(Path(directory).resolve())
        try:
            yield Path(tempfile.tempdir)
        finally:
            tempfile.tempdir = previous


def ntfs_suite(out):
    with fixture_temp_root(out):
        return test_suite(NTFS_MODULES, out, "ntfs")


def guard():
    from applications.shared_a0_extraction_review.sof_gate import inventory
    path = ROOT/"evaluations/internal-runtime-a0-milestone/sof-compatibility-baseline.json"
    expected = json.loads(path.read_bytes())
    if expected["files"] != inventory(): raise ValueError("SOF protected bytes/membership drift")
    return {"status": "MATCHED_PROTECTED_BYTES", "files": len(expected["files"]),
            "historical_tests_reexecuted_by_this_check": False}


def crate(out, name, action):
    manifest = ROOT/"plugins/rust"/name/"Cargo.toml"
    if not manifest.with_name("Cargo.lock").is_file(): raise ValueError("lockfile required: "+name)
    command(out, name+"-"+action, ["cargo", action, "--locked", "--manifest-path", str(manifest)]+(["--release"] if action == "build" else []))


def run(profile, out):
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False)
    report = {"schema": "sof-runtime.internal-engineering-ci.v0", "profile": profile, "platform": sys.platform,
              "status": "INCOMPLETE", "not_executed": list(LOCAL_ONLY), "release_or_tag_created": False}
    try:
        report["sof_guard"] = guard()
        command(out, "python-environment", [sys.executable, "-m", "pip", "freeze"])
        if profile == "sof":
            from applications.shared_a0_extraction_review.sof_gate import run as sof_run
            tests = sof_run(out/"sof")
            report["tests"] = tests
            if tests["skipped"]: raise RuntimeError("SOF selected tests skipped")
            report["legacy_cross_language"] = test_suite(["tests.cross_language.test_plugin_protocol", "tests.cross_language.test_rust_positive_word_plugin"], out, "legacy-cross-language")
            report["not_executed"] += ["A0 NTFS controls: separate Windows job", "A0 portable Rust controls: separate portable job"]
        elif profile == "a0-portable":
            crate(out, "a0-mechanical-core", "test"); crate(out, "a0-inventory-inspector", "build")
            command(out, "core-format", ["cargo", "fmt", "--check", "--manifest-path", str(ROOT/"plugins/rust/a0-mechanical-core/Cargo.toml")])
            report["review_tests"] = test_suite(["tests.cross_language.test_shared_a0_extraction_review", "tests.cross_language.test_engineering_ci"], out, "portable-tests")
            report["ntfs"] = "NOT_EXECUTED_PLATFORM" if os.name != "nt" else "NOT_EXECUTED_PROFILE"
            report["not_executed"] += list(NTFS_MODULES)
            if os.name != "nt":
                binary = ROOT/"plugins/rust/a0-inventory-inspector/target/release/a0-inventory-inspector"
                completed = subprocess.run([str(binary), "unused-root", "unused-manifest", "unused-bindings"], capture_output=True, timeout=15)
                (out/"unsupported-backend.stdout.json").write_bytes(completed.stdout)
                (out/"unsupported-backend.stderr.txt").write_bytes(completed.stderr)
                value = json.loads(completed.stdout)
                if completed.returncode == 0 or value["status"] != "INCOMPLETE" or value["error"]["code"] != "UNSUPPORTED_PLATFORM":
                    raise ValueError("non-Windows backend failed to refuse unsupported observation")
                report["unsupported_backend_refusal"] = "PASS_REFUSAL_ONLY_NOT_NTFS_VALIDATION"
        elif profile == "a0-ntfs":
            if os.name != "nt": raise RuntimeError("UNRESOLVED: selected NTFS job requires Windows, not a platform skip")
            from applications.solana_inventory_shadow.reference import Handle
            with tempfile.TemporaryDirectory() as temporary:
                h = Handle(Path(temporary).resolve(), True)
                try: h.ntfs(); h.stamp()
                finally: h.close()
            # The frozen adapters deliberately build offline; populate only
            # their locked dependency caches before invoking the existing tests.
            for name in ("a0-mechanical-core", "a0-inventory-inspector", "solana-publication-recovery"):
                command(out, name+"-fetch", ["cargo", "fetch", "--locked", "--manifest-path", str(ROOT/"plugins/rust"/name/"Cargo.toml")])
            report["ntfs_tests"] = ntfs_suite(out)
            command(out, "ntfs-optimized", [sys.executable, "-B", "-O", "tools/run_engineering_ci.py", "_ntfs-tests", "--out", str(out/"optimized")])
            report["ntfs"] = "EXECUTED_LOCAL_NTFS_FIXTURES"
            report["not_executed"] += ["Windows process-counter attribution: retained local evidence, not this NTFS test menu"]
        elif profile == "_ntfs-tests":
            if os.name != "nt": raise RuntimeError("NTFS optimized subprocess requires Windows")
            report["ntfs_tests"] = ntfs_suite(out)
        else: raise ValueError("unknown CI profile")
        report["sof_guard_after"] = guard()
        report["status"] = "PASS_SELECTED_CHECKS"
    except Exception as e:
        report["status"] = "FAILED_OR_UNRESOLVED"; report["error"] = str(e)
        raise
    finally:
        (out/"ci-result.json").write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("profile", choices=("sof", "a0-portable", "a0-ntfs", "_ntfs-tests")); p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(); print(json.dumps(run(a.profile, a.out), sort_keys=True))
