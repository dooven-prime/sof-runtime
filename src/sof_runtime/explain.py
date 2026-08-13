"""Structured provenance explanation over a source-addressed artifact graph."""

from __future__ import annotations

import hashlib
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest_value(value: Any) -> str | None:
    if isinstance(value, str) and len(value) == 64:
        return value
    if isinstance(value, dict):
        digest = value.get("value")
        if isinstance(digest, str) and len(digest) == 64:
            return digest
    return None


def _artifact_ref(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"uri": value}
    if not isinstance(value, dict):
        raise ValueError("source-addressed reference must be a string or object")
    nested = value.get("artifact")
    if isinstance(nested, str):
        result = {"uri": nested}
        if "digest" in value:
            result["digest"] = value["digest"]
        return result
    if isinstance(nested, dict):
        return nested
    return value


def _path_from_uri(uri: str) -> Path:
    path = Path(uri)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _ref_summary(ref: Any) -> Any:
    if not isinstance(ref, dict):
        return ref
    result: dict[str, Any] = {}
    for key in (
        "uri",
        "artifact",
        "digest",
        "role",
        "id",
        "audit_id",
        "receipt_id",
    ):
        if key in ref:
            result[key] = ref[key]
    if "artifact" in ref and isinstance(ref["artifact"], dict):
        result["artifact"] = _ref_summary(ref["artifact"])
    if "validation_receipt" in ref:
        result["validation_receipt"] = _ref_summary(ref["validation_receipt"])
    return result or ref


def _digest_ref(path: Path, role: str) -> dict[str, Any]:
    digest = _sha256(path)
    return {
        "role": role,
        "uri": f"artifact://sha256/{digest}",
        "digest": {"algorithm": "sha256", "value": digest},
    }


class _ArtifactGraph:
    """Resolve JSON nodes by declared URI or digest within one supplied closure."""

    def __init__(self, seed: Path):
        self.seed = seed.resolve()
        self.root = self.seed.parent if self.seed.is_file() else self.seed
        self.payloads: dict[Path, dict[str, Any]] = {}
        self.by_digest: dict[str, list[Path]] = {}
        candidates = [self.seed] if self.seed.is_file() else self.root.rglob("*.json")
        for path in candidates:
            if not path.is_file():
                continue
            try:
                payload = load_json(path)
            except (OSError, ValueError):
                continue
            resolved = path.resolve()
            self.payloads[resolved] = payload
            self.by_digest.setdefault(_sha256(resolved), []).append(resolved)

    def nodes(self, predicate: Any) -> list[tuple[Path, dict[str, Any]]]:
        return [
            (path, payload)
            for path, payload in self.payloads.items()
            if predicate(payload)
        ]

    def resolve(self, ref: Any) -> tuple[Path, dict[str, Any]]:
        artifact = _artifact_ref(ref)
        expected = _digest_value(artifact.get("digest"))
        uri = artifact.get("uri")
        if isinstance(uri, str):
            path = _path_from_uri(uri).resolve()
            if path.is_file():
                actual = _sha256(path)
                if expected is not None and actual != expected:
                    raise ValueError(f"artifact digest mismatch for {uri}")
                return path, load_json(path)
        if expected is not None:
            matches = self.by_digest.get(expected, [])
            if matches:
                path = sorted(matches)[0]
                return path, self.payloads[path]
        raise FileNotFoundError(f"source-addressed JSON artifact is unavailable: {uri}")

    def one_primary(
        self,
        predicate: Any,
        label: str,
    ) -> tuple[Path, dict[str, Any]] | None:
        nodes = self.nodes(predicate)
        by_digest: dict[str, tuple[Path, dict[str, Any]]] = {}
        for path, payload in nodes:
            by_digest.setdefault(_sha256(path), (path, payload))
        if len(by_digest) > 1:
            raise ValueError(f"ambiguous {label} artifacts in explanation closure")
        return next(iter(by_digest.values()), None)

    def receipt_for(
        self,
        artifact_type: str,
        owner_key: str,
        artifact_digest: str,
    ) -> tuple[Path, dict[str, Any]] | None:
        matches = []
        for path, payload in self.payloads.items():
            if payload.get("artifact_type") != artifact_type:
                continue
            owner = payload.get(owner_key, {})
            ref = owner.get("artifact") if isinstance(owner, dict) else None
            if _digest_value(_artifact_ref(ref).get("digest")) == artifact_digest:
                matches.append((path, payload))
        if len(matches) > 1:
            distinct = {_sha256(path) for path, _ in matches}
            if len(distinct) > 1:
                raise ValueError(f"ambiguous receipts for {artifact_digest}")
        return sorted(matches, key=lambda item: str(item[0]))[0] if matches else None

    def realization_receipt_for(
        self, candidate_digest: str
    ) -> tuple[Path, dict[str, Any]] | None:
        """Find the realization receipt that closes over one candidate."""
        matches: list[tuple[Path, dict[str, Any]]] = []
        for path, payload in self.payloads.items():
            if payload.get("workflow_version") is None:
                continue
            if payload.get("stage") != "realization":
                continue
            candidate = payload.get("realization_candidate")
            if _digest_value(_artifact_ref(candidate).get("digest")) == candidate_digest:
                matches.append((path, payload))
        if len(matches) > 1:
            distinct = {_sha256(path) for path, _ in matches}
            if len(distinct) > 1:
                raise ValueError(f"ambiguous realization receipts for {candidate_digest}")
        return sorted(matches, key=lambda item: str(item[0]))[0] if matches else None

    def realization_receipt_for_ref(
        self, candidate_ref: Any
    ) -> tuple[Path, dict[str, Any]] | None:
        """Resolve a candidate and locate its source-addressed realization receipt."""
        candidate_path, _ = self.resolve(candidate_ref)
        candidate_digest = _sha256(candidate_path)
        receipt = self.realization_receipt_for(candidate_digest)
        if receipt is not None:
            return receipt
        for parent in (candidate_path.parent, *candidate_path.parents):
            receipt_path = parent / "run-receipt.json"
            if not receipt_path.is_file():
                continue
            try:
                payload = load_json(receipt_path)
            except (OSError, ValueError):
                continue
            if payload.get("stage") != "realization":
                continue
            receipt_candidate = payload.get("realization_candidate")
            if _digest_value(_artifact_ref(receipt_candidate).get("digest")) == candidate_digest:
                return receipt_path.resolve(), payload
        return None


def _validator_summary(receipt: dict[str, Any] | None) -> dict[str, Any] | None:
    if receipt is None:
        return None
    validator = receipt.get("validator", {})
    return {
        "status": receipt.get("status"),
        "receipt_id": receipt.get("receipt_id"),
        "validator_id": validator.get("validator_id"),
        "validator_version": validator.get("validator_version"),
        "implementation": _ref_summary(validator.get("implementation")),
    }


def _unavailable_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for coordinate_id, coordinate in payload.get("coordinates", {}).items():
        state = coordinate.get("comparison_state") or coordinate.get("result_state")
        if state in UNAVAILABLE_STATES:
            findings.append(
                {
                    "coordinate_id": coordinate_id,
                    "state": state,
                    "reason": coordinate.get("reason")
                    or coordinate.get("negative_boundary"),
                }
            )
    for item in payload.get("degradation_items", []):
        findings.append(
            {
                "coordinate_id": item.get("item_id"),
                "state": item.get("result_state", "UNAVAILABLE"),
                "reason": item.get("statement") or item.get("degradation_reason"),
            }
        )
    return findings


def _report_explanation(
    report: dict[str, Any],
    report_ref: dict[str, Any],
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "report_id": report.get("report_id"),
        "artifact": _ref_summary(report_ref),
        "record_kind": report.get("record_kind"),
        "source_mapping": report.get("source_mapping", {}).get("status"),
        "validation": _validator_summary(receipt),
    }


def _realization_from_report(
    graph: _ArtifactGraph,
    report: dict[str, Any],
    report_ref: dict[str, Any],
    receipt: dict[str, Any] | None,
    realization_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    declaration: dict[str, Any] = {}
    candidate: dict[str, Any] = {}
    for source_ref in report.get("source_artifacts", []):
        try:
            _, payload = graph.resolve(source_ref)
        except (FileNotFoundError, ValueError):
            continue
        if "declaration_version" in payload and "domain_id" in payload:
            declaration = payload
        if "candidate_version" in payload and "candidate_kind" in payload:
            candidate = payload
    source_ref = report.get("provenance", {}).get("source_snapshot")
    candidate_kind = candidate.get("candidate_kind")
    eligibility = (
        realization_receipt.get("eligibility")
        if realization_receipt is not None
        else candidate_kind
    )
    canonical_compilable = (
        realization_receipt.get("canonical_compilable")
        if realization_receipt is not None
        else (candidate_kind == "canonical_compilable" if candidate_kind is not None else None)
    )
    result = {
        "stage": "realization",
        "source": _ref_summary(source_ref),
        "source_id": candidate.get("source_id") or (
            realization_receipt.get("source", {}).get("source_id")
            if realization_receipt is not None
            else None
        ),
        "eligibility": eligibility,
        "canonical_compilable": canonical_compilable,
        "adapter": {
            "id": report.get("source_mapping", {}).get("adapter_id"),
            "version": report.get("source_mapping", {}).get("adapter_version"),
            "domain_id": declaration.get("domain_id"),
        },
        "declared": {
            "carriers": declaration.get("supported_carriers", []),
            "observables": declaration.get("supported_observables", []),
            "capabilities": declaration.get("capabilities", []),
            "unsupported": declaration.get("unsupported_capabilities", []),
            "sectorization_origin": declaration.get("sectorization_origin"),
        },
        "known_nonclaims": (
            realization_receipt.get("negative_boundary", [])
            if realization_receipt is not None
            else candidate.get("negative_boundary", [])
        ),
        "report": _report_explanation(report, report_ref, receipt),
        "claims": [
            {
                "claim_id": claim.get("claim_id"),
                "statement": claim.get("statement"),
                "claim_status": claim.get("claim_status"),
                "negative_boundary": claim.get("negative_boundary"),
            }
            for claim in report.get("claims", [])
        ],
    }
    return result


def _realization_from_receipt(
    graph: _ArtifactGraph,
    path: Path,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    _, declaration = graph.resolve(receipt["adapter"]["declaration"])
    _, candidate = graph.resolve(receipt["realization_candidate"])
    return {
        "stage": "realization",
        "run_receipt": _digest_ref(path, "realization-receipt"),
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


def _comparison_explanation(
    audit: dict[str, Any],
    audit_ref: dict[str, Any],
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "stage": "comparison",
        "audit_id": audit.get("audit_id"),
        "artifact": _ref_summary(audit_ref),
        "validation": _validator_summary(receipt),
        "alignment": {
            "sector": audit.get("alignment", {})
            .get("sector_alignment", {})
            .get("alignment_id"),
            "observable": audit.get("alignment", {})
            .get("observable_alignment", {})
            .get("alignment_id"),
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


def _interpretation_explanation(
    action: dict[str, Any],
    action_ref: dict[str, Any],
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    records = action.get("interpretation_records", [])
    return {
        "stage": "interpretation",
        "action_record_id": action.get("action_record_id"),
        "artifact": _ref_summary(action_ref),
        "validation": _validator_summary(receipt),
        "context_id": action.get("action_context", {}).get("context_id"),
        "policy_id": action.get("policy_profile", {}).get("policy_id"),
        "interpretations": [
            {
                "interpretation_id": record.get("interpretation_id"),
                "assessment_kind": record.get("assessment_kind"),
                "uncertainty": record.get("uncertainty"),
                "policy_rule_refs": record.get("policy_rule_refs", []),
                "evidence_refs": [
                    _ref_summary(item) for item in record.get("evidence_refs", [])
                ],
                "negative_boundary": record.get("negative_boundary"),
            }
            for record in records
        ],
        "candidate_actions": [
            {
                "action_id": item.get("action_id"),
                "disposition": item.get("disposition"),
                "authorization_state": item.get("authorization_state"),
                "evidence_refs": [
                    _ref_summary(ref) for ref in item.get("evidence_refs", [])
                ],
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
    """Explain the strongest artifact reachable from a supplied closure."""
    graph = _ArtifactGraph(Path(run_directory))
    action_node = graph.one_primary(
        lambda item: "sofaction_version" in item and "source_audit" in item,
        "SOFAction",
    )
    audit_node = graph.one_primary(
        lambda item: "sofaudit_version" in item and "source_reports" in item,
        "SOFAUDIT",
    )
    report_nodes = graph.nodes(
        lambda item: "sofrs_version" in item and "report_id" in item
    )
    realization_nodes = graph.nodes(
        lambda item: "workflow_version" in item
        and "realization_candidate" in item
        and "adapter" in item
    )

    action: dict[str, Any] | None = None
    action_ref: dict[str, Any] | None = None
    action_receipt: dict[str, Any] | None = None
    if action_node is not None:
        action_path, action = action_node
        action_digest = _sha256(action_path)
        receipt_node = graph.receipt_for(
            "sofaction_validation_receipt", "action", action_digest
        )
        if receipt_node is not None:
            _, action_receipt = receipt_node
            action_ref = _artifact_ref(action_receipt["action"]["artifact"])
        else:
            action_ref = _digest_ref(action_path, "action")
        audit_path, audit = graph.resolve(action["source_audit"])
        audit_ref = _artifact_ref(action["source_audit"])
        _, audit_receipt = graph.resolve(action["source_audit"]["validation_receipt"])
        audit_node = (audit_path, audit)
    elif audit_node is not None:
        audit_path, audit = audit_node
        audit_digest = _sha256(audit_path)
        receipt_node = graph.receipt_for(
            "sofaudit_validation_receipt", "audit", audit_digest
        )
        audit_receipt = receipt_node[1] if receipt_node else None
        audit_ref = (
            _artifact_ref(audit_receipt["audit"]["artifact"])
            if audit_receipt is not None
            else _digest_ref(audit_path, "audit")
        )
    else:
        audit = None
        audit_receipt = None
        audit_ref = None

    reports: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]] = []
    if audit is not None:
        for role in ("reference", "target"):
            source = audit.get("source_reports", {}).get(role)
            if not isinstance(source, dict):
                continue
            _, report = graph.resolve(source["artifact"])
            try:
                _, report_receipt = graph.resolve(source["validation_receipt"])
            except (FileNotFoundError, ValueError):
                report_receipt = None
            reports.append((report, _artifact_ref(source["artifact"]), report_receipt))
    elif report_nodes:
        for report_path, report in sorted(
            report_nodes, key=lambda item: str(item[1].get("report_id"))
        ):
            digest = _sha256(report_path)
            receipt_node = graph.receipt_for(
                "sofrs_report_validation_receipt", "report", digest
            )
            receipt = receipt_node[1] if receipt_node else None
            ref = (
                _artifact_ref(receipt["report"]["artifact"])
                if receipt is not None
                else _digest_ref(report_path, "report")
            )
            reports.append((report, ref, receipt))

    if reports:
        realizations = []
        for report, ref, receipt in reports:
            realization_receipt = None
            for source_ref in report.get("source_artifacts", []):
                try:
                    receipt_node = graph.realization_receipt_for_ref(source_ref)
                except (FileNotFoundError, ValueError):
                    receipt_node = None
                if receipt_node is not None:
                    realization_receipt = receipt_node[1]
                    break
            realizations.append(
                _realization_from_report(
                    graph, report, ref, receipt, realization_receipt
                )
            )
    else:
        realizations = [
            _realization_from_receipt(graph, path, receipt)
            for path, receipt in sorted(realization_nodes, key=lambda item: str(item[0]))
        ]

    if action is not None:
        workflow = "full_pipeline"
        run_id = action.get("action_record_id")
    elif audit is not None:
        workflow = "comparison"
        run_id = audit.get("audit_id")
    elif reports:
        workflow = "report"
        run_id = reports[0][0].get("report_id")
    elif realizations:
        workflow = "realization"
        run_id = realizations[0].get("source_id")
    else:
        raise FileNotFoundError("no explainable SOF artifact graph found")

    return {
        "explanation_version": "1.1",
        "run_id": run_id,
        "workflow": workflow,
        "realizations": realizations,
        "comparison": (
            _comparison_explanation(audit, audit_ref, audit_receipt)
            if audit is not None and audit_ref is not None
            else None
        ),
        "interpretation": (
            _interpretation_explanation(action, action_ref, action_receipt)
            if action is not None and action_ref is not None
            else None
        ),
        "known_nonclaims": [
            "This explanation is a structured view of source-addressed artifacts, not an independent scientific conclusion.",
            "Validation PASS establishes the declared contract and artifact closure only.",
            "CandidateAction is not a recommendation, authorization, execution command, or causal-effect certificate.",
        ],
    }
