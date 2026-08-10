"""Runtime producer for Paper XIV interpretation and bounded candidates."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.contracts import load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.reporting.assembly_v2 import artifact_reference

from .validation_v2 import (
    ACTION_RECEIPT_SCHEMA,
    _assert_acyclic,
    _matching_rule,
    _precedence_graph,
    build_action_validation_receipt,
    validate_action,
)


def _snapshot(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def _audit_ref(audit_path: Path, receipt_path: Path, audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_id": audit["audit_id"],
        "artifact": audit_path.relative_to(PROJECT_ROOT).as_posix(),
        "sofaudit_version": "2.0",
        "digest": artifact_reference(audit_path, repository_root=PROJECT_ROOT)["digest"],
        "validation_receipt": {
            "receipt_id": f"receipt.{audit['audit_id']}.sofaudit-v2",
            "artifact": receipt_path.relative_to(PROJECT_ROOT).as_posix(),
            "digest": artifact_reference(receipt_path, repository_root=PROJECT_ROOT)["digest"],
            "validator_id": "sofaudit.runtime-semantic-validator.v2",
            "validator_version": "2.0",
        },
    }


def _interpretations(
    audit: dict[str, Any],
    context: dict[str, Any],
    policy: dict[str, Any],
    audit_ref: dict[str, Any],
    action_record_id: str,
) -> list[dict[str, Any]]:
    graph = _precedence_graph(policy)
    _assert_acyclic(graph)
    records = []
    for coordinate_id, coordinate in audit["coordinates"].items():
        rule, conflict = _matching_rule(policy, audit, coordinate_id, coordinate, context, graph)
        if conflict:
            assessment_kind = "policy_conflict"
            rule_refs: list[str] = []
            note = "Multiple matching policy rules lack a unique precedence-dominant rule."
            uncertainty_status = "unresolved"
            dispositions: list[str] = []
            boundary = ["A policy conflict cannot be resolved by producer declaration order."]
        elif rule is None:
            assessment_kind = "inconclusive"
            rule_refs = []
            note = "The declared policy does not authorize an interpretation for this coordinate."
            uncertainty_status = "unresolved"
            dispositions = []
            boundary = ["No applicable policy rule was found for this coordinate."]
        else:
            assessment_kind = rule["assessment_kind"]
            rule_refs = [rule["rule_id"]]
            note = rule["assessment_note"]
            uncertainty_status = rule["uncertainty_status"]
            dispositions = list(rule.get("allowed_dispositions", []))
            boundary = list(rule["negative_boundary"])
        if coordinate["comparison_state"] in {"UNRESOLVED", "NOT_DECLARED", "INCOMPARABLE", "NOT_APPLICABLE"}:
            dispositions = []
        records.append({
            "interpretation_id": f"interp:{action_record_id}:{coordinate_id}",
            "audit_coordinate_refs": [{"coordinate_id": coordinate_id, "comparison_state": coordinate["comparison_state"], "carrier": coordinate.get("carrier", coordinate["coordinate_family"])}],
            "context_refs": [context["context_id"]],
            "policy_rule_refs": rule_refs,
            "assessment_kind": assessment_kind,
            "assessment_note": note,
            "uncertainty": {"status": uncertainty_status, "reasons": [] if coordinate["comparison_state"] in {"ALIGNED", "MISMATCH"} else [f"source comparison state is {coordinate['comparison_state']}"]},
            "rationale": note,
            "supported_dispositions": dispositions,
            "evidence_refs": [audit_ref],
            "negative_boundary": boundary,
        })
    return records


def _candidate_actions(
    interpretations: list[dict[str, Any]],
    context: dict[str, Any],
    audit_ref: dict[str, Any],
) -> list[dict[str, Any]]:
    actions = []
    for interpretation in interpretations:
        for disposition in interpretation["supported_dispositions"]:
            if disposition not in {"Investigate", "RequestEvidence", "Mitigate", "Rollback", "Escalate"}:
                continue
            coordinate = interpretation["audit_coordinate_refs"][0]
            action_id = f"{disposition.lower()}:{coordinate['coordinate_id']}"
            actions.append({
                "action_id": action_id,
                "disposition": disposition,
                "target": coordinate["coordinate_id"],
                "carrier": coordinate["carrier"],
                "supported_by_interpretations": [interpretation["interpretation_id"]],
                "audit_coordinate_refs": [coordinate],
                "context_ref": context["context_id"],
                "policy_rule_refs": interpretation["policy_rule_refs"],
                "preconditions": ["the source audit projection and coordinate state remain unchanged", "a domain owner confirms the candidate is applicable"],
                "intended_diagnostic_consequence": {"status": "intended_diagnostic_consequence", "statements": ["obtain evidence relevant to the declared comparison coordinate"]},
                "declared_risk_considerations": ["the candidate may be irrelevant after context or policy review", "an observed post-action change would require a new Paper XIII audit"],
                "reversibility": "unknown",
                "evidence_refs": [audit_ref],
                "authorization_state": "not_requested",
                "negative_boundary": ["This is a candidate disposition, not an execution command or correctness claim."],
            })
    return actions


def build_interpretation(
    audit_path: str | Path,
    audit_receipt_path: str | Path,
    context_path: str | Path,
    policy_path: str | Path,
    output_directory: str | Path,
) -> dict[str, Any]:
    audit_path = Path(audit_path).resolve()
    audit_receipt_path = Path(audit_receipt_path).resolve()
    context = load_json(context_path)
    policy = load_json(policy_path)
    audit = load_json(audit_path)
    audit_ref = _audit_ref(audit_path, audit_receipt_path, audit)
    action_record_id = f"action.{audit['audit_id']}"
    interpretations = _interpretations(audit, context, policy, audit_ref, action_record_id)
    actions = _candidate_actions(interpretations, context, audit_ref)
    if actions:
        disposition = {"kind": "candidate_action_set", "reason": "The admitted policy supports bounded candidate dispositions.", "interpretation_ids": [item["interpretation_id"] for item in interpretations], "candidate_action_ids": [item["action_id"] for item in actions]}
    elif any(item["assessment_kind"] == "inconclusive" for item in interpretations):
        disposition = {"kind": "unresolved_disposition", "reason": "The admitted inputs do not support an affirmative candidate disposition.", "interpretation_ids": [item["interpretation_id"] for item in interpretations], "candidate_action_ids": []}
    else:
        disposition = {"kind": "no_action_disposition", "reason": "The admitted policy supports no action for the interpreted coordinates.", "interpretation_ids": [item["interpretation_id"] for item in interpretations], "candidate_action_ids": []}
    action = {
        "sofaction_version": "2.0",
        "record_type": "sofaction",
        "action_record_id": action_record_id,
        "claim_status": "Computational Certificate",
        "record_class": "decision_trace_certificate",
        "record_basis": {"basis_kind": "protocol_trace", "evidence_refs": [audit_ref], "causal_status": "not_claimed", "negative_boundary": ["Protocol trace completeness does not establish policy validity or action effectiveness."]},
        "claim_note": "This object records policy-relative interpretation and bounded candidates; it does not select or execute an action.",
        "source_audit": audit_ref,
        "audit_projection": {"audit_id": audit["audit_id"], "signature": deepcopy(audit["coordinates"])},
        "context_admission": {"status": "admitted", "contract_validation": "admitted", "applicability": "applicable", "completeness": "complete", "missing_fields": [], "rationale": "ActionContext supplied by the caller."},
        "policy_admission": {"status": "admitted", "contract_validation": "admitted", "applicability": "applicable", "completeness": "complete", "missing_fields": [], "rationale": "PolicyProfile supplied by the caller and replayed by the runtime."},
        "action_context": context,
        "policy_profile": policy,
        "interpretation_records": interpretations,
        "candidate_action_set": {"count": len(actions), "actions": actions},
        "disposition_result": disposition,
        "failure_modes": ["difference is not defect, severity, or action without the admitted context and policy", "candidate actions are not execution commands, authorization, feasibility, or causal-effect claims", "post-action facts require a new Paper XIII audit"],
    }
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    context_out = write_json(output / "context.json", context)
    policy_out = write_json(output / "policy.json", policy)
    action_path = write_json(output / "result.sofaction.json", action)
    validate_action(action_path, repository_root=PROJECT_ROOT)
    validator_snapshot = _snapshot(
        Path(__import__("sof_runtime.action.validation_v2", fromlist=["__file__"]).__file__).resolve(),
        output / "validator" / "sofaction-validator.py",
    )
    receipt_contract_snapshot = _snapshot(
        ACTION_RECEIPT_SCHEMA,
        output / "contracts" / "sofaction-validation-receipt.schema.json",
    )
    receipt = build_action_validation_receipt(
        action_path,
        repository_root=PROJECT_ROOT,
        validator_implementation_path=validator_snapshot,
        receipt_contract_path=receipt_contract_snapshot,
    )
    receipt_path = write_json(output / "validation-receipt.json", receipt)
    return {"action": str(action_path), "receipt": str(receipt_path), "context": str(context_out), "policy": str(policy_out), "action_record_id": action_record_id, "candidate_count": len(actions)}
