# Conformance and Promotion

`sof-runtime` is a reusable execution and artifact protocol. It is not the
semantic authority for SOF mathematics or for any application's scientific
claims.

## Adoption Levels

An application may adopt only the layers it needs:

1. **Artifact protocol.** Use versioned schemas, canonical JSON, SHA-256,
   producer identities, input references, and immutable result artifacts.
2. **Execution protocol.** Use RunRequest/RunResponse and the external plugin
   boundary without importing Python runtime types.
3. **Extension validation.** Supply a domain payload schema and an independent
   validator with a declared finite scope.
4. **SOF compilation.** Emit Typed SOF IR and Compiler Output only for objects,
   carriers, policies, and promotions admitted by the vendored upstream
   contracts.
5. **Reporting protocol.** Bind Compiler Output to a separately versioned
   Assembly Profile, preserve every normative item exactly once, and validate
   the resulting `.sofreport`; do not serialize a runtime debug view as a
   report.
6. **Comparison protocol.** Consume two receipt-validated SOFRS reports only
   through explicit sector/observable alignment and a controlled comparison
   specification. Preserve unmatched and incomparable states and do not treat
   the reference role as correctness authority.
7. **Action-trace protocol.** Consume one receipt-validated SOFAUDIT only with
   an explicit ActionContext and PolicyProfile. Preserve the audit projection,
   replay the closed predicate language, and emit bounded candidates without
   claiming selection, authorization, or causal effect.

Using levels 1--3 does not require accepting the full SOF theory. It requires
honest declarations and source-addressed evidence. Level 4 additionally
requires the applicable SOF object and compiler contracts.

## Status Separation

Keep these statements distinct:

- **validation passed:** the declared validator reproduced its bounded checks;
- **compiler item emitted:** the frozen Manifest/IR/Profile contract admitted
  an item;
- **report assembly validated:** the report preserved the exact CompilerOutput
  items and bound artifact closure under the selected Assembly Profile;
- **comparison audit validated:** the audit preserved report-item identity and
  computed coordinates faithfully relative to the declared alignment and
  comparison specification;
- **action trace validated:** the runtime replayed the declared context/policy
  predicates and regenerated the bounded candidate set without changing the
  source audit;
- **upstream contract accepted:** `rime-lite` versioned the semantic object or
  promotion rule;
- **paper claim published:** an owning manuscript and release identity accepted
  the claim.

None implies the next without an explicit artifact and review step.

The current SOFRS v2, SOFAUDIT v2, and SOFAction v2 integrations are immutable
vendored upstream inputs pinned by `upstream.lock.json` to the published
release-content commits of their owning papers. Runtime validation establishes
conformance to those exact bytes only. It does not establish adapter adequacy,
reference truth, policy correctness, authorization, execution, outcome, or
causal effect.

## Promotion Package

A proposal from this repository to `rime-lite` should contain:

- source and extension schema identifiers;
- canonical input and output digests;
- producer and validator IDs with versions;
- RunRequest, RunResponse, result bundle, and validation certificate;
- the proposed carrier semantics and negative boundaries;
- exact/truncated, cutoff, tolerance, and saturation conventions;
- tests or formal artifacts supporting the proposed promotion;
- the requested reader-facing claim status and its scope.

The frozen RunResponse is content-addressed before the promotion package is
assembled. Its `artifact_closure` fixes the canonical artifact count, ordered
IDs, each URI/schema/digest tuple, artifact-manifest digest, and validator
certificate digest. The package binds exactly that closure plus the frozen
RunResponse artifact; it is not embedded back into RunResponse. Files added to
a run directory after freezing are not promotion evidence.

Acceptance occurs in `rime-lite`. After acceptance, update
`contracts/upstream.lock.json` and import the new immutable contract snapshot.
Do not patch vendored files locally.
