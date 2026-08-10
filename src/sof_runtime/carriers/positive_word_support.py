from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from sof_runtime.adapters.markov import normalize_source, support_adjacency
from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes


PLUGIN_ID = "org.rime.positive-word-support"
PLUGIN_VERSION = "0.1.0"
SUPPORTED_POLICY = {
    "positive_word": {"mode": "exhaustive", "pair_scope": "off_diagonal"}
}


class UnsupportedPositiveWordPolicy(ValueError):
    pass


def _pair_depths(source: dict[str, Any]) -> list[dict[str, Any]]:
    adjacency = support_adjacency(source)
    states = source["states"]
    pairs: list[dict[str, Any]] = []
    for start in range(len(states)):
        distances = {start: 0}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for target, present in enumerate(adjacency[current]):
                if present and target not in distances:
                    distances[target] = distances[current] + 1
                    queue.append(target)
        for target in range(len(states)):
            if start == target:
                continue
            pairs.append(
                {
                    "source": states[start],
                    "target": states[target],
                    "first_positive_depth": distances.get(target),
                }
            )
    return pairs


def compute_positive_word_support(
    source: dict[str, Any],
    *,
    semantic_run_id: str,
    execution_id: str,
    policies: dict[str, Any],
    created_at: str | None = None,
) -> dict[str, Any]:
    normalize_source(source)
    if policies != SUPPORTED_POLICY:
        raise UnsupportedPositiveWordPolicy(
            "positive-word-support v1 supports only exhaustive off-diagonal pair scope"
        )
    pairs = _pair_depths(source)
    finite_depths = [
        item["first_positive_depth"]
        for item in pairs
        if item["first_positive_depth"] is not None
    ]
    now = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload_id = "payload.ordered-pair-first-hits"
    payload = {
        "schema_id": "rime.positive-word-support.finding.v1",
        "payload_id": payload_id,
        "kind": "ordered_pair_first_hit_census",
        "pairs": pairs,
        "reachable_pair_count": len(finite_depths),
        "unreachable_pair_count": len(pairs) - len(finite_depths),
        "maximum_first_hit_depth": max(finite_depths) if finite_depths else None,
        "closure_exhausted": True,
    }
    envelope = {
        "schema_id": "sof.finding.v1",
        "finding_id": f"finding:{source['source_id']}:positive-word-support",
        "record_kind": "strict_sof",
        "source_ref": f"source:{source['source_id']}",
        "carrier_ref": "extension:positive-word-support:v1",
        "scope": {
            "object_ids": [f"positive-word-support:{source['source_id']}"],
            "pair_scope": {"kind": "ordered_off_diagonal"},
            "depth_scope": {"kind": "exact_positive_power", "starts_at": 1},
        },
        "result_state": "OBSERVED",
        "claim_status": "Computational Observation",
        "value_ref": payload_id,
        "policy_refs": ["policy:positive-word-orbit-exhaustion"],
        "evidence_refs": [],
        "derivation_refs": [],
        "provenance": {
            "producer": PLUGIN_ID,
            "producer_version": PLUGIN_VERSION,
            "semantic_run_id": semantic_run_id,
            "execution_id": execution_id,
            "created_at": now,
        },
    }
    return {
        "schema_id": "rime.positive-word-support.bundle.v1",
        "semantic_run_id": semantic_run_id,
        "execution_id": execution_id,
        "source_digest": sha256_bytes(canonical_json_bytes(source)),
        "policy_digest": sha256_bytes(canonical_json_bytes(policies)),
        "object": {
            "schema_id": "rime.positive-word-support.object.v1",
            "object_id": f"positive-word-support:{source['source_id']}",
            "source_ref": f"source:{source['source_id']}",
            "state_count": len(source["states"]),
            "operator_label": "P",
            "pair_scope": "ordered_off_diagonal",
            "semantics": "first positive power with nonzero coordinate-sector support",
        },
        "findings": [{"envelope": envelope, "payload": payload}],
        "claim_boundary": "Single-letter nonnegative support first hits are not mixing times, route depth, rank collapse, or Lie/Hall depth.",
    }


class PositiveWordSupportPlugin:
    plugin_id = PLUGIN_ID
    plugin_version = PLUGIN_VERSION
    carrier_kind = "positive_word_support"
    contract_version = "1.0"
    execution_mode = "python_in_process"
    implementation_language = "python"
    semantic_environment = {
        "algorithm_mode": "exhaustive_support_bfs",
        "arithmetic_backend": "exact_nonnegative_rational_support",
        "dependency_lock_digest": None,
        "feature_flags": [],
    }

    def compute(self, request: dict[str, Any]) -> dict[str, Any]:
        return compute_positive_word_support(
            request["source"],
            semantic_run_id=request["semantic_run_id"],
            execution_id=request["execution_id"],
            policies=request["policies"],
            created_at=request["created_at"],
        )
