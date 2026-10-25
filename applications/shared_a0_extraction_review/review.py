"""Source-bound extraction controls; not a common runtime execution protocol."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

from .sof_gate import ROOT, canonical, command, inventory as protected_inventory, run as sof_run, sha

PRIOR = ROOT/"runs/a0-malecns-cache-shadow/acceptance-v0-final"
HERE = Path(__file__).resolve().parent
CORE = ROOT/"plugins/rust/a0-mechanical-core"
INSPECTOR = ROOT/"plugins/rust/a0-inventory-inspector"


def capture(directory):
    # The actual saved 0.2.0 closures must still verify before any extraction.
    from applications.malecns_cache_inventory_shadow.verify import verify
    prior_verified = verify(PRIOR)
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=False)
    paths = []
    for name in ("solana_inventory_shadow", "malecns_cache_inventory_shadow"):
        here = ROOT/"applications"/name
        paths += list(here.glob("*.py"))+[here/"CONTRACT.md", here/"plan.v0.json"]
    crate = ROOT/"plugins/rust/a0-inventory-inspector"
    paths += list((crate/"src").glob("*.rs"))+[crate/"Cargo.toml", crate/"Cargo.lock"]
    paths += [ROOT/"tests/cross_language"/n for n in ("test_a0_inventory_shadow.py", "test_a0_malecns_cache_shadow.py")]
    sources = {}
    for p in paths:
        name = p.relative_to(ROOT).as_posix(); target = directory/"prior-source"/name
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, target); sources[name] = sha(p)
    binary = crate/"target/release/a0-inventory-inspector.exe"
    shutil.copyfile(binary, directory/"prior-a0-observer.exe")
    before = protected_inventory(); tests = sof_run(directory/"sof-before")
    if before != protected_inventory(): raise ValueError("pre-capture SOF drift")
    record = {"schema": "sof-runtime.shared-a0-extraction-before.v0", "captured_client_date": "2026-10-25",
              "prior_verified": prior_verified, "prior_receipts": {str(p.relative_to(ROOT)): sha(p) for p in (PRIOR/"acceptance.v0.json", PRIOR/"solana-regression/acceptance.v0.json")},
              "prior_sources": sources, "prior_binary_sha256": sha(binary), "sof_files": before, "sof_tests": tests}
    (directory/"before.json").write_bytes(canonical(record)); return {"captured": True, "protected_files": len(before), "sof_tests": tests["count"]}


def capture_snapshot(directory, snapshot):
    """Retry only the SOF baseline after an environmental harness failure.

    Old candidate bytes come from the source/executable saved before extraction,
    and are checked against their already accepted receipts, not current source.
    """
    snapshot = Path(snapshot).resolve(); directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copytree(snapshot/"prior-source", directory/"prior-source")
    shutil.copyfile(snapshot/"prior-a0-observer.exe", directory/"prior-a0-observer.exe")
    sources = {p.relative_to(directory/"prior-source").as_posix(): sha(p) for p in (directory/"prior-source").rglob("*") if p.is_file()}
    before = protected_inventory()
    attempts = []
    if (snapshot/"before.json").exists():
        prior_capture = json.loads((snapshot/"before.json").read_bytes())
        attempts = prior_capture.get("environmental_attempts", [])
        if not attempts and "failed_baseline_files" in prior_capture:
            attempts = [{"root_local": prior_capture["failed_baseline_local"], "files": prior_capture["failed_baseline_files"]}]
    attempts = attempts + [{"root_local": str(snapshot), "files": {p.relative_to(snapshot/"sof-before").as_posix(): sha(p) for p in (snapshot/"sof-before").rglob("*") if p.is_file()}}]
    r = {"schema": "sof-runtime.shared-a0-extraction-before.v0", "captured_client_date": "2026-10-25",
         "baseline_retry_reason": "source checkout and venv wheel installation launch profile made explicit; no protected code changed",
         "environmental_attempts": attempts,
         "failed_baseline_local": str(snapshot),
         "failed_baseline_files": {p.relative_to(snapshot/"sof-before").as_posix(): sha(p) for p in (snapshot/"sof-before").rglob("*") if p.is_file()},
         "prior_receipts": {str(p.relative_to(ROOT)): sha(p) for p in (PRIOR/"acceptance.v0.json", PRIOR/"solana-regression/acceptance.v0.json")},
         "prior_sources": sources, "prior_binary_sha256": sha(directory/"prior-a0-observer.exe"), "sof_files": before}
    # Validate the captured old implementation before running the corrected gate.
    (directory/"before.json").write_bytes(canonical(r)); check_before(directory)
    r["sof_tests"] = sof_run(directory/"sof-before")
    if before != protected_inventory(): raise ValueError("protected baseline drift")
    (directory/"before.json").write_bytes(canonical(r))
    return {"captured": True, "protected_files": len(before), "sof_tests": r["sof_tests"]["count"]}


def check_before(directory):
    directory = Path(directory); r = json.loads((directory/"before.json").read_bytes())
    if r["sof_files"] != protected_inventory(): raise ValueError("SOF protected closure changed")
    if "failed_baseline_files" in r:
        failed = Path(r["failed_baseline_local"])/"sof-before"
        if r["failed_baseline_files"] != {p.relative_to(failed).as_posix(): sha(p) for p in failed.rglob("*") if p.is_file()}: raise ValueError("failed baseline evidence changed")
    for attempt in r.get("environmental_attempts", []):
        failed = Path(attempt["root_local"])/"sof-before"
        if attempt["files"] != {p.relative_to(failed).as_posix(): sha(p) for p in failed.rglob("*") if p.is_file()}: raise ValueError("environmental attempt evidence changed")
    if sha(directory/"prior-a0-observer.exe") != r["prior_binary_sha256"]: raise ValueError("prior executable not preserved")
    for name, digest in r["prior_sources"].items():
        if sha(directory/"prior-source"/name) != digest: raise ValueError("prior source snapshot changed")
    for name, digest in r["prior_receipts"].items():
        if sha(ROOT/name) != digest: raise ValueError("old receipt overwritten")
    # Bind the snapshot to the exact previously accepted implementation, not
    # merely to a new list of files captured after the refactor.
    for name in r["prior_receipts"]:
        prior = json.loads((ROOT/name).read_bytes())
        for path, expected in prior["implementation_sha256"]["shadow"].items():
            if path == "rust_binary": actual = sha(directory/"prior-a0-observer.exe")
            elif path == "python_executable": actual = sha(sys.executable)
            else: actual = sha(directory/"prior-source"/path) if path in r["prior_sources"] else sha(ROOT/path)
            if actual != expected: raise ValueError("snapshot/old receipt mismatch: "+path)
    return r


def core_boundary():
    source = {p.relative_to(CORE).as_posix(): sha(p) for p in sorted((CORE/"src").rglob("*.rs"))}
    text = (CORE/"src/lib.rs").read_text()
    if set(re.findall(r"^pub mod (\w+);", text, re.M)) != {"identity", "codec", "inventory"}: raise ValueError("core module boundary enlarged")
    if "publish = false" not in (CORE/"Cargo.toml").read_text(): raise ValueError("core became publishable")
    all_text = "\n".join(p.read_text() for p in (CORE/"src").rglob("*.rs"))
    for forbidden in ("quarantine", "checkpoint_inheritance", "retry_admission", "source_approval", "Solana", "MaleCNS", "CACHE_HIT", '"PASS"'):
        if forbidden in all_text: raise ValueError("application policy in core: "+forbidden)
    for forbidden in ("std::process", "std::thread", "File::create", ".write_all(", "fs::rename", "fs::remove", "create_new("):
        if forbidden in all_text: raise ValueError("writer/process mechanism entered core: "+forbidden)
    if sorted(p.name for p in (INSPECTOR/"src").iterdir()) != ["lib.rs", "main.rs"]: raise ValueError("duplicate inspector mechanism source remains")
    if 'a0-mechanical-core = { path = "../a0-mechanical-core" }' not in (INSPECTOR/"Cargo.toml").read_text(): raise ValueError("adapter not linked to shared core")
    # A lexical stop control, not a whole-program proof of non-interference.
    return {"top_level_modules": ["identity", "codec", "inventory"], "files": source,
            "no_domain_policy_or_writer_lexical_control": True, "independent_python_reference_retained": True}


def compare_runs(old_file, new_file):
    old, new = (json.loads(Path(p).read_bytes()) for p in (old_file, new_file))
    old_cases, new_cases = ({c["name"]: c for c in r["cases"]} for r in (old, new))
    if set(old_cases) != set(new_cases) or len(old_cases) != len(old["cases"]) or len(new_cases) != len(new["cases"]): raise ValueError("control matrix changed")
    count = 0; paired = 0
    for name, a in old_cases.items():
        b = new_cases[name]
        if a["kind"] != b["kind"]: raise ValueError("control kind changed")
        for key in ("observation", "fresh", "later"):
            if (key in a) != (key in b): raise ValueError("observation boundary changed")
            if key not in a: continue
            x, y = a[key], b[key]; paired += 1
            for f in ("status", "matching_observation_admissible", "application_decision"):
                if x[f] != y[f]: raise ValueError(f"{name}: {f} changed")
            for f in ("actually_killed", "changed_during_observation"):
                if x["process"][f] != y["process"][f]: raise ValueError("fault boundary changed")
            if (x["result"] is None) != (y["result"] is None): raise ValueError("partial result admitted")
            if x["result"] is None: continue
            for f in ("status", "source_trust", "application_decision", "validity"):
                if x["result"].get(f) != y["result"].get(f): raise ValueError("result semantics/lifetime changed")
            if "error" in x["result"]:
                for f in ("class", "code"):
                    if x["result"]["error"][f] != y["result"].get("error", {}).get(f): raise ValueError("failure classification changed: "+name)
            if x["status"] == "MATCHED_BYTES":
                for f in ("entries", "manifest_utf8", "manifest_sha256", "bindings_sha256", "byte_passes", "backend"):
                    if x["result"]["inspection"][f] != y["result"]["inspection"][f]: raise ValueError("inventory/codec bytes changed: "+name+":"+f)
                count += 1
        if a["kind"] == "semantic-boundary":
            if "original_application_rejection" in a:
                if a["original_application_rejection"] != b["original_application_rejection"]: raise ValueError("Solana semantic negative changed")
            elif a["original_application"]["result"] != b["original_application"]["result"]: raise ValueError("cache semantic negative changed")
    return {"cases": len(new_cases), "paired_observations": paired, "byte_identical_matching_observations": count,
            "failure_classes_and_codes_equal": True, "timing_pid_file_ids_not_compared": True}


def source_binding():
    paths = list(HERE.glob("*.py"))+[ROOT/"docs/internal/SOF_COMPATIBILITY_GUARD_V0.md", ROOT/"docs/internal/SHARED_A0_EXTRACTION_REVIEW_V0.md",
                                      ROOT/"tests/cross_language/test_shared_a0_extraction_review.py"]
    for crate in (CORE, INSPECTOR): paths += list((crate/"src").rglob("*.rs"))+[crate/"Cargo.toml", crate/"Cargo.lock"]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def accept(before_dir, directory):
    from applications.solana_inventory_shadow.evidence import inventory as evidence_inventory
    from applications.malecns_cache_inventory_shadow.verify import verify as verify_cache
    before_dir = Path(before_dir).resolve(); before = check_before(before_dir)
    if before.get("sof_tests", {}).get("successful") is not True:
        raise ValueError("SOF before gate is incomplete or failed; extraction acceptance is not admissible")
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=False)
    boundary = core_boundary(); sources = source_binding()
    command(directory, "review-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/cross_language", "-p", "test_shared_a0_extraction_review.py", "-v"])
    command(directory, "core-tests", ["cargo", "test", "--locked", "--offline", "--manifest-path", str(CORE/"Cargo.toml")])
    command(directory, "core-format", ["cargo", "fmt", "--check", "--manifest-path", str(CORE/"Cargo.toml")])
    # Existing acceptance programs own all application checks, including real kills.
    command(directory, "shadows", [sys.executable, "-B", "-m", "applications.malecns_cache_inventory_shadow.acceptance", str(directory/"shadows")], timeout=600)
    for optimized in (False, True):
        command(directory, "saved"+("-O" if optimized else ""), [sys.executable, "-B"]+(["-O"] if optimized else [])+
                ["-m", "applications.malecns_cache_inventory_shadow.verify", str(directory/"shadows")], timeout=300)
    validation = verify_cache(directory/"shadows")
    comparisons = {"solana": compare_runs(PRIOR/"solana-regression/acceptance.v0.json", directory/"shadows/solana-regression/acceptance.v0.json"),
                   "malecns": compare_runs(PRIOR/"acceptance.v0.json", directory/"shadows/acceptance.v0.json")}
    tests = sof_run(directory/"sof-after", wheel=True)
    if tests != before["sof_tests"]: raise ValueError("SOF test identities/outcomes/skips changed")
    if source_binding() != sources or check_before(before_dir) != before: raise ValueError("source or protected closure drift")
    # All writes below are review-local evidence, never application artifacts.
    r = {"schema": "sof-runtime.shared-a0-extraction-review.v0", "status": "PASS_LOCAL_SHARED_A0_EXTRACTION_EXPERIMENT",
         "client_date": "2026-10-25", "before_local": str(before_dir), "before_sha256": sha(before_dir/"before.json"),
         "sources": sources, "core_boundary": boundary, "comparisons": comparisons, "shadow_verification": validation,
         "sof_compatibility": {"protected_files": len(before["sof_files"]), "tests": tests["count"], "skipped": tests["skipped"],
                               "protected_bytes_equal": True, "test_outcomes_equal": True, "installed_wheel_checked": True},
         "observer_executable_sha256": sha(INSPECTOR/"target/release/a0-inventory-inspector.exe"),
         "boundary": {"public_api": False, "production_paths_migrated": False, "b_or_c_extracted": False,
                      "application_pass_issued_by_core": False, "independent_execution_attestation": False},
         "files": evidence_inventory(directory, exclude=("review.v0.json",))}
    (directory/"review.v0.json").write_bytes(canonical(r)); return {k:r[k] for k in ("status", "comparisons", "sof_compatibility", "boundary")}


def verify(directory):
    from applications.solana_inventory_shadow.evidence import inventory as evidence_inventory
    from applications.malecns_cache_inventory_shadow.verify import verify as verify_cache
    directory = Path(directory).resolve(); r = json.loads((directory/"review.v0.json").read_bytes())
    if r["status"] != "PASS_LOCAL_SHARED_A0_EXTRACTION_EXPERIMENT" or r["sources"] != source_binding() or r["core_boundary"] != core_boundary(): raise ValueError("review source/boundary drift")
    before_dir = Path(r["before_local"]); before = check_before(before_dir)
    if sha(before_dir/"before.json") != r["before_sha256"]: raise ValueError("before capture changed")
    if r["files"] != evidence_inventory(directory, exclude=("review.v0.json",)): raise ValueError("review evidence changed")
    if json.loads((directory/"sof-after/tests/test-result.json").read_bytes()) != before["sof_tests"]: raise ValueError("SOF test closure changed")
    if r["shadow_verification"] != verify_cache(directory/"shadows"): raise ValueError("shadow closure changed")
    for name, old, new in (("solana", PRIOR/"solana-regression/acceptance.v0.json", directory/"shadows/solana-regression/acceptance.v0.json"),
                           ("malecns", PRIOR/"acceptance.v0.json", directory/"shadows/acceptance.v0.json")):
        if r["comparisons"][name] != compare_runs(old, new): raise ValueError("comparison drift")
    if r["observer_executable_sha256"] != sha(INSPECTOR/"target/release/a0-inventory-inspector.exe"): raise ValueError("new observer identity changed")
    return {"status": "VERIFIED_LOCAL_SAVED_SHARED_A0_EXTRACTION", "rust_reexecuted": False,
            "compatibility_tests_reexecuted": False, "independent_execution_attestation": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("mode", choices=["capture", "capture-snapshot", "accept", "verify"]); p.add_argument("directory", type=Path)
    p.add_argument("--before", type=Path)
    p.add_argument("--snapshot", type=Path)
    args = p.parse_args()
    if args.mode == "capture": result = capture(args.directory)
    elif args.mode == "capture-snapshot":
        if args.snapshot is None: p.error("capture-snapshot requires preserved --snapshot")
        result = capture_snapshot(args.directory, args.snapshot)
    elif args.mode == "verify": result = verify(args.directory)
    else:
        if args.before is None: p.error("accept requires an already frozen --before capture")
        result = accept(args.before, args.directory)
    print(json.dumps(result, sort_keys=True))
