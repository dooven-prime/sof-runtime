# Solana Off-Chain Vertical Slice v0

Fixed finalized RPC capture -> separately implemented Rust/Python projection ->
slot segments/checkpoint -> replay and actual process-kill recovery.
This is a bounded application, not a validator, live stream, external sink,
plugin ABI, production Solana runtime or admitted SOF capability.

Read the [contract](CONTRACT.md) and [acceptance plan](ACCEPTANCE_PLAN.md).
The first [local readout](READOUT_V0.md) and
[compact receipt](results/acceptance.v0.json) retain the bounded acceptance.
Only legacy/v0 raw-JSON transactions are supported. Current v1 is refused;
maxSupportedTransactionVersion=0 does not mean every current block is readable.
An unlisted slot gets an explicit source-index marker, never a fabricated empty
block or an independent skipped-slot certificate.

## Local Workflow

Use Python 3.11+, psutil and Cargo/Rust 1.89+. Python uses its standard library
for projection; Rust has locked serde/sha2/bs58/fs2 dependencies. Initial Cargo
acquisition and capture need network access. Offline execution/recovery does not.
Run from this repository root; new output directories must not exist:

```powershell
python -B -m applications.solana_offchain_slice.capture `
  --start-slot 378967388 --count 3 `
  --output-dir runs/solana-offchain/NEW-CAPTURE
python -B -m unittest tests.cross_language.test_solana_offchain_slice -v
python -B -m applications.solana_offchain_slice.run_controls `
  runs/solana-offchain/NEW-CAPTURE/manifest.json `
  --output-dir runs/solana-offchain/NEW-ACCEPTANCE
python -B -m applications.solana_offchain_slice.verify `
  runs/solana-offchain/NEW-CAPTURE/manifest.json `
  runs/solana-offchain/NEW-ACCEPTANCE
```

Historical RPC availability is not guaranteed. Missing data, unsupported
versions and RPC errors leave an incomplete capture without a manifest; do not
substitute a synthetic fixture or silently change the range. The capture saves
raw request/response bytes before reporting a received JSON-RPC failure. The explicit
historical sample avoids widening the decoder to v1, not a claim that v1 is
unimportant. Node getVersion observes the capture endpoint, not past producer
software.

The kernel can also run directly after a locked release build:

```powershell
cargo build --release --locked --manifest-path plugins/rust/solana-offchain-slice/Cargo.toml
plugins/rust/solana-offchain-slice/target/release/solana-offchain-slice.exe `
  runs/solana-offchain/NEW-CAPTURE/manifest.json runs/solana-offchain/NEW-STATE
```

Rerun that exact command to verify/reuse a completed state. Code or capture
identity changes require a new state directory. An error exits 2 with
application-local UNRESOLVED; do not infer completion from files or cursor
presence alone. `--pause POINT SLOT` is a test-only crash-boundary hook, not a
resident execution API. The acceptance runner actually kills and reaps children.

## Evidence and Recovery Boundary

Each slot's immutable segment is published before checkpoint advancement.
Restart validates the committed prefix, adopts only byte-matching orphan
segments and rebuilds an absent aggregate from complete segments. No append
sink is used, and no external exactly-once or power-loss guarantee is claimed.
One advisory OS lock rejects concurrent protocol writers; it is not protection
against malicious storage mutation or a writer that ignores the lock.

Resume currently reconstructs the complete bounded capture and verifies the
committed prefix. It saves duplicate publication, not input decode work; no
incremental or streaming performance claim follows from the cursor.

Full raw capture, references, state directories and logs remain under ignored
`runs/`. A selected compact receipt is not a public self-contained replay
package. Saved-closure verification rechecks bytes and Python comparisons,
not worker execution or source consensus. This is a tested local-checkout
workflow, not a clean-checkout/public release claim.

Small synthetic tests are labelled separately from the real capture. Diagnostic
measurements begin only after correctness/recovery pass, include full process
cost and retain decode/commit fields. They do not establish tail latency,
mainnet representativeness, production SLOs or an independent finality proof.
