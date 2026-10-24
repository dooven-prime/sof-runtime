# A0 MaleCNS Prepared-Cache Inventory Shadow v0

Second **read-only** A0 application, using the same Rust file/handle inspection
mechanism as the [Solana shadow](../solana_inventory_shadow/README.md).
It neither migrates the old cache nor grants cache-hit/consumer permission.
The [contract](CONTRACT.md) and [fixed plan](plan.v0.json) own this experiment's
scope; the [readout](READOUT_V0.md) records the selected local result.

## What Is Compared

The existing full somaSide prepared-cache entry has a two-file flat inventory:
`manifest.json`, `packet.bin`. A second root holds exact copies of the old
benchmark receipt, original archived request and semantic result. Detached
inventory metadata declares original producer and typed Source/Execution/Cache
bindings; the inspector has its own separate observation identity.

Rust and separately implemented Python agree on exact canonical metadata
bytes, entry order, types, lengths and digests. Python does not call Rust. Its
restricted codec/NTFS backend is copied from the first shadow to leave that
source snapshot unchanged; this is not a new recursive scanner.

The unchanged application probe validates an ordinary copy and rejects another
with the first row sign set to zero. In the negative copy, **both** its old
manifest packet digest and A0 digest declarations match the actual bad bytes.
A0 matching and application rejection are the expected pair of outcomes, not
a discrepancy to eliminate. The old packet grammar, source checks, cache key,
quarantine/rebuild and consumption rules remain application-owned.

## Local Run

From this runtime checkout, on local Windows NTFS:

```powershell
python -B -m unittest discover -s tests/cross_language -p test_a0_malecns_cache_shadow.py -v
python -B -O -m unittest discover -s tests/cross_language -p test_a0_malecns_cache_shadow.py -v
python -B -m applications.malecns_cache_inventory_shadow.acceptance runs/a0-malecns-cache-shadow/NEW-RUN
python -B -m applications.malecns_cache_inventory_shadow.verify runs/a0-malecns-cache-shadow/NEW-RUN
```

Use a new output directory. The complete acceptance needs the retained local
full-carrier cache run, source carrier bytes, archived request, original
producer/consumer and read-only probe binaries, prior A0 snapshot and prior
Solana receipt listed in the plan. Missing prerequisites fail rather than
inventing provenance or silently rebuilding. The small unit controls do not
require that carrier. Cargo builds the locked candidate offline; the original
cache and probe binaries are checked, not rebuilt or replaced.

The acceptance also creates a **new** Solana regression run using candidate
0.2.0 and the original Solana test/validator code. It never overwrites the prior
Solana record. The earlier candidate 0.1.0 source and executable are retained
in a local snapshot and compared with the earlier record's hashes. A verifier
bound to the old candidate is not reinterpreted as validating the new one.

The compact [selected summary](results/acceptance-summary.v0.json) points to the
full ignored local run. It is not a self-contained public replay package or
external attestation. Saved verification repeats Python decisions, byte/type/
link/stream inventory and source bindings, but does not reexecute Rust or prove
past process events independently.

## Boundaries

Every detached observation retains `application_decision: NOT_ASSESSED`,
`cache_hit_permission: NOT_GRANTED`, `cache_policy: NOT_INVOKED`. Outcomes are
matching bytes, mechanical rejection or incomplete observation, not cache
decisions. Logs remain outside all observed roots. Actual kills and in-window
replacement/change controls cannot create acceptable complete observations.

Observation validity is interval-only under trusted local/quiescent-storage
assumptions. It is not a future snapshot credential or an adversarial-race,
power-loss or exactly-once guarantee. No performance improvement is claimed.
The second shadow supplies review evidence for a possible later A extraction;
it does **not** approve that extraction, B/C, process scheduling, publication,
new cache policy, service API or old receipt migration.

## Later Candidate Binding

The selected 0.2.0 readout and receipt retain their historical source/binary
binding. Candidate 0.3.0 is a separate
[shared-core extraction experiment](../shared_a0_extraction_review/README.md),
with new runs/identities and a protected SOF compatibility gate. Do not verify
the old receipt against current candidate bytes or overwrite its summary.
Only the inspector's Rust mechanics are shared; this independent Python
reference and application profiles remain distinct.
