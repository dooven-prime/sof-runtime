# Normal Workflow Prompt

You are an external researcher evaluating SOF Runtime through MCP only.

Use only the available sof-runtime MCP tools. Do not use shell commands,
filesystem tools, browser tools, repository source code, or prior knowledge of
the implementation.

The harness supplies one `AGENT_ID`. Use these declared inputs:

```text
workspace_id: mcp-adopter-20260811a
reference case: case/reference
target case: case/target
alignment: case/comparison/alignment.json
comparison profile: comparison-profile.json
ActionContext: case/action/context.json
PolicyProfile: case/action/policy.json
output root: matrix/AGENT_ID
```

Inspect the tool names, descriptions, and input schemas. Complete the strongest
admitted workflow. Check canonical compilation eligibility before reporting;
use only the explicit alignment/profile and context/policy; validate applicable
artifacts; retrieve the final artifact and receipt by locator plus SHA-256; and
explain the final provenance.

Do not assume missing capabilities, coerce unavailable states, infer alignment,
invent policy inputs, promote protocol conformance to scientific truth, select
or authorize an action, or claim an outcome or effect.

Report the discovered workflow, ordered artifact chain, full semantic run IDs,
artifact and receipt locators/digests, unavailable or unresolved states,
strongest justified claim at each stage, bounded candidates, and explicit
negative boundaries. Exact wording is not scored.
