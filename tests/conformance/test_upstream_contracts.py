from __future__ import annotations

import hashlib
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
        for entry in lock["entries"]:
            path = PROJECT_ROOT / entry["local_path"]
            self.assertTrue(path.is_file(), entry["local_path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                entry["sha256"],
            )

    def test_published_sofaction_is_in_immutable_inventory(self) -> None:
        lock = load_json(PROJECT_ROOT / "contracts" / "upstream.lock.json")
        promotion = lock["latest_promotion"]
        self.assertEqual(promotion["contract_family"], "SOFAction v2")
        self.assertEqual(promotion["release_tag"], "paper14-v2.0")
        self.assertEqual(promotion["publication_doi"], "10.5281/zenodo.21880943")
        action_entries = [
            entry
            for entry in lock["entries"]
            if entry["role"] == "canonical_action_contract"
        ]
        self.assertEqual(len(action_entries), 2)
        self.assertTrue(
            all(
                entry["local_path"].startswith("contracts/action/v2.0/")
                for entry in action_entries
            )
        )
        self.assertFalse(
            (PROJECT_ROOT / "contracts" / "upstream-candidate.lock.json").exists()
        )

    def test_upstream_lock_records_rime_repository_snapshot(self) -> None:
        lock = load_json(PROJECT_ROOT / "contracts" / "upstream.lock.json")
        snapshot = lock["repository_snapshot"]
        self.assertEqual(snapshot["release_tag"], "rime-lite-v2.0")
        self.assertEqual(
            snapshot["source_snapshot_commit"],
            "28711f67aee03b02786c8e9f451156576c0f65ef",
        )
        self.assertEqual(
            snapshot["release_content_commit"],
            "de572e942a4e0f9ac5edc4180e997bfd1f069e8a",
        )
        self.assertEqual(snapshot["publication_doi"], "10.5281/zenodo.22004683")

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
