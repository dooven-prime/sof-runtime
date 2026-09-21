"""Runtime semantic validation and receipts for SOFAUDIT v2.1."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import FunctionType
from typing import Any

from sof_runtime.artifacts.digest import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.non_intervention import (
    SOFAUDIT_ATTRIBUTION_BOUNDARY,
    SOFAUDIT_FORBIDDEN_KEYS,
    forbidden_key_paths,
)
from sof_runtime.paths import COMPARISON_V2_1_CONTRACT_ROOT, PROJECT_ROOT
from sof_runtime.reporting.assembly_v2 import artifact_reference, resolve_artifact_reference
from sof_runtime.reporting.validation_v2_1 import (
    validate_receipt as validate_report_receipt,
)
from sof_runtime.reporting.validation_v2_1 import validate_report

from . import validation_v2 as legacy


AUDIT_SCHEMA = COMPARISON_V2_1_CONTRACT_ROOT / "sofaudit.schema.json"
AUDIT_RECEIPT_SCHEMA = COMPARISON_V2_1_CONTRACT_ROOT / "validation-receipt.schema.json"
COMMON_CHECKS = {
    "aligned-difference-without-attribution",
    "artifact-digest-closure",
    "forbidden-semantic-role-scan",
    "reference-role-boundary",
    "schema-validation",
    "source-report-receipt-validation",
}
MIGRATION_CHECKS = COMMON_CHECKS | {
    "explicit-v2.0-to-v2.1-migration",
    "v2.0-source-validation",
}
NATIVE_CHECKS = COMMON_CHECKS | {
    "generation-input-closure",
    "native-v2.1-generation",
}


def _reference(item: dict[str, Any]) -> dict[str, Any]:
    return {"uri": item["uri"], "digest": deepcopy(item["digest"])}


def _resolve(reference: dict[str, Any], root: Path, label: str) -> Path:
    try:
        return resolve_artifact_reference(reference, repository_root=root)
    except (KeyError, TypeError, ContractError) as error:
        raise ContractError(f"{label}: {error}") from error


def _semantic_projection(audit: dict[str, Any]) -> dict[str, Any]:
    projection = deepcopy(audit)
    projection["sofaudit_version"] = "2.0"
    projection.pop("revision_provenance", None)
    projection.pop("attribution_boundary", None)
    for side in ("reference", "target"):
        projection["source_reports"][side]["sofrs_version"] = "2.0"
        projection["source_reports"][side]["admission_basis"] = "native_sofrs_v2"
    return projection


def _projected_report_validator(
    path: str | Path, *, repository_root: str | Path = PROJECT_ROOT
) -> dict[str, Any]:
    report = validate_report(path, repository_root=repository_root)
    projection = deepcopy(report)
    projection["sofrs_version"] = "2.0"
    projection.pop("revision_provenance", None)
    projection.pop("object_transition_boundary", None)
    return projection


def _projected_receipt_validator(
    path: str | Path, *, repository_root: str | Path = PROJECT_ROOT
) -> dict[str, Any]:
    receipt = validate_report_receipt(path, repository_root=repository_root)
    projection = deepcopy(receipt)
    projection["receipt_version"] = "2.0"
    projection["report"]["sofrs_version"] = "2.0"
    return projection


def _validate_legacy_projection(
    projection: dict[str, Any],
    root: Path,
    reports: dict[Path, dict[str, Any]],
    receipts: dict[Path, dict[str, Any]],
) -> None:
    def report_validator(
        path: str | Path, *, repository_root: str | Path = PROJECT_ROOT
    ) -> dict[str, Any]:
        resolved = Path(path).resolve()
        report = reports.get(resolved)
        if report is None:
            return _projected_report_validator(
                resolved, repository_root=repository_root
            )
        result = deepcopy(report)
        result["sofrs_version"] = "2.0"
        result.pop("revision_provenance", None)
        result.pop("object_transition_boundary", None)
        return result

    def receipt_validator(
        path: str | Path, *, repository_root: str | Path = PROJECT_ROOT
    ) -> dict[str, Any]:
        resolved = Path(path).resolve()
        receipt = receipts.get(resolved)
        if receipt is None:
            return _projected_receipt_validator(
                resolved, repository_root=repository_root
            )
        result = deepcopy(receipt)
        result["receipt_version"] = "2.0"
        result["report"]["sofrs_version"] = "2.0"
        return result

    isolated_globals = dict(legacy._validate_semantics.__globals__)
    isolated_globals["validate_report"] = report_validator
    isolated_globals["validate_receipt"] = receipt_validator
    isolated_validator = FunctionType(
        legacy._validate_semantics.__code__,
        isolated_globals,
        legacy._validate_semantics.__name__,
        legacy._validate_semantics.__defaults__,
        legacy._validate_semantics.__closure__,
    )
    isolated_validator(projection, repository_root=root)


def _validate_linked_reports(
    audit: dict[str, Any], root: Path
) -> tuple[dict[Path, dict[str, Any]], dict[Path, dict[str, Any]]]:
    reports: dict[Path, dict[str, Any]] = {}
    receipts: dict[Path, dict[str, Any]] = {}
    for side in ("reference", "target"):
        reference = audit["source_reports"][side]
        report_path = _resolve(reference["artifact"], root, f"{side} report")
        receipt_path = _resolve(
            reference["validation_receipt"], root, f"{side} report receipt"
        )
        receipt = validate_report_receipt(receipt_path, repository_root=root)
        report = load_json(report_path)
        if reference["sofrs_version"] != "2.1" or report["sofrs_version"] != "2.1":
            raise ContractError("SOFAUDIT v2.1 consumes only SOFRS v2.1")
        if (
            receipt["report"]["artifact"]["digest"]
            != reference["artifact"]["digest"]
            or receipt["report"]["report_id"] != reference["report_id"]
        ):
            raise ContractError(f"{side} receipt binds a different report")
        reports[report_path.resolve()] = report
        receipts[receipt_path.resolve()] = receipt
    return reports, receipts


def _validate_migration_projection(
    source: dict[str, Any],
    audit: dict[str, Any],
    root: Path,
    reports: dict[Path, dict[str, Any]],
) -> None:
    expected = deepcopy(source)
    for side in ("reference", "target"):
        old_reference = source["source_reports"][side]
        new_reference = audit["source_reports"][side]
        report_path = _resolve(new_reference["artifact"], root, f"{side} report")
        report = reports[report_path.resolve()]
        report_revision = report["revision_provenance"]
        if (
            report_revision["kind"] != "explicit_v2_0_to_v2_1_migration"
            or report_revision["source_artifact"] != old_reference["artifact"]
            or report_revision["source_validation_receipt"]
            != old_reference["validation_receipt"]
        ):
            raise ContractError(
                f"{side} SOFRS v2.1 report is not the explicit migration of the v2.0 source"
            )
        projected_reference = deepcopy(old_reference)
        projected_reference["artifact"] = deepcopy(new_reference["artifact"])
        projected_reference["validation_receipt"] = deepcopy(
            new_reference["validation_receipt"]
        )
        projected_reference["sofrs_version"] = "2.1"
        projected_reference["admission_basis"] = "native_sofrs_v2_1"
        expected["source_reports"][side] = projected_reference

    replacements = {
        "reference-report": expected["source_reports"]["reference"]["artifact"],
        "reference-report-validation-receipt": expected["source_reports"]["reference"]["validation_receipt"],
        "target-report": expected["source_reports"]["target"]["artifact"],
        "target-report-validation-receipt": expected["source_reports"]["target"]["validation_receipt"],
    }
    for item in expected["source_artifacts"]:
        replacement = replacements.get(item["role"])
        if replacement is not None:
            item["uri"] = replacement["uri"]
            item["digest"] = deepcopy(replacement["digest"])
    for coordinate in expected["coordinates"].values():
        binding = coordinate.get("report_item_binding", {})
        for side in ("reference", "target"):
            item_ref = binding.get(f"{side}_item_ref")
            if item_ref is not None:
                item_ref["artifact_digest"] = deepcopy(
                    expected["source_reports"][side]["artifact"]["digest"]
                )
    expected["sofaudit_version"] = "2.1"
    expected["revision_provenance"] = deepcopy(audit["revision_provenance"])
    expected["attribution_boundary"] = deepcopy(SOFAUDIT_ATTRIBUTION_BOUNDARY)
    if audit != expected:
        raise ContractError(
            "SOFAUDIT v2.1 migration differs from the exact v2.0 boundary projection"
        )


def validate_audit(
    audit_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    audit = load_json(audit_path)
    validate_contract(audit, AUDIT_SCHEMA, label="SOFAUDIT v2.1 audit")
    violations = forbidden_key_paths(audit, SOFAUDIT_FORBIDDEN_KEYS)
    if violations:
        raise ContractError(
            "SOFAUDIT v2.1 contains forbidden attribution fields: "
            + ", ".join(violations)
        )
    if audit["attribution_boundary"] != SOFAUDIT_ATTRIBUTION_BOUNDARY:
        raise ContractError("SOFAUDIT v2.1 attribution boundary differs")
    reports, receipts = _validate_linked_reports(audit, root)
    revision = audit["revision_provenance"]
    if revision["kind"] == "native_v2_1_generation":
        _resolve(
            revision["generation_implementation"], root, "generation implementation"
        )
        for index, reference in enumerate(revision["generation_inputs"]):
            _resolve(reference, root, f"generation input {index}")
    else:
        source_path = _resolve(
            revision["source_artifact"], root, "v2.0 source audit"
        )
        _resolve(
            revision["migration_implementation"], root, "migration implementation"
        )
        source = legacy.validate_audit(source_path, repository_root=root)
        _validate_migration_projection(source, audit, root, reports)

    projection = _semantic_projection(audit)
    _validate_legacy_projection(
        projection,
        root,
        reports,
        receipts,
    )
    return audit


def _generation(audit: dict[str, Any]) -> dict[str, Any]:
    revision = audit["revision_provenance"]
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


def build_audit_validation_receipt(
    audit_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
    validator_implementation_path: str | Path | None = None,
    audit_contract_path: str | Path | None = None,
    receipt_contract_path: str | Path | None = None,
    boundary_helper_path: str | Path | None = None,
    migration_source_receipt_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    path = Path(audit_path).resolve()
    audit = validate_audit(path, repository_root=root)
    validator_path = Path(validator_implementation_path or __file__).resolve()
    audit_contract = Path(audit_contract_path or AUDIT_SCHEMA).resolve()
    receipt_contract = Path(receipt_contract_path or AUDIT_RECEIPT_SCHEMA).resolve()
    boundary_helper = Path(
        boundary_helper_path
        or __import__("sof_runtime.non_intervention", fromlist=["__file__"]).__file__
    ).resolve()
    revision = audit["revision_provenance"]
    ordered = [
        {"role": "audit", "artifact": artifact_reference(path, repository_root=root)}
    ]
    if revision["kind"] == "explicit_v2_0_to_v2_1_migration":
        if migration_source_receipt_path is None:
            raise ContractError(
                "SOFAUDIT migration receipt requires the v2.0 source receipt"
            )
        ordered.extend(
            [
                {"role": "revision-source-audit-v2.0", "artifact": revision["source_artifact"]},
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
            {"role": "audit-contract", "artifact": artifact_reference(audit_contract, repository_root=root)},
            *[
                {"role": item["role"], "artifact": _reference(item)}
                for item in audit["source_artifacts"]
            ],
            {"role": "validator-implementation", "artifact": artifact_reference(validator_path, repository_root=root)},
            {"role": "validation-receipt-contract", "artifact": artifact_reference(receipt_contract, repository_root=root)},
        ]
    )
    roles = [item["role"] for item in ordered]
    if len(roles) != len(set(roles)):
        raise ContractError("SOFAUDIT v2.1 receipt roles are not unique")
    role_map = {item["role"]: item["artifact"] for item in ordered}
    checks = (
        MIGRATION_CHECKS
        if revision["kind"] == "explicit_v2_0_to_v2_1_migration"
        else NATIVE_CHECKS
    )
    receipt = {
        "receipt_version": "2.1",
        "artifact_type": "sofaudit_validation_receipt",
        "receipt_kind": "SOFAUDIT_VALIDATION_RECEIPT",
        "receipt_scope": "SOFAUDIT_PROTOCOL_CONFORMANCE_ONLY",
        "receipt_id": f"receipt.{audit['audit_id']}.sofaudit-v2_1",
        "audit": {
            "audit_id": audit["audit_id"],
            "sofaudit_version": "2.1",
            "artifact": role_map["audit"],
        },
        "validator": {
            "validator_id": "sofaudit.semantic-validator.v2_1",
            "validator_version": "2.1",
            "implementation": role_map["validator-implementation"],
            "audit_contract": role_map["audit-contract"],
            "receipt_contract": role_map["validation-receipt-contract"],
        },
        "generation": _generation(audit),
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
        "attribution_boundary": {
            "causal_status": "OUT_OF_SCOPE_FOR_SOFAUDIT",
            "defect_attribution_status": "OUT_OF_SCOPE_FOR_SOFAUDIT",
            "reference_causal_role": "NOT_A_CAUSAL_BASELINE",
        },
        "negative_boundaries": [
            "This receipt establishes aligned comparison conformance only; it establishes neither defect attribution nor causality."
        ],
    }
    validate_contract(receipt, AUDIT_RECEIPT_SCHEMA, label="SOFAUDIT v2.1 receipt")
    return receipt


def validate_audit_validation_receipt(
    receipt_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    receipt = load_json(receipt_path)
    validate_contract(receipt, AUDIT_RECEIPT_SCHEMA, label="SOFAUDIT v2.1 receipt")
    expected_checks = (
        MIGRATION_CHECKS
        if receipt["generation"]["kind"] == "migration"
        else NATIVE_CHECKS
    )
    checks = [item["check_id"] for item in receipt["checks"]]
    if len(checks) != len(set(checks)) or set(checks) != expected_checks:
        raise ContractError("SOFAUDIT v2.1 receipt check set is not exact")
    closure = receipt["artifact_closure"]
    ordered = closure["ordered_artifacts"]
    if closure["artifact_count"] != len(ordered):
        raise ContractError("SOFAUDIT v2.1 receipt artifact count differs")
    if closure["closure_digest"] != _closure_digest(ordered):
        raise ContractError("SOFAUDIT v2.1 receipt closure digest differs")
    roles = [item["role"] for item in ordered]
    if len(roles) != len(set(roles)):
        raise ContractError("SOFAUDIT v2.1 receipt roles are not unique")
    role_map = {item["role"]: item["artifact"] for item in ordered}
    for item in ordered:
        _resolve(item["artifact"], root, f"receipt role {item['role']}")
    if receipt["audit"]["artifact"] != role_map.get("audit"):
        raise ContractError("SOFAUDIT v2.1 receipt audit differs from closure")
    audit_path = _resolve(receipt["audit"]["artifact"], root, "receipt audit")
    audit = validate_audit(audit_path, repository_root=root)
    if receipt["generation"] != _generation(audit):
        raise ContractError("SOFAUDIT v2.1 receipt generation differs from audit")
    if receipt["generation"]["kind"] == "migration":
        source_receipt_ref = role_map.get("source-validation-receipt-v2.0")
        if source_receipt_ref is None:
            raise ContractError("SOFAUDIT migration receipt omits the v2.0 receipt")
        source_receipt_path = _resolve(
            source_receipt_ref, root, "v2.0 source receipt"
        )
        source_receipt = legacy.validate_audit_validation_receipt(
            source_receipt_path, repository_root=root
        )
        if source_receipt["audit"]["artifact"] != receipt["generation"]["source_artifact"]:
            raise ContractError("SOFAUDIT v2.0 receipt binds another source audit")
    validator_path = _resolve(
        receipt["validator"]["implementation"], root, "receipt validator"
    )
    audit_contract = _resolve(
        receipt["validator"]["audit_contract"], root, "audit contract"
    )
    receipt_contract = _resolve(
        receipt["validator"]["receipt_contract"], root, "receipt contract"
    )
    if sha256_file(validator_path) != sha256_file(Path(__file__).resolve()):
        raise ContractError("SOFAUDIT v2.1 receipt binds another validator")
    if sha256_file(audit_contract) != sha256_file(AUDIT_SCHEMA):
        raise ContractError("SOFAUDIT v2.1 receipt binds another audit contract")
    if sha256_file(receipt_contract) != sha256_file(AUDIT_RECEIPT_SCHEMA):
        raise ContractError("SOFAUDIT v2.1 receipt binds another receipt contract")
    return receipt
