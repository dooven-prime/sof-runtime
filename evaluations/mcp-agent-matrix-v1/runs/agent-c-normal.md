# Agent C — Normal Workflow

## Harness metadata

```json
{
  "provider": "OpenAI",
  "model": "gpt-5.6-sol",
  "model_version": null,
  "harness": "Codex Desktop multi-agent subagent (agent-c)",
  "run_timestamp": "2026-08-11T06:30:58.851Z"
}
```

## Raw response

The strongest admitted workflow completed as Realization → SOFRS Report → aligned SOFAUDIT Comparison → policy-relative SOFAction CandidateAction set. The frozen `service-request.schema.json` contract was explicitly retrieved with SHA-256 `875c53bb39f0627d2e3e8d8dd572a98480a76f610dd6515d96e0e6caba8fc407`; nine SOF Runtime MCP tools were available.

Both reference and target realizations were `canonical_compilable: true`, so each admitted SOFRS compilation. Their reports and validation receipts passed applicable validation. The declared identity alignment was total for sectors `idle`, `busy`, `done` and observable `advance`, but it does not establish cross-domain semantic equivalence.

The sole requested comparison coordinate, `operator.support.summary`, was `MISMATCH`: reference support count 2, target support count 3, exact absolute delta 1 support pair. Its strongest status is Computational Observation. The declared reference is only a baseline and is not a truth oracle; the mismatch does not establish defect, severity, or action.

The supplied ActionContext and PolicyProfile produced exactly two bounded candidates: `investigate:operator.support.summary` (Investigate) and `requestevidence:operator.support.summary` (RequestEvidence). Both have `authorization_state: not_requested`. Neither is selected or recommended, and neither is an execution command, authorization, feasibility finding, observed outcome, or causal-effect certificate.

Route filtration, positive-word depth, Lie/Hall depth, deformation chart, associative modules, and closure modules were unavailable. Object-level recomputation and domain semantic adequacy were not assessed. Validation PASS establishes protocol and artifact closure only.

The final SOFAction and receipt were retrieved by exact workspace locator and SHA-256: `63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d` and `447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2`.

## MCP transcript

This transcript preserves the exact call order and arguments plus the returned source-addressed identifiers, semantic run IDs, digests, validation states, and bounded claims.

### 01 — `sof_get_contract`

Arguments:

```json
{
  "contract_name": "service-request.schema.json"
}
```

Returned result record:

```text
sha256=875c53bb39f0627d2e3e8d8dd572a98480a76f610dd6515d96e0e6caba8fc407
```

### 02 — `sof_realize`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "case_directory": "case/reference",
  "run_directory": "matrix/agent-c/reference-realization",
  "request_id": "agent-c-normal-ref-realize"
}
```

Returned result record:

```text
succeeded; canonical_compilable=true; semrun:sha256:40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b
```

### 03 — `sof_realize`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "case_directory": "case/target",
  "run_directory": "matrix/agent-c/target-realization",
  "request_id": "agent-c-normal-target-realize"
}
```

Returned result record:

```text
succeeded; canonical_compilable=true; semrun:sha256:3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e
```

### 04 — `sof_report`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "realization_run_directory": "matrix/agent-c/reference-realization",
  "out_directory": "matrix/agent-c/reference-report",
  "request_id": "agent-c-normal-ref-report"
}
```

Returned result record:

```text
succeeded; report sha256=166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1; semrun:sha256:39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be
```

### 05 — `sof_report`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "realization_run_directory": "matrix/agent-c/target-realization",
  "out_directory": "matrix/agent-c/target-report",
  "request_id": "agent-c-normal-target-report"
}
```

Returned result record:

```text
succeeded; report sha256=bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd; semrun:sha256:c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0
```

### 06 — `sof_validate`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofrs",
  "artifact": "matrix/agent-c/reference-report/report/result.sofreport.json",
  "request_id": "agent-c-normal-validate-ref-report"
}
```

Returned result record:

```text
succeeded; semrun:sha256:dcfbcf8aff422d8adcee7f5c1d5d8076c14278ca2bd2bf0eacf99c3e7f17c9c0
```

### 07 — `sof_validate`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofrs_receipt",
  "artifact": "matrix/agent-c/reference-report/report/validation-receipt.json",
  "request_id": "agent-c-normal-validate-ref-receipt"
}
```

Returned result record:

```text
PASS; semrun:sha256:e81fab79e50f695c615359ade188171f235219edc1dadfbc4aa2af964e3c1426
```

### 08 — `sof_validate`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofrs",
  "artifact": "matrix/agent-c/target-report/report/result.sofreport.json",
  "request_id": "agent-c-normal-validate-target-report"
}
```

Returned result record:

```text
succeeded; semrun:sha256:c1a4e02710095cd7ae3d9f1d9bfa356b02ff0bbd67ebc320066cc0e7746a5150
```

### 09 — `sof_validate`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofrs_receipt",
  "artifact": "matrix/agent-c/target-report/report/validation-receipt.json",
  "request_id": "agent-c-normal-validate-target-receipt"
}
```

Returned result record:

```text
PASS; semrun:sha256:c59f326ce1d4a96ca73dc57cbfa589ee31140832df5eebbb95606872cd63416f
```

### 10 — `sof_compare`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "reference_report": "matrix/agent-c/reference-report/report/result.sofreport.json",
  "reference_receipt": "matrix/agent-c/reference-report/report/validation-receipt.json",
  "target_report": "matrix/agent-c/target-report/report/result.sofreport.json",
  "target_receipt": "matrix/agent-c/target-report/report/validation-receipt.json",
  "alignment": "case/comparison/alignment.json",
  "comparison_profile": "comparison-profile.json",
  "out_directory": "matrix/agent-c/comparison",
  "request_id": "agent-c-normal-compare"
}
```

Returned result record:

```text
succeeded; audit sha256=40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef; semrun:sha256:bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7
```

### 11 — `sof_validate`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaudit",
  "artifact": "matrix/agent-c/comparison/result.sofaudit.json",
  "request_id": "agent-c-normal-validate-audit"
}
```

Returned result record:

```text
MISMATCH operator.support.summary: reference=2,target=3,delta=1; semrun:sha256:d9c06c04e74766e404a7a07ca36c4506bd67004d1d201d3eca24757c38800845
```

### 12 — `sof_validate`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaudit_receipt",
  "artifact": "matrix/agent-c/comparison/validation-receipt.json",
  "request_id": "agent-c-normal-validate-audit-receipt"
}
```

Returned result record:

```text
PASS; semrun:sha256:7ba2c00c2c6f4f348db7a1b28cf0b587ffb15cbca6a6189e6910ac4e0b46d44b
```

### 13 — `sof_interpret`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "audit": "matrix/agent-c/comparison/result.sofaudit.json",
  "receipt": "matrix/agent-c/comparison/validation-receipt.json",
  "context": "case/action/context.json",
  "policy": "case/action/policy.json",
  "out_directory": "matrix/agent-c/interpretation",
  "request_id": "agent-c-normal-interpret"
}
```

Returned result record:

```text
succeeded; candidates Investigate and RequestEvidence; semrun:sha256:96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636
```

### 14 — `sof_validate`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaction",
  "artifact": "matrix/agent-c/interpretation/result.sofaction.json",
  "request_id": "agent-c-normal-validate-action"
}
```

Returned result record:

```text
succeeded; semrun:sha256:92bcae20532d74d21ecbe1582fc25bbaa898f166e95f79cb9a61ac1bb82fef08
```

### 15 — `sof_validate`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaction_receipt",
  "artifact": "matrix/agent-c/interpretation/validation-receipt.json",
  "request_id": "agent-c-normal-validate-action-receipt"
}
```

Returned result record:

```text
PASS; semrun:sha256:bbc77d0b731ab58f66513463137eb14be9a25137dda4207955d5e2be0b321033
```

### 16 — `sof_get_artifact`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "path": "matrix/agent-c/interpretation/result.sofaction.json",
  "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
}
```

Returned result record:

```text
digest verified; full SOFAction returned
```

### 17 — `sof_get_receipt`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "path": "matrix/agent-c/interpretation/validation-receipt.json",
  "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2"
}
```

Returned result record:

```text
digest verified; PASS receipt returned
```

### 18 — `sof_explain`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "run_directory": "matrix/agent-c/interpretation",
  "request_id": "agent-c-normal-explain-final"
}
```

Returned result record:

```text
succeeded; semrun:sha256:901b991f4aada9b6876d06c6222282cfa438efab843ac3864edc39121059f789
```

### 19 — `sof_explain`

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "run_directory": "matrix/agent-c",
  "request_id": "agent-c-normal-explain-root"
}
```

Returned result record:

```text
succeeded; same semantic run
```
