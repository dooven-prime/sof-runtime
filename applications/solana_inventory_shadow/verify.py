"""Saved A0 shadow verification, including hostile named streams and junctions."""
import argparse
from pathlib import Path

from applications.solana_offchain_slice.common import canonical, parse, file_sha
from applications.solana_source_advancement.runner import tree_hashes
from applications.solana_source_advancement.reference import check_success
from applications.solana_publication_recovery.reference import check as original_check, predict as original_predict
from applications.solana_publication_recovery.runner import control as original_control
from .reference import Handle, inspect
from .runner import HERE, ROOT, binary, bindings, compare
from .evidence import inventory


def verify(directory):
    root = Path(directory).resolve(strict=True); receipt = root/"acceptance.v0.json"
    h = Handle(receipt)
    try: h.stamp()
    finally: h.close()
    r = parse(receipt.read_bytes()); plan = parse((HERE/"plan.v0.json").read_bytes())
    if r["status"] != "PASS_LOCAL_READ_ONLY_A0_SHADOW" or r["schema"] != "sof-runtime.a0-solana-shadow-acceptance.v0" or r["plan"] != plan:
        raise ValueError("acceptance identity")
    if r["implementation_sha256"] != bindings(): raise ValueError("implementation binding changed")
    if r["files"] != inventory(root, exclude=("acceptance.v0.json",)): raise ValueError("complete file/type/link/stream evidence changed")
    origin = ROOT/plan["origin_run"]
    if Path(r["origin"]["root_local"]).resolve() != origin.resolve() or file_sha(origin/"acceptance.v0.json") != plan["origin_receipt_sha256"] or tree_hashes(origin) != r["origin"]["files"]:
        raise ValueError("original producer closure changed")
    prior = parse((origin/"acceptance.v0.json").read_bytes()); source = next(c for c in prior["cases"] if c["name"] == plan["origin_case"])
    original_state, original_req = origin/source["destination"], origin/source["request"]
    original_check(original_req, original_state, source["result"])
    required = {"normal-"+s for s in plan["normal_roots"]} | {"decl-"+s for s in plan["declaration_controls"]} | {"file-"+s for s in plan["file_controls"]}
    required |= {"kill-"+s+"-"+p for s in plan["normal_roots"] for p in plan["kill_points"]}
    required |= {"mutation-"+s for s in plan["mutation_controls"]} | {"expired-observation", "semantic-boundary"}
    if len(r["cases"]) != len(required) or {c["name"] for c in r["cases"]} != required: raise ValueError("incomplete/duplicate matrix")

    def confined(name):
        p = Path(name)
        if p.is_absolute() or ".." in p.parts: raise ValueError("evidence path escaped")
        return root/p

    def observation(o):
        saved = parse((root/"logs"/o["observation_file"]).read_bytes())
        if saved != o or o["observer_executable_sha256"] != file_sha(binary()) or o["application_decision"] != "NOT_ASSESSED":
            raise ValueError("detached observation identity")
        stem = o["observation_file"].removesuffix(".observation.json")
        stdout, stderr = root/"logs"/(stem+".stdout.json"), root/"logs"/(stem+".stderr.txt")
        if file_sha(stdout) != o["process"]["stdout_sha256"] or file_sha(stderr) != o["process"]["stderr_sha256"]:
            raise ValueError("observation bytes changed")
        if o["process"]["actually_killed"]:
            if o["status"] != "INCOMPLETE" or o["result"] is not None: raise ValueError("kill admitted result")
            marker = parse((root/"logs"/(stem+".marker.json")).read_bytes())
            if marker != o["process"]["marker"]: raise ValueError("kill marker changed")
        elif parse(stdout.read_bytes()) != o["result"]: raise ValueError("recorded Rust result mismatch")
        if o["matching_observation_admissible"] != (o["status"] == "MATCHED_BYTES"): raise ValueError("admission changed")
        if o["status"] == "MATCHED_BYTES":
            result = o["result"]
            if o["process"]["returncode"] != 0 or result["observer_identity"] != {"role": "ShadowObserverExecution", "sha256": file_sha(binary())} or result["validity"] != "OBSERVED_INTERVAL_ONLY" or result["application_decision"] != "NOT_ASSESSED" or result["source_trust"] != "NOT_ASSESSED":
                raise ValueError("semantic/time/observer boundary changed")

    for row in r["cases"]:
        data, m, b = (confined(row[k]) for k in ("data", "manifest", "bindings")); o = row["observation"]; observation(o)
        if row["kind"] == "kill":
            if not o["process"]["actually_killed"] or o["process"]["marker"]["point"] != row["fault_point"]: raise ValueError("not the declared actual kill")
            observation(row["fresh"]); compare(data, m, b, row["fresh"])
        elif row["kind"] == "mutation":
            if o["status"] != "INCOMPLETE" or not o["process"]["changed_during_observation"] or o["result"]["error"]["code"] != "INPUT_CHANGED":
                raise ValueError("changed interval admitted")
            observation(row["fresh"]); compare(data, m, b, row["fresh"])
        elif row["kind"] == "expiry":
            observation(row["later"]); compare(data, m, b, row["later"])
            compare(confined(row["before_view"]), m, b, o)
            if o["status"] != "MATCHED_BYTES" or row["later"]["status"] != "REJECTED": raise ValueError("time boundary lost")
        else:
            compare(data, m, b, o)
            if row["kind"] in ("declaration", "filesystem") and o["status"] != "REJECTED": raise ValueError("hostile input admitted")
        if row["kind"] == "normal":
            expected = tree_hashes(original_state) if row["name"] == "normal-state" else {"receipt.json": file_sha(original_control(original_state)/"receipt.json")}
            if tree_hashes(data) != expected or expected != row["original_files"]: raise ValueError("normal artifact bytes changed")
            if row["name"] == "normal-state":
                for name in expected:
                    if (data/name).read_bytes() != (original_state/name).read_bytes(): raise ValueError("byte comparison failed")
            elif (data/"receipt.json").read_bytes() != (original_control(original_state)/"receipt.json").read_bytes(): raise ValueError("original receipt changed")
        if row["kind"] == "semantic-boundary":
            if o["status"] != "MATCHED_BYTES": raise ValueError("integrity control not matched")
            try: check_success(original_predict(original_req, original_state), source["result"]["advancement"], data)
            except ValueError as e:
                if str(e) != row["original_application_rejection"]: raise ValueError("application refusal differs")
            else: raise ValueError("integrity promoted to application validity")
    return {"status": "VERIFIED_LOCAL_SAVED_A0_SHADOW", "cases": len(r["cases"]), "real_kills": 6,
            "rust_reexecuted": False, "independent_execution_attestation": False, "b_or_c_extracted": False,
            "original_producer_identity_preserved": True, "future_snapshot_credential": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); print(canonical(verify(args.directory)).decode())
