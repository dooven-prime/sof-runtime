from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.workflow_positive_word import (
    run_positive_word_support,
    validate_positive_word_response,
)


class MarkovVerticalSliceFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = load_json(
            PROJECT_ROOT / "examples" / "markov" / "cycle4-lazy.json"
        )

    def test_invalid_row_sum_produces_structured_failure(self) -> None:
        source = copy.deepcopy(self.source)
        source["transition_numerators"][0][0] = 2
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_positive_word_support(
                source,
                directory,
                execution_id="exec:markov-invalid",
                created_at="2026-08-04T00:00:00Z",
            )
            checked = validate_positive_word_response(
                Path(directory) / "run-response.json"
            )
            self.assertEqual(response["status"], "FAILED_VALIDATION")
            self.assertEqual(response["failure"]["stage"], "INPUT_VALIDATION")
            self.assertEqual(checked, response)

    def test_cutoff_policy_is_unsupported_and_changes_semantic_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as exact_dir:
            exact = run_positive_word_support(
                self.source,
                exact_dir,
                execution_id="exec:markov-exact",
                created_at="2026-08-04T00:00:00Z",
            )
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as cutoff_dir:
            cutoff = run_positive_word_support(
                self.source,
                cutoff_dir,
                policies={
                    "positive_word": {
                        "mode": "cutoff",
                        "pair_scope": "off_diagonal",
                        "max_depth": 2,
                    }
                },
                execution_id="exec:markov-cutoff",
                created_at="2026-08-04T00:00:00Z",
            )
            validate_positive_word_response(Path(cutoff_dir) / "run-response.json")
        self.assertNotEqual(exact["semantic_run_id"], cutoff["semantic_run_id"])
        self.assertEqual(cutoff["status"], "UNSUPPORTED")
        self.assertEqual(cutoff["failure"]["stage"], "POLICY_ADMISSION")

    def test_repeated_input_has_stable_semantic_identity(self) -> None:
        responses = []
        for suffix in ("a", "b"):
            with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
                responses.append(
                    run_positive_word_support(
                        self.source,
                        directory,
                        execution_id=f"exec:markov-repeat-{suffix}",
                        created_at="2026-08-04T00:00:00Z",
                    )
                )
        self.assertEqual(responses[0]["semantic_run_id"], responses[1]["semantic_run_id"])
        self.assertNotEqual(responses[0]["execution_id"], responses[1]["execution_id"])

    def test_artifact_tampering_is_detected_by_shared_bus(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_positive_word_support(
                self.source,
                directory,
                execution_id="exec:markov-tamper",
                created_at="2026-08-04T00:00:00Z",
            )
            bundle_ref = next(
                item["artifact_ref"]
                for item in response["outputs"]
                if item["kind"] == "result_bundle"
            )
            (PROJECT_ROOT / bundle_ref["uri"]).write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "artifact verification failed"):
                validate_positive_word_response(Path(directory) / "run-response.json")


if __name__ == "__main__":
    unittest.main()
