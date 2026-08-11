"""Runtime validation for the published Paper XIV SOFAction v2 object."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote

from sof_runtime.artifacts.digest import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.paths import ACTION_CONTRACT_ROOT, COMPARISON_CONTRACT_ROOT


ACTION_SCHEMA = ACTION_CONTRACT_ROOT / "sofaction.schema.json"
ACTION_RECEIPT_SCHEMA = ACTION_CONTRACT_ROOT / "validation-receipt.schema.json"
UNAVAILABLE_STATES = {"UNRESOLVED", "NOT_DECLARED", "INCOMPARABLE", "NOT_APPLICABLE"}
CANDIDATE_DISPOSITIONS = {
    "Investigate", "RequestEvidence", "Mitigate", "Rollback", "Escalate"
}
RECORD_CLASSES = {"policy_conformance_certificate", "decision_trace_certificate"}


def _path(root: Path, value: str) -> Path:
    candidate = Path(unquote(value))
    return candidate if candidate.is_absolute() else root / candidate


def _audit_reference_errors(reference: dict[str, Any], source: dict[str, Any], root: Path) -> list[str]:
    if "audit_id" in reference:
        expected = {
            "audit_id": source.get("audit_id"),
            "sofaudit_version": source.get("sofaudit_version"),
        }
        if any(reference.get(key) != value for key, value in expected.items()):
            return ["audit evidence refers to a different SOFAUDIT"]
        if reference.get("digest", {}).get("value") != source.get("_digest"):
            return ["audit evidence digest differs from the source SOFAUDIT"]
        if reference.get("validation_receipt") != source.get("_validation_receipt"):
            return ["audit evidence does not bind the source validation receipt"]
        return []
    uri = reference.get("uri", "")
    if not isinstance(uri, str) or not uri.startswith("artifact://"):
        return ["evidence reference is not source-addressed"]
    artifact = _path(root, uri.removeprefix("artifact://"))
    if not artifact.is_file():
        return [f"evidence artifact does not exist: {uri}"]
    if reference.get("digest", {}).get("value") != sha256_file(artifact):
        return [f"evidence artifact digest differs: {uri}"]
    return []


def _predicate_matches(
    predicate: dict[str, Any], audit: dict[str, Any], coordinate_id: str,
    coordinate: dict[str, Any], context: dict[str, Any], policy: dict[str, Any],
) -> bool:
    if predicate.get("predicate_version") != "1.0":
        return False
    op = predicate.get("op")
    if op == "all":
        return all(_predicate_matches(item, audit, coordinate_id, coordinate, context, policy) for item in predicate["args"])
    if op == "any":
        return any(_predicate_matches(item, audit, coordinate_id, coordinate, context, policy) for item in predicate["args"])
    if op == "not":
        return not _predicate_matches(predicate["args"][0], audit, coordinate_id, coordinate, context, policy)
    target_id = predicate.get("coordinate_id")
    target = coordinate if target_id == "*" else audit.get("coordinates", {}).get(target_id)
    if op == "coordinate_exists":
        return target is not None
    if op == "coordinate_state_is":
        return isinstance(target, dict) and target.get("comparison_state") == predicate.get("value")
    if op == "coordinate_carrier_is":
        return isinstance(target, dict) and target.get("carrier", target.get("coordinate_family")) == predicate.get("value")
    if op == "coordinate_relation_is":
        relation = target.get("relation") or target.get("value", {}).get("relation") if isinstance(target, dict) else None
        return relation == predicate.get("value")
    if op == "comparison_role_is":
        return context.get("comparison_role") == predicate.get("value")
    if op == "contract_status_is":
        return context.get("contract_status") == predicate.get("value")
    if op == "authority_status_in":
        return context.get("authority", {}).get("status") in predicate.get("values", [])
    if op == "uncertainty_status_is":
        return context.get("uncertainty_status") == predicate.get("value")
    if op == "transformation_contract_present":
        return bool(context.get("transformation_contract_refs"))
    if op == "context_constraint_has_status":
        return any(
            item.get("constraint_id") == predicate.get("constraint_id")
            and item.get("status") == predicate.get("value")
            for item in context.get("constraints", [])
        )
    if op == "policy_basis_present":
        return bool(policy.get("normative_basis"))
    return False


def _precedence_graph(policy: dict[str, Any]) -> dict[str, set[str]]:
    rule_ids = {rule["rule_id"] for rule in policy["rules"]}
    graph = {rule_id: set() for rule_id in rule_ids}
    for edge in policy["precedence_edges"]:
        before, after = edge["before"], edge["after"]
        if before not in rule_ids or after not in rule_ids or before == after:
            raise ContractError("invalid policy precedence edge")
        graph[before].add(after)
    return graph


def _assert_acyclic(graph: dict[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ContractError("policy precedence contains a cycle")
        if node in visited:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _reaches(graph: dict[str, set[str]], start: str, target: str) -> bool:
    pending = list(graph[start])
    visited: set[str] = set()
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node not in visited:
            visited.add(node)
            pending.extend(graph[node])
    return False


def _matching_rule(
    policy: dict[str, Any], audit: dict[str, Any], coordinate_id: str,
    coordinate: dict[str, Any], context: dict[str, Any], graph: dict[str, set[str]],
) -> tuple[dict[str, Any] | None, bool]:
    rules = {rule["rule_id"]: rule for rule in policy["rules"]}
    suppressed: set[str] = set()
    for exception in policy["exceptions"]:
        if _predicate_matches(exception["when"], audit, coordinate_id, coordinate, context, policy):
            suppressed.update(exception["overrides_rule_ids"])
    matching = {
        rule_id for rule_id, rule in rules.items()
        if rule_id not in suppressed
        and _predicate_matches(rule["when"], audit, coordinate_id, coordinate, context, policy)
    }
    if not matching:
        return None, False
    dominant = [
        rule_id for rule_id in matching
        if all(rule_id == other or _reaches(graph, rule_id, other) for other in matching)
    ]
    if len(dominant) != 1:
        return None, True
    return rules[dominant[0]], False


def _load_source(payload: dict[str, Any], root: Path) -> dict[str, Any]:
    reference = payload["source_audit"]
    source_path = _path(root, reference["artifact"])
    if not source_path.is_file():
        raise ContractError(f"source audit does not exist: {source_path}")
    source = load_json(source_path)
    validate_contract(source, COMPARISON_CONTRACT_ROOT / "sofaudit.schema.json", label="SOFAUDIT v2")
    source["_digest"] = sha256_file(source_path)
    if reference["audit_id"] != source["audit_id"] or reference["digest"]["value"] != source["_digest"]:
        raise ContractError("source_audit does not bind the exact SOFAUDIT artifact")
    receipt = reference["validation_receipt"]
    receipt_path = _path(root, receipt["artifact"])
    if not receipt_path.is_file():
        raise ContractError("source_audit validation receipt does not exist")
    receipt_payload = load_json(receipt_path)
    if receipt["digest"]["value"] != sha256_file(receipt_path):
        raise ContractError("source_audit validation receipt digest differs")
    if receipt_payload.get("receipt_id") != receipt["receipt_id"] or receipt_payload.get("status") != "PASS":
        raise ContractError("source_audit validation receipt is not the bound PASS receipt")
    validator = receipt_payload.get("validator", {})
    if (
        validator.get("validator_id") != receipt.get("validator_id")
        or validator.get("validator_version") != receipt.get("validator_version")
    ):
        raise ContractError("source_audit receipt validator identity differs")
    if receipt_payload.get("audit", {}).get("artifact", {}).get("digest", {}).get("value") != source["_digest"]:
        raise ContractError("source_audit receipt binds a different audit digest")
    source["_validation_receipt"] = receipt
    source["_validation_receipt_payload"] = receipt_payload
    return source


def validate_action(path: str | Path, *, repository_root: str | Path | None = None) -> dict[str, Any]:
    """Validate a Paper XIV SOFAction v2 artifact and return its payload."""

    action_path = Path(path).resolve()
    root = Path(repository_root).resolve() if repository_root is not None else action_path.parent
    payload = load_json(action_path)
    validate_contract(payload, ACTION_SCHEMA, label="SOFAction v2")
    source = _load_source(payload, root)
    source_ref = payload["source_audit"]
    projection = payload["audit_projection"]
    if projection["audit_id"] != source["audit_id"] or projection["signature"] != source["coordinates"]:
        raise ContractError("AuditProjection does not preserve the source coordinate map")
    if canonical_json_bytes(projection["signature"]) != canonical_json_bytes(source["coordinates"]):
        raise ContractError("AuditProjection canonical encoding differs from source coordinates")
    if payload["record_class"] not in RECORD_CLASSES or payload["claim_status"] != "Computational Certificate":
        raise ContractError("SOFAction v2 record class/status pair is not admitted")
    if payload["record_basis"]["basis_kind"] != "protocol_trace":
        raise ContractError("SOFAction record basis must be protocol_trace")
    for reference in payload["record_basis"]["evidence_refs"]:
        errors = _audit_reference_errors(reference, source, root)
        if errors:
            raise ContractError("; ".join(errors))
    context_admitted = payload["context_admission"]["status"] == "admitted"
    policy_admitted = payload["policy_admission"]["status"] == "admitted"
    if not context_admitted or not policy_admitted:
        if payload["action_context"] is not None or payload["policy_profile"] is not None:
            raise ContractError("non-admitted ActionContext or PolicyProfile must be null")
        if payload["interpretation_records"] or payload["candidate_action_set"]["actions"]:
            raise ContractError("non-admitted inputs cannot emit interpretations or candidates")
        if payload["disposition_result"]["kind"] != "no_disposition":
            raise ContractError("non-admitted inputs require no_disposition")
        return payload
    context = payload["action_context"]
    policy = payload["policy_profile"]
    for label, admission in (
        ("context", payload["context_admission"]),
        ("policy", payload["policy_admission"]),
    ):
        if (
            admission["contract_validation"] != "admitted"
            or admission["applicability"] != "applicable"
            or admission["completeness"] != "complete"
            or admission["missing_fields"]
        ):
            raise ContractError(f"admitted {label} has inconsistent admission fields")
    if context["scope"]["audit_id"] != source["audit_id"]:
        raise ContractError("ActionContext scope does not identify the source audit")
    authority = context["authority"]
    if context["actor"]["actor_id"] not in authority["actor_ids"] or context["scope"]["scope_id"] not in authority["scope_ids"]:
        raise ContractError("ActionContext actor or scope is outside authority")
    if source["regime"] not in policy["applicability"]["regimes"] or context["comparison_role"] not in policy["applicability"]["comparison_roles"]:
        raise ContractError("PolicyProfile is not applicable to the source context")
    graph = _precedence_graph(policy)
    _assert_acyclic(graph)
    if len({rule["rule_id"] for rule in policy["rules"]}) != len(policy["rules"]):
        raise ContractError("policy rule IDs are not unique")
    for exception in policy["exceptions"]:
        if not set(exception["overrides_rule_ids"]) <= set(graph):
            raise ContractError("policy exception covers an unknown rule")
    for index, basis in enumerate(policy["normative_basis"]):
        errors = _audit_reference_errors(basis["source_ref"], source, root)
        if "audit_id" in basis["source_ref"]:
            raise ContractError("policy normative basis must use an artifact reference")
        if errors:
            raise ContractError(f"normative basis {index}: {'; '.join(errors)}")
    for index, reference in enumerate(context["transformation_contract_refs"]):
        errors = _audit_reference_errors(reference, source, root)
        if "audit_id" in reference or errors:
            raise ContractError(f"transformation contract {index}: {'; '.join(errors) or 'invalid reference'}")
    rule_ids = set(graph)
    if any(set(rule.get("allowed_dispositions", [])) & CANDIDATE_DISPOSITIONS - set(policy["candidate_families"]) for rule in policy["rules"]):
        raise ContractError("policy rule emits a disposition outside candidate_families")
    coordinates = source["coordinates"]
    interpretations = payload["interpretation_records"]
    seen: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for interpretation in interpretations:
        interpretation_id = interpretation["interpretation_id"]
        if interpretation_id in by_id:
            raise ContractError("duplicate interpretation ID")
        by_id[interpretation_id] = interpretation
        if interpretation["context_refs"] != [context["context_id"]]:
            raise ContractError("interpretation context reference differs")
        for coordinate_ref in interpretation["audit_coordinate_refs"]:
            coordinate_id = coordinate_ref["coordinate_id"]
            if coordinate_id not in coordinates or coordinate_ref["comparison_state"] != coordinates[coordinate_id]["comparison_state"]:
                raise ContractError("interpretation changed a source coordinate")
            source_carrier = coordinates[coordinate_id].get("carrier", coordinates[coordinate_id].get("coordinate_family"))
            if coordinate_ref["carrier"] != source_carrier:
                raise ContractError("interpretation changed a coordinate carrier")
            seen.append(coordinate_id)
            rule, conflict = _matching_rule(policy, source, coordinate_id, coordinates[coordinate_id], context, graph)
            expected_kind = "policy_conflict" if conflict else rule["assessment_kind"] if rule else "inconclusive"
            expected_refs = [rule["rule_id"]] if rule else []
            if interpretation["assessment_kind"] != expected_kind or interpretation["policy_rule_refs"] != expected_refs:
                raise ContractError("validator replay disagrees with InterpretationRecord")
            if coordinates[coordinate_id]["comparison_state"] in UNAVAILABLE_STATES and interpretation["supported_dispositions"]:
                raise ContractError("unavailable coordinate supports an affirmative disposition")
            for reference in interpretation["evidence_refs"]:
                errors = _audit_reference_errors(reference, source, root)
                if errors:
                    raise ContractError("; ".join(errors))
    if sorted(seen) != sorted(coordinates):
        raise ContractError("interpretations must cover every source coordinate exactly once")
    actions = payload["candidate_action_set"]["actions"]
    expected_ids = {
        f"{disposition.lower()}:{item['audit_coordinate_refs'][0]['coordinate_id']}"
        for item in interpretations
        for disposition in item["supported_dispositions"]
        if disposition in CANDIDATE_DISPOSITIONS
    }
    if {action["action_id"] for action in actions} != expected_ids or payload["candidate_action_set"]["count"] != len(actions):
        raise ContractError("Candidate Action Set is not the regenerated policy-supported set")
    for action in actions:
        if action["context_ref"] != context["context_id"] or not set(action["policy_rule_refs"]) <= rule_ids:
            raise ContractError("candidate context or policy references are invalid")
        support = [by_id[item] for item in action["supported_by_interpretations"] if item in by_id]
        if len(support) != len(action["supported_by_interpretations"]):
            raise ContractError("candidate support references an unknown interpretation")
        if action["disposition"] not in set().union(*(set(item["supported_dispositions"]) for item in support)):
            raise ContractError("candidate disposition is not policy-supported")
        for coordinate_ref in action["audit_coordinate_refs"]:
            source_carrier = coordinates[coordinate_ref["coordinate_id"]].get("carrier", coordinates[coordinate_ref["coordinate_id"]].get("coordinate_family"))
            if coordinate_ref["carrier"] != source_carrier or action["carrier"] != source_carrier:
                raise ContractError("candidate carrier does not match its source coordinate")
        for reference in action["evidence_refs"]:
            errors = _audit_reference_errors(reference, source, root)
            if errors:
                raise ContractError("; ".join(errors))
    return payload


def build_action_validation_receipt(
    action_path: str | Path,
    *,
    repository_root: str | Path | None = None,
    validator_implementation_path: str | Path | None = None,
    receipt_contract_path: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(action_path).resolve()
    root = Path(repository_root).resolve() if repository_root is not None else path.parent
    action = validate_action(path, repository_root=root)
    implementation = Path(validator_implementation_path or __file__).resolve()
    receipt_contract = Path(receipt_contract_path or ACTION_RECEIPT_SCHEMA).resolve()

    def reference(artifact_path: Path) -> dict[str, Any]:
        return {
            "uri": artifact_path.relative_to(root).as_posix(),
            "digest": {"algorithm": "sha256", "value": sha256_file(artifact_path)},
        }

    action_ref = reference(path)
    implementation_ref = reference(implementation)
    receipt_contract_ref = reference(receipt_contract)
    ordered_artifacts = [
        {"role": "action", "artifact": action_ref},
        {"role": "validator-implementation", "artifact": implementation_ref},
        {"role": "validation-receipt-contract", "artifact": receipt_contract_ref},
    ]
    receipt = {
        "receipt_version": "2.0",
        "artifact_type": "sofaction_validation_receipt",
        "receipt_id": f"receipt.{action['action_record_id']}.sofaction-v2",
        "status": "PASS",
        "action": {
            "action_record_id": action["action_record_id"],
            "sofaction_version": "2.0",
            "artifact": action_ref,
        },
        "validator": {
            "validator_id": "sofaction.runtime-validator.v2",
            "validator_version": "2.0",
            "implementation": implementation_ref,
            "receipt_contract": receipt_contract_ref,
        },
        "artifact_closure": {
            "artifact_count": len(ordered_artifacts),
            "ordered_artifacts": ordered_artifacts,
            "closure_digest": {
                "algorithm": "sha256",
                "value": sha256_bytes(canonical_json_bytes(ordered_artifacts)),
            },
        },
        "checks": [
            {"check_id": check_id, "status": "PASS"}
            for check_id in (
                "schema-validation",
                "artifact-digest-closure",
                "action-context-policy-admission",
                "audit-projection-preservation",
                "predicate-replay",
                "candidate-set-regeneration",
                "disposition-closure",
                "authorization-boundary",
            )
        ],
        "negative_boundaries": [
            "This receipt establishes interpretation and candidate-set protocol conformance only; it does not establish policy correctness, action feasibility, authorization, or causal effect."
        ],
    }
    validate_contract(receipt, ACTION_RECEIPT_SCHEMA, label="SOFAction validation receipt")
    return receipt


def validate_action_validation_receipt(
    receipt_path: str | Path,
    *,
    repository_root: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(receipt_path).resolve()
    root = Path(repository_root).resolve() if repository_root is not None else path.parent
    receipt = load_json(path)
    validate_contract(receipt, ACTION_RECEIPT_SCHEMA, label="SOFAction validation receipt")
    closure = receipt["artifact_closure"]
    ordered = closure["ordered_artifacts"]
    if closure["artifact_count"] != len(ordered):
        raise ContractError("SOFAction receipt artifact count is incorrect")
    if closure["closure_digest"]["value"] != sha256_bytes(canonical_json_bytes(ordered)):
        raise ContractError("SOFAction receipt closure digest is incorrect")
    role_map = {item["role"]: item["artifact"] for item in ordered}
    if len(role_map) != len(ordered):
        raise ContractError("SOFAction receipt artifact roles are not unique")
    for reference in role_map.values():
        artifact_path = root / reference["uri"]
        if not artifact_path.is_file() or sha256_file(artifact_path) != reference["digest"]["value"]:
            raise ContractError("SOFAction receipt artifact closure is invalid")
    action_ref = receipt["action"]["artifact"]
    if role_map.get("action") != action_ref:
        raise ContractError("SOFAction receipt action differs from its closure")
    action_path = root / action_ref["uri"]
    action = validate_action(action_path, repository_root=root)
    if receipt["action"]["action_record_id"] != action["action_record_id"]:
        raise ContractError("SOFAction receipt identifies a different action object")
    implementation = root / receipt["validator"]["implementation"]["uri"]
    if role_map.get("validator-implementation") != receipt["validator"]["implementation"]:
        raise ContractError("SOFAction receipt validator differs from its closure")
    if sha256_file(implementation) != sha256_file(Path(__file__).resolve()):
        raise ContractError("SOFAction receipt binds a different validator implementation")
    if role_map.get("validation-receipt-contract") != receipt["validator"]["receipt_contract"]:
        raise ContractError("SOFAction receipt contract differs from its closure")
    contract_path = root / receipt["validator"]["receipt_contract"]["uri"]
    if sha256_file(contract_path) != sha256_file(ACTION_RECEIPT_SCHEMA):
        raise ContractError("SOFAction receipt binds a different receipt contract")
    return receipt
