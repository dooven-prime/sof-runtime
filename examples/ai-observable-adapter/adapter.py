"""Black-box AI observable ExpertAdapter.

Only provider responses at the declared API boundary are observed. The adapter
does not inspect or infer weights, activations, routing, latent mechanisms,
causal effects, or operational authority.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from sof_runtime.contracts import validate_contract
from sof_runtime.paths import AI_OBSERVABLE_CONTRACT_ROOT


TASKS = (
    {"id": "format-json", "class": "format", "prompt": "Return only JSON with one key named result and value four.", "expected": "4"},
    {"id": "semantic-grounded", "class": "semantic", "prompt": "Context: Project Atlas has one deadline: Tuesday. What is the deadline?", "expected": "tuesday"},
    {"id": "behavior-instruction", "class": "behavior", "prompt": "Reply with exactly TOKEN_OK and no other text.", "expected": "TOKEN_OK"},
)
PROTOCOLS = ("bare", "constrained")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def _fixture_response(behavior: str, task: dict[str, str], protocol: str) -> str:
    if task["id"] == "format-json":
        if behavior == "format-fragile" and protocol == "bare":
            return "The result is 4."
        return '{"result":"4"}'
    if task["id"] == "semantic-grounded":
        if behavior == "semantic-fragile" and protocol == "bare":
            return "Wednesday"
        return "Tuesday"
    if behavior == "format-fragile" and protocol == "bare":
        return "TOKEN_OK with explanation"
    return "TOKEN_OK"


def _api_response(source: dict[str, Any], task: dict[str, str], protocol: str) -> str:
    if source.get("endpoint") != DEEPSEEK_ENDPOINT:
        raise ValueError("live example endpoint is not the pinned DeepSeek endpoint")
    key = os.environ.get(source["credential_env"])
    if not key:
        raise ValueError(f"required credential environment variable is unset: {source['credential_env']}")
    system = (
        "Follow the requested output contract exactly. Do not add unsupported facts."
        if protocol == "constrained"
        else "Answer the user request."
    )
    body = {
        "model": source["model_id"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": task["prompt"]},
        ],
        "temperature": 0,
        "max_tokens": 80,
    }
    request = urllib.request.Request(
        DEEPSEEK_ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        opener = urllib.request.build_opener(_NoRedirectHandler())
        with opener.open(request, timeout=float(source.get("timeout_seconds", 30))) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload["choices"][0]["message"].get("content") or "").strip()
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError) as error:
        raise ValueError(f"provider request failed: {type(error).__name__}") from error


def _score(task: dict[str, str], response: str) -> dict[str, bool | None]:
    parsed = None
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        pass
    normalized = re.sub(r"\s+", " ", response.strip()).casefold()
    format_valid = isinstance(parsed, dict) and set(parsed) == {"result"} and str(parsed["result"]) == "4"
    semantic_exact = normalized == task["expected"]
    behavior_exact = response.strip() == "TOKEN_OK"
    return {
        "format.json_contract": format_valid if task["class"] == "format" else None,
        "semantic.exact_answer": semantic_exact if task["class"] == "semantic" else None,
        "behavior.exact_instruction": behavior_exact if task["class"] == "behavior" else None,
    }


def _summary(values: list[bool | None]) -> dict[str, int | float | None]:
    retained = [value for value in values if value is not None]
    success_count = sum(retained)
    applicable_count = len(retained)
    return {
        "success_count": success_count,
        "applicable_count": applicable_count,
        "rate_percent": (
            100.0 * success_count / applicable_count if applicable_count else None
        ),
    }


class AIObservableAdapter:
    def __init__(self) -> None:
        self._last_evidence: dict[str, Any] | None = None

    def describe(self) -> dict[str, Any]:
        return {
            "declaration_version": "1.0",
            "adapter_id": "example.ai-observable-adapter",
            "adapter_version": "1.0",
            "domain_id": "black-box-ai-observable-evaluation",
            "native_objects": ["model API identity", "prompt protocol", "response envelope"],
            "supported_carriers": ["diagnostic_analogue"],
            "supported_observables": ["format", "semantic", "behavior", "repair_probe_result"],
            "sectorization_origin": "task and prompt-protocol probe descriptors; not projectors",
            "capabilities": ["source-addressed black-box probe evaluation"],
            "unsupported_capabilities": ["strict sectorization", "operator carrier", "word or Lie/Hall depth", "internal mechanism", "action selection", "authorization", "execution", "outcome", "causal effect"],
            "parameterization": {"tasks": [item["id"] for item in TASKS], "protocols": list(PROTOCOLS)},
            "normalization_threshold_requirements": {"rates": "percentage over applicable deterministic probes", "missing": "null-not-zero"},
            "evidence_requirements": ["model/configuration identity", "probe protocol", "normalized probe results", "adapter implementation"],
        }

    def inspect_source(self, source: dict[str, Any]) -> dict[str, Any]:
        validate_contract(
            source,
            AI_OBSERVABLE_CONTRACT_ROOT / "source.schema.json",
            label="AI observable source",
        )
        required = {"source_id", "mode", "provider", "model_id", "configuration_id"}
        if required - set(source):
            raise ValueError("AI observable source lacks required identity fields")
        if source["mode"] not in {"fixture", "api"}:
            raise ValueError("AI observable mode must be fixture or api")
        if source["mode"] == "api" and source.get("credential_env") != "DeepSeek_Service_Key":
            raise ValueError("live example requires the declared DeepSeek credential variable")
        if source["mode"] == "api" and source.get("endpoint") != DEEPSEEK_ENDPOINT:
            raise ValueError("live example requires the pinned DeepSeek endpoint")
        return {
            "status": "PASS",
            "validator_id": "example.ai-observable-source-validator",
            "validator_version": "1.0",
            "checks": [
                "model/configuration identity",
                "closed probe protocol",
                "pinned live endpoint with redirects disabled",
                "credential name only; secret not retained",
            ],
        }

    def realize(self, source: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        self.inspect_source(source)
        records = []
        for task in TASKS:
            for protocol in PROTOCOLS:
                response = (
                    _fixture_response(source["fixture_behavior"], task, protocol)
                    if source["mode"] == "fixture"
                    else _api_response(source, task, protocol)
                )
                records.append({"task": task["id"], "protocol": protocol, "scores": _score(task, response)})
        base_keys = (
            "format.json_contract",
            "semantic.exact_answer",
            "behavior.exact_instruction",
        )
        statistics = {
            key: _summary(
                [
                    item["scores"][key]
                    for item in records
                    if item["protocol"] == "bare"
                ]
            )
            for key in base_keys
        }
        for key in base_keys:
            before = [item["scores"][key] for item in records if item["protocol"] == "bare"]
            after = [item["scores"][key] for item in records if item["protocol"] == "constrained"]
            applicable = [(left, right) for left, right in zip(before, after, strict=True) if left is not None and right is not None]
            statistics[f"repair_probe_result.{key.split('.', 1)[1]}"] = _summary(
                [(not left) and right for left, right in applicable]
            )
        values = {
            key: summary["rate_percent"] for key, summary in statistics.items()
        }
        self._last_evidence = {
            "status": "PASS",
            "evidence_version": "1.0",
            "method": "closed task/protocol probe scoring",
            "probe_count": len(records),
            "coordinate_statistics": statistics,
            "raw_response_retention": False,
            "claim_boundary": "API-level Computational Observation only",
        }
        return {
            "candidate_version": "1.0",
            "record_kind": "diagnostic_analogue",
            "source_id": request["source_id"],
            "model_identity": {"provider": source["provider"], "model_id": source["model_id"], "configuration_id": source["configuration_id"]},
            "analogue_mapping": "Tasks and prompt protocols index black-box probes; they are not strict sectors, operators, or hidden mechanisms.",
            "observable_descriptor": {
                "format": ["json_contract"],
                "semantic": ["exact_answer"],
                "behavior": ["exact_instruction"],
                "repair": ["repair_probe_result.json_contract", "repair_probe_result.exact_answer", "repair_probe_result.exact_instruction"]
            },
            "observable_values": values,
            "coordinate_statistics": statistics,
            "probe_protocol": {"tasks": [item["id"] for item in TASKS], "protocols": list(PROTOCOLS), "scoring_version": "1.0"},
            "raw_response_retention": False,
            "claim": {
                "statement": "The declared model/configuration produced the recorded bounded black-box probe results.",
                "scope": "Three task-scoped probes under bare and constrained prompt protocols.",
                "negative_boundary": "The observation does not establish internal mechanism, global model quality, defect, action suitability, successful repair, outcome, or causal effect."
            },
            "negative_boundary": [
                "The report is a diagnostic analogue and does not instantiate strict SOF objects or theorems.",
                "The observable family is task-, protocol-, evaluator-, provider-, and model-version-relative.",
                "repair_probe_result denotes only a changed probe result under a declared prompt protocol.",
                "No candidate action, recommendation, selection, authorization, or execution is produced.",
                "No successful operational outcome or causal effect is observed or claimed.",
                "No access to or claim about weights, activations, routing, latent state, or internal mechanism is made."
            ]
        }

    def evidence(self) -> dict[str, Any]:
        if self._last_evidence is None:
            raise ValueError("realize must run before evidence")
        return self._last_evidence


ADAPTER = AIObservableAdapter()
