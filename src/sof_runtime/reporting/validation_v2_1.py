"""Runtime validation and receipts for SOFRS v2.1."""

from __future__ import annotations

import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.artifacts.digest import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.contracts.validation import write_json
from sof_runtime.non_intervention import (
    SOFRS_FORBIDDEN_KEYS,
    SOFRS_OBJECT_TRANSITION_BOUNDARY,
    forbidden_key_paths,
)
from sof_runtime.paths import PROJECT_ROOT, REPORTING_V2_1_CONTRACT_ROOT

from .assembly_v2 import artifact_reference, resolve_artifact_reference
from .validation_v2 import validate_receipt as validate_v2_receipt
from .validation_v2 import validate_report as validate_v2_report


REPORT_SCHEMA = REPORTING_V2_1_CONTRACT_ROOT / "sofrs.schema.json"
RECEIPT_SCHEMA = REPORTING_V2_1_CONTRACT_ROOT / "validation-receipt.schema.json"
COMMON_CHECKS = {
    "artifact-closure",
    "assembly-faithfulness",
    "claim-compatibility",
    "degradation-semantics",
    "forbidden-semantic-role-scan",
    "report-non-intervention",
    "schema-validation",
}
MIGRATION_CHECKS = COMMON_CHECKS | {
    "explicit-v2.0-to-v2.1-migration",
    "v2.0-source-validation",
}
NATIVE_CHECKS = COMMON_CHECKS | {
    "generation-input-closure",
    "native-v2.1-generation",
}


def _v2_projection(report: dict[str, Any]) -> dict[str, Any]:
    projection = deepcopy(report)
    projection["sofrs_version"] = "2.0"
    projection.pop("revision_provenance", None)
    projection.pop("object_transition_boundary", None)
    return projection


def _validate_reference(reference: dict[str, Any], root: Path, label: str) -> Path:
    try:
        return resolve_artifact_reference(reference, repository_root=root)
    except (KeyError, TypeError, ContractError) as error:
        raise ContractError(f"{label}: {error}") from error


def validate_report(
    report_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    path = Path(report_path).resolve()
    report = load_json(path)
    validate_contract(report, REPORT_SCHEMA, label="SOFRS v2.1 report")
    violations = forbidden_key_paths(report, SOFRS_FORBIDDEN_KEYS)
    if violations:
        raise ContractError(
            "SOFRS v2.1 contains forbidden semantic fields: "
            + ", ".join(violations)
        )
    if report["object_transition_boundary"] != SOFRS_OBJECT_TRANSITION_BOUNDARY:
        raise ContractError("SOFRS v2.1 object-transition boundary differs")

    revision = report["revision_provenance"]
    if revision["kind"] == "native_v2_1_generation":
        _validate_reference(
            revision["generation_implementation"], root, "generation implementation"
        )
        for index, reference in enumerate(revision["generation_inputs"]):
            _validate_reference(reference, root, f"generation input {index}")
        with tempfile.TemporaryDirectory(prefix="sof-runtime-sofrs-v2_1-") as tmp:
            projection_path = write_json(
                Path(tmp) / "projection.sofreport.json", _v2_projection(report)
            )
            validate_v2_report(projection_path, repository_root=root)
        return report

    source_path = _validate_reference(
        revision["source_artifact"], root, "v2.0 source report"
    )
    source_receipt_path = _validate_reference(
        revision["source_validation_receipt"], root, "v2.0 source receipt"
    )
    _validate_reference(
        revision["migration_implementation"], root, "migration implementation"
    )
    source = validate_v2_report(source_path, repository_root=root)
    source_receipt = validate_v2_receipt(source_receipt_path, repository_root=root)
    if source_receipt["report"]["artifact"] != revision["source_artifact"]:
        raise ContractError("v2.0 source receipt binds a different report")
    expected = deepcopy(source)
    expected["sofrs_version"] = "2.1"
    expected["revision_provenance"] = deepcopy(revision)
    expected["object_transition_boundary"] = deepcopy(
        SOFRS_OBJECT_TRANSITION_BOUNDARY
    )
    if report != expected:
        raise ContractError(
            "SOFRS v2.1 migration differs from the exact v2.0 boundary projection"
        )
    return report


def _generation(receipt_source: dict[str, Any]) -> dict[str, Any]:
    revision = receipt_source["revision_provenance"]
    if revision["kind"] == "explicit_v2_0_to_v2_1_migration":
        return {
            "kind": "migration",
            "class": "boundary_annotation",
            "source_version": "2.0",
            "source_artifact": deepcopy(revision["source_artifact"]),
            "source_validation_receipt": deepcopy(
                revision["source_validation_receipt"]
            ),
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


def build_validation_receipt(
    report_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
    validator_implementation_path: str | Path | None = None,
    report_contract_path: str | Path | None = None,
    receipt_contract_path: str | Path | None = None,
    boundary_helper_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    path = Path(report_path).resolve()
    report = validate_report(path, repository_root=root)
    validator_path = Path(validator_implementation_path or __file__).resolve()
    report_contract = Path(report_contract_path or REPORT_SCHEMA).resolve()
    receipt_contract = Path(receipt_contract_path or RECEIPT_SCHEMA).resolve()
    boundary_helper = Path(
        boundary_helper_path
        or __import__("sof_runtime.non_intervention", fromlist=["__file__"]).__file__
    ).resolve()
    revision = report["revision_provenance"]
    ordered = [
        {"role": "report", "artifact": artifact_reference(path, repository_root=root)}
    ]
    if revision["kind"] == "explicit_v2_0_to_v2_1_migration":
        ordered.extend(
            [
                {"role": "revision-source-report-v2.0", "artifact": revision["source_artifact"]},
                {"role": "source-validation-receipt-v2.0", "artifact": revision["source_validation_receipt"]},
                {"role": "migration-implementation", "artifact": revision["migration_implementation"]},
            ]
        )
    else:
        ordered.append(
            {"role": "generation-implementation", "artifact": revision["generation_implementation"]}
        )
        ordered.extend(
            {"role": f"generation-input-{index}", "artifact": reference}
            for index, reference in enumerate(revision["generation_inputs"])
        )
    contracts = report["compiler_contracts"]
    ordered.extend(
        [
            {"role": "boundary-helper", "artifact": artifact_reference(boundary_helper, repository_root=root)},
            {"role": "report-contract", "artifact": artifact_reference(report_contract, repository_root=root)},
            {"role": "capability-manifest", "artifact": contracts["capability_manifest"]},
            {"role": "typed-sof-ir", "artifact": contracts["typed_sof_ir"]},
            {"role": "compiler-profile", "artifact": contracts["compiler_profile"]},
            {"role": "compiler-output", "artifact": contracts["compiler_output"]},
            {"role": "assembly-profile", "artifact": report["assembly_contract"]["assembly_profile"]},
            {"role": "assembly-implementation", "artifact": report["assembly_contract"]["implementation"]},
            {"role": "validator-implementation", "artifact": artifact_reference(validator_path, repository_root=root)},
            {"role": "validation-receipt-contract", "artifact": artifact_reference(receipt_contract, repository_root=root)},
        ]
    )
    role_map = {item["role"]: item["artifact"] for item in ordered}
    checks = (
        MIGRATION_CHECKS
        if revision["kind"] == "explicit_v2_0_to_v2_1_migration"
        else NATIVE_CHECKS
    )
    receipt = {
        "receipt_version": "2.1",
        "artifact_type": "sofrs_report_validation_receipt",
        "receipt_kind": "SOFRS_VALIDATION_RECEIPT",
        "receipt_scope": "SOFRS_PROTOCOL_CONFORMANCE_ONLY",
        "receipt_id": f"receipt.{report['report_id']}.sofrs-v2_1",
        "report": {
            "report_id": report["report_id"],
            "sofrs_version": "2.1",
            "record_kind": report["record_kind"],
            "artifact": role_map["report"],
        },
        "validator": {
            "validator_id": "sofrs.report-validator.v2_1",
            "validator_version": "2.1",
            "implementation": role_map["validator-implementation"],
            "report_contract": role_map["report-contract"],
            "receipt_contract": role_map["validation-receipt-contract"],
        },
        "generation": _generation(report),
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
        "object_transition_boundary": {
            "intervention_semantics": "NONE",
            "source_state_transition_authority": "NONE",
            "implementation_purity_status": "NOT_ESTABLISHED_BY_SOFRS",
        },
        "negative_boundaries": [
            "This receipt establishes SOFRS protocol conformance only; it neither induces nor authorizes an object-state transition, and it does not establish implementation purity."
        ],
    }
    validate_contract(receipt, RECEIPT_SCHEMA, label="SOFRS v2.1 receipt")
    return receipt


def validate_receipt(
    receipt_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    receipt = load_json(receipt_path)
    validate_contract(receipt, RECEIPT_SCHEMA, label="SOFRS v2.1 receipt")
    expected_checks = (
        MIGRATION_CHECKS
        if receipt["generation"]["kind"] == "migration"
        else NATIVE_CHECKS
    )
    checks = [item["check_id"] for item in receipt["checks"]]
    if len(checks) != len(set(checks)) or set(checks) != expected_checks:
        raise ContractError("SOFRS v2.1 receipt check set is not exact")
    closure = receipt["artifact_closure"]
    ordered = closure["ordered_artifacts"]
    if closure["artifact_count"] != len(ordered):
        raise ContractError("SOFRS v2.1 receipt artifact count differs")
    if closure["closure_digest"] != _closure_digest(ordered):
        raise ContractError("SOFRS v2.1 receipt closure digest differs")
    roles = [item["role"] for item in ordered]
    if len(roles) != len(set(roles)):
        raise ContractError("SOFRS v2.1 receipt roles are not unique")
    role_map = {item["role"]: item["artifact"] for item in ordered}
    for item in ordered:
        _validate_reference(item["artifact"], root, f"receipt role {item['role']}")
    if receipt["report"]["artifact"] != role_map.get("report"):
        raise ContractError("SOFRS v2.1 receipt report differs from closure")
    report_path = _validate_reference(receipt["report"]["artifact"], root, "receipt report")
    report = validate_report(report_path, repository_root=root)
    if receipt["generation"] != _generation(report):
        raise ContractError("SOFRS v2.1 receipt generation differs from report")
    for field in ("report_id", "sofrs_version", "record_kind"):
        if receipt["report"][field] != report[field]:
            raise ContractError(f"SOFRS v2.1 receipt {field} differs")
    validator_path = _validate_reference(
        receipt["validator"]["implementation"], root, "receipt validator"
    )
    report_contract = _validate_reference(
        receipt["validator"]["report_contract"], root, "report contract"
    )
    receipt_contract = _validate_reference(
        receipt["validator"]["receipt_contract"], root, "receipt contract"
    )
    if sha256_file(validator_path) != sha256_file(Path(__file__).resolve()):
        raise ContractError("SOFRS v2.1 receipt binds another validator")
    if sha256_file(report_contract) != sha256_file(REPORT_SCHEMA):
        raise ContractError("SOFRS v2.1 receipt binds another report contract")
    if sha256_file(receipt_contract) != sha256_file(RECEIPT_SCHEMA):
        raise ContractError("SOFRS v2.1 receipt binds another receipt contract")
    return receipt
