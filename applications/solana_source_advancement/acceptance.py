"""Offline, correctness-only source advancement controls with separate Python decisions."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from applications.solana_incremental_replay.reference import projection
from .fixtures import corpus, request
from .reference import evaluate, check_success
from .runner import HERE, ROOT, binary, bindings, build, invoke, tree_hashes


def run(upstream, directory):
    build()
    upstream = Path(upstream).resolve(strict=True)
    root = Path(directory).resolve(); root.mkdir(parents=True, exist_ok=False)
    (root/"requests").mkdir(); (root/"reference").mkdir()
    plan = parse((HERE/"plan.v0.json").read_bytes())
    if file_sha(upstream) != plan["upstream_manifest_sha256"]:
        raise ValueError("not the frozen upstream capture")
    before = bindings(); upstream_files = tree_hashes(upstream.parent)
    d = corpus(upstream, root/"corpus")
    for optimized in (False, True):
        args = [sys.executable, "-B"]+(["-O"] if optimized else [])+["-m", "unittest", "discover", "-s", "tests/cross_language", "-p", "test_solana_source_advancement.py", "-v"]
        env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
        name = "controls-optimized" if optimized else "controls"
        with (root/f"{name}.stdout.txt").open("xb") as out, (root/f"{name}.stderr.txt").open("xb") as err:
            subprocess.run(args, cwd=ROOT, env=env, stdout=out, stderr=err, check=True, timeout=180)
    cases = []

    def case(name, req, destination=None):
        destination = root/name if destination is None else Path(destination)
        request_path = root/"requests"/f"{name}.json"; request_path.write_bytes(canonical(req))
        predicted = evaluate(request_path, destination, file_sha(binary()))
        old_state = Path(req["old_state"]) if req["old_state"] else None
        old_before = tree_hashes(old_state) if old_state else None
        capture_before = tree_hashes(Path(req["candidate_manifest"]).parent)
        existed = tree_hashes(destination) if destination.exists() else None
        actual, process = invoke(req, destination, root/"logs", name, timeout=plan["process_timeout_seconds"])
        if actual["status"] != predicted["status"] or actual["earliest_conflict_slot"] != predicted["earliest_conflict_slot"]:
            raise ValueError(f"Rust/Python decision mismatch: {name}: {actual}, {predicted}")
        if actual["status"] == "COMPLETED_OFFLINE_ADVANCEMENT":
            check_success(predicted, actual, destination)
            (root/"reference"/f"{name}.jsonl").write_bytes(predicted["projection_bytes"])
        else:
            if actual["published"] or actual["new_checkpoint_sha256"] is not None or not actual["reason"]:
                raise ValueError("refusal claimed publication")
            if existed is None and destination.exists():
                raise ValueError("refused transition published state")
            if existed is not None and tree_hashes(destination) != existed:
                raise ValueError("existing destination was overwritten")
            if actual["status"] == "REJECTED_PREFIX_CONFLICT" and actual["affected_checkpoint_sha256"] != req["old_checkpoint_sha256"]:
                raise ValueError("conflict checkpoint binding")
        if old_state and tree_hashes(old_state) != old_before:
            raise ValueError("parent state was modified")
        if tree_hashes(Path(req["candidate_manifest"]).parent) != capture_before:
            raise ValueError("candidate capture was modified")
        if list(root.glob(".*.staging-*")):
            raise ValueError("unpublished stage survived normal validation refusal")
        summary = {"status": predicted["status"], "reason": predicted["reason"], "earliest_conflict_slot": predicted["earliest_conflict_slot"]}
        if predicted["status"] == "COMPLETED_OFFLINE_ADVANCEMENT":
            summary.update(compatibility=predicted["compatibility"], projection_sha256=sha(predicted["projection_bytes"]),
                           projection_bytes=len(predicted["projection_bytes"]), inherited_slots=predicted["inherited_slots"], new_slots=predicted["new_slots"],
                           candidate_prefix_decoded_slots=predicted["prefix_decode_slots"], candidate_suffix_decoded_slots=predicted["suffix_decode_slots"])
        cases.append({"name": name, "request": req, "state": destination.relative_to(root).as_posix(),
            "destination_preexisted": existed is not None, "parent_state_unchanged": True, "capture_unchanged": True,
            "no_staging_leftovers": True, "python_model": summary, "result": actual, "process": process})
        return actual

    a16, a32, a64 = (d["captures"][f"a-{n}"] for n in plan["windows"])
    initial = case("initial", request(d["policy"], a16, "init"))
    second = case("append_32", request(d["policy"], a32, "append", a16, root/"initial", initial["new_checkpoint_sha256"]))
    third = case("append_64", request(d["policy"], a64, "append", a32, root/"append_32", second["new_checkpoint_sha256"]))
    full = case("full_64", request(d["policy"], a64, "init"))
    if (root/"append_64/projection.jsonl").read_bytes() != (root/"full_64/projection.jsonl").read_bytes() or (root/"full_64/projection.jsonl").read_bytes() != projection(upstream):
        raise ValueError("advancement/full/upstream projection difference")
    if initial["source_identity_sha256"] != third["source_identity_sha256"] or initial["execution_identity_sha256"] != third["execution_identity_sha256"] or third["new_checkpoint_sha256"] == full["new_checkpoint_sha256"]:
        raise ValueError("three identities collapsed")
    old_args = (a64, root/"append_64", third["new_checkpoint_sha256"])
    for name, capture_name, mode in (("credential_change_without_reapproval", "b-full", "append"),
                                      ("credential_change_reapproved", "b-full", "reapprove"),
                                      ("same_source_raw_revision_without_reapproval", "raw-revision", "append"),
                                      ("same_source_raw_revision_reapproved", "raw-revision", "reapprove"),
                                      ("prefix_conflict", "conflict", "reapprove"),
                                      ("listed_status_conflict", "listed-conflict", "reapprove"),
                                      ("unknown_credential", "unknown", "reapprove")):
        case(name, request(d["policy"], d["captures"][capture_name], mode, *old_args))
    for name, member in (("missing_admission", "admission.json"), ("missing_payload", f"block-{plan['windows'][-1]-1+parse(upstream.read_bytes())['start_slot']}.response.json")):
        folder = root/f"input-{name}"; shutil.copytree(a64.parent, folder); (folder/member).unlink()
        case(name, request(d["policy"], folder/"manifest.json", "append", *old_args))
    case("continuity_failure", request(d["policy"], d["captures"]["bad-continuity"], "append", a32, root/"append_32", second["new_checkpoint_sha256"]))
    case("range_shrink", request(d["policy"], a16, "append", *old_args))
    req = request(d["policy"], a64, "append", a32, root/"append_32", "0"*64)
    case("bad_parent_anchor", req)
    req = request(d["policy"], a64, "append", a32, root/"append_32", second["new_checkpoint_sha256"]); req["policy_sha256"] = "0"*64
    case("bad_policy_anchor", req)
    corrupt = root/"input-corrupt-parent"; shutil.copytree(root/"append_32", corrupt)
    first_slot = parse(upstream.read_bytes())["start_slot"]
    (corrupt/f"slot-{first_slot}.jsonl").write_bytes(b"corrupt\n")
    case("corrupt_parent_segment", request(d["policy"], a64, "append", a32, corrupt, second["new_checkpoint_sha256"]))
    foreign = root/"input-foreign-parent"; shutil.copytree(root/"append_32", foreign)
    cp = foreign/"checkpoint.json"; frame = parse(cp.read_bytes()); frame["body"]["execution_identity"]["program_sha256"] = "f"*64
    frame["body_sha256"] = sha(canonical(frame["body"])); cp.write_bytes(canonical(frame))
    case("foreign_execution", request(d["policy"], a64, "append", a32, foreign, file_sha(cp)))
    occupied = root/"destination_exists"; occupied.mkdir(); (occupied/"retain.txt").write_text("retain")
    case("destination_exists", request(d["policy"], a64, "append", a32, root/"append_32", second["new_checkpoint_sha256"]), occupied)
    if sorted(c["name"] for c in cases) != sorted(plan["required_cases"]):
        raise ValueError("acceptance cases differ from plan")
    if before != bindings() or upstream_files != tree_hashes(upstream.parent):
        raise ValueError("code or frozen source changed")
    record = {"schema": "sof-runtime.source-advancement-acceptance.v0", "status": "PASS_LOCAL_SOURCE_ADVANCEMENT_CONTROLS",
        "created_utc": datetime.now(timezone.utc).isoformat(), "implementation_sha256": before, "plan": plan,
        "upstream": {"manifest_path_local": str(upstream), "manifest_sha256": file_sha(upstream), "files": upstream_files},
        "environment": {"python": sys.version, "platform": platform.platform()}, "cases": cases,
        "controls": {"ordinary_and_optimized_unittest": "PASS", "separate_python_decisions_and_full_outputs": "PASS",
                     "continuous_vs_full_projection": "PASS", "parent_state_preservation": "PASS", "refusals_publish_no_new_state": "PASS"},
        "scope": "OFFLINE_REAL_CAPTURE_DERIVED_CONTROLS_NOT_PROVIDER_ADMISSION_OR_REORG",
        "files": {p.relative_to(root).as_posix(): file_sha(p) for p in sorted(root.rglob("*")) if p.is_file()}}
    (root/"acceptance.v0.json").write_bytes(canonical(record))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("upstream", type=Path); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); result = run(args.upstream, args.directory)
    print(canonical({"status": result["status"], "cases": [{"name": c["name"], "status": c["result"]["status"],
        "earliest_conflict_slot": c["result"]["earliest_conflict_slot"], "reason": c["result"]["reason"]} for c in result["cases"]]}).decode())
