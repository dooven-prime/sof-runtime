from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.artifacts.digest import sha256_file
from sof_runtime.compiler import compile_documents
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.paths import (
    PROJECT_ROOT,
    REPORTING_CONTRACT_ROOT,
    RUNTIME_CONTRACT_ROOT,
)


ASSEMBLY_SCHEMA = REPORTING_CONTRACT_ROOT / "assembly-profile.schema.json"
REPORT_SCHEMA = REPORTING_CONTRACT_ROOT / "sofrs.schema.json"
COMPILER_OUTPUT_SCHEMA = RUNTIME_CONTRACT_ROOT / "compiler-output.schema.json"


def _inside_root(path: str | Path, repository_root: str | Path) -> Path:
    root = Path(repository_root).resolve()
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ContractError(f"artifact path escapes repository root: {resolved}") from error
    return resolved


def artifact_reference(
    path: str | Path,
    *,
    repository_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    resolved = _inside_root(path, root)
    if not resolved.is_file():
        raise ContractError(f"artifact is missing: {resolved}")
    return {
        "uri": resolved.relative_to(root).as_posix(),
        "digest": {"algorithm": "sha256", "value": sha256_file(resolved)},
    }


def resolve_artifact_reference(
    reference: dict[str, Any],
    *,
    repository_root: str | Path = PROJECT_ROOT,
    verify_digest: bool = True,
) -> Path:
    root = Path(repository_root).resolve()
    path = _inside_root(root / reference["uri"], root)
    if not path.is_file():
        raise ContractError(f"referenced artifact is missing: {reference['uri']}")
    digest = reference.get("digest", {})
    if digest.get("algorithm") != "sha256":
        raise ContractError("the reference reporting runtime requires sha256 artifacts")
    if verify_digest and sha256_file(path) != digest.get("value"):
        raise ContractError(f"artifact digest mismatch: {reference['uri']}")
    return path


def _indexed(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item["id"]
        if item_id in result:
            raise ContractError(f"duplicate {label} id: {item_id}")
        result[item_id] = item
    return result


def _normative_items(
    compiler_output: dict[str, Any],
    ir: dict[str, Any],
    claim_classifications: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    ir_claims = _indexed(ir["claims"], "IR claim")
    carriers = _indexed(ir["carriers"], "carrier")
    claims: list[dict[str, Any]] = []
    degradations: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []

    for index, item in enumerate(compiler_output["items"]):
        source_id = f"compiler.item.{index:04d}"
        report_id = f"report.{item['item_kind']}-item.{index:04d}"
        bindings.append(
            {
                "compiler_output_item_id": source_id,
                "report_item_id": report_id,
                "item_kind": item["item_kind"],
                "rendering_status": "rendered",
            }
        )
        if item["item_kind"] == "claim":
            try:
                claim = ir_claims[item["claim_id"]]
            except KeyError as error:
                raise ContractError(
                    f"CompilerOutput claim is absent from IR: {item['claim_id']}"
                ) from error
            unknown_carriers = sorted(set(item["carrier_ids"]) - set(carriers))
            if unknown_carriers:
                raise ContractError(
                    "CompilerOutput claim references unknown carriers: "
                    + ", ".join(unknown_carriers)
                )
            try:
                classification = claim_classifications[item["claim_id"]]
            except KeyError as error:
                raise ContractError(
                    f"SOFRS presentation lacks classification for {item['claim_id']}"
                ) from error
            claims.append(
                {
                    "report_item_id": report_id,
                    "source_output_item_id": source_id,
                    "claim_id": item["claim_id"],
                    "statement": claim["statement"],
                    "result_state": item["result_state"],
                    "claim_status": item["claim_status"],
                    "claim_target": classification["claim_target"],
                    "certificate_class": classification["certificate_class"],
                    "classification_source": classification["classification_source"],
                    "external_basis_refs": deepcopy(
                        classification["external_basis_refs"]
                    ),
                    "external_constraint_ids": deepcopy(
                        classification["external_constraint_ids"]
                    ),
                    "carrier_kinds": sorted(
                        {carriers[carrier_id]["kind"] for carrier_id in item["carrier_ids"]}
                    ),
                    "scope": claim["scope"],
                    "negative_boundary": claim["negative_boundary"],
                }
            )
            continue

        degradation = {
            "report_item_id": report_id,
            "source_output_item_id": source_id,
            "module_id": item["module_id"],
            "action": item["action"],
            "reason_kind": item["reason_kind"],
            "details": deepcopy(item["details"]),
        }
        if "source_ir_id" in item:
            degradation["source_ir_id"] = item["source_ir_id"]
        degradations.append(degradation)

    return claims, degradations, bindings


def _module_summaries(
    compiler_output: dict[str, Any],
    ir: dict[str, Any],
    compiler_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = _indexed(ir["findings"], "finding")
    claims = _indexed(ir["claims"], "claim")
    output_by_module: dict[str, list[dict[str, Any]]] = {}
    for item in compiler_output["items"]:
        output_by_module.setdefault(item["module_id"], []).append(item)

    summaries: list[dict[str, Any]] = []
    for module in compiler_profile["modules"]:
        module_items = output_by_module.get(module["id"], [])
        claim_items = [item for item in module_items if item["item_kind"] == "claim"]
        if claim_items:
            claim_records = [claims[item["claim_id"]] for item in claim_items]
            finding_ids = sorted(
                {
                    finding_id
                    for claim in claim_records
                    for finding_id in claim["finding_ids"]
                    if finding_id in findings
                }
            )
            summaries.append(
                {
                    "module_id": module["id"],
                    "status": "ENABLED",
                    "carrier_kinds": module["carrier_kinds"],
                    "finding_ids": finding_ids,
                    "claim_ids": [item["claim_id"] for item in claim_items],
                    "output_sections": module["output_sections"],
                }
            )
            continue

        details = [
            detail
            for item in module_items
            if item["item_kind"] == "degradation"
            for detail in item["details"]
        ]
        summaries.append(
            {
                "module_id": module["id"],
                "status": "UNAVAILABLE",
                "carrier_kinds": module["carrier_kinds"],
                "finding_ids": [],
                "claim_ids": [],
                "output_sections": module["output_sections"],
                "reason": (
                    "; ".join(details)
                    if details
                    else "Paper X Compile_v1 emitted no eligible claim item."
                ),
            }
        )
    return summaries


def _alignment_metadata(
    manifest: dict[str, Any],
    ir: dict[str, Any],
    *,
    report_id: str,
    system: str,
    assembly_profile_id: str,
    compiler_profile_id: str,
    source_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    sector_capability = manifest["capabilities"]["sectorization"]
    if sector_capability["availability"] == "DECLARED":
        configuration = sector_capability["configuration"]
        sector_metadata = {
            "status": "PRESENT",
            "labels": configuration["labels"],
            "provenance": configuration["provenance"],
            "ranks_or_dimensions": [],
            "semantics": configuration["origin"],
        }
    else:
        sector_metadata = {
            "status": sector_capability["availability"],
            "labels": [],
            "provenance": None,
            "ranks_or_dimensions": [],
            "semantics": None,
        }

    alphabets = [item for item in ir["objects"] if item["kind"] == "labelled_alphabet"]
    if alphabets:
        labels = sorted(
            {
                label
                for alphabet in alphabets
                for label in alphabet.get("data", {}).get("labels", [])
            }
        )
        observable_metadata = {
            "status": "PRESENT",
            "labels": labels,
            "provenance": manifest["adapter"]["id"],
            "ranks_or_dimensions": [],
            "semantics": "labelled operative alphabet",
        }
    else:
        observable_metadata = {
            "status": "NOT_DECLARED",
            "labels": [],
            "provenance": None,
            "ranks_or_dimensions": [],
            "semantics": None,
        }

    return {
        "adapter": {
            "id": manifest["adapter"]["id"],
            "version": manifest["adapter"]["version"],
        },
        "compiler_profile_id": compiler_profile_id,
        "assembly_profile_id": assembly_profile_id,
        "sector_metadata": sector_metadata,
        "observable_metadata": observable_metadata,
        "carrier_kinds": sorted({item["kind"] for item in ir["carriers"]}),
        "semantic_conventions": [
            {"id": item["id"], "kind": item["kind"]}
            for item in ir["semantic_conventions"]
        ],
        "run_policies": [
            {"id": item["id"], "kind": item["kind"]}
            for item in ir["run_policies"]
        ],
        "comparison_keys": [
            f"report:{report_id}",
            f"system:{system.lower().replace(' ', '-')}",
            f"record-kind:{manifest['record_kind']}",
        ],
        "source_artifact_digests": deepcopy(source_artifacts),
    }


def assemble_report(
    manifest_path: str | Path,
    ir_path: str | Path,
    compiler_profile_path: str | Path,
    compiler_output_path: str | Path,
    assembly_profile_path: str | Path,
    *,
    assembly_implementation: dict[str, Any],
    presentation: dict[str, Any],
    repository_root: str | Path = PROJECT_ROOT,
    verify_artifacts: bool = True,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    paths = [
        _inside_root(path, root)
        for path in (
            manifest_path,
            ir_path,
            compiler_profile_path,
            compiler_output_path,
            assembly_profile_path,
        )
    ]
    manifest_path, ir_path, compiler_profile_path, compiler_output_path, assembly_profile_path = paths
    manifest = load_json(manifest_path)
    ir = load_json(ir_path)
    compiler_profile = load_json(compiler_profile_path)
    compiler_output = load_json(compiler_output_path)
    assembly_profile = load_json(assembly_profile_path)

    validate_contract(
        compiler_output,
        COMPILER_OUTPUT_SCHEMA,
        label="CompilerOutput",
    )
    validate_contract(
        assembly_profile,
        ASSEMBLY_SCHEMA,
        label="SOFRS Assembly Profile",
    )
    if assembly_profile["record_kind"] != manifest["record_kind"]:
        raise ContractError("Assembly Profile record_kind differs from Manifest")
    if assembly_profile["compiler_profile_id"] != compiler_profile["profile_id"]:
        raise ContractError("Assembly Profile binds a different Compiler Report Profile")

    recomputed = compile_documents(
        manifest,
        ir,
        compiler_profile,
        repository_root=root,
        verify_artifacts=verify_artifacts,
    )
    if compiler_output != recomputed:
        raise ContractError("bound CompilerOutput differs from Compile_v1 recomputation")

    required_presentation = {
        "report_id",
        "system",
        "strict_reconstruction",
        "source_mapping",
        "source_artifacts",
        "failure_modes",
        "provenance",
        "external_basis_registry",
        "claim_classifications",
    }
    missing = sorted(required_presentation - set(presentation))
    if missing:
        raise ContractError("missing SOFRS presentation fields: " + ", ".join(missing))
    if verify_artifacts:
        resolve_artifact_reference(
            assembly_implementation,
            repository_root=root,
        )
        for reference in presentation["source_artifacts"]:
            resolve_artifact_reference(reference, repository_root=root)

    modules = _module_summaries(compiler_output, ir, compiler_profile)
    claims, degradations, bindings = _normative_items(
        compiler_output,
        ir,
        presentation["claim_classifications"],
    )
    enabled_findings = {
        finding_id
        for module in modules
        if module["status"] == "ENABLED"
        for finding_id in module["finding_ids"]
    }
    findings = [
        {
            "finding_id": item["id"],
            "kind": item["kind"],
            "result_state": item["result_state"],
            "value": deepcopy(item["value"]),
        }
        for item in ir["findings"]
        if item["id"] in enabled_findings
    ]

    compiler_output_ref = artifact_reference(compiler_output_path, repository_root=root)
    alignment_readiness = presentation.get("alignment_readiness")
    if alignment_readiness is None:
        alignment_readiness = _alignment_metadata(
            manifest,
            ir,
            report_id=presentation["report_id"],
            system=presentation["system"],
            assembly_profile_id=assembly_profile["assembly_profile_id"],
            compiler_profile_id=compiler_profile["profile_id"],
            source_artifacts=presentation["source_artifacts"],
        )

    report = {
        "sofrs_version": "2.0",
        "report_id": presentation["report_id"],
        "system": presentation["system"],
        "record_kind": manifest["record_kind"],
        "strict_reconstruction": deepcopy(presentation["strict_reconstruction"]),
        "external_basis_registry": deepcopy(
            presentation["external_basis_registry"]
        ),
        "compiler_contracts": {
            "capability_manifest": artifact_reference(manifest_path, repository_root=root),
            "typed_sof_ir": artifact_reference(ir_path, repository_root=root),
            "compiler_profile": artifact_reference(
                compiler_profile_path, repository_root=root
            ),
            "compiler_output": compiler_output_ref,
        },
        "compiler_output_binding": {
            "artifact_id": "artifact.compiler-output",
            "artifact": compiler_output_ref,
            "compiler_id": compiler_output["compiler_id"],
            "compiler_output_version": compiler_output["compiler_output_version"],
            "compiler_profile_id": compiler_output["profile_id"],
        },
        "assembly_contract": {
            "schema_id": "sofrs-assembly-v2.0",
            "version": "2.0",
            "implementation": deepcopy(assembly_implementation),
            "assembly_profile": artifact_reference(
                assembly_profile_path, repository_root=root
            ),
            "assembly_profile_id": assembly_profile["assembly_profile_id"],
        },
        "item_bindings": bindings,
        "alignment_readiness": alignment_readiness,
        "source_mapping": deepcopy(presentation["source_mapping"]),
        "source_artifacts": deepcopy(presentation["source_artifacts"]),
        "modules": modules,
        "findings": findings,
        "claims": claims,
        "degradation_items": degradations,
        "failure_modes": deepcopy(presentation["failure_modes"]),
        "provenance": deepcopy(presentation["provenance"]),
    }
    validate_contract(report, REPORT_SCHEMA, label="SOFRS v2 report")
    return report
