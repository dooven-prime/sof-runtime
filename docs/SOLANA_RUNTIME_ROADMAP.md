# Solana Data Processing Runtime Roadmap

## Intent

The repository's next system direction is a Rust-based runtime for high-volume
Solana data processing. The engineering focus is throughput, tail latency,
operational reliability, deterministic replay, and safe plugin distribution.
This is a target, not a description of the current implementation: today's
runtime, service layer, and most application workflows are Python, and the
repository does not yet provide a production Solana ingestion or processing
runtime.

The existing SOF implementation remains useful as a versioned artifact and
diagnostic protocol, and as a reference for provenance and validation. Its
schemas do not define Solana slots, transaction ordering, fork handling,
source cursors, or chain-data replay semantics. Those need independent
contracts and explicit design before implementation.

## Engineering Priorities

The implementation principle is: **mathematics limits what may be safely
compressed; Rust implements measured hot paths; Python remains a checkable
reference.** A storage encoding, a query-specific state quotient, and a
language port are separate changes and need separate correctness and cost
comparisons. No expected speedup is an acceptance premise.

Start with single-host kernels. Distribution is justified only after measuring
the single-host bottleneck and specifying global merge, ordering, witness,
and recovery obligations. Independent source-row jobs are not equivalent to
distributing a global BFS or a consumer-state fiber check.

- **Throughput and latency:** benchmark end-to-end records per second and
  p50/p95/p99 processing latency, including decode, plugin, persistence, and
  replay costs. Publish workload shape, hardware, configuration, and failure
  behavior with every performance result.
- **Reliability:** make backpressure, bounded queues, cancellation, retries,
  crash recovery, resource limits, and partial failures observable. No dropped
  or duplicated records should be hidden behind a successful run status.
- **Replay:** bind executions to source identity, cursor/range, decoder and
  plugin versions, configuration, and relevant environment. Replaying the same
  admitted input should reproduce stable output identities, with nondeterminism
  either excluded or represented explicitly.
- **Plugin distribution:** define a versioned plugin manifest, compatibility
  rules, integrity verification, provenance, installation/update lifecycle,
  and isolation/resource policy before treating plugins as deployable units.
- **Operational clarity:** distinguish semantic output, execution attempt,
  source progress, and delivery status. Expose enough structured diagnostics
  to locate slow, failed, retried, or replayed work without using logs as the
  source of truth.

## Staged Work

### Current milestone: full-carrier MaleCNS profile census

The first serial baseline is now complete on the declared domain; see the
[full-carrier readout](../applications/malecns_profile_census/FULL_CARRIER_READOUT.md)
and its source-bound receipt. This completion is local engineering evidence,
not production or Solana acceptance. The requirements below remain the gate
for replaying or extending that baseline.

Complete the existing offline integer-profile case before adding another
kernel. Use the release-anchored edge and node files, all 163,439 eligible
sources and 25,214,058 known-sign edges, with the `somaSide` sectorization.
Compare complete canonical outputs, including the digest of exact profile
classes, rather than only the class count. Preparation verifies input hashes
and expected domain sizes; it is measured separately from execution.

The controlled baseline is serial Python versus serial release-built Rust on
the same packet and with the same output obligations. Use untimed build and
cache prefetch, warmups, alternating execution order, repeated fresh processes,
resource limits, and recorded hardware/software. Report process wall time,
observable memory peaks and explicit internal phase timings. Streaming decode,
validation and row aggregation are currently fused and must be reported
together, not presented as an isolated arithmetic kernel. Do not label this
filesystem-cache-warm test as cold-cache or decoded-data-resident execution.

The executable protocol and limits are owned by
`applications/malecns_profile_census/BENCHMARK_PLAN.md`. This is an engineering
parity and performance case, not a new Paper XVI/XVII result, biological
validation, SOF admission, or Solana workload.

### Subsequent kernel gates

1. Measure source-addressed prepared-input reuse before adding threads: the
   completed baseline's common preparation cost exceeds the Rust census cost.
   A reusable packet must bind source digests, sector/sign policy, packet
   format and preparer version, and must reject incompatible or corrupt cache
   entries. The first serial baseline did not test this cache contract; the
   separate [Prepared Input Cache v1 readout](../applications/malecns_profile_census/CACHE_READOUT_V1.md)
   now records local miss/hit/reject/rebuild behavior, real-process lifecycle
   tests and complete output parity. Source/metadata verification now costs
   more than the census itself; any relaxation needs its own validity law,
   not an unchecked mtime/existence shortcut. Distributed storage, power-loss
   durability and descendant cancellation remain separate open obligations.
   The subsequent [Cache Hit Cost Decomposition](../applications/malecns_profile_census/CACHE_COST_READOUT_V1.md)
   now separates request derivation from per-consumption validation. Fixed
   request reuse reduced local hit cost without skipping v1 checks; a bounded
   sequential Rust worker showed no stable complete-hit benefit and is not
   promoted. Structural-validation credentials or immutable input lifetimes
   need their own validity/consumption contract before checks can be removed.
   The [hash/parse fusion experiment](../applications/malecns_profile_census/FUSED_VALIDATION_READOUT_V1.md)
   is also complete: accepted records and full census outputs agree, validation
   byte passes fall from four to two per hit, and pre/post checks remain.
   CPU, wall and memory are separately recorded; the whole-hit memory result
   is essentially unchanged. Keep the candidate and stop this optimization
   round rather than continue worker or buffer tuning.
2. The first separately scoped [signed sparse-kernel baseline](../applications/malecns_sparse_kernel/READOUT_V0.md)
   is now complete on pinned carrier bytes. Target-row storage supports
   race-free `Y^T x`; numerical controls compare SciPy CSC/CSR and Rust 1/2/4
   threads. Exact BigRational/Fraction controls retain rational clipping but
   cover only the declared one-hot full-carrier actions and multistep small
   fixtures, not every Paper XVII orbit. Complete outputs, validation/setup,
   resident compute, process resources and conversion-amortization estimates
   are separate. Serial Rust is not uniformly faster than SciPy; local parallel
   benefit does not remove packet/setup costs. Keep this new packet/receipt
   identity distinct from the earlier profile census and do not promote a
   general runtime API or resident worker from this bounded result alone.
3. Parallel profile processing is optional and deferred, not a prerequisite
   for the sparse kernel or Solana slice. Preserve global exact class merges
   and deterministic output if resumed; measure it separately from language
   and validation-fusion comparisons.
4. Treat compact placed-partition pushforward and fixed-F search as independent
   candidates. The existing Rust Q2 enumerator is not the complete typed Q2
   engine. A count match does not establish state/edge or witness parity.
   A separate [Q2 Parallel Fiber Checker v0](../applications/event_causal_consumers/parallel_v0/READOUT.md)
   now checks existing 2--4 position controls with 2--4 fixed shards. Python
   saturates the global domain; Rust workers return fiber summaries, not
   PASS; the reducer checks cross-shard R/G/T consistency and actual histories.
   V0 also regenerates the domain and rechecks every signature in Python. Its
   local correctness controls are not an acceleration result or a distributed
   BFS coverage theorem, and do not block the sparse-kernel gate above.
5. Do not make porting every research application a prerequisite for Solana.
   After this first engineering case, build the separately specified chain-data
   vertical slice below. The first Solana target is off-chain processing, not
   validator execution or an on-chain program.

### 0. Solana workload contract

The first [off-chain slice v0](../applications/solana_offchain_slice/READOUT_V0.md)
now fixes finalized devnet slots 378967388--378967390: 79 legacy/v0 transactions,
raw source identities, canonical ordered JSONL and local checkpoint/replay.
The recent-range attempt was explicitly rejected for unsupported v1; it was
not turned into a skipped slot. This historical sample does not establish
provider completeness or independently verify finality. Live sources, v1,
fork/correction handling and a representative operational workload remain
separate next-scope decisions, not implied by this bounded capture.

### 1. Rust chain-data prototype

A Rust raw-JSON projection and separately implemented Python reference now
agree on the complete capture. Source transaction order, address resolution,
failure records and version bounds are explicit. Correctness controls precede
diagnostic measurements; decode/validation, commit and full process costs stay
distinct. This is an application-owned crate, not the installed runtime API,
an on-chain program or a production ingestion implementation.

### 2. Runtime contracts and recovery

V0 binds manifest and executable identity, immutable per-slot segments and a
contiguous checkpoint. Repeated execution and six real process-kill/restart
boundaries reproduce the same complete projection and state. Corrupt/foreign
state and concurrent writers are rejected. Resume reconstructs the whole
bounded input; it prevents duplicate publication rather than avoiding decode.
Power-loss durability, external exactly-once delivery, code migration and
distributed recovery have not been established.

A separate [Incremental Replay v1](../applications/solana_incremental_replay/READOUT_V1.md)
now uses the predeclared 64-slot historical capture (1,381 legacy/v0 transactions).
An externally bound, previously validated checkpoint permits prefix hashing
without block JSON decoding or projection. Only the uncommitted suffix is
projected; post-input hashing and streamed output aggregation remain. Three
paired measurements at 2/32/62 committed slots verify exact avoided work and
the same complete Python/Rust output. Later cloned-prefix integrity checks
dominate this local sample; no consistent end-to-end speedup or scale law is
claimed. V0 remains unchanged. This is still fixed-capture, single-writer,
process-interruption recovery, not live ingestion or immutable trusted storage.

A narrow [Prefix Integrity Cost Attribution v1](../applications/solana_prefix_integrity/READOUT_V1.md)
now separates raw hashes, segment validation, checkpoint/anchor and aggregate
streaming on a fixed 62-slot prefix. Its 24 probes retain all checks and balance
original/copied states and explicit read-warm order. The first copied-segment
access carries a large non-CPU, file-state-sensitive penalty; no particular
storage/security mechanism is identified. The predeclared stop condition is
met: stop fixed-capture acceleration work, without mtime shortcuts or cache
credentials. Input advancement, correction and checkpoint invalidation are
separate next semantics, not capabilities established by these experiments.

[Source Advancement and Checkpoint Invalidation v0](../applications/solana_source_advancement/READOUT_V0.md)
now checks those semantics in a narrow offline domain: distinct source,
execution and checkpoint identities; exact-evidence append; explicitly
permitted equal-record reapproval; and candidate-relative conflict refusal.
Twenty real-capture-derived/synthetic cases compare Rust execution with a
separate full Python model. Append 16--32--64 equals fresh full replay; failures
publish no new state and preserve the old checkpoint. These local credentials
are pinned test permissions, not live provider authentication. The result
does not implement reorg, rollback, live advancement, code/policy migration or
publication-stage crash recovery. Existing replay checkpoints are not silently
reinterpreted as the new source-bound schema.

A separate [Source-Transition Publication Recovery v0](../applications/solana_publication_recovery/READOUT_V0.md)
now covers that publication gap on the same fixed offline domain. An immutable
intent binds inputs/executable/destination; complete stage validation precedes
directory publication; a deterministic receipt can be recovered after a lost
response. Eighteen actual-kill points in both append and credential reapproval,
successive interruptions and corrupt/incomplete-publication refusals preserve
parent bytes and exact clean outputs. Each retry recalculates privately; this
is not a recovery speedup or power-loss guarantee. V0 remains unchanged, and
no live input, reorg or checkpoint migration is introduced. The internal
[Runtime Execution Contract Inventory](internal/RUNTIME_EXECUTION_CONTRACT_INVENTORY.md)
separates repeated orchestration patterns from application semantics. Review
public-core candidates next; do not infer a shared API or common reducer from
these application-local controls.

The internal [Rust Execution Core - Boundary Review v0](internal/RUST_EXECUTION_CORE_BOUNDARY_REVIEW_V0.md)
now records the contract-only extraction boundary. Start with raw byte identity
and a restricted, exact flat inventory; process observation is a later gate,
and local publication remains a mechanical sketch rather than a shared recovery
policy. Same-key locks, destination exclusion, quarantine and source-transition
retry are not assumed interchangeable. The first proposed shadow inspects
unchanged Solana artifacts without replacing their producer or execution
identity. No implementation, migration or public Rust API is admitted by this
design review.

The first [A0 Read-only Solana Inventory Shadow](../applications/solana_inventory_shadow/READOUT_V0.md)
now checks copied state and producer-receipt roots without replacing the original
producer. Forty-three local controls verify exact canonical inventory parity,
hostile Windows object refusal, actual interruption, observation lifetime and
separation from domain validation. A well-hashed altered transaction projection
is matched mechanically and rejected by the old application reference. The
inspector has its own observation identity and provides no future snapshot
credential. This is a single experimental A0 adapter, not extraction of the
process/publication layers or permission for broad application migration.

The second [A0 MaleCNS Prepared-Cache Inventory Shadow](../applications/malecns_cache_inventory_shadow/READOUT_V0.md)
uses the same flat inventory/NTFS mechanism, with a separate nominal cache
identity profile. Its 27 local controls include an accurately hashed packet
that the original application grammar rejects. A new run of the 43 Solana
controls also passes; old producer artifacts and the earlier observer snapshot
remain unchanged. The second shadow permits a later A extraction review only:
it does not approve common process/publication code, cache migration, a generic
directory scanner or an immutable validation credential.

The [Shared A0 Extraction Review v0](internal/SHARED_A0_EXTRACTION_REVIEW_V0.md)
now has a [passing local experiment](../applications/shared_a0_extraction_review/READOUT_V0.md):
one internal identity/codec/inventory library, 70 rerun shadow cases and an
unchanged protected SOF byte/test closure. The
[SOF compatibility lane](internal/SOF_COMPATIBILITY_GUARD_V0.md) remains stable;
the Rust data-runtime lane develops independently. Only shadows call the new
core. This does not mean the existing SOF or Solana business path has migrated,
and it does not approve common process/publication semantics or a public API.

### 3. Plugin ABI and distribution

Choose the plugin boundary based on measured isolation and performance needs.
Define ABI/API compatibility, manifest metadata, artifact digests, provenance,
installation, rollback, and resource limits. Validate plugins before enabling
them and make the selected plugin build part of replay identity. Distribution
and sandbox decisions remain open until this contract is designed.

### 4. Performance and operational acceptance

Publish reproducible throughput and latency results under normal load,
backpressure, restart, and replay. Include resource consumption and recovery
time. A release claim requires correctness and reliability checks to pass at
the same scale as the performance measurement; a microbenchmark alone is not
an acceptance result.

## Compatibility and Evidence Boundaries

- Keep the current SOF APIs and artifacts explicitly labeled as SOF workflows;
  do not silently repurpose their contracts for Solana data.
- Keep Python as the current reference/control implementation until a Rust
  execution path has equivalent declared behavior and conformance coverage.
- Treat the Q2 Rust enumerator as a bounded technical-feasibility prototype.
  Its cross-language count agreement is not a Solana benchmark, a general
  plugin ABI test, or evidence that the main runtime is Rust.
- Do not claim deterministic replay, exactly-once processing, production
  reliability, or performance gains until each has a versioned definition and
  a reproducible acceptance test.

## Open Decisions

The initial fixed-capture source, record order, single-writer checkpoint and
process boundary are now explicit local choices, not universal runtime rules.
Future work still needs a representative source/range or live-ingestion
contract, v1 support, fork/correction semantics where relevant, storage
durability, deployment topology, plugin isolation and operational SLOs. Those
decisions determine whether any later core should use in-process Rust plugins,
a resident process boundary, or both.
