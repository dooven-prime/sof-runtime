from __future__ import annotations

import copy
import unittest

from sof_runtime.adapters.automata import build_manifest
from sof_runtime.carriers.rank_collapse import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    SUPPORTED_POLICY,
    RankCollapsePlugin,
    compute_rank_collapse,
)
from sof_runtime.compiler import compile_documents
from sof_runtime.contracts import ContractError, load_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.run_identity import compute_semantic_run_id, semantic_environment_for
from sof_runtime.validation.rank_collapse import validate_rank_collapse
from sof_runtime.workflow import CONTRACT_VERSIONS


SOURCE = {
    "schema_id": "rime.automata.source.v1",
    "source_id": "cerny4",
    "states": ["0", "1", "2", "3"],
    "alphabet": ["a", "b"],
    "transitions": {
        "a": ["1", "2", "3", "0"],
        "b": ["0", "1", "2", "0"],
    },
}


class EvidenceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        semantic_run_id = compute_semantic_run_id(
            source=SOURCE,
            plugin={"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
            carrier_kind="rank_collapse",
            contract_versions=CONTRACT_VERSIONS,
            policies=SUPPORTED_POLICY,
            semantic_environment=semantic_environment_for(RankCollapsePlugin()),
        )
        self.bundle = compute_rank_collapse(
            copy.deepcopy(SOURCE),
            semantic_run_id=semantic_run_id,
            execution_id="exec:regression-cerny4",
            policies=SUPPORTED_POLICY,
            created_at="2026-08-04T00:00:00Z",
        )

    def test_mutated_depth_fails_independent_validation(self) -> None:
        mutated = copy.deepcopy(self.bundle)
        mutated["findings"][0]["payload"]["depth"] = 8
        self.assertEqual(validate_rank_collapse(SOURCE, mutated)["status"], "FAIL")

    def test_raw_plugin_cannot_claim_certificate_status(self) -> None:
        mutated = copy.deepcopy(self.bundle)
        mutated["findings"][0]["envelope"]["result_state"] = "CERTIFIED"
        mutated["findings"][0]["envelope"]["claim_status"] = "Computational Certificate"
        self.assertEqual(validate_rank_collapse(SOURCE, mutated)["status"], "FAIL")

    def test_adapter_does_not_manufacture_route_or_lie_capabilities(self) -> None:
        manifest = build_manifest(SOURCE)
        self.assertEqual(manifest["capabilities"]["route_carrier"]["availability"], "NOT_DECLARED")
        self.assertEqual(manifest["capabilities"]["lie_hall_carrier"]["availability"], "NOT_DECLARED")

    def test_compiler_rejects_failed_certificate(self) -> None:
        fixtures = PROJECT_ROOT / "tests" / "conformance" / "fixtures" / "upstream-v1.0"
        manifest = load_json(fixtures / "strict-associative-capabilities-v1.0.json")
        ir = load_json(fixtures / "strict-associative-ir-v1.0.json")
        profile = load_json(fixtures / "basic-associative-closure-profile-v1.0.json")
        for certificate in ir["certificates"]:
            certificate["status"] = "FAIL"
        with self.assertRaises(ContractError):
            compile_documents(manifest, ir, profile)


if __name__ == "__main__":
    unittest.main()
