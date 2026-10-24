# A0 Read-only Solana Inventory Shadow: Local Readout

2026-10-24. Status: `PASS_LOCAL_READ_ONLY_A0_SHADOW`. This is the first
experimental A0 adapter, not a public/shared library extraction or application
migration. B and C remain unimplemented common-core candidates.

## Fixed Origin and Identity

The [selected summary](results/acceptance-summary.v0.json) binds
`runs/a0-solana-inventory-shadow/acceptance-v0-final/acceptance.v0.json`, SHA-256
`92fec64b8735148c8efcd1789281e0c7a430fbdf6b620c3cf3eee4cd615a8cb4`.
The full local record binds 1,796 evidence objects, including directories,
intentional hard-link counts, junction targets and named-stream content. The
summary is not a self-contained public evidence package.

Origin is the unchanged publication-recovery `clean-reapprove` result on the
fixed 64-slot capture. Its producing executable hash remains
`a10a747cc69e1e57f032b806cb8bedf781326d2ca44347efb456d774056c9880`.
The A0 observer hash is separately
`29b434e4f62d4610d16f6f28bd7a6184f8bd43e37c1fc7ec8a87e26235626fe8`.
No checkpoint is reinterpreted as produced by that new executable.

Two ordinary input copies are inspected: 68 original state files and, separately,
one exact producer-receipt file. All copied files, including the checkpoint and
receipt, remain byte-identical to the originals. The whole original producer
run's byte inventory remains unchanged. Primary acceptance reads its existing
artifacts and reuses the unchanged Python semantic reference; it does not rerun
or replace the full original producer.

## Four Acceptance Groups

| Group | Local result |
| --- | --- |
| Normal manifest consistency | Both roots match in Rust and Python: exact ordered entries, lengths, hashes, canonical manifest bytes and metadata bindings. |
| Hostile declarations/objects | 18 declaration controls and 11 filesystem controls are rejected, including extra/missing data, wrong type, corruption/truncation, device/ADS/traversal/drive/UNC names, case aliases, self-reference, real ADS, hard links and junction/reparse points. |
| Execution and observation boundary | Six actual process kills leave no admissible matching observation. Four changes in the same observation interval produce INPUT_CHANGED/INCOMPLETE. Fresh complete observation is required after every interruption. |
| Semantic boundary | A copied slot segment has one transaction fee changed while its new bytes are accurately declared. A0 matches the inventory; the unchanged application reference rejects with SEGMENT_PROJECTION_DIFFERENCE. A0 never emits a domain-valid or source-approved result. |

There are 43 primary case records and 54 inspector invocations, including fresh
checks. Their primary outcomes are four MATCHED_BYTES, 29 REJECTED and ten
INCOMPLETE. The four matching rows include the semantic-negative control and
the historical first observation in the expiry control; they are not four
application successes.

Actual kill points are enumeration, hashing and partial-result output, for each
normal root. These are bounded named controls, not all instruction interleavings.
The changed-window cases cover content, same-byte file replacement, an extra
file and a newly introduced named stream. Same-byte replacement invalidates
that observation interval, while a fresh interval can match the content again.
This is intentionally not a permanent file-instance identity.

The expiry control separately modifies data after a completed observation;
another observation rejects it against the old manifest. The earlier observation
is retained as historical evidence, not reused as a snapshot credential.

## Verification and Retention

Ordinary and -O Python suites each pass 12 test methods with bounded subcases.
Rust passes two unit tests, the identity-role compile-fail doctest, and format
checking. The codec has the eight exact review vectors plus rejection controls.
Windows controls ran against actual NTFS streams, hard links and directory
junctions; they were not replaced by mocks. Path/handle normalization checks
also reject unsupported aliases, but no exhaustive Windows namespace coverage
or adversarial race-proof security result is claimed.

The local saved verifier passes in ordinary and -O modes. It rechecks the whole
file/type/link/stream inventory and independent Python decisions, the original
producer identities, partial-output refusal and the semantic-negative control.
It does not rerun Rust, reconstruct past file IDs or independently attest the
saved process events. Full runs remain ignored local data; the summary is only
a selected source-bound entry point.

## Extraction Boundary

The candidate library contains no Solana transaction parser, source approval,
lock, process supervisor, rename/publisher, quarantine or retry-admission logic.
The test binary's pause markers and the Python fault controller are not common
runtime services. The recursive hostile-fixture evidence recorder is not the
flat A0 admission inventory and is not extracted into the core.

The backend requires inspectable local Windows NTFS metadata. Checks describe
their observed interval under source-quiescence/trusted-storage assumptions,
not an immutable snapshot, power-loss durability, hostile change-and-restore
defense, future validation credential or external exactly-once delivery.
No validation is skipped and no performance improvement is claimed.

Existing application code/receipts and service/vendored contracts are unchanged.
The next decision is a review of this one shadow's boundary; neither a second
application migration nor B/C implementation is automatic.

### Later Candidate Note

This readout and selected receipt retain their original 0.1.0 candidate binding.
The [MaleCNS second shadow](../malecns_cache_inventory_shadow/READOUT_V0.md)
records a new 0.2.0 Solana regression and preservation of the old source/binary
snapshot. It does not replace this record or rebind its observer identity.
