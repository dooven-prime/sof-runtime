from __future__ import annotations

from collections import deque
from typing import Any

from sof_runtime.adapters.automata import indexed_transition, normalize_source
from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes
from sof_runtime.carriers.rank_collapse import PLUGIN_ID, PLUGIN_VERSION, SUPPORTED_POLICY
from sof_runtime.run_identity import verify_semantic_run_id


VALIDATOR_ID = "sof-runtime.rank-collapse-validator"
VALIDATOR_VERSION = "0.1.0"


def _apply_word(
    subset: set[int],
    word: list[str],
    alphabet: list[str],
    transition: tuple[tuple[int, ...], ...],
) -> set[int]:
    label_to_index = {label: index for index, label in enumerate(alphabet)}
    current = set(subset)
    for label in word:
        letter = transition[label_to_index[label]]
        current = {letter[state] for state in current}
    return current


def validate_rank_collapse(
    source: dict[str, Any],
    bundle: dict[str, Any],
    *,
    request: dict[str, Any] | None = None,
    input_source: str = "in_memory_values",
    validator_independence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalize_source(source)
    transition = indexed_transition(source)
    full = frozenset(range(len(source["states"])))
    distances = {full: 0}
    queue = deque([full])
    while queue:
        current = queue.popleft()
        for letter in transition:
            nxt = frozenset(letter[state] for state in current)
            if nxt not in distances:
                distances[nxt] = distances[current] + 1
                queue.append(nxt)

    expected: dict[int, int | None] = {}
    for threshold in range(1, len(source["states"]) + 1):
        hits = [depth for subset, depth in distances.items() if len(subset) <= threshold]
        expected[threshold] = min(hits) if hits else None

    errors: list[str] = []
    policy_digest = sha256_bytes(canonical_json_bytes(SUPPORTED_POLICY))
    if bundle.get("source_digest") != sha256_bytes(canonical_json_bytes(source)):
        errors.append("source digest mismatch")
    if bundle.get("policy_digest") != policy_digest:
        errors.append("policy digest mismatch")
    if request is not None:
        if request.get("source") != source:
            errors.append("request source differs from canonical source artifact")
        if not verify_semantic_run_id(request):
            errors.append("semantic run identity mismatch")
        if request.get("policies") != SUPPORTED_POLICY:
            errors.append("request policy is unsupported by rank-collapse v1")
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
        "schema_id": "rime.rank-collapse.object.v1",
        "object_id": f"rank-collapse:{source['source_id']}",
        "source_ref": f"source:{source['source_id']}",
        "state_count": len(source["states"]),
        "alphabet_labels": source["alphabet"],
        "semantics": "exact image subsets of positive deterministic words",
    }
    if bundle.get("object") != expected_object:
        errors.append("rank-collapse object mismatch")
    if bundle.get("object", {}).get("state_count") != len(source["states"]):
        errors.append("state count mismatch")

    expected_layers = []
    for depth in range(max(distances.values()) + 1):
        layer = sorted(subset for subset, first_hit in distances.items() if first_hit == depth)
        expected_layers.append(
            {
                "depth": depth,
                "images": [
                    [source["states"][index] for index in subset] for subset in layer
                ],
                "minimum_rank": min(len(subset) for subset in layer),
            }
        )
    if bundle.get("layer_semantics") != "shortest first-hit distance from the full state image":
        errors.append("image-layer semantics mismatch")
    if bundle.get("image_layers") != expected_layers:
        errors.append("shortest first-hit image layers mismatch")

    findings = bundle.get("findings", [])
    thresholds = [item.get("payload", {}).get("rank_threshold") for item in findings]
    expected_thresholds = list(range(1, len(source["states"]) + 1))
    if sorted(value for value in thresholds if isinstance(value, int)) != expected_thresholds:
        errors.append("rank-threshold finding census is incomplete or duplicated")

    for item in findings:
        payload = item["payload"]
        threshold = payload["rank_threshold"]
        if threshold not in expected:
            errors.append(f"rank threshold {threshold}: outside source rank range")
            continue
        depth = expected[threshold]
        if payload["depth"] != depth:
            errors.append(f"rank threshold {threshold}: first-hit depth mismatch")
            continue
        if payload.get("reachable_image_subset_count") != len(distances):
            errors.append(f"rank threshold {threshold}: closure census mismatch")
        if payload.get("closure_exhausted") is not True:
            errors.append(f"rank threshold {threshold}: closure is not marked exhausted")

        envelope = item["envelope"]
        expected_payload_id = f"payload.rank-threshold-{threshold}"
        if envelope.get("value_ref") != expected_payload_id or payload.get("payload_id") != expected_payload_id:
            errors.append(f"rank threshold {threshold}: payload reference mismatch")
        if envelope.get("result_state") != "OBSERVED" or envelope.get("claim_status") != "Computational Observation":
            errors.append(f"rank threshold {threshold}: raw plugin output claims certificate status")
        if envelope.get("evidence_refs"):
            errors.append(f"rank threshold {threshold}: raw plugin output predeclares evidence")
        if envelope.get("source_ref") != f"source:{source['source_id']}":
            errors.append(f"rank threshold {threshold}: source reference mismatch")
        if envelope.get("carrier_ref") != "extension:rank-collapse:v1":
            errors.append(f"rank threshold {threshold}: carrier reference mismatch")
        provenance = envelope.get("provenance", {})
        if provenance.get("semantic_run_id") != bundle.get("semantic_run_id"):
            errors.append(f"rank threshold {threshold}: semantic run provenance mismatch")
        if provenance.get("execution_id") != bundle.get("execution_id"):
            errors.append(f"rank threshold {threshold}: execution provenance mismatch")
        if envelope.get("provenance", {}).get("producer") != "org.rime.rank-collapse":
            errors.append(f"rank threshold {threshold}: producer identity mismatch")
        if envelope.get("provenance", {}).get("producer_version") != "0.1.0":
            errors.append(f"rank threshold {threshold}: producer version mismatch")

        if depth is None:
            if payload["kind"] != "rank_threshold_unreachable":
                errors.append(f"rank threshold {threshold}: unreachable kind mismatch")
            if payload.get("shortest_word") is not None or payload.get("lower_depths_verified") is not None:
                errors.append(f"rank threshold {threshold}: unreachable finding carries a witness")
            continue
        if payload["kind"] != "rank_threshold_first_hit":
            errors.append(f"rank threshold {threshold}: first-hit kind mismatch")
        word = payload["shortest_word"]
        if not isinstance(word, list) or len(word) != depth:
            errors.append(f"rank threshold {threshold}: witness length does not equal first-hit depth")
            continue
        try:
            image = _apply_word(
                set(range(len(source["states"]))),
                word,
                source["alphabet"],
                transition,
            )
        except KeyError:
            errors.append(f"rank threshold {threshold}: witness uses an unknown letter")
            continue
        if len(image) > threshold:
            errors.append(f"rank threshold {threshold}: witness does not hit threshold")
        lower_hits = [
            observed
            for subset, observed in distances.items()
            if len(subset) <= threshold and observed < depth
        ]
        if lower_hits:
            errors.append(f"rank threshold {threshold}: lower non-hit check failed")
        if payload["lower_depths_verified"] != max(depth - 1, 0):
            errors.append(f"rank threshold {threshold}: lower-depth certificate mismatch")

    status = "PASS" if not errors else "FAIL"
    return {
        "schema_id": "rime.rank-collapse.certificate.v1",
        "certificate_id": f"certificate:{source['source_id']}:rank-collapse:{bundle.get('execution_id', 'unknown')}",
        "semantic_run_id": bundle.get("semantic_run_id", "semrun:sha256:" + "0" * 64),
        "execution_id": bundle.get("execution_id", "exec:unknown"),
        "validator_id": VALIDATOR_ID,
        "validator_version": VALIDATOR_VERSION,
        "validator_independence": validator_independence
        or {
            "implementation_relation": "separate_implementation",
            "language_relation": "same_language",
            "runtime_relation": "same_process",
            "input_source": input_source,
            "producer_cache_used": False,
        },
        "status": status,
        "scope": "Exact reachable subset orbit and all rank-threshold first hits.",
        "input_digests": {
            "source": sha256_bytes(canonical_json_bytes(source)),
            "bundle": sha256_bytes(canonical_json_bytes(bundle)),
            "policy": policy_digest,
            "request": (
                sha256_bytes(canonical_json_bytes(request))
                if request is not None
                else None
            ),
        },
        "checks": [
            "source digest",
            "reachable subset closure",
            "shortest first-hit image layers",
            "raw finding envelope boundary",
            "first-hit depths",
            "reset-word witnesses",
            "lower-depth non-hits",
        ],
        "recomputed": {
            "reachable_image_subset_count": len(distances),
            "first_hit_depth_by_rank_threshold": {
                str(threshold): depth for threshold, depth in expected.items()
            },
            "errors": errors,
        },
    }
