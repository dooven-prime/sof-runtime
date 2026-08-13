from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.artifacts.digest import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.paths import PROJECT_ROOT, REPORTING_CONTRACT_ROOT

from .assembly_v2 import (
    REPORT_SCHEMA,
    artifact_reference,
    assemble_report,
    resolve_artifact_reference,
)


RECEIPT_SCHEMA = REPORTING_CONTRACT_ROOT / "validation-receipt.schema.json"
REQUIRED_CHECKS = (
    "artifact-closure",
    "claim-compatibility",
    "claim-external-basis-binding",
    "compiler-output-recompilation",
    "cutoff-provenance",
    "record-kind-boundary",
    "report-assembly-recomputation",
    "schema-validation",
)
EXTERNAL_CONSTRAINT_IDS = {
    "source-snapshot-pinned",
    "object-level-recomputation",
    "realization-structure-validation",
    "domain-semantic-adequacy",
}
EXTERNAL_BASIS_LEVELS = {
    "source_identity",
    "object_level",
    "structure_level",
    "semantic_adequacy",
}
RESULT_CLAIM_STATUS = {
    "ESTABLISHED": "Theorem",
    "CERTIFIED": "Computational Certificate",
    "OBSERVED": "Computational Observation",
}
CLAIM_COMPATIBILITY = {
    ("external_mathematical_object", "object"): {
        "compiler_ir",
        "domain_adapter",
        "independent_validator",
        "external_evaluator",
    },
    ("empirical_domain_system", "object"): {
        "domain_adapter",
        "independent_validator",
        "external_evaluator",
    },
    ("empirical_domain_system", None): {
        "domain_adapter",
        "external_evaluator",
    },
    ("representation_interface", "protocol_conformance"): {
        "compiler_ir",
        "assembly_profile",
        "assembly_validator",
        "independent_validator",
    },
    ("representation_interface", None): {
        "domain_adapter",
        "migration_adapter",
    },
    ("protocol_conformance", "protocol_conformance"): {
        "compiler_ir",
        "assembly_profile",
        "assembly_validator",
        "independent_validator",
    },
    ("migration_consistency", "migration_assembly"): {
        "migration_adapter",
        "assembly_validator",
        "independent_validator",
    },
}
CLOSURE_ROLES = (
    "report",
    "capability_manifest",
    "typed_sof_ir",
    "compiler_profile",
    "compiler_output",
    "assembly_profile",
    "assembly_implementation",
)


def _presentation(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": report["report_id"],
        "system": report["system"],
        "strict_reconstruction": deepcopy(report["strict_reconstruction"]),
        "source_mapping": deepcopy(report["source_mapping"]),
        "source_artifacts": deepcopy(report["source_artifacts"]),
        "failure_modes": deepcopy(report["failure_modes"]),
        "provenance": deepcopy(report["provenance"]),
        # Alignment readiness is report-level declared metadata. Its source
        # artifacts and schema are validated before faithful assembly replay.
        "alignment_readiness": deepcopy(report["alignment_readiness"]),
        "external_basis_registry": deepcopy(report["external_basis_registry"]),
        "claim_classifications": {
            claim["claim_id"]: {
                "claim_target": claim["claim_target"],
                "certificate_class": claim["certificate_class"],
                "classification_source": claim["classification_source"],
                "external_basis_refs": deepcopy(claim["external_basis_refs"]),
                "external_constraint_ids": deepcopy(
                    claim["external_constraint_ids"]
                ),
            }
            for claim in report["claims"]
        },
    }


def _validate_claim_classification(report: dict[str, Any]) -> None:
    for claim in report["claims"]:
        expected_status = RESULT_CLAIM_STATUS.get(claim["result_state"])
        if expected_status is None or claim["claim_status"] != expected_status:
            raise ContractError(
                f"SOFRS claim {claim['claim_id']} has an illegal result/claim status pair"
            )
        certificate_class = claim["certificate_class"]
        if claim["claim_status"] == "Computational Certificate":
            if certificate_class is None:
                raise ContractError(
                    f"SOFRS claim {claim['claim_id']} lacks certificate_class"
                )
        elif certificate_class is not None:
            raise ContractError(
                f"SOFRS claim {claim['claim_id']} gives a class to a non-certificate"
            )
        allowed_sources = CLAIM_COMPATIBILITY.get(
            (claim["claim_target"], certificate_class)
        )
        if allowed_sources is None:
            raise ContractError(
                f"SOFRS claim {claim['claim_id']} has an incompatible target/class"
            )
        if claim["classification_source"] not in allowed_sources:
            raise ContractError(
                f"SOFRS claim {claim['claim_id']} has an incompatible classification source"
            )


def _resolve_basis_evidence(
    references: list[dict[str, Any]],
    *,
    source_artifacts: list[dict[str, Any]],
    repository_root: Path,
) -> None:
    for reference in references:
        if reference not in source_artifacts:
            raise ContractError("external basis evidence is outside source_artifacts")
        resolve_artifact_reference(reference, repository_root=repository_root)


def _validate_external_basis(report: dict[str, Any], *, repository_root: Path) -> None:
    registry = report["external_basis_registry"]
    packages = registry["packages"]
    package_by_id = {item["basis_id"]: item for item in packages}
    if len(package_by_id) != len(packages):
        raise ContractError("duplicate external basis package id")
    levels = {level: [] for level in EXTERNAL_BASIS_LEVELS}
    for package in packages:
        levels[package["level"]].append(package)
        _resolve_basis_evidence(
            package["evidence_artifacts"],
            source_artifacts=report["source_artifacts"],
            repository_root=repository_root,
        )
        if package["status"] == "SATISFIED" and not package["evidence_artifacts"]:
            raise ContractError("satisfied external basis package lacks evidence")

    constraints = registry["constraints"]
    constraint_by_id = {item["constraint_id"]: item for item in constraints}
    if set(constraint_by_id) != EXTERNAL_CONSTRAINT_IDS or len(constraint_by_id) != len(
        constraints
    ):
        raise ContractError("external basis constraint set is not exact")
    for constraint in constraints:
        package = package_by_id.get(constraint["basis_id"])
        if package is None or constraint["constraint_id"] not in package["constraint_ids"]:
            raise ContractError("external constraint is not bound to its basis package")
        if package["status"] != constraint["status"]:
            raise ContractError("external constraint status differs from basis package")
        _resolve_basis_evidence(
            constraint["evidence_artifacts"],
            source_artifacts=report["source_artifacts"],
            repository_root=repository_root,
        )
        if constraint["status"] == "SATISFIED" and not constraint["evidence_artifacts"]:
            raise ContractError("satisfied external constraint lacks evidence")

    expected_basis_status = "COMPLETE"
    if any(
        not levels[level]
        or any(item["status"] != "SATISFIED" for item in levels[level])
        for level in EXTERNAL_BASIS_LEVELS
    ) or any(item["status"] != "SATISFIED" for item in constraints):
        expected_basis_status = "PARTIAL"
    if registry["basis_status"] != expected_basis_status:
        raise ContractError("external basis status differs from validator recomputation")
    source_packages = levels["source_identity"]
    for package in source_packages:
        if package["status"] == "SATISFIED" and package["evidence_artifacts"] != report[
            "source_artifacts"
        ]:
            raise ContractError("source identity basis differs from source_artifacts")

    for claim in report["claims"]:
        for basis_id in claim["external_basis_refs"]:
            if basis_id not in package_by_id:
                raise ContractError(f"SOFRS claim {claim['claim_id']} has unknown basis")
        for constraint_id in claim["external_constraint_ids"]:
            constraint = constraint_by_id.get(constraint_id)
            if constraint is None or constraint["basis_id"] not in claim[
                "external_basis_refs"
            ]:
                raise ContractError(
                    f"SOFRS claim {claim['claim_id']} has an unbound external constraint"
                )
        if claim["certificate_class"] == "object":
            object_packages = [
                package_by_id[basis_id]
                for basis_id in claim["external_basis_refs"]
                if package_by_id[basis_id]["level"] == "object_level"
            ]
            if not object_packages or any(
                package["status"] != "SATISFIED"
                or not package["evidence_artifacts"]
                for package in object_packages
            ):
                raise ContractError("Object Certificate lacks satisfied object basis")
            if "object-level-recomputation" not in claim["external_constraint_ids"]:
                raise ContractError("Object Certificate lacks object constraint")
    if report["record_kind"] == "strict_sof" and (
        not levels["structure_level"]
        or any(item["status"] != "SATISFIED" for item in levels["structure_level"])
    ):
        raise ContractError("strict_sof report lacks satisfied structure basis")


def _report_input_paths(
    report: dict[str, Any],
    *,
    repository_root: str | Path,
) -> dict[str, Path]:
    contracts = report["compiler_contracts"]
    references = {
        "manifest": contracts["capability_manifest"],
        "ir": contracts["typed_sof_ir"],
        "compiler_profile": contracts["compiler_profile"],
        "compiler_output": contracts["compiler_output"],
        "assembly_profile": report["assembly_contract"]["assembly_profile"],
        "assembly_implementation": report["assembly_contract"]["implementation"],
    }
    return {
        role: resolve_artifact_reference(reference, repository_root=repository_root)
        for role, reference in references.items()
    }


def _validate_identity_mapping(report: dict[str, Any]) -> None:
    bindings = report["item_bindings"]
    source_ids = [item["compiler_output_item_id"] for item in bindings]
    report_ids = [item["report_item_id"] for item in bindings]
    if len(source_ids) != len(set(source_ids)):
        raise ContractError("SOFRS item bindings duplicate a CompilerOutput item")
    if len(report_ids) != len(set(report_ids)):
        raise ContractError("SOFRS item bindings duplicate a report item")

    normative = report["claims"] + report["degradation_items"]
    normative_ids = [item["report_item_id"] for item in normative]
    normative_source_ids = [item["source_output_item_id"] for item in normative]
    if set(report_ids) != set(normative_ids):
        raise ContractError("SOFRS item bindings differ from rendered normative items")
    if set(source_ids) != set(normative_source_ids):
        raise ContractError("SOFRS normative items differ from bound CompilerOutput items")


def validate_report(
    report_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    report = load_json(report_path)
    validate_contract(report, REPORT_SCHEMA, label="SOFRS v2 report")
    _validate_identity_mapping(report)
    _validate_claim_classification(report)
    _validate_external_basis(report, repository_root=root)

    if report["source_mapping"]["status"] == "heuristic":
        raise ContractError("heuristic source mappings cannot enter SOFRS")
    for reference in report["source_artifacts"]:
        resolve_artifact_reference(reference, repository_root=root)

    paths = _report_input_paths(report, repository_root=root)
    compiler_output = load_json(paths["compiler_output"])
    binding = report["compiler_output_binding"]
    if binding["artifact"] != report["compiler_contracts"]["compiler_output"]:
        raise ContractError("direct CompilerOutput binding differs from compiler contracts")
    for report_field, output_field in (
        ("compiler_id", "compiler_id"),
        ("compiler_output_version", "compiler_output_version"),
        ("compiler_profile_id", "profile_id"),
    ):
        if binding[report_field] != compiler_output[output_field]:
            raise ContractError(f"CompilerOutput binding {report_field} mismatch")

    expected = assemble_report(
        paths["manifest"],
        paths["ir"],
        paths["compiler_profile"],
        paths["compiler_output"],
        paths["assembly_profile"],
        assembly_implementation=report["assembly_contract"]["implementation"],
        presentation=_presentation(report),
        repository_root=root,
        verify_artifacts=True,
    )
    if report != expected:
        raise ContractError(
            "SOFRS report differs from faithful Assemble_v2 recomputation"
        )
    return report


def _closure_digest(ordered_artifacts: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": sha256_bytes(canonical_json_bytes(ordered_artifacts)),
    }


def build_validation_receipt(
    report_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
    validator_implementation_path: str | Path | None = None,
    receipt_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    report_path = Path(report_path).resolve()
    report = validate_report(report_path, repository_root=root)
    contracts = report["compiler_contracts"]
    ordered_artifacts = [
        {
            "role": "report",
            "artifact": artifact_reference(report_path, repository_root=root),
        },
        {"role": "capability_manifest", "artifact": contracts["capability_manifest"]},
        {"role": "typed_sof_ir", "artifact": contracts["typed_sof_ir"]},
        {"role": "compiler_profile", "artifact": contracts["compiler_profile"]},
        {"role": "compiler_output", "artifact": contracts["compiler_output"]},
        {
            "role": "assembly_profile",
            "artifact": report["assembly_contract"]["assembly_profile"],
        },
        {
            "role": "assembly_implementation",
            "artifact": report["assembly_contract"]["implementation"],
        },
    ]
    validator_path = Path(validator_implementation_path or __file__).resolve()
    receipt = {
        "receipt_version": "2.0",
        "artifact_type": "sofrs_report_validation_receipt",
        "receipt_id": f"receipt.{report['report_id']}.sofrs-v2",
        "report": {
            "report_id": report["report_id"],
            "sofrs_version": "2.0",
            "record_kind": report["record_kind"],
            "artifact": ordered_artifacts[0]["artifact"],
        },
        "validator": {
            "validator_id": "sofrs.report-validator.v2",
            "validator_version": "2.0",
            "implementation": artifact_reference(validator_path, repository_root=root),
            "receipt_contract": deepcopy(receipt_contract)
            if receipt_contract is not None
            else artifact_reference(RECEIPT_SCHEMA, repository_root=root),
        },
        "artifact_closure": {
            "artifact_count": len(ordered_artifacts),
            "ordered_artifacts": ordered_artifacts,
            "closure_digest": _closure_digest(ordered_artifacts),
        },
        "status": "PASS",
        "checks": [
            {"check_id": check_id, "status": "PASS"}
            for check_id in REQUIRED_CHECKS
        ],
        "negative_boundaries": [
            "This receipt validates faithful SOFRS assembly and its bound compiler-contract closure; it does not establish adapter scientific adequacy, cross-report alignment, or downstream interpretation."
        ],
    }
    validate_contract(receipt, RECEIPT_SCHEMA, label="SOFRS validation receipt")
    return receipt


def validate_receipt(
    receipt_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    receipt = load_json(receipt_path)
    validate_contract(receipt, RECEIPT_SCHEMA, label="SOFRS validation receipt")

    checks = [item["check_id"] for item in receipt["checks"]]
    if len(checks) != len(set(checks)) or set(checks) != set(REQUIRED_CHECKS):
        raise ContractError("SOFRS receipt check set is not exact")
    closure = receipt["artifact_closure"]
    ordered = closure["ordered_artifacts"]
    if [item["role"] for item in ordered] != list(CLOSURE_ROLES):
        raise ContractError("SOFRS receipt closure role order is not canonical")
    if closure["artifact_count"] != len(ordered):
        raise ContractError("SOFRS receipt artifact count mismatch")
    if closure["closure_digest"] != _closure_digest(ordered):
        raise ContractError("SOFRS receipt closure digest mismatch")

    for item in ordered:
        resolve_artifact_reference(item["artifact"], repository_root=root)
    validator_path = resolve_artifact_reference(
        receipt["validator"]["implementation"], repository_root=root
    )
    if sha256_file(validator_path) != sha256_file(Path(__file__).resolve()):
        raise ContractError("SOFRS receipt binds a different validator implementation")
    receipt_contract_path = resolve_artifact_reference(
        receipt["validator"]["receipt_contract"], repository_root=root
    )
    if sha256_file(receipt_contract_path) != sha256_file(RECEIPT_SCHEMA):
        raise ContractError("SOFRS receipt binds a different receipt contract")

    report_ref = ordered[0]["artifact"]
    if receipt["report"]["artifact"] != report_ref:
        raise ContractError("SOFRS receipt report reference differs from closure")
    report_path = resolve_artifact_reference(report_ref, repository_root=root)
    report = validate_report(report_path, repository_root=root)
    for field in ("report_id", "sofrs_version", "record_kind"):
        if receipt["report"][field] != report[field]:
            raise ContractError(f"SOFRS receipt {field} differs from report")

    expected_inputs = [
        report["compiler_contracts"]["capability_manifest"],
        report["compiler_contracts"]["typed_sof_ir"],
        report["compiler_contracts"]["compiler_profile"],
        report["compiler_contracts"]["compiler_output"],
        report["assembly_contract"]["assembly_profile"],
        report["assembly_contract"]["implementation"],
    ]
    if [item["artifact"] for item in ordered[1:]] != expected_inputs:
        raise ContractError("SOFRS receipt closure differs from report inputs")
    return receipt
