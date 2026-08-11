# Test Layers

- `unit/`: carrier, validator, and layered run-identity behavior.
- `conformance/`: immutable upstream contracts, exact Compile_v1 fixture,
  SOFRS faithful-assembly/receipt integration, SOFAUDIT semantic validation,
  and published SOFAction replay.
- `golden/`: complete extension runs, external-adopter workflows, and
  direct API/CLI/HTTP/MCP service transport controls.
- `regression/`: evidence promotion and missing-capability boundaries.
- `cross_language/`: JSON stdin/stdout executable protocol and the scoped
  Python/Rust Markov conformance pair.

The golden run is intentionally small. Ordinary computation outputs remain
under ignored `runs/`; only compact, reviewed fixtures should enter Git.

The rank-collapse regression matrix covers valid execution, malformed source,
plugin failure, artifact and closure tampering, validator-version mismatch,
source-digest change, unsupported cutoff policy, repeated semantic runs,
semantic/concrete environment separation, and in-process versus
external-executable semantic parity.

The SOFRS conformance slice recomputes `Compile_v1`, assembles every
ordered compiler item exactly once, validates the report object, and freezes a
seven-artifact validation-receipt closure. Its negative cases reject claim
drift, duplicate item bindings, degradation/failure-mode retyping, and a
tampered CompilerOutput.

The SOFAUDIT conformance slice builds two independently receipt-validated strict
SOFRS reports and an identity-aligned comparison. Hostile cases verify
reference/target roles, regime and profile closure, all four declared alignment
properties, guard-coordinate coupling, comparison-basis completeness,
claim/result/certificate compatibility, artifact ID/role/digest closure, and
the independent-oracle requirement for external-object claims.

The SOFAction runtime slice consumes a Paper XIII receipt-bound fixture and
independently replays Paper XIV Policy Predicate Language v1.0. Hostile cases
reject arbitrary predicates, projection rewrites, and candidate-set deletion.
This is a runtime conformance test against the published Paper XIV contract;
it does not establish policy correctness, authorization, execution, outcome,
or causal effect.

The service slice freezes closed orchestration envelopes and keeps job state,
semantic identity, and SOF result state separate. It executes the same
realization through direct Python, CLI, HTTP, and MCP projections, requiring
distinct job IDs, one semantic run ID, and one candidate digest. A second
control runs the complete Report/Comparison/Interpretation chain in two
workspace IDs and requires byte-identical SOFRS, SOFAUDIT, and SOFAction
artifacts. The installed-wheel check separately executes the HTTP realization
without importing repository internals.

`evaluations/mcp-agent-blackbox-v1/` records a separate MCP-only agent control.
Its validator checks discovered stages, explicit inputs, digest references,
unavailable capabilities, claim boundaries, hostile-prompt refusals, and the
distinction between subject `contract_status` and protocol admission. It does
not compare model prose.

`evaluations/mcp-agent-matrix-v1/` extends that method to three independent
agents and three frozen task classes. Pending runs retain null rates; the
matrix scorer distinguishes historical observations from acceptance runs under
the current source-addressed service implementation closure. Violation scoring
is categorical and does not compare response text.

The Rust positive-word suite additionally checks exact `sof-cjson-v1` bytes,
SHA-256 parity, NFC and numeric rejection, semantic-run identity, bundle and
artifact-digest equality, separate-process validator metadata, structured
exit failure, and orchestrator-owned artifact paths. It discovers Cargo from
`CARGO`, `PATH`, or `~/.cargo/bin`; when Cargo is absent, only this optional
cross-language class is skipped.
