"""Saved-byte and separate Python prefix checks, not an execution attestation."""
import argparse
from pathlib import Path

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from applications.solana_incremental_replay.reference import load, segments
from applications.solana_incremental_replay.validation import expected_entries
from .experiment import classify
from .runner import HERE, bindings


def verify(manifest, directory):
    root = Path(directory).resolve(strict=True)
    record = parse((root/"attribution.v1.json").read_bytes())
    plan = parse((HERE/"plan.v1.json").read_bytes())
    if record["implementation_sha256"] != bindings() or canonical(record["plan"]) != canonical(plan) or record["status"] != "PASS_LOCAL_ATTRIBUTION_CONTROLS":
        raise ValueError("code/plan/receipt identity")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(record["files"]) | {"attribution.v1.json"}:
        raise ValueError("run inventory")
    for name, digest in record["files"].items():
        path = root/name
        if Path(name).is_absolute() or ".." in Path(name).parts or not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in [path, *path.parents] if p != root.parent) or file_sha(path) != digest:
            raise ValueError("saved artifact identity")
    manifest = Path(manifest).resolve(strict=True)
    m, msha = load(manifest)
    if msha != plan["capture_manifest_sha256"] or record["capture"]["manifest_sha256"] != msha or record["capture"]["files"] != {p.name: file_sha(p) for p in sorted(manifest.parent.iterdir()) if p.is_file()}:
        raise ValueError("capture identity")
    n = plan["prefix_slots"]
    projected = list(segments(manifest))
    expected = b"".join(s["bytes"] for s in projected[:n])
    if (root/"reference-prefix.jsonl").read_bytes() != expected or record["prefix"]["aggregate_sha256"] != sha(expected):
        raise ValueError("full Python prefix")
    entries = expected_entries(manifest, projected)[:n]
    identity = {"manifest_sha256": msha, "projection": m["projection"], "executable_sha256": record["implementation_sha256"]["frozen_replay"]["rust_binary"]}
    body = {"schema": "sof-runtime.solana-checkpoint.v1", "identity": identity, "next_index": n, "committed": entries}
    frame = canonical({"body": body, "body_sha256": sha(canonical(body))})
    if len(record["attempts"]) != plan["pairs"]*2*(1+plan["explicit_read_warm_rounds"]):
        raise ValueError("probe count")
    raw_bytes = sum((manifest.parent/m["rpc"][b["role"]]["response"]).stat().st_size for b in m["listed_blocks"] if b["slot"] < m["start_slot"]+n)
    for a in record["attempts"]:
        r = a["result"]; state = root/a["state"]
        if r["status"] != "MEASURED_VERIFIED_PREFIX" or r["block_decodes"] or r["new_commits"] or r["checkpoint_sha256"] != sha(frame):
            raise ValueError("probe work/binding")
        if (state/"checkpoint.json").read_bytes() != frame or (state/"identity.json").read_bytes() != canonical(identity):
            raise ValueError("prefix state")
        if (root/"aggregates"/f"{a['name']}.jsonl").read_bytes() != expected or r["aggregate_sha256"] != sha(expected):
            raise ValueError("prefix aggregate")
        log = root/"logs"/f"{a['name']}.stdout.json"
        if canonical(parse(log.read_bytes())) != canonical(r) or file_sha(log) != a["process"]["stdout_sha256"]:
            raise ValueError("result/log binding")
        for key, length in (("raw_input_hash", raw_bytes), ("segment_validation", len(expected)), ("aggregate_stream", len(expected))):
            if r["phases"][key]["logical_read_bytes"] != length:
                raise ValueError("actual read-byte accounting")
        if r["phases"]["aggregate_stream"]["logical_written_bytes"] != len(expected):
            raise ValueError("actual write-byte accounting")
        if a["condition"] == "read_warmed" and (not a["prewarm"] or a["prewarm"]["kind"] != "EXPLICIT_READ_ONLY_NOT_VALIDATION"):
            raise ValueError("prewarm protocol")
        for item, s in zip(entries, projected):
            if (state/f"slot-{item['slot']}.jsonl").read_bytes() != s["bytes"]:
                raise ValueError("state segment changed")
    if canonical(record["disposition"]) != canonical(classify(record["attempts"], plan)):
        raise ValueError("stop-rule disposition")
    return {"status": "VERIFIED_LOCAL_SAVED_ATTRIBUTION", "probes": len(record["attempts"]),
            "classification": record["disposition"]["classification"], "worker_reexecuted": False,
            "independent_execution_attestation": False, "physical_disk_measured": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); print(canonical(verify(args.manifest, args.directory)).decode())
