# A0 MaleCNS Prepared-Cache Inventory Shadow v0: Local Readout

2026-10-24. Status: `PASS_LOCAL_READ_ONLY_A0_CACHE_SHADOW`.
See the [contract](CONTRACT.md), [plan](plan.v0.json) and compact
[selected summary](results/acceptance-summary.v0.json). This is a second
experimental application shadow, not shared-library extraction or migration.

## Fixed Original and Distinct Observer

The original full somaSide entry and its 254,592,750-byte packet are copied
exactly. Another flat root holds the original benchmark receipt, archived
request and semantic result. All five payload files remain byte-identical to
their originals; the original complete run, carrier source hashes, source code
closure, producer and consumer binaries remain unchanged.

The packet SHA-256 remains
`b23d2c7a75f3c57cb9635bef28fd418a21998e97ad94f5cba79a553367ec6c32`.
The original cache producer SHA-256 remains
`fa3e15956cc277999c6d5dc52183d05743369d2adbe0e900dafe5b35a44ad938`.
The new A0 observer SHA-256 is separately
`b895128695ffdcf50a3f1820e40086c306fad11835d5a6f8aa7eb49d616220c8`.

The candidate adds a nominal CacheIdentity and explicit cache metadata profile;
it does not relabel that digest as a CheckpointIdentity. Source, declared
execution-input and cache identity derivations are application-owned and
documented in the contract. No new identity is retroactively assigned to an old
receipt. Observer identity is not producer identity or cache identity.

## Acceptance Results

| Control | Result |
| --- | --- |
| Normal cache entry and archive | Rust/Python exact manifest bytes, ordered entries, lengths, types and hashes match. Original probe accepts the normal entry without consuming it. |
| Identity/declaration controls | Eight refusals, including role substitution even in matching declarations, checkpoint slot, wrong key/producer, profile mismatch and self-reference. |
| File controls | Eight refusals: missing, extra, damaged, truncated, directory, actual case mismatch, hard link and actual NTFS ADS. |
| Actual process death | Three kills on the full cache copy at enumeration, hashing and partial output. No incomplete result becomes a matching observation or cache permission. |
| In-window mutation | Four changes, including same-byte replacement, are INPUT_CHANGED/INCOMPLETE. Every fresh observation still grants no cache permission. |
| Lifetime | A later changed packet is rejected against the old inventory. The earlier observation remains historical, not a future credential. |
| Semantic negative | Truthfully hashed invalid packet matches A0; the original application probe rejects its zero source-sign record. |

There are 27 primary cases and 35 inspector invocations including fresh checks.
Primary outcomes are four MATCHED_BYTES, 16 REJECTED and seven INCOMPLETE.
Matching includes the semantic-negative object and an earlier valid interval;
it is not a count of accepted cache hits. Every observation records
`cache_hit_permission: NOT_GRANTED`, `cache_policy: NOT_INVOKED` and
`application_decision: NOT_ASSESSED`.

The hostile full-carrier copy preserves its valid preamble, header and length.
Its first record's sign is changed to zero, and both the old manifest's digest
and detached A0 declarations are accurately rebound to the bad bytes. The
unchanged original `validate_entry` reached through the existing read-only
probe rejects with `source record bounds/order`; the unchanged Python packet
reader independently rejects with `invalid source record`. This is not a
checksum-only refusal. No cache execution, rebuild or quarantine was invoked.

## Cross-Application and Saved Evidence

The original Solana shadow is rerun in a new directory with candidate 0.2.0:
43 controls, six actual kills and both Python test modes pass again. Its prior
0.1.0 receipt is not overwritten. The earlier A0 source and executable are
retained in a local snapshot and match the earlier receipt's exact hashes.
The file/NTFS backend, codec and executable entrypoint are unchanged; only the
typed declaration profiles are extended. The Python reference remains
independent of Rust; its shared OS assumptions are not a security proof.

The full local receipt is
`runs/a0-malecns-cache-shadow/acceptance-v0-final/acceptance.v0.json`, SHA-256
`dd64b4159d94a83f58672e87980a530012e27184dd5511d57e772945d8455393`.
It binds 2,110 evidence objects, including the newly recorded Solana regression.
Full runs are ignored local data, not a self-contained public release package.

Both ordinary and -O modes pass 11 MaleCNS test methods plus their subcases.
The Solana regression passes 12 methods in each mode. Rust passes two unit
tests and two compile-fail identity-role doctests. Saved verification rechecks
the inventories, original data/source bindings, Python decisions and negative
grammar control; it does not rerun Rust or independently attest past kills.

## Disposition

The second workload supports the same mechanical/semantic boundary: matching
an opaque inventory does not authorize use of its content. This is bounded
local evidence for reviewing a possible A extraction, not approval to do it.
Cache policy and execution paths remain untouched. There is no B/C extraction,
public runtime API, recursive scanner, immutable snapshot credential,
performance claim, power-loss guarantee or external execution attestation.
