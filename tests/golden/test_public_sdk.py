from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sof_runtime.adapters.expert import load_expert_adapter, validate_declaration
from sof_runtime.cli.scaffold import init_adapter
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.sdk import (
    CapabilityDeclaration,
    ExpertAdapter,
    RealizationCandidate,
    SourceBundle,
)


class PublicSdkTests(unittest.TestCase):
    def test_public_sdk_names_are_importable(self) -> None:
        self.assertIsNotNone(ExpertAdapter)
        self.assertIsNotNone(SourceBundle)
        self.assertIsNotNone(RealizationCandidate)
        self.assertIsNotNone(CapabilityDeclaration)

    def test_init_adapter_generates_valid_declaration_scaffold(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            scaffold = init_adapter("network-routing", Path(directory))
            adapter = load_expert_adapter(scaffold / "adapter.py")
            validate_declaration(adapter.describe())
            self.assertTrue((scaffold / "fixtures" / "positive" / ".keep").is_file())
            self.assertIn("not runnable", (scaffold / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
