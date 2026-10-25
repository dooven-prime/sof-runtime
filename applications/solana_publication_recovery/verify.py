"""Verify saved local publication closure and Python semantics, without rerunning Rust."""
import argparse
from pathlib import Path

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from .reference import check, equal_state
from .runner import HERE, POINTS, bindings, control, tree_hashes


def verify(directory):
    root = Path(directory).resolve(strict=True); receipt_path = root/"acceptance.v0.json"
    record = parse(receipt_path.read_bytes())
    if record["schema"] != "sof-runtime.publication-recovery-acceptance.v0" or record["status"] != "PASS_LOCAL_PUBLICATION_RECOVERY":
        raise ValueError("acceptance identity")
    actual = {p.relative_to(root).as_posix(): file_sha(p) for p in sorted(root.rglob("*")) if p.is_file() and p != receipt_path}
    if any(p.is_symlink() for p in root.rglob("*")) or actual != record["files"]: raise ValueError("saved closure inventory/hash")
    if record["implementation_sha256"] != bindings() or record["plan"] != parse((HERE/"plan.v0.json").read_bytes()):
        raise ValueError("source/binary/plan binding")
    if tree_hashes(Path(record["upstream"]["path"]).parent) != record["upstream"]["files"]: raise ValueError("upstream changed")
    if tree_hashes(root/"parent") != record["parent_files"] or tree_hashes(root/"corpus") != record["corpus_files"]: raise ValueError("protected input changed")
    initial = record["initial"]; check(root/initial["request"], root/initial["destination"], initial["result"])
    required = {f"{mode}-{point}" for mode in ("append", "reapprove") for point in POINTS}
    refused = {"refuse-"+s for s in ("staged-segment", "pending-transition", "ready", "published-checkpoint",
        "published-segment", "receipt", "foreign-output", "request-identity")}
    names = required | refused | {"clean-append", "clean-reapprove", "repeated-interruption"}
    if len(record["cases"]) != len(names) or {c["name"] for c in record["cases"]} != names:
        raise ValueError("acceptance coverage")
    kills = [c for c in record["cases"] if c["kind"] == "kill"]
    if len(kills) != len(required) or {c["name"] for c in kills} != required: raise ValueError("incomplete kill matrix")
    for c in record["cases"]:
        req, dest = root/c["request"], root/c["destination"]
        if c["kind"] == "refusal":
            if c["result"]["status"] != "UNRESOLVED" or c["result"]["publication_confirmed"] is not False:
                raise ValueError("refusal was success")
            saved = parse((root/"logs"/f"{c['name']}-deny.stdout.json").read_bytes())
            if saved != c["result"]: raise ValueError("refusal output mismatch")
            kind = c["name"].removeprefix("refuse-")
            cr = control(dest); model = cr/"calculation/model"
            if kind == "staged-segment":
                damaged = list((cr/"stage").glob("slot-*.jsonl"))
                if not any(p.read_bytes() != (model/p.name).read_bytes() for p in damaged): raise ValueError("no staged corruption")
            elif kind == "pending-transition":
                if (model/"transition.json").read_bytes().startswith((cr/"stage/transition.json.pending").read_bytes()):
                    raise ValueError("pending corruption not demonstrated")
            elif kind == "ready":
                if (cr/"ready.json").read_bytes() != b"{}": raise ValueError("ready control changed")
            elif kind in ("published-checkpoint", "published-segment"):
                if tree_hashes(dest) == tree_hashes(root/"clean-append"): raise ValueError("publication corruption not demonstrated")
            elif kind == "receipt":
                if (cr/"receipt.json").read_bytes() != b"{}": raise ValueError("receipt control changed")
            elif kind == "foreign-output":
                if tree_hashes(dest) != {"retain.txt": sha(b"foreign state must remain")}: raise ValueError("foreign output overwritten")
            elif kind == "request-identity":
                if parse((cr/"intent.json").read_bytes())["request_sha256"] == file_sha(req): raise ValueError("identity did not change")
            if kind not in ("published-checkpoint", "published-segment", "receipt", "foreign-output") and dest.exists():
                raise ValueError("refusal published a new directory")
            continue
        checked = check(req, dest, c["result"])
        if checked != c["python_check"]: raise ValueError("saved Python check drift")
        if c["kind"] == "kill":
            marker = parse((root/"logs"/f"{c['name']}-kill.marker.json").read_bytes())
            if not c["kill_process"]["actually_killed"] or marker != c["kill_process"]["marker"] or marker["point"] != c["fault_point"]:
                raise ValueError("kill marker mismatch")
            if c["visible_after_kill"] != (c["fault_point"] in ("after_publication", "receipt_partial", "receipt_published")):
                raise ValueError("publication linearization mismatch")
            check(req, dest, c["retry"])
            equal_state(root/f"clean-{parse(req.read_bytes())['mode']}", dest)
            if c["retry"]["receipt_sha256"] != c["result"]["receipt_sha256"]: raise ValueError("retry identity drift")
        elif c["kind"] == "repeated-kill":
            if len(c["kills"]) != 4 or not all(p["actually_killed"] for p in c["kills"]): raise ValueError("repeated interruption")
            equal_state(root/"clean-reapprove", dest)
    return {"status": "VERIFIED_LOCAL_SAVED_PUBLICATION_RECOVERY", "cases": len(record["cases"]), "matrix_kills": len(kills),
        "worker_reexecuted": False, "independent_execution_attestation": False,
        "power_loss_durability": False, "live_source_or_reorg": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); print(canonical(verify(args.directory)).decode())
