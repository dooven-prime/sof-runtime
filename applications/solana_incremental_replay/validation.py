"""Separate checks of saved complete states and decoded-slot accounting."""
from pathlib import Path

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from .reference import coverage, load, segments
from .runner import check_work


def expected_entries(manifest_path, projected):
    m, _ = load(manifest_path)
    result = []
    for segment in projected:
        slot = segment["slot"]
        item = m["rpc"].get(f"block-{slot}")
        result.append({"slot": slot, "sha256": sha(segment["bytes"]), "bytes": len(segment["bytes"]),
                       "records": len(segment["records"]), "input_sha256": item["response_sha256"] if item else None,
                       "header": segment["records"][0]})
    return result


def check_state(state, identity, entries, expected):
    state = Path(state)
    body = {"schema": "sof-runtime.solana-checkpoint.v1", "identity": identity,
            "next_index": len(entries), "committed": entries}
    frame = {"body": body, "body_sha256": sha(canonical(body))}
    if (state/"checkpoint.json").read_bytes() != canonical(frame) or (state/"identity.json").read_bytes() != canonical(identity):
        raise ValueError("complete state/checkpoint differs from full reference")
    if (state/"projection.jsonl").read_bytes() != expected:
        raise ValueError("complete aggregate differs from Python")
    offset = 0
    for entry in entries:
        raw = expected[offset:offset+entry["bytes"]]
        if (state/f"slot-{entry['slot']}.jsonl").read_bytes() != raw:
            raise ValueError("segment differs from Python")
        offset += len(raw)
    if offset != len(expected) or any(state.glob("*.tmp")):
        raise ValueError("incomplete or temporary state")
    allowed = {"identity.json", "checkpoint.json", "writer.lock", "projection.jsonl"} | {f"slot-{e['slot']}.jsonl" for e in entries}
    if {p.name for p in state.iterdir()} != allowed:
        raise ValueError("state inventory")


def check_result(result, m, initial, mode, source_root):
    if result["status"] != "COMPLETED_LOCAL_CAPTURE":
        raise ValueError(f"replay did not complete: {result}")
    check_work(result, m, initial, mode)
    work = result["work"]
    for field, trace in (("prefix_decode_bytes", "prefix_decoded_slots"), ("suffix_decode_bytes", "suffix_decoded_slots")):
        expected = sum((Path(source_root)/m["rpc"][f"block-{s}"]["response"]).stat().st_size for s in work[trace])
        if work[field] != expected:
            raise ValueError("decode byte accounting")
    prefix_inputs = sum((Path(source_root)/m["rpc"][f"block-{b['slot']}"]["response"]).stat().st_size
                        for b in m["listed_blocks"] if b["slot"] < m["start_slot"]+initial)
    if work["prefix_verified_input_bytes"] != prefix_inputs:
        raise ValueError("prefix integrity input byte accounting")


def verify(manifest_path, directory):
    from .runner import bindings
    root = Path(directory).resolve(strict=True)
    record = parse((root/"acceptance.v1.json").read_bytes())
    if record["status"] != "PASS_LOCAL_INCREMENTAL_CONTROLS" or record["implementation_sha256"] != bindings():
        raise ValueError("code/receipt identity")
    files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if files != set(record["files"]) | {"acceptance.v1.json"}:
        raise ValueError("run inventory")
    for name, digest in record["files"].items():
        path = root/name
        if Path(name).is_absolute() or ".." in Path(name).parts or not path.resolve().is_relative_to(root):
            raise ValueError("receipt path")
        if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent) or file_sha(path) != digest:
            raise ValueError("run byte identity")
    manifest_path = Path(manifest_path).resolve(strict=True)
    m, msha = load(manifest_path)
    source_files = {p.name: file_sha(p) for p in sorted(manifest_path.parent.iterdir()) if p.is_file()}
    if source_files != record["capture"]["files"] or msha != record["capture"]["manifest_sha256"]:
        raise ValueError("capture identity")
    plan = parse(Path(__file__).with_name("plan.v1.json").read_bytes())
    if canonical(record["plan"]) != canonical(plan) or m["plan_sha256"] != file_sha(Path(__file__).with_name("plan.v1.json")):
        raise ValueError("fixed acceptance plan")
    if coverage(manifest_path) != record["capture"]["coverage"]:
        raise ValueError("capture coverage differs")
    projected = list(segments(manifest_path))
    expected = b"".join(s["bytes"] for s in projected)
    if (root/"reference.jsonl").read_bytes() != expected or sha(expected) != record["projection"]["sha256"]:
        raise ValueError("full reference")
    identity = {"manifest_sha256": msha, "projection": m["projection"], "executable_sha256": record["implementation_sha256"]["rust_binary"]}
    entries = expected_entries(manifest_path, projected)
    for state in record["completed_states"]:
        check_state(root/state, identity, entries, expected)
    for attempt in record["attempts"]:
        result = attempt["result"]
        output = root/"logs"/f"{attempt['name']}.stdout.json"
        error = root/"logs"/f"{attempt['name']}.stderr.txt"
        if canonical(parse(output.read_bytes())) != canonical(result) or file_sha(output) != attempt["process"]["stdout_sha256"] or file_sha(error) != attempt["process"]["stderr_sha256"]:
            raise ValueError("attempt/result log binding")
        if attempt["fault_boundary"]:
            point, slot = attempt["fault_boundary"]
            if result != {"status": "FAULT_REACHED", "point": point, "slot": slot} or not attempt["process"]["terminated_at_boundary"]:
                raise ValueError("recorded process boundary")
        if result["status"] == "COMPLETED_LOCAL_CAPTURE":
            check_result(result, m, attempt["initial_committed_slots"], attempt["mode"], manifest_path.parent)
            if result["projection_sha256"] != sha(expected) or result["checkpoint_sha256"] != file_sha(root/attempt["state"]/"checkpoint.json"):
                raise ValueError("result/actual output")
            n = attempt["initial_committed_slots"]
            if result["work"]["prefix_verified_segment_bytes"] != sum(e["bytes"] for e in entries[:n]):
                raise ValueError("prefix segment verification accounting")
            if result["projection_bytes"] != len(expected) or result["projection_records"] != sum(e["records"] for e in entries):
                raise ValueError("output length/record accounting")
    from .runner import POINTS
    if {r["point"] for r in record["recoveries"]} != set(POINTS) or len(record["recoveries"]) != len(POINTS):
        raise ValueError("recovery inventory")
    if [c["committed_slots"] for c in record["recovery_curves"]] != plan["prefix_slots"] or len(record["clean_attempts"]) != plan["clean_repetitions"]:
        raise ValueError("curve/clean plan")
    by_name = {a["name"]: a for a in record["attempts"]}
    if len(by_name) != len(record["attempts"]) or len(record["completed_states"]) != plan["clean_repetitions"]+len(POINTS)+2*len(plan["prefix_slots"])*plan["paired_repetitions"]:
        raise ValueError("attempt/state inventory")
    for curve in record["recovery_curves"]:
        if len(curve["pairs"]) != plan["paired_repetitions"]:
            raise ValueError("pair count")
        for rep, pair in enumerate(curve["pairs"]):
            if pair["rep"] != rep or pair["order"] != (["incremental", "full_reproject"] if rep % 2 == 0 else ["full_reproject", "incremental"]):
                raise ValueError("paired order")
            for mode, measurement in pair["measurements"].items():
                attempt = by_name[measurement["attempt"]]
                if attempt["mode"] != mode or attempt["initial_committed_slots"] != curve["committed_slots"] or attempt["checkpoint_anchor_sha256"] != curve["checkpoint_anchor_sha256"] or canonical(measurement["work"]) != canonical(attempt["result"]["work"]) or canonical(measurement["resources"]) != canonical(attempt["process"]):
                    raise ValueError("curve/result binding")
    return {"status": "VERIFIED_LOCAL_SAVED_COMPARISONS", "completed_states": len(record["completed_states"]),
            "projection_sha256": sha(expected), "worker_reexecuted": False, "independent_execution_attestation": False,
            "independent_finality_verification": False}
