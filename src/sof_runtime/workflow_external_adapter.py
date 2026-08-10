"""Level 1 external ExpertAdapter workflow: source bundle -> SOFRS."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.adapters.expert import (
    load_case_json,
    load_expert_adapter,
    validate_candidate,
    validate_declaration,
)
from sof_runtime.compiler import compile_documents
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.contracts.validation import write_json
from sof_runtime.paths import COMPILER_CONTRACT_ROOT, PROJECT_ROOT, RUNTIME_CONTRACT_ROOT
from sof_runtime.reporting import (
    artifact_reference,
    assemble_report,
    build_validation_receipt,
    validate_receipt,
    validate_report,
)
from sof_runtime.reporting.assembly_v2 import resolve_artifact_reference
from sof_runtime.reporting.validation_v2 import RECEIPT_SCHEMA


WORKFLOW_VERSION = "1.0"
IR_SCHEMA = COMPILER_CONTRACT_ROOT / "typed-sof-ir.schema.json"
MANIFEST_SCHEMA = COMPILER_CONTRACT_ROOT / "capability-manifest.schema.json"
ADAPTER_DECLARATION_SCHEMA = RUNTIME_CONTRACT_ROOT / "expert-adapter-declaration.schema.json"
REALIZATION_CANDIDATE_SCHEMA = RUNTIME_CONTRACT_ROOT / "expert-realization-candidate.schema.json"


def _ref(path: Path) -> dict[str, Any]:
    return artifact_reference(path, repository_root=PROJECT_ROOT)


def _snapshot(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def _ir_artifact(artifact_id: str, path: Path, role: str, schema_version: str) -> dict[str, Any]:
    reference = _ref(path)
    return {
        "id": artifact_id,
        "uri": reference["uri"],
        "digest": reference["digest"],
        "media_type": "application/json",
        "schema_version": schema_version,
        "role": role,
    }


def _capability(availability: str, description: str, configuration: dict[str, Any] | None = None) -> dict[str, Any]:
    result = {"availability": availability, "description": description}
    if configuration is not None:
        result["configuration"] = configuration
    return result


def _build_manifest(candidate: dict[str, Any], declaration: dict[str, Any]) -> dict[str, Any]:
    labels = candidate["sectorization"]["labels"]
    alphabet = candidate["operative_alphabet"]["labels"]
    return {
        "manifest_version": "1.0",
        "manifest_id": f"{declaration['adapter_id']}.{candidate['source_id']}.manifest",
        "record_kind": candidate["record_kind"],
        "sof_semantics_version": "2.0",
        "adapter": {
            "id": declaration["adapter_id"],
            "version": declaration["adapter_version"],
            "domain": declaration["domain_id"],
            "source_type": "external-expert-source-bundle",
        },
        "space": candidate["space"],
        "capabilities": {
            "sectorization": _capability("DECLARED", "Complete sectorization supplied by the external adapter.", {"origin": candidate["sectorization"]["origin"], "complete": True, "labels": labels, "provenance": declaration["adapter_id"]}),
            "operator_carrier": _capability("DECLARED", "Labelled operative alphabet supplied by the external adapter.", {"alphabet_id": f"{candidate['source_id']}.alphabet", "labels": alphabet, "word_convention": "positive", "adjoint_closed": False, "projectors_are_letters": False}),
            "operator_system": _capability("DECLARED", "Minimal observable operator system for the direct-support control.", {"definition": "span_C{I,Y_a,Y_a^*}"}),
            "route_carrier": _capability("NOT_DECLARED", "The external adapter does not provide routed products."),
            "word_carrier": _capability("NOT_DECLARED", "The external adapter does not provide full-word filtration."),
            "positive_associative_closure": _capability("NOT_DECLARED", "The external adapter does not provide closure saturation."),
            "observable_star_closure": _capability("NOT_DECLARED", "The external adapter does not provide star closure."),
            "sector_enriched_star_closure": _capability("NOT_DECLARED", "The external adapter does not provide sector-enriched closure."),
            "lie_hall_carrier": _capability("NOT_DECLARED", "No Lie/Hall carrier is inferred from the transition matrices."),
            "deformation_chart": _capability("NOT_APPLICABLE", "This reference case is static."),
            "proxy_diagnostic": _capability("NOT_APPLICABLE", "No continuous proxy is used."),
            "diagnostic_analogue": _capability("NOT_APPLICABLE", "The candidate is an explicit strict finite realization."),
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
            "threshold": "required",
            "cutoff": "not_applicable",
            "norm": "required",
            "numerical_tolerance": "required",
            "saturation_audit": "not_applicable",
            "sampling_grid": "not_applicable",
            "trajectory_parameterization": "not_applicable",
        },
        "notes": [
            "The runtime owns Manifest and IR construction; the adapter declares domain semantics and capability boundaries.",
            "Missing carriers remain NOT_DECLARED and are not converted to zero findings.",
        ],
    }


def _build_ir(
    candidate: dict[str, Any],
    declaration: dict[str, Any],
    manifest: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    rule_registry_path: Path,
) -> dict[str, Any]:
    source_id = candidate["source_id"]
    labels = candidate["sectorization"]["labels"]
    alphabet = candidate["operative_alphabet"]["labels"]
    source_artifact_ids = ["artifact.source", "artifact.adapter", "artifact.declaration", "artifact.inspection", "artifact.candidate", "artifact.evidence"]
    return {
        "ir_version": "1.0",
        "record_id": f"{declaration['adapter_id']}.{source_id}.run-001",
        "record_kind": "strict_sof",
        "manifest_ref": {"manifest_id": manifest["manifest_id"], "manifest_version": "1.0", "artifact_id": "artifact.manifest", "digest": artifacts["artifact.manifest"]["digest"]},
        "source": {"adapter_id": declaration["adapter_id"], "adapter_version": declaration["adapter_version"], "source_id": source_id, "artifact_ids": source_artifact_ids},
        "objects": [
            {"id": "space.v", "kind": "finite_space", "label": f"V = C^{candidate['space']['dimension']}", "provenance_artifact_ids": ["artifact.source"], "data": candidate["space"]},
            {"id": "sectorization.q", "kind": "sectorization", "label": "Q = declared sectorization", "carrier_id": "carrier.sector", "provenance_artifact_ids": ["artifact.candidate"], "data": {"labels": labels, "complete": True}},
            {"id": "alphabet.y", "kind": "labelled_alphabet", "label": "Y = declared operative alphabet", "carrier_id": "carrier.operator", "provenance_artifact_ids": ["artifact.candidate"], "data": {"labels": alphabet}},
            {"id": "operator-system.ey", "kind": "operator_system", "label": "E_Y", "carrier_id": "carrier.operator-system", "provenance_artifact_ids": ["artifact.candidate"], "data": {"definition": "span_C{I,Y_a,Y_a^*}"}},
        ],
        "carriers": [
            {"id": "carrier.sector", "kind": "sector", "capability_id": "sectorization", "semantics": "Complete orthogonal sectorization from the adapter's declared state basis.", "object_ids": ["sectorization.q"], "semantic_convention_ids": ["semantic.direction"]},
            {"id": "carrier.operator", "kind": "operator", "capability_id": "operator_carrier", "semantics": "Labelled operative transition operators; projectors are not letters.", "object_ids": ["alphabet.y"], "semantic_convention_ids": ["semantic.alphabet", "semantic.word", "semantic.projector-letter", "semantic.direction", "semantic.depth-indexing"]},
            {"id": "carrier.operator-system", "kind": "operator_system", "capability_id": "operator_system", "semantics": "Observable operator system without inferred Lie or closure semantics.", "object_ids": ["operator-system.ey"], "semantic_convention_ids": ["semantic.alphabet"]},
        ],
        "semantic_conventions": [
            {"id": "semantic.alphabet", "kind": "operative_alphabet", "specification": {"alphabet_id": f"{source_id}.alphabet", "labels": alphabet, "adjoint_closed": False}},
            {"id": "semantic.word", "kind": "word_convention", "specification": {"type": "positive"}},
            {"id": "semantic.projector-letter", "kind": "projector_letter_policy", "specification": {"projectors_are_letters": False}},
            {"id": "semantic.direction", "kind": "direction_convention", "specification": {"channel_direction": "j_to_i"}},
            {"id": "semantic.depth-indexing", "kind": "depth_indexing", "specification": {"first_generator_depth": 1}},
        ],
        "run_policies": [
            {"id": "run.threshold", "kind": "threshold", "specification": {"type": "absolute_matrix_entry", "value": 1e-12, "comparison": "strictly_greater_than"}},
            {"id": "run.norm", "kind": "norm", "specification": {"name": "absolute_entry"}},
            {"id": "run.tolerance", "kind": "numerical_tolerance", "specification": {"absolute": 1e-12, "relative": 1e-10}},
        ],
        "artifacts": list(artifacts.values()) + [_ir_artifact("artifact.rule-registry", rule_registry_path, "proof-reference", "1.0")],
        "certificates": [{"id": "certificate.direct-support", "validator_id": f"{declaration['adapter_id']}.independent-validator", "status": "PASS", "scope": "Finite transition matrices and thresholded direct support.", "artifact_ids": ["artifact.evidence"]}],
        "findings": [{"id": "finding.direct-support", "kind": "boolean_support", "carrier_id": "carrier.operator", "subject_object_ids": ["sectorization.q", "alphabet.y"], "value": candidate["direct_support"], "result_state": "CERTIFIED", "semantic_convention_ids": ["semantic.alphabet", "semantic.direction"], "run_policy_ids": ["run.threshold", "run.norm", "run.tolerance"], "certificate_ids": ["certificate.direct-support"], "artifact_ids": ["artifact.evidence"]}],
        "claims": [{"id": "claim.direct-support", "statement": candidate["claim"]["statement"], "result_state": "CERTIFIED", "claim_status": "Computational Certificate", "capability_ids": ["sectorization", "operator_carrier"], "carrier_ids": ["carrier.sector", "carrier.operator"], "object_ids": ["sectorization.q", "alphabet.y"], "finding_ids": ["finding.direct-support"], "semantic_convention_ids": ["semantic.alphabet", "semantic.direction"], "run_policy_ids": ["run.threshold", "run.norm", "run.tolerance"], "hypotheses": ["The adapter declares a complete finite state basis", "The adapter declares a thresholded transition observable"], "certificate_ids": ["certificate.direct-support"], "artifact_ids": ["artifact.evidence"], "scope": candidate["claim"]["scope"], "negative_boundary": candidate["claim"]["negative_boundary"]}],
        "derivations": [],
    }


def _external_basis(source_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [("source_identity", "source-snapshot-pinned", "SATISFIED"), ("object_level", "object-level-recomputation", "NOT_ASSESSED"), ("structure_level", "realization-structure-validation", "SATISFIED"), ("semantic_adequacy", "domain-semantic-adequacy", "NOT_ASSESSED")]
    packages = []
    constraints = []
    for index, (level, constraint_id, status) in enumerate(entries):
        evidence = deepcopy(source_artifacts) if status == "SATISFIED" else []
        basis_id = f"basis.{level.replace('_', '.')}"
        packages.append({"basis_id": basis_id, "level": level, "status": status, "method": "external-adapter-reference-workflow", "scope": "Bounded external-adapter Level 1 workflow.", "evidence_artifacts": evidence, "constraint_ids": [constraint_id], "negative_boundary": ["Protocol conformance does not establish domain adequacy."]})
        constraints.append({"constraint_id": constraint_id, "basis_id": basis_id, "status": status, "statement": "Declared external-adapter workflow condition.", "evidence_artifacts": evidence})
    return {"registry_version": "1.0", "basis_status": "PARTIAL", "packages": packages, "constraints": constraints, "negative_boundary": ["The runtime validates the adapter contract and report closure; it does not become the domain authority."]}


def _declared_path(case_dir: Path, value: str) -> Path:
    local = (case_dir / value).resolve()
    if local.is_file():
        return local
    return (PROJECT_ROOT / value).resolve()


def run_external_realization(case_directory: str | Path, run_directory: str | Path) -> dict[str, Any]:
    """Run Level 1A and stop before canonical compilation."""
    case_dir = Path(case_directory).resolve()
    run_dir = Path(run_directory).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    case = load_case_json(case_dir)
    adapter = load_expert_adapter(case_dir / case["adapter"])
    declaration = adapter.describe()
    validate_declaration(declaration)
    source = load_json(case_dir / case["source"])
    request = {"workflow_version": WORKFLOW_VERSION, "case_id": case["case_id"], "source_id": source.get("source_id", case["case_id"]), "adapter_id": declaration["adapter_id"], "adapter_version": declaration["adapter_version"]}
    inspection = adapter.inspect_source(deepcopy(source))
    if not isinstance(inspection, dict) or inspection.get("status") != "PASS":
        raise ValueError("external adapter source inspection did not return PASS")
    candidate = adapter.realize(deepcopy(source), request)
    eligibility = validate_candidate(candidate)
    evidence = adapter.evidence()
    if not isinstance(evidence, dict) or evidence.get("status") != "PASS":
        raise ValueError("external adapter evidence() did not return PASS")

    source_path = write_json(run_dir / "source" / "input.json", source)
    adapter_source_path = (case_dir / case["adapter"]).resolve()
    adapter_path = run_dir / "adapter" / "implementation.py"
    adapter_path.parent.mkdir(parents=True, exist_ok=True)
    adapter_path.write_bytes(adapter_source_path.read_bytes())
    declaration_path = write_json(run_dir / "adapter" / "declaration.json", declaration)
    inspection_path = write_json(run_dir / "adapter" / "inspection.json", inspection)
    candidate_path = write_json(run_dir / "realization" / "candidate.json", candidate)
    evidence_path = write_json(run_dir / "realization" / "evidence.json", evidence)

    report_profiles: dict[str, Any] = {}
    for key in ("compiler_profile", "assembly_profile"):
        if key in case:
            profile_path = _declared_path(case_dir, case[key])
            if not profile_path.is_file():
                raise ContractError(f"declared {key} is missing: {profile_path}")
            report_profiles[key] = _ref(profile_path)

    run_receipt = {
        "workflow_version": WORKFLOW_VERSION,
        "stage": "realization",
        "status": "PASS",
        "case_id": case["case_id"],
        "eligibility": eligibility,
        "canonical_compilable": eligibility == "canonical_compilable",
        "adapter": {
            "id": declaration["adapter_id"],
            "version": declaration["adapter_version"],
            "implementation": _ref(adapter_path),
            "declaration": _ref(declaration_path),
            "inspection": _ref(inspection_path),
        },
        "source": _ref(source_path),
        "realization_candidate": _ref(candidate_path),
        "evidence": _ref(evidence_path),
        "report_profiles": report_profiles,
        "negative_boundary": [
            "Realization validation does not establish adapter scientific adequacy.",
            "Only canonical_compilable realizations may enter Manifest, Typed SOF IR, CompilerOutput, or SOFRS assembly.",
        ],
    }
    run_receipt_path = write_json(run_dir / "run-receipt.json", run_receipt)
    return {
        "status": "PASS",
        "stage": "realization",
        "run_directory": str(run_dir),
        "source_id": candidate["source_id"],
        "eligibility": eligibility,
        "canonical_compilable": eligibility == "canonical_compilable",
        "candidate": str(candidate_path),
        "declaration": str(declaration_path),
        "inspection": str(inspection_path),
        "evidence": str(evidence_path),
        "run_receipt": str(run_receipt_path),
    }


def build_external_report(
    realization_directory: str | Path,
    output_directory: str | Path | None = None,
    *,
    compiler_profile_path: str | Path | None = None,
    assembly_profile_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run Level 1B for a canonical-compilable realization."""
    realization_dir = Path(realization_directory).resolve()
    run_receipt_path = realization_dir / "run-receipt.json"
    realization_receipt = load_json(run_receipt_path)
    if realization_receipt.get("eligibility") != "canonical_compilable":
        raise ContractError(
            "extension-only realization is not eligible for canonical compilation; "
            "create a promotion proposal instead"
        )

    run_dir = Path(output_directory).resolve() if output_directory else realization_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    rule_registry_path = _snapshot(
        COMPILER_CONTRACT_ROOT / "rule-registry.json",
        run_dir / "compiler" / "rule-registry.json",
    )
    candidate_path = resolve_artifact_reference(realization_receipt["realization_candidate"])
    declaration_path = resolve_artifact_reference(realization_receipt["adapter"]["declaration"])
    inspection_path = resolve_artifact_reference(realization_receipt["adapter"]["inspection"])
    adapter_path = resolve_artifact_reference(realization_receipt["adapter"]["implementation"])
    source_path = resolve_artifact_reference(realization_receipt["source"])
    evidence_path = resolve_artifact_reference(realization_receipt["evidence"])
    candidate = load_json(candidate_path)
    declaration = load_json(declaration_path)

    profiles = realization_receipt.get("report_profiles", {})
    if compiler_profile_path is None:
        if "compiler_profile" not in profiles:
            raise ContractError("canonical report requires an explicit compiler profile")
        compiler_profile_path = resolve_artifact_reference(profiles["compiler_profile"])
    else:
        compiler_profile_path = Path(compiler_profile_path).resolve()
    if assembly_profile_path is None:
        if "assembly_profile" not in profiles:
            raise ContractError("canonical report requires an explicit assembly profile")
        assembly_profile_path = resolve_artifact_reference(profiles["assembly_profile"])
    else:
        assembly_profile_path = Path(assembly_profile_path).resolve()

    manifest = _build_manifest(candidate, declaration)
    manifest_path = write_json(run_dir / "compiler" / "manifest.json", manifest)
    manifest_artifact = _ir_artifact("artifact.manifest", manifest_path, "manifest", "1.0")
    artifacts = {
        "artifact.source": _ir_artifact("artifact.source", source_path, "source-input", "external-source-v1"),
        "artifact.adapter": _ir_artifact("artifact.adapter", adapter_path, "adapter-output", "python-source"),
        "artifact.declaration": _ir_artifact("artifact.declaration", declaration_path, "adapter-output", "1.0"),
        "artifact.inspection": _ir_artifact("artifact.inspection", inspection_path, "validator-output", "1.0"),
        "artifact.candidate": _ir_artifact("artifact.candidate", candidate_path, "adapter-output", "1.0"),
        "artifact.evidence": _ir_artifact("artifact.evidence", evidence_path, "validator-output", "1.0"),
        "artifact.manifest": manifest_artifact,
    }
    ir = _build_ir(candidate, declaration, manifest, artifacts, rule_registry_path)
    ir_path = write_json(run_dir / "compiler" / "typed-ir.json", ir)
    validate_contract(manifest, MANIFEST_SCHEMA, label="runtime-built Capability Manifest")
    validate_contract(ir, IR_SCHEMA, label="runtime-built Typed SOF IR")
    compiler_profile = load_json(compiler_profile_path)
    compiler_output = compile_documents(manifest, ir, compiler_profile, repository_root=PROJECT_ROOT, verify_artifacts=True)
    compiler_output_path = write_json(run_dir / "compiler" / "compiler-output.json", compiler_output)
    assembly_profile = load_json(assembly_profile_path)
    assembly_implementation_path = Path(__import__("sof_runtime.reporting.assembly_v2", fromlist=["__file__"]).__file__).resolve()
    workflow_implementation_path = Path(__file__).resolve()
    assembly_implementation_snapshot = _snapshot(
        assembly_implementation_path,
        run_dir / "compiler" / "assembly-implementation.py",
    )
    workflow_implementation_snapshot = _snapshot(
        workflow_implementation_path,
        run_dir / "compiler" / "workflow-implementation.py",
    )
    validator_implementation_snapshot = _snapshot(
        Path(__import__("sof_runtime.reporting.validation_v2", fromlist=["__file__"]).__file__).resolve(),
        run_dir / "compiler" / "report-validator.py",
    )
    receipt_contract_snapshot = _snapshot(
        RECEIPT_SCHEMA,
        run_dir / "compiler" / "sofrs-validation-receipt.schema.json",
    )
    source_artifact_refs = [_ref(path) for path in (source_path, adapter_path, declaration_path, inspection_path, candidate_path, evidence_path)]
    presentation = {
        "report_id": f"{declaration['adapter_id']}.{candidate['source_id']}.sofreport",
        "system": f"External adapter reference: {declaration['domain_id']}",
        "strict_reconstruction": {"candidate_status": "not_applicable", "available_requirements": [], "missing_requirements": [], "evaluator_id": f"{declaration['adapter_id']}.source-validator", "evaluator_version": declaration["adapter_version"], "interpretation": "The external adapter supplied an explicit finite complex realization candidate."},
        "source_mapping": {"status": "adapter-derived", "construction": "Runtime-owned Manifest/IR construction from an admitted ExpertAdapter RealizationCandidate.", "adapter_id": declaration["adapter_id"], "adapter_version": declaration["adapter_version"], "justification": "The adapter maps domain transition matrices to a declared sectorization and operative alphabet.", "limitations": ["The runtime does not infer omitted carriers or domain adequacy."]},
        "source_artifacts": source_artifact_refs,
        "failure_modes": ["This Level 1 workflow does not compare two reports or interpret a SOFAUDIT.", "Direct support is certified only under the adapter-declared source and threshold boundary."],
        "provenance": {"kind": "native_generation", "producer": _ref(workflow_implementation_snapshot), "source_snapshot": _ref(source_path), "adapter": _ref(adapter_path), "compiler_profile_ref": _ref(compiler_profile_path), "compiler_output_ref": _ref(compiler_output_path), "assembly_profile_ref": _ref(assembly_profile_path)},
        "external_basis_registry": _external_basis(source_artifact_refs),
        "claim_classifications": {"claim.direct-support": {"claim_target": "representation_interface", "certificate_class": "protocol_conformance", "classification_source": "independent_validator", "external_basis_refs": ["basis.source.identity", "basis.structure.level"], "external_constraint_ids": ["source-snapshot-pinned", "realization-structure-validation"]}},
    }
    report = assemble_report(manifest_path, ir_path, compiler_profile_path, compiler_output_path, assembly_profile_path, assembly_implementation=_ref(assembly_implementation_snapshot), presentation=presentation, repository_root=PROJECT_ROOT, verify_artifacts=True)
    report_path = write_json(run_dir / "report" / "result.sofreport.json", report)
    validate_report(report_path, repository_root=PROJECT_ROOT)
    receipt = build_validation_receipt(
        report_path,
        repository_root=PROJECT_ROOT,
        validator_implementation_path=validator_implementation_snapshot,
        receipt_contract=_ref(receipt_contract_snapshot),
    )
    receipt_path = write_json(run_dir / "report" / "validation-receipt.json", receipt)
    validate_receipt(receipt_path, repository_root=PROJECT_ROOT)
    report_stage_receipt = {
        "workflow_version": WORKFLOW_VERSION,
        "stage": "report",
        "status": "PASS",
        "realization_receipt": _ref(run_receipt_path),
        "report": _ref(report_path),
        "validation_receipt": _ref(receipt_path),
        "negative_boundary": [
            "Report conformance does not establish adapter scientific adequacy or universal SOF support."
        ],
    }
    report_stage_receipt_path = write_json(
        run_dir / "report" / "report-stage-receipt.json",
        report_stage_receipt,
    )
    return {
        "status": "PASS",
        "stage": "report",
        "run_directory": str(run_dir),
        "source_id": candidate["source_id"],
        "report_id": report["report_id"],
        "candidate": str(candidate_path),
        "manifest": str(manifest_path),
        "typed_ir": str(ir_path),
        "report": str(report_path),
        "validation_receipt": str(receipt_path),
        "run_receipt": str(run_receipt_path),
        "report_stage_receipt": str(report_stage_receipt_path),
        "compiler_items": len(compiler_output["items"]),
    }


def run_external_adapter(case_directory: str | Path, run_directory: str | Path) -> dict[str, Any]:
    """Reference convenience wrapper for Level 1A plus Level 1B."""
    realization = run_external_realization(case_directory, run_directory)
    if not realization["canonical_compilable"]:
        raise ContractError(
            "external-adapter report workflow requires a canonical-compilable realization"
        )
    report = build_external_report(run_directory)
    return {**realization, **report, "stage": "realization_and_report"}
