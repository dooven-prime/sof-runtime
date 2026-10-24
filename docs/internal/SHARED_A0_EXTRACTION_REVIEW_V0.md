# Shared A0 Core Extraction Review v0

2026-10-25. Scope approved: a restricted **internal, non-published extraction
experiment** after the two read-only shadows. This document does not authorize
production migration, public API publication or B/C work. The
[SOF compatibility guard](SOF_COMPATIBILITY_GUARD_V0.md) is a blocking gate.

## Ownership

| Module | Shared mechanism | Remains outside |
| --- | --- | --- |
| `identity` | Raw SHA-256, unsigned byte length, nominal Source/Execution/Checkpoint/Cache wrappers | Trust/authentication, cache key and checkpoint derivation |
| `codec` | Exact `ascii-json-u64.v0` metadata encode/decode | Historical JSON encodings, domain schema/normalization |
| `inventory` | Exact single-level membership, local NTFS handles/types/streams/aliases, two-pass hashes and changed-interval refusal | Packet grammar, slot order, cache permission, complete-state admission |

`a0-mechanical-core` is a library with `publish = false` and exactly these three
top-level modules. The NTFS backend is private to `inventory`. Mechanical
errors are shared; there is no application PASS, source approval, writer, lock,
process executor, publisher or retry state machine. Nominal identity constructors
only wrap an explicit caller declaration; equal digest bytes do not convert
between roles. ByteLength is a u64 length, not another content identity.

## Adapter Boundary

The inspector becomes version 0.3.0. It owns the existing checkpoint/cache
declaration profiles, producer/schema equality rules, stdout envelope and test
pause hooks. It delegates all actual file inspection to a path dependency on
the single shared library. Its duplicate identity/codec/NTFS source files are
removed, not retained as a fallback.

The shared inspector opens and holds the exact detached declaration/binding
files, supplies their observed bytes to the caller's profile decoder, validates
the returned Entry list itself, and rechecks controls and files at the end.
The callback does not give core-owned approval to an application schema. Both
Python application adapters invoke the same linked executable; their reference
implementations remain separate from Rust for cross-language checking.

The exposed restricted encoder now rejects unsupported output Values as well
as refusing unsupported input bytes. Supported canonical bytes and old profile
acceptance are unchanged. Sorting is explicit, not dependent on an unrelated
serde_json map-order feature. This is not normalization of historical payloads.

The exact flat scope remains 4096 files/512 MiB on inspectable local Windows
NTFS. There is no recursion, Unicode namespace expansion, immutable snapshot
credential, adversarial change-and-restore protection, durability or performance
claim. Observations retain their original interval-only and no-domain-decision
semantics.

## Frozen Identities and SOF Lane

Keep prior 0.1.0 and 0.2.0 observer sources, executables and all prior receipts
under their original hashes. The old application producers, carrier sources,
cache packet, checkpoint and receipt bytes never become output of the new
observer. New library/adapter/binary bytes receive new implementation bindings.
Do not suppress old receipt binding failures by substituting a new executable.

The SOF Python facade, compiler, assembly, comparison, action, validators,
vendored contracts, reference artifacts and version identities remain unchanged.
The extraction is used by shadow code only. Neither SOF nor Solana receives a
new semantic interpretation, and the Python runtime is not replaced by an
unvalidated Rust equivalent.

## Acceptance

1. Freeze the prior candidate and protected SOF file membership/hashes. Run the
   unchanged SOF test closure against this checkout's source explicitly, not a
   different editable install. Preserve failed attempts rather than rewriting
   their results; environmental retries must be identified.
2. Run shared crate tests, exact codec vectors, unsupported-output refusal,
   nominal-identity compile-fail controls and the inspector tests.
3. Reexecute Solana's 43 cases and MaleCNS's 27 cases in new owned directories,
   including actual kill and changed-window controls. Run both ordinary and -O
   Python suites and saved byte/type/link/stream verification.
4. Compare with the prior accepted 0.2.0 records: mechanical status, failure
   class/code, matching canonical manifest bytes/entries/digests, fault points
   and observation lifetime must agree. New observer identities, PIDs, timings,
   local paths and filesystem-instance IDs are intentionally not equalized.
   This comparison is against saved source-bound local controls, not a fresh
   execution attestation of the earlier candidate.
5. Keep both digest-correct/domain-invalid controls: A0 matches while the
   unchanged Solana reference and MaleCNS protocol validator reject. No shared
   mechanism is permitted to resolve that deliberate difference.
6. Rerun the SOF gate and installed-wheel check. Exact protected bytes and test
   identities/counts/skips/outcomes must match the before closure. Any drift
   blocks acceptance, irrespective of A0 results.

The review's lexical module/policy/writer scan is an additional stop control,
not a whole-program proof or security audit. A bounded local PASS supports this
one extraction experiment only. It neither publishes a Rust API nor approves
service integration or a second mechanical subsystem.

## Stop Rule

If implementation needs Solana slots, MaleCNS sign rules, quarantine,
checkpoint inheritance, source approval or retry admission inside the core,
shrink the interface. Do not enlarge A0 to make extraction work. If exact old
bytes, independent references, same-interval refusal or SOF compatibility cannot
be maintained, preserve evidence and leave acceptance unresolved or rejected.
