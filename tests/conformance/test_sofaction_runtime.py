from __future__ import annotations

import json
import unittest
from pathlib import Path

from sof_runtime.action import validate_action
from sof_runtime.contracts import ContractError


ROOT = Path(__file__).resolve().parent / "fixtures" / "sofaction"
ACTION = ROOT / "gridworld_f4_native.sofaction"


class SofactionRuntimeTests(unittest.TestCase):
    def test_native_fixture_replays_and_validates(self) -> None:
        payload = validate_action(ACTION, repository_root=ROOT)
        self.assertEqual(payload["record_class"], "decision_trace_certificate")
        self.assertEqual(
            {item["disposition"] for item in payload["candidate_action_set"]["actions"]},
            {"Investigate", "RequestEvidence"},
        )

    def test_projection_rewrite_is_rejected(self) -> None:
        payload = json.loads(ACTION.read_text(encoding="utf-8"))
        payload["audit_projection"]["signature"].pop("operator.support.summary")
        hostile = ROOT / "hostile-projection.sofaction"
        hostile.write_text(json.dumps(payload), encoding="utf-8")
        try:
            with self.assertRaises(ContractError):
                validate_action(hostile, repository_root=ROOT)
        finally:
            hostile.unlink(missing_ok=True)

    def test_arbitrary_predicate_is_rejected_by_schema(self) -> None:
        payload = json.loads(ACTION.read_text(encoding="utf-8"))
        payload["policy_profile"]["rules"][0]["when"] = {
            "predicate_version": "1.0",
            "op": "trust_me",
            "value": "high risk",
        }
        hostile = ROOT / "hostile-predicate.sofaction"
        hostile.write_text(json.dumps(payload), encoding="utf-8")
        try:
            with self.assertRaises(ContractError):
                validate_action(hostile, repository_root=ROOT)
        finally:
            hostile.unlink(missing_ok=True)

    def test_action_set_deletion_is_rejected(self) -> None:
        payload = json.loads(ACTION.read_text(encoding="utf-8"))
        payload["candidate_action_set"]["actions"].pop()
        payload["candidate_action_set"]["count"] = 1
        hostile = ROOT / "hostile-candidate-set.sofaction"
        hostile.write_text(json.dumps(payload), encoding="utf-8")
        try:
            with self.assertRaises(ContractError):
                validate_action(hostile, repository_root=ROOT)
        finally:
            hostile.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
