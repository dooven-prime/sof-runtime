from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from sof_runtime.artifacts import sha256_file
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.paths import COMPILER_CONTRACT_ROOT, RUNTIME_CONTRACT_ROOT


STATUS_MATRIX = {
    "DECLARED": {None, "Research Program"},
    "ESTABLISHED": {"Theorem"},
    "CERTIFIED": {"Computational Certificate"},
    "OBSERVED": {"Computational Observation"},
    "UNREACHED_AT_CUTOFF": {
        "Computational Certificate",
        "Computational Observation",
    },
    "NOT_APPLICABLE": {None},
    "NOT_DECLARED": {None},
}

OBSERVATION_ARTIFACT_ROLES = {
    "source-input",
    "adapter-output",
    "validator-output",
    "source-data",
    "log",
}


def _indexed(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item["id"]
        if item_id in result:
            raise ContractError(f"{label}: duplicate ID {item_id}")
        result[item_id] = item
    return result


def _require_refs(
    owner: str,
    refs: list[str],
    available: dict[str, Any],
    collection: str,
) -> None:
    missing = sorted(set(refs) - set(available))
    if missing:
        raise ContractError(f"{owner}: missing {collection} refs: {', '.join(missing)}")


def validate_compiler_inputs(
    manifest: dict[str, Any],
    ir: dict[str, Any],
    profile: dict[str, Any],
    rule_registry: dict[str, Any],
    *,
    repository_root: str | Path | None = None,
    verify_artifacts: bool = False,
) -> None:
    validate_contract(
        manifest,
        COMPILER_CONTRACT_ROOT / "capability-manifest.schema.json",
        label="Capability Manifest",
    )
    validate_contract(
        ir,
        COMPILER_CONTRACT_ROOT / "typed-sof-ir.schema.json",
        label="Typed SOF IR",
    )
    validate_contract(
        profile,
        COMPILER_CONTRACT_ROOT / "report-profile.schema.json",
        label="Report Profile",
    )
    if rule_registry.get("rule_registry_version") != "1.0":
        raise ContractError("unsupported rule registry version")
    if manifest["manifest_id"] != ir["manifest_ref"]["manifest_id"]:
        raise ContractError("IR manifest_ref does not match Capability Manifest")
    if manifest["record_kind"] != ir["record_kind"]:
        raise ContractError("IR record_kind does not match Capability Manifest")

    objects = _indexed(ir["objects"], "objects")
    carriers = _indexed(ir["carriers"], "carriers")
    conventions = _indexed(ir["semantic_conventions"], "semantic conventions")
    policies = _indexed(ir["run_policies"], "run policies")
    artifacts = _indexed(ir["artifacts"], "artifacts")
    certificates = _indexed(ir["certificates"], "certificates")
    findings = _indexed(ir["findings"], "findings")
    claims = _indexed(ir["claims"], "claims")
    derivations = _indexed(ir["derivations"], "derivations")
    capabilities = manifest["capabilities"]
    rules = {rule["id"]: rule for rule in rule_registry["rules"]}

    _require_refs("manifest_ref", [ir["manifest_ref"]["artifact_id"]], artifacts, "artifact")
    _require_refs("source", ir["source"]["artifact_ids"], artifacts, "artifact")
    manifest_artifact = artifacts[ir["manifest_ref"]["artifact_id"]]
    if manifest_artifact["role"] != "manifest":
        raise ContractError("IR manifest_ref must identify a manifest artifact")
    if ir["manifest_ref"]["digest"] != manifest_artifact["digest"]:
        raise ContractError("IR manifest_ref digest does not match its artifact")

    for carrier in carriers.values():
        if carrier["capability_id"] not in capabilities:
            raise ContractError(f"carrier {carrier['id']}: unknown capability")
        _require_refs(carrier["id"], carrier["object_ids"], objects, "object")
        _require_refs(
            carrier["id"],
            carrier["semantic_convention_ids"],
            conventions,
            "semantic convention",
        )
    for obj in objects.values():
        if "carrier_id" in obj:
            _require_refs(obj["id"], [obj["carrier_id"]], carriers, "carrier")
        _require_refs(
            obj["id"], obj["provenance_artifact_ids"], artifacts, "artifact"
        )
    for certificate in certificates.values():
        _require_refs(
            certificate["id"], certificate["artifact_ids"], artifacts, "artifact"
        )
    for finding in findings.values():
        if finding["carrier_id"] is not None:
            _require_refs(finding["id"], [finding["carrier_id"]], carriers, "carrier")
        _require_refs(finding["id"], finding["subject_object_ids"], objects, "object")
        _require_refs(
            finding["id"], finding["semantic_convention_ids"], conventions, "semantic convention"
        )
        _require_refs(finding["id"], finding["run_policy_ids"], policies, "run policy")
        _require_refs(finding["id"], finding["certificate_ids"], certificates, "certificate")
        _require_refs(finding["id"], finding["artifact_ids"], artifacts, "artifact")
    for claim in claims.values():
        if claim["claim_status"] not in STATUS_MATRIX[claim["result_state"]]:
            raise ContractError(
                f"claim {claim['id']}: illegal result_state/claim_status pairing"
            )
        unknown_capabilities = sorted(set(claim["capability_ids"]) - set(capabilities))
        if unknown_capabilities:
            raise ContractError(f"claim {claim['id']}: unknown capabilities {unknown_capabilities}")
        _require_refs(claim["id"], claim["carrier_ids"], carriers, "carrier")
        _require_refs(claim["id"], claim["object_ids"], objects, "object")
        _require_refs(claim["id"], claim["finding_ids"], findings, "finding")
        _require_refs(
            claim["id"], claim["semantic_convention_ids"], conventions, "semantic convention"
        )
        _require_refs(claim["id"], claim["run_policy_ids"], policies, "run policy")
        _require_refs(claim["id"], claim["certificate_ids"], certificates, "certificate")
        _require_refs(claim["id"], claim["artifact_ids"], artifacts, "artifact")
    for derivation in derivations.values():
        _require_refs(
            derivation["id"], derivation["source_claim_ids"], claims, "source claim"
        )
        _require_refs(
            derivation["id"], [derivation["target_claim_id"]], claims, "target claim"
        )
        if derivation["rule_id"] not in rules:
            raise ContractError(f"derivation {derivation['id']}: unknown rule")

    convention_kinds = {item["kind"] for item in conventions.values()}
    policy_kinds = {item["kind"] for item in policies.values()}
    for kind, requirement in manifest["semantic_convention_requirements"].items():
        if requirement == "required" and kind not in convention_kinds:
            raise ContractError(f"required semantic convention missing: {kind}")
    for kind, requirement in manifest["run_policy_requirements"].items():
        if requirement == "required" and kind not in policy_kinds:
            raise ContractError(f"required run policy missing: {kind}")

    if verify_artifacts:
        if repository_root is None:
            raise ValueError("repository_root is required when verifying artifacts")
        root = Path(repository_root).resolve()
        for artifact in artifacts.values():
            path = (root / artifact["uri"]).resolve()
            try:
                path.relative_to(root)
            except ValueError as error:
                raise ContractError(f"artifact {artifact['id']} escapes repository") from error
            if not path.is_file():
                raise ContractError(f"artifact {artifact['id']} is missing: {path}")
            if artifact["digest"]["algorithm"] != "sha256":
                raise ContractError("reference runtime verifies sha256 artifacts only")
            if sha256_file(path) != artifact["digest"]["value"]:
                raise ContractError(f"artifact {artifact['id']} digest mismatch")
        manifest_path = root / manifest_artifact["uri"]
        if load_json(manifest_path) != manifest:
            raise ContractError("manifest artifact content does not match compiler input")


def _expression_errors(values: set[str], expression: dict[str, Any]) -> list[str]:
    errors = []
    missing = sorted(set(expression["all_of"]) - values)
    if missing:
        errors.append("missing all_of: " + ", ".join(missing))
    if expression["any_of"] and not values.intersection(expression["any_of"]):
        errors.append("no any_of member present: " + ", ".join(expression["any_of"]))
    prohibited = sorted(values.intersection(expression["none_of"]))
    if prohibited:
        errors.append("none_of member present: " + ", ".join(prohibited))
    return errors


def _claim_requirement_errors(
    claim: dict[str, Any],
    module: dict[str, Any],
    capabilities: dict[str, Any],
    objects: dict[str, Any],
    conventions: dict[str, Any],
    policies: dict[str, Any],
) -> list[str]:
    values = (
        (
            "capability",
            {
                item
                for item in claim["capability_ids"]
                if capabilities[item]["availability"] == "DECLARED"
            },
            module["capability_requirements"],
        ),
        (
            "object",
            {objects[item]["kind"] for item in claim["object_ids"]},
            module["object_kind_requirements"],
        ),
        (
            "semantic convention",
            {conventions[item]["kind"] for item in claim["semantic_convention_ids"]},
            module["semantic_convention_requirements"],
        ),
        (
            "run policy",
            {policies[item]["kind"] for item in claim["run_policy_ids"]},
            module["run_policy_requirements"],
        ),
    )
    return [
        f"{label}: {error}"
        for label, present, expression in values
        for error in _expression_errors(present, expression)
    ]


def _derivation_errors(
    claim: dict[str, Any],
    derivations_by_target: dict[str, list[dict[str, Any]]],
    rules: dict[str, dict[str, Any]],
) -> list[str]:
    errors = []
    for derivation in derivations_by_target.get(claim["id"], []):
        rule = rules.get(derivation["rule_id"])
        if rule is None:
            errors.append(f"unknown rule {derivation['rule_id']}")
            continue
        if derivation["derivation_state"] != "VALID":
            errors.append(f"derivation {derivation['id']} is {derivation['derivation_state']}")
        if derivation["rule_status"] == "Research Program":
            errors.append(f"derivation {derivation['id']} uses an open rule")
        unchecked = [
            item["condition_id"]
            for item in derivation["condition_checks"]
            if item["status"] != "SATISFIED"
        ]
        if unchecked:
            errors.append(
                f"derivation {derivation['id']} has unsatisfied conditions {', '.join(unchecked)}"
            )
    return errors


def _evidence_errors(
    claim: dict[str, Any],
    requirement: str,
    artifacts: dict[str, Any],
    certificates: dict[str, Any],
) -> list[str]:
    if requirement in {"NO_EVIDENCE_REQUIRED", "NO_CLAIM"}:
        return []
    if requirement == "PROOF_REFERENCE" and any(
        artifacts[item]["role"] == "proof-reference" for item in claim["artifact_ids"]
    ):
        return []
    if requirement == "PASS_CERTIFICATE":
        referenced = [certificates[item] for item in claim["certificate_ids"]]
        if referenced and all(item["status"] == "PASS" for item in referenced):
            return []
    if requirement == "SOURCE_ARTIFACT" and any(
        artifacts[item]["role"] in OBSERVATION_ARTIFACT_ROLES
        for item in claim["artifact_ids"]
    ):
        return []
    return [f"claim {claim['id']} does not satisfy {requirement}"]


def compile_v1(
    manifest: dict[str, Any],
    ir: dict[str, Any],
    profile: dict[str, Any],
    rule_registry: dict[str, Any],
) -> dict[str, Any]:
    if manifest["record_kind"] not in profile["applies_to"]:
        raise ContractError("Report Profile does not apply to this record_kind")

    capabilities = manifest["capabilities"]
    declared_capabilities = {
        key for key, value in capabilities.items() if value["availability"] == "DECLARED"
    }
    objects = {item["id"]: item for item in ir["objects"]}
    carriers = {item["id"]: item for item in ir["carriers"]}
    conventions = {item["id"]: item for item in ir["semantic_conventions"]}
    policies = {item["id"]: item for item in ir["run_policies"]}
    artifacts = {item["id"]: item for item in ir["artifacts"]}
    certificates = {item["id"]: item for item in ir["certificates"]}
    rules = {item["id"]: item for item in rule_registry["rules"]}
    derivations_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for derivation in ir["derivations"]:
        derivations_by_target[derivation["target_claim_id"]].append(derivation)

    global_values = (
        ("capability", declared_capabilities, "capability_requirements", "unsatisfied_capability_expression"),
        ("object", {item["kind"] for item in objects.values()}, "object_kind_requirements", "unsatisfied_object_expression"),
        ("semantic convention", {item["kind"] for item in conventions.values()}, "semantic_convention_requirements", "unsatisfied_policy_expression"),
        ("run policy", {item["kind"] for item in policies.values()}, "run_policy_requirements", "unsatisfied_policy_expression"),
    )
    items: list[dict[str, Any]] = []
    fatal_errors: list[str] = []

    for module in profile["modules"]:
        blocked = False
        for label, present, requirement_field, degradation_field in global_values:
            failures = _expression_errors(present, module[requirement_field])
            if not failures:
                continue
            action = profile["degradation_policy"][degradation_field]
            items.append(
                {
                    "item_kind": "degradation",
                    "module_id": module["id"],
                    "action": action,
                    "reason_kind": f"unsatisfied_{requirement_field}",
                    "details": failures,
                }
            )
            if action == "fail_profile":
                fatal_errors.append(f"module {module['id']}: unsatisfied {label}")
            blocked = True
        if blocked:
            continue

        eligible: list[dict[str, Any]] = []
        for claim in ir["claims"]:
            claim_carrier_kinds = {
                carriers[item]["kind"] for item in claim["carrier_ids"]
            }
            if not claim_carrier_kinds.intersection(module["carrier_kinds"]):
                continue
            if claim["result_state"] not in module["accepted_result_states"]:
                continue
            if claim["claim_status"] is not None and claim["claim_status"] not in module["accepted_claim_statuses"]:
                continue
            failures = _claim_requirement_errors(
                claim, module, capabilities, objects, conventions, policies
            )
            if failures:
                items.append(
                    {
                        "item_kind": "degradation",
                        "module_id": module["id"],
                        "action": "omit_claim",
                        "reason_kind": "claim_ineligible",
                        "source_ir_id": claim["id"],
                        "details": failures,
                    }
                )
                continue
            failures = _derivation_errors(claim, derivations_by_target, rules)
            if failures:
                items.append(
                    {
                        "item_kind": "degradation",
                        "module_id": module["id"],
                        "action": "omit_claim",
                        "reason_kind": "derivation_invalid",
                        "source_ir_id": claim["id"],
                        "details": failures,
                    }
                )
                continue
            eligible.append(claim)

        if not eligible:
            fatal_errors.append(f"profile module {module['id']}: no eligible IR claims")
            continue
        for claim in eligible:
            evidence_key = claim["claim_status"] if claim["claim_status"] is not None else "null"
            requirement = module["evidence_requirements"][evidence_key]
            claim_errors = _evidence_errors(claim, requirement, artifacts, certificates)
            forbidden = set(module["forbidden_promotion_ids"])
            for derivation in derivations_by_target.get(claim["id"], []):
                rule = rules.get(derivation["rule_id"])
                if rule and rule["promotion_id"] in forbidden:
                    claim_errors.append(
                        f"target claim {claim['id']} uses forbidden promotion {rule['promotion_id']}"
                    )
            if claim_errors:
                fatal_errors.extend(
                    f"profile module {module['id']}: {error}" for error in claim_errors
                )
                continue
            items.append(
                {
                    "item_kind": "claim",
                    "module_id": module["id"],
                    "claim_id": claim["id"],
                    "source_ir_kind": "claim",
                    "source_ir_id": claim["id"],
                    "claim_status": claim["claim_status"],
                    "result_state": claim["result_state"],
                    "carrier_ids": claim["carrier_ids"],
                    "derivation_ids": [
                        item["id"] for item in derivations_by_target.get(claim["id"], [])
                    ],
                }
            )
        if not module["forbidden_promotion_ids"]:
            fatal_errors.append(
                f"profile module {module['id']}: forbidden_promotion_ids must be explicit"
            )

    if fatal_errors:
        raise ContractError("Compile_v1 rejected inputs: " + "; ".join(fatal_errors))
    output = {
        "compiler_output_version": "1.0",
        "compiler_id": "sofcompiler.compile_v1",
        "manifest_id": manifest["manifest_id"],
        "ir_record_id": ir["record_id"],
        "profile_id": profile["profile_id"],
        "item_type": "ClaimItem_v1 | DegradationItem_v1",
        "items": items,
    }
    validate_contract(
        output,
        RUNTIME_CONTRACT_ROOT / "compiler-output.schema.json",
        label="Compiler Output",
    )
    return output


def compile_documents(
    manifest: dict[str, Any],
    ir: dict[str, Any],
    profile: dict[str, Any],
    *,
    rule_registry: dict[str, Any] | None = None,
    repository_root: str | Path | None = None,
    verify_artifacts: bool = False,
) -> dict[str, Any]:
    rules = rule_registry or load_json(COMPILER_CONTRACT_ROOT / "rule-registry.json")
    validate_compiler_inputs(
        manifest,
        ir,
        profile,
        rules,
        repository_root=repository_root,
        verify_artifacts=verify_artifacts,
    )
    return compile_v1(manifest, ir, profile, rules)
