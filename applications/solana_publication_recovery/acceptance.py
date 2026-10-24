"""Fixed-input real-kill publication recovery matrix; no performance claim."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import subprocess
import sys

from applications.solana_offchain_slice.common import canonical, file_sha, parse
from applications.solana_source_advancement.fixtures import corpus, request
from .reference import check, equal_state
from .runner import HERE, ROOT, POINTS, binary, bindings, build, control, invoke, tree_hashes, write_request


def run(upstream, directory):
    build(); upstream = Path(upstream).resolve(strict=True)
    plan = parse((HERE/"plan.v0.json").read_bytes())
    if file_sha(upstream) != plan["upstream_manifest_sha256"]: raise ValueError("not the frozen upstream capture")
    root = Path(directory).resolve(); root.mkdir(parents=True, exist_ok=False)
    (root/"requests").mkdir(); before = bindings(); upstream_before = tree_hashes(upstream.parent)
    for optimized in (False, True):
        name = "tests-optimized" if optimized else "tests"
        env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
        args = [sys.executable, "-B"]+(["-O"] if optimized else [])+["-m", "unittest", "discover", "-s", "tests/cross_language", "-p", "test_solana_publication_recovery.py", "-v"]
        with (root/f"{name}.stdout.txt").open("xb") as out, (root/f"{name}.stderr.txt").open("xb") as err:
            subprocess.run(args, cwd=ROOT, env=env, stdout=out, stderr=err, check=True, timeout=300)
    d = corpus(upstream, root/"corpus")
    initial_req = write_request(root/"requests/init.json", request(d["policy"], d["captures"]["a-16"], "init"))
    initial, init_process = invoke(initial_req, root/"parent", root/"logs", "init")
    init_check = check(initial_req, root/"parent", initial)
    parent_before, corpus_before = tree_hashes(root/"parent"), tree_hashes(root/"corpus")
    cases = []; clean = {}; requests = {}

    def protected():
        if tree_hashes(root/"parent") != parent_before or tree_hashes(root/"corpus") != corpus_before:
            raise ValueError("parent/source modified")

    for mode, candidate in (("append", "a-32"), ("reapprove", "b-full")):
        req = write_request(root/f"requests/{mode}.json", request(d["policy"], d["captures"][candidate], mode,
            d["captures"]["a-16"], root/"parent", initial["advancement"]["new_checkpoint_sha256"]))
        requests[mode] = req; dest = root/f"clean-{mode}"
        result, process = invoke(req, dest, root/"logs", f"clean-{mode}")
        checked = check(req, dest, result); clean[mode] = dest
        cases.append({"name": f"clean-{mode}", "kind": "clean", "request": str(req.relative_to(root)),
            "destination": dest.name, "result": result, "process": process, "python_check": checked})
        for point in POINTS:
            name = f"{mode}-{point}"; dest = root/name
            _, kill_process = invoke(req, dest, root/"logs", name+"-kill", point)
            visible_after_kill = dest.exists()
            should_be_visible = point in ("after_publication", "receipt_partial", "receipt_published")
            if visible_after_kill != should_be_visible: raise ValueError("publication boundary disagreement")
            # Persist the actual interrupted inventory before recovery consumes it.
            interrupted = {"control": tree_hashes(control(dest)), "destination": tree_hashes(dest) if dest.exists() else None}
            (root/"logs"/f"{name}.interrupted.json").write_bytes(canonical(interrupted))
            protected()
            result, resume_process = invoke(req, dest, root/"logs", name+"-resume")
            checked = check(req, dest, result); equal_state(clean[mode], dest)
            receipt_raw = (control(dest)/"receipt.json").read_bytes()
            retry, retry_process = invoke(req, dest, root/"logs", name+"-retry")
            check(req, dest, retry)
            if (control(dest)/"receipt.json").read_bytes() != receipt_raw or retry["recovery"] != "REPLAYED_PUBLISHED":
                raise ValueError("retry identity changed")
            protected()
            cases.append({"name": name, "kind": "kill", "request": str(req.relative_to(root)), "destination": dest.name,
                "fault_point": point, "visible_after_kill": visible_after_kill, "kill_process": kill_process,
                "result": result, "retry": retry, "resume_process": resume_process, "retry_process": retry_process,
                "python_check": checked, "full_state_bytes_equal_clean": True,
                "receipt_bytes_equal_on_retry": True, "parent_and_captures_unchanged": True})

    req = requests["reapprove"]; dest = root/"repeated-interruption"; kills = []
    for i, point in enumerate(("transition_partial", "checkpoint_partial", "after_publication", "receipt_partial")):
        _, process = invoke(req, dest, root/"logs", f"repeat-{i}", point); kills.append(process); protected()
    result, process = invoke(req, dest, root/"logs", "repeat-resume")
    checked = check(req, dest, result); equal_state(clean["reapprove"], dest)
    cases.append({"name": dest.name, "kind": "repeated-kill", "request": str(req.relative_to(root)), "destination": dest.name,
        "kills": kills, "result": result, "process": process, "python_check": checked, "full_state_bytes_equal_clean": True})

    for kind in ("staged-segment", "pending-transition", "ready", "published-checkpoint", "published-segment", "receipt", "foreign-output", "request-identity"):
        name = "refuse-"+kind; dest = root/name; req = requests["append"]
        kill_process = None
        if kind in ("staged-segment", "pending-transition", "ready", "request-identity"):
            point = {"staged-segment": "segment_published", "pending-transition": "transition_partial",
                     "ready": "ready_published", "request-identity": "stage_created"}[kind]
            _, kill_process = invoke(req, dest, root/"logs", name+"-kill", point)
            if kind == "staged-segment": next((control(dest)/"stage").glob("slot-*.jsonl")).write_bytes(b"corrupt\n")
            elif kind == "pending-transition": (control(dest)/"stage/transition.json.pending").write_bytes(b"invalid prefix")
            elif kind == "ready": (control(dest)/"ready.json").write_bytes(b"{}")
            else:
                value = parse(req.read_bytes()); value["mode"] = "reapprove"
                req = write_request(root/f"requests/{name}.json", value)
        elif kind == "foreign-output":
            dest.mkdir(); (dest/"retain.txt").write_bytes(b"foreign state must remain")
        else:
            success, _ = invoke(req, dest, root/"logs", name+"-prepare"); check(req, dest, success)
            if kind == "published-checkpoint": (dest/"checkpoint.json").unlink()
            elif kind == "published-segment": next(dest.glob("slot-*.jsonl")).write_bytes(b"corrupt\n")
            else: (control(dest)/"receipt.json").write_bytes(b"{}")
        old = tree_hashes(dest) if dest.exists() else None
        stage = tree_hashes(control(dest)/"stage") if (control(dest)/"stage").exists() else None
        actual, process = invoke(req, dest, root/"logs", name+"-deny")
        if actual["status"] != "UNRESOLVED" or actual["publication_confirmed"] is not False or not actual["reason"]:
            raise ValueError("fault admitted publication")
        if (tree_hashes(dest) if dest.exists() else None) != old: raise ValueError("refusal changed final state")
        if stage is not None and tree_hashes(control(dest)/"stage") != stage: raise ValueError("refusal erased staging evidence")
        protected()
        cases.append({"name": name, "kind": "refusal", "request": str(req.relative_to(root)), "destination": dest.name,
            "kill_process": kill_process, "result": actual, "process": process, "existing_output_preserved": True,
            "unpublished_evidence_preserved": True, "parent_and_captures_unchanged": True})

    protected()
    if before != bindings() or upstream_before != tree_hashes(upstream.parent): raise ValueError("implementation/upstream changed")
    record = {"schema": "sof-runtime.publication-recovery-acceptance.v0", "status": "PASS_LOCAL_PUBLICATION_RECOVERY",
        "created_utc": datetime.now(timezone.utc).isoformat(), "implementation_sha256": before, "plan": plan,
        "upstream": {"path": str(upstream), "manifest_sha256": file_sha(upstream), "files": upstream_before},
        "environment": {"platform": platform.platform(), "python": sys.version},
        "initial": {"request": "requests/init.json", "destination": "parent", "result": initial, "process": init_process, "python_check": init_check},
        "cases": cases, "parent_files": parent_before, "corpus_files": corpus_before,
        "controls": {"ordinary_and_optimized_tests": "PASS",
            "real_kills": sum(1 for c in cases if c.get("kill_process", {}) and c["kill_process"]["actually_killed"])+len(kills), "matrix_kills": 36,
            "real_capture_modes": ["append", "reapprove"], "complete_python_projection": "PASS",
            "bytewise_state_and_retry_receipt": "PASS", "parent_and_input_preservation": "PASS"},
        "scope": "LOCAL_PROCESS_KILL_NOT_POWER_LOSS_REORG_OR_EXTERNAL_ATTESTATION",
        "files": {p.relative_to(root).as_posix(): file_sha(p) for p in sorted(root.rglob("*")) if p.is_file()}}
    (root/"acceptance.v0.json").write_bytes(canonical(record))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("upstream", type=Path); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); r = run(args.upstream, args.directory)
    print(canonical({"status": r["status"], "cases": len(r["cases"]), "controls": r["controls"]}).decode())
