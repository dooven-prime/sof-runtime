"""Capture a predeclared range without filtering unsupported or failed blocks."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import time
import urllib.error
import urllib.request

from applications.solana_offchain_slice.common import CONFIG, canonical, parse, sha

SCHEMA = "sof-runtime.solana-capture.v1"
PLAN = Path(__file__).with_name("plan.v1.json")


def capture(directory):
    plan_raw = PLAN.read_bytes()
    plan = parse(plan_raw)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    (root / "plan.json").write_bytes(plan_raw)
    entries = {}
    calls = 0

    def rpc(role, method, params):
        nonlocal calls
        calls += 1
        request = canonical({"jsonrpc": "2.0", "id": calls, "method": method, "params": params})
        request_name = f"{calls:03d}-{role}.request.json"
        (root / request_name).write_bytes(request)
        response_name = f"{calls:03d}-{role}.response.json"
        for attempt in range(plan["attempts_per_request"]):
            try:
                with urllib.request.urlopen(urllib.request.Request(
                    plan["endpoint"], request, {"Content-Type": "application/json", "Accept-Encoding": "identity"}
                ), timeout=plan["request_timeout_seconds"]) as reply:
                    raw = reply.read(plan["max_response_bytes"] + 1)
                    if reply.status != 200 or len(raw) > plan["max_response_bytes"]:
                        raise ValueError("HTTP status/response size")
                break
            except (urllib.error.URLError, TimeoutError) as error:
                (root / f"{calls:03d}-{role}.attempt-{attempt}.json").write_bytes(canonical({
                    "attempt": attempt, "error": str(error), "utc": datetime.now(timezone.utc).isoformat()
                }))
                if attempt + 1 == plan["attempts_per_request"]:
                    raise
                time.sleep(plan["retry_delays_seconds"][attempt])
        (root / response_name).write_bytes(raw)
        reply = parse(raw)
        if reply.get("jsonrpc") != "2.0" or type(reply.get("id")) is not int or reply["id"] != calls or "error" in reply or "result" not in reply:
            raise ValueError(f"RPC failure; no complete manifest: {reply}")
        entries[role] = {"id": calls, "method": method, "params": params, "request": request_name,
                         "response": response_name, "request_sha256": sha(request), "response_sha256": sha(raw)}
        print(f"captured {role}", flush=True)
        return reply["result"]

    started = datetime.now(timezone.utc).isoformat()
    version = rpc("version", "getVersion", [])
    genesis = rpc("genesis", "getGenesisHash", [])
    finalized = rpc("root_before", "getSlot", [{"commitment": "finalized"}])
    start = plan["start_slot"]
    end = start + plan["count"] - 1
    if type(finalized) is not int or end > finalized:
        raise ValueError("range outside finalized root")
    slots = rpc("index_before", "getBlocks", [start, end, {"commitment": "finalized"}])
    if not slots or slots != sorted(set(slots)) or any(type(s) is not int or not start <= s <= end for s in slots):
        raise ValueError("invalid source index")
    blocks = []
    first = None
    for slot in slots:
        block = rpc(f"block-{slot}", "getBlock", [slot, CONFIG])
        if not isinstance(block, dict):
            raise ValueError("listed block missing; no filtering")
        if first is None:
            first = block
        blocks.append({"slot": slot, "role": f"block-{slot}", "blockhash": block["blockhash"]})
    anchor_slot = first["parentSlot"]
    anchor = rpc("anchor", "getBlock", [anchor_slot, {**CONFIG, "transactionDetails": "none"}])
    if not isinstance(anchor, dict) or anchor["blockhash"] != first["previousBlockhash"]:
        raise ValueError("predecessor mismatch")
    if rpc("index_after", "getBlocks", [start, end, {"commitment": "finalized"}]) != slots:
        raise ValueError("source index changed")
    if rpc("root_after", "getSlot", [{"commitment": "finalized"}]) < end or rpc("genesis_after", "getGenesisHash", []) != genesis:
        raise ValueError("root/cluster changed")
    manifest = {"schema": SCHEMA, "projection": "sof-runtime.solana-projection.v0", "capture_kind": "rpc_capture",
                "source": plan["endpoint"], "commitment": "finalized", "config": CONFIG, "genesis": genesis,
                "server_version": version, "start_slot": start, "end_slot": end, "listed_blocks": blocks,
                "anchor": {"slot": anchor_slot, "blockhash": anchor["blockhash"]}, "rpc": entries,
                "started_utc": started, "completed_utc": datetime.now(timezone.utc).isoformat(),
                "finality_independently_verified": False, "plan_sha256": sha(plan_raw)}
    with (root / "manifest.json").open("xb") as stream:
        stream.write(canonical(manifest))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    result = capture(parser.parse_args().output_dir)
    print(canonical({"status": "CAPTURED_LOCAL", "range": [result["start_slot"], result["end_slot"]],
                     "blocks": len(result["listed_blocks"])}).decode())
