from __future__ import annotations

import copy
import unittest

from sof_runtime.carriers.rank_collapse import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    SUPPORTED_POLICY,
    RankCollapsePlugin,
    compute_rank_collapse,
)
from sof_runtime.contracts import ContractError, validate_contract
from sof_runtime.paths import RUNTIME_CONTRACT_ROOT
from sof_runtime.run_identity import compute_semantic_run_id, semantic_environment_for
from sof_runtime.workflow import CONTRACT_VERSIONS
from sof_runtime.validation.rank_collapse import validate_rank_collapse


CERNY4 = {
    "schema_id": "rime.automata.source.v1",
    "source_id": "cerny4",
    "states": ["0", "1", "2", "3"],
    "alphabet": ["a", "b"],
    "transitions": {
        "a": ["1", "2", "3", "0"],
        "b": ["0", "1", "2", "0"],
    },
}


class RankCollapseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.semantic_run_id = compute_semantic_run_id(
            source=CERNY4,
            plugin={"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
            carrier_kind="rank_collapse",
            contract_versions=CONTRACT_VERSIONS,
            policies=SUPPORTED_POLICY,
            semantic_environment=semantic_environment_for(RankCollapsePlugin()),
        )
        self.bundle = compute_rank_collapse(
            copy.deepcopy(CERNY4),
            semantic_run_id=self.semantic_run_id,
            execution_id="exec:test-cerny4",
            policies=SUPPORTED_POLICY,
            created_at="2026-08-04T00:00:00Z",
        )

    def test_cerny4_exact_reset_depth(self) -> None:
        rank_one = next(
            item["payload"]
            for item in self.bundle["findings"]
            if item["payload"]["rank_threshold"] == 1
        )
        self.assertEqual(rank_one["depth"], 9)
        self.assertEqual("".join(rank_one["shortest_word"]), "baaabaaab")
        self.assertEqual(rank_one["reachable_image_subset_count"], 15)

    def test_raw_findings_are_not_precertified(self) -> None:
        for item in self.bundle["findings"]:
            self.assertEqual(item["envelope"]["result_state"], "OBSERVED")
            self.assertEqual(
                item["envelope"]["claim_status"], "Computational Observation"
            )
            self.assertEqual(item["envelope"]["evidence_refs"], [])

    def test_finding_schema_rejects_illegal_status_pair(self) -> None:
        envelope = copy.deepcopy(self.bundle["findings"][0]["envelope"])
        envelope["result_state"] = "CERTIFIED"
        with self.assertRaises(ContractError):
            validate_contract(
                envelope,
                RUNTIME_CONTRACT_ROOT / "finding-envelope.schema.json",
                label="mutated finding envelope",
            )

    def test_independent_validation_passes(self) -> None:
        certificate = validate_rank_collapse(CERNY4, self.bundle)
        self.assertEqual(certificate["status"], "PASS")
        self.assertEqual(
            certificate["recomputed"]["first_hit_depth_by_rank_threshold"]["1"],
            9,
        )

    def test_permutation_only_automaton_is_exactly_non_synchronizing(self) -> None:
        source = {
            "schema_id": "rime.automata.source.v1",
            "source_id": "cycle3",
            "states": ["0", "1", "2"],
            "alphabet": ["a"],
            "transitions": {"a": ["1", "2", "0"]},
        }
        bundle = compute_rank_collapse(
            source,
            semantic_run_id=compute_semantic_run_id(
                source=source,
                plugin={"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
                carrier_kind="rank_collapse",
                contract_versions=CONTRACT_VERSIONS,
                policies=SUPPORTED_POLICY,
                semantic_environment=semantic_environment_for(RankCollapsePlugin()),
            ),
            execution_id="exec:test-cycle3",
            policies=SUPPORTED_POLICY,
            created_at="2026-08-04T00:00:00Z",
        )
        rank_one = bundle["findings"][0]["payload"]
        self.assertEqual(rank_one["kind"], "rank_threshold_unreachable")
        self.assertIsNone(rank_one["depth"])
        self.assertEqual(validate_rank_collapse(source, bundle)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
