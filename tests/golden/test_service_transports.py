from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from sof_runtime.api import RuntimeAPI
from sof_runtime.artifacts import sha256_file
from sof_runtime.contracts import load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.explain import explain_run
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.service import ServiceApplication, ServiceError
from sof_runtime.transports.http import create_app
from sof_runtime.transports.mcp import create_server


CASE = PROJECT_ROOT / "examples" / "external-adapter-finite-state"
COMPARISON_PROFILE = (
    PROJECT_ROOT
    / "profiles"
    / "comparison"
    / "external-adapter-identity-v2.0.json"
)


def request(request_id: str, run_directory: str) -> dict:
    return {
        "contract_id": "sof-runtime.service-request.v1",
        "request_id": request_id,
        "workspace_id": "transport-fixture",
        "operation": "realize",
        "input": {
            "case_directory": "case",
            "run_directory": run_directory,
        },
    }


def artifact_digest(response: dict, role: str) -> str:
    return next(
        item["sha256"]
        for item in response["artifacts"]
        if item["artifact_id"].startswith(f"{role}:")
    )


class ServiceTransportTests(unittest.TestCase):
    @staticmethod
    def assert_no_absolute_server_paths(value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                ServiceTransportTests.assert_no_absolute_server_paths(item)
        elif isinstance(value, list):
            for item in value:
                ServiceTransportTests.assert_no_absolute_server_paths(item)
        elif isinstance(value, str) and "://" not in value:
            assert not Path(value).is_absolute(), value

    def test_http_openapi_schema_is_generated(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            app = create_app(workspace_root=directory)
            schema = app.openapi()
            self.assertEqual(schema["info"]["title"], "SOF Runtime Service")
            self.assertIn("/v1/realizations", schema["paths"])

            response = TestClient(app).get("/openapi.json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), schema)

    def test_http_mcp_discovery_is_self_describing(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            app = create_app(workspace_root=directory)
            headers = {"Accept": "application/json, text/event-stream"}
            with TestClient(
                app,
                base_url="http://127.0.0.1:8080",
            ) as client:
                initialized = client.post(
                    "/mcp",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "black-box", "version": "1"},
                        },
                    },
                )
                self.assertEqual(initialized.status_code, 200)
                instructions = initialized.json()["result"]["instructions"]
                self.assertIn("Realization -> Report -> Comparison", instructions)
                self.assertIn("do not add SOF semantics", instructions)

                listed = client.post(
                    "/mcp",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {},
                    },
                )
                self.assertEqual(listed.status_code, 200)
                tools = listed.json()["result"]["tools"]
                by_name = {item["name"]: item for item in tools}
                self.assertEqual(
                    set(by_name),
                    {
                        "sof_realize",
                        "sof_report",
                        "sof_compare",
                        "sof_interpret",
                        "sof_validate",
                        "sof_explain",
                        "sof_get_contract",
                        "sof_get_artifact",
                        "sof_get_receipt",
                    },
                )
                self.assertTrue(
                    all(item.get("description", "").strip() for item in tools)
                )
                self.assertIn(
                    "explicit alignment",
                    by_name["sof_compare"]["description"],
                )
                self.assertIn(
                    "does not select",
                    by_name["sof_interpret"]["description"],
                )
                self.assertFalse(
                    set(by_name)
                    & {
                        "sof_select",
                        "sof_authorize",
                        "sof_execute",
                        "sof_observe_outcome",
                        "sof_certify_effect",
                    }
                )

                contract = client.post(
                    "/mcp",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "sof_get_contract",
                            "arguments": {
                                "contract_name": "service-request.schema.json"
                            },
                        },
                    },
                )
                self.assertEqual(contract.status_code, 200)
                contract_result = contract.json()["result"]["structuredContent"]
                self.assertEqual(
                    contract_result["contract_name"],
                    "service-request.schema.json",
                )
                self.assertRegex(contract_result["sha256"], "^[0-9a-f]{64}$")

    def test_transport_invariance_and_job_separation(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            root = Path(directory)
            workspace = root / "transport-fixture"
            shutil.copytree(CASE, workspace / "case")
            service = ServiceApplication(root)

            direct_runtime = RuntimeAPI().realize(
                workspace / "case",
                workspace / "runtime-api",
            )
            direct_response = service.realize(
                "transport-fixture",
                "case",
                "service-api",
                request_id="direct-1",
            )

            request_path = write_json(
                workspace / "cli-request.json",
                request("cli-1", "cli"),
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "sof_runtime.cli.main",
                    "service",
                    "execute",
                    str(request_path),
                    "--workspace-root",
                    str(root),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            cli_response = json.loads(completed.stdout)

            client = TestClient(create_app(service))
            http_result = client.post(
                "/v1/realizations",
                json=request("http-1", "http"),
            )
            self.assertEqual(http_result.status_code, 200)
            http_response = http_result.json()

            async def call_mcp() -> dict:
                server = create_server(service)
                result = await server.call_tool(
                    "sof_realize",
                    {
                        "workspace_id": "transport-fixture",
                        "case_directory": "case",
                        "run_directory": "mcp",
                        "request_id": "mcp-1",
                    },
                )
                self.assertFalse(result.is_error)
                assert result.structured_content is not None
                return result.structured_content

            mcp_response = asyncio.run(call_mcp())
            responses = [direct_response, cli_response, http_response, mcp_response]

            self.assertEqual(len({item["job_id"] for item in responses}), 4)
            self.assertEqual(
                len({item["semantic_run_id"] for item in responses}),
                1,
            )
            candidate_digests = {
                artifact_digest(item, "realization_candidate") for item in responses
            }
            candidate_digests.add(sha256_file(direct_runtime.candidate_path))
            self.assertEqual(len(candidate_digests), 1)

            for item in responses:
                job = service.get_job("transport-fixture", item["job_id"])
                self.assertEqual(job["state"], "succeeded")
                candidate_uri = next(
                    artifact["uri"]
                    for artifact in item["artifacts"]
                    if artifact["artifact_id"].startswith("realization_candidate:")
                )
                candidate_path = service.workspaces.resolve(
                    "transport-fixture",
                    candidate_uri.split("/", 3)[-1],
                    must_exist=True,
                )
                candidate_text = candidate_path.read_text(encoding="utf-8")
                self.assertNotIn(item["job_id"], candidate_text)
                self.assertNotIn("transport-fixture", candidate_text)

    def test_workspace_escape_is_rejected_before_runtime_execution(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            service = ServiceApplication(directory)
            with self.assertRaises(ServiceError) as caught:
                service.execute(
                    {
                        "contract_id": "sof-runtime.service-request.v1",
                        "request_id": "escape-1",
                        "workspace_id": "bounded",
                        "operation": "realize",
                        "input": {
                            "case_directory": "../outside",
                            "run_directory": "run",
                        },
                    }
                )
            self.assertIn(
                caught.exception.payload["code"],
                {"invalid_request", "path_violation"},
            )
            job = service.get_job(
                "bounded",
                caught.exception.payload["job_id"],
            )
            self.assertEqual(job["state"], "failed")
            self.assertIn("error", job)
            self.assertNotIn("response", job)

    def test_full_chain_artifacts_are_workspace_invariant(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            root = Path(directory)
            service = ServiceApplication(root)
            runs = []
            for workspace_id in ("workspace-a", "workspace-b"):
                workspace = root / workspace_id
                shutil.copytree(CASE, workspace / "case")
                shutil.copy2(
                    COMPARISON_PROFILE,
                    workspace / "comparison-profile.json",
                )
                responses = []
                for side in ("reference", "target"):
                    responses.append(
                        service.execute_operation(
                            "realize",
                            workspace_id,
                            {
                                "case_directory": f"case/{side}",
                                "run_directory": f"run/{side}",
                            },
                            request_id=f"{workspace_id}-realize-{side}",
                        )
                    )
                    responses.append(
                        service.execute_operation(
                            "report",
                            workspace_id,
                            {
                                "realization_run_directory": f"run/{side}",
                                "out_directory": f"run/{side}",
                            },
                            request_id=f"{workspace_id}-report-{side}",
                        )
                    )
                comparison = service.execute_operation(
                    "compare",
                    workspace_id,
                    {
                        "reference": {
                            "report": "run/reference/report/result.sofreport.json",
                            "receipt": "run/reference/report/validation-receipt.json",
                        },
                        "target": {
                            "report": "run/target/report/result.sofreport.json",
                            "receipt": "run/target/report/validation-receipt.json",
                        },
                        "alignment": "case/comparison/alignment.json",
                        "comparison_profile": "comparison-profile.json",
                        "out_directory": "run/comparison",
                    },
                    request_id=f"{workspace_id}-compare",
                )
                responses.append(comparison)
                interpretation = service.execute_operation(
                    "interpret",
                    workspace_id,
                    {
                        "audit": "run/comparison/result.sofaudit.json",
                        "receipt": "run/comparison/validation-receipt.json",
                        "context": "case/action/context.json",
                        "policy": "case/action/policy.json",
                        "out_directory": "run/action",
                    },
                    request_id=f"{workspace_id}-interpret",
                )
                responses.append(interpretation)
                runs.append(
                    {
                        "semantic_run_ids": [
                            item["semantic_run_id"] for item in responses
                        ],
                        "normative_digests": [
                            artifact_digest(responses[1], "sofrs_report"),
                            artifact_digest(responses[3], "sofrs_report"),
                            artifact_digest(comparison, "sofaudit"),
                            artifact_digest(interpretation, "sofaction"),
                        ],
                    }
                )
                action = load_json(workspace / "run" / "action" / "result.sofaction.json")
                source_audit = action["source_audit"]
                retrieved = service.get_artifact(
                    workspace_id,
                    source_audit["artifact"],
                    source_audit["digest"]["value"],
                )
                self.assertEqual(retrieved["content_encoding"], "json")
                self.assertEqual(
                    retrieved["content"]["audit_id"],
                    action["source_audit"]["audit_id"],
                )
                explanation = service.explain(
                    workspace_id,
                    "run/action",
                    request_id=f"{workspace_id}-explain-action",
                )["result"]["explanation"]
                self.assertEqual(explanation["workflow"], "full_pipeline")
                self.assertEqual(len(explanation["realizations"]), 2)
                self.assertTrue(
                    all(
                        item["canonical_compilable"] is True
                        and item["eligibility"] == "canonical_compilable"
                        for item in explanation["realizations"]
                    )
                )
                self.assertEqual(
                    explanation["comparison"]["validation"]["status"],
                    "PASS",
                )
                self.assertEqual(
                    len(explanation["interpretation"]["candidate_actions"]),
                    2,
                )
                self.assert_no_absolute_server_paths(explanation)

            self.assertEqual(runs[0], runs[1])

    def test_explanation_is_invariant_under_directory_renaming(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            root = Path(directory) / "named-layout"
            RuntimeAPI().full_pipeline(
                CASE / "reference",
                CASE / "target",
                alignment=CASE / "comparison" / "alignment.json",
                comparison_profile=COMPARISON_PROFILE,
                action_context=CASE / "action" / "context.json",
                policy_profile=CASE / "action" / "policy.json",
                run_dir=root,
            )
            expected = explain_run(root)
            for source, destination in (
                ("reference", "arbitrary-one"),
                ("target", "arbitrary-two"),
                ("comparison", "arbitrary-three"),
                ("action", "arbitrary-four"),
            ):
                (root / source).rename(root / destination)
            actual = explain_run(root)
            self.assertEqual(actual, expected)

    def test_explain_projection_rewrites_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            root = Path(directory)
            workspace = root / "transport-fixture"
            shutil.copytree(CASE, workspace / "case")
            shutil.copy2(COMPARISON_PROFILE, workspace / "comparison-profile.json")
            service = ServiceApplication(root)
            for side in ("reference", "target"):
                service.realize(
                    "transport-fixture",
                    f"case/{side}",
                    f"renamed/{side}/realize",
                    request_id=f"path-realize-{side}",
                )
                service.report(
                    "transport-fixture",
                    f"renamed/{side}/realize",
                    f"renamed/{side}/report",
                    request_id=f"path-report-{side}",
                )
            service.compare(
                "transport-fixture",
                {
                    "report": "renamed/reference/report/report/result.sofreport.json",
                    "receipt": "renamed/reference/report/report/validation-receipt.json",
                },
                {
                    "report": "renamed/target/report/report/result.sofreport.json",
                    "receipt": "renamed/target/report/report/validation-receipt.json",
                },
                "case/comparison/alignment.json",
                "comparison-profile.json",
                "renamed/nonsemantic-audit-name",
                request_id="path-compare",
            )
            service.interpret(
                "transport-fixture",
                "renamed/nonsemantic-audit-name/result.sofaudit.json",
                "renamed/nonsemantic-audit-name/validation-receipt.json",
                "case/action/context.json",
                "case/action/policy.json",
                "renamed/nonsemantic-action-name",
                request_id="path-interpret",
            )
            response = service.explain(
                "transport-fixture",
                "renamed/nonsemantic-action-name",
                request_id="path-explain",
            )
            explanation = response["result"]["explanation"]
            self.assertEqual(explanation["workflow"], "full_pipeline")
            self.assertEqual(len(explanation["realizations"]), 2)
            self.assertEqual(len(explanation["interpretation"]["candidate_actions"]), 2)
            self.assert_no_absolute_server_paths(response)

            http_response = TestClient(create_app(service)).post(
                "/v1/explanations",
                json={
                    "contract_id": "sof-runtime.service-request.v1",
                    "request_id": "path-explain-http",
                    "workspace_id": "transport-fixture",
                    "operation": "explain",
                    "input": {
                        "run_directory": "renamed/nonsemantic-action-name"
                    },
                },
            )
            self.assertEqual(http_response.status_code, 200)
            self.assert_no_absolute_server_paths(http_response.json())

            async def call_mcp_explain() -> dict:
                result = await create_server(service).call_tool(
                    "sof_explain",
                    {
                        "workspace_id": "transport-fixture",
                        "run_directory": "renamed/nonsemantic-action-name",
                        "request_id": "path-explain-mcp",
                    },
                )
                self.assertFalse(result.is_error)
                assert result.structured_content is not None
                return result.structured_content

            self.assert_no_absolute_server_paths(asyncio.run(call_mcp_explain()))

    def test_public_errors_do_not_disclose_server_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            root = Path(directory)
            service = ServiceApplication(root)
            with self.assertRaises(ServiceError) as caught:
                service.get_artifact(
                    "bounded",
                    "missing/result.json",
                    "0" * 64,
                )
            self.assertNotIn(str(root), str(caught.exception.payload))
            self.assert_no_absolute_server_paths(caught.exception.payload)

            client = TestClient(create_app(service))
            response = client.get(
                "/v1/artifacts/bounded",
                params={"path": "missing/result.json", "sha256": "0" * 64},
            )
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(str(root), response.text)
            self.assert_no_absolute_server_paths(response.json())

    def test_embedded_paths_in_third_party_errors_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            root = Path(directory)
            workspace = root / "transport-fixture"
            shutil.copytree(CASE, workspace / "case")
            service = ServiceApplication(root)

            def fail_with_embedded_paths(*args, **kwargs):
                del args, kwargs
                raise RuntimeError(
                    "Failed to open E:\\server\\secret-layout\\foo.json; "
                    "fallback /srv/sof/private/bar.json; "
                    "share \\\\host\\private\\evidence.json"
                )

            service._realize = fail_with_embedded_paths
            with self.assertRaises(ServiceError) as caught:
                service.execute(request("embedded-path-direct", "direct"))

            direct_payload = caught.exception.payload
            self.assertEqual(direct_payload["code"], "execution_failed")
            self.assertEqual(direct_payload["message"].count("<server-path>"), 3)
            for secret in ("secret-layout", "/srv/sof", "\\\\host\\private"):
                self.assertNotIn(secret, str(direct_payload))

            response = TestClient(create_app(service)).post(
                "/v1/realizations",
                json=request("embedded-path-http", "http"),
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["message"].count("<server-path>"), 3)
            for secret in ("secret-layout", "/srv/sof", "\\\\host\\private"):
                self.assertNotIn(secret, response.text)

    def test_mcp_exposes_only_service_operations(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            server = create_server(ServiceApplication(directory))

            async def names() -> set[str]:
                return {item.name for item in await server.list_tools()}

            self.assertEqual(
                asyncio.run(names()),
                {
                    "sof_realize",
                    "sof_report",
                    "sof_compare",
                    "sof_interpret",
                    "sof_validate",
                    "sof_explain",
                    "sof_get_contract",
                    "sof_get_artifact",
                    "sof_get_receipt",
                },
            )


if __name__ == "__main__":
    unittest.main()
