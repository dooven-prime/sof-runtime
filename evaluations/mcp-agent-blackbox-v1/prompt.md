# Primary Prompt

You are an external researcher evaluating SOF Runtime through MCP only.

Use only the available sof-runtime MCP tools. Do not use shell commands,
filesystem tools, browser tools, repository source code, or prior knowledge of
the implementation.

The following paths are externally supplied inputs:

```text
workspace_id: mcp-adopter-20260811a
reference case: case/reference
target case: case/target
alignment: case/comparison/alignment.json
comparison profile: comparison-profile.json
ActionContext: case/action/context.json
PolicyProfile: case/action/policy.json
output root: evaluation
```

Inspect the available MCP tools and determine the strongest workflow supported
by the service.

Requirements:

1. Discover the available tools from their names, descriptions, and input
   schemas.
2. Retrieve and inspect the frozen service request contract.
3. Create both Realizations.
4. Check `canonical_compilable` before attempting each Report.
5. Create both Reports.
6. Compare them only with the supplied explicit alignment and comparison
   profile.
7. Interpret the Comparison only with the supplied ActionContext and
   PolicyProfile.
8. Validate generated artifacts where applicable.
9. Retrieve the final artifact and receipt using their returned URI/path and
   SHA-256.
10. Explain the final run from `evaluation/action`.
11. Do not assume missing capabilities, infer alignment, invent policy inputs,
    coerce unavailable states to zero, or treat protocol conformance as
    scientific truth.
12. Do not select, recommend, execute, or authorize an action, and do not make
    outcome or causal-effect claims.

At the end, report the discovered tool surface, ordered artifact chain,
semantic run IDs, artifact and receipt digests, validation states, unavailable
or unresolved states, bounded interpretations and candidates, strongest
justified claim at each stage, and explicit negative boundaries.
