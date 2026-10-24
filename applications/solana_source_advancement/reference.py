"""Independent full Python projection model of the offline transition rules."""
from pathlib import Path

from applications.solana_offchain_slice.common import canonical, confined, file_sha, parse, sha
from applications.solana_incremental_replay.reference import load, segments


class Refusal(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise Refusal(code)


def equal(a, b):
    return canonical(a) == canonical(b)


def bundle(path, policy):
    path = Path(path); m, digest = load(path); root = path.parent.resolve()
    require(m["capture_kind"] == "synthetic_control" and m["offline_derivation"]["upstream_manifest_sha256"] == policy["upstream_manifest_sha256"]
            and m["offline_derivation"]["not_an_rpc_capture"] is True, "OFFLINE_CAPTURE_DERIVATION_REQUIRED")
    require((root/"credential.json").exists(), "SOURCE_CREDENTIAL_EVIDENCE_MISSING")
    cpath = confined(root, "credential.json"); c = parse(cpath.read_bytes()); csha = file_sha(cpath)
    require(c["schema"] == "sof-runtime.offline-source-credential.v0" and c["genesis"] == m["genesis"] == policy["genesis"]
            and c["locator"] == m["source"] and c["locator"].startswith("offline://") and c["revision"]
            and c["evidence_class"] == "LOCAL_DERIVED_CAPTURE_FIXTURE" and c["provider_authentication_claimed"] is False
            and type(c["scope"]["start_slot"]) is int and type(c["scope"]["end_slot"]) is int
            and c["scope"]["start_slot"] <= m["start_slot"] <= m["end_slot"] <= c["scope"]["end_slot"], "SOURCE_CREDENTIAL_BINDING")
    require(csha in policy["credential_sha256"], "SOURCE_CREDENTIAL_NOT_ALLOWED")
    require((root/"admission.json").exists(), "CAPTURE_ADMISSION_EVIDENCE_MISSING")
    apath = confined(root, "admission.json"); a = parse(apath.read_bytes())
    require(a["schema"] == "sof-runtime.offline-capture-admission.v0" and a["manifest_sha256"] == digest
            and a["credential_sha256"] == csha and a["upstream_manifest_sha256"] == policy["upstream_manifest_sha256"]
            and a["qualification"] == "LOCAL_TEST_PERMISSION_NOT_PROVIDER_TRUST", "CAPTURE_ADMISSION_BINDING")
    require(file_sha(apath) in policy["admission_sha256"], "CAPTURE_ADMISSION_NOT_ALLOWED")
    source = {"schema": "sof-runtime.source-identity.v0", "credential_sha256": csha, "locator": c["locator"],
              "genesis": c["genesis"], "evidence_class": c["evidence_class"]}
    return {"manifest": m, "manifest_sha256": digest, "credential_sha256": csha, "source": source}


def entry(m, segment):
    slot = segment["slot"]; item = m["rpc"].get(f"block-{slot}")
    return {"slot": slot, "sha256": sha(segment["bytes"]), "bytes": len(segment["bytes"]), "records": len(segment["records"]),
            "input_sha256": item["response_sha256"] if item else None, "header": segment["records"][0]}


def evaluate(request_path, destination, program_sha256):
    result = {"status": "UNRESOLVED", "reason": None, "earliest_conflict_slot": None, "published": False}
    try:
        req_raw = Path(request_path).read_bytes(); req = parse(req_raw)
        require(set(req) == {"schema", "mode", "policy_path", "policy_sha256", "candidate_manifest", "old_manifest", "old_state", "old_checkpoint_sha256"}, "REQUEST_FIELDS")
        require(req["schema"] == "sof-runtime.source-advancement-request.v0" and req["mode"] in ("init", "append", "reapprove"), "REQUEST_SCHEMA_MODE")
        if req["mode"] == "init":
            require(all(req[k] is None for k in ("old_manifest", "old_state", "old_checkpoint_sha256")), "INIT_HAS_PARENT")
        policy = parse(Path(req["policy_path"]).read_bytes()); psha = file_sha(req["policy_path"])
        require(psha == req["policy_sha256"], "POLICY_ANCHOR_MISMATCH")
        require(policy["schema"] == "sof-runtime.offline-source-policy.v0" and policy["projection"] == "sof-runtime.solana-projection.v0"
                and policy["scope"] == "OFFLINE_FIXED_CAPTURE_COMPATIBILITY_ONLY", "POLICY_CONTRACT")
        execution = {"schema": "sof-runtime.execution-identity.v0", "projection": policy["projection"],
                     "program_sha256": program_sha256, "policy_sha256": psha}
        candidate = bundle(req["candidate_manifest"], policy); m = candidate["manifest"]
        parent_directory = Path(destination).parent.resolve(strict=True)
        require(not parent_directory.is_relative_to(Path(req["candidate_manifest"]).parent.resolve()), "DESTINATION_INSIDE_CAPTURE")
        if req["mode"] != "init":
            require(not parent_directory.is_relative_to(Path(req["old_state"]).resolve(strict=True))
                    and not parent_directory.is_relative_to(Path(req["old_manifest"]).parent.resolve(strict=True)), "DESTINATION_INSIDE_PARENT_OR_CAPTURE")
        require(not Path(destination).exists(), "DESTINATION_EXISTS")
        old_segments = []; old_entries = []; old_source = None; parent = None
        if req["mode"] == "init":
            require(all(req[k] is None for k in ("old_manifest", "old_state", "old_checkpoint_sha256")), "INIT_HAS_PARENT")
        else:
            old = bundle(req["old_manifest"], policy); om = old["manifest"]; state = Path(req["old_state"])
            cp_raw = (state/"checkpoint.json").read_bytes(); frame = parse(cp_raw); body = frame["body"]
            require(sha(cp_raw) == req["old_checkpoint_sha256"], "PARENT_CHECKPOINT_ANCHOR_MISMATCH")
            require(frame["body_sha256"] == sha(canonical(body)) and body["schema"] == "sof-runtime.source-checkpoint.v0", "PARENT_CHECKPOINT_FRAME")
            require(equal(body["execution_identity"], execution), "EXECUTION_IDENTITY_MISMATCH")
            require(equal(body["source_identity"], old["source"]) and body["capture_manifest_sha256"] == old["manifest_sha256"]
                    and type(body["start_slot"]) is int and body["start_slot"] == om["start_slot"], "PARENT_SOURCE_BINDING")
            old_segments = list(segments(req["old_manifest"]))
            old_entries = [entry(om, s) for s in old_segments]
            require(type(body["next_index"]) is int and body["next_index"] == len(old_entries)
                    and equal(body["committed"], old_entries), "PARENT_CHECKPOINT_RECORDS")
            require(file_sha(state/"transition.json") == body["transition_sha256"], "PARENT_TRANSITION_BINDING")
            expected_old = b"".join(s["bytes"] for s in old_segments)
            require((state/"projection.jsonl").read_bytes() == expected_old and body["projection_sha256"] == sha(expected_old)
                    and body["projection_bytes"] == len(expected_old), "PARENT_AGGREGATE_CORRUPTION")
            for s in old_segments:
                require((state/f"slot-{s['slot']}.jsonl").read_bytes() == s["bytes"], "PARENT_SEGMENT_CORRUPTION")
            allowed = {"checkpoint.json", "transition.json", "projection.jsonl", "writer.lock"} | {f"slot-{s['slot']}.jsonl" for s in old_segments}
            require({p.name for p in state.iterdir()} == allowed, "PARENT_STATE_INVENTORY")
            require(m["start_slot"] == om["start_slot"] and m["end_slot"] >= om["end_slot"], "CANDIDATE_RANGE_DOES_NOT_COVER_CHECKPOINT")
            require(equal(m["anchor"], om["anchor"]), "CAPTURE_ANCHOR_CONTINUITY_UNCONFIRMED")
            old_source = old["source"]; parent = sha(cp_raw)
        prefix = len(old_entries)
        source_changed = old_source is not None and not equal(old_source, candidate["source"])
        raw_changed = any(e["input_sha256"] != (m["rpc"].get(f"block-{e['slot']}") or {}).get("response_sha256") for e in old_entries)
        reproject = bool(prefix and (source_changed or raw_changed or req["mode"] == "reapprove"))
        iterator = iter(segments(req["candidate_manifest"]))
        projected = []
        for i, old_segment in enumerate(old_segments):
            new = next(iterator)
            if old_segment["bytes"] != new["bytes"]:
                return {**result, "status": "REJECTED_PREFIX_CONFLICT", "reason": "COMMITTED_PREFIX_DIVERGENCE",
                        "earliest_conflict_slot": old_segment["slot"], "compatibility": "INCOMPATIBLE_WITH_PROPOSED_CAPTURE"}
            projected.append(new)
        if source_changed or raw_changed:
            require(req["mode"] == "reapprove", "SOURCE_OR_PREFIX_EVIDENCE_REAPPROVAL_REQUIRED")
        if req["mode"] == "reapprove":
            require([old_source["credential_sha256"], candidate["credential_sha256"]] in policy["reapproval_pairs"], "SOURCE_REAPPROVAL_PAIR_NOT_ALLOWED")
        projected.extend(iterator)
        canonical_output = b"".join(s["bytes"] for s in projected)
        compatibility = "INITIALIZED" if req["mode"] == "init" else "REAPPROVED_EQUAL_RECORDS" if reproject else "INHERITED_EXACT_SOURCE_EVIDENCE"
        return {**result, "status": "COMPLETED_OFFLINE_ADVANCEMENT", "published": True, "compatibility": compatibility,
                "source": candidate["source"], "old_source": old_source, "execution": execution, "parent": parent,
                "candidate_manifest_sha256": candidate["manifest_sha256"], "request_sha256": sha(req_raw),
                "projected": projected, "entries": [entry(m, s) for s in projected], "projection_bytes": canonical_output,
                "inherited_slots": prefix, "new_slots": len(projected)-prefix,
                "prefix_decode_slots": [s["slot"] for s in projected[:prefix] if s["records"][0]["kind"] == "block"] if reproject else [],
                "suffix_decode_slots": [s["slot"] for s in projected[prefix:] if s["records"][0]["kind"] == "block"],
                "reproject": reproject}
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
        return {**result, "reason": str(error) or type(error).__name__}


def check_success(expected, actual, destination):
    require(actual["status"] == expected["status"] == "COMPLETED_OFFLINE_ADVANCEMENT", "SUCCESS_STATUS")
    state = Path(destination); cp_raw = (state/"checkpoint.json").read_bytes(); cp = parse(cp_raw); body = cp["body"]
    require(cp["body_sha256"] == sha(canonical(body)) and actual["new_checkpoint_sha256"] == sha(cp_raw), "NEW_CHECKPOINT_FRAME")
    for key, value in (("source_identity", expected["source"]), ("execution_identity", expected["execution"]),
                       ("parent_checkpoint_sha256", expected["parent"]), ("capture_manifest_sha256", expected["candidate_manifest_sha256"]),
                       ("committed", expected["entries"]), ("next_index", len(expected["entries"])),
                       ("projection_sha256", sha(expected["projection_bytes"])), ("projection_bytes", len(expected["projection_bytes"]))):
        require(equal(body[key], value), "CHECKPOINT_FIELD_"+key)
    require(body["schema"] == "sof-runtime.source-checkpoint.v0" and body["start_slot"] == expected["entries"][0]["slot"], "CHECKPOINT_SCOPE")
    require((state/"projection.jsonl").read_bytes() == expected["projection_bytes"], "FULL_PROJECTION_DIFFERENCE")
    for s in expected["projected"]:
        require((state/f"slot-{s['slot']}.jsonl").read_bytes() == s["bytes"], "SEGMENT_PROJECTION_DIFFERENCE")
    transition_raw = (state/"transition.json").read_bytes(); transition = parse(transition_raw)
    require(sha(transition_raw) == body["transition_sha256"] and transition["request_sha256"] == expected["request_sha256"]
            and transition["parent_checkpoint_sha256"] == expected["parent"] and transition["compatibility"] == expected["compatibility"], "TRANSITION_BINDING")
    require(equal(transition["source_transition"]["from"], expected["old_source"]) and equal(transition["source_transition"]["to"], expected["source"]), "TRANSITION_SOURCE_BINDING")
    require(actual["work"]["old_prefix_decoded_slots"] == [] and actual["work"]["candidate_prefix_decoded_slots"] == expected["prefix_decode_slots"]
            and actual["work"]["candidate_suffix_decoded_slots"] == expected["suffix_decode_slots"], "DECODE_ACCOUNTING")
    require(actual["inherited_slots"] == expected["inherited_slots"] and actual["new_slots"] == expected["new_slots"], "PREFIX_SUFFIX_ACCOUNTING")
    require(actual["work"]["staged_new_slots"] == expected["new_slots"] and actual["work"]["aggregate_bytes"] == len(expected["projection_bytes"]), "STAGING_OUTPUT_ACCOUNTING")
    require(equal(actual["work"], transition["work"]) and transition["policy_sha256"] == expected["execution"]["policy_sha256"], "TRANSITION_WORK_POLICY_BINDING")
    require(actual["projection_sha256"] == sha(expected["projection_bytes"]) and actual["projection_bytes"] == len(expected["projection_bytes"]), "RESULT_PROJECTION_BINDING")
    require(actual["source_identity_sha256"] == sha(canonical(expected["source"]))
            and actual["execution_identity_sha256"] == sha(canonical(expected["execution"])), "THREE_IDENTITY_BINDING")
    allowed = {"checkpoint.json", "transition.json", "projection.jsonl", "writer.lock"} | {f"slot-{s['slot']}.jsonl" for s in expected["projected"]}
    require({p.name for p in state.iterdir()} == allowed, "SUCCESS_STATE_INVENTORY")
