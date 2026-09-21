"""Explicit SOFRS v2.0 to v2.1 boundary-annotation migration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.contracts.validation import write_json
from sof_runtime.non_intervention import SOFRS_OBJECT_TRANSITION_BOUNDARY
from sof_runtime.paths import PROJECT_ROOT

from .assembly_v2 import artifact_reference
from .validation_v2 import validate_receipt as validate_v2_receipt
from .validation_v2 import validate_report as validate_v2_report
from .validation_v2_1 import (
    RECEIPT_SCHEMA,
    REPORT_SCHEMA,
    build_validation_receipt,
)


def _snapshot(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def migrate_report(
    source_report_path: str | Path,
    source_receipt_path: str | Path,
    output_directory: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
    migrator_implementation_path: str | Path | None = None,
    **receipt_paths: Any,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    source_path = Path(source_report_path).resolve()
    source_receipt = Path(source_receipt_path).resolve()
    source = validate_v2_report(source_path, repository_root=root)
    receipt = validate_v2_receipt(source_receipt, repository_root=root)
    if receipt["report"]["artifact"] != artifact_reference(source_path, repository_root=root):
        raise ValueError("SOFRS v2.0 receipt does not bind the source report")
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    implementation_source = Path(migrator_implementation_path or __file__).resolve()
    implementation = _snapshot(
        implementation_source,
        output / "migrator" / "sofrs-v2-to-v2_1.py",
    )
    migrated = deepcopy(source)
    migrated["sofrs_version"] = "2.1"
    migrated["revision_provenance"] = {
        "kind": "explicit_v2_0_to_v2_1_migration",
        "source_version": "2.0",
        "source_artifact": artifact_reference(source_path, repository_root=root),
        "source_validation_receipt": artifact_reference(source_receipt, repository_root=root),
        "migration_implementation": artifact_reference(implementation, repository_root=root),
    }
    migrated["object_transition_boundary"] = deepcopy(
        SOFRS_OBJECT_TRANSITION_BOUNDARY
    )
    report_path = write_json(output / "result.sofreport.json", migrated)
    validator_snapshot = _snapshot(
        Path(__import__("sof_runtime.reporting.validation_v2_1", fromlist=["__file__"]).__file__).resolve(),
        output / "validator" / "sofrs-validator.py",
    )
    report_contract_snapshot = _snapshot(
        REPORT_SCHEMA,
        output / "contracts" / "sofrs.schema.json",
    )
    receipt_contract_snapshot = _snapshot(
        RECEIPT_SCHEMA,
        output / "contracts" / "sofrs-validation-receipt.schema.json",
    )
    boundary_helper_snapshot = _snapshot(
        Path(__import__("sof_runtime.non_intervention", fromlist=["__file__"]).__file__).resolve(),
        output / "validator" / "non-intervention.py",
    )
    new_receipt = build_validation_receipt(
        report_path,
        repository_root=root,
        validator_implementation_path=validator_snapshot,
        report_contract_path=report_contract_snapshot,
        receipt_contract_path=receipt_contract_snapshot,
        boundary_helper_path=boundary_helper_snapshot,
        **receipt_paths,
    )
    receipt_path = write_json(output / "validation-receipt.json", new_receipt)
    return {
        "report": str(report_path),
        "validation_receipt": str(receipt_path),
        "report_id": migrated["report_id"],
    }
