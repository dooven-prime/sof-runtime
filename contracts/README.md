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

The ExpertAdapter realization contracts are deliberately split. The strict
`expert-realization-candidate` shape is the current canonical-compilable
reference variant. `expert-extension-realization-candidate` records a
validated extension-only realization; it is not eligible for Manifest, Typed
SOF IR, CompilerOutput, or SOFRS assembly until an upstream carrier contract
is accepted.

`contracts/action/candidate-v2.0/` is the byte-pinned Paper XIV SOFAction v2
schema and validation-receipt candidate imported through
`upstream-candidate.lock.json`. The runtime action validator replays the
closed Policy Predicate Language, checks the Paper XIII audit and validation
receipt closure, preserves the audit projection, and verifies candidate-set
faithfulness. Candidate import does not promote Paper XIV into the canonical
upstream contract surface.

`contracts/reporting/candidate-v2.0/` is a byte-pinned integration snapshot of
the active Paper XII SOFRS v2 candidate: report envelope, Assembly Profile, and
validation receipt. It remains outside `upstream.lock.json` because the source
schemas are not yet reproducible from a `rime-lite` commit. The separate
`upstream-candidate.lock.json` records this limitation explicitly. A passing
candidate reporting test establishes assembly conformance to those bytes; it
does not publish or promote the protocol.

`contracts/comparison/candidate-v2.0/` similarly vendors the active Paper XIII
SOFAUDIT v2 schema, receipt, coordinate registry, and official profiles. JSON
Schema validates shape only. Runtime semantic
validation additionally rechecks the two SOFRS reports and receipts and
recomputes roles, regime, profile closure, alignment properties, inherited
guards, comparison basis, claim compatibility, and artifact closure. Passing
that validator does not establish that a declared reference is true or that an
alignment is scientifically preferred.

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
python tools/import_candidate_contracts.py --upstream-root ../rime-lite
```

Restore it from the frozen Git commit with:

```bash
python tools/import_contracts.py --upstream-root ../rime-lite --write
```

Stable semantic changes are proposed and versioned in `rime-lite` before a new
upstream snapshot is imported here.
