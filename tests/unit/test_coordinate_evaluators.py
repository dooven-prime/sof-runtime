from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from sof_runtime.comparison.evaluators import CoordinateEvaluatorRegistry
from sof_runtime.contracts import ContractError, load_json
from sof_runtime.paths import PROJECT_ROOT


REPORT_ROOT = (
    PROJECT_ROOT
    / "tests"
    / "conformance"
    / "fixtures"
    / "sofaction"
    / "experiments"
    / "paper13"
    / "results"
    / "native"
    / "gridworld-f4"
    / "source-reports"
    / "reports"
)


def _specification(
    *, normalization_id: str = "identity", metric_id: str = "discrete-mismatch"
) -> dict:
    return {
        "normalization": {"normalization_id": normalization_id},
        "metric": {"metric_id": metric_id},
    }


def _alignment() -> dict:
    return {
        "alignment_kind": "identity",
        "sector_pairs": [{"reference_id": "cell-0", "target_id": "cell-0"}],
        "observable_pairs": [{"reference_id": "N", "target_id": "N"}],
    }


class CoordinateEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = CoordinateEvaluatorRegistry.load()
        cls.reference = load_json(REPORT_ROOT / "gridworld-f4-reference.sofreport.json")
        cls.target = load_json(REPORT_ROOT / "gridworld-f4-target.sofreport.json")

    def test_registry_resolves_only_declared_coordinate_ids(self) -> None:
        self.assertEqual(
            self.registry.resolve("operator.support.summary")["coordinate_family"],
            "operator",
        )
        self.assertEqual(
            self.registry.resolve("word.support.length-2.summary")[
                "value_schema_id"
            ],
            "word.support.v1",
        )
        with self.assertRaisesRegex(ContractError, "no registered coordinate evaluator"):
            self.registry.resolve("rank-collapse.summary")

    def test_word_support_uses_its_own_finding_and_claim(self) -> None:
        outcome = self.registry.evaluate(
            "word.support.length-2.summary",
            self.reference,
            self.target,
            _alignment(),
            _specification(),
        )
        self.assertEqual(outcome.reference.finding["finding_id"], "finding.word-length-two")
        self.assertEqual(outcome.reference.claim["claim_id"], "claim.word-length-two")
        self.assertEqual(outcome.result["comparison_state"], "ALIGNED")
        self.assertEqual(outcome.result["reference_value"]["pair_count"], 104)
        self.assertEqual(
            outcome.result["normalized_reference_value"]["pairs"][0],
            ["cell-0", "cell-2"],
        )
        self.assertEqual(
            outcome.result["pair_encoding"]["reference_input_form"],
            "zero_based_index",
        )

    def test_string_pairs_remain_label_normalized(self) -> None:
        reference = deepcopy(self.reference)
        target = deepcopy(self.reference)
        for report in (reference, target):
            finding = next(
                item
                for item in report["findings"]
                if item["finding_id"] == "finding.direct-support"
            )
            finding["value"] = {"pairs": [["cell-0", "cell-1"]], "pair_count": 1}
        outcome = self.registry.evaluate(
            "operator.support.summary",
            reference,
            target,
            _alignment(),
            _specification(),
        )
        self.assertEqual(
            outcome.result["normalized_reference_value"]["pairs"],
            [["cell-0", "cell-1"]],
        )
        self.assertEqual(
            outcome.result["pair_encoding"]["reference_input_form"], "label"
        )

    def test_integer_pairs_follow_each_reports_declared_label_order(self) -> None:
        reference = deepcopy(self.reference)
        target = deepcopy(self.reference)
        for report in (reference, target):
            finding = next(
                item
                for item in report["findings"]
                if item["finding_id"] == "finding.direct-support"
            )
            finding["value"] = {"pairs": [[0, 1]], "pair_count": 1}
        target_labels = target["alignment_readiness"]["sector_metadata"]["labels"]
        target_labels[0], target_labels[1] = target_labels[1], target_labels[0]
        outcome = self.registry.evaluate(
            "operator.support.summary",
            reference,
            target,
            _alignment(),
            _specification(),
        )
        self.assertEqual(outcome.result["comparison_state"], "MISMATCH")
        self.assertEqual(
            outcome.result["normalized_reference_value"]["pairs"],
            [["cell-0", "cell-1"]],
        )
        self.assertEqual(
            outcome.result["normalized_target_value"]["pairs"],
            [["cell-1", "cell-0"]],
        )

    def test_cross_module_claim_finding_binding_is_rejected(self) -> None:
        reference = deepcopy(self.reference)
        basic = next(item for item in reference["modules"] if item["module_id"] == "sof-basic")
        associative = next(
            item for item in reference["modules"] if item["module_id"] == "associative"
        )
        basic["claim_ids"].remove("claim.direct-support")
        associative["claim_ids"].append("claim.direct-support")
        with self.assertRaisesRegex(ContractError, "exactly one enabled module"):
            self.registry.evaluate(
                "operator.support.summary",
                reference,
                self.target,
                _alignment(),
                _specification(),
            )

    def test_unknown_and_out_of_range_pair_endpoints_are_rejected(self) -> None:
        for endpoint, message in (("cell-unknown", "unknown sector labels"), (25, "out-of-range sector index")):
            with self.subTest(endpoint=endpoint):
                reference = deepcopy(self.reference)
                finding = next(
                    item
                    for item in reference["findings"]
                    if item["finding_id"] == "finding.direct-support"
                )
                finding["value"] = {"pairs": [[0, endpoint]], "pair_count": 1}
                if isinstance(endpoint, str):
                    finding["value"]["pairs"] = [["cell-0", endpoint]]
                with self.assertRaisesRegex(ContractError, message):
                    self.registry.evaluate(
                        "operator.support.summary",
                        reference,
                        self.target,
                        _alignment(),
                        _specification(),
                    )

    def test_missing_finding_is_not_coerced_to_zero(self) -> None:
        reference = deepcopy(self.reference)
        reference["findings"] = [
            item
            for item in reference["findings"]
            if item["finding_id"] != "finding.word-length-two"
        ]
        outcome = self.registry.evaluate(
            "word.support.length-2.summary",
            reference,
            self.target,
            _alignment(),
            _specification(),
        )
        self.assertEqual(outcome.result["status"], "unavailable")
        self.assertEqual(outcome.result["comparison_state"], "NOT_DECLARED")
        self.assertIsNone(outcome.result["reference_value"])
        self.assertIsNone(outcome.result["metric_result"])

    def test_unsupported_normalization_and_metric_are_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "does not support normalization"):
            self.registry.evaluate(
                "operator.support.summary",
                self.reference,
                self.target,
                _alignment(),
                _specification(normalization_id="z-score"),
            )
        with self.assertRaisesRegex(ContractError, "does not support metric"):
            self.registry.evaluate(
                "word.support.length-2.summary",
                self.reference,
                self.target,
                _alignment(),
                _specification(metric_id="absolute-difference"),
            )

    def test_non_identity_alignment_is_not_silently_applied(self) -> None:
        alignment = _alignment()
        alignment["alignment_kind"] = "declared-map"
        with self.assertRaisesRegex(ContractError, "does not support alignment"):
            self.registry.evaluate(
                "word.support.length-2.summary",
                self.reference,
                self.target,
                alignment,
                _specification(),
            )


if __name__ == "__main__":
    unittest.main()
