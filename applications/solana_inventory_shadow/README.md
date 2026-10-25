# A0 Read-only Solana Inventory Shadow v0

Experimental first A0 adapter under the [boundary review](../../docs/internal/RUST_EXECUTION_CORE_BOUNDARY_REVIEW_V0.md).
See the [contract](CONTRACT.md), [fixed plan](plan.v0.json) and
[local readout](READOUT_V0.md). No application is migrated and no public Rust
runtime API, common process scheduler, lock, publisher or receipt protocol is
introduced. The experimental Cargo package has `publish = false`.

## What Runs

```text
unchanged original Solana producer and semantic reference
  -> exact copies: state directory / separately copied producer receipt
  -> detached exact manifest + independent expected declarations
  -> Rust read-only A0 inspector
  -> separate Python byte/type/handle reference
  -> detached shadow observation, not a Solana decision
```

The original checkpoint, producer receipt and producing executable identity
are never rewritten. The new inspector reports `ShadowObserverExecution` with
its own executable hash. State and receipt are separate flat input roots so
neither a new manifest nor a copied receipt becomes an unregistered state file.

The A0 library only hashes, decodes restricted manifest metadata and reads
existing filesystem objects. It never parses a slot/transaction, decides source
permission or runs an application producer. The binary adds stdout diagnostics
and test-only detached pause markers. The Python controller is local test code,
not extraction of the proposed B process layer.

## Observation, Not a Snapshot Credential

Exact membership includes extra-file refusal. File data may be arbitrary bytes;
only the detached manifest uses `ascii-json-u64.v0`. Missing/damaged/truncated/
wrong-type data, unsafe names, schema/producer/role mismatch and noncanonical
metadata are rejected. The local NTFS backend also inspects actual handle/path
identity, links, reparse attributes and named streams. It retains handles,
enumerates twice and hashes payloads twice, with pre/post checks.

A successful result means `OBSERVED_INTERVAL_ONLY`. It cannot authorize a future
read or substitute for an application validator. Source quiescence and trusted
local storage remain assumptions; this is not a defense against arbitrary
change-and-restore races. OS file IDs are not portable persisted content IDs.

The controller accepts a matching observation only after complete JSON and a
successful inspector exit. Killed/partial/unresolved observations remain
`INCOMPLETE`, not a usable successful receipt. A rejected or incomplete record
can still be fully retained as local evidence. Application decision and source
trust remain `NOT_ASSESSED` in every inspector result.

## Run Locally

Prerequisites: Windows NTFS with inspectable handle/stream metadata, Python with
the existing application dependencies, Rust >=1.89 and Cargo.lock dependencies.
The primary acceptance uses the existing frozen producer run under
`runs/solana-publication-recovery/acceptance-v0-final/`; it does not fetch or
regenerate that source. This is not a clean-checkout public replay package.
Small unit controls generate their own fixtures, including one with the
unchanged original producer.

```powershell
cargo build --release --locked --offline --manifest-path plugins/rust/a0-inventory-inspector/Cargo.toml
cargo test --locked --offline --manifest-path plugins/rust/a0-inventory-inspector/Cargo.toml
python -B -m unittest discover -s tests/cross_language -p test_a0_inventory_shadow.py -v
python -B -O -m unittest discover -s tests/cross_language -p test_a0_inventory_shadow.py -v
python -B -m applications.solana_inventory_shadow.acceptance runs/a0-solana-inventory-shadow/my-new-run
python -B -O -m applications.solana_inventory_shadow.verify runs/a0-solana-inventory-shadow/my-new-run
```

Use a new run directory. The raw inspector CLI is `ROOT MANIFEST BINDINGS` and
writes only stdout in normal operation. The controller's stdout/stderr and
observation files must be new and outside ROOT. `--pause POINT MARKER` and its
`.continue` handshake are test hooks, not a runtime scheduling/publication API.

Saved verification checks exact evidence membership, type, byte hashes, link
counts and named streams. It records fixture junctions without following them;
their targets must stay in the owned run. This evidence recorder is deliberately
different from A0, which refuses such inputs. The top acceptance record is
explicitly excluded from its own payload inventory, and its hash is bound by
the selected detached summary. It is not a common receipt design.

The verifier rechecks Python semantics and original artifacts but does not
rerun Rust or attest that historical kills occurred. It is local source-bound
checking, not an external execution attestation. No B/C or second application
is promoted by this first adapter.

### Candidate Version Binding

The selected first receipt/readout remains bound to inspector candidate 0.1.0.
The [second, MaleCNS shadow](../malecns_cache_inventory_shadow/READOUT_V0.md)
adds an explicit CacheIdentity metadata profile in candidate 0.2.0, with no
change to the byte/NTFS backend. It retains the earlier candidate source and
executable locally against the first receipt's hashes and records a separate
43-control Solana regression. Do not run a current-source verifier against an
old candidate receipt and reinterpret the expected binding failure as either
validation of the new candidate or a failure of the historical result.

The new source-bound regression is verified with:

```powershell
python -B -m applications.solana_inventory_shadow.verify runs/a0-malecns-cache-shadow/acceptance-v0-final/solana-regression
```

Neither receipt is overwritten or given the other candidate's execution identity.

Candidate 0.3.0 is the separate [Shared A0 extraction experiment](../shared_a0_extraction_review/README.md).
Its inspector delegates mechanics to the internal `a0-mechanical-core` library;
this adapter still owns its declaration profile and the independent Python
reference. The 0.1.0/0.2.0 records above remain historical, source-bound records:
the displayed 0.2.0 verification command requires its matching old candidate.
For the new candidate use the extraction review's new run, not an old receipt.

## Windows Backend References

Read-only `OPEN_EXISTING` and no final reparse traversal use
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).
Handle/volume/link metadata use
[BY_HANDLE_FILE_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-by_handle_file_information);
the backend is explicitly NTFS, not a claim about permanent file identifiers.
Named-stream inspection uses
[GetFileInformationByHandleEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyhandleex)
and [FILE_STREAM_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_stream_info).
Unavailable or unsupported metadata is unresolved, never a fallback to success.
