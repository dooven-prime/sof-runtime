"""Explicitly derived offline windows; no synthesized envelope is an RPC capture."""
from copy import deepcopy
from pathlib import Path

from applications.solana_offchain_slice.common import CONFIG, PROJECTION, canonical, parse, response, sha
from applications.solana_incremental_replay.reference import load

HERE = Path(__file__).resolve().parent


def corpus(upstream, directory, small=False):
    upstream = Path(upstream)
    m, upstream_sha = load(upstream)
    plan = parse((HERE/"plan.v0.json").read_bytes())
    if not small and upstream_sha != plan["upstream_manifest_sha256"]:
        raise ValueError("not the fixed real upstream capture")
    root = Path(directory); root.mkdir(parents=True, exist_ok=False)
    block_data = {b["slot"]: response(upstream.parent, m["rpc"][b["role"]]) for b in m["listed_blocks"]}
    start, end = m["start_slot"], m["end_slot"]
    maximum = end-start+1
    windows = [1, 2, maximum] if small else plan["windows"]
    if len(set(windows)) != 3 or maximum < windows[-1]:
        raise ValueError("fixture requires three distinct windows")
    credentials = {}
    for name in ("A", "B", "unknown"):
        credentials[name] = {"schema": "sof-runtime.offline-source-credential.v0", "locator": f"offline://source-{name.lower()}",
            "genesis": m["genesis"], "evidence_class": "LOCAL_DERIVED_CAPTURE_FIXTURE", "revision": name+"-1",
            "scope": {"start_slot": start, "end_slot": end}, "provider_authentication_claimed": False}
    paths = {}
    admission_hashes = []

    def make(name, count, source="A", mutation=None):
        folder = root/name; folder.mkdir()
        entries = {}
        last = start+count-1
        slots = [s for s in sorted(block_data) if s <= last]
        data = {s: deepcopy(block_data[s]) for s in slots}
        if mutation:
            mutation(data, slots)

        def save(role, method, params, result, identifier):
            a, b = role+".request.json", role+".response.json"
            raw_request = canonical({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
            raw_reply = canonical({"jsonrpc": "2.0", "id": identifier, "result": result})
            (folder/a).write_bytes(raw_request); (folder/b).write_bytes(raw_reply)
            entries[role] = {"id": identifier, "method": method, "params": params, "request": a, "response": b,
                             "request_sha256": sha(raw_request), "response_sha256": sha(raw_reply)}

        for i, (role, method, params, value) in enumerate([
            ("version", "getVersion", [], m["server_version"]),
            ("genesis", "getGenesisHash", [], m["genesis"]),
            ("genesis_after", "getGenesisHash", [], m["genesis"]),
            ("root_before", "getSlot", [{"commitment": "finalized"}], end+1),
            ("root_after", "getSlot", [{"commitment": "finalized"}], end+1),
            ("index_before", "getBlocks", [start, last, {"commitment": "finalized"}], slots),
            ("index_after", "getBlocks", [start, last, {"commitment": "finalized"}], slots),
            ("anchor", "getBlock", [m["anchor"]["slot"], {**CONFIG, "transactionDetails": "none"}], {"blockhash": m["anchor"]["blockhash"]})], 1):
            save(role, method, params, value, i)
        listed = []
        for s in slots:
            role = f"block-{s}"
            save(role, "getBlock", [s, CONFIG], data[s], 1000+s-start)
            listed.append({"slot": s, "role": role, "blockhash": data[s]["blockhash"]})
        fixture_plan = canonical({"schema": "sof-runtime.offline-window-fixture.v0", "upstream_manifest_sha256": upstream_sha,
                                  "window": [start, last], "name": name, "not_an_rpc_capture": True})
        (folder/"plan.json").write_bytes(fixture_plan)
        credential_raw = canonical(credentials[source]); credential_sha = sha(credential_raw)
        (folder/"credential.json").write_bytes(credential_raw)
        view = {"schema": "sof-runtime.solana-capture.v1", "projection": PROJECTION, "capture_kind": "synthetic_control",
            "source": credentials[source]["locator"], "commitment": "finalized", "config": CONFIG, "genesis": m["genesis"],
            "server_version": m["server_version"], "start_slot": start, "end_slot": last, "listed_blocks": listed,
            "anchor": m["anchor"], "rpc": entries, "finality_independently_verified": False, "plan_sha256": sha(fixture_plan),
            "offline_derivation": {"upstream_manifest_sha256": upstream_sha, "not_an_rpc_capture": True}}
        raw = canonical(view); (folder/"manifest.json").write_bytes(raw)
        admission = {"schema": "sof-runtime.offline-capture-admission.v0", "manifest_sha256": sha(raw),
            "credential_sha256": credential_sha, "upstream_manifest_sha256": upstream_sha,
            "qualification": "LOCAL_TEST_PERMISSION_NOT_PROVIDER_TRUST"}
        admission_raw = canonical(admission); (folder/"admission.json").write_bytes(admission_raw)
        admission_hashes.append(sha(admission_raw)); paths[name] = folder/"manifest.json"

    for count in windows:
        make(f"a-{count}", count)
    make("b-full", windows[-1], "B")
    def raw_revision(data, slots):
        data[slots[0]]["offline_unprojected_note"] = "same projected records, changed evidence"
    make("raw-revision", windows[-1], mutation=raw_revision)
    def conflict(data, slots):
        offsets = (0, min(1, len(slots)-1)) if small else (plan["earliest_mutation_offset"], plan["later_mutation_offset"])
        for offset in set(offsets):
            data[slots[offset]]["transactions"][0]["meta"]["fee"] += 1
    make("conflict", windows[-1], "B", conflict)
    def missing_listed(data, slots):
        removed = slots.pop(0); del data[removed]
        if slots:
            data[slots[0]]["parentSlot"] = m["anchor"]["slot"]
            data[slots[0]]["previousBlockhash"] = m["anchor"]["blockhash"]
    make("listed-conflict", windows[-1], "B", missing_listed)
    def continuity(data, slots):
        data[slots[-1]]["parentSlot"] = start-2
    make("bad-continuity", windows[-1], mutation=continuity)
    make("unknown", windows[-1], "unknown")
    policy = {"schema": "sof-runtime.offline-source-policy.v0", "projection": PROJECTION, "genesis": m["genesis"],
        "upstream_manifest_sha256": upstream_sha, "scope": "OFFLINE_FIXED_CAPTURE_COMPATIBILITY_ONLY",
        "credential_sha256": [sha(canonical(credentials[n])) for n in ("A", "B")], "admission_sha256": admission_hashes,
        "reapproval_pairs": [[sha(canonical(credentials[a])), sha(canonical(credentials[b]))] for a, b in (("A", "A"), ("A", "B"), ("B", "A"), ("B", "B"))]}
    policy_path = root/"policy.json"; policy_path.write_bytes(canonical(policy))
    return {"captures": paths, "policy": policy_path, "windows": windows, "upstream_manifest_sha256": upstream_sha}


def request(policy, candidate, mode, old_manifest=None, old_state=None, anchor=None):
    from applications.solana_offchain_slice.common import file_sha
    return {"schema": "sof-runtime.source-advancement-request.v0", "mode": mode,
            "policy_path": str(Path(policy).resolve()), "policy_sha256": file_sha(policy),
            "candidate_manifest": str(Path(candidate).resolve()),
            "old_manifest": str(Path(old_manifest).resolve()) if old_manifest else None,
            "old_state": str(Path(old_state).resolve()) if old_state else None, "old_checkpoint_sha256": anchor}
