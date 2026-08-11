# Action Contracts

`v2.0/` is an immutable, byte-pinned snapshot of the published Paper XIV
SOFAction v2 schema and validation-receipt contract. Their provenance is
recorded in `../upstream.lock.json`.

Runtime validation independently replays the closed Policy Predicate Language,
checks the bound SOFAUDIT receipt and audit projection, and regenerates the
finite candidate set. Passing these checks establishes protocol conformance,
not policy correctness, authorization, execution, outcome, or causal effect.

The upstream publication defines the contract. This runtime snapshot and its
validator provide implementation-level conformance evidence only.
