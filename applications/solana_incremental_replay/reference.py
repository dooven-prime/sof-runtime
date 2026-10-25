"""Full Python replay; it never relies on the Rust checkpoint to project input."""
from pathlib import Path

from applications.solana_offchain_slice.common import CONFIG, PROJECTION, canonical, confined, parse, response, sha
from applications.solana_offchain_slice.reference import base58, integer, project_block
from .capture import SCHEMA


def load(manifest_path):
    path = Path(manifest_path)
    if path.is_symlink() or path.stat().st_size > 1024**2:
        raise ValueError("manifest size/type")
    raw = path.read_bytes()
    m = parse(raw)
    root = path.parent.resolve()
    if m["schema"] != SCHEMA or m["projection"] != PROJECTION or canonical(m["config"]) != canonical(CONFIG) or m["commitment"] != "finalized":
        raise ValueError("capture contract")
    if m["capture_kind"] not in ("rpc_capture", "synthetic_control") or m["finality_independently_verified"] is not False:
        raise ValueError("capture provenance")
    if sha(confined(root, "plan.json").read_bytes()) != m["plan_sha256"]:
        raise ValueError("plan identity")
    start, end = integer(m["start_slot"]), integer(m["end_slot"])
    if not 1 <= end-start+1 <= 256:
        raise ValueError("range")
    blocks = m["listed_blocks"]
    slots = [integer(b["slot"]) for b in blocks]
    if not slots or slots != sorted(set(slots)) or any(not start <= s <= end for s in slots):
        raise ValueError("listed slots")
    required = {"version", "genesis", "genesis_after", "root_before", "root_after", "index_before", "index_after", "anchor"}
    if set(m["rpc"]) != required | {f"block-{s}" for s in slots}:
        raise ValueError("RPC inventory")
    seen_ids, seen_files = set(), set()
    for role, item in m["rpc"].items():
        identifier = integer(item["id"])
        if identifier in seen_ids:
            raise ValueError("aliased RPC id")
        seen_ids.add(identifier)
        for field in ("request", "response"):
            if item[field] in seen_files:
                raise ValueError("aliased RPC file")
            seen_files.add(item[field])
            confined(root, item[field])
        request = confined(root, item["request"]).read_bytes()
        if len(request) > 65536 or sha(request) != item["request_sha256"] or canonical(parse(request)) != canonical({
            "jsonrpc": "2.0", "id": identifier, "method": item["method"], "params": item["params"]
        }):
            raise ValueError("request identity/envelope")
        if role.startswith("block-"):
            expected = ("getBlock", [int(role[6:]), CONFIG])
        elif role == "version":
            expected = ("getVersion", [])
        elif role in ("genesis", "genesis_after"):
            expected = ("getGenesisHash", [])
        elif role in ("root_before", "root_after"):
            expected = ("getSlot", [{"commitment": "finalized"}])
        elif role in ("index_before", "index_after"):
            expected = ("getBlocks", [start, end, {"commitment": "finalized"}])
        else:
            expected = ("getBlock", [integer(m["anchor"]["slot"]), {**CONFIG, "transactionDetails": "none"}])
        if item["method"] != expected[0] or canonical(item["params"]) != canonical(expected[1]):
            raise ValueError("RPC role/parameters")
        if role.startswith("block-"):
            continue
        value = response(root, item)
        if role == "version" and (canonical(value) != canonical(m["server_version"]) or not isinstance(value["solana-core"], str)):
            raise ValueError("version")
        if role in ("genesis", "genesis_after") and value != base58(m["genesis"], 32):
            raise ValueError("cluster")
        if role in ("root_before", "root_after") and integer(value) < end:
            raise ValueError("root")
        if role in ("index_before", "index_after") and canonical(value) != canonical(slots):
            raise ValueError("source index")
        if role == "anchor" and value["blockhash"] != base58(m["anchor"]["blockhash"], 32):
            raise ValueError("anchor")
    return m, sha(raw)


def segments(manifest_path):
    m, _ = load(manifest_path)
    root = Path(manifest_path).parent.resolve()
    known = {b["slot"]: b for b in m["listed_blocks"]}
    previous, previous_hash = integer(m["anchor"]["slot"]), m["anchor"]["blockhash"]
    for slot in range(m["start_slot"], m["end_slot"]+1):
        if slot not in known:
            records = [{"kind": "not_listed_by_source", "slot": slot}]
        else:
            if known[slot]["role"] != f"block-{slot}":
                raise ValueError("block role")
            block = response(root, m["rpc"][f"block-{slot}"])
            records = project_block(slot, block)
            if block["blockhash"] != known[slot]["blockhash"] or block["parentSlot"] != previous or block["previousBlockhash"] != previous_hash:
                raise ValueError("block chain mismatch")
            previous, previous_hash = slot, block["blockhash"]
        raw = b"".join(canonical(record)+b"\n" for record in records)
        yield {"slot": slot, "bytes": raw, "records": records}


def coverage(manifest_path):
    counts = {"listed_blocks": 0, "not_listed_slots": 0, "transactions": 0, "legacy": 0, "v0": 0,
              "failed_transactions": 0, "transactions_with_loaded_addresses": 0, "loaded_writable": 0, "loaded_readonly": 0}
    for segment in segments(manifest_path):
        header = segment["records"][0]
        counts["listed_blocks" if header["kind"] == "block" else "not_listed_slots"] += 1
        for r in segment["records"][1:]:
            counts["transactions"] += 1
            counts["legacy" if r["version"] == "legacy" else "v0"] += 1
            counts["failed_transactions"] += r["error"] is not None
            counts["transactions_with_loaded_addresses"] += bool(r["loaded_writable"] or r["loaded_readonly"])
            counts["loaded_writable"] += len(r["loaded_writable"])
            counts["loaded_readonly"] += len(r["loaded_readonly"])
    return counts


def projection(manifest_path):
    return b"".join(s["bytes"] for s in segments(manifest_path))
