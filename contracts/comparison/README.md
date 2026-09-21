# Comparison Contracts

`v2.0/` is the immutable runtime snapshot of the published SOFAUDIT v2 schema,
validation receipt, coordinate registry, and official Audit Profiles. Their
upstream paths, digests, and release-content commit are recorded in
`../upstream.lock.json`.

The schema defines shape. Runtime acceptance additionally requires semantic
validation of report roles and receipts, source-addressed Audit Profile and
coordinate-registry closure, regime and profile closure,
alignment map properties, inherited guard state, coordinate availability,
comparison-basis completeness, epistemic compatibility, and artifact digest
closure. An external-object claim also requires a declared independent oracle.
Every admitted Audit Profile must require both `audit-profile` and
`coordinate-semantics-registry` evidence roles.

A passing comparison validator establishes conformance relative to the
declared alignment and comparison specification; it does not make the selected
reference a truth oracle or establish adapter adequacy.

`v2.1/` contains exactly the published SOFAUDIT v2.1 audit and receipt schemas.
The coordinate registry remains v1.0 and the official comparison profiles
remain v2.0. New Level 2 runs generate v2.1 by default; v2.0 validation stays
available, while migration validates the complete old closure and the two
explicitly migrated SOFRS inputs before issuing a new v2.1 receipt.
