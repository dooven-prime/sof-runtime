"""Recompute offline decisions and complete outputs from saved inputs, without attesting execution."""
import argparse
from pathlib import Path

from applications.solana_offchain_slice.common import canonical, file_sha, parse
from .reference import evaluate, check_success, require, equal
from .runner import HERE, bindings, tree_hashes


def verify(upstream, directory):
    root = Path(directory).resolve(strict=True)
    record = parse((root/"acceptance.v0.json").read_bytes())
    plan = parse((HERE/"plan.v0.json").read_bytes())
    require(record["status"] == "PASS_LOCAL_SOURCE_ADVANCEMENT_CONTROLS" and equal(record["plan"], plan)
            and equal(record["implementation_sha256"], bindings()), "CODE_PLAN_RECEIPT_IDENTITY")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    require(actual == set(record["files"]) | {"acceptance.v0.json"}, "RUN_INVENTORY")
    for name, digest in record["files"].items():
        path = root/name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and path.resolve().is_relative_to(root), "RECEIPT_PATH")
        require(not any(p.is_symlink() for p in [path, *path.parents] if p != root.parent) and file_sha(path) == digest, "SAVED_FILE_IDENTITY")
    upstream = Path(upstream).resolve(strict=True)
    require(file_sha(upstream) == plan["upstream_manifest_sha256"] == record["upstream"]["manifest_sha256"]
            and equal(tree_hashes(upstream.parent), record["upstream"]["files"]), "UPSTREAM_IDENTITY")
    cases = record["cases"]
    require(sorted(c["name"] for c in cases) == sorted(plan["required_cases"]) and len(cases) == len(plan["required_cases"]), "CASE_INVENTORY")
    counts = {}
    for case in cases:
        name = case["name"]; destination = root/case["state"]
        require(destination.resolve().is_relative_to(root), "STATE_PATH")
        req_path = root/"requests"/f"{name}.json"
        require(equal(parse(req_path.read_bytes()), case["request"]), "REQUEST_RECORD")
        # Evaluate successful calls against a hypothetical absent destination, not their now-published state.
        model_destination = destination if case["destination_preexisted"] else root/f".absent-model-output-{name}"
        require(case["destination_preexisted"] or not model_destination.exists(), "MODEL_DESTINATION")
        expected = evaluate(req_path, model_destination, record["implementation_sha256"]["advancement"]["rust_binary"])
        result = case["result"]
        require(result["status"] == expected["status"] and result["earliest_conflict_slot"] == expected["earliest_conflict_slot"], "MODEL_DECISION")
        output = root/"logs"/f"{name}.stdout.json"; request_log = root/"logs"/f"{name}.request.json"; error = root/"logs"/f"{name}.stderr.txt"
        require(equal(parse(output.read_bytes()), result) and file_sha(output) == case["process"]["stdout_sha256"]
                and request_log.read_bytes() == req_path.read_bytes() and file_sha(request_log) == case["process"]["request_sha256"]
                and file_sha(error) == case["process"]["stderr_sha256"] and error.stat().st_size == 0, "PROCESS_LOG_BINDING")
        if result["status"] == "COMPLETED_OFFLINE_ADVANCEMENT":
            require(case["process"]["returncode"] == 0 and result["published"] is True, "SUCCESS_PROTOCOL")
            check_success(expected, result, destination)
            require((root/"reference"/f"{name}.jsonl").read_bytes() == expected["projection_bytes"], "REFERENCE_OUTPUT")
        else:
            require(case["process"]["returncode"] != 0 and result["published"] is False and result["new_checkpoint_sha256"] is None and result["reason"], "REFUSAL_PROTOCOL")
            if not case["destination_preexisted"]:
                require(not destination.exists(), "REFUSAL_PUBLISHED_STATE")
            else:
                require({p.name for p in destination.iterdir()} == {"retain.txt"} and (destination/"retain.txt").read_text() == "retain", "EXISTING_DESTINATION")
            if result["status"] == "REJECTED_PREFIX_CONFLICT":
                require(result["affected_checkpoint_sha256"] == case["request"]["old_checkpoint_sha256"]
                        and result["compatibility"] == "INCOMPATIBLE_WITH_PROPOSED_CAPTURE", "CONFLICT_SCOPE")
        require(case["parent_state_unchanged"] and case["capture_unchanged"] and case["no_staging_leftovers"], "PRESERVATION_CONTROL")
        counts[result["status"]] = counts.get(result["status"], 0)+1
    require(not list(root.glob(".*.staging-*")), "STAGING_LEFTOVERS")
    require((root/"append_64/projection.jsonl").read_bytes() == (root/"full_64/projection.jsonl").read_bytes(), "CONTINUOUS_VS_FULL")
    return {"status": "VERIFIED_LOCAL_SAVED_SOURCE_TRANSITIONS", "cases": len(cases), "decisions": counts,
            "worker_reexecuted": False, "independent_execution_attestation": False, "live_provider_admission": False,
            "reorg_handling": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("upstream", type=Path); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); print(canonical(verify(args.upstream, args.directory)).decode())
