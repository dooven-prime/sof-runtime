# Prepared Input Cache v1

Contract: `sof-runtime.prepared-input-cache.v1`. Scope: the local MaleCNS
profile packet and its existing Python preparer. This is an application-owned
execution contract, not a SOF result state, a paper theorem, or a Solana cache.

## Identity

The key is SHA-256 of canonical UTF-8 JSON for an identity containing:

- ordered source roles, names, lengths and content SHA-256 values;
- sector policy, including field and missing-label normalization;
- sign policy and its explicit transmitter/sign map;
- packet schema, magic, byte order and expected complete protocol header;
- preparer ID/version, source closure hashes, interpreter hash, selected
  dependency versions and normalized command template.

Paths, cache location, attempts, timing and the consumer executable do not
enter prepared-input identity. Source placeholders in the command template
are resolved separately. Changing a source hash, declared policy, format or
preparer version cannot reuse an old key. The production factory still
requires the two existing release-anchored carrier files; a changed source is
not silently admitted as a different MaleCNS carrier. Fixture mode is separate.

The preparer's declared closure and dependency versions are provenance, not
a hermetic-build proof. Requests and the local cache directory are trusted
application inputs; the tool is not a sandbox for arbitrary commands.

## Validity and Consumption

`entries/KEY/` is valid only when its canonical `manifest.json` binds the
requested identity/key and one regular `packet.bin`. The Rust validator checks
length, full SHA-256, canonical expected header, every source/edge record,
ordered source IDs, sign/sector bounds, positive weights, checked row masses,
declared row count, total edge count and EOF. A checksum alone is not protocol
validation. Symlink entry/packet/manifest files are rejected.

Source files and preparer closure are content-checked before lookup and again
before success. Referenced sources must remain immutable during the call;
before/after checks are not a defense against a malicious concurrent writer
that changes and restores bytes. A valid manifest supplies integrity and
provenance under the trusted-cache model, not cryptographic authorship.

An optional Rust census executable runs while the same per-key lock is held.
Its executable hash is checked, and packet integrity and source bindings are
checked again before returning a successful consumption receipt. The caller
must still compare its semantic output to the declared reference. Returning
a cache path without a consumer certifies validation at that return, not any
arbitrary later read of the path.

## Publication and Recovery

Use a stable per-key lock file and an exclusive OS file lock, held across
validation, preparation, publication and optional execution. It is released
on process exit; a persistent lock filename is not itself a stale lease.
Lock waiting is bounded and diagnosed separately.

Build under a unique `staging/KEY.ATTEMPT/` on the same filesystem. Validate
the complete packet, sync packet and manifest files, and publish the directory
by rename while holding the lock. Final entries never contain partially
written new packets. A failed or interrupted preparation publishes no entry.
Abandoned staging directories are ignored, not adopted or automatically
deleted. A killed parent may leave preparer work in its own unpublished
staging directory; cancellation of such descendant processes is a caller
responsibility, and the interruption test cleans up its test child.

Default invalid policy is `reject`: return `CACHE_INVALID_REJECTED`, without
executing a consumer or silently preparing again. Explicit `rebuild` moves
the invalid entry into a unique quarantine location and builds a new one.
There is no automatic deletion of quarantine or other attempts. Competing
cooperative builders for one key serialize; after one publishes, the other
validates and uses it rather than publishing a second build.

These are process-interruption guarantees on a trusted local filesystem.
Network-filesystem semantics, adversarial namespace mutation, disk failure,
and power-loss durability are not established. File syncing does not promote
this to a distributed or exactly-once execution protocol.

## Diagnostics and Costs

Success states are `CACHE_MISS_PREPARED`, `CACHE_HIT_VALIDATED` and
`CACHE_INVALID_REBUILT`. Rejections distinguish invalid requests, source or
preparer identity, lock timeout, invalid cache, failed preparation and failed
execution. Failures produce a nonzero exit and no success receipt.

Report source/preparer verification, lock wait, existing-entry validation,
preparation, newly built validation/publication, consumer execution, final
validation and whole-call time independently. Cache lookup is not free:
every hit still verifies source content and the full prepared packet.
The Python caller separately records request/identity construction and full
process wall time. No old performance evidence is rewritten.

## Acceptance

Tests must cover changed source identity, each key component, damaged payload,
wrong length/digest/header, absent/incomplete manifest, explicit rebuild,
failed/interrupted builder, concurrent same-key builds and lock timeout.
Use actual processes for interruption and concurrency, not only mocks.
Measure first preparation, validated hits and explicit rebuilds separately on
the unchanged complete carrier, and compare every census output with the
retained serial baseline. No parallel-speedup premise is introduced.
