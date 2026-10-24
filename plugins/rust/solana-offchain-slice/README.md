# Fixed-Capture Projection Worker v0

Application-owned crate for the [off-chain slice](../../../applications/solana_offchain_slice/CONTRACT.md).
It does not connect to RPC, submit transactions or implement a general plugin
ABI. Inputs are raw-JSON capture files bound by a manifest; outputs are ordered
JSONL slot segments, an identity-bound checkpoint and a final aggregate.

```text
solana-offchain-slice MANIFEST STATE_DIR
solana-offchain-slice MANIFEST STATE_DIR --pause POINT SLOT
```

The second form is a test-only pause at partial segment, segment publication,
partial checkpoint, checkpoint publication, partial projection or projection
publication. The Python controller kills a live paused process and verifies
restart; a pause marker is never a completion result.

Fresh execution and resume both validate input hashes/config/index/chain and
supported transaction structures, plus already committed output bytes. Duplicate
JSON keys, unknown versions and source errors are refused, not omitted. A
single advisory OS lock is released by process termination. Same-filesystem
atomic rename is assumed; directory/power-loss durability is not claimed.

Bounds: 1 MiB manifest, 1--16 slots, each raw RPC response 32 MiB and request
64 KiB. Python acceptance additionally enforces a 60-second child timeout and
observed 1 GiB RSS limit. These cooperative controls are not a sandbox or a
complexity guarantee. Capture/source SHA checks are not cryptographic finality
or signature verification. This projection does not execute the Solana ledger.
