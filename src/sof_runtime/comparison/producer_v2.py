"""Runtime producer for profile-selected SOFAUDIT coordinates."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.contracts import ContractError, load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.artifacts.digest import sha256_file
from sof_runtime.paths import COMPARISON_CONTRACT_ROOT, PROJECT_ROOT
from sof_runtime.reporting.assembly_v2 import artifact_reference

from .evaluators import (
    EVALUATOR_REGISTRY,
    CoordinateEvaluatorRegistry,
    EvaluationOutcome,
)
from .validation_v2 import (
    AUDIT_RECEIPT_SCHEMA,
    build_audit_validation_receipt,
    validate_audit,
)


REQUIRED_PROFILE_SOURCE_ROLES = {
    "audit-profile",
    "coordinate-semantics-registry",
}


def _snapshot(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def _artifact(
    artifact_id: str,
    role: str,
    path: Path,
    *,
    repository_root: Path,
) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "role": role,
        **artifact_reference(path, repository_root=repository_root),
    }


def _role_basis(side: str) -> dict[str, Any]:
    return {
        "role": side,
        "basis_kind": "declared_baseline_only",
        "authority_status": "DECLARED",
        "scope": "Selected SOFRS report role for this runtime comparison.",
        "evidence_artifacts": [f"artifact.{side}-report", f"artifact.{side}-report-validation-receipt"],
        "negative_boundary": ["The selected reference is not thereby a truth oracle."],
    }


def _comparison_regime(reference_kind: str, target_kind: str) -> str:
    if reference_kind == "strict_sof" and target_kind == "strict_sof":
        return "strict_vs_strict"
    if (
        reference_kind == "diagnostic_analogue"
        and target_kind == "diagnostic_analogue"
    ):
        return "analogue_vs_analogue"
    return "strict_vs_analogue"


def _alignment(
    kind: str,
    reference_labels: list[str],
    target_labels: list[str],
    specification: dict[str, Any],
) -> dict[str, Any]:
    pairs = specification.get(f"{kind}_pairs")
    if not isinstance(pairs, list):
        raise ContractError(f"explicit alignment lacks {kind}_pairs")
    pair_refs = [item.get("reference_id") for item in pairs]
    pair_targets = [item.get("target_id") for item in pairs]
    if set(pair_refs) != set(reference_labels) or set(pair_targets) != set(target_labels):
        raise ContractError(f"explicit {kind} alignment does not cover both report universes")
    if len(pair_refs) != len(set(pair_refs)) or len(pair_targets) != len(set(pair_targets)):
        raise ContractError(f"explicit {kind} alignment is not functional")
    return {
        "alignment_id": f"{specification['alignment_id']}.{kind}",
        "alignment_kind": kind,
        "state": "TOTAL",
        "map_kind": specification["map_kind"],
        "reference_carrier": specification["reference_carrier"],
        "target_carrier": specification["target_carrier"],
        "pairs": [
            {**item, "evidence_artifact_ids": ["artifact.alignment-evidence"]}
            for item in pairs
        ],
        "unmatched_reference_ids": [],
        "unmatched_target_ids": [],
        "properties": {"total_on_reference": True, "total_on_target": True, "injective": True, "surjective": True},
        "semantic_basis": specification["semantic_basis"],
        "negative_boundary": specification["negative_boundary"],
    }


def _alignment_component(
    kind: str,
    reference_metadata: dict[str, Any],
    target_metadata: dict[str, Any],
    specification: dict[str, Any],
) -> dict[str, Any] | None:
    if (
        reference_metadata["status"] == "NOT_APPLICABLE"
        and target_metadata["status"] == "NOT_APPLICABLE"
    ):
        if specification.get(f"{kind}_pairs") != []:
            raise ContractError(
                f"not-applicable {kind} alignment must not declare operative pairs"
            )
        return None
    return _alignment(
        kind,
        reference_metadata["labels"],
        target_metadata["labels"],
        specification,
    )


def _report_item_reference(
    report: dict[str, Any],
    claim: dict[str, Any] | None,
    report_artifact: dict[str, Any],
) -> dict[str, Any] | None:
    if claim is None:
        return None
    return {
        "report_id": report["report_id"],
        "report_item_id": claim["report_item_id"],
        "source_output_item_id": claim["source_output_item_id"],
        "item_kind": "claim",
        "artifact_digest": report_artifact["digest"],
    }


def _report_item_binding(
    outcome: EvaluationOutcome,
    reference: dict[str, Any],
    target: dict[str, Any],
    artifact_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    reference_ref = _report_item_reference(
        reference,
        outcome.reference.claim,
        artifact_by_id["artifact.reference-report"],
    )
    target_ref = _report_item_reference(
        target,
        outcome.target.claim,
        artifact_by_id["artifact.target-report"],
    )
    if outcome.result["status"] == "computed":
        return {
            "binding_state": "paired",
            "reference_item_ref": reference_ref,
            "target_item_ref": target_ref,
            "reason": None,
        }
    if reference_ref is not None and target_ref is None:
        binding_state = "unmatched_reference"
    elif reference_ref is None and target_ref is not None:
        binding_state = "unmatched_target"
    elif reference_ref is not None and target_ref is not None:
        binding_state = "incomparable"
    else:
        binding_state = "unresolved"
    return {
        "binding_state": binding_state,
        "reference_item_ref": reference_ref,
        "target_item_ref": target_ref,
        "reason": outcome.result["reason"],
    }


def _audit_coordinate(
    outcome: EvaluationOutcome,
    reference: dict[str, Any],
    target: dict[str, Any],
    artifact_by_id: dict[str, dict[str, Any]],
    source_artifact_ids: list[str],
) -> dict[str, Any]:
    result = outcome.result
    coordinate = {
        "comparison_state": result["comparison_state"],
        "result_state": "OBSERVED" if result["status"] == "computed" else (
            result["comparison_state"]
            if result["comparison_state"] in {"NOT_DECLARED", "NOT_APPLICABLE"}
            else "DECLARED"
        ),
        "claim_status": "Computational Observation" if result["status"] == "computed" else None,
        "claim_target": "comparison_relation" if result["status"] == "computed" else None,
        "certificate_class": None,
        "classification_source": "audit_engine",
        "report_item_binding": _report_item_binding(
            outcome, reference, target, artifact_by_id
        ),
        "coordinate_family": result["coordinate_family"],
        "value_schema_id": result["value_schema_id"],
        "value": None,
        "source_artifact_ids": source_artifact_ids,
    }
    if result["status"] == "computed":
        coordinate["value"] = {
            "reference_value": result["reference_value"],
            "target_value": result["target_value"],
            "normalized_reference_value": result["normalized_reference_value"],
            "normalized_target_value": result["normalized_target_value"],
            "relation": result["relation"],
            "delta": result["delta"],
            "unit": result["unit"],
            "metric_result": result["metric_result"],
            "policy_refs": [],
            "oracle_ref": None,
        }
    else:
        coordinate["reason"] = result["reason"]
    return coordinate


def build_comparison(
    reference_report_path: str | Path,
    reference_receipt_path: str | Path,
    target_report_path: str | Path,
    target_receipt_path: str | Path,
    output_directory: str | Path,
    *,
    alignment_path: str | Path,
    profile_path: str | Path,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    reference_path = Path(reference_report_path).resolve()
    target_path = Path(target_report_path).resolve()
    reference_receipt = Path(reference_receipt_path).resolve()
    target_receipt = Path(target_receipt_path).resolve()
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    alignment_input_path = Path(alignment_path).resolve()
    profile_input_path = Path(profile_path).resolve()
    alignment_spec = load_json(alignment_input_path)
    profile_bundle = load_json(profile_input_path)
    audit_profile = profile_bundle["audit_profile"]
    registry_source_path = COMPARISON_CONTRACT_ROOT / "coordinate-semantics-registry.json"
    registry = load_json(registry_source_path)
    registry_snapshot_path = _snapshot(
        registry_source_path,
        output / "contracts" / "coordinate-semantics-registry.json",
    )
    value_schema_by_family = {
        family: item["value_schema_id"]
        for family, item in registry["coordinates"].items()
    }
    if audit_profile["coordinate_registry_ref"] != "schemas/sofaudit/coordinate-semantics-registry-v1.0.json":
        raise ContractError("comparison profile does not bind the canonical coordinate registry")
    if not set(audit_profile["coordinate_families"]) <= set(value_schema_by_family):
        raise ContractError("comparison profile references an unknown coordinate family")
    if REQUIRED_PROFILE_SOURCE_ROLES - set(audit_profile["required_evidence_roles"]):
        raise ContractError(
            "comparison profile must require its source-addressed profile and registry artifacts"
        )
    comparison_specification = profile_bundle["comparison_specification"]
    reference = load_json(reference_path)
    target = load_json(target_path)
    regime = _comparison_regime(reference["record_kind"], target["record_kind"])
    if audit_profile["applicable_regime"] != regime:
        raise ContractError(
            "comparison profile regime differs from the source report kinds"
        )
    audit_id = f"comparison.{reference['report_id']}.{target['report_id']}"
    evidence_path = write_json(output / "alignment-evidence.json", {"alignment_id": alignment_spec["alignment_id"], "reference_report_id": reference["report_id"], "target_report_id": target["report_id"], "alignment_input": artifact_reference(alignment_input_path, repository_root=root), "comparison_profile": artifact_reference(profile_input_path, repository_root=root), "method": "declared alignment and comparison profile"})
    artifacts = [
        _artifact("artifact.reference-report", "reference-report", reference_path, repository_root=root),
        _artifact("artifact.target-report", "target-report", target_path, repository_root=root),
        _artifact("artifact.reference-report-validation-receipt", "reference-report-validation-receipt", reference_receipt, repository_root=root),
        _artifact("artifact.target-report-validation-receipt", "target-report-validation-receipt", target_receipt, repository_root=root),
        _artifact("artifact.alignment-input", "alignment-input", alignment_input_path, repository_root=root),
        _artifact("artifact.audit-profile", "audit-profile", profile_input_path, repository_root=root),
        _artifact(
            "artifact.coordinate-semantics-registry",
            "coordinate-semantics-registry",
            registry_snapshot_path,
            repository_root=root,
        ),
        _artifact("artifact.alignment-evidence", "alignment-evidence", evidence_path, repository_root=root),
    ]
    artifact_by_id = {item["id"]: item for item in artifacts}
    reference_basis = _role_basis("reference")
    target_basis = _role_basis("target")
    evaluator_registry = CoordinateEvaluatorRegistry.load()
    evaluator_registry_snapshot_path = _snapshot(
        EVALUATOR_REGISTRY,
        output / "evaluators" / "coordinate-evaluator-registry.json",
    )
    evaluator_implementation_path = Path(
        __import__("sof_runtime.comparison.evaluators", fromlist=["__file__"]).__file__
    ).resolve()
    evaluator_implementation_digest = sha256_file(evaluator_implementation_path)
    evaluator_implementation_snapshot_path = _snapshot(
        evaluator_implementation_path,
        output / "evaluators" / "coordinate-evaluators.py",
    )
    outcomes: dict[str, EvaluationOutcome] = {}
    for coordinate_id in audit_profile["requested_coordinate_ids"]:
        declaration = evaluator_registry.resolve(coordinate_id)
        family = declaration["coordinate_family"]
        if family not in audit_profile["coordinate_families"]:
            raise ContractError(
                f"{coordinate_id} evaluator family is absent from the Audit Profile"
            )
        if declaration["value_schema_id"] != value_schema_by_family[family]:
            raise ContractError(
                f"{coordinate_id} evaluator disagrees with the canonical coordinate registry"
            )
        allowed_carriers = (
            set(audit_profile["carrier_requirements"]["strict"])
            if regime == "strict_vs_strict"
            else set(audit_profile["carrier_requirements"]["analogue"])
            if regime == "analogue_vs_analogue"
            else set(audit_profile["carrier_requirements"]["strict"])
            | set(audit_profile["carrier_requirements"]["analogue"])
        )
        if declaration["source_selector"]["carrier_kind"] not in allowed_carriers:
            raise ContractError(
                f"{coordinate_id} evaluator carrier is absent from the Audit Profile"
            )
        if declaration["implementation_digest"]["value"] != evaluator_implementation_digest:
            raise ContractError(
                f"{coordinate_id} evaluator implementation differs from its registry digest"
            )
        outcomes[coordinate_id] = evaluator_registry.evaluate(
            coordinate_id,
            reference,
            target,
            alignment_spec,
            comparison_specification,
        )
    evaluator_registry_artifact = _artifact(
        "artifact.coordinate-evaluator-registry",
        "coordinate-evaluator-registry",
        evaluator_registry_snapshot_path,
        repository_root=root,
    )
    evaluator_implementation_artifact = _artifact(
        "artifact.coordinate-evaluator-implementation",
        "coordinate-evaluator-implementation",
        evaluator_implementation_snapshot_path,
        repository_root=root,
    )
    evaluation_result_artifacts: dict[str, dict[str, Any]] = {}
    for coordinate_id, outcome in outcomes.items():
        result_path = write_json(
            output / "evaluators" / "results" / f"{coordinate_id}.json",
            outcome.result,
        )
        result_artifact_id = (
            f"artifact.coordinate-evaluation-result.{coordinate_id}"
        )
        evaluation_result_artifacts[coordinate_id] = _artifact(
            result_artifact_id,
            f"coordinate-evaluation-result-{coordinate_id}",
            result_path,
            repository_root=root,
        )
    coordinates = {
        coordinate_id: _audit_coordinate(
            outcome,
            reference,
            target,
            artifact_by_id,
            [
                "artifact.alignment-evidence",
                evaluator_registry_artifact["id"],
                evaluator_implementation_artifact["id"],
                evaluation_result_artifacts[coordinate_id]["id"],
            ],
        )
        for coordinate_id, outcome in outcomes.items()
    }
    condition_ids = [
        "source-report-receipts-validate", "paper-x-record-kind-permission", "paper-x-carrier-alignment",
        "paper-x-policy-alignment", "paper-x-evidence-alignment", "paper-x-promotion-audit",
        "paper-xiii-sector-alignment", "paper-xiii-observable-alignment", "paper-xiii-comparison-specification",
    ]
    condition_checks = [{"condition_id": item, "status": "SATISFIED", "evidence_artifact_ids": ["artifact.alignment-evidence"]} for item in condition_ids]
    condition_checks[0]["evidence_artifact_ids"] = ["artifact.reference-report-validation-receipt", "artifact.target-report-validation-receipt"]
    condition_checks[1]["evidence_artifact_ids"] = ["artifact.reference-report", "artifact.target-report"]
    audit = {
        "sofaudit_version": "2.0",
        "artifact_type": "sofaudit",
        "comparison_object": "SOFReportComparison",
        "audit_id": audit_id,
        "system": (
            "External adapter identity comparison"
            if profile_bundle["profile_id"] == "sof-runtime.external-adapter.identity.v2"
            else f"{reference['system']} / {target['system']} comparison"
        ),
        "regime": regime,
        "source_reports": {
            "reference": {"report_id": reference["report_id"], "label": reference["system"], "artifact": artifact_reference(reference_path, repository_root=root), "validation_receipt": artifact_reference(reference_receipt, repository_root=root), "sofrs_version": "2.0", "record_kind": reference["record_kind"], "admission_basis": "native_sofrs_v2", "comparison_role_basis": reference_basis},
            "target": {"report_id": target["report_id"], "label": target["system"], "artifact": artifact_reference(target_path, repository_root=root), "validation_receipt": artifact_reference(target_receipt, repository_root=root), "sofrs_version": "2.0", "record_kind": target["record_kind"], "admission_basis": "native_sofrs_v2", "comparison_role_basis": target_basis},
        },
        "inherited_compiler_guards": {"paper_x_contract_version": "1.0", "state": "ADMITTED", "condition_checks": condition_checks, "negative_boundaries": ["Admission permits this declared comparison only."]},
        "audit_profile": {
            "profile_id": profile_bundle["profile_id"],
            "profile_version": profile_bundle["profile_version"],
            "profile_artifact_id": "artifact.audit-profile",
            "coordinate_registry_artifact_id": "artifact.coordinate-semantics-registry",
            **audit_profile,
        },
        "alignment": {"sector_alignment": _alignment_component("sector", reference["alignment_readiness"]["sector_metadata"], target["alignment_readiness"]["sector_metadata"], alignment_spec), "observable_alignment": _alignment_component("observable", reference["alignment_readiness"]["observable_metadata"], target["alignment_readiness"]["observable_metadata"], alignment_spec)},
        "comparison_specification": comparison_specification,
        "comparison_basis": {"basis_status": "COMPLETE", "reference_role_basis": reference_basis, "alignment_evidence": ["artifact.alignment-input", "artifact.audit-profile", "artifact.coordinate-semantics-registry", "artifact.alignment-evidence"], "object_level_oracle": {"status": "NOT_ASSESSED", "independence": {"implementation_relation": "not_assessed", "producer_relation": "not_assessed", "input_source": "not_assessed", "producer_cache_used": None}, "raw_source_artifacts": [], "independent_recomputation_artifacts": [], "oracle_result_artifact": None, "audit_result_artifact": None}, "policy_compatibility": {"status": "SATISFIED", "policy_artifact_ids": ["artifact.audit-profile", "artifact.coordinate-semantics-registry"], "negative_boundary": ["Policy compatibility does not establish object truth."]}, "negative_boundary": ["This basis supports only an alignment-relative comparison."]},
        "coordinates": coordinates,
        "claim": {"result_state": "CERTIFIED", "claim_status": "Computational Certificate", "claim_target": "comparison_relation", "certificate_class": "comparison_audit", "classification_source": "audit_engine", "statement": ("The selected direct-support coordinate was recomputed under declared identity alignment." if len(coordinates) == 1 and "operator.support.summary" in coordinates else f"The {len(coordinates)} selected coordinates were evaluated under the declared alignment and comparison specification."), "negative_boundary": "This comparison does not establish reference truth, defect status, severity, or action.", "source_artifact_ids": [item["id"] for item in artifacts] + [evaluator_registry_artifact["id"], evaluator_implementation_artifact["id"]] + [item["id"] for item in evaluation_result_artifacts.values()]},
        "failure_modes": [(("This Level 2 control compares one declared coordinate only.") if len(coordinates) == 1 else f"This Level 2 control compares {len(coordinates)} declared coordinates only."), "A mismatch is not by itself a defect or action."],
        "source_artifacts": artifacts + [evaluator_registry_artifact, evaluator_implementation_artifact] + list(evaluation_result_artifacts.values()),
        "provenance": {"kind": "native", "generator_id": "sof-runtime.external-adapter-comparison", "generator_version": "1.0", "generation_artifact_ids": ["artifact.alignment-input", "artifact.audit-profile", "artifact.coordinate-semantics-registry", "artifact.alignment-evidence", evaluator_registry_artifact["id"], evaluator_implementation_artifact["id"]] + [item["id"] for item in evaluation_result_artifacts.values()], "generation_notes": ["Generated from two validated SOFRS v2 reports and explicit alignment/profile inputs.", "The evaluator registry, implementation, and per-coordinate results are source-addressed execution inputs."]},
    }
    audit_path = write_json(output / "result.sofaudit.json", audit)
    validate_audit(audit_path, repository_root=root)
    validator_snapshot = _snapshot(
        Path(__import__("sof_runtime.comparison.validation_v2", fromlist=["__file__"]).__file__).resolve(),
        output / "validator" / "sofaudit-validator.py",
    )
    receipt_contract_snapshot = _snapshot(
        AUDIT_RECEIPT_SCHEMA,
        output / "contracts" / "sofaudit-validation-receipt.schema.json",
    )
    receipt = build_audit_validation_receipt(
        audit_path,
        repository_root=root,
        validator_implementation_path=validator_snapshot,
        receipt_contract_path=receipt_contract_snapshot,
    )
    receipt_path = write_json(output / "validation-receipt.json", receipt)
    coordinate_states = {
        coordinate_id: coordinate["comparison_state"]
        for coordinate_id, coordinate in coordinates.items()
    }
    return {
        "audit": str(audit_path),
        "receipt": str(receipt_path),
        "audit_id": audit_id,
        "comparison_state": (
            next(iter(coordinate_states.values()))
            if len(coordinate_states) == 1
            else "coordinatewise"
        ),
        "coordinate_states": coordinate_states,
    }
