"""Closed runtime evaluators for upstream-registered SOFAUDIT coordinates."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any

from sof_runtime.contracts import ContractError, load_json
from sof_runtime.contracts.validation import validate_contract
from sof_runtime.paths import RUNTIME_CONTRACT_ROOT


EVALUATOR_REGISTRY = RUNTIME_CONTRACT_ROOT / "coordinate-evaluator-registry.json"
EVALUATOR_REGISTRY_SCHEMA = (
    RUNTIME_CONTRACT_ROOT / "coordinate-evaluator-registry.schema.json"
)
EVALUATION_RESULT_SCHEMA = (
    RUNTIME_CONTRACT_ROOT / "coordinate-evaluation-result.schema.json"
)


@dataclass(frozen=True)
class SourceSelection:
    finding: dict[str, Any] | None
    claim: dict[str, Any] | None
    raw_pairs: list[list[Any]] | None
    pairs: list[list[Any]] | None
    pair_input_form: str | None
    unavailable_state: str | None
    reason: str | None
    descriptor: dict[str, float | int | None] | None = None


@dataclass(frozen=True)
class EvaluationOutcome:
    declaration: dict[str, Any]
    result: dict[str, Any]
    reference: SourceSelection
    target: SourceSelection


def _pair_key(pair: list[Any]) -> str:
    return json.dumps(pair, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _normalize_sector_pairs(
    pairs: list[list[Any]],
    report: dict[str, Any],
    declaration: dict[str, Any],
) -> tuple[list[list[str]], str]:
    encoding = declaration["pair_encoding"]
    labels = report["alignment_readiness"]["sector_metadata"]["labels"]
    if len(labels) != len(set(labels)):
        raise ContractError("report sector labels are not unique")
    endpoints = [endpoint for pair in pairs for endpoint in pair]
    endpoint_forms = {
        "zero_based_index"
        if isinstance(endpoint, int) and not isinstance(endpoint, bool)
        else "label"
        if isinstance(endpoint, str)
        else "unsupported"
        for endpoint in endpoints
    }
    if "unsupported" in endpoint_forms or len(endpoint_forms) != 1:
        raise ContractError(
            f"report finding {declaration['source_selector']['finding_id']} "
            "uses mixed or unsupported pair endpoint forms"
        )
    input_form = next(iter(endpoint_forms), "label")
    if input_form not in encoding["accepted_forms"]:
        raise ContractError(
            f"evaluator {declaration['evaluator_id']} does not accept {input_form} pairs"
        )
    if input_form == "label":
        unknown = sorted({endpoint for endpoint in endpoints if endpoint not in labels})
        if unknown:
            raise ContractError(
                f"report finding {declaration['source_selector']['finding_id']} "
                f"uses unknown sector labels: {unknown}"
            )
        return deepcopy(pairs), input_form

    index_base = encoding["index_base"]
    normalized: list[list[str]] = []
    for pair in pairs:
        normalized_pair: list[str] = []
        for endpoint in pair:
            index = endpoint - index_base
            if index < 0 or index >= len(labels):
                raise ContractError(
                    f"report finding {declaration['source_selector']['finding_id']} "
                    f"uses out-of-range sector index {endpoint}"
                )
            normalized_pair.append(labels[index])
        normalized.append(normalized_pair)
    return normalized, input_form


def _select_source(
    report: dict[str, Any], declaration: dict[str, Any]
) -> SourceSelection:
    selector = declaration["source_selector"]
    finding = next(
        (
            item
            for item in report["findings"]
            if item["finding_id"] == selector["finding_id"]
        ),
        None,
    )
    if finding is None:
        return SourceSelection(
            None,
            None,
            None,
            None,
            None,
            declaration["unavailable_state_policy"]["missing_finding"],
            f"report does not declare finding {selector['finding_id']}",
        )
    claim = next(
        (
            item
            for item in report["claims"]
            if item["claim_id"] == selector["claim_id"]
        ),
        None,
    )
    if claim is None:
        return SourceSelection(
            finding,
            None,
            None,
            None,
            None,
            declaration["unavailable_state_policy"]["missing_claim"],
            f"report finding {selector['finding_id']} lacks claim {selector['claim_id']}",
        )
    binding_modules = [
        module
        for module in report["modules"]
        if module["status"] == "ENABLED"
        and selector["finding_id"] in module["finding_ids"]
        and selector["claim_id"] in module["claim_ids"]
    ]
    if len(binding_modules) != 1:
        raise ContractError(
            f"report does not bind finding {selector['finding_id']} and claim "
            f"{selector['claim_id']} in exactly one enabled module"
        )
    if (
        finding["kind"] != selector["finding_kind"]
        or selector["carrier_kind"] not in claim["carrier_kinds"]
        or selector["carrier_kind"] not in binding_modules[0]["carrier_kinds"]
    ):
        return SourceSelection(
            finding,
            claim,
            None,
            None,
            None,
            declaration["unavailable_state_policy"]["incompatible_payload"],
            f"report source items are incompatible with evaluator {declaration['evaluator_id']}",
        )
    value = finding["value"]
    if declaration["implementation_id"] == "sof-runtime.analogue-descriptor.v1":
        descriptor_field = selector["descriptor_field"]
        descriptor = value.get(descriptor_field) if isinstance(value, dict) else None
        if not isinstance(descriptor, dict) or not descriptor:
            return SourceSelection(
                finding,
                claim,
                None,
                None,
                None,
                declaration["unavailable_state_policy"]["incompatible_payload"],
                f"report finding {selector['finding_id']} lacks {descriptor_field}",
            )
        if any(
            not isinstance(key, str)
            or isinstance(item, bool)
            or not (isinstance(item, (int, float)) or item is None)
            for key, item in descriptor.items()
        ):
            return SourceSelection(
                finding,
                claim,
                None,
                None,
                None,
                declaration["unavailable_state_policy"]["incompatible_payload"],
                f"report finding {selector['finding_id']} has a non-numeric descriptor payload",
            )
        missing_prefixes = [
            prefix
            for prefix in selector["required_descriptor_prefixes"]
            if not any(key.startswith(prefix) for key in descriptor)
        ]
        if missing_prefixes:
            return SourceSelection(
                finding,
                claim,
                None,
                None,
                None,
                declaration["unavailable_state_policy"]["incompatible_payload"],
                f"report finding {selector['finding_id']} lacks descriptor families {missing_prefixes}",
            )
        return SourceSelection(
            finding,
            claim,
            None,
            None,
            None,
            None,
            None,
            deepcopy(descriptor),
        )

    pair_value = None
    if isinstance(value, dict):
        for field in selector["accepted_pair_fields"]:
            if field in value:
                pair_value = value[field]
                break
    if not isinstance(pair_value, list) or any(
        not isinstance(pair, list) or len(pair) != 2 for pair in pair_value
    ):
        return SourceSelection(
            finding,
            claim,
            None,
            None,
            None,
            declaration["unavailable_state_policy"]["incompatible_payload"],
            f"report finding {selector['finding_id']} lacks a supported pair payload",
        )
    raw_pairs = deepcopy(pair_value)
    pairs, pair_input_form = _normalize_sector_pairs(
        raw_pairs, report, declaration
    )
    if len({_pair_key(pair) for pair in pairs}) != len(pairs):
        return SourceSelection(
            finding,
            claim,
            raw_pairs,
            None,
            pair_input_form,
            declaration["unavailable_state_policy"]["incompatible_payload"],
            f"report finding {selector['finding_id']} contains duplicate normalized pairs",
        )
    return SourceSelection(
        finding, claim, raw_pairs, pairs, pair_input_form, None, None
    )


def _unavailable_result(
    declaration: dict[str, Any],
    reference: SourceSelection,
    target: SourceSelection,
) -> dict[str, Any]:
    states = {
        item.unavailable_state
        for item in (reference, target)
        if item.unavailable_state is not None
    }
    state = "UNRESOLVED" if "UNRESOLVED" in states else "NOT_DECLARED"
    reasons = [
        f"{side}: {selection.reason}"
        for side, selection in (("reference", reference), ("target", target))
        if selection.reason is not None
    ]
    return {
        "result_contract_id": "sof-runtime.coordinate-evaluation-result.v1",
        "evaluator_id": declaration["evaluator_id"],
        "evaluator_version": declaration["evaluator_version"],
        "coordinate_id": declaration["coordinate_id"],
        "coordinate_family": declaration["coordinate_family"],
        "value_schema_id": declaration["value_schema_id"],
        "status": "unavailable",
        "comparison_state": state,
        "reference_value": None,
        "target_value": None,
        "normalized_reference_value": None,
        "normalized_target_value": None,
        "pair_encoding": None,
        "relation": None,
        "delta": None,
        "unit": None,
        "metric_result": None,
        "reason": "; ".join(reasons),
    }


def _support_pair_result(
    declaration: dict[str, Any],
    reference: SourceSelection,
    target: SourceSelection,
    metric_id: str,
) -> dict[str, Any]:
    if reference.pairs is None or target.pairs is None:
        raise ContractError("support-pair evaluator received unavailable source values")
    if reference.raw_pairs is None or target.raw_pairs is None:
        raise ContractError("support-pair evaluator lacks raw source values")
    if metric_id == "absolute-difference":
        reference_value = {"support_count": len(reference.raw_pairs)}
        target_value = {"support_count": len(target.raw_pairs)}
        normalized_reference_value = {"support_count": len(reference.pairs)}
        normalized_target_value = {"support_count": len(target.pairs)}
        delta: Any = target_value["support_count"] - reference_value["support_count"]
        metric_value = abs(delta)
        unit = "support pairs"
    elif metric_id == "discrete-mismatch":
        reference_by_key = {_pair_key(pair): pair for pair in reference.pairs}
        target_by_key = {_pair_key(pair): pair for pair in target.pairs}
        missing_pairs = [
            reference_by_key[key] for key in sorted(reference_by_key.keys() - target_by_key.keys())
        ]
        extra_pairs = [
            target_by_key[key] for key in sorted(target_by_key.keys() - reference_by_key.keys())
        ]
        reference_value = {
            "pairs": deepcopy(reference.raw_pairs),
            "pair_count": len(reference.raw_pairs),
        }
        target_value = {
            "pairs": deepcopy(target.raw_pairs),
            "pair_count": len(target.raw_pairs),
        }
        normalized_reference_value = {
            "pairs": deepcopy(reference.pairs),
            "pair_count": len(reference.pairs),
        }
        normalized_target_value = {
            "pairs": deepcopy(target.pairs),
            "pair_count": len(target.pairs),
        }
        delta = {
            "missing_pairs": missing_pairs,
            "extra_pairs": extra_pairs,
            "total_mismatch": len(missing_pairs) + len(extra_pairs),
        }
        metric_value = delta["total_mismatch"]
        unit = "ordered-sector-pair count"
    else:
        raise ContractError(f"unsupported support-pair metric: {metric_id}")
    state = "ALIGNED" if metric_value == 0 else "MISMATCH"
    return {
        "result_contract_id": "sof-runtime.coordinate-evaluation-result.v1",
        "evaluator_id": declaration["evaluator_id"],
        "evaluator_version": declaration["evaluator_version"],
        "coordinate_id": declaration["coordinate_id"],
        "coordinate_family": declaration["coordinate_family"],
        "value_schema_id": declaration["value_schema_id"],
        "status": "computed",
        "comparison_state": state,
        "reference_value": reference_value,
        "target_value": target_value,
        "normalized_reference_value": normalized_reference_value,
        "normalized_target_value": normalized_target_value,
        "pair_encoding": {
            "declaration": deepcopy(declaration["pair_encoding"]),
            "reference_input_form": reference.pair_input_form,
            "target_input_form": target.pair_input_form,
        },
        "relation": "equal" if state == "ALIGNED" else "mismatch",
        "delta": delta,
        "unit": unit,
        "metric_result": {
            "metric_id": metric_id,
            "status": "computed",
            "value": metric_value,
        },
        "reason": None,
    }


def _analogue_descriptor_result(
    declaration: dict[str, Any],
    reference: SourceSelection,
    target: SourceSelection,
    metric_id: str,
) -> dict[str, Any]:
    if metric_id != "coordinatewise-record":
        raise ContractError(f"unsupported analogue-descriptor metric: {metric_id}")
    if reference.descriptor is None or target.descriptor is None:
        raise ContractError("analogue-descriptor evaluator received unavailable values")
    reference_keys = set(reference.descriptor)
    target_keys = set(target.descriptor)
    if reference_keys != target_keys:
        missing = sorted(reference_keys - target_keys)
        extra = sorted(target_keys - reference_keys)
        raise ContractError(
            "analogue descriptor keys require explicit identity: "
            f"missing_from_target={missing}, extra_in_target={extra}"
        )
    delta: dict[str, float | int | str | None] = {}
    mismatch_count = 0
    for key in sorted(reference_keys):
        reference_value = reference.descriptor[key]
        target_value = target.descriptor[key]
        if reference_value == target_value:
            delta[key] = 0 if reference_value is not None else None
            continue
        mismatch_count += 1
        if isinstance(reference_value, (int, float)) and isinstance(
            target_value, (int, float)
        ):
            delta[key] = target_value - reference_value
        else:
            delta[key] = "null-mismatch"
    state = "ALIGNED" if mismatch_count == 0 else "MISMATCH"
    return {
        "result_contract_id": "sof-runtime.coordinate-evaluation-result.v1",
        "evaluator_id": declaration["evaluator_id"],
        "evaluator_version": declaration["evaluator_version"],
        "coordinate_id": declaration["coordinate_id"],
        "coordinate_family": declaration["coordinate_family"],
        "value_schema_id": declaration["value_schema_id"],
        "status": "computed",
        "comparison_state": state,
        "reference_value": deepcopy(reference.descriptor),
        "target_value": deepcopy(target.descriptor),
        "normalized_reference_value": deepcopy(reference.descriptor),
        "normalized_target_value": deepcopy(target.descriptor),
        "pair_encoding": None,
        "relation": "equal" if state == "ALIGNED" else "mismatch",
        "delta": delta,
        "unit": "declared black-box probe score (percent)",
        "metric_result": {
            "metric_id": metric_id,
            "status": "computed",
            "value": mismatch_count,
        },
        "reason": None,
    }


class CoordinateEvaluatorRegistry:
    """Resolve exact coordinate IDs to a closed runtime implementation set."""

    def __init__(self, document: dict[str, Any]) -> None:
        self.document = document
        declarations = document["evaluators"]
        self._by_coordinate = {
            declaration["coordinate_id"]: declaration for declaration in declarations
        }
        if len(self._by_coordinate) != len(declarations):
            raise ContractError("coordinate evaluator registry contains duplicate coordinate ids")
        evaluator_ids = [item["evaluator_id"] for item in declarations]
        if len(set(evaluator_ids)) != len(evaluator_ids):
            raise ContractError("coordinate evaluator registry contains duplicate evaluator ids")

    @classmethod
    def load(cls) -> "CoordinateEvaluatorRegistry":
        document = load_json(EVALUATOR_REGISTRY)
        validate_contract(
            document,
            EVALUATOR_REGISTRY_SCHEMA,
            label="coordinate evaluator registry",
        )
        return cls(document)

    def resolve(self, coordinate_id: str) -> dict[str, Any]:
        declaration = self._by_coordinate.get(coordinate_id)
        if declaration is None:
            raise ContractError(
                f"no registered coordinate evaluator for {coordinate_id}"
            )
        return declaration

    def evaluate(
        self,
        coordinate_id: str,
        reference_report: dict[str, Any],
        target_report: dict[str, Any],
        alignment_specification: dict[str, Any],
        comparison_specification: dict[str, Any],
    ) -> EvaluationOutcome:
        declaration = self.resolve(coordinate_id)
        normalization_id = comparison_specification["normalization"][
            "normalization_id"
        ]
        metric_id = comparison_specification["metric"]["metric_id"]
        alignment_kind = alignment_specification.get("alignment_kind")
        if alignment_kind not in declaration["supported_alignment_kinds"]:
            raise ContractError(
                f"{coordinate_id} evaluator does not support alignment {alignment_kind}"
            )
        if alignment_kind == "identity":
            for pair_kind in ("sector", "observable"):
                pairs = alignment_specification.get(f"{pair_kind}_pairs", [])
                if any(
                    item.get("reference_id") != item.get("target_id") for item in pairs
                ):
                    raise ContractError(
                        f"{coordinate_id} identity alignment relabels {pair_kind} ids"
                    )
        if normalization_id not in declaration["supported_normalizations"]:
            raise ContractError(
                f"{coordinate_id} evaluator does not support normalization {normalization_id}"
            )
        if metric_id not in declaration["supported_metrics"]:
            raise ContractError(
                f"{coordinate_id} evaluator does not support metric {metric_id}"
            )
        reference = _select_source(reference_report, declaration)
        target = _select_source(target_report, declaration)
        if reference.unavailable_state or target.unavailable_state:
            result = _unavailable_result(declaration, reference, target)
        elif declaration["implementation_id"] == "sof-runtime.support-pairs.v1":
            result = _support_pair_result(
                declaration, reference, target, metric_id
            )
        elif declaration["implementation_id"] == "sof-runtime.analogue-descriptor.v1":
            result = _analogue_descriptor_result(
                declaration, reference, target, metric_id
            )
        else:
            raise ContractError(
                f"unimplemented coordinate evaluator {declaration['implementation_id']}"
            )
        validate_contract(
            result,
            EVALUATION_RESULT_SCHEMA,
            label=f"coordinate evaluation {coordinate_id}",
        )
        return EvaluationOutcome(declaration, result, reference, target)


__all__ = [
    "CoordinateEvaluatorRegistry",
    "EVALUATION_RESULT_SCHEMA",
    "EVALUATOR_REGISTRY",
    "EVALUATOR_REGISTRY_SCHEMA",
    "EvaluationOutcome",
]
