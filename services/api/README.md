# HTTP Service Reference Deployment

Status: runnable `v0.3.0` reference deployment.

Build from the repository root:

```text
docker build -f services/api/Dockerfile -t sof-runtime:0.3.0 .
docker run --rm -p 8080:8080 -v sof-runtime-data:/data sof-runtime:0.3.0
```

The container starts `sof serve` with `/data/service` as its confined service
workspace. Provision each expert case beneath one workspace before submitting
a versioned request envelope. Service schemas are available from
`GET /v1/contracts/{contract-name}`. The same process exposes the MCP
Streamable HTTP endpoint at `/mcp`; its tools delegate to the same
`ServiceApplication` as the HTTP routes.

Artifact and receipt retrieval accepts either a `sof-workspace://` projection
URI or a canonical cache URI emitted inside a normative artifact. Both require
the expected SHA-256. Arbitrary repository paths are rejected.

The reference image is deliberately single-process. It has no authentication,
authorization, tenant administration, remote source upload, distributed queue,
external object store, TLS termination, or production availability claim.
Deployments must add those controls outside `ServiceApplication` without
changing SOF contracts or interpreting missing evidence.

Known non-claims:

- service conformance is not adapter adequacy or scientific validity;
- `JobState` is not a SOF result or evidence state;
- HTTP paths and workspaces are not semantic inputs;
- the image does not select, authorize, execute, or certify an action;
- the image is not a multi-tenant security boundary;
- no gRPC contract is defined.
