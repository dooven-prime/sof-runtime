from __future__ import annotations

from typing import Any

from sof_runtime.contracts import ContractError, validate_contract
from sof_runtime.paths import MARKOV_CONTRACT_ROOT


SOURCE_SCHEMA = MARKOV_CONTRACT_ROOT / "source.schema.json"


def normalize_source(payload: dict[str, Any]) -> dict[str, Any]:
    validate_contract(payload, SOURCE_SCHEMA, label="Markov source")
    size = len(payload["states"])
    rows = payload["transition_numerators"]
    denominators = payload["row_denominators"]
    if len(rows) != size or len(denominators) != size:
        raise ContractError("Markov matrix and denominator census must match the state count")
    for index, (row, denominator) in enumerate(zip(rows, denominators, strict=True)):
        if len(row) != size:
            raise ContractError(f"Markov row {index} must contain {size} entries")
        if sum(row) != denominator:
            raise ContractError(
                f"Markov row {index} has numerator sum {sum(row)}, expected {denominator}"
            )
    return payload


def support_adjacency(payload: dict[str, Any]) -> tuple[tuple[bool, ...], ...]:
    normalize_source(payload)
    return tuple(
        tuple(value > 0 for value in row)
        for row in payload["transition_numerators"]
    )


def build_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    normalize_source(payload)
    labels = payload["states"]
    source_id = payload["source_id"]

    def absent(description: str, *, applicable: bool = True) -> dict[str, Any]:
        return {
            "availability": "NOT_DECLARED" if applicable else "NOT_APPLICABLE",
            "description": description,
        }

    return {
        "manifest_version": "1.0",
        "manifest_id": f"markov.{source_id}",
        "record_kind": "strict_sof",
        "sof_semantics_version": "2.0",
        "adapter": {
            "id": "markov-positive-word-adapter",
            "version": "0.1.0",
            "domain": "finite exact rational Markov operators",
            "source_type": "rime.markov.source.v1",
        },
        "space": {"dimension": len(labels), "scalar_field": "complex"},
        "capabilities": {
            "sectorization": {
                "availability": "DECLARED",
                "description": "Singleton coordinate sectors indexed by Markov states.",
                "configuration": {
                    "origin": "declared state coordinate decomposition",
                    "realization_status": "exact",
                    "complete": True,
                    "labels": labels,
                    "provenance": source_id,
                },
            },
            "operator_carrier": {
                "availability": "DECLARED",
                "description": "One exact rational row-stochastic operator P.",
                "configuration": {
                    "alphabet_id": f"alphabet.{source_id}",
                    "word_convention": "positive",
                    "adjoint_closed": False,
                    "projectors_are_letters": False,
                },
            },
            "operator_system": absent("No operator-system module is requested."),
            "route_carrier": absent("No routed-product module is requested."),
            "word_carrier": {
                "availability": "DECLARED",
                "description": "Exact positive powers of the single labelled operator P.",
                "configuration": {
                    "semantics": "positive powers P^d with d starting at one"
                },
            },
            "positive_associative_closure": absent("No algebra-closure claim is requested."),
            "observable_star_closure": absent("No star-closure claim is requested."),
            "sector_enriched_star_closure": absent("No sector-enriched closure claim is requested."),
            "lie_hall_carrier": absent("No Lie/Hall family is declared."),
            "deformation_chart": absent("The positive-word run is static.", applicable=False),
            "proxy_diagnostic": absent("No proxy diagnostic is used.", applicable=False),
            "diagnostic_analogue": absent("This is a strict SOF realization.", applicable=False),
        },
        "semantic_convention_requirements": {
            "operative_alphabet": "required",
            "word_convention": "required",
            "projector_letter_policy": "required",
            "direction_convention": "required",
            "depth_indexing": "required",
            "hall_convention": "not_applicable",
        },
        "run_policy_requirements": {
            "threshold": "not_applicable",
            "cutoff": "not_applicable",
            "norm": "not_applicable",
            "numerical_tolerance": "not_applicable",
            "saturation_audit": "required",
            "sampling_grid": "not_applicable",
            "trajectory_parameterization": "not_applicable",
        },
        "notes": [
            "The extension records off-diagonal support first hits for powers of P.",
            "Nonnegative entries prevent route-sum cancellation in this declared source class.",
            "No mixing-time, route-depth, rank-collapse, or Lie/Hall claim is inferred.",
        ],
    }
