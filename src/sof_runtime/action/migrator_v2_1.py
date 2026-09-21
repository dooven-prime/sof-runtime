"""Explicit SOFAction v2.0 to v2.1 boundary-annotation migration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.comparison.validation_v2_1 import (
    validate_audit,
    validate_audit_validation_receipt,
)
from sof_runtime.contracts import ContractError
from sof_runtime.contracts.validation import write_json
from sof_runtime.non_intervention import SOFACTION_EXECUTION_BOUNDARY
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.reporting.assembly_v2 import artifact_reference

from .validation_v2 import validate_action as validate_v2_action
from .validation_v2 import (
    validate_action_validation_receipt as validate_v2_receipt,
)
from .validation_v2_1 import (
    ACTION_RECEIPT_SCHEMA,
    ACTION_SCHEMA,
    build_action_validation_receipt,
)


def _snapshot(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def _audit_reference(
    audit_path: Path,
    receipt_path: Path,
    *,
    root: Path,
) -> dict[str, Any]:
    audit = validate_audit(audit_path, repository_root=root)
    receipt = validate_audit_validation_receipt(receipt_path, repository_root=root)
    audit_ref = artifact_reference(audit_path, repository_root=root)
    receipt_ref = artifact_reference(receipt_path, repository_root=root)
    if receipt["audit"]["artifact"] != audit_ref:
        raise ContractError("SOFAUDIT v2.1 receipt does not bind the migrated audit")
    return {
        "audit_id": audit["audit_id"],
        "artifact": audit_ref["uri"],
        "sofaudit_version": "2.1",
        "digest": deepcopy(audit_ref["digest"]),
        "validation_receipt": {
            "receipt_id": receipt["receipt_id"],
            "artifact": receipt_ref["uri"],
            "digest": deepcopy(receipt_ref["digest"]),
            "validator_id": receipt["validator"]["validator_id"],
            "validator_version": receipt["validator"]["validator_version"],
        },
    }


def _replace_audit_references(
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
            key: _replace_audit_references(child, old_audit_id, replacement)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_audit_references(child, old_audit_id, replacement)
            for child in value
        ]
    return value


def migrate_action(
    source_action_path: str | Path,
    source_receipt_path: str | Path,
    audit_path: str | Path,
    audit_receipt_path: str | Path,
    output_directory: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
    migrator_implementation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate a v2.0 action closure and emit a new v2.1 action closure."""

    root = Path(repository_root).resolve()
    source_path = Path(source_action_path).resolve()
    source_receipt = Path(source_receipt_path).resolve()
    source = validate_v2_action(source_path, repository_root=root)
    old_receipt = validate_v2_receipt(source_receipt, repository_root=root)
    if old_receipt["action"]["artifact"] != artifact_reference(
        source_path, repository_root=root
    ):
        raise ContractError("SOFAction v2.0 receipt does not bind the source action")

    migrated_audit_path = Path(audit_path).resolve()
    migrated_audit_receipt = Path(audit_receipt_path).resolve()
    replacement = _audit_reference(
        migrated_audit_path, migrated_audit_receipt, root=root
    )
    audit = validate_audit(migrated_audit_path, repository_root=root)
    audit_revision = audit["revision_provenance"]
    old_audit = source["source_audit"]
    if (
        audit_revision["kind"] != "explicit_v2_0_to_v2_1_migration"
        or audit_revision["source_artifact"]["uri"] != old_audit["artifact"]
        or audit_revision["source_artifact"]["digest"] != old_audit["digest"]
    ):
        raise ContractError("migrated SOFAUDIT does not bind the v2.0 source audit")

    migrated = _replace_audit_references(
        source, source["source_audit"]["audit_id"], replacement
    )
    migrated["audit_projection"]["signature"] = deepcopy(audit["coordinates"])
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    implementation = _snapshot(
        Path(migrator_implementation_path or __file__).resolve(),
        output / "migrator" / "sofaction-v2-to-v2_1.py",
    )
    migrated["sofaction_version"] = "2.1"
    migrated["revision_provenance"] = {
        "kind": "explicit_v2_0_to_v2_1_migration",
        "source_version": "2.0",
        "source_artifact": artifact_reference(source_path, repository_root=root),
        "migration_implementation": artifact_reference(
            implementation, repository_root=root
        ),
    }
    migrated["execution_boundary"] = deepcopy(SOFACTION_EXECUTION_BOUNDARY)
    migrated["record_basis"]["causal_status"] = "OUT_OF_SCOPE_FOR_SOFACTION"
    action_path = write_json(output / "result.sofaction.json", migrated)

    validator_snapshot = _snapshot(
        Path(__import__("sof_runtime.action.validation_v2_1", fromlist=["__file__"]).__file__).resolve(),
        output / "validator" / "sofaction-validator.py",
    )
    action_contract_snapshot = _snapshot(
        ACTION_SCHEMA, output / "contracts" / "sofaction.schema.json"
    )
    receipt_contract_snapshot = _snapshot(
        ACTION_RECEIPT_SCHEMA,
        output / "contracts" / "sofaction-validation-receipt.schema.json",
    )
    boundary_helper_snapshot = _snapshot(
        Path(__import__("sof_runtime.non_intervention", fromlist=["__file__"]).__file__).resolve(),
        output / "validator" / "non-intervention.py",
    )
    receipt = build_action_validation_receipt(
        action_path,
        repository_root=root,
        validator_implementation_path=validator_snapshot,
        action_contract_path=action_contract_snapshot,
        receipt_contract_path=receipt_contract_snapshot,
        boundary_helper_path=boundary_helper_snapshot,
        migration_source_receipt_path=source_receipt,
    )
    receipt_path = write_json(output / "validation-receipt.json", receipt)
    return {
        "action": str(action_path),
        "receipt": str(receipt_path),
        "action_record_id": migrated["action_record_id"],
        "candidate_count": migrated["candidate_action_set"]["count"],
    }
