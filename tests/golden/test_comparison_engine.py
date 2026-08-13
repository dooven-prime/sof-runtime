from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from sof_runtime.comparison import (
    build_comparison,
    validate_audit,
    validate_audit_validation_receipt,
)
from sof_runtime.contracts import ContractError, load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.artifacts.digest import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.reporting import build_validation_receipt

from tests.conformance import test_sofrs_candidate as sofrs_fixture


PROFILE = PROJECT_ROOT / "profiles" / "comparison" / "gridworld-f4-support-v2.0.json"


def _synchronize_fabricated_receipt(audit_path: Path, receipt_path: Path) -> None:
    audit = load_json(audit_path)
    receipt = load_json(receipt_path)
    source_by_role = {
        item["role"]: {"uri": item["uri"], "digest": item["digest"]}
        for item in audit["source_artifacts"]
    }
    audit_reference = {
        "uri": audit_path.relative_to(PROJECT_ROOT).as_posix(),
        "digest": {"algorithm": "sha256", "value": sha256_file(audit_path)},
    }
    receipt["audit"]["artifact"] = deepcopy(audit_reference)
    for item in receipt["artifact_closure"]["ordered_artifacts"]:
        if item["role"] == "audit":
            item["artifact"] = deepcopy(audit_reference)
        elif item["role"] in source_by_role:
            item["artifact"] = deepcopy(source_by_role[item["role"]])
    ordered = receipt["artifact_closure"]["ordered_artifacts"]
    receipt["artifact_closure"]["closure_digest"]["value"] = sha256_bytes(
        canonical_json_bytes(ordered)
    )
    write_json(receipt_path, receipt)


def _alignment(reference: dict, target: dict) -> dict:
    sector_labels = reference["alignment_readiness"]["sector_metadata"]["labels"]
    target_sector_labels = target["alignment_readiness"]["sector_metadata"]["labels"]
    observable_labels = reference["alignment_readiness"]["observable_metadata"]["labels"]
    target_observable_labels = target["alignment_readiness"]["observable_metadata"]["labels"]
    return {
        "alignment_version": "1.0",
        "alignment_id": "sof-runtime.gridworld-f4.identity",
        "alignment_kind": "identity",
        "map_kind": "bijection",
        "reference_carrier": "gridworld-report-labels",
        "target_carrier": "gridworld-report-labels",
        "sector_pairs": [
            {"reference_id": left, "target_id": right, "relation": "equivalent"}
            for left, right in zip(sector_labels, target_sector_labels, strict=True)
        ],
        "observable_pairs": [
            {"reference_id": left, "target_id": right, "relation": "equivalent"}
            for left, right in zip(
                observable_labels, target_observable_labels, strict=True
            )
        ],
        "semantic_basis": "Declared identity on the retained GridWorld F4 frame.",
        "negative_boundary": [
            "Identity on this fixture does not establish domain adequacy or reference truth."
        ],
    }


def _add_two_support_carriers(ir: dict) -> None:
    direct_pairs = [["A", "B"], ["B", "C"]]
    word_pairs = direct_pairs + [["A", "C"]]
    _set_direct_support_pairs(ir, direct_pairs)
    ir["findings"].append(
        {
            "id": "finding.word-length-two",
            "kind": "boolean_support",
            "carrier_id": "carrier.word",
            "subject_object_ids": ["word-space.depth-5"],
            "value": {"pairs": word_pairs, "pair_count": len(word_pairs)},
            "result_state": "CERTIFIED",
            "semantic_convention_ids": [
                "semantic.alphabet",
                "semantic.word",
                "semantic.projector-letter",
                "semantic.direction",
                "semantic.depth-indexing",
            ],
            "run_policy_ids": ["run.cutoff", "run.threshold", "run.norm"],
            "certificate_ids": ["certificate.route-word-audit"],
            "artifact_ids": ["artifact.evidence"],
        }
    )
    ir["claims"].append(
        {
            "id": "claim.word-length-two",
            "statement": "The fixture records ordered positive-word support at length two.",
            "result_state": "CERTIFIED",
            "claim_status": "Computational Certificate",
            "capability_ids": [
                "sectorization",
                "operator_carrier",
                "word_carrier",
            ],
            "carrier_ids": ["carrier.word"],
            "object_ids": ["word-space.depth-5"],
            "finding_ids": ["finding.word-length-two"],
            "semantic_convention_ids": [
                "semantic.alphabet",
                "semantic.word",
                "semantic.projector-letter",
                "semantic.direction",
                "semantic.depth-indexing",
            ],
            "run_policy_ids": ["run.cutoff", "run.threshold", "run.norm"],
            "hypotheses": [
                "The labelled positive-word carrier is declared",
                "Length-two products are evaluated under the report threshold",
            ],
            "certificate_ids": ["certificate.route-word-audit"],
            "artifact_ids": ["artifact.evidence"],
            "scope": "The declared finite length-two word-support fixture.",
            "negative_boundary": "Length-two support is not exact word depth or route support.",
        }
    )


def _set_direct_support_pairs(ir: dict, direct_pairs: list[list[str]] | None = None) -> None:
    pairs = direct_pairs or [["A", "B"], ["B", "C"]]
    direct = next(
        item for item in ir["findings"] if item["id"] == "finding.direct-support"
    )
    direct["value"] = {"pairs": pairs, "pair_count": len(pairs)}


def _comparison_profile(root: Path) -> Path:
    profile = load_json(PROFILE)
    profile["profile_id"] = "sof-runtime.two-carrier-conformance.v2"
    profile["comparison_specification"]["specification_id"] = (
        "sof-runtime.two-carrier-conformance.theta-v2"
    )
    profile["comparison_specification"]["thresholds"] = {
        "threshold_id": "entrywise-support",
        "value": 1e-12,
        "source": "comparison-specification",
    }
    return write_json(root / "comparison-profile.json", profile)


class ComparisonEngineTests(unittest.TestCase):
    def test_profile_drives_operator_and_word_coordinate_evaluators(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            root = Path(temporary)
            builder = sofrs_fixture.SofrsCandidateConformanceTests()
            reference_path, _, reference = builder._build(
                root / "reference",
                report_id="two-carrier-reference",
                system="Two-carrier reference fixture",
                ir_transform=_add_two_support_carriers,
            )
            target_path, _, target = builder._build(
                root / "target",
                report_id="two-carrier-target",
                system="Two-carrier target fixture",
                ir_transform=_add_two_support_carriers,
            )
            reference_receipt = write_json(
                root / "reference" / "validation-receipt.json",
                build_validation_receipt(reference_path),
            )
            target_receipt = write_json(
                root / "target" / "validation-receipt.json",
                build_validation_receipt(target_path),
            )
            alignment_path = write_json(
                root / "alignment.json", _alignment(reference, target)
            )
            profile_path = _comparison_profile(root)
            result = build_comparison(
                reference_path,
                reference_receipt,
                target_path,
                target_receipt,
                root / "comparison",
                alignment_path=alignment_path,
                profile_path=profile_path,
            )
            audit = validate_audit(result["audit"])
            receipt = validate_audit_validation_receipt(result["receipt"])

        self.assertEqual(
            list(audit["coordinates"]),
            ["operator.support.summary", "word.support.length-2.summary"],
        )
        self.assertEqual(
            result["coordinate_states"],
            {
                "operator.support.summary": "ALIGNED",
                "word.support.length-2.summary": "ALIGNED",
            },
        )
        operator = audit["coordinates"]["operator.support.summary"]
        word = audit["coordinates"]["word.support.length-2.summary"]
        claim_items = {item["claim_id"]: item for item in reference["claims"]}
        self.assertEqual(
            operator["report_item_binding"]["reference_item_ref"]["report_item_id"],
            claim_items["claim.direct-support"]["report_item_id"],
        )
        self.assertEqual(
            word["report_item_binding"]["reference_item_ref"]["report_item_id"],
            claim_items["claim.word-length-two"]["report_item_id"],
        )
        self.assertNotEqual(
            operator["report_item_binding"]["reference_item_ref"]["report_item_id"],
            word["report_item_binding"]["reference_item_ref"]["report_item_id"],
        )
        self.assertEqual(operator["value"]["reference_value"]["pair_count"], 2)
        self.assertEqual(word["value"]["reference_value"]["pair_count"], 3)
        self.assertEqual(operator["coordinate_family"], "operator")
        self.assertEqual(word["coordinate_family"], "word")
        artifact_roles = {item["role"] for item in audit["source_artifacts"]}
        self.assertIn("coordinate-evaluator-registry", artifact_roles)
        self.assertIn("coordinate-evaluator-implementation", artifact_roles)
        self.assertIn(
            "coordinate-evaluation-result-operator.support.summary", artifact_roles
        )
        self.assertIn(
            "coordinate-evaluation-result-word.support.length-2.summary", artifact_roles
        )
        receipt_roles = {
            item["role"] for item in receipt["artifact_closure"]["ordered_artifacts"]
        }
        self.assertTrue(artifact_roles <= receipt_roles)
        self.assertIn(
            "artifact.coordinate-evaluator-implementation",
            operator["source_artifact_ids"],
        )

    def test_evaluator_execution_artifacts_are_digest_bound(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            root = Path(temporary)
            builder = sofrs_fixture.SofrsCandidateConformanceTests()
            reference_path, _, reference = builder._build(
                root / "reference", report_id="closure-reference"
            )
            target_path, _, target = builder._build(
                root / "target", report_id="closure-target"
            )
            reference_receipt = write_json(
                root / "reference" / "validation-receipt.json",
                build_validation_receipt(reference_path),
            )
            target_receipt = write_json(
                root / "target" / "validation-receipt.json",
                build_validation_receipt(target_path),
            )
            result = build_comparison(
                reference_path,
                reference_receipt,
                target_path,
                target_receipt,
                root / "comparison",
                alignment_path=write_json(
                    root / "alignment.json", _alignment(reference, target)
                ),
                profile_path=PROFILE,
            )
            audit = load_json(result["audit"])
            artifacts = {item["role"]: item for item in audit["source_artifacts"]}
            for role in (
                "coordinate-evaluator-implementation",
                "coordinate-evaluation-result-operator.support.summary",
            ):
                path = PROJECT_ROOT / artifacts[role]["uri"]
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b"\n")
                    with self.assertRaisesRegex(ContractError, "artifact digest mismatch"):
                        validate_audit(result["audit"])
                    with self.assertRaisesRegex(ContractError, "artifact digest mismatch"):
                        validate_audit_validation_receipt(result["receipt"])
                finally:
                    path.write_bytes(original)

    def test_coordinated_implementation_tampering_fails_trusted_digest(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            root = Path(temporary)
            builder = sofrs_fixture.SofrsCandidateConformanceTests()
            reference_path, _, reference = builder._build(
                root / "reference", report_id="implementation-reference"
            )
            target_path, _, target = builder._build(
                root / "target", report_id="implementation-target"
            )
            reference_receipt = write_json(
                root / "reference" / "validation-receipt.json",
                build_validation_receipt(reference_path),
            )
            target_receipt = write_json(
                root / "target" / "validation-receipt.json",
                build_validation_receipt(target_path),
            )
            result = build_comparison(
                reference_path,
                reference_receipt,
                target_path,
                target_receipt,
                root / "comparison",
                alignment_path=write_json(
                    root / "alignment.json", _alignment(reference, target)
                ),
                profile_path=PROFILE,
            )
            audit = load_json(result["audit"])
            artifacts = {item["role"]: item for item in audit["source_artifacts"]}
            implementation = PROJECT_ROOT / artifacts[
                "coordinate-evaluator-implementation"
            ]["uri"]
            implementation.write_bytes(implementation.read_bytes() + b"\n# fabricated\n")
            fabricated_digest = sha256_file(implementation)
            artifacts["coordinate-evaluator-implementation"]["digest"][
                "value"
            ] = fabricated_digest
            registry_path = PROJECT_ROOT / artifacts[
                "coordinate-evaluator-registry"
            ]["uri"]
            registry = load_json(registry_path)
            for declaration in registry["evaluators"]:
                declaration["implementation_digest"]["value"] = fabricated_digest
            write_json(registry_path, registry)
            artifacts["coordinate-evaluator-registry"]["digest"]["value"] = (
                sha256_file(registry_path)
            )
            write_json(result["audit"], audit)
            _synchronize_fabricated_receipt(
                Path(result["audit"]), Path(result["receipt"])
            )

            with self.assertRaisesRegex(ContractError, "trusted registry"):
                validate_audit_validation_receipt(result["receipt"])

    def test_coordinated_result_and_projection_tampering_fails_replay(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            root = Path(temporary)
            builder = sofrs_fixture.SofrsCandidateConformanceTests()
            reference_path, _, reference = builder._build(
                root / "reference",
                report_id="result-reference",
                ir_transform=_set_direct_support_pairs,
            )
            target_path, _, target = builder._build(
                root / "target",
                report_id="result-target",
                ir_transform=_set_direct_support_pairs,
            )
            reference_receipt = write_json(
                root / "reference" / "validation-receipt.json",
                build_validation_receipt(reference_path),
            )
            target_receipt = write_json(
                root / "target" / "validation-receipt.json",
                build_validation_receipt(target_path),
            )
            result = build_comparison(
                reference_path,
                reference_receipt,
                target_path,
                target_receipt,
                root / "comparison",
                alignment_path=write_json(
                    root / "alignment.json", _alignment(reference, target)
                ),
                profile_path=PROFILE,
            )
            audit = load_json(result["audit"])
            artifacts = {item["role"]: item for item in audit["source_artifacts"]}
            result_role = "coordinate-evaluation-result-operator.support.summary"
            result_path = PROJECT_ROOT / artifacts[result_role]["uri"]
            evaluation = load_json(result_path)
            evaluation["target_value"]["pairs"] = [["A", "C"]]
            evaluation["target_value"]["pair_count"] = 1
            evaluation["normalized_target_value"] = deepcopy(
                evaluation["target_value"]
            )
            evaluation["delta"] = {
                "missing_pairs": [["A", "B"], ["B", "C"]],
                "extra_pairs": [["A", "C"]],
                "total_mismatch": 3,
            }
            evaluation["comparison_state"] = "MISMATCH"
            evaluation["relation"] = "mismatch"
            evaluation["metric_result"]["value"] = 3
            write_json(result_path, evaluation)
            artifacts[result_role]["digest"]["value"] = sha256_file(result_path)
            coordinate = audit["coordinates"]["operator.support.summary"]
            coordinate["comparison_state"] = evaluation["comparison_state"]
            for field in (
                "reference_value",
                "target_value",
                "normalized_reference_value",
                "normalized_target_value",
                "relation",
                "delta",
                "unit",
                "metric_result",
            ):
                coordinate["value"][field] = deepcopy(evaluation[field])
            write_json(result["audit"], audit)
            _synchronize_fabricated_receipt(
                Path(result["audit"]), Path(result["receipt"])
            )

            with self.assertRaisesRegex(ContractError, "trusted replay"):
                validate_audit_validation_receipt(result["receipt"])

    def test_profile_must_allow_each_evaluator_carrier(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            root = Path(temporary)
            builder = sofrs_fixture.SofrsCandidateConformanceTests()
            reference_path, _, reference = builder._build(
                root / "reference", report_id="carrier-reference"
            )
            target_path, _, target = builder._build(
                root / "target", report_id="carrier-target"
            )
            reference_receipt = write_json(
                root / "reference" / "validation-receipt.json",
                build_validation_receipt(reference_path),
            )
            target_receipt = write_json(
                root / "target" / "validation-receipt.json",
                build_validation_receipt(target_path),
            )
            profile = load_json(PROFILE)
            profile["audit_profile"]["carrier_requirements"]["strict"] = []
            profile_path = write_json(root / "carrier-profile.json", profile)
            with self.assertRaisesRegex(ContractError, "carrier is absent"):
                build_comparison(
                    reference_path,
                    reference_receipt,
                    target_path,
                    target_receipt,
                    root / "comparison",
                    alignment_path=write_json(
                        root / "alignment.json", _alignment(reference, target)
                    ),
                    profile_path=profile_path,
                )

    def test_sector_permutation_survives_producer_audit_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            root = Path(temporary)
            builder = sofrs_fixture.SofrsCandidateConformanceTests()

            def integer_pairs(ir: dict) -> None:
                _set_direct_support_pairs(ir, [[0, 1]])

            reference_path, _, reference = builder._build(
                root / "reference",
                report_id="permutation-reference",
                ir_transform=integer_pairs,
            )
            target_path, _, target = builder._build(
                root / "target",
                report_id="permutation-target",
                ir_transform=integer_pairs,
            )
            target_labels = target["alignment_readiness"]["sector_metadata"][
                "labels"
            ]
            target_labels[0], target_labels[1] = target_labels[1], target_labels[0]
            write_json(target_path, target)
            reference_receipt = write_json(
                root / "reference" / "validation-receipt.json",
                build_validation_receipt(reference_path),
            )
            target_receipt = write_json(
                root / "target" / "validation-receipt.json",
                build_validation_receipt(target_path),
            )
            alignment = _alignment(reference, target)
            alignment["sector_pairs"] = [
                {
                    "reference_id": label,
                    "target_id": label,
                    "relation": "equivalent",
                }
                for label in reference["alignment_readiness"]["sector_metadata"][
                    "labels"
                ]
            ]
            result = build_comparison(
                reference_path,
                reference_receipt,
                target_path,
                target_receipt,
                root / "comparison",
                alignment_path=write_json(root / "alignment.json", alignment),
                profile_path=PROFILE,
            )
            audit = validate_audit(result["audit"])
            validate_audit_validation_receipt(result["receipt"])

        coordinate = audit["coordinates"]["operator.support.summary"]
        self.assertEqual(coordinate["comparison_state"], "MISMATCH")
        self.assertEqual(
            coordinate["value"]["normalized_reference_value"]["pairs"],
            [["A", "B"]],
        )
        self.assertEqual(
            coordinate["value"]["normalized_target_value"]["pairs"],
            [["B", "A"]],
        )

    def test_missing_word_coordinate_remains_not_declared(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as temporary:
            root = Path(temporary)
            builder = sofrs_fixture.SofrsCandidateConformanceTests()
            reference_path, _, reference = builder._build(
                root / "reference",
                report_id="operator-only-reference",
                ir_transform=_set_direct_support_pairs,
            )
            target_path, _, target = builder._build(
                root / "target",
                report_id="operator-only-target",
                ir_transform=_set_direct_support_pairs,
            )
            reference_receipt = write_json(
                root / "reference" / "validation-receipt.json",
                build_validation_receipt(reference_path),
            )
            target_receipt = write_json(
                root / "target" / "validation-receipt.json",
                build_validation_receipt(target_path),
            )
            result = build_comparison(
                reference_path,
                reference_receipt,
                target_path,
                target_receipt,
                root / "comparison",
                alignment_path=write_json(
                    root / "alignment.json", _alignment(reference, target)
                ),
                profile_path=_comparison_profile(root),
            )
            audit = validate_audit(result["audit"])

        operator = audit["coordinates"]["operator.support.summary"]
        word = audit["coordinates"]["word.support.length-2.summary"]
        self.assertEqual(operator["comparison_state"], "ALIGNED")
        self.assertEqual(word["comparison_state"], "NOT_DECLARED")
        self.assertEqual(word["result_state"], "NOT_DECLARED")
        self.assertIsNone(word["value"])
        self.assertIsNone(word["claim_status"])


if __name__ == "__main__":
    unittest.main()
