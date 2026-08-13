from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
import socket
import tempfile
import unittest
from urllib.error import URLError
from unittest import mock

from tools.mcp_agent_harness import (
    MCPAgent,
    OpenAICompatibleProvider,
    _normal_milestones,
    _prepare_workspace,
    _spawn_local_server,
)
from sof_runtime.paths import PROJECT_ROOT


class MCPAgentHarnessTests(unittest.TestCase):
    def test_fixture_manifest_prepares_source_addressed_workspace(self) -> None:
        matrix = PROJECT_ROOT / "evaluations" / "mcp-agent-matrix-v1"
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            digests = _prepare_workspace(
                matrix,
                Path(directory),
                "agent-test",
                "agent-a",
                overwrite=False,
            )
            self.assertGreaterEqual(len(digests), 10)
            self.assertTrue((Path(directory) / "agent-test" / "case" / "reference" / "case.json").is_file())
            self.assertTrue((Path(directory) / "agent-test" / "comparison-profile.json").is_file())

    def test_milestone_projection_requires_canonical_realizations(self) -> None:
        events = [
            {"kind": "tool_discovery"},
            {"kind": "tool_call", "call": {"id": "reference", "name": "sof_realize", "arguments": {"case_directory": "case/reference"}}},
            {"kind": "tool_call", "call": {"id": "target", "name": "sof_realize", "arguments": {"case_directory": "case/target"}}},
            {"kind": "tool_result", "call_id": "reference", "tool": "sof_realize", "is_error": False, "result": '{"status":"succeeded","result":{"canonical_compilable":true}}'},
            {"kind": "tool_result", "call_id": "target", "tool": "sof_realize", "is_error": False, "result": '{"status":"succeeded","result":{"canonical_compilable":false}}'},
        ]
        self.assertNotIn("verify_canonical_compilation_eligibility", _normal_milestones(events))

    def test_milestone_projection_accepts_successful_realization_retry(self) -> None:
        events = [
            {"kind": "tool_call", "call": {"id": "reference", "name": "sof_realize", "arguments": {"case_directory": "case/reference"}}},
            {"kind": "tool_result", "call_id": "reference", "tool": "sof_realize", "is_error": False, "result": '{"status":"succeeded","result":{"canonical_compilable":true}}'},
            {"kind": "tool_call", "call": {"id": "target-failed", "name": "sof_realize", "arguments": {"case_directory": "case/target"}}},
            {"kind": "tool_result", "call_id": "target-failed", "tool": "sof_realize", "is_error": True, "result": "permission denied"},
            {"kind": "tool_call", "call": {"id": "target-retry", "name": "sof_realize", "arguments": {"case_directory": "case/target"}}},
            {"kind": "tool_result", "call_id": "target-retry", "tool": "sof_realize", "is_error": False, "result": '{"status":"succeeded","result":{"canonical_compilable":true}}'},
        ]
        self.assertIn(
            "verify_canonical_compilation_eligibility",
            _normal_milestones(events),
        )

    def test_report_milestones_follow_realization_paths_not_directory_names(self) -> None:
        events = [
            {"kind": "tool_call", "call": {"name": "sof_realize", "arguments": {"case_directory": "case/reference", "run_directory": "matrix/a/reference/custom"}}},
            {"kind": "tool_call", "call": {"name": "sof_realize", "arguments": {"case_directory": "case/target", "run_directory": "matrix/a/target/custom"}}},
            {"kind": "tool_call", "call": {"name": "sof_report", "arguments": {"realization_run_directory": "matrix/a/reference/custom"}}},
            {"kind": "tool_call", "call": {"name": "sof_report", "arguments": {"realization_run_directory": "matrix/a/target/custom"}}},
        ]
        milestones = _normal_milestones(events)
        self.assertIn("report_reference", milestones)
        self.assertIn("report_target", milestones)

    def test_provider_requires_https_and_does_not_follow_redirects(self) -> None:
        provider = OpenAICompatibleProvider(
            provider="test", model="test", base_url="http://127.0.0.1", api_key_env="TEST_KEY"
        )
        with mock.patch.dict("os.environ", {"TEST_KEY": "test-only"}):
            with self.assertRaisesRegex(RuntimeError, "HTTPS"):
                provider.complete([], [])

    def test_provider_retries_transport_failure_before_response(self) -> None:
        provider = OpenAICompatibleProvider(
            provider="test",
            model="test",
            base_url="https://example.invalid/v1",
            api_key_env="TEST_KEY",
        )
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'{"choices":[{"message":{"role":"assistant","content":"done"}}]}'
        )
        opener = mock.MagicMock()
        opener.open.side_effect = [URLError("transient"), response]
        with (
            mock.patch.dict("os.environ", {"TEST_KEY": "test-only"}),
            mock.patch("tools.mcp_agent_harness.build_opener", return_value=opener),
            mock.patch("tools.mcp_agent_harness.time.sleep"),
        ):
            result = provider.complete([], [])
        self.assertEqual(result["message"]["content"], "done")
        self.assertEqual(opener.open.call_count, 2)

    def test_provider_neutral_loop_executes_native_tool_calls(self) -> None:
        class Tool:
            name = "sof_get_contract"
            description = "read contract"
            input_schema = {
                "type": "object",
                "properties": {"contract_name": {"type": "string"}},
                "required": ["contract_name"],
            }

        class Listed:
            tools = []

        class Result:
            content = []
            structuredContent = {"status": "PASS"}
            isError = False

        class Session:
            async def list_tools(self):
                from tools.mcp_agent_harness import EXPECTED_MCP_TOOLS

                listed = Listed()
                listed.tools = []
                for name in sorted(EXPECTED_MCP_TOOLS):
                    tool = Tool()
                    tool.name = name
                    listed.tools.append(tool)
                return listed

            async def call_tool(self, name, arguments):
                self.called = (name, arguments)
                return Result()

        class Provider:
            provider = "fixture"
            model = "fixture"
            model_version = "1"

            def __init__(self):
                self.turn = 0

            def complete(self, messages, tools):
                self.turn += 1
                if self.turn == 1:
                    return {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "sof_get_contract",
                                    "arguments": '{"contract_name":"service-request.schema.json"}',
                                },
                            }],
                        },
                        "finish_reason": "tool_calls",
                        "usage": None,
                    }
                return {
                    "message": {"role": "assistant", "content": "done"},
                    "finish_reason": "stop",
                    "usage": None,
                }

        import asyncio

        with tempfile.TemporaryDirectory() as directory:
            session = Session()
            agent = MCPAgent(
                session,
                Provider(),
                Path(directory) / "transcript.json",
                3,
            )
            final = asyncio.run(
                agent.run([{"role": "user", "content": "inspect"}])
            )
            self.assertEqual(final, "done")
            self.assertEqual(
                session.called,
                (
                    "sof_get_contract",
                    {"contract_name": "service-request.schema.json"},
                ),
            )
            transcript = json.loads(
                (Path(directory) / "transcript.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [item["kind"] for item in transcript["events"]],
                [
                    "tool_discovery",
                    "model_response",
                    "tool_call",
                    "tool_result",
                    "model_response",
                    "final_response",
                ],
            )

    def test_named_provider_endpoint_cannot_be_overridden(self) -> None:
        from tools.mcp_agent_harness import _provider

        args = Namespace(
            provider="deepseek",
            base_url="https://example.invalid/v1",
            api_key_env=None,
            model="deepseek-chat",
            model_version=None,
            provider_timeout=10.0,
        )
        with self.assertRaisesRegex(SystemExit, "pinned endpoint"):
            _provider(args)

    def test_spawned_server_lifecycle_uses_current_source(self) -> None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        matrix = PROJECT_ROOT / "evaluations" / "mcp-agent-matrix-v1"
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            args = Namespace(
                workspace_root=Path(directory) / "workspace",
                mcp_url=f"http://127.0.0.1:{port}/mcp",
                output_dir=Path(directory) / "output",
                matrix_dir=matrix,
                agent_id="server-lifecycle",
                server_start_timeout=30.0,
            )
            with _spawn_local_server(args) as process:
                self.assertIsNone(process.poll())
            self.assertIsNotNone(process.poll())


if __name__ == "__main__":
    unittest.main()
