# Source-Transition Publication Recovery v0: Local Readout

2026-10-24. Status: `PASS_LOCAL_PUBLICATION_RECOVERY` on the fixed local domain.
The [contract](CONTRACT.md) and [predeclared plan](plan.v0.json) are implemented
in a separate Rust adapter; source advancement v0 and its evidence are unchanged.

## Result

The [selected summary](results/acceptance-summary.v0.json) binds the full local
run at `runs/solana-publication-recovery/acceptance-v0-final/`. Its full receipt
has SHA-256 `9ca248d36588889c5b1ef2881aa01d659a4726ab2f3f6aba0c2c652c43d4ce0f`
and binds 6,309 saved files. The summary is not a self-contained public package.

The source is the unchanged 64-slot devnet capture, slots 378967388--378967451,
with 1,381 legacy/v0 transactions. Derived offline windows/credentials remain
explicit test fixtures, not authenticated new provider captures. From a new
16-slot parent made by this executable, controls exercise same-source append
to 32 slots and permitted equal-record source change/reapproval to 64 slots.

| Control | Observed result |
| --- | --- |
| 18 named kill points x 2 transition modes | All 36 fresh-process recoveries reproduce every uninterrupted state file byte for byte. |
| Retry after each recovery | Full validation succeeds; the same operation's exact receipt bytes and checkpoint identity remain unchanged. |
| One operation interrupted four successive times | Transition partial, checkpoint partial, after publication and receipt partial recover to the clean reapproval state. |
| Eight saved refusal cases | Corrupt staged segment, pending transition, ready, published checkpoint/segment, receipt, foreign destination and changed request all return UNRESOLVED. No new output is admitted and existing output/evidence is retained. |
| Parent and capture snapshots | Byte inventories remain identical throughout the primary matrix. |

There are 47 primary case records plus the separately recorded parent
initialization. The matrix includes 44 actual kills: 36 systematic, four
successive interruptions and four refusal preparations. Additional small-domain
unit controls are separate, not included in that count.

The kill points cover partial/published intent, calculation start/completion,
stage creation, partial/published segment, aggregate, transition and checkpoint,
published ready, before/after final rename, and partial/published receipt.
They are named bounded controls, not an exhaustive test of all instruction
interleavings or every segment ordinal. Before final directory rename there
is no published output; after rename a complete output can exist with no
returned success. Retry verifies it and completes the deterministic receipt.

## Identities and Independent Reference

The separate Python model reconstructs complete source projections, parent
compatibility, framed checkpoint fields, source/execution identities, input
inventory, ready and exact receipt bytes. Reapproval's full projection is
1,994,158 bytes with the same previously retained canonical SHA-256
`a8053b902e3824651851bd612b741d4358ae5112ff8397ca3ea2cde6770d1f92`.

For the fixed requests in this run, all append recoveries have checkpoint
`290516a03a6ac07510981a3e7850f4cb5388af0397d2136565129a0b26fdc301`;
all reapproval recoveries have checkpoint
`9f54a26245289002fbb87ed42fb19aaa665f2f52df4ac0579e88605d2bc6b688`.
These are local source/path/executable-bound identities, not portable fixture
constants. Different destination directories have different transaction/receipt
identities even though the same semantic request yields equal state bytes.

Both ordinary and -O Python suites pass eight test methods, including all
small-domain kill points, concurrent writer exclusion, repeated interruption,
source-semantic refusals, protected input paths and changed bindings. Two
inherited Rust parser tests and format checking also pass. The saved closure
verifier passes in ordinary and -O modes without rerunning Rust. This is
separately implemented local checking, not independent execution attestation.

## Boundaries and Next Decision

Every attempt regenerates a private semantic result before publication checks,
even on a retry of published output. Calculation/storage/validation are thus
duplicated by design. Source validator work counters do not describe the
wrapper's entire IO, and this readout makes no latency, throughput or avoided-
computation claim. Retained private calculation files are evidence, not a
garbage-collection or production lifecycle policy.

The new executable has a new execution identity; no old checkpoint is migrated.
The wrapper uses process-local locks, file sync and complete-directory rename.
It does not establish power-loss durability, adversarial-filesystem security,
external exactly-once delivery, live inputs, provider trust, reorg or rollback.
A corrupted previously published output is refused without deleting its
historical receipt; that receipt is not proof of its current integrity.

Earlier Solana/cache/Q2/sparse evidence bindings, 25 vendored contract digests
and the service implementation closure remain unchanged. The
[internal inventory](../../docs/internal/RUNTIME_EXECUTION_CONTRACT_INVENTORY.md)
now supports a separate core-boundary review. No common Rust runtime API is
extracted here, and no source, consumer or arithmetic semantics are generalized
by similarity of orchestration patterns.
