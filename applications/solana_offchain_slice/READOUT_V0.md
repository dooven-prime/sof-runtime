# Off-Chain Slice v0: Local Acceptance Readout

## Result

The [fixed-capture contract](CONTRACT.md) and [acceptance plan](ACCEPTANCE_PLAN.md)
are implemented without changing the frozen MaleCNS or Q2 packages. The
[selected local receipt](results/acceptance.v0.json) records byte-identical
Python/Rust projection, repeated execution and six actual process-kill/restart
controls. This is a local finite capture/recovery result, not a production
runtime, SOF admission, consensus proof or external exactly-once guarantee.

## Exact Input Scope

The real sample is public devnet RPC, finalized slots
`378967388--378967390`, with raw JSON/full transaction responses and maximum
supported version 0. Capture retains 23 request/response/manifest files, their
byte hashes, genesis, an external predecessor anchor and before/after finalized
roots and block indexes. The endpoint reported `solana-core=4.4.0-beta.1`,
feature-set `3993424257`. This is the server observed at capture time, not the
software version that historically produced those blocks.

| Slot | Transactions |
| --- | ---: |
| 378967388 | 44 |
| 378967389 | 18 |
| 378967390 | 17 |

All 79 transactions are retained: 72 legacy, 7 v0, including 5 reported
failures and 2 transactions with nonempty loaded address sets. The projection
has 3 block headers plus 79 transaction rows, 136,507 bytes. Its SHA-256 is
`689630666517ca618032afa0e437f435dc1fb2c89b88dc6d56f203222c637f89`.

A prior attempt on a recent devnet range failed on RPC error `-32015` for a
v1 transaction. Its raw rejection is retained separately and no complete
manifest was created. It was not interpreted as a skipped/empty block. The
historical range is an explicit scoped sample, not a filtered current-range
success claim. Source finality and getBlocks completeness remain trusted RPC
assertions; this implementation does not independently establish them.

## Correctness and Recovery

Twenty-five real child attempts cover clean execution, repeat, a second state
directory, six kill/resume pairs and five measured fresh/repeat pairs. The six
terminated children are not counted as successful runs. Every completed run
matches Python's entire ordered projection; every recovered state has the
same identity, checkpoint, segments and aggregate as the clean state.

| Killed after | Resume cursor | Orphan segments adopted |
| --- | ---: | ---: |
| Partial first segment | 0 | 0 |
| First segment publication | 0 | 1 |
| Partial first checkpoint | 0 | 1 |
| First checkpoint publication | 1 | 0 |
| Partial final aggregate | 3 | 0 |
| Final aggregate publication | 3 | 0 |

Repeat execution leaves committed state bytes unchanged. Recovery validates
the actual committed prefix, not only cursor counts. A segment published
before checkpoint advancement is adopted only after deterministic byte
comparison. The complete aggregate can be rebuilt from committed segments.
No external append sink or transaction delivery is being tested.

Ten focused tests pass in ordinary Python and `-O` mode; two Rust unit tests
also pass. Synthetic controls separately cover an explicitly unlisted slot,
loaded-address resolution, failed transactions and repeated payloads without
deduplication. Hostile controls refuse unsupported versions, null/missing
metadata, RPC errors, invalid base58/indices/lookup counts, range/root/cluster/
chain mismatches, Boolean/integer coercion, byte damage, duplicate JSON keys,
path escape, corrupt checkpoints/segments/aggregates, foreign state and changed
capture identity. A concurrent writer is refused while the first process
holds its OS lock; killing the owner releases that lock for actual recovery.

## Diagnostic Measurements

Correctness gates completed before measurement. Five fresh invocations have
median process wall time 95.9 ms (80.9--105.5 ms); five completed-state replays
have median 51.1 ms (46.4--54.8 ms). Observed RSS peaks are approximately
7.05 MB fresh and 7.11 MB replay. CPU observations and OS peak working set
are separate receipt fields, not inferred from wall time.

For the first clean run, initial decode/validation/projection took 7.83 ms,
identity/lock/checkpoint/aggregate work 45.72 ms and post-capture validation
8.02 ms; whole child process time was 102.79 ms. These nested intervals do not
sum to an independently measured startup/serialization cost. RPC acquisition
is outside offline execution measurements.

The tiny capture was already read and the filesystem cache was not evicted.
Diagnostic transactions/second counts source transactions verified per full
invocation; replay does not deliver another 79 transactions. There is no p99,
mainnet, live ingestion, cold-cache or production throughput conclusion. Resume
currently redecodes/reconstructs the whole bounded capture: the cursor prevents
duplicate publication, not input decode work.

## Retention and Boundaries

Full source bytes remain in
`runs/solana-offchain/capture-devnet-historical-v0/`, the incomplete recent
attempt in `runs/solana-offchain/capture-devnet-v0/`, and 142 bound run files in
`runs/solana-offchain/acceptance-v0-final/`. This final bound run includes the
strict RPC-ID/checkpoint comparison guard; the earlier development run remains
unchanged and is not the current implementation closure. These directories remain ignored; the
compact receipt alone is not a public self-contained replay package.

The saved-closure verifier passes all 13 completed state directories against
the capture, Python reconstruction, file hashes and current implementation.
It does not rerun workers, authenticate the receipt, verify transaction
signatures or prove finality. Commands are in the [README](README.md).

Durability is limited to the tested local process-crash model and assumed
same-filesystem atomic replacement. Power loss, directory durability,
malicious storage/concurrent mutation, external delivery, reorg processing,
v1 support, real-time streams and distributed deployment remain outside v0.
This result does not by itself justify a resident executor or generic plugin
API; those require their own workload and lifecycle contracts.
