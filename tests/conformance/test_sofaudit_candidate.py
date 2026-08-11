from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sof_runtime.comparison import validate_audit
from sof_runtime.contracts import ContractError
from sof_runtime.contracts.validation import write_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.reporting import artifact_reference, build_validation_receipt

from . import test_sofrs_candidate as sofrs_fixture


def _artifact(artifact_id: str, role: str, path: Path) -> dict:
    return {
        "id": artifact_id,
        "role": role,
        **artifact_reference(path, repository_root=PROJECT_ROOT),
    }


def _role_basis(side: str) -> dict:
    return {
        "role": side,
        "basis_kind": "declared_baseline_only",
        "authority_status": "DECLARED",
        "scope": "Selected report baseline for this conformance fixture.",
        "evidence_artifacts": [
            f"artifact.{side}-report",
            f"artifact.{side}-report-validation-receipt",
        ],
        "negative_boundary": [
            "The selected reference is not thereby a truth oracle."
        ],
    }


def _alignment(kind: str, labels: list[str]) -> dict:
    return {
        "alignment_id": f"fixture.{kind}.identity",
        "alignment_kind": kind,
        "state": "TOTAL",
        "map_kind": "bijection",
        "reference_carrier": "strict-report-labels",
        "target_carrier": "strict-report-labels",
        "pairs": [
            {
                "reference_id": label,
                "target_id": label,
                "relation": "equivalent",
                "evidence_artifact_ids": ["artifact.alignment-evidence"],
            }
            for label in labels
        ],
        "unmatched_reference_ids": [],
        "unmatched_target_ids": [],
        "properties": {
            "total_on_reference": True,
            "total_on_target": True,
            "injective": True,
            "surjective": True,
        },
        "semantic_basis": "Identity on the shared strict conformance labels.",
        "negative_boundary": [
            "Fixture identity does not establish cross-domain semantic equivalence."
        ],
    }


class SofauditCandidateConformanceTests(unittest.TestCase):
    def _build(self, directory: Path) -> tuple[Path, dict]:
        builder = sofrs_fixture.SofrsCandidateConformanceTests()
        reference_path, _, reference = builder._build(
            directory / "reference",
            report_id="strict-reference",
            system="Strict comparison reference",
        )
        target_path, _, target = builder._build(
            directory / "target",
            report_id="strict-target",
            system="Strict comparison target",
        )
        reference_receipt_path = write_json(
            directory / "reference.validation-receipt.json",
            build_validation_receipt(reference_path),
        )
        target_receipt_path = write_json(
            directory / "target.validation-receipt.json",
            build_validation_receipt(target_path),
        )
        alignment_evidence_path = write_json(
            directory / "alignment-evidence.json",
            {
                "alignment_id": "fixture.identity",
                "reference_report_id": reference["report_id"],
                "target_report_id": target["report_id"],
                "method": "declared identity on equal labels",
            },
        )
        profile_document = {
            "profile_id": "sof-runtime.strict-identity.v2",
            "profile_version": "2.0",
            "applicable_regime": "strict_vs_strict",
            "requested_coordinate_ids": ["operator.support.summary"],
            "coordinate_registry_ref": "schemas/sofaudit/coordinate-semantics-registry-v1.0.json",
            "coordinate_families": ["operator"],
            "availability_semantics": {
                "unavailable_states": ["NOT_DECLARED", "NOT_APPLICABLE", "INCOMPARABLE", "UNRESOLVED"],
                "null_value_states": ["NOT_DECLARED", "NOT_APPLICABLE", "INCOMPARABLE", "UNRESOLVED"],
                "zero_is_unavailable": False,
            },
            "comparison_semantics": {
                "matched_states": ["ALIGNED", "MISMATCH"],
                "comparison_is_pairwise": True,
            },
            "carrier_requirements": {"strict": ["operator"], "analogue": []},
            "required_evidence_roles": [
                "reference-report",
                "target-report",
                "reference-report-validation-receipt",
                "target-report-validation-receipt",
                "audit-profile",
                "coordinate-semantics-registry",
            ],
        }
        profile_path = write_json(directory / "audit-profile.json", profile_document)
        registry_path = (
            PROJECT_ROOT
            / "contracts"
            / "comparison"
            / "v2.0"
            / "coordinate-semantics-registry.json"
        )
        artifacts = [
            _artifact("artifact.reference-report", "reference-report", reference_path),
            _artifact("artifact.target-report", "target-report", target_path),
            _artifact(
                "artifact.reference-report-validation-receipt",
                "reference-report-validation-receipt",
                reference_receipt_path,
            ),
            _artifact(
                "artifact.target-report-validation-receipt",
                "target-report-validation-receipt",
                target_receipt_path,
            ),
            _artifact(
                "artifact.alignment-evidence",
                "alignment-evidence",
                alignment_evidence_path,
            ),
            _artifact("artifact.audit-profile", "audit-profile", profile_path),
            _artifact(
                "artifact.coordinate-semantics-registry",
                "coordinate-semantics-registry",
                registry_path,
            ),
        ]
        artifact_by_id = {item["id"]: item for item in artifacts}
        reference_basis = _role_basis("reference")
        target_basis = _role_basis("target")
        reference_item = reference["claims"][0]
        target_item = target["claims"][0]
        sector_labels = reference["alignment_readiness"]["sector_metadata"][
            "labels"
        ]
        observable_labels = reference["alignment_readiness"][
            "observable_metadata"
        ]["labels"]
        guard_evidence = ["artifact.alignment-evidence"]
        condition_checks = []
        for condition_id in (
            "source-report-receipts-validate",
            "paper-x-record-kind-permission",
            "paper-x-carrier-alignment",
            "paper-x-policy-alignment",
            "paper-x-evidence-alignment",
            "paper-x-promotion-audit",
            "paper-xiii-sector-alignment",
            "paper-xiii-observable-alignment",
            "paper-xiii-comparison-specification",
        ):
            evidence = guard_evidence
            if condition_id == "source-report-receipts-validate":
                evidence = [
                    "artifact.reference-report-validation-receipt",
                    "artifact.target-report-validation-receipt",
                ]
            elif condition_id == "paper-x-record-kind-permission":
                evidence = ["artifact.reference-report", "artifact.target-report"]
            condition_checks.append(
                {
                    "condition_id": condition_id,
                    "status": "SATISFIED",
                    "evidence_artifact_ids": evidence,
                }
            )

        audit = {
            "sofaudit_version": "2.0",
            "artifact_type": "sofaudit",
            "comparison_object": "SOFReportComparison",
            "audit_id": "strict-identity-comparison",
            "system": "Strict SOFRS identity comparison fixture",
            "regime": "strict_vs_strict",
            "source_reports": {
                "reference": {
                    "report_id": reference["report_id"],
                    "label": reference["system"],
                    "artifact": artifact_reference(
                        reference_path, repository_root=PROJECT_ROOT
                    ),
                    "validation_receipt": artifact_reference(
                        reference_receipt_path, repository_root=PROJECT_ROOT
                    ),
                    "sofrs_version": "2.0",
                    "record_kind": "strict_sof",
                    "admission_basis": "native_sofrs_v2",
                    "comparison_role_basis": reference_basis,
                },
                "target": {
                    "report_id": target["report_id"],
                    "label": target["system"],
                    "artifact": artifact_reference(
                        target_path, repository_root=PROJECT_ROOT
                    ),
                    "validation_receipt": artifact_reference(
                        target_receipt_path, repository_root=PROJECT_ROOT
                    ),
                    "sofrs_version": "2.0",
                    "record_kind": "strict_sof",
                    "admission_basis": "native_sofrs_v2",
                    "comparison_role_basis": target_basis,
                },
            },
            "inherited_compiler_guards": {
                "paper_x_contract_version": "1.0",
                "state": "ADMITTED",
                "condition_checks": condition_checks,
                "negative_boundaries": [
                    "Admission permits this declared comparison only."
                ],
            },
            "audit_profile": {
                **profile_document,
                "profile_artifact_id": "artifact.audit-profile",
                "coordinate_registry_artifact_id": "artifact.coordinate-semantics-registry",
            },
            "alignment": {
                "sector_alignment": _alignment("sector", sector_labels),
                "observable_alignment": _alignment(
                    "observable", observable_labels
                ),
            },
            "comparison_specification": {
                "specification_id": "sof-runtime.exact-identity.v2",
                "normalization": {
                    "normalization_id": "identity",
                    "numeric_policy": "exact",
                    "equality_tolerance": 0,
                    "sentinel_policy": "state-not-infinity",
                    "generator_policy": "report-bound-generators",
                },
                "metric": {
                    "metric_id": "absolute-difference",
                    "domain": "integer",
                    "unit_policy": "unitless",
                    "missing_value_policy": "incomparable",
                    "zero_denominator_policy": "not-applicable",
                },
                "depth_semantics": {
                    "carrier": "not-applicable",
                    "mode": "not-applicable",
                    "reference_cutoff": None,
                    "target_cutoff": None,
                    "unreached_policy": "incomparable",
                },
                "thresholds": {
                    "threshold_id": "not-applicable",
                    "value": None,
                    "source": "not-applicable",
                },
                "parameter_synchronization": {
                    "kind": "identity",
                    "map_artifact_id": None,
                    "interpolation_method": "not-applicable",
                    "extrapolation_forbidden": True,
                },
                "aggregation": {
                    "kind": "coordinatewise",
                    "scalarization": "none",
                    "weights_artifact_id": None,
                    "weight_declaration": None,
                },
            },
            "comparison_basis": {
                "basis_status": "COMPLETE",
                "reference_role_basis": deepcopy(reference_basis),
                "alignment_evidence": ["artifact.alignment-evidence"],
                "object_level_oracle": {
                    "status": "NOT_ASSESSED",
                    "independence": {
                        "implementation_relation": "not_assessed",
                        "producer_relation": "not_assessed",
                        "input_source": "not_assessed",
                        "producer_cache_used": None,
                    },
                    "raw_source_artifacts": [],
                    "independent_recomputation_artifacts": [],
                    "oracle_result_artifact": None,
                    "audit_result_artifact": None,
                },
                "policy_compatibility": {
                    "status": "SATISFIED",
                    "policy_artifact_ids": ["artifact.alignment-evidence"],
                    "negative_boundary": [
                        "Policy compatibility does not establish object truth."
                    ],
                },
                "negative_boundary": [
                    "This basis supports only an alignment-relative comparison."
                ],
            },
            "coordinates": {
                "operator.support.summary": {
                    "comparison_state": "ALIGNED",
                    "result_state": "OBSERVED",
                    "claim_status": "Computational Observation",
                    "claim_target": "comparison_relation",
                    "certificate_class": None,
                    "classification_source": "audit_engine",
                    "report_item_binding": {
                        "binding_state": "paired",
                        "reference_item_ref": {
                            "report_id": reference["report_id"],
                            "report_item_id": reference_item["report_item_id"],
                            "source_output_item_id": reference_item[
                                "source_output_item_id"
                            ],
                            "item_kind": "claim",
                            "artifact_digest": artifact_by_id[
                                "artifact.reference-report"
                            ]["digest"],
                        },
                        "target_item_ref": {
                            "report_id": target["report_id"],
                            "report_item_id": target_item["report_item_id"],
                            "source_output_item_id": target_item[
                                "source_output_item_id"
                            ],
                            "item_kind": "claim",
                            "artifact_digest": artifact_by_id[
                                "artifact.target-report"
                            ]["digest"],
                        },
                        "reason": None,
                    },
                    "coordinate_family": "operator",
                    "value_schema_id": "operator.support.v1",
                    "value": {
                        "reference_value": {"support_count": 1},
                        "target_value": {"support_count": 1},
                        "normalized_reference_value": {"support_count": 1},
                        "normalized_target_value": {"support_count": 1},
                        "relation": "equal",
                        "delta": 0,
                        "unit": None,
                        "metric_result": {
                            "metric_id": "absolute-difference",
                            "status": "computed",
                            "value": 0,
                        },
                        "policy_refs": [],
                        "oracle_ref": None,
                    },
                    "source_artifact_ids": ["artifact.alignment-evidence"],
                }
            },
            "claim": {
                "result_state": "CERTIFIED",
                "claim_status": "Computational Certificate",
                "claim_target": "comparison_relation",
                "certificate_class": "comparison_audit",
                "classification_source": "audit_engine",
                "statement": "The selected report items agree under declared identity alignment.",
                "negative_boundary": "This does not establish external-object truth.",
                "source_artifact_ids": [
                    "artifact.reference-report",
                    "artifact.target-report",
                    "artifact.reference-report-validation-receipt",
                    "artifact.target-report-validation-receipt",
                    "artifact.alignment-evidence",
                ],
            },
            "failure_modes": [
                "The fixture tests protocol-relative identity only."
            ],
            "source_artifacts": artifacts,
            "provenance": {
                "kind": "native",
                "generator_id": "sof-runtime.comparison-fixture",
                "generator_version": "2.0",
                "generation_artifact_ids": ["artifact.alignment-evidence"],
                "generation_notes": ["Generated from two validated SOFRS v2 reports."],
            },
        }
        audit_path = write_json(directory / "strict-identity.sofaudit.json", audit)
        return audit_path, audit

    def test_native_comparison_validates_semantically(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            self.assertEqual(validate_audit(audit_path), audit)

    def test_cli_validates_sofaudit(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, _ = self._build(Path(temporary))
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "sof_runtime.cli.main",
                    "validate-sofaudit",
                    str(audit_path),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn('"status": "PASS"', completed.stdout)

    def test_role_and_regime_are_recomputed(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["source_reports"]["reference"]["comparison_role_basis"][
                "role"
            ] = "target"
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "comparison role"):
                validate_audit(audit_path)

    def test_regime_is_recomputed(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["regime"] = "strict_vs_analogue"
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "regime differs"):
                validate_audit(audit_path)

    def test_alignment_properties_are_recomputed(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            for property_name in (
                "total_on_reference",
                "total_on_target",
                "injective",
                "surjective",
            ):
                hostile = deepcopy(audit)
                properties = hostile["alignment"]["sector_alignment"]["properties"]
                properties[property_name] = not properties[property_name]
                write_json(audit_path, hostile)
                with self.assertRaisesRegex(ContractError, "properties differ"):
                    validate_audit(audit_path)

    def test_profile_coordinate_closure_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["audit_profile"]["requested_coordinate_ids"] = [
                "operator.support.other"
            ]
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "not closed"):
                validate_audit(audit_path)

    def test_guard_state_controls_coordinates(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["inherited_compiler_guards"]["condition_checks"][3][
                "status"
            ] = "FAILED"
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "guard state"):
                validate_audit(audit_path)

    def test_rejected_guard_cannot_emit_affirmative_audit(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["inherited_compiler_guards"]["condition_checks"][3][
                "status"
            ] = "FAILED"
            audit["inherited_compiler_guards"]["state"] = "REJECTED"
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "emitted a comparison"):
                validate_audit(audit_path)

    def test_basis_complete_is_recomputed(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["comparison_basis"]["alignment_evidence"] = []
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "basis status"):
                validate_audit(audit_path)

    def test_claim_certificate_compatibility_is_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["claim"]["certificate_class"] = "protocol_conformance"
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "not permitted"):
                validate_audit(audit_path)

    def test_artifact_digest_is_recomputed(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["source_artifacts"][0]["digest"]["value"] = "0" * 64
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "digest mismatch"):
                validate_audit(audit_path)

    def test_artifact_ids_and_roles_are_unique(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            duplicate = deepcopy(audit["source_artifacts"][0])
            duplicate["role"] = "duplicate-report-role"
            audit["source_artifacts"].append(duplicate)
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "ids are not unique"):
                validate_audit(audit_path)

            audit_path, audit = self._build(Path(temporary))
            duplicate = deepcopy(audit["source_artifacts"][0])
            duplicate["id"] = "artifact.duplicate-report"
            audit["source_artifacts"].append(duplicate)
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "roles are not unique"):
                validate_audit(audit_path)

    def test_external_object_claim_requires_independent_oracle(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            audit_path, audit = self._build(Path(temporary))
            audit["claim"].update(
                {
                    "claim_target": "external_mathematical_object",
                    "certificate_class": "object",
                    "classification_source": "independent_oracle",
                }
            )
            audit["comparison_basis"]["basis_status"] = "PARTIAL"
            write_json(audit_path, audit)
            with self.assertRaisesRegex(ContractError, "independent oracle"):
                validate_audit(audit_path)


if __name__ == "__main__":
    unittest.main()
