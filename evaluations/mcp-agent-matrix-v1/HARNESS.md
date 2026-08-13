# Provider-Native MCP Replay Harness

`tools/mcp_agent_harness.py` runs the frozen three-task matrix through a real
provider tool-calling loop. The model receives only the nine discovered SOF
MCP tools. It receives no shell, filesystem, browser, or repository tools.

The harness prepares the server workspace from `fixture-manifest.json`, records
the source fixture digests, discovers the MCP tool surface, forwards native
tool calls to the server, and writes:

```text
runs/<agent-id>.json
runs/<agent-id>-normal.md
runs/<agent-id>-normal-transcript.json
runs/<agent-id>-epistemic.md
runs/<agent-id>-epistemic-transcript.json
runs/<agent-id>-operational.md
runs/<agent-id>-operational-transcript.json
```

The JSON result is intentionally emitted as `awaiting_review`. Normal-workflow
milestones are projected from actual tool calls and tool results. Hostile
boundary violations and unsupported inferences require an independent reviewer
annotation; the harness never infers them from keywords or model self-report.

## Run

Start the existing MCP service, then run one provider/model identity:

```powershell
$env:DeepSeek_Service_Key = "..."
python tools/mcp_agent_harness.py `
  --agent-id deepseek-a `
  --provider deepseek `
  --model deepseek-chat `
  --mcp-url http://127.0.0.1:8082/mcp `
  --workspace-root runs/mcp-matrix-service `
  --spawn-server
```

`--spawn-server` is recommended for acceptance replay. It starts the service
from the current local source closure, waits for readiness, runs the matrix,
and terminates the child process. Connecting to an already-running or remote
server is supported, but the result records its closure as
`asserted_by_operator` rather than harness-verified.

For any OpenAI-compatible provider:

```powershell
$env:PROVIDER_KEY = "..."
python tools/mcp_agent_harness.py `
  --agent-id provider-a `
  --provider provider-name `
  --model model-id `
  --base-url https://provider.example/v1 `
  --api-key-env PROVIDER_KEY `
  --workspace-root runs/service
```

The named `deepseek` and `openai` presets have pinned provider endpoints. Use a
different provider name and an explicitly named credential environment variable
for any other endpoint; preset credentials cannot be redirected by CLI flags.

The provider endpoint must be HTTPS and redirects are rejected. The harness
does not print or persist API keys, raw provider request headers, or raw MCP
server filesystem paths beyond the service's public response projections.

## Review And Score

Annotate the generated result under the frozen rubric:

```powershell
python tools/review_mcp_agent_run.py `
  evaluations/mcp-agent-matrix-v1/runs/deepseek-a.json `
  --reviewer reviewer-id `
  --write
```

Add repeated flags when the reviewer observes a declared category, for example
`--operational-violation action_selection` or
`--normal-unsupported-inference inferred_alignment`. Then score the completed
matrix:

```powershell
python tools/score_mcp_agent_matrix.py evaluations/mcp-agent-matrix-v1
```

Do not replace the three frozen agent result files until their provider,
model identity, closure digest, transcript closure, and reviewer annotation
procedure are intentionally accepted as a new evaluation record. A new
cross-model study should use a new matrix directory or versioned result set.

## Boundary

Workspace preparation is harness orchestration. `workspace_id`, `job_id`, and
transcript paths do not enter the semantic SOF artifact identity. A successful
tool loop demonstrates interface behavior for the declared provider, prompt,
fixture, and pinned service closure; it does not establish scientific truth,
agent safety, model quality, or action authority.
