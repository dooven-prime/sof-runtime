from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from sof_runtime.adapters.automata import indexed_transition, normalize_source
from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes


PLUGIN_ID = "org.rime.rank-collapse"
PLUGIN_VERSION = "0.1.0"
SUPPORTED_POLICY = {"rank_collapse": {"mode": "exhaustive"}}


class UnsupportedRankCollapsePolicy(ValueError):
    pass


def _next_subset(subset: tuple[int, ...], letter: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted({letter[state] for state in subset}))


def compute_rank_collapse(
    source: dict[str, Any],
    *,
    semantic_run_id: str,
    execution_id: str,
    policies: dict[str, Any],
    created_at: str | None = None,
) -> dict[str, Any]:
    normalize_source(source)
    if policies != SUPPORTED_POLICY:
        raise UnsupportedRankCollapsePolicy(
            "rank-collapse v1 supports only exhaustive reachable-subset-orbit policy"
        )
    transition = indexed_transition(source)
    states = source["states"]
    alphabet = source["alphabet"]
    full = tuple(range(len(states)))
    distance = {full: 0}
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        full: None
    }
    queue = deque([full])
    while queue:
        current = queue.popleft()
        for letter_index, letter in enumerate(transition):
            nxt = _next_subset(current, letter)
            if nxt not in distance:
                distance[nxt] = distance[current] + 1
                predecessor[nxt] = (current, letter_index)
                queue.append(nxt)

    def shortest_word(target: tuple[int, ...]) -> list[str]:
        word: list[str] = []
        current = target
        while predecessor[current] is not None:
            parent, letter_index = predecessor[current]
            word.append(alphabet[letter_index])
            current = parent
        return list(reversed(word))

    first_hits: list[dict[str, Any]] = []
    now = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for threshold in range(1, len(states) + 1):
        candidates = [
            (depth, subset)
            for subset, depth in distance.items()
            if len(subset) <= threshold
        ]
        payload_id = f"payload.rank-threshold-{threshold}"
        if candidates:
            depth, target = min(candidates, key=lambda item: (item[0], item[1]))
            payload = {
                "schema_id": "rime.rank-collapse.finding.v1",
                "payload_id": payload_id,
                "kind": "rank_threshold_first_hit",
                "rank_threshold": threshold,
                "depth": depth,
                "shortest_word": shortest_word(target),
                "lower_depths_verified": max(depth - 1, 0),
                "closure_exhausted": True,
                "reachable_image_subset_count": len(distance),
            }
        else:
            payload = {
                "schema_id": "rime.rank-collapse.finding.v1",
                "payload_id": payload_id,
                "kind": "rank_threshold_unreachable",
                "rank_threshold": threshold,
                "depth": None,
                "shortest_word": None,
                "lower_depths_verified": None,
                "closure_exhausted": True,
                "reachable_image_subset_count": len(distance),
            }
        envelope = {
            "schema_id": "sof.finding.v1",
            "finding_id": f"finding:{source['source_id']}:rank-threshold:{threshold}",
            "record_kind": "strict_sof",
            "source_ref": f"source:{source['source_id']}",
            "carrier_ref": "extension:rank-collapse:v1",
            "scope": {
                "object_ids": [f"rank-collapse:{source['source_id']}"],
                "pair_scope": None,
                "depth_scope": {"kind": "exact", "rank_threshold": threshold},
            },
            "result_state": "OBSERVED",
            "claim_status": "Computational Observation",
            "value_ref": payload_id,
            "policy_refs": ["policy:reachable-subset-orbit-exhaustion"],
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
        first_hits.append({"envelope": envelope, "payload": payload})

    image_layers = []
    for depth in range(max(distance.values()) + 1):
        layer = sorted(subset for subset, first_hit in distance.items() if first_hit == depth)
        image_layers.append(
            {
                "depth": depth,
                "images": [[states[index] for index in subset] for subset in layer],
                "minimum_rank": min(len(subset) for subset in layer),
            }
        )

    return {
        "schema_id": "rime.rank-collapse.bundle.v1",
        "semantic_run_id": semantic_run_id,
        "execution_id": execution_id,
        "source_digest": sha256_bytes(canonical_json_bytes(source)),
        "policy_digest": sha256_bytes(canonical_json_bytes(policies)),
        "object": {
            "schema_id": "rime.rank-collapse.object.v1",
            "object_id": f"rank-collapse:{source['source_id']}",
            "source_ref": f"source:{source['source_id']}",
            "state_count": len(states),
            "alphabet_labels": alphabet,
            "semantics": "exact image subsets of positive deterministic words",
        },
        "image_layers": image_layers,
        "layer_semantics": "shortest first-hit distance from the full state image",
        "findings": first_hits,
        "claim_boundary": "Image-rank first-hit depth is not route depth, sector-pair word depth, or Lie/Hall depth.",
    }


class RankCollapsePlugin:
    plugin_id = PLUGIN_ID
    plugin_version = PLUGIN_VERSION
    carrier_kind = "rank_collapse"
    contract_version = "1.0"
    execution_mode = "python_in_process"
    implementation_language = "python"
    semantic_environment = {
        "algorithm_mode": "exhaustive_reachable_subset_bfs",
        "arithmetic_backend": "exact_finite_transformations",
        "dependency_lock_digest": None,
        "feature_flags": [],
    }

    def compute(self, request: dict[str, Any]) -> dict[str, Any]:
        return compute_rank_collapse(
            request["source"],
            semantic_run_id=request["semantic_run_id"],
            execution_id=request["execution_id"],
            policies=request["policies"],
            created_at=request["created_at"],
        )
