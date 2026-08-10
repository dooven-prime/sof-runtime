"""A deliberately small third-party-style adapter.

The adapter knows the domain source and its matrix convention. It does not
construct Capability Manifest, Typed SOF IR, CompilerOutput, or SOFRS.
"""

from __future__ import annotations

from math import isfinite
from typing import Any


class FiniteStateAdapter:
    def describe(self) -> dict[str, Any]:
        return {
            "declaration_version": "1.0",
            "adapter_id": "example.finite-state-adapter",
            "adapter_version": "1.0",
            "domain_id": "finite-state-transition-system",
            "native_objects": ["finite state set", "labelled transition matrix"],
            "supported_carriers": ["sectorization", "operator_carrier", "operator_system"],
            "supported_observables": ["thresholded direct support"],
            "sectorization_origin": "one-hot basis of the declared finite state set",
            "capabilities": ["complete finite sectorization", "labelled transition operators"],
            "unsupported_capabilities": ["route filtration", "positive-word depth", "Lie/Hall depth", "deformation chart"],
            "parameterization": {"state_basis": "one-hot", "channel_direction": "j_to_i"},
            "normalization_threshold_requirements": {"threshold_field": "source.threshold", "matrix_entry_norm": "absolute_value"},
            "evidence_requirements": ["source snapshot", "square-matrix validation", "thresholded support recomputation"],
        }

    def inspect_source(self, source: dict[str, Any]) -> dict[str, Any]:
        states = source.get("states")
        operators = source.get("operators")
        if not isinstance(states, list) or not states or len(set(states)) != len(states):
            raise ValueError("source states must be a non-empty unique list")
        if not isinstance(operators, list) or not operators:
            raise ValueError("source must declare at least one operator")
        dimension = len(states)
        for operator in operators:
            matrix = operator.get("matrix")
            if not isinstance(matrix, list) or len(matrix) != dimension:
                raise ValueError("operator matrix must be square with state dimension")
            for row in matrix:
                if not isinstance(row, list) or len(row) != dimension:
                    raise ValueError("operator matrix row has wrong dimension")
                if not all(isinstance(value, (int, float)) and isfinite(value) for value in row):
                    raise ValueError("operator matrix must contain finite real entries")
        if source.get("matrix_convention") != "row_i_column_j_is_channel_j_to_i":
            raise ValueError("unsupported matrix convention")
        return {
            "status": "PASS",
            "validator_id": "example.finite-state-source-validator",
            "validator_version": "1.0",
            "dimension": dimension,
            "operator_count": len(operators),
            "threshold": source.get("threshold"),
            "checks": ["unique state labels", "square finite matrices", "declared channel convention"],
        }

    def realize(self, source: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        self.inspect_source(source)
        states = source["states"]
        threshold = float(source["threshold"])
        support_pairs = set()
        for operator in source["operators"]:
            for row_index, row in enumerate(operator["matrix"]):
                for column_index, value in enumerate(row):
                    if abs(float(value)) > threshold:
                        support_pairs.add((states[column_index], states[row_index]))
        return {
            "candidate_version": "1.0",
            "record_kind": "strict_sof",
            "source_id": request["source_id"],
            "space": {"dimension": len(states), "scalar_field": "complex"},
            "sectorization": {"labels": states, "origin": "one-hot basis of the declared finite state set", "complete": True},
            "operative_alphabet": {"labels": [item["id"] for item in source["operators"]], "semantics": "declared finite transition matrices"},
            "direct_support": {
                "present": bool(support_pairs),
                "support_pairs": [list(pair) for pair in sorted(support_pairs)],
                "threshold_statement": f"absolute matrix entry > {threshold}",
            },
            "claim": {
                "statement": "The external adapter's declared transition family has certified thresholded direct support.",
                "scope": "The finite state basis and the supplied transition matrices.",
                "negative_boundary": "This claim does not establish route, word, Lie/Hall, causal, or domain-adequacy conclusions.",
            },
        }

    def evidence(self) -> dict[str, Any]:
        return {
            "status": "PASS",
            "evidence_version": "1.0",
            "method": "independent source inspection and support recomputation",
            "claim_boundary": "protocol and finite realization control only",
        }


ADAPTER = FiniteStateAdapter()
