"""FastAPI projection of the SOF service application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sof_runtime import __version__
from sof_runtime.paths import PROJECT_ROOT, SERVICE_CONTRACT_ROOT
from sof_runtime.service import (
    SERVICE_CONTRACT_NAMES,
    ServiceApplication,
    ServiceError,
)


_ENDPOINT_OPERATIONS = {
    "realizations": "realize",
    "reports": "report",
    "comparisons": "compare",
    "interpretations": "interpret",
    "validations": "validate",
    "explanations": "explain",
}
def create_app(
    service: ServiceApplication | None = None,
    *,
    workspace_root: str | Path | None = None,
    mcp_host: str = "127.0.0.1",
):
    try:
        from fastapi import FastAPI, Query
        from fastapi.responses import FileResponse, JSONResponse
    except ImportError as error:  # pragma: no cover - exercised by wheel extras
        raise RuntimeError(
            "HTTP transport requires 'sof-runtime[service]'"
        ) from error

    application = service or ServiceApplication(
        workspace_root or PROJECT_ROOT / "runs" / "service"
    )
    from sof_runtime.transports.mcp import create_server

    mcp_server = create_server(application)
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        host=mcp_host,
    )

    @asynccontextmanager
    async def lifespan(_app):
        async with mcp_server.session_manager.run():
            yield

    app = FastAPI(
        title="SOF Runtime Service",
        version=__version__,
        description=(
            "Transport projection over RuntimeAPI. JSON Schema and canonical "
            "SOF artifacts remain the contracts."
        ),
        lifespan=lifespan,
    )
    app.state.sof_service = application
    app.state.sof_mcp_server = mcp_server

    @app.exception_handler(ServiceError)
    async def service_error_handler(_request: Any, error: ServiceError):
        status_by_code = {
            "invalid_request": 422,
            "path_violation": 403,
            "not_found": 404,
            "dependency_unavailable": 503,
            "execution_failed": 409,
        }
        return JSONResponse(
            status_code=status_by_code.get(error.payload["code"], 500),
            content=error.payload,
        )

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "service_contract": "v1"}

    @app.get("/v1/contracts/{contract_name}")
    def contract(contract_name: str):
        if contract_name not in SERVICE_CONTRACT_NAMES:
            raise ServiceError("not_found", "unknown service contract")
        return FileResponse(
            SERVICE_CONTRACT_ROOT / contract_name,
            media_type="application/schema+json",
        )

    def execute(expected_operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("operation") != expected_operation:
            raise ServiceError(
                "invalid_request",
                f"endpoint requires operation={expected_operation!r}",
                request_id=payload.get("request_id"),
            )
        return application.execute(payload)

    def make_route(expected: str):
        def route(payload: dict[str, Any]) -> dict[str, Any]:
            return execute(expected, payload)

        return route

    for endpoint, operation in _ENDPOINT_OPERATIONS.items():
        app.add_api_route(
            f"/v1/{endpoint}",
            make_route(operation),
            methods=["POST"],
            name=f"sof_{operation}",
        )

    @app.get("/v1/jobs/{workspace_id}/{job_id}")
    def get_job(workspace_id: str, job_id: str) -> dict[str, Any]:
        try:
            return application.get_job(workspace_id, job_id)
        except FileNotFoundError as error:
            raise ServiceError("not_found", str(error)) from error

    def artifact_response(
        workspace_id: str,
        path: str,
        sha256: str,
    ):
        result = application.get_artifact(workspace_id, path, sha256)
        resolved = application.resolve_artifact(workspace_id, path)
        return FileResponse(
            resolved,
            media_type=result["artifact"]["media_type"],
            headers={
                "ETag": f'"sha256:{sha256}"',
                "X-SOF-Artifact-SHA256": sha256,
            },
        )

    @app.get("/v1/artifacts/{workspace_id}")
    def get_artifact(
        workspace_id: str,
        path: str = Query(...),
        sha256: str = Query(..., pattern="^[0-9a-f]{64}$"),
    ):
        return artifact_response(workspace_id, path, sha256)

    @app.get("/v1/receipts/{workspace_id}")
    def get_receipt(
        workspace_id: str,
        path: str = Query(...),
        sha256: str = Query(..., pattern="^[0-9a-f]{64}$"),
    ):
        return artifact_response(workspace_id, path, sha256)

    app.mount("/", mcp_app, name="sof_mcp")

    return app
