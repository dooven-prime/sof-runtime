# Solana Incremental Replay v1

A separate fixed-capture application. It preserves the
[v0 projection](../solana_offchain_slice/CONTRACT.md) and does not modify v0's
code or selected receipt. [Contract](CONTRACT.md) and [plan](plan.v1.json) fix
scope before capture and recovery measurements. See [readout](READOUT_V1.md).

## Build and Offline Controls

From the repository root, with Rust, Python 3.11+ and `psutil` installed:

```powershell
cargo build --release --locked --manifest-path plugins/rust/solana-incremental-replay/Cargo.toml
python -B -m unittest discover -s tests/cross_language -p test_solana_incremental_replay.py -v
python -B -O -m unittest discover -s tests/cross_language -p test_solana_incremental_replay.py -v
```

The crate compiles the unchanged v0 Rust source as a private module. Python
uses the separately implemented v0 projection law with a new v1 envelope
validator. Neither is an installed runtime API or transaction execution engine.

## Fixed Real Capture and Acceptance

The capture command reads the fixed range and retry policy from `plan.v1.json`.
Use a new output directory. Unsupported/listed-null/error responses abort the
capture; they are not filtered or relabelled as absent slots.

```powershell
python -B -m applications.solana_incremental_replay.capture --output-dir runs/solana-incremental/my-capture-v1
python -B -m applications.solana_incremental_replay.acceptance runs/solana-incremental/my-capture-v1/manifest.json runs/solana-incremental/my-acceptance-v1
python -B -O -m applications.solana_incremental_replay.verify runs/solana-incremental/my-capture-v1/manifest.json runs/solana-incremental/my-acceptance-v1
```

Re-capture is a new provenance identity, even for the same historical range.
Public RPC availability is not guaranteed. The selected receipt records a
local capture and saved comparisons; raw capture bytes, state directories and
logs stay in ignored `runs/`. The compact receipt is not a self-contained
public replay package or an independent execution/finality attestation.

## Recovery Trust and Work

For a fresh state, invoke the binary with `MANIFEST STATE incremental`.
For a nonempty committed prefix, incremental mode also requires
`--checkpoint-sha256 SHA`, supplied by the controller from a previously
validated run/checkpoint of this implementation. **Hashing arbitrary state
does not establish that precondition.** `full_reproject` can instead verify
the whole committed prefix against the input without assuming such a prior
anchor. Changing projection, code or capture identity requires a new state.

Incremental mode still hashes prefix input and segment bytes, checks chain
and cursor metadata, streams final aggregation, and hashes input again after
consumption. It skips prefix block JSON decoding and projection, not all
prefix I/O. A matching orphan next segment is uncommitted: it is projected
again before adoption. The test-only `--forbid-prefix-decode` guard fails if
any prefix projection is attempted; acceptance enables it in incremental mode.

Each process returns decoded slot traces and separate phase timings. Clean
and resumed states are checked byte-for-byte against the full Python
projection. The reducer also checks exact suffix work, not only equal output.
Three paired repetitions alternate full-reproject/incremental order at
2/32/62 committed slots. Directory copying is outside the child timer and is
not claimed as free in an operational runtime. CPU sampling is a lower bound;
Windows OS peak working set and sampled RSS are recorded separately.

## Deliberate Boundaries

No live processing, remote sink, fork switching, transaction-version expansion,
distributed workers, malicious concurrent storage, power-loss durability or
production exactly-once claim. No immutable-storage credential is implemented.
The external checkpoint anchor is a declared trust input, not a new proof of
arbitrary cached state. Larger fixed data and exact work accounting establish
this prototype's scope, not representative network coverage or asymptotics.
