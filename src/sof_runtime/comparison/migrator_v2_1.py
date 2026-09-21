"""Explicit SOFAUDIT v2.0 to v2.1 boundary-annotation migration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.contracts import ContractError, load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.non_intervention import SOFAUDIT_ATTRIBUTION_BOUNDARY
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.reporting.assembly_v2 import artifact_reference
from sof_runtime.reporting.validation_v2_1 import (
    validate_receipt as validate_report_receipt,
)
from sof_runtime.reporting.validation_v2_1 import validate_report

from .validation_v2 import validate_audit as validate_v2_audit
from .validation_v2 import (
    validate_audit_validation_receipt as validate_v2_receipt,
)
from .validation_v2_1 import (
    AUDIT_RECEIPT_SCHEMA,
    AUDIT_SCHEMA,
    build_audit_validation_receipt,
)


def _snapshot(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def _report_reference(
    old_reference: dict[str, Any],
    report_path: Path,
    receipt_path: Path,
    *,
    root: Path,
) -> dict[str, Any]:
    report = validate_report(report_path, repository_root=root)
    receipt = validate_report_receipt(receipt_path, repository_root=root)
    report_ref = artifact_reference(report_path, repository_root=root)
    receipt_ref = artifact_reference(receipt_path, repository_root=root)
    if receipt["report"]["artifact"] != report_ref:
        raise ContractError("SOFRS v2.1 receipt does not bind the migrated report")
    if report["report_id"] != old_reference["report_id"]:
        raise ContractError("migrated SOFRS report ID differs from SOFAUDIT v2.0")
    revision = report["revision_provenance"]
    if revision["kind"] != "explicit_v2_0_to_v2_1_migration":
        raise ContractError("SOFAUDIT migration requires explicitly migrated reports")
    if revision["source_artifact"] != old_reference["artifact"]:
        raise ContractError("migrated SOFRS report does not bind the v2.0 report")
    if revision["source_validation_receipt"] != old_reference["validation_receipt"]:
        raise ContractError("migrated SOFRS report does not bind the v2.0 receipt")
    result = deepcopy(old_reference)
    result["artifact"] = report_ref
    result["validation_receipt"] = receipt_ref
    result["sofrs_version"] = "2.1"
    result["admission_basis"] = "native_sofrs_v2_1"
    return result


def migrate_audit(
    source_audit_path: str | Path,
    source_receipt_path: str | Path,
    reference_report_path: str | Path,
    reference_receipt_path: str | Path,
    target_report_path: str | Path,
    target_receipt_path: str | Path,
    output_directory: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
    migrator_implementation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate a v2.0 audit closure and emit a new v2.1 audit closure."""

    root = Path(repository_root).resolve()
    source_path = Path(source_audit_path).resolve()
    source_receipt = Path(source_receipt_path).resolve()
    source = validate_v2_audit(source_path, repository_root=root)
    old_receipt = validate_v2_receipt(source_receipt, repository_root=root)
    if old_receipt["audit"]["artifact"] != artifact_reference(
        source_path, repository_root=root
    ):
        raise ContractError("SOFAUDIT v2.0 receipt does not bind the source audit")

    migrated = deepcopy(source)
    report_paths = {
        "reference": (
            Path(reference_report_path).resolve(),
            Path(reference_receipt_path).resolve(),
        ),
        "target": (
            Path(target_report_path).resolve(),
            Path(target_receipt_path).resolve(),
        ),
    }
    for side, (report_path, receipt_path) in report_paths.items():
        migrated["source_reports"][side] = _report_reference(
            source["source_reports"][side],
            report_path,
            receipt_path,
            root=root,
        )

    replacements = {
        "reference-report": artifact_reference(
            report_paths["reference"][0], repository_root=root
        ),
        "reference-report-validation-receipt": artifact_reference(
            report_paths["reference"][1], repository_root=root
        ),
        "target-report": artifact_reference(
            report_paths["target"][0], repository_root=root
        ),
        "target-report-validation-receipt": artifact_reference(
            report_paths["target"][1], repository_root=root
        ),
    }
    for item in migrated["source_artifacts"]:
        replacement = replacements.get(item["role"])
        if replacement is not None:
            item["uri"] = replacement["uri"]
            item["digest"] = replacement["digest"]

    for coordinate in migrated["coordinates"].values():
        binding = coordinate.get("report_item_binding", {})
        for side in ("reference", "target"):
            item_ref = binding.get(f"{side}_item_ref")
            if item_ref is not None:
                item_ref["artifact_digest"] = migrated["source_reports"][side][
                    "artifact"
                ]["digest"]

    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    implementation = _snapshot(
        Path(migrator_implementation_path or __file__).resolve(),
        output / "migrator" / "sofaudit-v2-to-v2_1.py",
    )
    migrated["sofaudit_version"] = "2.1"
    migrated["revision_provenance"] = {
        "kind": "explicit_v2_0_to_v2_1_migration",
        "source_version": "2.0",
        "source_artifact": artifact_reference(source_path, repository_root=root),
        "migration_implementation": artifact_reference(
            implementation, repository_root=root
        ),
    }
    migrated["attribution_boundary"] = deepcopy(
        SOFAUDIT_ATTRIBUTION_BOUNDARY
    )
    audit_path = write_json(output / "result.sofaudit.json", migrated)

    validator_snapshot = _snapshot(
        Path(__import__("sof_runtime.comparison.validation_v2_1", fromlist=["__file__"]).__file__).resolve(),
        output / "validator" / "sofaudit-validator.py",
    )
    audit_contract_snapshot = _snapshot(
        AUDIT_SCHEMA, output / "contracts" / "sofaudit.schema.json"
    )
    receipt_contract_snapshot = _snapshot(
        AUDIT_RECEIPT_SCHEMA,
        output / "contracts" / "sofaudit-validation-receipt.schema.json",
    )
    boundary_helper_snapshot = _snapshot(
        Path(__import__("sof_runtime.non_intervention", fromlist=["__file__"]).__file__).resolve(),
        output / "validator" / "non-intervention.py",
    )
    receipt = build_audit_validation_receipt(
        audit_path,
        repository_root=root,
        validator_implementation_path=validator_snapshot,
        audit_contract_path=audit_contract_snapshot,
        receipt_contract_path=receipt_contract_snapshot,
        boundary_helper_path=boundary_helper_snapshot,
        migration_source_receipt_path=source_receipt,
    )
    receipt_path = write_json(output / "validation-receipt.json", receipt)
    return {
        "audit": str(audit_path),
        "receipt": str(receipt_path),
        "audit_id": migrated["audit_id"],
    }
