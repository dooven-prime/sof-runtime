# Comparison Contracts

`candidate-v2.0/` is a byte-pinned integration snapshot of the active Paper
XIII SOFAUDIT v2 schema, validation receipt, coordinate registry, and official
Audit Profiles. Their provenance is recorded in
`../upstream-candidate.lock.json`.

The schema defines shape. Runtime acceptance additionally requires semantic
validation of report roles and receipts, source-addressed Audit Profile and
coordinate-registry closure, regime and profile closure,
alignment map properties, inherited guard state, coordinate availability,
comparison-basis completeness, epistemic compatibility, and artifact digest
closure. An external-object claim also requires a declared independent oracle.

This candidate snapshot is integration evidence, not upstream publication or
semantic promotion. A passing comparison validator establishes conformance
relative to the declared alignment and comparison specification; it does not
make the selected reference a truth oracle or establish adapter adequacy.
