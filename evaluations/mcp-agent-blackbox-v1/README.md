# MCP Agent Black-Box Evaluation v1

Status: structured semantic-behavior acceptance record.

This evaluation asks an external agent to use only the public SOF Runtime MCP
surface. It measures whether the agent can discover and execute the strongest
admitted workflow while preserving SOF evidence and authority boundaries. It
does not score exact prose.

The supplied finite-state source bundle is
`examples/external-adapter-finite-state/`. Before a run, provision that bundle
and the declared comparison profile beneath a confined service workspace. The
recorded run used workspace ID `mcp-adopter-20260811a` and output root
`evaluation/`.

Files:

- `prompt.md`: primary MCP-only task;
- `hostile-prompt.md`: follow-up authority-escalation test;
- `tool-surface.json`: discovered public MCP tools and negative surface;
- `service-contract-ref.json`: digest-bound service request contract;
- `run-summary.json`: semantic result of the recorded agent run;
- `artifact-chain.json`: artifact, receipt, and semantic-run digest manifest;
- `expected-invariants.json`: model-independent acceptance properties.

Validate the package from the repository root:

```text
python tools/validate_mcp_agent_evaluation.py \
  evaluations/mcp-agent-blackbox-v1
```

## Field distinction

`ActionContext.contract_status` names the supplied status of the evaluated
subject relative to an external, transformation, or business contract. It is
not the machine-contract admission status of the `ActionContext`. The latter is
recorded separately by `context_admission.status` and
`context_admission.contract_validation`.

The fixture intentionally exercises this distinction:

```text
ActionContext.contract_status = nonconforming
context_admission.status = admitted
context_admission.contract_validation = admitted
```

This means that a protocol-valid context describes a nonconforming subject. It
does not mean that protocol admission proves the substantive status correct.

## Known non-claims

- This package is an agent-behavior control, not paper evidence.
- Workspace URIs are local projections and are not portable artifact storage.
- A passing run does not establish adapter adequacy or scientific truth.
- Report certificates in this control are `protocol_conformance` certificates;
  object-level recomputation and domain semantic adequacy remain unassessed.
- A mismatch is not a defect, and a CandidateAction is not a recommendation,
  selection, authorization, execution command, outcome, or effect certificate.
- Model updates may change wording while still satisfying the frozen semantic
  invariants.
- The original raw model response and MCP transcript are not retained in this
  package. Its validator checks the recorded structured summary and artifact
  closure, not an independently recoverable classification of agent prose.
