"""Structured provenance explanation for a runtime run directory.

This module deliberately returns data, not generated prose. A UI, CLI, or
domain tool may render the result without inventing claims or evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT


UNAVAILABLE_STATES = {
    "NOT_DECLARED",
    "NOT_APPLICABLE",
    "INCOMPARABLE",
    "UNRESOLVED",
}


def _path_from_uri(uri: str) -> Path:
    path = Path(uri)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _ref_summary(ref: Any) -> Any:
    if not isinstance(ref, dict):
        return ref
    result: dict[str, Any] = {}
    for key in ("uri", "artifact", "digest", "role", "id", "audit_id", "receipt_id"):
        if key in ref:
            result[key] = ref[key]
    if "artifact" in ref and isinstance(ref["artifact"], dict):
        result["artifact"] = _ref_summary(ref["artifact"])
    if "validation_receipt" in ref:
        result["validation_receipt"] = _ref_summary(ref["validation_receipt"])
    return result or ref


def _validator_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    validator = receipt.get("validator", {})
    return {
        "status": receipt.get("status"),
        "receipt_id": receipt.get("receipt_id"),
        "validator_id": validator.get("validator_id"),
        "validator_version": validator.get("validator_version"),
        "implementation": _ref_summary(validator.get("implementation")),
    }


def _load_ref(ref: dict[str, Any]) -> dict[str, Any]:
    artifact = ref.get("artifact", ref)
    if not isinstance(artifact, dict) or "uri" not in artifact:
        raise ValueError("source-addressed reference lacks uri")
    return load_json(_path_from_uri(artifact["uri"]))


def _realization_explanation(run_receipt_path: Path) -> dict[str, Any]:
    receipt = load_json(run_receipt_path)
    declaration = _load_ref(receipt["adapter"]["declaration"])
    candidate = _load_ref(receipt["realization_candidate"])
    result = {
        "stage": "realization",
        "run_receipt": _ref_summary({"uri": str(run_receipt_path)}),
        "source": _ref_summary(receipt["source"]),
        "source_id": candidate.get("source_id"),
        "eligibility": receipt.get("eligibility"),
        "canonical_compilable": receipt.get("canonical_compilable"),
        "adapter": {
            "id": receipt["adapter"].get("id"),
            "version": receipt["adapter"].get("version"),
            "domain_id": declaration.get("domain_id"),
            "declaration": _ref_summary(receipt["adapter"]["declaration"]),
        },
        "declared": {
            "carriers": declaration.get("supported_carriers", []),
            "observables": declaration.get("supported_observables", []),
            "capabilities": declaration.get("capabilities", []),
            "unsupported": declaration.get("unsupported_capabilities", []),
            "sectorization_origin": declaration.get("sectorization_origin"),
        },
        "known_nonclaims": receipt.get("negative_boundary", []),
    }
    report_ref = receipt.get("report")
    validation_ref = receipt.get("validation_receipt")
    if report_ref is None:
        stage_receipt_path = run_receipt_path.parent / "report" / "report-stage-receipt.json"
        if stage_receipt_path.is_file():
            stage_receipt = load_json(stage_receipt_path)
            report_ref = stage_receipt.get("report")
            validation_ref = stage_receipt.get("validation_receipt")
    if report_ref is not None and validation_ref is not None:
        report = _load_ref(report_ref)
        report_receipt = _load_ref(validation_ref)
        result["report"] = {
            "report_id": report.get("report_id"),
            "artifact": _ref_summary(report_ref),
            "record_kind": report.get("record_kind"),
            "source_mapping": report.get("source_mapping", {}).get("status"),
            "validation": _validator_summary(report_receipt),
        }
        result["claims"] = [
            {
                "claim_id": claim.get("claim_id"),
                "statement": claim.get("statement"),
                "claim_status": claim.get("claim_status"),
                "source_artifacts": [
                    _ref_summary(item)
                    for item in report.get("alignment_readiness", {}).get("source_artifact_digests", [])
                ],
                "negative_boundary": claim.get("negative_boundary"),
            }
            for claim in report.get("claims", [])
        ]
    return result


def _unavailable_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for coordinate_id, coordinate in payload.get("coordinates", {}).items():
        state = coordinate.get("comparison_state") or coordinate.get("result_state")
        if state in UNAVAILABLE_STATES:
            findings.append({
                "coordinate_id": coordinate_id,
                "state": state,
                "reason": coordinate.get("reason") or coordinate.get("negative_boundary"),
            })
    for item in payload.get("degradation_items", []):
        findings.append({
            "coordinate_id": item.get("item_id"),
            "state": item.get("result_state", "UNAVAILABLE"),
            "reason": item.get("statement") or item.get("degradation_reason"),
        })
    return findings


def _comparison_explanation(root: Path) -> dict[str, Any] | None:
    audit_path = root / "comparison" / "result.sofaudit.json"
    receipt_path = root / "comparison" / "validation-receipt.json"
    if not audit_path.is_file() or not receipt_path.is_file():
        return None
    audit = load_json(audit_path)
    receipt = load_json(receipt_path)
    return {
        "stage": "comparison",
        "audit_id": audit.get("audit_id"),
        "artifact": {"uri": str(audit_path)},
        "validation": _validator_summary(receipt),
        "alignment": {
            "sector": audit.get("alignment", {}).get("sector_alignment", {}).get("alignment_id"),
            "observable": audit.get("alignment", {}).get("observable_alignment", {}).get("alignment_id"),
        },
        "coordinates": [
            {
                "coordinate_id": coordinate_id,
                "state": coordinate.get("comparison_state"),
                "claim_status": coordinate.get("claim_status"),
                "source_artifacts": coordinate.get("source_artifact_ids", []),
            }
            for coordinate_id, coordinate in audit.get("coordinates", {}).items()
        ],
        "why_unresolved_or_unavailable": _unavailable_findings(audit),
        "negative_boundary": audit.get("claim", {}).get("negative_boundary"),
    }


def _interpretation_explanation(root: Path) -> dict[str, Any] | None:
    action_path = root / "action" / "result.sofaction.json"
    receipt_path = root / "action" / "validation-receipt.json"
    if not action_path.is_file() or not receipt_path.is_file():
        return None
    action = load_json(action_path)
    receipt = load_json(receipt_path)
    records = action.get("interpretation_records", [])
    return {
        "stage": "interpretation",
        "action_record_id": action.get("action_record_id"),
        "artifact": {"uri": str(action_path)},
        "validation": _validator_summary(receipt),
        "context_id": action.get("action_context", {}).get("context_id"),
        "policy_id": action.get("policy_profile", {}).get("policy_id"),
        "interpretations": [
            {
                "interpretation_id": record.get("interpretation_id"),
                "assessment_kind": record.get("assessment_kind"),
                "uncertainty": record.get("uncertainty"),
                "policy_rule_refs": record.get("policy_rule_refs", []),
                "evidence_refs": [_ref_summary(item) for item in record.get("evidence_refs", [])],
                "negative_boundary": record.get("negative_boundary"),
            }
            for record in records
        ],
        "candidate_actions": [
            {
                "action_id": item.get("action_id"),
                "disposition": item.get("disposition"),
                "authorization_state": item.get("authorization_state"),
                "evidence_refs": [_ref_summary(ref) for ref in item.get("evidence_refs", [])],
            }
            for item in action.get("candidate_action_set", {}).get("actions", [])
        ],
        "disposition_result": action.get("disposition_result"),
        "why_unresolved_or_unavailable": [
            {
                "interpretation_id": record.get("interpretation_id"),
                "status": record.get("uncertainty", {}).get("status"),
                "reasons": record.get("uncertainty", {}).get("reasons", []),
            }
            for record in records
            if record.get("uncertainty", {}).get("status") != "resolved"
        ],
        "negative_boundary": action.get("failure_modes", []),
    }


def explain_run(run_directory: str | Path) -> dict[str, Any]:
    """Return a deterministic, source-addressed explanation of a run."""
    root = Path(run_directory).resolve()
    if root.is_file() and root.name == "run-receipt.json":
        root = root.parent
    receipts = sorted(root.glob("*/run-receipt.json"))
    if (root / "run-receipt.json").is_file():
        receipts.insert(0, root / "run-receipt.json")
    if not receipts:
        raise FileNotFoundError(f"no run receipt found below {root}")
    result: dict[str, Any] = {
        "explanation_version": "1.0",
        "run_id": root.name,
        "run_directory": str(root),
        "workflow": "full_pipeline" if (root / "comparison").is_dir() else "realization",
        "realizations": [_realization_explanation(path) for path in receipts],
        "comparison": _comparison_explanation(root),
        "interpretation": _interpretation_explanation(root),
        "known_nonclaims": [
            "This explanation is a structured view of source-addressed artifacts, not an independent scientific conclusion.",
            "Validation PASS establishes the declared contract and artifact closure only.",
            "CandidateAction is not a recommendation, authorization, execution command, or causal-effect certificate.",
        ],
    }
    return result
