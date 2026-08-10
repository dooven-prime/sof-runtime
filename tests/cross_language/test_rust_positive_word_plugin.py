from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes
from sof_runtime.carriers.positive_word_support import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    PositiveWordSupportPlugin,
)
from sof_runtime.contracts import ContractError, load_json, loads_json, validate_contract
from sof_runtime.paths import PROJECT_ROOT, RUNTIME_CONTRACT_ROOT
from sof_runtime.plugins import ExternalPluginRunner, PluginExecutionError
from sof_runtime.run_identity import semantic_environment_for
from sof_runtime.workflow_positive_word import (
    build_positive_word_request,
    run_positive_word_support,
    validate_positive_word_response,
)


CRATE_ROOT = PROJECT_ROOT / "plugins" / "rust" / "positive-word-support"
MANIFEST_PATH = CRATE_ROOT / "Cargo.toml"
PLUGIN_MANIFEST_PATH = (
    PROJECT_ROOT / "plugins" / "rust" / "positive-word-support.plugin.json"
)
FIXED_CREATED_AT = "2026-08-04T00:00:00Z"
FIXED_EXECUTION_ID = "exec:rust-python-positive-word-parity"


def _cargo_path() -> Path | None:
    configured = os.environ.get("CARGO")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path(shutil.which("cargo")) if shutil.which("cargo") else None,
        Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo"),
    ]
    return next((path for path in candidates if path and path.is_file()), None)


def _python_canonicalize(raw: bytes) -> bytes:
    return canonical_json_bytes(loads_json(raw.decode("utf-8")))


class RustPositiveWordPluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cargo = _cargo_path()
        if cargo is None:
            raise unittest.SkipTest("Cargo is unavailable; set CARGO to run Rust conformance")
        subprocess.run(
            [
                str(cargo),
                "build",
                "--release",
                "--locked",
                "--manifest-path",
                str(MANIFEST_PATH),
            ],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )
        suffix = ".exe" if os.name == "nt" else ""
        cls.binary = CRATE_ROOT / "target" / "release" / f"sof-positive-word-support{suffix}"
        if not cls.binary.is_file():
            raise RuntimeError(f"Rust plugin binary was not produced: {cls.binary}")
        cls.source = load_json(PROJECT_ROOT / "examples" / "markov" / "cycle4-lazy.json")

    def rust_runner(self, *extra_arguments: str) -> ExternalPluginRunner:
        return ExternalPluginRunner(
            [str(self.binary), *extra_arguments],
            plugin_id=PLUGIN_ID,
            plugin_version=PLUGIN_VERSION,
            carrier_kind="positive_word_support",
            implementation_language="rust",
            semantic_environment=semantic_environment_for(PositiveWordSupportPlugin()),
        )

    def rust_mode(self, mode: str, raw: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(self.binary), mode],
            input=raw,
            capture_output=True,
            cwd=PROJECT_ROOT,
        )

    def test_manifest_is_a_valid_external_plugin_declaration(self) -> None:
        validate_contract(
            load_json(PLUGIN_MANIFEST_PATH),
            RUNTIME_CONTRACT_ROOT / "plugin-manifest.schema.json",
            label="Rust plugin manifest",
        )

    def test_canonical_json_bytes_and_sha256_match_python(self) -> None:
        fixtures = [
            {"z": [3, True, None], "a": "caf\u00e9"},
            {
                "controls": "\b\f\n\r\t\u0001",
                "slashes": "</script>/\\\"",
                "astral": "\U0001f600",
                "\ue000": "private-use key",
            },
        ]
        for payload in fixtures:
            with self.subTest(payload=payload):
                expected = canonical_json_bytes(payload)
                canonicalized = self.rust_mode("--canonicalize", expected)
                self.assertEqual(
                    canonicalized.returncode,
                    0,
                    canonicalized.stderr.decode(),
                )
                self.assertEqual(canonicalized.stdout, expected)

        expected = canonical_json_bytes(fixtures[0])
        self.assertEqual(expected, b'{"a":"caf\xc3\xa9","z":[3,true,null]}')

        digest = self.rust_mode("--canonical-sha256", expected)
        self.assertEqual(digest.returncode, 0, digest.stderr.decode())
        self.assertEqual(digest.stdout.decode("ascii"), sha256_bytes(expected))
        self.assertEqual(
            digest.stdout.decode("ascii"),
            "9ebb0a5694eab1694b3f7a388c44f3e6f3d20212ad3b3c6c999ca380814a55db",
        )

    def test_both_implementations_reject_noncanonical_values(self) -> None:
        rejected = {
            "non_nfc": b'{"value":"e\\u0301"}',
            "duplicate_key": b'{"value":1,"value":2}',
            "float": b'{"value":1.25}',
            "out_of_range_integer": b'{"value":9223372036854775808}',
            "negative_zero": b'{"value":-0}',
        }
        for label, raw in rejected.items():
            with self.subTest(label=label):
                with self.assertRaises((ContractError, ValueError)):
                    _python_canonicalize(raw)
                result = self.rust_mode("--canonicalize", raw)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
                self.assertTrue(result.stderr.startswith(b"sof-rust-positive-word:"))

    def test_rust_recomputes_semantic_run_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as run_directory:
            runner = self.rust_runner()
            request = build_positive_word_request(
                self.source,
                run_directory,
                plugin=runner,
                execution_id=FIXED_EXECUTION_ID,
                created_at=FIXED_CREATED_AT,
            )
            request["semantic_run_id"] = "semrun:sha256:" + "0" * 64
            with self.assertRaises(PluginExecutionError) as raised:
                runner.compute(request)
            self.assertIn(b"semantic run identity mismatch", raised.exception.stderr)

    def test_python_and_rust_emit_identical_bundle_bytes_and_digest(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as python_directory:
            python_response = run_positive_word_support(
                self.source,
                python_directory,
                execution_id=FIXED_EXECUTION_ID,
                created_at=FIXED_CREATED_AT,
            )
            python_certificate = validate_positive_word_response(
                Path(python_directory) / "run-response.json"
            )
            python_outputs = {item["kind"]: item for item in python_response["outputs"]}
            python_bundle = load_json(
                PROJECT_ROOT
                / python_outputs["result_bundle"]["artifact_ref"]["uri"]
            )

        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as rust_directory:
            rust_response = run_positive_word_support(
                self.source,
                rust_directory,
                plugin=self.rust_runner(),
                execution_id=FIXED_EXECUTION_ID,
                created_at=FIXED_CREATED_AT,
            )
            rust_certificate = validate_positive_word_response(
                Path(rust_directory) / "run-response.json"
            )
            rust_outputs = {item["kind"]: item for item in rust_response["outputs"]}
            rust_bundle = load_json(
                PROJECT_ROOT / rust_outputs["result_bundle"]["artifact_ref"]["uri"]
            )

            artifact_root = (PROJECT_ROOT / rust_response["artifact_directory"]).resolve()
            for item in rust_response["outputs"]:
                artifact_path = (PROJECT_ROOT / item["artifact_ref"]["uri"]).resolve()
                artifact_path.relative_to(artifact_root)

        self.assertEqual(python_response["status"], "SUCCEEDED")
        self.assertEqual(rust_response["status"], "SUCCEEDED")
        self.assertEqual(python_response["semantic_run_id"], rust_response["semantic_run_id"])
        self.assertEqual(canonical_json_bytes(python_bundle), canonical_json_bytes(rust_bundle))
        self.assertEqual(
            python_outputs["result_bundle"]["artifact_ref"]["sha256"],
            rust_outputs["result_bundle"]["artifact_ref"]["sha256"],
        )
        self.assertEqual(
            python_bundle["findings"][0]["payload"],
            rust_bundle["findings"][0]["payload"],
        )
        self.assertEqual(
            python_certificate["validator_independence"],
            {
                "implementation_relation": "separate_algorithm",
                "language_relation": "same_language",
                "runtime_relation": "same_process",
                "input_source": "canonical_source_artifacts",
                "producer_cache_used": False,
            },
        )
        self.assertEqual(
            rust_certificate["validator_independence"],
            {
                "implementation_relation": "separate_algorithm",
                "language_relation": "different_language",
                "runtime_relation": "separate_process",
                "input_source": "canonical_source_artifacts",
                "producer_cache_used": False,
            },
        )
        self.assertEqual(
            rust_certificate["recomputed"],
            {
                "reachable_pair_count": 12,
                "unreachable_pair_count": 0,
                "maximum_first_hit_depth": 3,
                "errors": [],
            },
        )

    def test_nonzero_exit_becomes_digest_bound_failed_execution(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as run_directory:
            response = run_positive_word_support(
                self.source,
                run_directory,
                plugin=self.rust_runner("--fail"),
                execution_id="exec:rust-fixed-failure",
                created_at=FIXED_CREATED_AT,
            )
        expected_stderr = b"sof-rust-positive-word: deterministic failure fixture\n"
        self.assertEqual(response["status"], "FAILED_EXECUTION")
        self.assertEqual(response["failure"]["stage"], "PLUGIN_EXECUTION")
        self.assertEqual(response["failure"]["stderr_sha256"], sha256_bytes(expected_stderr))
        self.assertFalse(response["validator"]["ran"])
        self.assertEqual(response["failure"]["usable_finding_count"], 0)


if __name__ == "__main__":
    unittest.main()
