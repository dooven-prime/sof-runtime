# Solana Source-Transition Publication Recovery v0

Application-local implementation of the [contract](CONTRACT.md). Begin with
the internal [execution contract inventory](../../docs/internal/RUNTIME_EXECUTION_CONTRACT_INVENTORY.md).
This follows source advancement v0 without editing its bound source/results.

## Design

The Rust executable includes the unchanged advancement implementation. Each
attempt recalculates/validates the proposed transition privately; a separate
transaction layer stages its exact files and publishes the complete directory.
Intent binds request, executable, destination and all input/parent bytes. Ready
binds the complete state. The directory rename is the publication boundary;
success receipt publication follows it and is recoverable after lost stdout.

An interrupted .pending file is completed only when its bytes are an exact
prefix of newly calculated expected bytes. Finalized stage/output mismatches,
unknown files, changed identities and incomplete final directories are refused,
not silently repaired. The parent is retained, not promoted through a mutable
active pointer. A retry revalidates everything and reproduces the same receipt
for that operation. Different destination paths define different operations
and receipts, even when their semantic checkpoint/state bytes agree.

Private calculation can be regenerated after a kill. This layer currently
duplicates materialization and repeats validation even after publication; it
does not claim reduced recovery work or a throughput improvement. The source
validator's work counters describe that calculation, not total wrapper IO.

## Run

From the repository root, using Python with the existing application dependencies
(`psutil`) and Rust >=1.89 with the Cargo.lock dependencies available:

```powershell
cargo build --release --locked --offline --manifest-path plugins/rust/solana-publication-recovery/Cargo.toml
python -B -m unittest discover -s tests/cross_language -p test_solana_publication_recovery.py -v
python -B -O -m unittest discover -s tests/cross_language -p test_solana_publication_recovery.py -v
python -B -m applications.solana_publication_recovery.acceptance runs/solana-incremental/capture-devnet-64-v1/manifest.json runs/solana-publication-recovery/my-new-run
python -B -O -m applications.solana_publication_recovery.verify runs/solana-publication-recovery/my-new-run
```

Every run directory must be new. The fixed 64-slot capture is a local prerequisite,
not downloaded or reconstructed by these commands. The controller derives
explicitly offline source envelopes, not new authenticated RPC captures.

The executable accepts `REQUEST_JSON ABSOLUTE_OUTPUT_DIRECTORY`; retry these
same arguments after interruption. The request uses the source-advancement v0
schema. A checkpoint produced by another executable is not silently migrated.
`--pause POINT ABSOLUTE_MARKER` is a local fault-injection hook, not a service
API. The controller waits for the synced marker, kills the real process and
starts a fresh process; it does not simulate an exception inside Rust.

## Evidence and Boundaries

The fixed [plan](plan.v0.json) declares 18 interruption points for each of append
and credential reapproval. Controls include repeated interruption, idempotent
retry, concurrent writer exclusion, changed input/request/policy/executable
binding, corrupt stage/ready/receipt, incomplete final output, source-semantic
refusals and no writes inside protected inputs. Python reconstructs the full
projection and checks framed identities, inventories and exact receipt bytes.
Uninterrupted/recovered state files are also compared byte for byte.

See [the readout](READOUT_V0.md) for the selected local run. The compact summary
is not the full replay package. `runs/` is ignored. The saved verifier checks
the exact file inventory, implementation, input identities and Python model;
it does not rerun Rust or authenticate the recorded kills. It can detect a
changed saved result but cannot establish independent execution provenance.

Only process-crash behavior on this local filesystem is tested. No power-loss
durability, malicious-filesystem security, external exactly-once sink, live
provider admission, Solana reorg, rollback or code migration is claimed. A
historically published directory remains evidence even if a later retry is
refused; an UNRESOLVED attempt does not erase an earlier successful receipt.
No shared Rust core or live input is introduced by this gate.
