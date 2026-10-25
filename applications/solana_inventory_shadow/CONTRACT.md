# A0 Read-only Solana Inventory Shadow v0

Application-local experimental implementation of the A0 boundary review, not
a public Rust API or implementation of B/C. The original Solana producer,
checkpoint, receipts, semantic validators and execution identity are unchanged.
The inspector has a separate executable/observation identity. No lock,
publication, quarantine, retry admission or common receipt lifecycle is extracted.

## Exact Scope

One flat, caller-declared root, exact regular-file membership, lengths and full
SHA-256. Manifest and independent expected declarations are detached from that
root. Controls inside the root are rejected, including self-reference. No
manifest exclusion list, recursive traversal or ignored extra files exists.

The manifest schema is `sof-runtime.a0-flat-inventory.v0`, codec
`ascii-json-u64.v0`. Fields are schema, codec, declarations and entries.
Declarations contain producer (id, version, executable_sha256), typed source/
execution/checkpoint identity references (role, sha256), and their owning schemas
(role, id, version), sorted by role. Entries have name, kind=RegularFile,
byte_length and sha256, sorted by name. Detached bindings declare the exact
expected metadata under `sof-runtime.a0-inspection-bindings.v0`; matching a
declaration does not authenticate it. The inspector does not parse domain files.

The codec implements the review's printable-ASCII, unsigned-u64 JSON profile.
Reject duplicates, noncanonical incoming bytes, floats/negative numbers,
unsupported versions/fields and identity-role mismatch. No old artifact is
parsed/re-encoded with this codec. Output includes exact canonical manifest
text/digest so Python can compare its bytes, not merely the entry count.

Backend v0 is local Windows NTFS with readable file identity and stream metadata.
Other filesystems/platforms or unavailable inspection primitives are unresolved.
Open only existing objects for read, without following the final reparse point;
check ancestors, root and actual handles. Reject reparse points, nonregular
files, hard links, file-ID aliases, DOS device names, ADS syntax/named streams,
case-fold aliases, 8.3 path aliases, rooted/traversal/UNC/drive paths in names,
and unsupported names. Roots are explicit local absolute drive paths. Names
use ASCII letters/digits/period/underscore/hyphen, with no trailing period/space.
The inspector's normal code path writes only stdout. Fault markers are a
test-only CLI hook confined outside all observed inputs.

## Observation Lifetime

Keep root, ancestor, input-control and payload handles through observation.
Enumerate before and after; hash through the actual handles, then re-read and
recheck handle/path identity, type, link/stream metadata, length and write data.
Missing/replaced/changed objects during observation are unresolved, not a
successful immutable snapshot. Initial declaration/type/content mismatches are
mechanical rejections. Failure cannot yield a matching observation.

Validity is `OBSERVED_INTERVAL_ONLY`, including the recorded start/end and
verification facts. It is not a credential for any future read. Assume trusted
local storage and source quiescence; finite pre/post checks do not defeat an
adversarial writer that changes/restores data between checks. File IDs are
temporary observation facts, not persistent portable content identities.

## Shadow Controller and Evidence

Python independently implements codec, membership, byte/type/handle/stream
checks using the OS API, not the Rust library. Shared OS semantics are not an
independent security proof. A test-local controller launches a fresh inspector,
captures stdout and kills it at named hooks. This is not extraction of B.
Partial output, nonzero/unknown exit or a kill cannot be admitted as a completed
matching observation. Detached observations use MATCHED_BYTES, REJECTED or
INCOMPLETE; they never set a Solana Pass or source-approval field.

Use copies of one source-bound existing publication state and its producer
receipt, inspected as separate flat roots. Original artifacts and copies must
remain byte-identical after ordinary observation. Only hostile fixture copies
are deliberately damaged. Original application validation runs read-only with
the original producer identity, never the new inspector's hash.

For the semantic-boundary control, alter a transaction fee in a copied slot
segment, retain the old checkpoint, then declare the copied bytes accurately.
A0 must match that inventory while the old application reference rejects the
segment against the source projection. This proves separation of obligations,
not domain validity or a new Solana execution theorem.

Acceptance retains normal/full-manifest parity, hostile declarations/files,
actual kills, mutation/replacement during observation, re-verification after
post-observation change, Windows ADS/hard-link/junction controls, original
identity preservation and code/binary/input hashes. No speed claim, live input,
power-loss guarantee, external attestation or old evidence replacement follows.
