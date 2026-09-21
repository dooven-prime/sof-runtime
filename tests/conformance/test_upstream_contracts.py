from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from sof_runtime.contracts import load_json, validate_contract
from sof_runtime.paths import COMPILER_CONTRACT_ROOT, PROJECT_ROOT, RUNTIME_CONTRACT_ROOT


FIXTURES = PROJECT_ROOT / "tests" / "conformance" / "fixtures" / "upstream-v1.0"


class UpstreamContractTests(unittest.TestCase):
    def test_all_json_schemas_are_well_formed(self) -> None:
        for schema_path in (PROJECT_ROOT / "contracts").rglob("*.schema.json"):
            Draft202012Validator.check_schema(load_json(schema_path))

    def test_vendored_digests_match_lock(self) -> None:
        lock = load_json(PROJECT_ROOT / "contracts" / "upstream.lock.json")
        entries = [
            entry
            for imported_snapshot in lock["imports"]
            for entry in imported_snapshot["entries"]
        ]
        self.assertEqual(len(entries), 25)
        for entry in entries:
            path = PROJECT_ROOT / entry["local_path"]
            self.assertTrue(path.is_file(), entry["local_path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                entry["sha256"],
            )

    def test_published_sofaction_is_in_immutable_inventory(self) -> None:
        lock = load_json(PROJECT_ROOT / "contracts" / "upstream.lock.json")
        promotion = lock["latest_promotion"]
        self.assertEqual(promotion["contract_family"], "SOFAction v2.1")
        self.assertEqual(promotion["release_tag"], "paper14-v2.1")
        self.assertEqual(promotion["publication_doi"], "10.5281/zenodo.22024158")
        entries = [
            entry
            for imported_snapshot in lock["imports"]
            for entry in imported_snapshot["entries"]
        ]
        action_entries = [
            entry
            for entry in entries
            if entry["role"] == "canonical_action_contract"
        ]
        self.assertEqual(len(action_entries), 4)
        self.assertEqual(
            {Path(entry["local_path"]).parent.name for entry in action_entries},
            {"v2.0", "v2.1"},
        )
        self.assertFalse(
            (PROJECT_ROOT / "contracts" / "upstream-candidate.lock.json").exists()
        )

    def test_upstream_lock_records_rime_repository_snapshot(self) -> None:
        lock = load_json(PROJECT_ROOT / "contracts" / "upstream.lock.json")
        snapshot = lock["snapshots"]["rime-lite-v2.1"]
        self.assertEqual(snapshot["release_tag"], "rime-lite-v2.1")
        self.assertEqual(
            snapshot["release_manifest_commit"],
            "69b33d60ac729eeff45dfe42e79e68197cdd7f68",
        )
        self.assertEqual(
            snapshot["release_content_commit"],
            "005e2453d508ba5e12136bf9005050ac72185ae5",
        )
        self.assertEqual(snapshot["publication_doi"], "10.5281/zenodo.22048358")

    def test_v2_1_family_ownership_and_six_file_delta(self) -> None:
        lock = load_json(PROJECT_ROOT / "contracts" / "upstream.lock.json")
        self.assertEqual(
            {
                name: value["publication_doi"]
                for name, value in lock["contract_families"].items()
            },
            {
                "SOFRS v2.1": "10.5281/zenodo.22006816",
                "SOFAUDIT v2.1": "10.5281/zenodo.22010220",
                "SOFAction v2.1": "10.5281/zenodo.22024158",
            },
        )
        imported = next(
            item for item in lock["imports"] if item["snapshot"] == "rime-lite-v2.1"
        )
        self.assertEqual(len(imported["entries"]), 6)
        self.assertEqual(
            {
                entry["local_path"]
                for entry in imported["entries"]
            },
            {
                "contracts/reporting/v2.1/sofrs.schema.json",
                "contracts/reporting/v2.1/validation-receipt.schema.json",
                "contracts/comparison/v2.1/sofaudit.schema.json",
                "contracts/comparison/v2.1/validation-receipt.schema.json",
                "contracts/action/v2.1/sofaction.schema.json",
                "contracts/action/v2.1/validation-receipt.schema.json",
            },
        )

    def test_upstream_input_fixtures_validate(self) -> None:
        pairs = (
            (
                "strict-associative-capabilities-v1.0.json",
                "capability-manifest.schema.json",
            ),
            ("strict-associative-ir-v1.0.json", "typed-sof-ir.schema.json"),
            (
                "basic-associative-closure-profile-v1.0.json",
                "report-profile.schema.json",
            ),
        )
        for fixture, schema in pairs:
            validate_contract(
                load_json(FIXTURES / fixture),
                COMPILER_CONTRACT_ROOT / schema,
                label=fixture,
            )

    def test_local_plugin_manifests_validate_and_bind_contracts(self) -> None:
        manifests = sorted((PROJECT_ROOT / "plugins").rglob("*.plugin.json"))
        self.assertGreaterEqual(len(manifests), 2)
        for manifest_path in manifests:
            manifest = load_json(manifest_path)
            validate_contract(
                manifest,
                RUNTIME_CONTRACT_ROOT / "plugin-manifest.schema.json",
                label=manifest_path.name,
            )
            for field in ("input_schema", "output_schema"):
                target = PROJECT_ROOT / manifest[field]
                self.assertTrue(target.is_file(), f"{manifest_path.name}: {field}")


if __name__ == "__main__":
    unittest.main()
