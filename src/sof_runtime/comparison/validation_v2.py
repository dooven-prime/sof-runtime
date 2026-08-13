from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from sof_runtime.artifacts.digest import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.paths import COMPARISON_CONTRACT_ROOT, PROJECT_ROOT
from sof_runtime.reporting.assembly_v2 import resolve_artifact_reference
from sof_runtime.reporting.validation_v2 import validate_receipt, validate_report

from . import evaluators as evaluator_module
from .evaluators import (
    EVALUATION_RESULT_SCHEMA,
    EVALUATOR_REGISTRY,
    EVALUATOR_REGISTRY_SCHEMA,
    CoordinateEvaluatorRegistry,
)


AUDIT_SCHEMA = COMPARISON_CONTRACT_ROOT / "sofaudit.schema.json"
AUDIT_RECEIPT_SCHEMA = COMPARISON_CONTRACT_ROOT / "validation-receipt.schema.json"
REQUIRED_PROFILE_SOURCE_ROLES = {
    "audit-profile",
    "coordinate-semantics-registry",
}
MATCH_STATES = {"ALIGNED", "MISMATCH"}
REQUIRED_GUARDS = {
    "source-report-receipts-validate",
    "paper-x-record-kind-permission",
    "paper-x-carrier-alignment",
    "paper-x-policy-alignment",
    "paper-x-evidence-alignment",
    "paper-x-promotion-audit",
    "paper-xiii-sector-alignment",
    "paper-xiii-observable-alignment",
    "paper-xiii-comparison-specification",
}
RESULT_CLAIM_STATUS = {
    "ESTABLISHED": "Theorem",
    "CERTIFIED": "Computational Certificate",
    "OBSERVED": "Computational Observation",
}
UNAVAILABLE_RESULTS = {
    "NOT_DECLARED": "NOT_DECLARED",
    "NOT_APPLICABLE": "NOT_APPLICABLE",
    "INCOMPARABLE": "DECLARED",
    "UNRESOLVED": "DECLARED",
}
CLAIM_COMPATIBILITY = {
    ("comparison_relation", None): {
        "comparison_specification",
        "audit_engine",
        "alignment_validator",
    },
    ("comparison_relation", "comparison_audit"): {
        "audit_engine",
        "alignment_validator",
    },
    ("external_mathematical_object", "object"): {
        "independent_oracle",
        "independent_validator",
    },
    ("empirical_domain_system", "object"): {
        "independent_validator",
        "external_evaluator",
    },
    ("representation_interface", None): {
        "comparison_specification",
        "migration_adapter",
    },
    ("representation_interface", "protocol_conformance"): {
        "comparison_specification",
        "independent_validator",
    },
    ("protocol_conformance", "protocol_conformance"): {
        "comparison_specification",
        "independent_validator",
    },
    ("migration_consistency", "migration_assembly"): {
        "migration_adapter",
        "independent_validator",
    },
}


def _complete_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _artifact_reference(artifact: dict[str, Any]) -> dict[str, Any]:
    return {"uri": artifact["uri"], "digest": artifact["digest"]}


def _expected_regime(reference_kind: str, target_kind: str) -> str:
    if reference_kind == target_kind == "strict_sof":
        return "strict_vs_strict"
    if reference_kind == target_kind == "diagnostic_analogue":
        return "analogue_vs_analogue"
    return "strict_vs_analogue"


def _report_universe(report: dict[str, Any], kind: str) -> list[str]:
    key = "sector_metadata" if kind == "sector" else "observable_metadata"
    return report["alignment_readiness"][key]["labels"]


def _report_items(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for collection in ("claims", "degradation_items", "findings"):
        for item in report[collection]:
            item_id = item.get("report_item_id") or item.get("finding_id")
            if item_id is not None:
                items[item_id] = item
    return items


def _validate_runtime_evaluator_closure(
    audit: dict[str, Any],
    artifact_map: dict[str, dict[str, Any]],
    role_map: dict[str, dict[str, Any]],
    resolved_artifacts: dict[str, Path],
    reports: dict[str, dict[str, Any]],
    alignment_specification: dict[str, Any],
    comparison_specification: dict[str, Any],
    profile: dict[str, Any],
    regime: str,
) -> None:
    if audit["provenance"]["kind"] != "native" or audit["provenance"].get(
        "generator_id"
    ) != "sof-runtime.external-adapter-comparison":
        return
    registry_artifact = role_map.get("coordinate-evaluator-registry")
    implementation_artifact = role_map.get("coordinate-evaluator-implementation")
    if registry_artifact is None or implementation_artifact is None:
        raise ContractError("runtime SOFAUDIT lacks evaluator execution closure")
    registry = load_json(resolved_artifacts[registry_artifact["id"]])
    validate_contract(
        registry,
        EVALUATOR_REGISTRY_SCHEMA,
        label="coordinate evaluator registry snapshot",
    )
    trusted_registry = load_json(EVALUATOR_REGISTRY)
    validate_contract(
        trusted_registry,
        EVALUATOR_REGISTRY_SCHEMA,
        label="trusted coordinate evaluator registry",
    )
    if canonical_json_bytes(registry) != canonical_json_bytes(trusted_registry):
        raise ContractError(
            "coordinate evaluator registry snapshot differs from the trusted registry"
        )
    implementation_path = resolved_artifacts[implementation_artifact["id"]]
    implementation_digest = sha256_file(implementation_path)
    trusted_implementation_digest = sha256_file(
        Path(evaluator_module.__file__).resolve()
    )
    if implementation_digest != trusted_implementation_digest:
        raise ContractError(
            "coordinate evaluator implementation differs from the trusted implementation"
        )
    declarations = {
        item["coordinate_id"]: item for item in registry["evaluators"]
    }
    evaluator_registry = CoordinateEvaluatorRegistry(trusted_registry)
    required_generation_ids = {
        registry_artifact["id"],
        implementation_artifact["id"],
    }
    for coordinate_id, coordinate in audit["coordinates"].items():
        role = f"coordinate-evaluation-result-{coordinate_id}"
        result_artifact = role_map.get(role)
        if result_artifact is None:
            raise ContractError(f"{coordinate_id} lacks an evaluation result artifact")
        result = load_json(resolved_artifacts[result_artifact["id"]])
        validate_contract(
            result,
            EVALUATION_RESULT_SCHEMA,
            label=f"coordinate evaluation result {coordinate_id}",
        )
        declaration = declarations.get(coordinate_id)
        if declaration is None:
            raise ContractError(f"{coordinate_id} lacks an evaluator declaration")
        if declaration["implementation_digest"] != {
            "algorithm": "sha256",
            "value": implementation_digest,
        }:
            raise ContractError(
                f"{coordinate_id} implementation differs from its registry digest"
            )
        allowed_carriers = (
            set(profile["carrier_requirements"]["strict"])
            if regime == "strict_vs_strict"
            else set(profile["carrier_requirements"]["analogue"])
            if regime == "analogue_vs_analogue"
            else set(profile["carrier_requirements"]["strict"])
            | set(profile["carrier_requirements"]["analogue"])
        )
        if declaration["source_selector"]["carrier_kind"] not in allowed_carriers:
            raise ContractError(
                f"{coordinate_id} evaluator carrier is absent from the Audit Profile"
            )
        if any(
            result[field] != declaration[field]
            for field in (
                "evaluator_id",
                "evaluator_version",
                "coordinate_id",
                "coordinate_family",
                "value_schema_id",
            )
        ):
            raise ContractError(f"{coordinate_id} result differs from evaluator registry")
        expected_projection = {
            "comparison_state": result["comparison_state"],
            "coordinate_family": result["coordinate_family"],
            "value_schema_id": result["value_schema_id"],
            "value": (
                {
                    "reference_value": result["reference_value"],
                    "target_value": result["target_value"],
                    "normalized_reference_value": result[
                        "normalized_reference_value"
                    ],
                    "normalized_target_value": result["normalized_target_value"],
                    "relation": result["relation"],
                    "delta": result["delta"],
                    "unit": result["unit"],
                    "metric_result": result["metric_result"],
                    "policy_refs": [],
                    "oracle_ref": None,
                }
                if result["status"] == "computed"
                else None
            ),
        }
        if any(coordinate[field] != value for field, value in expected_projection.items()):
            raise ContractError(f"{coordinate_id} differs from its evaluation result")
        replay = evaluator_registry.evaluate(
            coordinate_id,
            reports["reference"],
            reports["target"],
            alignment_specification,
            comparison_specification,
        ).result
        if _complete_json_bytes(replay) != _complete_json_bytes(result):
            raise ContractError(
                f"{coordinate_id} evaluation result differs from trusted replay"
            )
        required_coordinate_ids = {
            registry_artifact["id"],
            implementation_artifact["id"],
            result_artifact["id"],
        }
        if required_coordinate_ids - set(coordinate["source_artifact_ids"]):
            raise ContractError(f"{coordinate_id} lacks evaluator artifact references")
        required_generation_ids.add(result_artifact["id"])
    if required_generation_ids - set(audit["provenance"]["generation_artifact_ids"]):
        raise ContractError("runtime SOFAUDIT provenance omits evaluator artifacts")
    if required_generation_ids - set(audit["claim"]["source_artifact_ids"]):
        raise ContractError("runtime SOFAUDIT claim omits evaluator artifacts")


def _classification_error(item: dict[str, Any], label: str) -> str | None:
    status = item["claim_status"]
    target = item["claim_target"]
    certificate_class = item["certificate_class"]
    if status is None:
        if target is not None or certificate_class is not None:
            return f"{label} has a classification without a claim"
        return None
    if status == "Computational Certificate":
        if certificate_class is None:
            return f"{label} certificate lacks certificate_class"
    elif certificate_class is not None:
        return f"{label} non-certificate has certificate_class"
    allowed = CLAIM_COMPATIBILITY.get((target, certificate_class))
    if allowed is None:
        return f"{label} target/certificate combination is not permitted"
    if item["classification_source"] not in allowed:
        return f"{label} classification_source is incompatible"
    return None


def _result_claim_error(item: dict[str, Any], label: str) -> str | None:
    expected = RESULT_CLAIM_STATUS.get(item["result_state"])
    if expected is not None and item["claim_status"] != expected:
        return f"{label} has an illegal result/claim status pair"
    if expected is None and item["claim_status"] is not None:
        return f"{label} unavailable result has a positive claim status"
    return None


def _validate_alignment(
    component: dict[str, Any] | None,
    *,
    name: str,
    kind: str,
    reference_ids: list[str],
    target_ids: list[str],
    artifact_ids: set[str],
) -> bool:
    if component is None:
        return False
    if component["alignment_kind"] != kind:
        raise ContractError(f"{name} has the wrong alignment_kind")
    pairs = component["pairs"]
    pair_refs = [item["reference_id"] for item in pairs]
    pair_targets = [item["target_id"] for item in pairs]
    reference_universe = set(reference_ids)
    target_universe = set(target_ids)
    mapped_refs = set(pair_refs)
    mapped_targets = set(pair_targets)
    if mapped_refs - reference_universe or mapped_targets - target_universe:
        raise ContractError(f"{name} pair id is outside the linked report universe")
    if any(count > 1 for count in Counter(zip(pair_refs, pair_targets)).values()):
        raise ContractError(f"{name} contains a duplicate pair")
    if set(component["unmatched_reference_ids"]) != reference_universe - mapped_refs:
        raise ContractError(f"{name} unmatched reference ids are incorrect")
    if set(component["unmatched_target_ids"]) != target_universe - mapped_targets:
        raise ContractError(f"{name} unmatched target ids are incorrect")
    function_on_reference = len(pair_refs) == len(set(pair_refs))
    properties = {
        "total_on_reference": bool(reference_universe)
        and mapped_refs == reference_universe,
        "total_on_target": bool(target_universe) and mapped_targets == target_universe,
        "injective": bool(pairs)
        and function_on_reference
        and len(pair_targets) == len(set(pair_targets)),
        "surjective": bool(pairs) and mapped_targets == target_universe,
    }
    if component["properties"] != properties:
        raise ContractError(f"{name} properties differ from recomputation")
    state = component["state"]
    if state == "TOTAL" and not (
        properties["total_on_reference"] and properties["total_on_target"]
    ):
        raise ContractError(f"{name} TOTAL state lacks two-sided coverage")
    if state == "PARTIAL" and (
        not pairs
        or properties["total_on_reference"] and properties["total_on_target"]
    ):
        raise ContractError(f"{name} PARTIAL state is inconsistent")
    if state in {"UNRESOLVED", "INCOMPARABLE"} and pairs:
        raise ContractError(f"{name} unavailable state carries operative pairs")
    map_kind = component["map_kind"]
    relations = {item["relation"] for item in pairs}
    if map_kind == "bijection" and not all(properties.values()):
        raise ContractError(f"{name} is not the declared bijection")
    if map_kind == "injection" and not (
        properties["total_on_reference"] and properties["injective"]
    ):
        raise ContractError(f"{name} is not the declared injection")
    if map_kind == "surjection" and not (
        function_on_reference
        and properties["total_on_reference"]
        and properties["surjective"]
    ):
        raise ContractError(f"{name} is not the declared surjection")
    if "aggregation" in relations and map_kind != "quotient":
        raise ContractError(f"{name} aggregation requires quotient map_kind")
    if "refinement" in relations and map_kind != "refinement":
        raise ContractError(f"{name} refinement requires refinement map_kind")
    for pair in pairs:
        if set(pair["evidence_artifact_ids"]) - artifact_ids:
            raise ContractError(f"{name} pair references unknown evidence")
    return state in {"TOTAL", "PARTIAL"}


def _validate_comparison_specification(
    specification: dict[str, Any], artifact_ids: set[str]
) -> None:
    normalization = specification["normalization"]
    tolerance = normalization["equality_tolerance"]
    if normalization["numeric_policy"] == "exact" and tolerance not in {None, 0}:
        raise ContractError("exact comparison requires null or zero tolerance")
    if normalization["numeric_policy"] == "float-tolerance" and (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or tolerance <= 0
    ):
        raise ContractError("float comparison requires positive tolerance")
    synchronization = specification["parameter_synchronization"]
    map_id = synchronization["map_artifact_id"]
    if synchronization["kind"] == "declared-map" and map_id is None:
        raise ContractError("declared-map synchronization lacks an artifact")
    if map_id is not None and map_id not in artifact_ids:
        raise ContractError("parameter synchronization references unknown artifact")
    aggregation = specification["aggregation"]
    weights_id = aggregation["weights_artifact_id"]
    if aggregation["scalarization"] == "weighted-hamming" and (
        weights_id is None and aggregation["weight_declaration"] is None
    ):
        raise ContractError("weighted-hamming lacks weights")
    if weights_id is not None and weights_id not in artifact_ids:
        raise ContractError("aggregation references unknown weights")


def _validate_semantics(
    audit: dict[str, Any], *, repository_root: Path
) -> None:
    artifacts = audit["source_artifacts"]
    artifact_ids = [item["id"] for item in artifacts]
    artifact_roles = [item["role"] for item in artifacts]
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ContractError("SOFAUDIT source artifact ids are not unique")
    if len(artifact_roles) != len(set(artifact_roles)):
        raise ContractError("SOFAUDIT source artifact roles are not unique")
    artifact_map = {item["id"]: item for item in artifacts}
    role_map = {item["role"]: item for item in artifacts}
    required_roles = {
        "reference-report",
        "target-report",
        "reference-report-validation-receipt",
        "target-report-validation-receipt",
        "audit-profile",
        "coordinate-semantics-registry",
    }
    if audit["provenance"]["kind"] == "migration":
        required_roles.add("source-audit")
    if required_roles - set(role_map):
        raise ContractError("SOFAUDIT lacks a required artifact role")
    resolved_artifacts = {}
    for artifact in artifacts:
        resolved_artifacts[artifact["id"]] = resolve_artifact_reference(
            _artifact_reference(artifact), repository_root=repository_root
        )

    reports: dict[str, dict[str, Any]] = {}
    for side in ("reference", "target"):
        report_ref = audit["source_reports"][side]
        if report_ref["comparison_role_basis"]["role"] != side:
            raise ContractError(f"{side} comparison role is inconsistent")
        if _artifact_reference(role_map[f"{side}-report"]) != report_ref["artifact"]:
            raise ContractError(f"{side} report differs from artifact closure")
        if (
            _artifact_reference(role_map[f"{side}-report-validation-receipt"])
            != report_ref["validation_receipt"]
        ):
            raise ContractError(f"{side} receipt differs from artifact closure")
        report_path = resolve_artifact_reference(
            report_ref["artifact"], repository_root=repository_root
        )
        receipt_path = resolve_artifact_reference(
            report_ref["validation_receipt"], repository_root=repository_root
        )
        report = validate_report(report_path, repository_root=repository_root)
        receipt = validate_receipt(receipt_path, repository_root=repository_root)
        if receipt["report"]["report_id"] != report["report_id"]:
            raise ContractError(f"{side} receipt identifies a different report")
        for key in ("report_id", "sofrs_version", "record_kind"):
            if report_ref[key] != report[key]:
                raise ContractError(f"{side} {key} differs from linked report")
        if report["sofrs_version"] != "2.0":
            raise ContractError("SOFAUDIT v2 consumes only SOFRS v2")
        if set(report_ref["comparison_role_basis"]["evidence_artifacts"]) - set(
            artifact_ids
        ):
            raise ContractError(f"{side} role basis references unknown evidence")
        reports[side] = report

    regime = _expected_regime(
        reports["reference"]["record_kind"], reports["target"]["record_kind"]
    )
    if audit["regime"] != regime:
        raise ContractError("SOFAUDIT regime differs from report-kind recomputation")
    profile = audit["audit_profile"]
    if profile["applicable_regime"] != regime:
        raise ContractError("Audit Profile regime differs from report-kind recomputation")
    if set(profile["requested_coordinate_ids"]) != set(audit["coordinates"]):
        raise ContractError("Audit Profile and coordinate keys are not closed")
    profile_artifact_id = profile["profile_artifact_id"]
    registry_artifact_id = profile["coordinate_registry_artifact_id"]
    if artifact_map.get(profile_artifact_id, {}).get("role") != "audit-profile":
        raise ContractError("Audit Profile does not bind an audit-profile artifact")
    if artifact_map.get(registry_artifact_id, {}).get("role") != "coordinate-semantics-registry":
        raise ContractError("Audit Profile does not bind a coordinate registry artifact")
    profile_document = load_json(resolved_artifacts[profile_artifact_id])
    source_profile = profile_document.get("audit_profile", profile_document)
    expected_profile = {
        "profile_id": profile_document.get("profile_id", source_profile.get("profile_id")),
        "profile_version": profile_document.get("profile_version", source_profile.get("profile_version")),
        "profile_artifact_id": profile_artifact_id,
        "coordinate_registry_artifact_id": registry_artifact_id,
        **source_profile,
    }
    if profile != expected_profile:
        raise ContractError("embedded Audit Profile differs from its source artifact")
    profile_comparison_specification = profile_document.get(
        "comparison_specification"
    )
    if (
        profile_comparison_specification is not None
        and audit["comparison_specification"] != profile_comparison_specification
    ):
        raise ContractError(
            "comparison specification differs from its profile artifact"
        )
    registry = load_json(resolved_artifacts[registry_artifact_id])
    if registry.get("registry_id") != "sofaudit.coordinate-semantics.v1":
        raise ContractError("unsupported coordinate semantics registry")
    value_schema_by_family = {
        family: item["value_schema_id"]
        for family, item in registry["coordinates"].items()
    }
    if set(profile["coordinate_families"]) - set(value_schema_by_family):
        raise ContractError("Audit Profile references an unknown coordinate family")
    if REQUIRED_PROFILE_SOURCE_ROLES - set(profile["required_evidence_roles"]):
        raise ContractError(
            "Audit Profile does not require its source-addressed profile and registry artifacts"
        )
    if set(profile["required_evidence_roles"]) - set(artifact_roles):
        raise ContractError("Audit Profile lacks required evidence roles")

    alignment_ready: dict[str, bool] = {}
    for field, kind in (
        ("sector_alignment", "sector"),
        ("observable_alignment", "observable"),
    ):
        metadata_key = (
            "sector_metadata" if kind == "sector" else "observable_metadata"
        )
        reference_metadata = reports["reference"]["alignment_readiness"][metadata_key]
        target_metadata = reports["target"]["alignment_readiness"][metadata_key]
        jointly_not_applicable = (
            reference_metadata["status"] == "NOT_APPLICABLE"
            and target_metadata["status"] == "NOT_APPLICABLE"
        )
        if jointly_not_applicable:
            if audit["alignment"][field] is not None:
                raise ContractError(
                    f"{field} must be null when both report universes are not applicable"
                )
            alignment_ready[field] = True
        else:
            alignment_ready[field] = _validate_alignment(
                audit["alignment"][field],
                name=field,
                kind=kind,
                reference_ids=_report_universe(reports["reference"], kind),
                target_ids=_report_universe(reports["target"], kind),
                artifact_ids=set(artifact_ids),
            )

    guards = audit["inherited_compiler_guards"]
    checks = guards["condition_checks"]
    check_map = {item["condition_id"]: item for item in checks}
    if len(check_map) != len(checks) or set(check_map) != REQUIRED_GUARDS:
        raise ContractError("inherited guard set is not exact")
    for field, condition_id in (
        ("sector_alignment", "paper-xiii-sector-alignment"),
        ("observable_alignment", "paper-xiii-observable-alignment"),
    ):
        component = audit["alignment"][field]
        expected = (
            "SATISFIED"
            if alignment_ready[field]
            else "FAILED"
            if component is not None and component["state"] == "INCOMPARABLE"
            else "NOT_CHECKED"
        )
        if check_map[condition_id]["status"] != expected:
            raise ContractError(f"{condition_id} differs from alignment recomputation")
    if any(item["status"] == "FAILED" for item in checks):
        guard_state = "REJECTED"
    elif any(item["status"] != "SATISFIED" for item in checks):
        guard_state = "UNRESOLVED"
    else:
        guard_state = "ADMITTED"
    if guards["state"] != guard_state:
        raise ContractError("inherited guard state differs from recomputation")
    for check in checks:
        if set(check["evidence_artifact_ids"]) - set(artifact_ids):
            raise ContractError("inherited guard references unknown evidence")

    for coordinate_id, coordinate in audit["coordinates"].items():
        state = coordinate["comparison_state"]
        if guard_state != "ADMITTED" and state in MATCH_STATES:
            raise ContractError("unresolved or rejected guards emitted a comparison")
        if not all(alignment_ready.values()) and state in MATCH_STATES:
            raise ContractError("comparison coordinate lacks validated alignment")
        expected_value_schema = value_schema_by_family.get(coordinate["coordinate_family"])
        if expected_value_schema is None:
            raise ContractError(f"{coordinate_id} uses an unregistered coordinate family")
        if coordinate["value_schema_id"] != expected_value_schema:
            raise ContractError(f"{coordinate_id} value schema differs from family")
        binding = coordinate["report_item_binding"]
        if binding["binding_state"] == "paired":
            if binding["reason"] is not None:
                raise ContractError(f"{coordinate_id} paired binding has a reason")
            for side in ("reference", "target"):
                item_ref = binding[f"{side}_item_ref"]
                if item_ref is None:
                    raise ContractError(f"{coordinate_id} paired binding is incomplete")
                if item_ref["report_id"] != reports[side]["report_id"]:
                    raise ContractError(f"{coordinate_id} item binds the wrong report")
                report_artifact = role_map[f"{side}-report"]
                if item_ref["artifact_digest"] != report_artifact["digest"]:
                    raise ContractError(f"{coordinate_id} item digest is incorrect")
                report_item = _report_items(reports[side]).get(
                    item_ref["report_item_id"]
                )
                if report_item is None:
                    raise ContractError(f"{coordinate_id} item is absent from report")
                if report_item.get("source_output_item_id") != item_ref[
                    "source_output_item_id"
                ]:
                    raise ContractError(f"{coordinate_id} CompilerOutput item differs")
        elif not binding["reason"]:
            raise ContractError(f"{coordinate_id} unpaired binding lacks a reason")

        if state in MATCH_STATES:
            error = _result_claim_error(coordinate, f"coordinate {coordinate_id}")
            if error:
                raise ContractError(error)
            error = _classification_error(coordinate, f"coordinate {coordinate_id}")
            if error:
                raise ContractError(error)
            if coordinate["value"] is None:
                raise ContractError(f"{coordinate_id} comparison lacks a value")
            metric_result = coordinate["value"]["metric_result"]
            if metric_result is not None and metric_result["metric_id"] != audit[
                "comparison_specification"
            ]["metric"]["metric_id"]:
                raise ContractError(f"{coordinate_id} metric differs from Theta")
            oracle_ref = coordinate["value"]["oracle_ref"]
            if oracle_ref is not None and oracle_ref not in artifact_map:
                raise ContractError(f"{coordinate_id} references unknown oracle")
        else:
            if coordinate["result_state"] != UNAVAILABLE_RESULTS[state]:
                raise ContractError(f"{coordinate_id} unavailable result state is wrong")
            if any(
                coordinate[field] is not None
                for field in ("claim_status", "claim_target", "certificate_class", "value")
            ):
                raise ContractError(f"{coordinate_id} unavailable state was promoted")
            if not coordinate["reason"]:
                raise ContractError(f"{coordinate_id} unavailable state lacks a reason")
        if set(coordinate["source_artifact_ids"]) - set(artifact_ids):
            raise ContractError(f"{coordinate_id} references unknown artifacts")

    if guard_state == "REJECTED" and audit["claim"]["claim_status"] is not None:
        raise ContractError("rejected audit emitted an affirmative claim")
    if guard_state == "UNRESOLVED" and audit["claim"]["claim_target"] not in {
        None,
        "migration_consistency",
        "protocol_conformance",
    }:
        raise ContractError("unresolved audit emitted an affirmative comparison claim")
    error = _result_claim_error(audit["claim"], "audit claim")
    if error:
        raise ContractError(error)
    error = _classification_error(audit["claim"], "audit claim")
    if error:
        raise ContractError(error)
    if set(audit["claim"]["source_artifact_ids"]) - set(artifact_ids):
        raise ContractError("audit claim references unknown artifacts")

    basis = audit["comparison_basis"]
    if basis["reference_role_basis"] != audit["source_reports"]["reference"][
        "comparison_role_basis"
    ]:
        raise ContractError("comparison basis differs from reference role basis")
    for identifier in (
        basis["reference_role_basis"]["evidence_artifacts"]
        + basis["alignment_evidence"]
        + basis["policy_compatibility"]["policy_artifact_ids"]
    ):
        if identifier not in artifact_map:
            raise ContractError("comparison basis references unknown artifact")
    object_claim = audit["claim"]["claim_target"] in {
        "external_mathematical_object",
        "empirical_domain_system",
    }
    oracle = basis["object_level_oracle"]
    oracle_ids = (
        oracle["raw_source_artifacts"]
        + oracle["independent_recomputation_artifacts"]
        + ([oracle["oracle_result_artifact"]] if oracle["oracle_result_artifact"] else [])
        + ([oracle["audit_result_artifact"]] if oracle["audit_result_artifact"] else [])
    )
    if set(oracle_ids) - set(artifact_ids):
        raise ContractError("comparison oracle references unknown artifact")
    independence = oracle["independence"]
    oracle_roles = (
        bool(oracle["raw_source_artifacts"])
        and all(
            artifact_map[item]["role"].startswith("raw-source")
            for item in oracle["raw_source_artifacts"]
        )
        and bool(oracle["independent_recomputation_artifacts"])
        and all(
            artifact_map[item]["role"].startswith("independent-recomputation")
            for item in oracle["independent_recomputation_artifacts"]
        )
        and oracle["oracle_result_artifact"] is not None
        and artifact_map[oracle["oracle_result_artifact"]]["role"]
        == "object-oracle-result"
        and oracle["audit_result_artifact"] is not None
        and artifact_map[oracle["audit_result_artifact"]]["role"] == "audit-result"
    )
    oracle_independent = (
        independence["implementation_relation"] != "not_assessed"
        and independence["producer_relation"] != "not_assessed"
        and independence["input_source"]
        in {"canonical_raw_sources", "frozen_source_artifacts"}
        and independence["producer_cache_used"] is False
    )
    oracle_complete = oracle["status"] == "SATISFIED" and oracle_roles and oracle_independent
    if set(oracle["raw_source_artifacts"]) & set(
        oracle["independent_recomputation_artifacts"]
    ):
        raise ContractError("independent recomputation reuses raw-source artifact identity")
    reference_basis = basis["reference_role_basis"]
    reference_sufficient = reference_basis["role"] == "reference"
    if object_claim:
        reference_sufficient = reference_sufficient and (
            reference_basis["basis_kind"] != "declared_baseline_only"
            and reference_basis["authority_status"] == "ESTABLISHED"
        )
    alignment_sufficient = all(alignment_ready.values()) and bool(
        basis["alignment_evidence"]
    )
    policy_sufficient = (
        basis["policy_compatibility"]["status"] == "SATISFIED"
        and bool(basis["policy_compatibility"]["policy_artifact_ids"])
    )
    complete = (
        reference_sufficient
        and alignment_sufficient
        and policy_sufficient
        and (oracle_complete if object_claim else True)
    )
    expected_basis_status = "COMPLETE" if complete else "PARTIAL"
    if basis["basis_status"] != expected_basis_status:
        raise ContractError("comparison basis status differs from recomputation")
    if object_claim and (
        audit["claim"]["certificate_class"] != "object" or not oracle_complete
    ):
        raise ContractError("Object Certificate lacks an independent oracle")
    if (
        audit["claim"]["certificate_class"] == "comparison_audit" and not complete
    ):
        raise ContractError("Comparison Audit Certificate lacks complete basis")
    for coordinate in audit["coordinates"].values():
        if coordinate["claim_target"] in {
            "external_mathematical_object",
            "empirical_domain_system",
        } and (coordinate["certificate_class"] != "object" or not oracle_complete):
            raise ContractError("coordinate Object Certificate lacks independent oracle")

    provenance = audit["provenance"]
    if provenance["kind"] == "migration":
        source_id = provenance["source_audit_artifact_id"]
        if source_id not in artifact_map or artifact_map[source_id]["role"] != "source-audit":
            raise ContractError("migration provenance does not bind source-audit")
    else:
        if set(provenance["generation_artifact_ids"]) - set(artifact_ids):
            raise ContractError("native provenance references unknown artifacts")
        if audit["claim"]["claim_target"] == "migration_consistency":
            raise ContractError("native provenance issued migration claim")
    _validate_comparison_specification(
        audit["comparison_specification"], set(artifact_ids)
    )
    alignment_artifact = role_map.get("alignment-input")
    runtime_native = (
        audit["provenance"]["kind"] == "native"
        and audit["provenance"].get("generator_id")
        == "sof-runtime.external-adapter-comparison"
    )
    if alignment_artifact is None and runtime_native:
        raise ContractError("native SOFAUDIT lacks an alignment-input artifact")
    if alignment_artifact is not None:
        alignment_specification = load_json(
            resolved_artifacts[alignment_artifact["id"]]
        )
        _validate_runtime_evaluator_closure(
            audit,
            artifact_map,
            role_map,
            resolved_artifacts,
            reports,
            alignment_specification,
            audit["comparison_specification"],
            profile,
            regime,
        )


def validate_audit(
    audit_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    audit = load_json(audit_path)
    validate_contract(audit, AUDIT_SCHEMA, label="SOFAUDIT v2 audit")
    _validate_semantics(audit, repository_root=root)
    return audit


def build_audit_validation_receipt(
    audit_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
    validator_implementation_path: str | Path | None = None,
    receipt_contract_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create the source-addressed Paper XIII receipt consumed by Paper XIV."""

    root = Path(repository_root).resolve()
    path = Path(audit_path).resolve()
    audit = validate_audit(path, repository_root=root)
    implementation = Path(validator_implementation_path or __file__).resolve()
    receipt_contract = Path(receipt_contract_path or AUDIT_RECEIPT_SCHEMA).resolve()
    audit_ref = _artifact_reference_for_path(path, root)
    implementation_ref = _artifact_reference_for_path(implementation, root)
    receipt_contract_ref = _artifact_reference_for_path(receipt_contract, root)
    ordered_artifacts = [
        {"role": "audit", "artifact": audit_ref},
        *[
            {"role": item["role"], "artifact": _artifact_reference(item)}
            for item in audit["source_artifacts"]
        ],
        {"role": "validator-implementation", "artifact": implementation_ref},
        {"role": "validation-receipt-contract", "artifact": receipt_contract_ref},
    ]
    receipt = {
        "receipt_version": "2.0",
        "artifact_type": "sofaudit_validation_receipt",
        "receipt_id": f"receipt.{audit['audit_id']}.sofaudit-v2",
        "status": "PASS",
        "audit": {
            "audit_id": audit["audit_id"],
            "sofaudit_version": "2.0",
            "artifact": audit_ref,
        },
        "validator": {
            "validator_id": "sofaudit.runtime-semantic-validator.v2",
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
                "source-report-receipt-validation",
                "role-regime-profile-closure",
                "alignment-property-recomputation",
                "guard-coordinate-coupling",
                "comparison-basis-recomputation",
                "claim-certificate-compatibility",
            )
        ],
        "negative_boundaries": [
            "This receipt establishes SOFAUDIT protocol conformance only; it does not establish reference truth or action meaning."
        ],
    }
    validate_contract(receipt, AUDIT_RECEIPT_SCHEMA, label="SOFAUDIT validation receipt")
    return receipt


def _artifact_reference_for_path(path: Path, root: Path) -> dict[str, Any]:
    return {
        "uri": path.resolve().relative_to(root).as_posix(),
        "digest": {"algorithm": "sha256", "value": sha256_file(path)},
    }


def validate_audit_validation_receipt(
    receipt_path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    receipt = load_json(receipt_path)
    validate_contract(receipt, AUDIT_RECEIPT_SCHEMA, label="SOFAUDIT validation receipt")
    closure = receipt["artifact_closure"]
    ordered = closure["ordered_artifacts"]
    if closure["artifact_count"] != len(ordered):
        raise ContractError("SOFAUDIT receipt artifact count is incorrect")
    if closure["closure_digest"]["value"] != sha256_bytes(canonical_json_bytes(ordered)):
        raise ContractError("SOFAUDIT receipt closure digest is incorrect")
    role_map = {item["role"]: item["artifact"] for item in ordered}
    if len(role_map) != len(ordered):
        raise ContractError("SOFAUDIT receipt artifact roles are not unique")
    for reference in role_map.values():
        resolve_artifact_reference(reference, repository_root=root)
    audit_path = resolve_artifact_reference(receipt["audit"]["artifact"], repository_root=root)
    if role_map.get("audit") != receipt["audit"]["artifact"]:
        raise ContractError("SOFAUDIT receipt audit differs from its closure")
    audit = validate_audit(audit_path, repository_root=root)
    if receipt["audit"]["audit_id"] != audit["audit_id"]:
        raise ContractError("SOFAUDIT receipt identifies a different audit")
    implementation = resolve_artifact_reference(receipt["validator"]["implementation"], repository_root=root)
    if role_map.get("validator-implementation") != receipt["validator"]["implementation"]:
        raise ContractError("SOFAUDIT receipt validator differs from its closure")
    if sha256_file(implementation) != sha256_file(Path(__file__).resolve()):
        raise ContractError("SOFAUDIT receipt binds a different validator implementation")
    if role_map.get("validation-receipt-contract") != receipt["validator"]["receipt_contract"]:
        raise ContractError("SOFAUDIT receipt contract differs from its closure")
    contract_path = resolve_artifact_reference(
        receipt["validator"]["receipt_contract"], repository_root=root
    )
    if sha256_file(contract_path) != sha256_file(AUDIT_RECEIPT_SCHEMA):
        raise ContractError("SOFAUDIT receipt binds a different receipt contract")
    return receipt
