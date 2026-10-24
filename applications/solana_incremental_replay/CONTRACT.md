# Incremental Replay v1

Application-owned fixed-capture prototype. The frozen v0 projection law and
legacy/v0 transaction compatibility are unchanged. This is not a SOF API,
live RPC runtime, validator, ledger verifier or production durability claim.

## Recovery Contract

Each invocation binds the exact capture manifest and executable. A checkpoint
is a contiguous ordered list of committed slot segments, their byte hashes,
record counts, input-response identities and block-chain metadata. A completed
segment is published before its checkpoint entry. Uncheckpointed output is
uncommitted and may be reconstructed. Only one writer holds the OS file lock.

Incremental resume of a nonempty prefix requires an externally bound expected
checkpoint SHA-256 from a previously validated execution of this same program.
A digest freshly calculated from arbitrary foreign state is not such a basis.
Full-reproject mode instead checks every committed segment against the actual
input and can establish a new local anchor. Both modes reject identity,
cursor, prefix-input, segment and checkpoint corruption; neither silently
repairs committed data. This is a single-writer, process-interruption model,
not protection against an attacker controlling the program and its anchor.

Incremental prefix validation hashes every committed raw response and output
segment, validates metadata continuity, but never JSON-decodes or projects
committed block responses. Only the uncommitted suffix is decoded/projected,
one block at a time. Post-consumption input hashes are checked again. Final
aggregation streams all output segments; prefix I/O has not been eliminated.

## Accounting

Metadata validation, prefix integrity, prefix full-reprojection control,
suffix decode/projection, new commits, aggregation and post-input hashing are
timed separately. Listed-block decode slots and bytes are recorded centrally.
Unlisted slots have explicit source-index markers, not invented skipped-block
claims. A valid complete repeated run has zero block decoding in incremental
mode. An orphan next segment is in the uncommitted suffix, not the prefix.

Clean and resumed canonical JSONL must be byte-identical to a separate Python
full projection. An incomplete capture, unsupported transaction, malformed
input, absent anchor, resource limit or writer conflict is UNRESOLVED, never
successful recovery. No filtering is used to make the larger capture pass.

The capture plan fixes 64 slots before retrieval. Recovery curves use three
paired repetitions at 2/32/62 committed slots, alternating mode order, plus
three clean baselines. These are local bounded measurements, not universal
complexity, independent finality, exactly-once sink or power-loss guarantees.
