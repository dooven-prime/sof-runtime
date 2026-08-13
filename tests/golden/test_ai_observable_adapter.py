from __future__ import annotations

from copy import deepcopy
import importlib.util
import tempfile
import unittest
from pathlib import Path
import os
from unittest import mock
import urllib.error

from sof_runtime.api import RuntimeAPI
from sof_runtime.comparison.evaluators import CoordinateEvaluatorRegistry
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.paths import AI_OBSERVABLE_CONTRACT_ROOT, PROJECT_ROOT


EXAMPLE = PROJECT_ROOT / "examples" / "ai-observable-adapter"
PROFILE = (
    PROJECT_ROOT / "profiles" / "comparison" / "ai-observable-identity-v2.0.json"
)


def _load_adapter_module():
    spec = importlib.util.spec_from_file_location(
        "ai_observable_adapter_test", EXAMPLE / "adapter.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AIObservableAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter_module = _load_adapter_module()

    def test_source_contract_and_adapter_reject_arbitrary_https_endpoint(self) -> None:
        source = load_json(EXAMPLE / "deepseek" / "source" / "input.json")
        source["endpoint"] = "https://example.invalid/collect"
        with self.assertRaises(ContractError):
            validate_contract(
                source,
                AI_OBSERVABLE_CONTRACT_ROOT / "source.schema.json",
                label="AI observable source",
            )

        prior = os.environ.pop("DeepSeek_Service_Key", None)
        try:
            with self.assertRaisesRegex(ValueError, "not the pinned DeepSeek endpoint"):
                self.adapter_module._api_response(
                    source,
                    self.adapter_module.TASKS[0],
                    "bare",
                )
        finally:
            if prior is not None:
                os.environ["DeepSeek_Service_Key"] = prior

    def test_live_client_disables_redirects(self) -> None:
        source = load_json(EXAMPLE / "deepseek" / "source" / "input.json")
        opener = mock.Mock()
        opener.open.side_effect = urllib.error.HTTPError(
            source["endpoint"], 302, "Found", {}, None
        )
        with mock.patch.dict(os.environ, {"DeepSeek_Service_Key": "test-only"}), mock.patch.object(
            self.adapter_module.urllib.request,
            "build_opener",
            return_value=opener,
        ) as build_opener:
            with self.assertRaisesRegex(ValueError, "provider request failed: HTTPError"):
                self.adapter_module._api_response(
                    source,
                    self.adapter_module.TASKS[0],
                    "bare",
                )
        handler = build_opener.call_args.args[0]
        self.assertIsInstance(handler, self.adapter_module._NoRedirectHandler)
        self.assertIsNone(
            handler.redirect_request(None, None, 302, "Found", {}, "https://example.invalid/")
        )
        opener.open.assert_called_once()

    def test_semantic_score_requires_normalized_exact_answer(self) -> None:
        task = self.adapter_module.TASKS[1]
        self.assertTrue(
            self.adapter_module._score(task, "  Tuesday\n")["semantic.exact_answer"]
        )
        for response in (
            "The deadline is not Tuesday.",
            "Tuesday is unsupported.",
            "Probably Tuesday.",
        ):
            with self.subTest(response=response):
                self.assertFalse(
                    self.adapter_module._score(task, response)["semantic.exact_answer"]
                )

    def test_live_case_requires_declared_credential_without_retaining_it(self) -> None:
        prior = os.environ.pop("DeepSeek_Service_Key", None)
        try:
            with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
                with self.assertRaisesRegex(
                    ValueError, "required credential environment variable is unset"
                ):
                    RuntimeAPI().realize(EXAMPLE / "deepseek", directory)
        finally:
            if prior is not None:
                os.environ["DeepSeek_Service_Key"] = prior

    def test_fixture_reports_and_comparison_preserve_analogue_boundary(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            runtime = RuntimeAPI()
            root = Path(directory)
            _, reference = runtime.realize_and_report(
                EXAMPLE / "reference", root / "reference"
            )
            _, target = runtime.realize_and_report(
                EXAMPLE / "target", root / "target"
            )
            comparison = runtime.compare(
                reference,
                target,
                alignment=EXAMPLE / "comparison" / "alignment.json",
                profile=PROFILE,
                out_dir=root / "comparison",
            )

            for report in (reference.payload, target.payload):
                self.assertEqual(report["record_kind"], "diagnostic_analogue")
                self.assertEqual(
                    report["alignment_readiness"]["sector_metadata"]["status"],
                    "NOT_APPLICABLE",
                )
                self.assertEqual(
                    report["alignment_readiness"]["observable_metadata"]["status"],
                    "PRESENT",
                )
                self.assertEqual(report["claims"][0]["claim_status"], "Computational Observation")
                self.assertFalse(report["findings"][0]["value"]["raw_response_retention"])
                self.assertNotIn("response_text", str(report))
                self.assertNotIn("candidate_action_set", str(report))
                statistics = report["findings"][0]["value"]["coordinate_statistics"]
                self.assertEqual(
                    set(statistics),
                    set(report["findings"][0]["value"]["observable_values"]),
                )
                for summary in statistics.values():
                    self.assertEqual(summary["applicable_count"], 1)
                    self.assertIn(summary["success_count"], {0, 1})
                    self.assertEqual(
                        summary["rate_percent"],
                        100.0 * summary["success_count"],
                    )

            audit = comparison.payload
            self.assertEqual(audit["regime"], "analogue_vs_analogue")
            self.assertIsNone(audit["alignment"]["sector_alignment"])
            coordinate = audit["coordinates"]["ai.observable.descriptor"]
            self.assertEqual(coordinate["comparison_state"], "MISMATCH")
            self.assertEqual(coordinate["claim_status"], "Computational Observation")
            self.assertEqual(
                coordinate["value"]["metric_result"],
                {
                    "metric_id": "coordinatewise-record",
                    "status": "computed",
                    "value": 4,
                },
            )
            self.assertEqual(
                coordinate["value"]["delta"]["repair_probe_result.json_contract"],
                100.0,
            )
            serialized = str(audit).lower()
            self.assertNotIn("authorization_state", serialized)
            self.assertNotIn("candidate_action_set", serialized)
            artifact_roles = {item["role"] for item in audit["source_artifacts"]}
            self.assertIn("coordinate-evaluator-registry", artifact_roles)
            self.assertIn("coordinate-evaluator-implementation", artifact_roles)
            self.assertIn(
                "coordinate-evaluation-result-ai.observable.descriptor",
                artifact_roles,
            )

    def test_descriptor_identity_does_not_infer_missing_keys(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            runtime = RuntimeAPI()
            _, reference = runtime.realize_and_report(
                EXAMPLE / "reference", directory
            )
            report = reference.payload
            target = deepcopy(report)
            target["findings"][0]["value"]["observable_values"].pop(
                "repair_probe_result.json_contract"
            )
            profile = load_json(PROFILE)["comparison_specification"]
            alignment = load_json(EXAMPLE / "comparison" / "alignment.json")
            with self.assertRaisesRegex(ContractError, "explicit identity"):
                CoordinateEvaluatorRegistry.load().evaluate(
                    "ai.observable.descriptor",
                    report,
                    target,
                    alignment,
                    profile,
                )


if __name__ == "__main__":
    unittest.main()
