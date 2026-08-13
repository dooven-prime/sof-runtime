# Contract Layout

`contracts/compiler/v1.0/` is an immutable vendored snapshot from the
`rime-lite` commit recorded in `upstream.lock.json`. Those files are canonical
upstream inputs and must not be edited locally.

`contracts/runtime/v1.0/` defines language-neutral execution envelopes used by
this repository. Compiler Output is represented here only as a runtime output
shape; it is not a fourth canonical Paper X input and is not a SOFRS report.
Canonical artifact bytes follow
[`runtime/canonical-json-v1.md`](runtime/canonical-json-v1.md). RunResponse
execution states are not finding result states or reader-facing claim statuses.
RunRequest separates semantic environment inputs from concrete execution
metadata. RunResponse freezes the complete referenced artifact closure, and a
Promotion Package must bind that exact closure plus the frozen response.

The runtime Coordinate Evaluator declaration, registry, and intermediate
result contracts close the executable mapping from an exact upstream
SOFAUDIT coordinate identifier to a local implementation. They do not add a
coordinate family, value schema, metric, or claim status. Audit Profiles and
the vendored coordinate-semantics registry remain the normative sources for
coordinate selection and typing; missing source items remain typed
unavailable rather than becoming zero-valued findings.

The ExpertAdapter realization contracts are deliberately split. The strict
`expert-realization-candidate` shape is the current canonical-compilable
reference variant. `expert-extension-realization-candidate` records a
validated extension-only realization; it is not eligible for Manifest, Typed
SOF IR, CompilerOutput, or SOFRS assembly until an upstream carrier contract
is accepted. `expert-analogue-realization-candidate` is canonical-compilable
only through the published `diagnostic_analogue` branch. It records declared
API-level descriptors and an explicit negative strict boundary; it does not
manufacture a sectorization, operator carrier, internal mechanism, or action
semantics.

`contracts/service/v1.0/` defines runtime-owned orchestration envelopes for
Python, CLI, HTTP, and MCP projections. It owns request routing, workspace
confinement, job lifecycle, and artifact retrieval only. A `JobState` is not a
SOF result state, evidence level, disposition, or claim status. Service
contracts do not redefine SOFRS, SOFAUDIT, SOFAction, their profiles, or their
validators.

`contracts/action/v2.0/` is the immutable, byte-pinned Paper XIV SOFAction v2
schema and validation-receipt contract imported through `upstream.lock.json`.
The runtime action validator replays the closed Policy Predicate Language,
checks the Paper XIII audit and validation-receipt closure, preserves the audit
projection, and verifies candidate-set faithfulness. Passing that validator
does not establish policy correctness, authorization, execution, outcome, or
causal effect.

`contracts/reporting/v2.0/` is the immutable SOFRS v2 report envelope, Assembly
Profile, and validation-receipt snapshot imported from the release-content
commit in `upstream.lock.json`. A passing reporting test establishes assembly
conformance to those bytes; it does not establish adapter adequacy.

`contracts/comparison/v2.0/` similarly vendors the published SOFAUDIT v2
schema, receipt, coordinate registry, and official profiles. JSON Schema
validates shape only. Runtime semantic
validation additionally rechecks the two SOFRS reports and receipts and
recomputes roles, regime, profile closure, alignment properties, inherited
guards, comparison basis, claim compatibility, and artifact closure. Native
runtime audits also bind the evaluator registry, implementation, and each
coordinate result into the receipt closure. Runtime validation additionally
requires the registry snapshot to equal the installed trusted registry,
checks the implementation artifact against the registry-pinned implementation
digest, and replays every evaluator from the two validated reports plus the
bound alignment and profile. The complete replay result must equal its bound
evaluation-result artifact. Source selection requires one enabled module to
bind the selected claim and finding, while pair endpoints are normalized from
an explicitly declared label or zero-based-index encoding into the report's
sector labels. The analogue descriptor evaluator instead requires an exact
declared observable-key identity and records coordinatewise values; it does
not infer descriptor alignment or interpret `repair_probe_result` as an action
or effect. Passing that validator does not establish that a declared reference
is true or that an alignment is scientifically preferred.

The coordinate-evaluator registry and implementation modules under
`contracts/runtime/v1.0/` are immutable v0.4 validation inputs. Adding or
replacing an evaluator requires a registry/module v2 rather than editing v1,
so historical v1 audits remain verifiable against their original trusted
execution closure.

`contracts/sources/` defines domain input formats. `contracts/extensions/`
defines carrier-specific payloads. An extension may consume or reference
upstream objects, but proximity to an upstream carrier does not identify their
semantics. An extension cannot add a canonical carrier kind, result state, or
claim status.

An extension that studies a genuinely different target, such as image-rank
collapse rather than sector-pair word accessibility, remains extension-typed.
Passing its validator does not authorize encoding it as the nearest upstream
carrier. Canonical compilation begins only after an accepted upstream contract
can represent the field without reinterpretation.

Verify the vendored snapshot with:

```bash
python tools/verify_digests.py
python tools/import_contracts.py --upstream-root ../rime-lite
```

Restore it from the frozen Git commit with:

```bash
python tools/import_contracts.py --upstream-root ../rime-lite --write
```

Stable semantic changes are proposed and versioned in `rime-lite` before a new
upstream snapshot is imported here.
