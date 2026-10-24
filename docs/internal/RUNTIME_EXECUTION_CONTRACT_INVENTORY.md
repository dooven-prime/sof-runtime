# Runtime Execution Contract Inventory

Internal engineering inventory, 2026-10-24. This is not a public runtime API,
SOF contract, paper promotion or claim of independent verification. Evidence
below is application-local. Similar mechanisms do not yet share one protocol.

## Mechanisms Observed Across Applications

| Mechanism | Existing bounded evidence | What may be reused; what may not |
| --- | --- | --- |
| Exact input/configuration/code binding | MaleCNS prepared cache and sparse kernel; Q2 shard plan; Solana captures/checkpoints | Reuse digest/version discipline. Do not equate source, execution, cache, checkpoint and scientific identities. A hash is not producer authentication. |
| Separate reference and Rust execution | Complete MaleCNS profiles, exact/numerical sparse controls, Q2 signatures, Solana ordered projections | Reuse comparison lifecycle. Arithmetic, tolerances, state interpretation and completeness remain application-owned. |
| Global acceptance after local computation | MaleCNS exact profile-class aggregation; Q2 cross-shard fibers; Solana ordered segments | A worker's COMPLETE is not global PASS. Each reducer needs its own coverage/order/consistency law. |
| Refusal instead of inferred success | Cache corruption, Q2 missing/foreign shards and resource stops, Solana absent/conflicting evidence | Preserve explicit unresolved/refused results and reason codes. Their mathematical meanings differ. |
| Locking and private staging | Prepared cache, Solana replay and source advancement | Single-host writer exclusion and complete-publication checks are recurring patterns, not a remote exactly-once protocol. |
| Actual kill and restart controls | Cache builder lifecycle; Q2 worker failure; Solana v0/v1 replay | Process kill tests establish only their named boundaries. They do not establish power-loss durability, arbitrary descendant cancellation or source-transition publication recovery. |
| Saved local receipts | All named applications | Reuse confined inventory/hash checks and source binding. Saved verification is not a fresh worker run or external attestation; ignored runs are not a public replay package. |
| Controlled cost accounting | Cache decomposition/fusion, sparse setup/resident costs, Solana prefix attribution | Distinguish nested timings, CPU/wall/bytes, preparation/consumption and computation/verification. Do not transfer a speedup between workloads. |

## Application-Owned Semantics

- **MaleCNS profile census:** signed integer profile definition, declared source
  domain, sector/sign policy and exact global class merge.
- **MaleCNS sparse kernel:** source normalization, transpose action, target-row
  layout, rational clipping versus numerical tolerance. The exact controls do
  not replay all Paper XVII orbits.
- **Q2:** typed expressions, exact generated-history domain, registration,
  R/G/T fiber consistency and actual-history rejection replay. V0 regenerates
  the domain and rechecks all signatures in Python; it is not distributed BFS
  or a demonstrated accelerated backend.
- **Solana:** accepted transaction versions, address resolution, source ordering,
  slot continuity, capture permissions, prefix equivalence and invalidation.
  Offline source correction is not reorg processing or provider authentication.

## Publication Recovery Gate

Source advancement v0 itself remains unchanged and does not recover its
publication transaction after process death. A separate
[publication recovery adapter](../../applications/solana_publication_recovery/READOUT_V0.md)
now passes a fixed 18-point x two-mode real-kill matrix, repeated interruption,
and corrupt/incomplete-publication refusals. Intent, complete directory and
receipt are distinct; retry revalidates the actual inputs and full output.
It regenerates private calculation on each attempt and makes no optimization
claim. Process-crash controls do not establish power-loss durability.

That bounded gate permits a core-boundary design review, not automatic
promotion. The [Boundary Review v0](RUST_EXECUTION_CORE_BOUNDARY_REVIEW_V0.md)
now records a contract-only A0 candidate and shadow acceptance plan; it creates
no shared implementation or public API. Candidates for review are exact
binding/inventory utilities,
explicit process outcome/resource handling and local publication lifecycle.
Their error types, identity domains, storage assumptions and evidence ownership
still need reconciliation before extraction. Source continuity/reapproval,
R/G/T reduction, sparse arithmetic and profile-class aggregation remain outside
that candidate core. No live input, shared reducer semantics, plugin ABI,
distributed commit or common trust store is authorized by this inventory.

## Evidence Entry Points

The first [A0 read-only Solana shadow](../../applications/solana_inventory_shadow/READOUT_V0.md)
now has 43 source-bound local controls, including exact byte/type/membership
parity, six actual kills, four changed-window refusals and a mechanical-match /
application-rejection control. Original producer artifacts and identity remain
unchanged. This is one experimental adapter only; no public library, second
application migration, process core or publication core is promoted.

The second [A0 MaleCNS prepared-cache shadow](../../applications/malecns_cache_inventory_shadow/READOUT_V0.md)
now passes 27 local controls on a full-carrier cache copy and bounded hostile
fixtures, including three actual kills, four changed intervals and a digest-
correct but protocol-invalid packet. The unchanged application validator rejects
that packet while A0 matches its declared bytes. Source/Execution/Cache roles
are explicit, and no observation grants cache-hit permission. A new 43-control
Solana regression preserves the previous observer/receipt snapshot. This meets
the second-shadow review prerequisite, not automatic A extraction, cache
migration or B/C approval.

The separately scoped [Shared A0 extraction experiment](../../applications/shared_a0_extraction_review/READOUT_V0.md)
now passes local acceptance with one internal three-module Rust library and
fresh 43/27-case shadow regressions. The
[SOF compatibility guard](SOF_COMPATIBILITY_GUARD_V0.md) preserves 304 protected
file identities, 131 test outcomes and the installed-wheel workflow. This is
shared mechanical code in shadow paths only, not a production migration or
permission to merge application semantics or extract B/C. Environmental
baseline failures and their review-only launch corrections are retained.

- [Prepared cache](../../applications/malecns_profile_census/CACHE_READOUT_V1.md)
  and [validation fusion](../../applications/malecns_profile_census/FUSED_VALIDATION_READOUT_V1.md).
- [Sparse kernel](../../applications/malecns_sparse_kernel/READOUT_V0.md).
- [Parallel Q2](../../applications/event_causal_consumers/parallel_v0/READOUT.md).
- [Off-chain v0](../../applications/solana_offchain_slice/READOUT_V0.md),
  [incremental v1](../../applications/solana_incremental_replay/READOUT_V1.md),
  [prefix attribution](../../applications/solana_prefix_integrity/READOUT_V1.md),
  [source advancement](../../applications/solana_source_advancement/READOUT_V0.md).
