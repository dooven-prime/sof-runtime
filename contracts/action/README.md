# Action Contracts

`candidate-v2.0/` is a byte-pinned integration snapshot of the active Paper
XIV SOFAction v2 schema and validation-receipt contract. Their provenance is
recorded in `../upstream-candidate.lock.json`.

Runtime validation independently replays the closed Policy Predicate Language,
checks the bound SOFAUDIT receipt and audit projection, and regenerates the
finite candidate set. Passing these checks establishes protocol conformance,
not policy correctness, authorization, execution, outcome, or causal effect.

This candidate snapshot is integration evidence, not upstream publication or
semantic promotion.
