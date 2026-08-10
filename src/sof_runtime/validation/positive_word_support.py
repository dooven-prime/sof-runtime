from __future__ import annotations

from typing import Any

from sof_runtime.adapters.markov import normalize_source, support_adjacency
from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes
from sof_runtime.carriers.positive_word_support import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    SUPPORTED_POLICY,
)
from sof_runtime.run_identity import verify_semantic_run_id


VALIDATOR_ID = "sof-runtime.positive-word-support-validator"
VALIDATOR_VERSION = "0.1.0"


def _floyd_warshall_pairs(source: dict[str, Any]) -> list[dict[str, Any]]:
    adjacency = support_adjacency(source)
    states = source["states"]
    size = len(states)
    infinity = size + 1
    distance = [[infinity for _ in range(size)] for _ in range(size)]
    for left in range(size):
        distance[left][left] = 0
        for right, present in enumerate(adjacency[left]):
            if present:
                distance[left][right] = min(distance[left][right], 1)
    for middle in range(size):
        for left in range(size):
            for right in range(size):
                distance[left][right] = min(
                    distance[left][right],
                    distance[left][middle] + distance[middle][right],
                )
    return [
        {
            "source": states[left],
            "target": states[right],
            "first_positive_depth": (
                distance[left][right] if distance[left][right] < infinity else None
            ),
        }
        for left in range(size)
        for right in range(size)
        if left != right
    ]


def validate_positive_word_support(
    source: dict[str, Any],
    bundle: dict[str, Any],
    *,
    request: dict[str, Any],
    validator_independence: dict[str, Any],
) -> dict[str, Any]:
    normalize_source(source)
    errors: list[str] = []
    source_digest = sha256_bytes(canonical_json_bytes(source))
    policy_digest = sha256_bytes(canonical_json_bytes(SUPPORTED_POLICY))
    if bundle.get("source_digest") != source_digest:
        errors.append("source digest mismatch")
    if bundle.get("policy_digest") != policy_digest:
        errors.append("policy digest mismatch")
    if request.get("source") != source:
        errors.append("request source differs from canonical source artifact")
    if not verify_semantic_run_id(request):
        errors.append("semantic run identity mismatch")
    if request.get("policies") != SUPPORTED_POLICY:
        errors.append("request policy mismatch")
    if request.get("plugin") != {
        "plugin_id": PLUGIN_ID,
        "plugin_version": PLUGIN_VERSION,
    }:
        errors.append("request plugin identity mismatch")
    if bundle.get("semantic_run_id") != request.get("semantic_run_id"):
        errors.append("bundle semantic run identity mismatch")
    if bundle.get("execution_id") != request.get("execution_id"):
        errors.append("bundle execution identity mismatch")

    expected_object = {
        "schema_id": "rime.positive-word-support.object.v1",
        "object_id": f"positive-word-support:{source['source_id']}",
        "source_ref": f"source:{source['source_id']}",
        "state_count": len(source["states"]),
        "operator_label": "P",
        "pair_scope": "ordered_off_diagonal",
        "semantics": "first positive power with nonzero coordinate-sector support",
    }
    if bundle.get("object") != expected_object:
        errors.append("positive-word object mismatch")

    expected_pairs = _floyd_warshall_pairs(source)
    findings = bundle.get("findings", [])
    if len(findings) != 1:
        errors.append("positive-word finding census must contain exactly one item")
        payload: dict[str, Any] = {}
        envelope: dict[str, Any] = {}
    else:
        payload = findings[0].get("payload", {})
        envelope = findings[0].get("envelope", {})
    finite_depths = [
        item["first_positive_depth"]
        for item in expected_pairs
        if item["first_positive_depth"] is not None
    ]
    expected_summary = {
        "pairs": expected_pairs,
        "reachable_pair_count": len(finite_depths),
        "unreachable_pair_count": len(expected_pairs) - len(finite_depths),
        "maximum_first_hit_depth": max(finite_depths) if finite_depths else None,
    }
    for key, value in expected_summary.items():
        if payload.get(key) != value:
            errors.append(f"positive-word payload {key} mismatch")
    if payload.get("closure_exhausted") is not True:
        errors.append("positive-word closure is not marked exhausted")
    if envelope.get("result_state") != "OBSERVED":
        errors.append("raw positive-word finding is not OBSERVED")
    if envelope.get("claim_status") != "Computational Observation":
        errors.append("raw positive-word finding claims promoted evidence")
    if envelope.get("carrier_ref") != "extension:positive-word-support:v1":
        errors.append("positive-word carrier reference mismatch")
    provenance = envelope.get("provenance", {})
    if provenance.get("semantic_run_id") != bundle.get("semantic_run_id"):
        errors.append("positive-word semantic provenance mismatch")
    if provenance.get("execution_id") != bundle.get("execution_id"):
        errors.append("positive-word execution provenance mismatch")
    if provenance.get("producer") != PLUGIN_ID:
        errors.append("positive-word producer identity mismatch")
    if provenance.get("producer_version") != PLUGIN_VERSION:
        errors.append("positive-word producer version mismatch")

    return {
        "schema_id": "rime.positive-word-support.certificate.v1",
        "certificate_id": f"certificate:{source['source_id']}:positive-word-support:{bundle.get('execution_id', 'unknown')}",
        "semantic_run_id": bundle.get("semantic_run_id", "semrun:sha256:" + "0" * 64),
        "execution_id": bundle.get("execution_id", "exec:unknown"),
        "validator_id": VALIDATOR_ID,
        "validator_version": VALIDATOR_VERSION,
        "validator_independence": validator_independence,
        "status": "PASS" if not errors else "FAIL",
        "scope": "Exact ordered off-diagonal first-hit support depths for positive powers of one nonnegative operator.",
        "applicability": {
            "alphabet_scope": "single_letter",
            "coefficient_scope": "entrywise_nonnegative",
            "arithmetic": "exact_rational",
            "positivity_rule": "strict_numerator_gt_zero",
            "graph_equivalence": (
                "support_graph_path_iff_positive_matrix_power_entry"
            ),
            "excluded_regimes": [
                "signed matrices",
                "multiple operative letters or their linear combinations",
                "complex weights",
                "route-sum cancellation",
                "tolerance-relative near-zero tests",
            ],
        },
        "input_digests": {
            "source": source_digest,
            "bundle": sha256_bytes(canonical_json_bytes(bundle)),
            "policy": policy_digest,
            "request": sha256_bytes(canonical_json_bytes(request)),
        },
        "checks": [
            "source and policy digests",
            "runtime identities",
            "exact rational Markov admission",
            "single-letter nonnegative strict-positivity applicability",
            "Floyd-Warshall support closure",
            "ordered off-diagonal first-hit census",
            "raw finding evidence boundary",
        ],
        "recomputed": {
            "reachable_pair_count": len(finite_depths),
            "unreachable_pair_count": len(expected_pairs) - len(finite_depths),
            "maximum_first_hit_depth": max(finite_depths) if finite_depths else None,
            "errors": errors,
        },
    }
