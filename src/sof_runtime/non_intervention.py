"""Shared SOF v2.1 non-intervention boundaries and structural guards."""

from __future__ import annotations

import re
from typing import Any, Iterable


SOFRS_OBJECT_TRANSITION_BOUNDARY = {
    "artifact_role": "INFORMATIONAL_REPORT",
    "intervention_semantics": "NONE",
    "source_state_transition_authority": "NONE",
    "implementation_purity_status": "NOT_ESTABLISHED_BY_SOFRS",
}

SOFAUDIT_ATTRIBUTION_BOUNDARY = {
    "localization_scope": "ALIGNED_REPORT_COORDINATES",
    "interpretation_status": "DOWNSTREAM",
    "defect_attribution_status": "OUT_OF_SCOPE_FOR_SOFAUDIT",
    "causal_status": "OUT_OF_SCOPE_FOR_SOFAUDIT",
    "reference_role": "COMPARISON_ROLE_ONLY",
    "reference_causal_role": "NOT_A_CAUSAL_BASELINE",
}

SOFACTION_EXECUTION_BOUNDARY = {
    "artifact_role": "CANDIDATE_SET_ONLY",
    "selection_semantics": "OUT_OF_SCOPE_FOR_SOFACTION",
    "authorization_semantics": "OUT_OF_SCOPE_FOR_SOFACTION",
    "execution_semantics": "OUT_OF_SCOPE_FOR_SOFACTION",
    "outcome_semantics": "OUT_OF_SCOPE_FOR_SOFACTION",
    "effect_semantics": "OUT_OF_SCOPE_FOR_SOFACTION",
}

SOFRS_FORBIDDEN_KEYS = {
    "causes_transition",
    "executes_change",
    "object_transition",
    "source_transition",
    "source_state_transition",
    "intervention_result",
    "execution_receipt",
    "authorization_receipt",
    "causal_attribution",
}

SOFAUDIT_FORBIDDEN_KEYS = {
    "causal_attribution",
    "causal_mechanism",
    "caused_by",
    "defect_attribution",
    "control_group",
    "causal_baseline",
}

DOWNSTREAM_ARTIFACT_ROLES = {
    "selected-plan",
    "sofplan",
    "authorization-receipt",
    "sofauth",
    "execution-receipt",
    "sofexec",
    "executor-result",
    "post-action-observation",
    "outcome-record",
    "sofoutcome",
    "effect-certificate",
    "sofeffect",
}


def iter_key_paths(value: Any, prefix: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}"
            yield path, key
            yield from iter_key_paths(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_key_paths(child, f"{prefix}[{index}]")


def forbidden_key_paths(value: Any, forbidden: set[str]) -> list[str]:
    return [path for path, key in iter_key_paths(value) if key in forbidden]


def normalize_role(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    for suffix in ("-json", "-artifact"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
    return normalized


def downstream_role_paths(value: Any) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    role_keys = {"role", "evidence_role", "artifact_type", "receipt_kind"}

    def visit(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                child_path = f"{path}.{key}"
                if (
                    key in role_keys
                    and isinstance(child, str)
                    and normalize_role(child) in DOWNSTREAM_ARTIFACT_ROLES
                ):
                    violations.append((child_path, child))
                visit(child, child_path)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{path}[{index}]")

    visit(value, "$")
    return violations
