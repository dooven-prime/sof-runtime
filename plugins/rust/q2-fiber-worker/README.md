# Q2 Fiber Worker v0

Pure task processor for the application-owned
[parallel fiber protocol](../../../applications/event_causal_consumers/parallel_v0/CONTRACT.md).
It receives one JSON task file and emits a fiber summary or an unresolved
error. It never emits PASS, enumerates a global domain or issues a receipt.

```text
q2-fiber-worker TASK.json
```

The versioned IR is compiled by the existing Python Q2 static checker. Rust
implements value interpretation and complete causal-summary updates separately;
it does not own a second static grammar. Type tags remain part of keys; Nat
payloads are decimal strings interpreted with `num-bigint`, and block atoms
are internal indices in the bound environment. Command labels are not
deduplicated by their raw letter.

Outputs group each distinct `(q, R/G/T signature)` with exact state members
and a representative. Local conflicts are diagnostic only. The application
reducer must check bindings, coverage, cross-shard fibers and histories. V0
also checks every signature through the Python reference, so this is not an
accelerated or externally independent Q2 backend.

Limits: task bytes 16 MiB, compiled expression depth 100 (JSON decoding can
impose a stricter nesting limit), each interpreted value/argument aggregate
1 MB, Nat arithmetic 4096 decimal digits, and the task's step budget. The
Python parent separately imposes its worker timeout. Exceeding a limit or a
malformed task exits nonzero and cannot support a global pass. No resident
service, network endpoint, sandbox or distributed execution attestation is
implemented.
