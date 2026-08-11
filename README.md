# sof-runtime

`sof-runtime` implements and applies versioned SOF contracts. It does not
redefine the mathematical objects, theorems, or ownership boundaries of the
RIME manuscripts. Canonical semantic authority remains in
[`dooven-prime/rime-lite`](https://github.com/dooven-prime/rime-lite).

Researchers may adopt the runtime protocol without accepting every SOF
theorem or implementing every carrier. Protocol adoption requires explicit
types, policies, provenance, validation, and artifact identity. It does not
transfer ownership of domain conclusions to SOF.

> The runtime controls language, conformance, and artifacts. Domain plugins
> remain responsible for domain semantics and conclusions.

## Boundary

The repository supports two related paths. The open execution path is usable
by domain applications and experimental extensions:

```text
domain source
  -> adapter declaration
  -> RunRequest
  -> plugin result
  -> content-addressed artifacts
  -> independent validation
  -> RunResponse
  -> promotion package
```

The canonical compilation path is available only when every emitted field is
expressible under the frozen upstream contracts:

```text
validated domain artifacts
  -> Capability Manifest
  -> Typed SOF IR
  -> Compiler Report Profile
  -> Compiler Output
  -> SOFRS Assembly Profile
  -> .sofreport + validation receipt
```

The layers remain separate:

- a Capability Manifest declares capabilities and contains no results;
- Typed SOF IR records typed objects, findings, evidence, and derivations but
  does not choose presentation;
- a Compiler Report Profile selects modules but cannot manufacture evidence;
- Compiler Output is `ClaimItem_v1 | DegradationItem_v1`, not a SOFRS report;
- a SOFRS Assembly Profile renders that exact output but cannot add, remove,
  duplicate, or retype a normative item;
- debug serializers are implementation tools, not manuscript authorities.

A validated runtime extension does not enter Typed SOF IR or
Compiler Output. New carrier semantics are first proposed and versioned in
`rime-lite`; this repository then imports the accepted contract by digest.

Canonical compiler contracts are vendored immutably from the commit recorded
in `contracts/upstream.lock.json`. Experimental carrier payloads live under
`contracts/extensions/`; they do not modify the upstream contracts.

The published SOFRS v2 and SOFAUDIT v2 contracts are imported immutably under
`contracts/reporting/v2.0/` and `contracts/comparison/v2.0/`; their upstream
commit and byte digests are pinned by `contracts/upstream.lock.json`. The
unpublished SOFAction v2 contract remains under
`contracts/action/candidate-v2.0/` and is isolated by
`contracts/upstream-candidate.lock.json`.

## Runtime Shape

Python is the reference control plane. JSON Schema, JSON/JSONL, artifact URIs,
SHA-256 digests, and explicit contract versions form the public interface.
Python classes, NumPy arrays, and pickle files are not interchange formats.
JSON artifacts use one deterministic canonical byte encoding so certificate
input digests and content-addressed artifact digests identify the same bytes.
The exact `sof-cjson-v1` byte profile is frozen in
[`contracts/runtime/canonical-json-v1.md`](contracts/runtime/canonical-json-v1.md).
Source checkouts use their local `contracts/` tree. Installed wheels carry the
same contract inventory under the environment prefix and use the current
directory as the default artifact workspace; deployments may set
`SOF_RUNTIME_WORKSPACE` explicitly.

Every request carries two identities. `semantic_run_id` is the SHA-256 identity
of source, plugin semantics, carrier, contract versions, policies, and the
declared `semantic_environment` projection. Algorithm mode, arithmetic
backend, dependency-lock digest, and semantics-affecting feature flags belong
in that projection. Concrete execution metadata such as execution mode,
implementation runtime/version, operating system, and machine architecture is
retained separately in `runtime_environment` and does not change semantic
identity. Hostnames, process IDs, timestamps, and temporary paths are never
semantic inputs. An automatically generated `execution_id` hashes the
semantic identity, concrete runtime environment, start time, and a nonce; it
identifies one actual attempt. Execution status (`SUCCEEDED`, structured failure,
cancellation, or unsupported policy) is independent of finding result state
and reader-facing claim status.

Every RunResponse also freezes its pre-response artifact closure: canonical
ordered artifact IDs, each URI/schema/digest tuple, an artifact-manifest
digest, artifact count, and the validator-certificate digest. A promotion
package must bind exactly that closure plus the frozen RunResponse artifact.
Additional files in a run directory are not evidence unless a new response
identity explicitly closes over them.

The initial runtime provides:

- schema and digest validation;
- a content-addressed artifact store;
- in-process and external-executable plugin boundaries;
- capability-aware compilation;
- faithful `CompilerOutput`-to-SOFRS assembly, report revalidation, and
  digest-bound validation receipts against the pinned Paper XII candidate;
- semantic SOFAUDIT validation against the pinned Paper XIII candidate,
  including report/receipt closure, alignment-map recomputation, guard and
  coordinate coupling, comparison-basis checks, and independent-oracle gates;
- candidate SOFAction v2 validation against a Paper XIII receipt-bound
  audit, including closed Policy Predicate replay, audit projection
  preservation, carrier closure, and Candidate Action Set regeneration;
- debug JSON and Markdown inspection;
- an external ExpertAdapter Level 1A workflow that validates a high-level
  realization candidate without assuming canonical carrier eligibility;
- a Level 1B workflow that enters Manifest, Typed SOF IR, CompilerOutput, and
  SOFRS assembly only for a canonical-compilable realization;
- two complete validated extension slices with distinct source and carrier
  semantics: synchronizing-automata rank collapse and single-letter Markov
  positive-word support.

## Public Runtime Surface

The application-facing surface is intentionally smaller than the internal
package tree. The stable runtime objects are:

| Object | Meaning | Stage |
|---|---|---|
| `Realization` | A validated domain realization with runtime-derived compilation eligibility | Level 1A |
| `Report` | A receipt-validated `.sofreport` artifact from a canonical-compilable realization | Level 1B |
| `Comparison` | A bounded `.sofaudit` produced from two reports and explicit alignment | Level 2 |
| `Interpretation` | A receipt-validated policy-relative interpretation trace | Level 3 |
| `CandidateAction` | One member of the generated finite candidate set | Level 3 |

These objects are handles over source-addressed JSON artifacts. They are not a
second semantic model and do not replace the schemas or the owning RIME
papers. The Python facade is available from `sof_runtime.api`; the thin
expert-adapter types are available from `sof_runtime.sdk`.

The staged workflow is:

```text
Level 1A ExpertAdapter -> Validated Realization
Level 1B canonical-compilable Realization -> Report
Level 2  Report + Report + alignment/profile -> Comparison
Level 3  Comparison + ActionContext + PolicyProfile -> Interpretation + CandidateAction*
```

Level 3 ends at candidate generation. The runtime does not select a
candidate, request or verify authorization, execute an action, certify an
effect, or prove that a candidate is correct. The current Paper XIV binding
uses one `PolicyProfile` as the normative input for interpretation and
candidate generation; a future semantic/action rulebook split is research,
not a second runtime interface.

An extension-only realization is a valid Level 1A result. It stops with a
source-addressed realization receipt and may be packaged as a promotion
proposal. It must not create a Manifest, Typed SOF IR, CompilerOutput, or
SOFRS report until the corresponding carrier contract is accepted upstream.

There is intentionally no REST service contract in this release. Applications
may call `RuntimeAPI`, use the `sof` CLI, or implement the external executable
plugin protocol. A future service wrapper must preserve these source-addressed
operations rather than introduce a competing semantic contract.

Technology responsibilities are explicit:

| Responsibility | Technology / owner |
|---|---|
| Theory, normative semantics, and release identity | `rime-lite` |
| Language-neutral contracts | JSON Schema, canonical encoding, and digests |
| Reference runtime and orchestration | Python |
| High-performance kernels | Rust, Julia, or C++ plugins |
| Formal proof artifacts | Lean source, build record, and digest |
| Large tabular and array data | Parquet, NPZ, and Zarr |
| Application-facing typed output | Compiler Output, then the downstream report protocol |

The repository separates immutable upstream contracts, local runtime
envelopes, carrier extensions, applications, profiles, and tests:

```text
contracts/       upstream locks, compiler/reporting contracts, runtime envelopes, extensions
src/sof_runtime/ adapters, carriers, validators, compiler, artifacts, CLI
applications/    domain-specific admission and claim boundaries
plugins/         in-process and external executable declarations
profiles/        versioned compiler selections
examples/        compact source fixtures
tests/           conformance, golden, regression, and cross-language checks
runs/            ignored local executions
```

Large runtime outputs belong under `runs/` and are ignored by Git. Reviewed
certificates, summaries, and compact fixtures become promotion candidates only
through an explicit source-addressed package.

## External Adapter Workflow

The general application-facing workflow stops at a validated realization:

```text
Source Bundle + ExpertAdapter -> validated Realization + receipt
canonical-compilable Realization + Report Profile -> valid SOFRS + receipt
```

An external adapter implements `describe`, `inspect_source`, `realize`, and
`evidence`. Its `realize` result is a high-level
`ExpertRealizationCandidate`; it must not contain canonical Manifest or Typed
SOF IR. Level 1A validates and source-addresses that candidate. Only when the
runtime classifies it as `canonical_compilable` does Level 1B build the
runtime-owned Manifest, Typed SOF IR, CompilerOutput, and SOFRS receipt. The
reference case is under
[`examples/external-adapter-finite-state/`](examples/external-adapter-finite-state/).

Run the generic Level 1A stage with:

```text
sof realize \
  examples/external-adapter-finite-state \
  --run-dir runs/external-adapter-finite-state
```

For the canonical-compilable reference case, continue with Level 1B:

```text
sof report runs/external-adapter-finite-state \
  --out-dir runs/external-adapter-finite-state
```

The old `sof external-adapter CASE --run-dir DIR` command remains as a
reference convenience wrapper for these two stages and rejects extension-only
realizations. Missing adapter capabilities remain `NOT_DECLARED`; the runtime
never turns them into zero, cutoff success, or nonexistence.

The public adapter contract is intentionally limited to four JSON-compatible
methods:

```python
class ExpertAdapter:
    def describe(self) -> dict: ...
    def inspect_source(self, source: dict) -> dict: ...
    def realize(self, source: dict, request: dict) -> dict: ...
    def evidence(self) -> dict: ...
```

`describe()` declares domain objects, carriers, observables, conventions, and
unsupported capabilities. `inspect_source()` performs the adapter's declared
source checks. `realize()` returns a domain realization candidate.
`evidence()` supplies bounded adapter evidence. The runtime validates these
outputs and constructs the internal Manifest, Typed SOF IR, Compiler Output,
report, and receipts. Adapter-supplied evidence is not independent merely
because it is schema-valid, and an adapter must not validate its own
runtime-owned report by merely returning that report.

## Level 2 and Level 3

The reference runtime exposes the next two stages as stable, source-addressed
objects:

```text
Realization -> Report -> Comparison -> Interpretation -> CandidateAction
```

`Comparison` consumes two validated SOFRS reports and emits a bounded SOFAUDIT
under an explicit alignment and comparison profile. `Interpretation` consumes
that SOFAUDIT, its validation receipt, an `ActionContext`, and a
`PolicyProfile`; it emits a policy-relative decision trace and a finite
`CandidateAction` set. Candidate actions are not selected, authorized,
executed, or certified as effective by this workflow.

`RuntimeAPI.compare()` requires `alignment`, `profile`, and `out_dir` as
explicit keyword inputs. `RuntimeAPI.full_pipeline()` likewise requires
`alignment`, `comparison_profile`, `action_context`, `policy_profile`, and
`run_dir`. The CLI requires `--alignment` and `--comparison-profile` for
`sof compare` and `sof full-pipeline`. No semantic API loads comparison inputs
implicitly from an example directory; the reference fixture only supplies
convenient paths for callers.

The Python facade is intentionally small. The general entry point is staged:

```python
from sof_runtime.api import RuntimeAPI

runtime = RuntimeAPI()
reference_realization = runtime.realize(
    "examples/external-adapter-finite-state/reference",
    "runs/full-pipeline/reference",
)
reference_report = runtime.report(reference_realization)
target_realization = runtime.realize(
    "examples/external-adapter-finite-state/target",
    "runs/full-pipeline/target",
)
target_report = runtime.report(target_realization)
comparison = runtime.compare(
    reference_report,
    target_report,
    alignment="examples/external-adapter-finite-state/comparison/alignment.json",
    profile="profiles/comparison/external-adapter-identity-v2.0.json",
    out_dir="runs/full-pipeline/comparison",
)
interpretation, candidates = runtime.interpret(
    comparison,
    "examples/external-adapter-finite-state/action/context.json",
    "examples/external-adapter-finite-state/action/policy.json",
    "runs/full-pipeline/action",
)
```

For a canonical-compilable reference case, the equivalent convenience call is
`runtime.realize_and_report(case_directory, run_directory)`. This convenience
does not change the Level 1A/1B eligibility boundary.

The complete reference workflow is also available as one call:

```python
result = runtime.full_pipeline(
    reference_case="examples/external-adapter-finite-state/reference",
    target_case="examples/external-adapter-finite-state/target",
    alignment="examples/external-adapter-finite-state/comparison/alignment.json",
    comparison_profile="profiles/comparison/external-adapter-identity-v2.0.json",
    action_context="examples/external-adapter-finite-state/action/context.json",
    policy_profile="examples/external-adapter-finite-state/action/policy.json",
    run_dir="runs/full-pipeline",
)
```

Equivalent CLI commands are available for scripted use:

```text
sof compare REFERENCE.sofreport.json REFERENCE.receipt.json TARGET.sofreport.json TARGET.receipt.json --alignment ALIGNMENT.json --comparison-profile COMPARISON_PROFILE.json --out-dir runs/comparison
sof interpret AUDIT.sofaudit.json AUDIT.receipt.json context.json policy.json --out-dir runs/action
sof full-pipeline examples/external-adapter-finite-state/reference examples/external-adapter-finite-state/target examples/external-adapter-finite-state/action/context.json examples/external-adapter-finite-state/action/policy.json --alignment examples/external-adapter-finite-state/comparison/alignment.json --comparison-profile profiles/comparison/external-adapter-identity-v2.0.json --run-dir runs/full-pipeline
```

The API objects are handles over validated artifacts, not a second semantic
model. Their payload properties reload the source-addressed JSON when needed;
the runtime contracts and owning RIME papers remain authoritative.

## Expert Onboarding

The public SDK is intentionally a thin import surface:

```python
from sof_runtime.sdk import (
    ExpertAdapter,
    SourceBundle,
    RealizationCandidate,
    CapabilityDeclaration,
)
```

These names describe JSON-shaped adapter inputs and outputs. They do not give
an adapter ownership of runtime-owned Manifest, Typed SOF IR, report, audit,
action, or receipt artifacts.

Create a starter directory with:

```text
sof init-adapter --domain network-routing
```

The generated directory is explicitly marked `scaffold / not runnable`. It
contains an adapter declaration, case file, source fixture, positive/hostile
fixture locations, tests, and a README with known non-claims. The scaffold
must be completed before it can enter the external-adapter workflow.

For an existing run directory, use:

```text
sof explain run runs/full-pipeline
```

This emits structured JSON rather than free-form prose. It traces source,
adapter declaration, declared carriers and unsupported capabilities, report
and validator receipts, comparison coordinates, interpretation uncertainty,
candidate evidence references, and known non-claims. It answers provenance
questions from the artifacts themselves; it does not infer a scientific
meaning or ask an LLM to summarize one.

The internal package layout remains implementation-oriented. `adapters`,
`compiler`, `reporting`, `comparison`, `action`, and `validation` retain their
current ownership boundaries. `sof_runtime.sdk`, the CLI, and the source-
addressed artifact objects are the public facade; duplicate `reports/`,
`comparisons/`, or `interpretations/` packages are intentionally not created.

Every generated adapter scaffold contains a `known non-claims` section. Keep
that section current when adding an example: a scaffold is not runnable until
the domain author supplies source semantics, positive and hostile cases, and
adapter tests. Public examples must either run from a clean checkout or state
explicitly why they do not run; they must not contain secrets, private data,
or undeclared external API dependencies.

## Conformance and Promotion

Conformance is scoped rather than all-or-nothing:

| Scope | What it establishes | What it does not establish |
|---|---|---|
| Runtime protocol | schema, digest, provenance, plugin, and artifact conformance | SOF admission or scientific truth |
| Extension validation | declared validator reproduced the bounded result | canonical carrier status |
| SOF compilation | frozen Manifest/IR/Profile contracts admitted an item | adapter adequacy or a SOFRS report |
| SOFRS assembly | exact CompilerOutput items were faithfully rendered and receipt-bound | adapter adequacy, cross-report alignment, or publication status |
| SOFAUDIT comparison | coordinates were computed faithfully under declared alignment and comparison semantics | reference truth, object correctness, interpretation, or action |
| SOFAction runtime | declared context/policy interpretation and bounded candidate-set trace conform to the runtime binding | action correctness, feasibility, authorization, causal effect, or selection |
| Upstream promotion | `rime-lite` accepted a versioned semantic contract | validity outside the declared scope |

The promotion flow is deliberately one-way:

```text
runtime experiment
  -> validated extension artifacts
  -> source-addressed promotion proposal
  -> normative review and versioning in rime-lite
  -> refreshed upstream lock in sof-runtime
```

See [`docs/CONFORMANCE_AND_PROMOTION.md`](docs/CONFORMANCE_AND_PROMOTION.md).

## Data and Evidence

Findings use a stable runtime envelope for identity, scope, evidence level,
policy references, and provenance. Mathematical values remain in
carrier-specific payloads. A shared envelope does not imply a shared payload
or a universal carrier.

Use formats according to the artifact, not according to the implementation
language:

| Content | Interchange format |
|---|---|
| Manifest, IR, Profile, finding, certificate | JSON |
| Large census or tabular output | Parquet |
| Sparse matrices | NPZ or Matrix Market |
| Dense arrays | NPZ |
| Large trajectories and multidimensional arrays | Zarr |
| Graphs | edge list or GraphML with JSON metadata |
| Formal certificates | Lean source, build record, and digest |
| Figures and documents | original media plus ArtifactRef |

Typed IR stores artifact references and digests rather than embedding large
matrices, complete censuses, or trajectories.

## Quick Start

```bash
python -m pip install -e .
sof validate-source examples/automata/cerny4.json
sof admit examples/automata/cerny4.json --out runs/cerny4/manifest.json
sof run rank-collapse examples/automata/cerny4.json --run-dir runs/cerny4
sof validate runs/cerny4/run-response.json
sof validate-promotion runs/cerny4/promotion-package.json runs/cerny4/run-response.json

sof validate-source examples/markov/cycle4-lazy.json
sof admit examples/markov/cycle4-lazy.json --out runs/cycle4-lazy/manifest.json
sof run positive-word-support examples/markov/cycle4-lazy.json --run-dir runs/cycle4-lazy
sof validate runs/cycle4-lazy/run-response.json
sof validate-promotion runs/cycle4-lazy/promotion-package.json runs/cycle4-lazy/run-response.json
```

Run the conformance suite with:

```bash
python tools/build_rust_plugins.py
python -m unittest discover -s tests
python tools/verify_digests.py
python tools/import_candidate_contracts.py --upstream-root ../rime-lite
python tools/check_wheel_install.py
```

## First Application

The automata adapter declares finite coordinate sectors and labelled
deterministic transition operators. The rank-collapse plugin computes exact
reachable image subsets and reset depth by exhaustive finite BFS. Its validated
payload remains extension-specific: rank collapse is not pairwise word
accessibility, route depth, or Lie/Hall depth. Until an independent
rank-collapse carrier is accepted upstream, this application emits a checked
RunResponse and promotion-candidate artifacts, not a canonical Typed SOF IR or
Compiler Output.

## Second Application

The Markov adapter declares singleton coordinate sectors and one exact
rational nonnegative operator `P`. The positive-word plugin records ordered
off-diagonal first-hit support depths in powers `P^d`; a Floyd-Warshall
validator recomputes the BFS-produced census from canonical source artifacts.
This application has no transformation monoid, reset word, reachable-subset
orbit, or rank-collapse finding. It exercises the same RunRequest, artifact,
failure, validation, RunResponse, and promotion contracts with different
domain semantics, demonstrating that those runtime contracts are not tied to
synchronizing automata.

Positive-word support remains distinct from mixing time, route depth,
algebra-saturation depth, rank collapse, and Lie/Hall depth. See
[`applications/markov_positive_word/README.md`](applications/markov_positive_word/README.md).

The BFS/Floyd-Warshall equivalence is limited to the admitted single-letter,
entrywise-nonnegative, exact-rational source with strict `> 0` positivity. It
does not authorize signed, complex, multi-letter, cancellation-sensitive, or
tolerance-relative support claims.

## Multi-Language Plugins

An external plugin reads one RunRequest JSON object from stdin and writes one
extension result payload to stdout. It cannot issue the final RunResponse. The
orchestrator canonicalizes and stores the payload, invokes the declared
validator, and only then emits RunResponse and a promotion package. Standard
error is reserved for logs and is digest-bound on failure. Rust, Julia, C++,
Java, and other implementations can participate without importing Python
runtime types.

The first non-Python fixture is a small Rust implementation of the Markov
positive-word BFS carrier. Against the Python implementation it checks exact
canonical JSON bytes, SHA-256, semantic run identity, result-bundle bytes,
artifact digest, structured process failure, and Python-validator
independence. The plugin cannot write artifact paths; storage remains an
orchestrator responsibility. This establishes one scoped Python/Rust
conformance pair, not general multi-language conformance.

## Candidate SOFRS Assembly

The reference reporting path is:

```text
Manifest + IR + Compiler Report Profile
  -> Compile_v1 recomputation
  -> bound CompilerOutput
  -> Assembly Profile
  -> item-identity-preserving .sofreport
  -> report validation receipt
```

`sof assemble-sofrs` accepts the five frozen compiler/assembly artifacts plus a
presentation JSON object. The CLI snapshots its own assembly implementation in
the output directory's content-addressed artifact store before assembling.
`sof validate-sofrs --receipt` reloads the report refs, recomputes compilation
and assembly, checks report-object equality, and snapshots the validator
implementation before issuing a receipt. `sof validate-sofrs-receipt` rechecks
the seven-artifact closure.

This path uses the immutable SOFRS v2 bytes pinned in `upstream.lock.json`.

## SOFAUDIT Validation

`sof validate-sofaudit AUDIT` first validates the Paper XIII v2 schema and then
executes cross-field semantics. It revalidates both bound SOFRS v2 reports and
their receipts, derives the comparison regime, closes the Audit Profile against
coordinate keys, recomputes alignment coverage and map properties from report
universes, derives inherited guard state, checks paired report items, recomputes
comparison-basis completeness, and verifies every referenced artifact digest.

An ordinary `comparison_audit` certificate establishes calculation relative to
the declared alignment and comparison specification. An external-object claim
is rejected unless the artifact closure contains separately identified raw
sources, independent recomputation, oracle result, and audit result with a
declared no-cache independence boundary. A declared reference alone supports
only difference from that baseline.

## Candidate SOFAction Validation

`sof validate-sofaction ACTION --repository-root ROOT` validates the unpublished
Paper XIV SOFAction v2 candidate binding. The validator consumes an exact Paper
XIII SOFAUDIT v2 artifact and its `PASS` validation receipt, replays the closed
Policy Predicate Language v1.0, rejects unresolved coordinates as affirmative
support, and independently regenerates the candidate action IDs. The schema and
receipt bytes are pinned in `upstream-candidate.lock.json`; that candidate lock
supports integration testing and does not promote Paper XIV into the canonical
contract set.

## Status

Version `0.1.0` is:

> A language-neutral runtime and artifact-conformance seed with two validated
> mathematical vertical slices and one byte-identical cross-language
> implementation.

The two slices exercise rank collapse and single-letter positive-word support
through the same evidence bus. The positive-word carrier additionally has
byte-identical Python and Rust implementations under the declared canonical
JSON and semantic-environment contracts.

The validated engineering claims for `0.1.0` are:

- two mathematically distinct carriers use the same evidence bus;
- canonical identity is consistent across the Python and Rust implementations;
- an external plugin cannot issue a validation certificate or final
  RunResponse;
- an artifact closure can be frozen and independently rechecked;
- a promotion package cannot add evidence outside the frozen closure;
- vendored upstream contracts can be verified against their recorded digests;
- SOFRS assembly preserves an exact CompilerOutput and rejects item drift;
- SOFAUDIT validation rejects fabricated role, regime, profile,
  alignment, guard, basis, claim-class, digest, and oracle declarations;
- candidate SOFAction validation replays a closed policy predicate tree and
  rejects audit-projection, receipt, carrier, and candidate-set tampering;
- the public Level 1A--3 facade exposes the staged object chain
  `Realization -> Report -> Comparison -> Interpretation -> CandidateAction`,
  with Report gated by runtime-derived canonical eligibility;
- extension-only realizations stop before Manifest/IR/CompilerOutput/SOFRS and
  retain a source-addressed promotion boundary;
- the external-adapter reference workflow has deterministic structured
  provenance output, and `sof init-adapter` generates a non-runnable scaffold
  with explicit known non-claims;
- an installed Python wheel carries the contracts and completes a validated
  runtime execution.

These claims concern runtime and artifact conformance. Version `0.1.0` is not
a new SOF specification, a scientific authority, or a publication identity.
It does not establish universal carrier coverage, general multi-language
conformance, large-scale artifact-store behavior, a published end-to-end
canonical application/report path, or scientific adequacy of an adapter. It
also does not establish candidate selection, authorization, action execution,
causal-effect certification, policy correctness, or a REST API.

## Citation and Release Identity

The immutable public source identity for this release is the
[`v0.1.0` tag](https://github.com/dooven-prime/sof-runtime/tree/v0.1.0).
`CITATION.cff` records the software citation metadata. The runtime tag identifies
an implementation; the owning RIME papers and their digest-locked contracts
remain the normative definition sources.
