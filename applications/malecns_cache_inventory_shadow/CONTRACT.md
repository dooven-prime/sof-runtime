# A0 MaleCNS Prepared-Cache Inventory Shadow v0

This is the second read-only application of the experimental A0 inspector,
not a shared-library extraction, public API, cache migration or performance
claim. B/C, application locks and publication/recovery policy remain untouched.

## Frozen Application and Opaque Payloads

The full `cache-baseline-v1-final` prepared entry is copied byte for byte,
including its original `manifest.json` and 254,592,750-byte `packet.bin`.
The original benchmark receipt, semantic result and archived request are also
copied into a separate flat inventory. A0 metadata is detached from both roots.
The old cache manifest is ordinary opaque payload, not the A0 inventory itself.
The old producer, preparer, source identities, output and receipts are unchanged.

The unchanged `cache-cost-probe` uses the original cache validator by source
inclusion. Only its existing read-only `probe` action is used: full source and
preparer checks, packet hash and original `validate_entry` including grammar.
It never calls the cache lookup/execute/rebuild branch. Its outcome is not a
cache-hit permit. No new executable is substituted for the old producer.

## Explicit Identity Profile

Inspector candidate 0.2.0 adds `sof-runtime.a0-cache-flat-inventory.v0` and
`sof-runtime.a0-cache-inspection-bindings.v0` alongside the unchanged checkpoint
profile. Cache identity cannot occupy a CheckpointIdentity slot. Mixing a
profile with the other profile's identity set is rejected, even if both
declarations agree. The codec, flat membership and Windows backend are unchanged.

Application-owned declarations are:

- `SourceIdentity`: SHA-256 of the old canonical ordered source-artifact list.
- `CacheIdentity`: the original key, SHA-256 of the complete prepared identity.
- `ExecutionIdentity`: SHA-256 of the new **declared input** record
  `(schema, original producer hash, cache key, original consumer declaration,
  invalid policy)` defined in `fixtures.declarations`. This is a detached
  observation binding, not a claim that the old receipt contained this identity,
  or an attestation of an actual execution. Old bytes are never rebound.
- `ShadowObserverExecution`: actual new observer executable SHA-256, separate
  from all producer and application-input identities.

Schema bindings are explicit. Role wrappers are nominal Rust types, with
compile-fail substitution controls; Python checks each exact serialized role.
Same SHA bytes in different wrappers do not make their roles interchangeable.

## Exact Inventory and Observation Lifetime

The inherited codec is `ascii-json-u64.v0`, with strict unknown-field/version,
duplicate, order, alias and noncanonical-byte refusal. Each root has an exact,
single-level set of ordinary files, at most 4096 entries/512 MiB. The backend
requires local Windows NTFS metadata and rejects hard links, reparse points,
named streams, device/ADS/traversal forms and case aliases. It is not a generic
recursive directory scanner. The test evidence recorder is a separate facility.

Open handles, two byte passes, path/file identity and final membership checks
bound an observation interval. Detection of change/replacement or actual process
interruption cannot yield an admissible matching observation. A later fresh
same-byte replacement may match again, but still grants no cache permission.
This is not an immutable snapshot credential, a hostile change-and-restore
defense, power-loss durability or independent execution attestation.

## Mechanical/Semantic Separation

All observations say `application_decision: NOT_ASSESSED`,
`cache_hit_permission: NOT_GRANTED`, `cache_policy: NOT_INVOKED`.
Quarantine, rebuild, key derivation, source admission and consumption permission
belong exclusively to the unchanged application, irrespective of A0 matching.

The negative full-carrier copy has a correct preamble/header and size, but the
first row sign is zero. The original manifest's packet digest and detached A0
inventory are accurately updated **only in the hostile copy**. A0 must match;
the original validator must reject with `source record bounds/order`. Neither
result is repaired to match the other. This tests an intentional boundary.

## Evidence

The plan is fixed before acceptance. Compare complete entries, order, lengths,
digests and canonical manifest bytes with independent Python code. That code's
codec/NTFS implementation is copied from the first shadow, not from Rust; no
independent OS/security audit is implied. Re-run the original Solana shadow with
candidate 0.2.0 in a new directory, without overwriting its prior receipt.
Retain the prior candidate's source/binary snapshot against its recorded hashes.

Saved verification rechecks source bindings, full inventories and Python byte
decisions. It does not reexecute Rust or independently attest old process kills.
Selected summaries are local entry points, not self-contained public closures.
