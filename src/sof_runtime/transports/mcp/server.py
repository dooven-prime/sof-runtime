"""MCP tool projection over the shared SOF service application."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from sof_runtime import __version__
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.service import ServiceApplication


_TOOL_DESCRIPTIONS = {
    "realize": (
        "First workflow step. Validate a prepared Source Bundle and ExpertAdapter "
        "at case_directory, relative to workspace_id, and write a typed Realization "
        "to run_directory. Inspect result.canonical_compilable before calling "
        "sof_report: an extension-only realization legitimately stops here. Missing "
        "capabilities are not inferred or coerced."
    ),
    "report": (
        "Create and validate one SOFRS Report from a prior canonical-compilable "
        "Realization. realization_run_directory and out_directory are relative to "
        "workspace_id; optional compiler_profile and assembly_profile are explicit "
        "workspace-relative overrides. This operation owns single-report assembly, "
        "not cross-report comparison or action semantics."
    ),
    "compare": (
        "Compare two validated SOFRS Reports. Both report and receipt paths, an "
        "explicit alignment, and an explicit comparison_profile are mandatory and "
        "workspace-relative. Produces a SOFAUDIT Comparison and receipt. No comparison "
        "is inferred before alignment, and unavailable coordinates are not zero."
    ),
    "interpret": (
        "Interpret one validated SOFAUDIT using an explicit ActionContext and "
        "PolicyProfile, all addressed by workspace-relative paths. Produces a "
        "SOFAction Interpretation and bounded CandidateAction set. It does not select, "
        "recommend, execute, authorize, observe outcomes, or certify causal effects. "
        "ActionContext.contract_status describes the evaluated subject; SOFAction "
        "context admission is recorded separately under context_admission."
    ),
    "validate": (
        "Run an existing semantic validator over one workspace-relative artifact. "
        "validation_kind must be one of sofrs, sofrs_receipt, sofaudit, "
        "sofaudit_receipt, sofaction, or sofaction_receipt. Validation certifies the "
        "declared contract closure only and does not upgrade scientific claims."
    ),
    "explain": (
        "Return a structured, source-addressed explanation for a run_directory relative "
        "to workspace_id: source, adapter, carrier/capabilities, validators, artifacts, "
        "receipts, policy rules, and negative boundaries where present. Stages are "
        "discovered from the artifact/receipt graph, not directory names. Explanation "
        "traces recorded provenance; it does not invent evidence or authorize action."
    ),
    "get_contract": (
        "Read one frozen service orchestration JSON Schema and its SHA-256 digest. "
        "Allowed names are service-request.schema.json, service-response.schema.json, "
        "service-error.schema.json, and job.schema.json. JobState is orchestration state, "
        "not a SOF scientific result state."
    ),
    "get_artifact": (
        "Retrieve a source-addressed artifact only when both its returned path or URI "
        "and exact lowercase SHA-256 digest are supplied with the owning workspace_id. "
        "Digest mismatch is rejected; retrieval does not alter or promote the artifact."
    ),
    "get_receipt": (
        "Retrieve a source-addressed validation or run receipt only when both its "
        "returned path or URI and exact lowercase SHA-256 digest are supplied with the "
        "owning workspace_id. A PASS receipt is not self-authenticating scientific proof."
    ),
}


def _request_id(value: str | None) -> str:
    return value or f"mcp:{uuid4().hex}"


def create_server(
    service: ServiceApplication | None = None,
    *,
    workspace_root: str | Path | None = None,
):
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as error:  # pragma: no cover - exercised by wheel extras
        raise RuntimeError("MCP transport requires 'sof-runtime[mcp]'") from error

    application = service or ServiceApplication(
        workspace_root or PROJECT_ROOT / "runs" / "service"
    )
    server = MCPServer(
        "sof-runtime",
        title="SOF Runtime",
        version=__version__,
        instructions=(
            "Use the staged workflow Realization -> Report -> Comparison -> "
            "Interpretation/CandidateAction. Query frozen service envelopes with "
            "sof_get_contract and retrieve outputs only by path/URI plus digest. "
            "Tools expose orchestration over existing validators; they do not add SOF "
            "semantics, infer missing claims, or perform selection, execution, "
            "authorization, outcome observation, or effect certification."
        ),
    )

    @server.tool(
        name="sof_realize",
        description=_TOOL_DESCRIPTIONS["realize"],
        structured_output=True,
    )
    def realize(
        workspace_id: str,
        case_directory: str,
        run_directory: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return application.realize(
            workspace_id,
            case_directory,
            run_directory,
            request_id=_request_id(request_id),
        )

    @server.tool(
        name="sof_report",
        description=_TOOL_DESCRIPTIONS["report"],
        structured_output=True,
    )
    def report(
        workspace_id: str,
        realization_run_directory: str,
        out_directory: str,
        compiler_profile: str | None = None,
        assembly_profile: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return application.report(
            workspace_id,
            realization_run_directory,
            out_directory,
            compiler_profile=compiler_profile,
            assembly_profile=assembly_profile,
            request_id=_request_id(request_id),
        )

    @server.tool(
        name="sof_compare",
        description=_TOOL_DESCRIPTIONS["compare"],
        structured_output=True,
    )
    def compare(
        workspace_id: str,
        reference_report: str,
        reference_receipt: str,
        target_report: str,
        target_receipt: str,
        alignment: str,
        comparison_profile: str,
        out_directory: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return application.compare(
            workspace_id,
            {"report": reference_report, "receipt": reference_receipt},
            {"report": target_report, "receipt": target_receipt},
            alignment,
            comparison_profile,
            out_directory,
            request_id=_request_id(request_id),
        )

    @server.tool(
        name="sof_interpret",
        description=_TOOL_DESCRIPTIONS["interpret"],
        structured_output=True,
    )
    def interpret(
        workspace_id: str,
        audit: str,
        receipt: str,
        context: str,
        policy: str,
        out_directory: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return application.interpret(
            workspace_id,
            audit,
            receipt,
            context,
            policy,
            out_directory,
            request_id=_request_id(request_id),
        )

    @server.tool(
        name="sof_validate",
        description=_TOOL_DESCRIPTIONS["validate"],
        structured_output=True,
    )
    def validate(
        workspace_id: str,
        validation_kind: str,
        artifact: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return application.validate(
            workspace_id,
            validation_kind,
            artifact,
            request_id=_request_id(request_id),
        )

    @server.tool(
        name="sof_explain",
        description=_TOOL_DESCRIPTIONS["explain"],
        structured_output=True,
    )
    def explain(
        workspace_id: str,
        run_directory: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return application.explain(
            workspace_id,
            run_directory,
            request_id=_request_id(request_id),
        )

    @server.tool(
        name="sof_get_contract",
        description=_TOOL_DESCRIPTIONS["get_contract"],
        structured_output=True,
    )
    def get_contract(contract_name: str) -> dict[str, Any]:
        return application.get_contract(contract_name)

    @server.tool(
        name="sof_get_artifact",
        description=_TOOL_DESCRIPTIONS["get_artifact"],
        structured_output=True,
    )
    def get_artifact(workspace_id: str, path: str, sha256: str) -> dict[str, Any]:
        return application.get_artifact(workspace_id, path, sha256)

    @server.tool(
        name="sof_get_receipt",
        description=_TOOL_DESCRIPTIONS["get_receipt"],
        structured_output=True,
    )
    def get_receipt(workspace_id: str, path: str, sha256: str) -> dict[str, Any]:
        return application.get_artifact(workspace_id, path, sha256)

    return server
