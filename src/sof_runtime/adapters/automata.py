from __future__ import annotations

from typing import Any

from sof_runtime.contracts import ContractError, validate_contract
from sof_runtime.paths import AUTOMATA_CONTRACT_ROOT


SOURCE_SCHEMA = AUTOMATA_CONTRACT_ROOT / "source.schema.json"


def normalize_source(payload: dict[str, Any]) -> dict[str, Any]:
    validate_contract(payload, SOURCE_SCHEMA, label="automaton source")
    states = payload["states"]
    alphabet = payload["alphabet"]
    transitions = payload["transitions"]
    if set(transitions) != set(alphabet):
        raise ContractError("automaton transitions must have exactly one row per alphabet label")
    state_set = set(states)
    for label in alphabet:
        row = transitions[label]
        if len(row) != len(states):
            raise ContractError(f"transition row {label} must have {len(states)} targets")
        unknown = sorted(set(row) - state_set)
        if unknown:
            raise ContractError(f"transition row {label} has unknown targets: {unknown}")
    return payload


def indexed_transition(payload: dict[str, Any]) -> tuple[tuple[int, ...], ...]:
    normalize_source(payload)
    index = {state: position for position, state in enumerate(payload["states"])}
    return tuple(
        tuple(index[target] for target in payload["transitions"][label])
        for label in payload["alphabet"]
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
        "manifest_id": f"automata.{source_id}",
        "record_kind": "strict_sof",
        "sof_semantics_version": "2.0",
        "adapter": {
            "id": "automata-adapter",
            "version": "0.1.0",
            "domain": "complete deterministic finite automata",
            "source_type": "rime.automata.source.v1",
        },
        "space": {"dimension": len(labels), "scalar_field": "complex"},
        "capabilities": {
            "sectorization": {
                "availability": "DECLARED",
                "description": "Singleton coordinate sectors indexed by automaton states.",
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
                "description": "Labelled deterministic transition operators.",
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
                "description": "Exact positive words in the transition alphabet.",
                "configuration": {
                    "semantics": "exact-length positive deterministic words"
                },
            },
            "positive_associative_closure": absent("No positive-closure claim is requested."),
            "observable_star_closure": absent("No star-closure claim is requested."),
            "sector_enriched_star_closure": absent("No sector-enriched closure claim is requested."),
            "lie_hall_carrier": absent("No Lie/Hall family is declared."),
            "deformation_chart": absent("The rank-collapse run is static.", applicable=False),
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
            "cutoff": "optional",
            "norm": "not_applicable",
            "numerical_tolerance": "not_applicable",
            "saturation_audit": "required",
            "sampling_grid": "not_applicable",
            "trajectory_parameterization": "not_applicable",
        },
        "notes": [
            "Rank collapse is a runtime extension computed from the declared labelled words.",
            "It is not registered as a canonical word-depth field before upstream promotion.",
            "No route or Lie/Hall result is inferred from synchronization depth.",
        ],
    }
