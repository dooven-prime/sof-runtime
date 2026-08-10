from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from sof_runtime.carriers.rank_collapse import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    RankCollapsePlugin,
)
from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.plugins import ExternalPluginRunner, PluginExecutionError
from sof_runtime.run_identity import semantic_environment_for
from sof_runtime.workflow import (
    build_rank_collapse_request,
    run_rank_collapse,
    validate_run_response,
)


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


def runner(script: Path) -> ExternalPluginRunner:
    return ExternalPluginRunner(
        [sys.executable, str(script)],
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        carrier_kind="rank_collapse",
        implementation_language="python",
        semantic_environment=semantic_environment_for(RankCollapsePlugin()),
    )


class ExternalPluginProtocolTests(unittest.TestCase):
    def test_json_stdin_stdout_carries_payload_not_run_response(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as run_directory:
            with tempfile.TemporaryDirectory() as script_directory:
                script = Path(script_directory) / "plugin.py"
                script.write_text(
                    "import json, sys\n"
                    "request = json.load(sys.stdin)\n"
                    "json.dump({'semantic_run_id': request['semantic_run_id'], "
                    "'execution_id': request['execution_id'], 'payload': 'fixture'}, sys.stdout)\n",
                    encoding="utf-8",
                )
                request = build_rank_collapse_request(
                    SOURCE,
                    run_directory,
                    plugin=runner(script),
                    execution_id="exec:external-protocol",
                    created_at="2026-08-04T00:00:00Z",
                )
                payload = runner(script).compute(request)
                self.assertEqual(payload["payload"], "fixture")
                self.assertNotIn("status", payload)

    def test_payload_must_bind_to_request(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as run_directory:
            with tempfile.TemporaryDirectory() as script_directory:
                script = Path(script_directory) / "wrong_run.py"
                script.write_text(
                    "import json, sys\n"
                    "request = json.load(sys.stdin)\n"
                    "json.dump({'semantic_run_id': request['semantic_run_id'], "
                    "'execution_id': 'exec:wrong'}, sys.stdout)\n",
                    encoding="utf-8",
                )
                external = runner(script)
                request = build_rank_collapse_request(
                    SOURCE,
                    run_directory,
                    plugin=external,
                    execution_id="exec:expected",
                    created_at="2026-08-04T00:00:00Z",
                )
                with self.assertRaises(PluginExecutionError):
                    external.compute(request)

    def test_external_executable_matches_in_process_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as script_directory:
            script = Path(script_directory) / "rank_collapse_external.py"
            script.write_text(
                textwrap.dedent(
                    """
                    import json
                    import sys
                    from sof_runtime.carriers.rank_collapse import compute_rank_collapse

                    request = json.load(sys.stdin)
                    bundle = compute_rank_collapse(
                        request["source"],
                        semantic_run_id=request["semantic_run_id"],
                        execution_id=request["execution_id"],
                        policies=request["policies"],
                        created_at=request["created_at"],
                    )
                    json.dump(bundle, sys.stdout)
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as python_dir:
                python_response = run_rank_collapse(
                    SOURCE,
                    python_dir,
                    execution_id="exec:python-parity",
                    created_at="2026-08-04T00:00:00Z",
                )
                python_certificate = validate_run_response(
                    Path(python_dir) / "run-response.json"
                )
                python_outputs = {item["kind"]: item for item in python_response["outputs"]}
                python_bundle = load_json(
                    PROJECT_ROOT / python_outputs["result_bundle"]["artifact_ref"]["uri"]
                )

            with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as external_dir:
                external_response = run_rank_collapse(
                    SOURCE,
                    external_dir,
                    plugin=runner(script),
                    execution_id="exec:external-parity",
                    created_at="2026-08-04T00:00:00Z",
                )
                external_certificate = validate_run_response(
                    Path(external_dir) / "run-response.json"
                )
                external_outputs = {item["kind"]: item for item in external_response["outputs"]}
                external_bundle = load_json(
                    PROJECT_ROOT / external_outputs["result_bundle"]["artifact_ref"]["uri"]
                )

            self.assertEqual(python_response["semantic_run_id"], external_response["semantic_run_id"])
            self.assertEqual(
                python_certificate["validator_independence"]["runtime_relation"],
                "same_process",
            )
            self.assertEqual(
                external_certificate["validator_independence"]["runtime_relation"],
                "separate_process",
            )
            self.assertEqual(python_bundle["image_layers"], external_bundle["image_layers"])
            self.assertEqual(
                [item["payload"] for item in python_bundle["findings"]],
                [item["payload"] for item in external_bundle["findings"]],
            )


if __name__ == "__main__":
    unittest.main()
