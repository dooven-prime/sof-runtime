# Solana Off-Chain Vertical Slice v0

## Fixed Workload and Source Authority

Only a fixed finalized RPC capture, 1--16 inclusive slots, is in scope.
Capture raw HTTP JSON response bytes and their exact requests for getVersion,
getGenesisHash, finalized getSlot, finalized getBlocks before/after, each
listed getBlock, and a predecessor-block anchor. The input manifest binds
source URL, observed node software/feature-set, genesis, slot range, explicit
RPC config, block hashes and every byte hash. getVersion is an observed server
version, not a claim about all validators or the version that produced a block.

Use encoding=json, transactionDetails=full, maxSupportedTransactionVersion=0,
rewards=false, commitment=finalized. Only legacy and version 0 are supported.
Current Solana also has v1: it is deliberately unsupported, not silently
truncated or reinterpreted. Any RPC error/null for a listed block, missing
required metadata, unknown version or malformed consumed field rejects the
capture/run. No successful checkpoint may skip that error.

Each slot in the range must be accounted for, even when not listed by the
captured getBlocks response. Such a slot projects to an explicit
`not_listed_by_source` marker. Absence in that RPC index is not independent
proof of a skipped slot; finality and index completeness are source claims.
Capture twice checks the index and finalized root; predecessor links/hashes
must form one reported chain across listed blocks. No consensus, signature,
ledger reexecution, fork-choice or provider-completeness verification is claimed.

## Projection v0

Produce canonical UTF-8 JSONL: sorted keys, compact separators, LF, no floats
in projected fields. Order by increasing slot, then one block header and all
transaction entries in their reported array order. This is a deterministic
source order, not a claim about physical instruction-execution chronology.
Do not sort/deduplicate transactions by signature. Preserve every reported
transaction index, including failed transactions and repeated payload values.

Header: slot, blockhash, previousBlockhash, parentSlot, blockHeight, blockTime,
transaction count. Transaction: slot/index, version, all signatures, fee,
complete err JSON, recentBlockhash, message header, static account keys,
loaded writable/readonly addresses, address-table lookups and all top-level
compiled instructions. Resolve instruction indices against static+writable+
readonly keys, preserving indices and base58 data. Check base58 key/hash length
32 and signature length 64, header/count/index bounds and ALT address counts.
These are structural checks, not signature authentication or ALT-state replay.

Inner instructions, balances, token interpretation, rewards, log semantics,
effects and transaction submission are excluded. Retain raw bytes so this
declared projection is not confused with a lossless transaction representation.
Python and Rust implement projection separately; they share this contract and
the capture, not a decoder implementation.

## Checkpoint and Recovery

Single writer, local directory, advisory OS lock held for the invocation.
Bind state identity to exact manifest SHA, projection version and executable
SHA. A different capture/code identity cannot resume without a new state dir.
One immutable JSONL segment per slot is the commit unit, not one transaction.
Write/sync a temporary segment, rename it, then write/sync and atomically
replace the checkpoint. Checkpoint stores the contiguous committed prefix and
each segment hash/count. Never append directly to an external sink.

Before continuing, recompute/validate all committed segments against input,
not just a trusted count. A published next segment without checkpoint advance
is an orphan: adopt only if byte-identical to its deterministic reconstruction.
Remove only known uncommitted temporary files; corrupt segments/checkpoints,
unknown files, symlinks, holes or foreign identities are errors, not repairs by
overwrite. Completion concatenates the ordered segments into a separately
published canonical projection. A complete checkpoint without that aggregate
can rebuild it. Rerunning a complete state is a verified no-op with the same
output identity, not a second delivery.

V0 reconstructs the whole bounded capture before committing, including on
resume, and rechecks it after execution. The checkpoint avoids duplicate
publication; it does not yet avoid redecoding the committed input prefix.

Test actual process termination after partial segment write, segment publish,
partial checkpoint write, checkpoint publish, partial aggregate write and
aggregate publish. Restart from each point and compare all bytes with a clean
run and Python. All internal prefix/cursor transitions refer to this same
capture; progress alone cannot assert a completed output.

This is process-crash recovery on the tested local filesystem, assuming
same-filesystem atomic file replacement. File sync is used; directory/power-loss
durability, distributed storage, malicious concurrent mutation, external sink
exactly-once delivery and reorg handling are not established. Advisory locks do
not protect against a process deliberately ignoring the protocol.

## Acceptance and Measurement

First require full Python/Rust projection equality, every slot accounted for,
contiguous transaction indices/counts, identical clean/repeated/recovered
output bytes, and fail-closed hostile controls. Synthetic controls are labelled
separately from the real RPC sample. Then record local decode/validation,
projection/commit, restart wall time, CPU observations, RSS and throughput for
this captured range. Tiny samples do not justify tail-latency or production SLO
claims. Live ingestion, resident services, plugins, remote workers, distribution
and SOF protocol admission are outside v0. Freeze MaleCNS/Q2 receipts unchanged.

## Primary Interfaces Checked

- [getBlock](https://solana.com/docs/rpc/http/getblock)
- [getBlocks](https://solana.com/docs/rpc/http/getblocks)
- [getVersion](https://solana.com/docs/rpc/http/getversion)
- [RPC JSON structures](https://solana.com/docs/rpc/json-structures)
- [Transaction versions](https://solana.com/developers/cookbook/transactions/versions)

These interfaces specify the input, not the correctness of this implementation.
