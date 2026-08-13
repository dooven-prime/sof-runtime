from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Callable
import unittest

from sof_runtime.compiler import compile_documents
from sof_runtime.contracts import ContractError, load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.reporting import (
    artifact_reference,
    assemble_report,
    build_validation_receipt,
    validate_receipt,
    validate_report,
)


UPSTREAM_FIXTURES = (
    PROJECT_ROOT / "tests" / "conformance" / "fixtures" / "upstream-v1.0"
)
COMPILER_PROFILE = PROJECT_ROOT / "profiles" / "compiler" / "strict-conformance-v1.0.json"
ASSEMBLY_PROFILE = PROJECT_ROOT / "profiles" / "assembly" / "strict-conformance-v2.0.json"
ASSEMBLY_IMPLEMENTATION = (
    PROJECT_ROOT / "src" / "sof_runtime" / "reporting" / "assembly_v2.py"
)


def _external_basis(source_artifacts: list[dict]) -> dict:
    package_specs = (
        (
            "basis.source.identity",
            "source_identity",
            "source-snapshot-pinned",
            "SATISFIED",
            source_artifacts,
        ),
        (
            "basis.object.recomputation",
            "object_level",
            "object-level-recomputation",
            "NOT_ASSESSED",
            [],
        ),
        (
            "basis.structure.validation",
            "structure_level",
            "realization-structure-validation",
            "SATISFIED",
            source_artifacts,
        ),
        (
            "basis.semantic.adequacy",
            "semantic_adequacy",
            "domain-semantic-adequacy",
            "NOT_ASSESSED",
            [],
        ),
    )
    packages = []
    constraints = []
    for basis_id, level, constraint_id, status, evidence in package_specs:
        packages.append(
            {
                "basis_id": basis_id,
                "level": level,
                "constraint_ids": [constraint_id],
                "status": status,
                "method": "strict-conformance-fixture",
                "scope": "Bounded SOFRS assembly conformance fixture.",
                "evidence_artifacts": deepcopy(evidence),
                "negative_boundary": [
                    "This basis does not establish domain adequacy or comparison correctness."
                ],
            }
        )
        constraints.append(
            {
                "constraint_id": constraint_id,
                "basis_id": basis_id,
                "status": status,
                "statement": "Fixture-scoped external basis condition.",
                "evidence_artifacts": deepcopy(evidence),
            }
        )
    return {
        "registry_version": "1.0",
        "basis_status": "PARTIAL",
        "packages": packages,
        "constraints": constraints,
        "negative_boundary": [
            "Protocol conformance does not establish external-object truth."
        ],
    }


def _claim_classifications(compiler_output: dict) -> dict[str, dict]:
    result = {}
    for item in compiler_output["items"]:
        if item["item_kind"] != "claim":
            continue
        certificate = item["claim_status"] == "Computational Certificate"
        result[item["claim_id"]] = {
            "claim_target": "representation_interface",
            "certificate_class": "protocol_conformance" if certificate else None,
            "classification_source": (
                "assembly_validator" if certificate else "domain_adapter"
            ),
            "external_basis_refs": [
                "basis.source.identity",
                "basis.structure.validation",
            ],
            "external_constraint_ids": [
                "source-snapshot-pinned",
                "realization-structure-validation",
            ],
        }
    return result


class SofrsCandidateConformanceTests(unittest.TestCase):
    def _build(
        self,
        directory: Path,
        *,
        report_id: str = "strict-associative-conformance",
        system: str = "Strict associative compiler conformance fixture",
        ir_transform: Callable[[dict], None] | None = None,
    ) -> tuple[Path, Path, dict]:
        manifest_path = (
            UPSTREAM_FIXTURES / "strict-associative-capabilities-v1.0.json"
        )
        evidence_path = UPSTREAM_FIXTURES / "strict-associative-evidence-v1.0.json"
        ir = load_json(UPSTREAM_FIXTURES / "strict-associative-ir-v1.0.json")
        if ir_transform is not None:
            ir_transform(ir)
        artifact_paths = {
            "artifact.manifest": manifest_path,
            "artifact.evidence": evidence_path,
            "artifact.rule-registry": (
                PROJECT_ROOT / "contracts" / "compiler" / "v1.0" / "rule-registry.json"
            ),
        }
        for artifact in ir["artifacts"]:
            artifact["uri"] = artifact_paths[artifact["id"]].relative_to(
                PROJECT_ROOT
            ).as_posix()
        ir_path = write_json(directory / "strict-associative.ir.json", ir)

        compiler_output = compile_documents(
            load_json(manifest_path),
            ir,
            load_json(COMPILER_PROFILE),
            repository_root=PROJECT_ROOT,
            verify_artifacts=True,
        )
        compiler_output_path = write_json(
            directory / "strict-associative.compiler-output.json",
            compiler_output,
        )
        source_artifacts = [
            artifact_reference(evidence_path, repository_root=PROJECT_ROOT)
        ]
        adapter_reference = source_artifacts[1] if len(source_artifacts) > 1 else source_artifacts[0]
        presentation = {
            "report_id": report_id,
            "system": system,
            "strict_reconstruction": {
                "candidate_status": "no",
                "available_requirements": [
                    "finite_space_dimension",
                    "explicit_operator_artifacts",
                    "projector_completeness_certificate",
                ],
                "missing_requirements": [],
                "evaluator_id": "sof-runtime.strict-admission-fixture",
                "evaluator_version": "1.0",
                "interpretation": (
                    "The fixture is already admitted as strict SOF; no reconstruction "
                    "candidate claim is made."
                ),
            },
            "source_mapping": {
                "status": "native",
                "construction": "upstream-compiler-conformance-adapter",
                "adapter_id": "example-matrix-adapter",
                "adapter_version": "1.0",
                "justification": (
                    "The source fixture declares finite complex space, complete marked "
                    "sectors, and a labelled operative alphabet."
                ),
                "limitations": [
                    "This compact fixture establishes protocol conformance only."
                ],
            },
            "source_artifacts": source_artifacts,
            "external_basis_registry": _external_basis(source_artifacts),
            "claim_classifications": _claim_classifications(compiler_output),
            "failure_modes": [
                "Conformance does not establish adapter adequacy outside this fixture."
            ],
            "provenance": {
                "kind": "native_generation",
                "producer": artifact_reference(
                    ASSEMBLY_IMPLEMENTATION,
                    repository_root=PROJECT_ROOT,
                ),
                "source_snapshot": source_artifacts[0],
                "adapter": adapter_reference,
                "compiler_profile_ref": artifact_reference(
                    COMPILER_PROFILE,
                    repository_root=PROJECT_ROOT,
                ),
                "compiler_output_ref": artifact_reference(
                    compiler_output_path,
                    repository_root=PROJECT_ROOT,
                ),
                "assembly_profile_ref": artifact_reference(
                    ASSEMBLY_PROFILE,
                    repository_root=PROJECT_ROOT,
                ),
            },
        }
        report = assemble_report(
            manifest_path,
            ir_path,
            COMPILER_PROFILE,
            compiler_output_path,
            ASSEMBLY_PROFILE,
            assembly_implementation=artifact_reference(
                ASSEMBLY_IMPLEMENTATION,
                repository_root=PROJECT_ROOT,
            ),
            presentation=presentation,
            repository_root=PROJECT_ROOT,
            verify_artifacts=True,
        )
        report_path = write_json(directory / "strict-associative.sofreport.json", report)
        return report_path, compiler_output_path, report

    def test_compiler_output_assembles_and_receipts_faithfully(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            directory = Path(temporary)
            report_path, _, report = self._build(directory)
            self.assertEqual(validate_report(report_path), report)
            self.assertEqual(len(report["item_bindings"]), 8)
            self.assertEqual(len(report["claims"]), 5)
            self.assertEqual(len(report["degradation_items"]), 3)
            self.assertTrue(
                any(
                    module["module_id"] == "sof-basic"
                    and module["status"] == "ENABLED"
                    for module in report["modules"]
                )
            )

            receipt = build_validation_receipt(report_path)
            receipt_path = write_json(directory / "validation-receipt.json", receipt)
            self.assertEqual(validate_receipt(receipt_path), receipt)

    def test_report_claim_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            report_path, _, report = self._build(Path(temporary))
            report["claims"][0]["statement"] = "Presentation-layer claim drift."
            write_json(report_path, report)
            with self.assertRaisesRegex(ContractError, "faithful Assemble_v2"):
                validate_report(report_path)

    def test_duplicate_item_binding_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            report_path, _, report = self._build(Path(temporary))
            report["item_bindings"].append(deepcopy(report["item_bindings"][0]))
            write_json(report_path, report)
            with self.assertRaisesRegex(ContractError, "duplicate"):
                validate_report(report_path)

    def test_degradation_cannot_be_retyped_as_failure_mode(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            report_path, _, report = self._build(Path(temporary))
            removed = report["degradation_items"].pop()
            report["failure_modes"].append(removed)
            write_json(report_path, report)
            with self.assertRaisesRegex(ContractError, "normative items"):
                validate_report(report_path)

    def test_tampered_compiler_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            report_path, output_path, _ = self._build(Path(temporary))
            output = load_json(output_path)
            output["items"][0]["result_state"] = "OBSERVED"
            write_json(output_path, output)
            with self.assertRaisesRegex(ContractError, "digest mismatch"):
                validate_report(report_path)

    def test_receipt_cannot_borrow_the_reference_validator_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            directory = Path(temporary)
            report_path, _, report = self._build(directory)
            receipt = build_validation_receipt(report_path)
            receipt["validator"]["implementation"] = report["assembly_contract"][
                "implementation"
            ]
            receipt_path = write_json(directory / "borrowed-validator-receipt.json", receipt)
            with self.assertRaisesRegex(ContractError, "validator implementation"):
                validate_receipt(receipt_path)

    def test_cli_assembles_reports_and_snapshots_receipt_dependencies(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            directory = Path(temporary)
            _, output_path, report = self._build(directory)
            presentation = {
                key: report[key]
                for key in (
                    "report_id",
                    "system",
                    "strict_reconstruction",
                    "source_mapping",
                    "source_artifacts",
                    "failure_modes",
                    "provenance",
                    "external_basis_registry",
                )
            }
            presentation["claim_classifications"] = {
                claim["claim_id"]: {
                    "claim_target": claim["claim_target"],
                    "certificate_class": claim["certificate_class"],
                    "classification_source": claim["classification_source"],
                    "external_basis_refs": claim["external_basis_refs"],
                    "external_constraint_ids": claim["external_constraint_ids"],
                }
                for claim in report["claims"]
            }
            presentation_path = write_json(directory / "presentation.json", presentation)
            cli_directory = directory / "cli"
            cli_report = cli_directory / "strict-associative.sofreport.json"
            manifest_path = PROJECT_ROOT / report["compiler_contracts"]["capability_manifest"]["uri"]
            ir_path = PROJECT_ROOT / report["compiler_contracts"]["typed_sof_ir"]["uri"]
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "sof_runtime.cli.main",
                    "assemble-sofrs",
                    str(manifest_path),
                    str(ir_path),
                    str(COMPILER_PROFILE),
                    str(output_path),
                    str(ASSEMBLY_PROFILE),
                    str(presentation_path),
                    "--out",
                    str(cli_report),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            validate_report(cli_report)

            receipt_path = cli_directory / "validation-receipt.json"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "sof_runtime.cli.main",
                    "validate-sofrs",
                    str(cli_report),
                    "--receipt",
                    str(receipt_path),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            receipt = validate_receipt(receipt_path)
            self.assertIn("/artifacts/sha256/", receipt["validator"]["implementation"]["uri"])
            self.assertIn("/artifacts/sha256/", receipt["validator"]["receipt_contract"]["uri"])

    def test_external_basis_complete_cannot_be_self_declared(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            report_path, _, report = self._build(Path(temporary))
            report["external_basis_registry"]["basis_status"] = "COMPLETE"
            write_json(report_path, report)
            with self.assertRaisesRegex(ContractError, "status differs"):
                validate_report(report_path)

    def test_claim_classification_source_is_constrained(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            report_path, _, report = self._build(Path(temporary))
            report["claims"][0]["classification_source"] = "migration_adapter"
            write_json(report_path, report)
            with self.assertRaisesRegex(ContractError, "classification source"):
                validate_report(report_path)


if __name__ == "__main__":
    unittest.main()
