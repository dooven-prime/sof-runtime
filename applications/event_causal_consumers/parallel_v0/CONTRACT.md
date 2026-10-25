# Q2 Parallel Fiber Checker v0

## Authority and Scope

This is a local acceptance prototype, not a distributed BFS, installed runtime
API, new Q2 language, Paper XL release replacement or SOF claim. The existing
Python typed Q2 compiler, global generated-domain enumerator and streaming
replay remain unchanged. Initially accept only environments with 2--4 carrier
positions and 2--4 fixed shards. All expressions use `ECC_SYN_V1`; the Rust
worker interprets a versioned compiled IR supplied by the trusted Python
compiler, not arbitrary callbacks or a separately owned static type system.

Coordinator, workers and reducer share orchestration patterns, not mathematical
reduction rules with MaleCNS, automata or Solana applications. No performance
advantage is claimed by this version.

## Exact Domain and Binding

The coordinator saturates the existing log model without a word-length bound,
then materializes the complete registered causal-summary image and its two raw
successors per state. Predecessor histories are witnesses, not state keys.
Round-robin state IDs partition that fixed image into 2--4 disjoint shards.
The plan binds the raw request, compiled IR, whole state/transition/history
table, exact shard memberships, code closure, Rust binary and encoding versions.
Digests bind bytes; they are not authenticated execution attestations.

The reducer reconstructs the plan from the original request using the trusted
enumerator and checks exact agreement. It checks every shard ID and assigned
state ID once, exact task/input/version bindings and coverage digests. A
COMPLETE flag or digest asserted by a worker is not coverage proof by itself.
V0 additionally recomputes every member's q/signature in Python. This deliberate
reference gate detects forged summaries as well as conformance defects and
makes this a correctness prototype, not an accelerated decision backend.

Empty registration, incomplete enumeration, missing/duplicate/foreign shards,
membership drift, crashes, timeouts, invalid artifacts and version mismatch
produce `UNRESOLVED`, never PASS. A result may retain `domain_complete=true`
while worker coverage is incomplete: these are distinct facts. A syntactically
invalid request is unresolved with an explicit invalid-input reason here; it
is not a mathematical counterexample.

## Worker Output

A fresh Rust process receives one exact shard task. It computes typed q/report
values, enabled labelled commands and q of actual successors. Its causal step
updates the complete partition, preserves the selected event and appends the
selected absorption record only if that carrier participates. It does not
read another shard, accept Python-computed signatures or emit PASS.

Each `fiber_record` groups one exact `(q, signature)` and lists all covered
state IDs plus a representative ID. Every distinct signature is retained.
`local_conflicts` is diagnostic and checked for consistency; absence of a local
conflict is not authority for a global pass. Disabled commands have no successor
entry; a valid Option-none q is not command undefinedness. Atom/Pos/Nat/Bool
remain type-distinct and command labels with identical actions remain distinct.

V0 uses UTF-8 canonical JSON and internal atom indices; Nat values use exact
decimal strings with arbitrary-precision Rust arithmetic. Worker steps, input
size, expression depth, numeric output size and parent timeouts are explicit
safety bounds. Exceeding one returns unresolved, never integer wraparound or
an incomplete exact result. No general resource/complexity theorem is implied.

## Reducer Decision

After full coverage/binding/reference verification, compare all distinct
signatures in every q fiber, including fibers crossing shards. Use the existing
global clause priority: all R reports, then all G commands, then T for commonly
enabled commands. Do not stop at a local T conflict while a cross-shard R
conflict remains unexamined.

Only the reducer may emit application-local `PASS`, `FAIL` or `UNRESOLVED`.
PASS requires a nonempty complete domain and all checks. FAIL additionally
contains the existing Q2 rejection object built from two actual predecessor
histories and checked by its independent streaming replay. Replay failure is
unresolved. For this prototype, even a valid local conflict does not bypass
the required complete-coverage gate. Replay verifies the two histories, not
global domain completeness, and shares declared types/interpreter with Q2.

## Receipt and Controls

Retain request, plan, all task/results and decision under a new output directory,
with per-file digests, source/binary closure, versions, worker outcomes and
coverage/reference/replay facts. Such a local closure is not a public release,
cryptographic worker attestation or independent mathematical certificate.
`--verify-run` checks the confined regular-file inventory and digests, exact
saved tasks and current implementation binding, then regenerates the domain
and reruns the reducer/replay. It does not rerun Rust workers and does not
authenticate the receipt itself. A valid closure can record an unresolved
decision; closure validity does not turn it into PASS.

Acceptance uses existing nine typed Q2 controls and 2/3/4 shards; compare
decision, clause and replay, not the exact words selected by another traversal.
Hostile controls include missing/duplicate/overlapping state coverage, altered
binding/version, process failure/timeout, malformed signatures and corrupted
histories. Include a case with individually conflict-free shards whose same-q
signatures disagree globally. No such fault may produce PASS.
