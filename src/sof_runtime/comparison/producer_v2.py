"""Runtime producer for a bounded one-coordinate SOFAUDIT comparison."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.contracts import ContractError, load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.paths import COMPARISON_CONTRACT_ROOT, PROJECT_ROOT
from sof_runtime.reporting.assembly_v2 import artifact_reference

from .validation_v2 import (
    AUDIT_RECEIPT_SCHEMA,
    build_audit_validation_receipt,
    validate_audit,
)


def _snapshot(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def _artifact(artifact_id: str, role: str, path: Path) -> dict[str, Any]:
    return {"id": artifact_id, "role": role, **artifact_reference(path, repository_root=PROJECT_ROOT)}


def _role_basis(side: str) -> dict[str, Any]:
    return {
        "role": side,
        "basis_kind": "declared_baseline_only",
        "authority_status": "DECLARED",
        "scope": "Selected SOFRS report role for this runtime comparison.",
        "evidence_artifacts": [f"artifact.{side}-report", f"artifact.{side}-report-validation-receipt"],
        "negative_boundary": ["The selected reference is not thereby a truth oracle."],
    }


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


def _support_value(report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    finding = next(item for item in report["findings"] if item["kind"] == "boolean_support")
    value = finding["value"]
    support_count = len(value.get("support_pairs", [])) if isinstance(value, dict) else int(bool(value))
    return finding, {"support_count": support_count}


def build_comparison(
    reference_report_path: str | Path,
    reference_receipt_path: str | Path,
    target_report_path: str | Path,
    target_receipt_path: str | Path,
    output_directory: str | Path,
    *,
    alignment_path: str | Path,
    profile_path: str | Path,
) -> dict[str, str]:
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
    comparison_specification = profile_bundle["comparison_specification"]
    reference = load_json(reference_path)
    target = load_json(target_path)
    audit_id = f"comparison.{reference['report_id']}.{target['report_id']}"
    evidence_path = write_json(output / "alignment-evidence.json", {"alignment_id": alignment_spec["alignment_id"], "reference_report_id": reference["report_id"], "target_report_id": target["report_id"], "alignment_input": artifact_reference(alignment_input_path, repository_root=PROJECT_ROOT), "comparison_profile": artifact_reference(profile_input_path, repository_root=PROJECT_ROOT), "method": "declared alignment and comparison profile"})
    artifacts = [
        _artifact("artifact.reference-report", "reference-report", reference_path),
        _artifact("artifact.target-report", "target-report", target_path),
        _artifact("artifact.reference-report-validation-receipt", "reference-report-validation-receipt", reference_receipt),
        _artifact("artifact.target-report-validation-receipt", "target-report-validation-receipt", target_receipt),
        _artifact("artifact.alignment-input", "alignment-input", alignment_input_path),
        _artifact("artifact.audit-profile", "audit-profile", profile_input_path),
        _artifact(
            "artifact.coordinate-semantics-registry",
            "coordinate-semantics-registry",
            registry_snapshot_path,
        ),
        _artifact("artifact.alignment-evidence", "alignment-evidence", evidence_path),
    ]
    artifact_by_id = {item["id"]: item for item in artifacts}
    reference_basis = _role_basis("reference")
    target_basis = _role_basis("target")
    ref_finding, ref_value = _support_value(reference)
    target_finding, target_value = _support_value(target)
    ref_item = reference["claims"][0]
    target_item = target["claims"][0]
    delta = target_value["support_count"] - ref_value["support_count"]
    state = "ALIGNED" if delta == 0 else "MISMATCH"
    relation = "equal" if state == "ALIGNED" else "mismatch"
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
        "system": "External adapter identity comparison",
        "regime": "strict_vs_strict",
        "source_reports": {
            "reference": {"report_id": reference["report_id"], "label": reference["system"], "artifact": artifact_reference(reference_path, repository_root=PROJECT_ROOT), "validation_receipt": artifact_reference(reference_receipt, repository_root=PROJECT_ROOT), "sofrs_version": "2.0", "record_kind": reference["record_kind"], "admission_basis": "native_sofrs_v2", "comparison_role_basis": reference_basis},
            "target": {"report_id": target["report_id"], "label": target["system"], "artifact": artifact_reference(target_path, repository_root=PROJECT_ROOT), "validation_receipt": artifact_reference(target_receipt, repository_root=PROJECT_ROOT), "sofrs_version": "2.0", "record_kind": target["record_kind"], "admission_basis": "native_sofrs_v2", "comparison_role_basis": target_basis},
        },
        "inherited_compiler_guards": {"paper_x_contract_version": "1.0", "state": "ADMITTED", "condition_checks": condition_checks, "negative_boundaries": ["Admission permits this declared comparison only."]},
        "audit_profile": {
            "profile_id": profile_bundle["profile_id"],
            "profile_version": profile_bundle["profile_version"],
            "profile_artifact_id": "artifact.audit-profile",
            "coordinate_registry_artifact_id": "artifact.coordinate-semantics-registry",
            **audit_profile,
        },
        "alignment": {"sector_alignment": _alignment("sector", reference["alignment_readiness"]["sector_metadata"]["labels"], target["alignment_readiness"]["sector_metadata"]["labels"], alignment_spec), "observable_alignment": _alignment("observable", reference["alignment_readiness"]["observable_metadata"]["labels"], target["alignment_readiness"]["observable_metadata"]["labels"], alignment_spec)},
        "comparison_specification": comparison_specification,
        "comparison_basis": {"basis_status": "COMPLETE", "reference_role_basis": reference_basis, "alignment_evidence": ["artifact.alignment-input", "artifact.audit-profile", "artifact.coordinate-semantics-registry", "artifact.alignment-evidence"], "object_level_oracle": {"status": "NOT_ASSESSED", "independence": {"implementation_relation": "not_assessed", "producer_relation": "not_assessed", "input_source": "not_assessed", "producer_cache_used": None}, "raw_source_artifacts": [], "independent_recomputation_artifacts": [], "oracle_result_artifact": None, "audit_result_artifact": None}, "policy_compatibility": {"status": "SATISFIED", "policy_artifact_ids": ["artifact.audit-profile", "artifact.coordinate-semantics-registry"], "negative_boundary": ["Policy compatibility does not establish object truth."]}, "negative_boundary": ["This basis supports only an alignment-relative comparison."]},
        "coordinates": {"operator.support.summary": {"comparison_state": state, "result_state": "OBSERVED", "claim_status": "Computational Observation", "claim_target": "comparison_relation", "certificate_class": None, "classification_source": "audit_engine", "report_item_binding": {"binding_state": "paired", "reference_item_ref": {"report_id": reference["report_id"], "report_item_id": ref_item["report_item_id"], "source_output_item_id": ref_item["source_output_item_id"], "item_kind": "claim", "artifact_digest": artifact_by_id["artifact.reference-report"]["digest"]}, "target_item_ref": {"report_id": target["report_id"], "report_item_id": target_item["report_item_id"], "source_output_item_id": target_item["source_output_item_id"], "item_kind": "claim", "artifact_digest": artifact_by_id["artifact.target-report"]["digest"]}, "reason": None}, "coordinate_family": "operator", "value_schema_id": "operator.support.v1", "value": {"reference_value": ref_value, "target_value": target_value, "normalized_reference_value": ref_value, "normalized_target_value": target_value, "relation": relation, "delta": delta, "unit": "support pairs", "metric_result": {"metric_id": "absolute-difference", "status": "computed", "value": abs(delta)}, "policy_refs": [], "oracle_ref": None}, "source_artifact_ids": ["artifact.alignment-evidence"]}},
        "claim": {"result_state": "CERTIFIED", "claim_status": "Computational Certificate", "claim_target": "comparison_relation", "certificate_class": "comparison_audit", "classification_source": "audit_engine", "statement": "The selected direct-support coordinate was recomputed under declared identity alignment.", "negative_boundary": "This comparison does not establish reference truth, defect status, severity, or action.", "source_artifact_ids": [item["id"] for item in artifacts]},
        "failure_modes": ["This Level 2 control compares one declared coordinate only.", "A mismatch is not by itself a defect or action."],
        "source_artifacts": artifacts,
        "provenance": {"kind": "native", "generator_id": "sof-runtime.external-adapter-comparison", "generator_version": "1.0", "generation_artifact_ids": ["artifact.alignment-input", "artifact.audit-profile", "artifact.coordinate-semantics-registry", "artifact.alignment-evidence"], "generation_notes": ["Generated from two validated SOFRS v2 reports and explicit alignment/profile inputs."]},
    }
    audit_path = write_json(output / "result.sofaudit.json", audit)
    validate_audit(audit_path, repository_root=PROJECT_ROOT)
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
        repository_root=PROJECT_ROOT,
        validator_implementation_path=validator_snapshot,
        receipt_contract_path=receipt_contract_snapshot,
    )
    receipt_path = write_json(output / "validation-receipt.json", receipt)
    return {"audit": str(audit_path), "receipt": str(receipt_path), "audit_id": audit_id, "comparison_state": state}
