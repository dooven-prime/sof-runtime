"""Runtime semantic validation and receipts for SOFAction v2.1."""

from __future__ import annotations

import tempfile
from copy import deepcopy
from pathlib import Path
from types import FunctionType
from typing import Any
from urllib.parse import unquote

from sof_runtime.artifacts.digest import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.comparison.validation_v2_1 import (
    validate_audit,
    validate_audit_validation_receipt,
)
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.contracts.validation import write_json
from sof_runtime.non_intervention import (
    SOFACTION_EXECUTION_BOUNDARY,
    downstream_role_paths,
)
from sof_runtime.paths import ACTION_V2_1_CONTRACT_ROOT, PROJECT_ROOT
from sof_runtime.reporting.assembly_v2 import artifact_reference

from . import validation_v2 as legacy


ACTION_SCHEMA = ACTION_V2_1_CONTRACT_ROOT / "sofaction.schema.json"
ACTION_RECEIPT_SCHEMA = ACTION_V2_1_CONTRACT_ROOT / "validation-receipt.schema.json"
COMMON_CHECKS = {
    "artifact-digest-closure",
    "audit-projection-preservation",
    "candidate-non-execution",
    "candidate-set-regeneration",
    "downstream-artifact-role-isolation",
    "schema-validation",
    "verified-authority-non-authorization",
}
MIGRATION_CHECKS = COMMON_CHECKS | {
    "explicit-v2.0-to-v2.1-migration",
    "v2.0-source-validation",
}
NATIVE_CHECKS = COMMON_CHECKS | {
    "generation-input-closure",
    "native-v2.1-generation",
}


def _path(root: Path, value: str) -> Path:
    candidate = Path(unquote(value))
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _resolve(reference: dict[str, Any], root: Path, label: str) -> Path:
    uri = reference.get("uri")
    if not isinstance(uri, str) or not uri:
        raise ContractError(f"{label} has no URI")
    path = _path(root, uri)
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ContractError(f"{label} escapes repository root") from error
    if not path.is_file():
        raise ContractError(f"{label} is missing: {uri}")
    if reference.get("digest", {}).get("value") != sha256_file(path):
        raise ContractError(f"{label} digest differs")
    return path


def _audit_closure(
    reference: dict[str, Any], root: Path
) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    audit_path = _path(root, reference["artifact"])
    receipt_path = _path(root, reference["validation_receipt"]["artifact"])
    if not audit_path.is_file() or not receipt_path.is_file():
        raise ContractError("SOFAction source audit closure is incomplete")
    if reference["digest"]["value"] != sha256_file(audit_path):
        raise ContractError("SOFAction source audit digest differs")
    if reference["validation_receipt"]["digest"]["value"] != sha256_file(receipt_path):
        raise ContractError("SOFAction source audit receipt digest differs")
    receipt = validate_audit_validation_receipt(receipt_path, repository_root=root)
    audit = load_json(audit_path)
    if reference["audit_id"] != audit["audit_id"]:
        raise ContractError("SOFAction source audit ID differs")
    if receipt["audit"]["artifact"]["digest"] != reference["digest"]:
        raise ContractError("SOFAction audit receipt binds another audit")
    nested = reference["validation_receipt"]
    if (
        nested["receipt_id"] != receipt["receipt_id"]
        or nested["validator_id"] != receipt["validator"]["validator_id"]
        or nested["validator_version"] != receipt["validator"]["validator_version"]
    ):
        raise ContractError("SOFAction audit receipt identity differs")
    return audit_path, receipt_path, audit, receipt
def _replace_audit_version(value: Any, version: str) -> Any:
    if isinstance(value, dict):
        result = {
            key: _replace_audit_version(child, version)
            for key, child in value.items()
        }
        if "audit_id" in result and "sofaudit_version" in result and "validation_receipt" in result:
            result["sofaudit_version"] = version
        return result
    if isinstance(value, list):
        return [_replace_audit_version(child, version) for child in value]
    return value


def _replace_audit_reference(
    value: Any, old_audit_id: str, replacement: dict[str, Any]
) -> Any:
    if isinstance(value, dict):
        if (
            value.get("audit_id") == old_audit_id
            and "sofaudit_version" in value
            and "validation_receipt" in value
        ):
            return deepcopy(replacement)
        return {
            key: _replace_audit_reference(child, old_audit_id, replacement)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_audit_reference(child, old_audit_id, replacement)
            for child in value
        ]
    return value


def _validate_migration_projection(
    source: dict[str, Any],
    action: dict[str, Any],
    root: Path,
    audit: dict[str, Any],
) -> None:
    old_audit = source["source_audit"]
    new_audit_ref = action["source_audit"]
    audit_revision = audit["revision_provenance"]
    if (
        audit_revision["kind"] != "explicit_v2_0_to_v2_1_migration"
        or audit_revision["source_artifact"]["uri"] != old_audit["artifact"]
        or audit_revision["source_artifact"]["digest"] != old_audit["digest"]
    ):
        raise ContractError(
            "SOFAction v2.1 source audit is not the explicit migration of the v2.0 audit"
        )
    expected = _replace_audit_reference(
        source, old_audit["audit_id"], new_audit_ref
    )
    expected["audit_projection"]["signature"] = deepcopy(audit["coordinates"])
    expected["sofaction_version"] = "2.1"
    expected["revision_provenance"] = deepcopy(action["revision_provenance"])
    expected["execution_boundary"] = deepcopy(SOFACTION_EXECUTION_BOUNDARY)
    expected["record_basis"]["causal_status"] = "OUT_OF_SCOPE_FOR_SOFACTION"
    if action != expected:
        raise ContractError(
            "SOFAction v2.1 migration differs from the exact v2.0 boundary projection"
        )


def _v2_projection(action: dict[str, Any]) -> dict[str, Any]:
    projection = _replace_audit_version(action, "2.0")
    projection["sofaction_version"] = "2.0"
    projection.pop("revision_provenance", None)
    projection.pop("execution_boundary", None)
    projection["record_basis"]["causal_status"] = "not_claimed"
    return projection


def _validate_v2_semantics(
    action: dict[str, Any], root: Path, source_audit: dict[str, Any]
) -> None:
    projection = _v2_projection(action)
    with tempfile.TemporaryDirectory(prefix="sof-runtime-sofaction-v2_1-") as tmp:
        path = write_json(Path(tmp) / "projection.sofaction.json", projection)
        def projected_source_loader(
            payload: dict[str, Any], loader_root: Path
        ) -> dict[str, Any]:
            reference = payload["source_audit"]
            audit_path = _path(loader_root, reference["artifact"])
            result = deepcopy(source_audit)
            result["sofaudit_version"] = "2.0"
            result.pop("revision_provenance", None)
            result.pop("attribution_boundary", None)
            result["_digest"] = sha256_file(audit_path)
            result["_validation_receipt"] = deepcopy(
                reference["validation_receipt"]
            )
            return result

        isolated_globals = dict(legacy.validate_action.__globals__)
        isolated_globals["_load_source"] = projected_source_loader
        isolated_validator = FunctionType(
            legacy.validate_action.__code__,
            isolated_globals,
            legacy.validate_action.__name__,
            legacy.validate_action.__defaults__,
            legacy.validate_action.__closure__,
        )
        isolated_validator(path, repository_root=root)


def validate_action(
    action_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = Path(action_path).resolve()
    root = Path(repository_root).resolve()
    action = load_json(path)
    validate_contract(action, ACTION_SCHEMA, label="SOFAction v2.1")
    if action["execution_boundary"] != SOFACTION_EXECUTION_BOUNDARY:
        raise ContractError("SOFAction v2.1 execution boundary differs")
    if action["record_basis"]["causal_status"] != "OUT_OF_SCOPE_FOR_SOFACTION":
        raise ContractError("SOFAction v2.1 causal status is not out of scope")
    downstream = downstream_role_paths(action)
    if downstream:
        raise ContractError(
            "SOFAction v2.1 embeds downstream artifact roles: "
            + ", ".join(path for path, _ in downstream)
        )
    _, _, audit, _ = _audit_closure(action["source_audit"], root)
    revision = action["revision_provenance"]
    if revision["kind"] == "native_v2_1_generation":
        _resolve(
            revision["generation_implementation"], root, "generation implementation"
        )
        for index, reference in enumerate(revision["generation_inputs"]):
            _resolve(reference, root, f"generation input {index}")
    else:
        source_path = _resolve(
            revision["source_artifact"], root, "v2.0 source action"
        )
        _resolve(
            revision["migration_implementation"], root, "migration implementation"
        )
        source = legacy.validate_action(source_path, repository_root=root)
        _validate_migration_projection(source, action, root, audit)
    _validate_v2_semantics(action, root, audit)
    for candidate in action["candidate_action_set"]["actions"]:
        if candidate["authorization_state"] not in {
            "not_requested",
            "required",
            "pending",
            "denied",
        }:
            raise ContractError("candidate authorization state is authorizing")
    return action


def _generation(action: dict[str, Any]) -> dict[str, Any]:
    revision = action["revision_provenance"]
    if revision["kind"] == "explicit_v2_0_to_v2_1_migration":
        return {
            "kind": "migration",
            "class": "boundary_annotation",
            "source_version": "2.0",
            "source_artifact": deepcopy(revision["source_artifact"]),
            "implementation": deepcopy(revision["migration_implementation"]),
        }
    return {
        "kind": "native",
        "implementation": deepcopy(revision["generation_implementation"]),
        "input_artifacts": deepcopy(revision["generation_inputs"]),
    }


def _closure_digest(ordered: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": sha256_bytes(canonical_json_bytes(ordered)),
    }


def _normative_basis_paths(action: dict[str, Any], root: Path) -> list[Path]:
    policy = action.get("policy_profile") or {}
    return [
        _path(root, item["source_ref"]["uri"].removeprefix("artifact://"))
        for item in policy.get("normative_basis", [])
    ]


def build_action_validation_receipt(
    action_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
    validator_implementation_path: str | Path | None = None,
    action_contract_path: str | Path | None = None,
    receipt_contract_path: str | Path | None = None,
    boundary_helper_path: str | Path | None = None,
    migration_source_receipt_path: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(action_path).resolve()
    root = Path(repository_root).resolve()
    action = validate_action(path, repository_root=root)
    validator_path = Path(validator_implementation_path or __file__).resolve()
    action_contract = Path(action_contract_path or ACTION_SCHEMA).resolve()
    receipt_contract = Path(receipt_contract_path or ACTION_RECEIPT_SCHEMA).resolve()
    boundary_helper = Path(
        boundary_helper_path
        or __import__("sof_runtime.non_intervention", fromlist=["__file__"]).__file__
    ).resolve()
    source_audit = action["source_audit"]
    audit_path = _path(root, source_audit["artifact"])
    audit_receipt_path = _path(
        root, source_audit["validation_receipt"]["artifact"]
    )
    revision = action["revision_provenance"]
    ordered = [
        {"role": "action", "artifact": artifact_reference(path, repository_root=root)}
    ]
    if revision["kind"] == "explicit_v2_0_to_v2_1_migration":
        if migration_source_receipt_path is None:
            raise ContractError(
                "SOFAction migration receipt requires the v2.0 source receipt"
            )
        ordered.extend(
            [
                {"role": "revision-source-action-v2.0", "artifact": revision["source_artifact"]},
                {"role": "migration-implementation", "artifact": revision["migration_implementation"]},
            ]
        )
        ordered.append(
            {
                "role": "source-validation-receipt-v2.0",
                "artifact": artifact_reference(
                    Path(migration_source_receipt_path).resolve(),
                    repository_root=root,
                ),
            }
        )
    else:
        ordered.append(
            {"role": "generation-implementation", "artifact": revision["generation_implementation"]}
        )
        ordered.extend(
            {"role": f"generation-input-{index}", "artifact": reference}
            for index, reference in enumerate(revision["generation_inputs"])
        )
    ordered.extend(
        [
            {"role": "boundary-helper", "artifact": artifact_reference(boundary_helper, repository_root=root)},
            {"role": "action-contract", "artifact": artifact_reference(action_contract, repository_root=root)},
            {"role": "source-audit", "artifact": artifact_reference(audit_path, repository_root=root)},
            {"role": "source-audit-validation-receipt", "artifact": artifact_reference(audit_receipt_path, repository_root=root)},
        ]
    )
    ordered.extend(
        {
            "role": f"normative-basis-{index}",
            "artifact": artifact_reference(basis_path, repository_root=root),
        }
        for index, basis_path in enumerate(_normative_basis_paths(action, root))
    )
    ordered.extend(
        [
            {"role": "validator-implementation", "artifact": artifact_reference(validator_path, repository_root=root)},
            {"role": "validation-receipt-contract", "artifact": artifact_reference(receipt_contract, repository_root=root)},
        ]
    )
    roles = [item["role"] for item in ordered]
    if len(roles) != len(set(roles)):
        raise ContractError("SOFAction v2.1 receipt roles are not unique")
    if downstream_role_paths(ordered):
        raise ContractError("SOFAction v2.1 receipt embeds a downstream role")
    role_map = {item["role"]: item["artifact"] for item in ordered}
    checks = (
        MIGRATION_CHECKS
        if revision["kind"] == "explicit_v2_0_to_v2_1_migration"
        else NATIVE_CHECKS
    )
    receipt = {
        "receipt_version": "2.1",
        "artifact_type": "sofaction_validation_receipt",
        "receipt_kind": "SOFACTION_VALIDATION_RECEIPT",
        "receipt_scope": "SOFACTION_PROTOCOL_CONFORMANCE_ONLY",
        "receipt_id": f"receipt.{action['action_record_id']}.sofaction-v2_1",
        "action": {
            "action_record_id": action["action_record_id"],
            "sofaction_version": "2.1",
            "artifact": role_map["action"],
        },
        "validator": {
            "validator_id": "paper14.sofaction-validator.v2_1",
            "validator_version": "2.1",
            "implementation": role_map["validator-implementation"],
            "action_contract": role_map["action-contract"],
            "receipt_contract": role_map["validation-receipt-contract"],
        },
        "generation": _generation(action),
        "artifact_closure": {
            "artifact_count": len(ordered),
            "ordered_artifacts": ordered,
            "closure_digest": _closure_digest(ordered),
        },
        "status": "PASS",
        "checks": [
            {"check_id": check_id, "status": "PASS"}
            for check_id in sorted(checks)
        ],
        "authorization_semantics": "NONE",
        "execution_semantics": "NONE",
        "outcome_semantics": "NONE",
        "effect_semantics": "NONE",
        "negative_boundaries": [
            "PASS certifies SOFAction candidate-protocol conformance only; it is not selection, authorization, execution, outcome, or effect evidence."
        ],
    }
    validate_contract(receipt, ACTION_RECEIPT_SCHEMA, label="SOFAction v2.1 receipt")
    return receipt


def validate_action_validation_receipt(
    receipt_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = Path(receipt_path).resolve()
    root = Path(repository_root).resolve()
    receipt = load_json(path)
    validate_contract(receipt, ACTION_RECEIPT_SCHEMA, label="SOFAction v2.1 receipt")
    if downstream_role_paths(receipt["artifact_closure"]):
        raise ContractError("SOFAction v2.1 receipt embeds a downstream role")
    expected_checks = (
        MIGRATION_CHECKS
        if receipt["generation"]["kind"] == "migration"
        else NATIVE_CHECKS
    )
    checks = [item["check_id"] for item in receipt["checks"]]
    if len(checks) != len(set(checks)) or set(checks) != expected_checks:
        raise ContractError("SOFAction v2.1 receipt check set is not exact")
    closure = receipt["artifact_closure"]
    ordered = closure["ordered_artifacts"]
    if closure["artifact_count"] != len(ordered):
        raise ContractError("SOFAction v2.1 receipt artifact count differs")
    if closure["closure_digest"] != _closure_digest(ordered):
        raise ContractError("SOFAction v2.1 receipt closure digest differs")
    roles = [item["role"] for item in ordered]
    if len(roles) != len(set(roles)):
        raise ContractError("SOFAction v2.1 receipt roles are not unique")
    role_map = {item["role"]: item["artifact"] for item in ordered}
    for item in ordered:
        _resolve(item["artifact"], root, f"receipt role {item['role']}")
    if receipt["action"]["artifact"] != role_map.get("action"):
        raise ContractError("SOFAction v2.1 receipt action differs from closure")
    action_path = _resolve(receipt["action"]["artifact"], root, "receipt action")
    action = validate_action(action_path, repository_root=root)
    if receipt["generation"] != _generation(action):
        raise ContractError("SOFAction v2.1 receipt generation differs from action")
    if receipt["generation"]["kind"] == "migration":
        source_receipt_ref = role_map.get("source-validation-receipt-v2.0")
        if source_receipt_ref is None:
            raise ContractError("SOFAction migration receipt omits the v2.0 receipt")
        source_receipt_path = _resolve(
            source_receipt_ref, root, "v2.0 source receipt"
        )
        source_receipt = legacy.validate_action_validation_receipt(
            source_receipt_path, repository_root=root
        )
        if source_receipt["action"]["artifact"] != receipt["generation"]["source_artifact"]:
            raise ContractError("SOFAction v2.0 receipt binds another source action")
    validator_path = _resolve(
        receipt["validator"]["implementation"], root, "receipt validator"
    )
    action_contract = _resolve(
        receipt["validator"]["action_contract"], root, "action contract"
    )
    receipt_contract = _resolve(
        receipt["validator"]["receipt_contract"], root, "receipt contract"
    )
    if sha256_file(validator_path) != sha256_file(Path(__file__).resolve()):
        raise ContractError("SOFAction v2.1 receipt binds another validator")
    if sha256_file(action_contract) != sha256_file(ACTION_SCHEMA):
        raise ContractError("SOFAction v2.1 receipt binds another action contract")
    if sha256_file(receipt_contract) != sha256_file(ACTION_RECEIPT_SCHEMA):
        raise ContractError("SOFAction v2.1 receipt binds another receipt contract")
    return receipt
