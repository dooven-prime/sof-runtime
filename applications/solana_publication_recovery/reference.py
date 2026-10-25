"""Full Python projection plus independent publication-frame/inventory checking."""
import os
from pathlib import Path

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from applications.solana_source_advancement.reference import evaluate, check_success, require
from applications.solana_source_advancement.runner import tree_hashes
from .runner import binary, control


def path_key(path):
    value = str(Path(path).resolve())
    if os.name == "nt":
        if value.startswith("\\\\?\\UNC\\"): value = "\\\\"+value[8:]
        else: value = value.removeprefix("\\\\?\\")
    return os.path.normcase(value)


def predict(request_path, destination):
    destination = Path(destination)
    # Model the semantic computation, not the existing publication directory.
    absent = destination.parent/f".{destination.name}.python-model-absent"
    require(not absent.exists(), "MODEL_PATH_OCCUPIED")
    return evaluate(request_path, absent, file_sha(binary()))


def check(request_path, destination, result, expected=None):
    expected = expected or predict(request_path, destination)
    require(result["status"] == "COMPLETED_RECOVERABLE_PUBLICATION" and result["publication_confirmed"] is True, "PUBLICATION_STATUS")
    check_success(expected, result["advancement"], destination)
    root = control(destination); req = parse(Path(request_path).read_bytes())
    intent_raw = (root/"intent.json").read_bytes(); intent = parse(intent_raw)
    require(canonical(intent) == intent_raw and intent["schema"] == "sof-runtime.publication-intent.v0", "INTENT_CANONICAL")
    require(intent["request_sha256"] == file_sha(request_path) and intent["executable_sha256"] == file_sha(binary())
        and path_key(intent["destination"]) == path_key(destination), "INTENT_BINDING")
    inputs = {path_key(request_path): file_sha(request_path), path_key(req["policy_path"]): file_sha(req["policy_path"])}
    for field in ("candidate_manifest", "old_manifest", "old_state"):
        if req[field] is None: continue
        path = Path(req[field]); path = path if field == "old_state" else path.parent
        inputs.update({path_key(path/name): digest for name, digest in tree_hashes(path).items()})
    require({path_key(k): v for k, v in intent["input_inventory"].items()} == inputs, "COMPLETE_INPUT_BINDING")
    files = tree_hashes(destination)
    ready = {"schema": "sof-runtime.publication-ready.v0", "intent_sha256": sha(intent_raw),
             "files": files, "advancement": result["advancement"]}
    ready_raw = canonical(ready)
    require((root/"ready.json").read_bytes() == ready_raw, "READY_BYTES")
    receipt = {"schema": "sof-runtime.publication-receipt.v0", "status": "COMPLETED_RECOVERABLE_PUBLICATION",
        "intent_sha256": sha(intent_raw), "ready_sha256": sha(ready_raw), "destination": intent["destination"],
        "files": files, "advancement": result["advancement"]}
    receipt_raw = canonical(receipt)
    require((root/"receipt.json").read_bytes() == receipt_raw and result["receipt_sha256"] == sha(receipt_raw)
        and result["intent_sha256"] == sha(intent_raw), "DETERMINISTIC_RECEIPT_BYTES")
    require(not (root/"stage").exists() and not list(root.glob("*.pending")), "UNFINISHED_SUCCESS")
    return {"checkpoint_sha256": file_sha(Path(destination)/"checkpoint.json"), "receipt_sha256": sha(receipt_raw),
        "projection_sha256": sha(expected["projection_bytes"]), "projection_bytes": len(expected["projection_bytes"]),
        "state_files": files, "parent_and_source_binding": True}


def equal_state(left, right):
    left, right = Path(left), Path(right)
    require(tree_hashes(left) == tree_hashes(right), "STATE_IDENTITIES_DIFFER")
    for name in tree_hashes(left):
        require((left/name).read_bytes() == (right/name).read_bytes(), "STATE_BYTES_DIFFER")
