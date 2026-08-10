from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.workflow_positive_word import (
    run_positive_word_support,
    validate_positive_word_promotion,
    validate_positive_word_response,
)


class MarkovVerticalSliceTests(unittest.TestCase):
    def test_cycle4_source_to_validated_extension_artifacts(self) -> None:
        source = load_json(PROJECT_ROOT / "examples" / "markov" / "cycle4-lazy.json")
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_positive_word_support(
                source,
                directory,
                execution_id="exec:golden-cycle4",
                created_at="2026-08-04T00:00:00Z",
            )
            certificate = validate_positive_word_response(
                Path(directory) / "run-response.json"
            )
            self.assertEqual(response["status"], "SUCCEEDED")
            self.assertEqual(response["carrier_kind"], "positive_word_support")
            self.assertEqual(certificate["status"], "PASS")
            self.assertEqual(
                certificate["applicability"],
                {
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
            )
            self.assertEqual(certificate["recomputed"]["reachable_pair_count"], 12)
            self.assertEqual(certificate["recomputed"]["maximum_first_hit_depth"], 3)
            self.assertEqual(
                certificate["validator_independence"]["implementation_relation"],
                "separate_algorithm",
            )
            outputs = {item["kind"]: item for item in response["outputs"]}
            bundle = load_json(
                PROJECT_ROOT / outputs["result_bundle"]["artifact_ref"]["uri"]
            )
            envelope = bundle["findings"][0]["envelope"]
            self.assertEqual(envelope["claim_status"], "Computational Observation")
            self.assertEqual(
                envelope["carrier_ref"], "extension:positive-word-support:v1"
            )
            promotion = validate_positive_word_promotion(
                Path(directory) / "promotion-package.json",
                Path(directory) / "run-response.json",
            )
            self.assertEqual(promotion["promotion_state"], "CANDIDATE")
            self.assertIn(
                "Positive-word support first hit is not rank collapse or route depth.",
                promotion["negative_evidence"]["separation_statements"],
            )


if __name__ == "__main__":
    unittest.main()
