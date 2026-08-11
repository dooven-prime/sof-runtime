# AGENTS.md - sof-runtime

This repository implements versioned SOF contracts. Canonical mathematical
definitions, theorems, ownership boundaries, and publication identities remain
in `dooven-prime/rime-lite`.

The runtime may be adopted as an artifact and diagnostic protocol without an
application accepting every SOF theorem. Control the shared language,
conformance conditions, provenance, and artifact identity; do not centralize
or overwrite domain-specific scientific conclusions.

## Authority Boundary

- Treat `contracts/compiler/` as immutable vendored upstream material.
- Verify vendored files against `contracts/upstream.lock.json`.
- Treat `contracts/reporting/v2.0/` and `contracts/comparison/v2.0/` as
  immutable upstream material and verify them against
  `contracts/upstream.lock.json`.
- Treat `contracts/action/candidate-v2.0/` as an explicitly non-canonical Paper
  XIV integration snapshot. Verify it against
  `contracts/upstream-candidate.lock.json`, but never cite that candidate lock
  as publication or upstream acceptance.
- Put runtime-only protocols under `contracts/runtime/`.
- Put domain payloads under versioned `contracts/sources/` or
  `contracts/extensions/`.
- Never add a new canonical SOF carrier, result state, or claim status locally.
- Propose stable semantic changes upstream instead of silently evolving a
  vendored contract.
- Keep validated extensions outside canonical Typed SOF IR and Compiler Output
  until their carrier and promotion rules are versioned upstream.
- Treat runtime validation, SOF compilation, and upstream promotion as three
  distinct statuses.

Compiler Output is not a SOFRS report. A SOFRS assembler must bind one exact
CompilerOutput, apply a separately typed Assembly Profile, and preserve a
type- and identity-bijective mapping from ordered compiler items to report
claims and degradation items. Compiler degradation is not an application
failure mode. Adapters declare capabilities, inspect source inputs, and may
compute bounded realization candidates, but they do not issue runtime-owned
reports or certificates. Carriers compute candidate findings. Independent
validators check bounded extension evidence where the contract requires
independence; adapter-supplied evidence is not independent merely because it
passes schema validation. Profiles select eligible canonical claims but do not
create evidence.

Public interchange uses JSON Schema, JSON/JSONL, artifact URIs, SHA-256, and
explicit contract versions. Python objects and pickle files are not public
contracts.

## Public Runtime API

The public application-facing facade is intentionally thin:

```text
sof_runtime.sdk  -> ExpertAdapter and JSON-shaped adapter declarations
sof_runtime.api  -> RuntimeAPI and validated artifact handles
sof CLI          -> scripted workflow entry points
```

The stable runtime object names are `Realization`, `Report`, `Comparison`,
`Interpretation`, and `CandidateAction`. They are handles over source-addressed
JSON artifacts, not a parallel semantic object model. Keep JSON Schema,
canonical JSON, artifact references, digests, and the owning RIME manuscripts
as the sources of truth.

The supported workflow is staged, and Level 1 has an explicit eligibility
boundary:

```text
Level 1A: ExpertAdapter -> Validated Realization
Level 1B: canonical-compilable Realization -> Report
Level 2: Report + Report + explicit alignment/profile -> Comparison
Level 3: Comparison + ActionContext + PolicyProfile -> Interpretation + CandidateAction*
```

Every Level 1A result is valid only as a realization artifact. If the runtime
cannot match the candidate to a currently accepted canonical carrier, its
eligibility is `extension_only`; the run stops with a realization receipt and
may become a promotion proposal. It must not construct Manifest, Typed SOF IR,
CompilerOutput, or SOFRS. Only `canonical_compilable` results may enter Level
1B. Keep this distinction visible in API types, receipts, CLI output, and
documentation.

`RuntimeAPI.compare()` requires keyword inputs `alignment`, `profile`, and
`out_dir`. `RuntimeAPI.full_pipeline()` requires `alignment`,
`comparison_profile`, `action_context`, `policy_profile`, and `run_dir`.
The CLI equivalents require `--alignment` and `--comparison-profile` for
`sof compare` and `sof full-pipeline`. Never load an alignment or comparison
profile implicitly from an example directory inside these semantic APIs.

The comparison producer must source-address the supplied alignment and profile
in the SOFAUDIT artifact closure and must use their values when constructing
the audit. A reference fixture may provide convenient paths, but it is not a
semantic default.

Level 3 stops at a bounded candidate set. It must not select, authorize,
execute, or certify the effectiveness of an action. `PolicyProfile` is the
current sole normative input for both interpretation and candidate generation;
do not add a second semantic rulebook or action-generation profile without a
versioned design decision. Such a split is a future research direction, not
an implicit contract.

The external `ExpertAdapter` boundary has exactly four required methods:
`describe`, `inspect_source`, `realize`, and `evidence`. Adapter methods use
JSON-compatible dictionaries. An adapter declares its capabilities and
unsupported capabilities, but does not construct or certify runtime-owned
Manifest, Typed SOF IR, CompilerOutput, SOFRS, SOFAUDIT, SOFAction, or receipt
objects. Missing capabilities remain typed unavailable states; never infer
zero, infinity, cutoff success, nonexistence, or a nearby carrier.

The public entry points are `sof realize` for Level 1A and `sof report` for
Level 1B. `sof external-adapter` may remain as a reference convenience wrapper
for a canonical-compilable example, but it must reject extension-only results.
`sof explain run <run-directory>` must remain deterministic and structured. It
may expose source, adapter, capability, evidence, validator, uncertainty, and
negative-boundary information from artifacts, but it must not invent a
scientific summary or rely on an LLM. `sof init-adapter --domain <name>` emits
a scaffold explicitly marked `scaffold / not runnable`; keep positive/hostile
fixtures, adapter tests, and known non-claims in that scaffold.

Do not reorganize the internal packages merely to mirror public nouns. The
current implementation boundaries are intentional:

```text
adapters/     compiler/     reporting/
comparison/   action/       validation/
```

Use the public facade for stable access. Do not create duplicate `reports/`,
`comparisons/`, or `interpretations/` packages unless a future versioned
contract requires a real ownership boundary.

## Evidence Boundary

Use the upstream reader-facing levels exactly:

- `Theorem`
- `Computational Certificate`
- `Computational Observation`
- `Research Program`

A carrier's raw output is not a certificate. A passing extension validator
creates a checked extension artifact, not an upstream SOF claim. Emit canonical
`CERTIFIED` only through an admitted Typed SOF IR and Report Profile. Missing
capabilities produce omitted or unavailable modules, never inferred substitutes.

## Validation

Run before release:

```bash
python tools/build_rust_plugins.py
python tools/verify_digests.py
python tools/import_candidate_contracts.py --upstream-root ../rime-lite
python -m unittest discover -s tests
python tools/check_wheel_install.py
```

Do not commit ordinary contents of `runs/`. Promote only compact fixtures,
certificates, and release artifacts deliberately.

Before documenting a new public workflow, verify it from a clean checkout or
mark it non-runnable. Update the relevant README and tests together. Public
examples must be source-addressed, contain no secrets or private data, and
list known non-claims. A passing runtime test establishes only the declared
protocol and bounded artifact closure; it does not promote a mathematical
carrier or establish domain adequacy.
