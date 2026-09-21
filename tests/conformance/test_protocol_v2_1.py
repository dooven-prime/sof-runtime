from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from sof_runtime.action import (
    migrate_action,
    validate_action,
    validate_action_validation_receipt,
)
from sof_runtime.action.producer_v2 import build_interpretation as build_v2_action
from sof_runtime.api import RuntimeAPI
from sof_runtime.comparison import (
    migrate_audit,
    validate_audit,
    validate_audit_validation_receipt,
)
from sof_runtime.comparison.validation_v2 import (
    build_audit_validation_receipt as build_v2_audit_receipt,
)
from sof_runtime.contracts import ContractError, load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.reporting import migrate_report, validate_receipt, validate_report

from . import test_sofaudit_candidate as sofaudit_fixture


CASE = PROJECT_ROOT / "examples" / "external-adapter-finite-state"


class ProtocolV21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs")
        cls.root = Path(cls._temporary.name)
        old_audit_path, old_audit = sofaudit_fixture.SofauditCandidateConformanceTests()._build(
            cls.root / "v2"
        )
        cls.old_audit_path = old_audit_path
        cls.old_audit_receipt_path = write_json(
            cls.root / "v2" / "strict-identity.validation-receipt.json",
            build_v2_audit_receipt(old_audit_path),
        )

        migrated_reports: dict[str, dict[str, str]] = {}
        for side in ("reference", "target"):
            source = old_audit["source_reports"][side]
            migrated_reports[side] = migrate_report(
                PROJECT_ROOT / source["artifact"]["uri"],
                PROJECT_ROOT / source["validation_receipt"]["uri"],
                cls.root / "v2.1" / "reports" / side,
            )
        cls.migrated_reports = migrated_reports
        cls.migrated_audit = migrate_audit(
            old_audit_path,
            cls.old_audit_receipt_path,
            migrated_reports["reference"]["report"],
            migrated_reports["reference"]["validation_receipt"],
            migrated_reports["target"]["report"],
            migrated_reports["target"]["validation_receipt"],
            cls.root / "v2.1" / "audit",
        )

        context = deepcopy(load_json(CASE / "action" / "context.json"))
        context["scope"]["audit_id"] = old_audit["audit_id"]
        context_path = write_json(cls.root / "v2" / "action-context.json", context)
        cls.old_action = build_v2_action(
            old_audit_path,
            cls.old_audit_receipt_path,
            context_path,
            CASE / "action" / "policy.json",
            cls.root / "v2" / "action",
        )
        cls.migrated_action = migrate_action(
            cls.old_action["action"],
            cls.old_action["receipt"],
            cls.migrated_audit["audit"],
            cls.migrated_audit["receipt"],
            cls.root / "v2.1" / "action",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def test_explicit_migration_chain_has_new_receipts(self) -> None:
        runtime = RuntimeAPI()
        self.assertTrue(callable(runtime.migrate_report))
        self.assertTrue(callable(runtime.migrate_comparison))
        self.assertTrue(callable(runtime.migrate_interpretation))
        for migrated in self.migrated_reports.values():
            report = validate_report(migrated["report"])
            receipt = validate_receipt(migrated["validation_receipt"])
            self.assertEqual(report["sofrs_version"], "2.1")
            self.assertEqual(receipt["generation"]["kind"], "migration")
        audit = validate_audit(self.migrated_audit["audit"])
        audit_receipt = validate_audit_validation_receipt(
            self.migrated_audit["receipt"]
        )
        action = validate_action(self.migrated_action["action"])
        action_receipt = validate_action_validation_receipt(
            self.migrated_action["receipt"]
        )
        self.assertEqual(audit["sofaudit_version"], "2.1")
        self.assertEqual(action["sofaction_version"], "2.1")
        self.assertEqual(audit_receipt["generation"]["kind"], "migration")
        self.assertEqual(action_receipt["generation"]["kind"], "migration")

    def test_migration_is_an_exact_boundary_projection(self) -> None:
        report_path = Path(self.migrated_reports["reference"]["report"])
        hostile = deepcopy(load_json(report_path))
        hostile["system"] = "hostile semantic rewrite"
        hostile_path = write_json(
            self.root / "hostile-migrated-report.json", hostile
        )
        with self.assertRaisesRegex(ContractError, "exact v2.0 boundary projection"):
            validate_report(hostile_path)

    def test_v2_1_boundaries_and_receipt_closure_are_hostile(self) -> None:
        action = deepcopy(load_json(self.migrated_action["action"]))
        action["execution_boundary"]["execution_semantics"] = "AUTHORIZED"
        hostile_action = write_json(self.root / "hostile-action.json", action)
        with self.assertRaises(ContractError):
            validate_action(hostile_action)

        receipt = deepcopy(load_json(self.migrated_audit["receipt"]))
        receipt["artifact_closure"]["artifact_count"] -= 1
        hostile_receipt = write_json(self.root / "hostile-audit-receipt.json", receipt)
        with self.assertRaisesRegex(ContractError, "artifact count"):
            validate_audit_validation_receipt(hostile_receipt)


if __name__ == "__main__":
    unittest.main()
