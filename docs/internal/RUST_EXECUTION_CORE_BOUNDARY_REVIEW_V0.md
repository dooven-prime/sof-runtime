# Rust Execution Core - Boundary Review v0

Date: 2026-10-24. Status: `CONTRACT_ONLY_REVIEW_RECORDED`.
This is an internal design specification, not an implemented library, public
API, wire contract, migration, test receipt or promotion decision. No application
code, old receipt, installed SOF facade or vendored contract changes here.

**Decision:** start with A0, a restricted Artifact Identity & Inventory shadow.
Keep B (process execution) as a separately gated design; keep C (publication)
as a mechanical lifecycle sketch, not a common recovery protocol. Implementation
and migration of even the first application require their own acceptance run.

The governing boundary is:

```text
application policy -> execution mechanisms -> observed evidence artifacts
                  <- explicit mechanical failures / observations
```

The core does not decide mathematical truth, source trust, checkpoint
inheritance, consumer sufficiency or application success. The
[inventory](RUNTIME_EXECUTION_CONTRACT_INVENTORY.md) and
[source-addressed review inputs](RUST_EXECUTION_CORE_BOUNDARY_REVIEW_V0.inputs.json)
are the basis. The latter records files read, not a fresh replay attestation.

## 1. Evidence and Extraction Decisions

"Two applications" means distinct application workloads, not two versions of
Solana replay. Their local checks are not independent external verification.
Existing source-bound controls support candidate mechanisms, not equivalence
of unimplemented common Rust code.

| Mechanism | Distinct bounded evidence | Review decision |
| --- | --- | --- |
| Raw SHA-256, lengths and explicit version/binary binding | MaleCNS [cache](../../applications/malecns_profile_census/CACHE_READOUT_V1.md), [sparse kernel](../../applications/malecns_sparse_kernel/READOUT_V0.md), Q2 [plans](../../applications/event_causal_consumers/parallel_v0/READOUT.md), Solana [publication](../../applications/solana_publication_recovery/READOUT_V0.md) | Candidate A0. Binding is not authentication or semantic validation. |
| Exact declared file membership and corrupt/missing input refusal | Cache packet/manifest; Q2 task/result closure; Solana segment/state inventory | Candidate A0 for one declared flat directory; no automatic general recursive scanner. |
| Deterministic encoding | Cache identity, Q2 typed values and Solana manifests | Only a restricted manifest codec is proposed. Shared arbitrary-JSON canonicalization is NOT established. |
| Fresh process, timeout/kill, output capture and resource observation | Q2 workers, MaleCNS sparse runner, cache builder and Solana fault controller | Candidate B, later. Current controllers are mostly Python; a Rust implementation is unverified. |
| Exclusive local lock, private stage and directory rename | MaleCNS cache and Solana publication recovery | Common primitive shape only. Lock address, admission, recovery and cleanup differ. C deferred. |
| Reapproval, quarantine, checkpoint adoption, global PASS or arithmetic acceptance | Different application laws | Not core responsibilities, even when some implementations share helpers. |

Read-only findings from actual implementations:

- Cache [execution](../../plugins/rust/prepared-input-cache/src/main.rs) uses
  a bounded-wait per-key lock, can explicitly quarantine/rebuild invalid entries,
  and ignores abandoned staging. Its key excludes paths and consumer executable.
- Solana [publication](../../plugins/rust/solana-publication-recovery/src/main.rs)
  uses fail-fast destination exclusion; intent includes destination, request,
  executable and complete input/parent inventories. It preserves mismatched
  stages/final output, and only rebuilds its owned calculation scratch.
- Q2 [reduction](../../applications/event_causal_consumers/parallel_v0/coordinator.py)
  checks complete coverage and cross-shard fibers; the worker cannot issue PASS.
  A completed process may carry a valid application rejection.
- Sparse [execution](../../applications/malecns_sparse_kernel/runner.py) checks
  process status and application output separately. Sampled RSS/CPU readings
  are observations, not a hard memory sandbox.

These findings rule out a universal `get_or_rebuild`, universal retry identity,
automatic quarantine, or a universal "success after rename" operation.

## 2. A0: Artifact Identity & Inventory

### 2.1 Identity Types

Illustrative Rust shapes only; constructors and serialization are not public:

```rust
struct ContentDigest([u8; 32]); // SHA-256 of exactly the supplied bytes
struct SourceIdentity(ContentDigest);
struct ExecutionIdentity(ContentDigest);
struct CheckpointIdentity(ContentDigest);
struct InventoryIdentity(ContentDigest);
struct AttemptId(String); // observation/lifecycle identity, not content identity
```

No implicit conversion between identity roles, no universal `ArtifactId`, and
no equality across roles merely because 32 bytes match. An explicit application
declaration binds each role to its owning schema, encoding and derivation rule.
Wrapping a digest gives a role, not trusted-source or validated-checkpoint status.
The core never derives SourceIdentity from a URL, ExecutionIdentity from a PID,
or CheckpointIdentity from a directory name.

Raw content hashing adds no hidden prefix or normalization to existing bytes.
Application identity construction remains application-owned; future domain-
separated hashes need a new declared profile, not a silent digest change.
Attempt IDs, timing, output paths and diagnostic metadata do not enter an old
identity unless that identity's owning contract already includes them.

### 2.2 Mechanical Manifest

Proposed A0 data, not a wire schema:

```text
Manifest = (core_schema_version, codec_profile,
            declared_producer, declared_schema_bindings, ordered_entries)
Entry    = (relative_name, kind=RegularFile, byte_length:u64, ContentDigest)
```

Producer/version/schema values are declarations checked for exact agreement
with caller-supplied expectations. They do not attest that the producer ran,
interpret a domain schema or authorize use of that schema. Unknown versions
are rejected, not guessed or upgraded. Domain payload files stay opaque.

First codec profile: fixed ASCII metadata keys, printable ASCII string values
(0x20--0x7e), unsigned decimal u64 integers, Boolean, null, arrays and objects.
Encode quote as `\"` and backslash as `\\`; all other printable ASCII, including
slash, is literal. Integers use `0` or a nonzero leading digit followed by
decimal digits. UTF-8; lexicographically sorted object keys; no BOM, whitespace
or final newline; array order preserved. Reject duplicate keys, unknown schema
fields, out-of-range integers, floats/exponents, negative zero and noncanonical
encodings. No Unicode/case normalization or generic number rewriting.

Proposed codec-level vectors (not complete manifest instances; code delimiters
and display line endings are not bytes in the vector):

| Logical value | Exact canonical bytes |
| --- | --- |
| Empty object | `{}` |
| Object with b=2 and a=1 | `{"a":1,"b":2}` |
| Array retaining order 2,1 | `[2,1]` |
| String containing one quote | `{"s":"\""}` |
| String containing one backslash | `{"s":"\\"}` |
| String containing a slash | `{"s":"/"}` |
| Largest u64 | `{"n":18446744073709551615}` |
| Distinct Boolean, null, integer and string | `[false,null,1,"1"]` |

Examples `1.0`, `1e0`, `-0`, duplicate keys and u64 overflow are rejected, not
repaired. Escaped `\u0061` as an alternate spelling of literal `a`, escaped
slash, extra whitespace and an appended newline are noncanonical incoming
bytes. Control/non-ASCII characters are outside this profile even if JSON can
represent them. Encoder object insertion order does not change the result;
verifier input must already have the declared canonical bytes.

These rules are narrower than existing domain JSON; old files are hashed as
bytes and never parsed/re-emitted through this codec to preserve their identity.

First inventory scope: one caller-declared flat root and an exact set of regular
files. Entries are sorted by their validated relative names. Require declared
length and full digest, reject missing/extra files, duplicate/aliasing names,
wrong type, truncation or changed bytes. Do not infer semantic completeness
from matching this declared membership. A complete shard directory does not
prove complete Q2 coverage; a complete Solana directory does not prove continuity.

The inventory's own manifest/receipt is detached or excluded by an explicit
non-self-referential schema scope, never by an ad hoc "ignore extra files"
option. Metadata exclusion must not hide unregistered payload. Payloads such
as writer.lock are verified as declared bytes, not given Solana-specific rules.

### 2.3 Paths, Writes and Validity Lifetime

- Use a validated root and single relative filename. For A0 accept only ASCII
  letters/digits plus `.`, `_`, `-`; reject empty, `.`/`..`, rooted/drive/UNC
  paths, either separator, colon/ADS, trailing dot/space and Windows device
  names. Reject case-fold aliases rather than silently rewriting names.
- Reject symlinks/reparse points, nonregular files and ambiguous roots/aliases.
  Recursive trees, arbitrary Unicode names and hard-link sharing are deferred.
  Uninspectable file identity/type/link metadata is unsupported, not accepted.
- A future writer uses create-new in newly owned scratch, never overwrite,
  truncate or replace an existing path. Verification alone never mutates input.
- Require source quiescence under the declared local/cooperative model. Record
  the opened file's identity/type/length, hash complete bytes, then recheck the
  relevant handle/path identities and membership before returning. Detected
  replacement or mutation fails. Lexical confinement alone is insufficient.
  OS file IDs are observation facts, not portable persisted content identities.
- A check describes the observed read interval. It supplies neither an immutable
  snapshot nor a reusable credential for future reads. Pre/post checks do not
  defeat a malicious writer that changes/restores bytes between observations.

The initial backend is the existing local Windows test environment, not a
cross-platform security guarantee. If the necessary no-follow/type/alias checks
cannot be supported, narrow/reject that backend instead of weakening the promise.

## 3. B: Process Execution & Outcomes

Keep process facts, parsed application claims and accepted domain decisions in
separate records. A future process observer can expose:

```text
ProcessOutcome = Completed | Failed | TimedOut | Killed | ResourceStopped
               | SpawnFailed | UnresolvedTermination
ProcessObservation = (AttemptId, executable/request/config digests,
                      argv, cwd, environment profile, exit observation,
                      stop requests/events, stdout/stderr references,
                      wall/CPU/memory observations and measurement scope)
ApplicationAssessment = application-owned decision + typed domain reason
```

Completed means observed normal zero exit, not application Pass. Failed retains
the actual nonzero exit/signal information; a nonzero Solana refusal can still
contain a valid application Reject. Conversely Q2 may return an application
failure after a zero exit. Malformed/missing output is not a mathematical
counterexample. No observer promotes worker COMPLETE to global PASS.

The observer preserves opaque result bytes, including nonzero-exit stdout;
the application parses, checks and decides. R/G/T clauses, source conflicts,
corrupt cache reasons and exact/numerical acceptance never become core enums.
Pass/Reject/Unresolved may be an adapter presentation, not core-owned semantics
or replacements for existing application statuses.

Timeout, resource stop and kill require explicit controller events, not an
inference from an exit code alone. Preserve event order, configured thresholds,
observed exit and any ambiguity/race; do not claim causal certainty about an
unobserved termination. A future profile must define classification precedence.
Spawn failure and unknown termination cannot fall through to Completed.

Require finite timeout, bounded log capture, explicit environment and eventual
child reaping in every path. Record unavailable measurements as unavailable,
not zero; distinguish sampled RSS from OS peak and soft stop from enforced
limit. Do not add nested time intervals. Root-child termination is the first
scope: descendant/job cancellation, sandboxing, remote workers and resident
services remain unimplemented obligations, not effects of a kill method.

## 4. C: Local Publication Mechanics, Not a Transaction Protocol

### 4.1 Proposed Physical States

```text
InputBindingsChecked -> LockHeld -> PrivateStage
  -> application constructs and semantically validates the output
  -> StageInventoryChecked -> DirectoryPublished
  -> PublishedInventoryChecked -> MechanicalObservationBound
  -> application may validate/bind its own success receipt
```

StageInventoryChecked records an exact expected inventory and opaque references
to application checks. Those references are not core-issued semantic authority.
Keep the lock through construction/validation/publication as required by the
application, not only around rename. Recheck declared bindings at required
boundaries; callbacks do not permit silent identity changes.

Only an absent target is eligible in the candidate common lifecycle. Use a
same-filesystem private stage; do not expose pending files as final. Existing
targets are conflicts for the core, even if an application later chooses to
revalidate/adopt them using its own contract. No generic replace flag.

DirectoryPublished means a local visibility milestone only. A failed post-
publication check or lost process/response can leave a directory but no accepted
application success. Preserve that physical fact in failure observations.
A mechanical receipt binds observed files/events, not source permission,
checkpoint compatibility, exactly-once processing or external delivery.

### 4.2 Locks Are Not Interchangeable Policies

| Question | Finding | Candidate boundary |
| --- | --- | --- |
| Same-key lock versus destination exclusion | Both use exclusive OS locks, but protect different equivalence classes. Two keys can alias one path; one key can occur under different roots. | A lock-address/guard primitive may be shared; key-to-address and destination reservation stay application-owned and explicit. |
| Wait policy | Cache waits with a bound; Solana fails fast. | Specify wait policy and timeout, never a shared hidden default. A persistent lock filename is not ownership or a stale lease. |
| Multiple resources | Destination and parent/input guards can coexist. | Declare acquisition order and alias checks before writes; do not infer a deadlock-free plan or global exclusion from one guard. |
| Cache quarantine versus Solana refusal | Quarantine/rebuild deliberately moves an invalid entry; Solana preserves mismatched state/evidence. | No common quarantine/rebuild/automatic cleanup. |
| Abandoned stage | Cache ignores it; Solana can complete exact pending prefixes but only under its own bound intent and fresh calculation. | No generic stage adoption or resume credential. |
| Retry identity | Cache key excludes paths/consumer; Solana intent includes destination/executable and parent/input bytes. | Pass typed opaque application bindings; do not manufacture one universal retry key. |

A future lock primitive must declare its namespace/backend, supported filesystem,
mode, wait policy and protected resource, and be tested against the existing
std/fs2 lock users before mixed use. Different lock filenames or incompatible
backends do not magically exclude each other.

### 4.3 Failure, Recovery and Trust

The core may return mismatch, busy, unsupported or IO observations; it must not
decide to quarantine, rebuild, inherit a prefix, trust a ready marker, skip
validation or emit application success. Application-supplied retry evidence
still requires application validation on the actual inputs. An old receipt is
not evidence of current file integrity.

Default failure handling preserves stage/final evidence. Any later cleanup
primitive must require ownership of precisely the newly created scratch scope,
verify resolved paths and reject links; it cannot sweep named prefixes or delete
input, parent, foreign final or application evidence directories. Disk-full,
rename/sync failure and permission errors preserve explicit physical-stage
information. File sync does not imply directory durability after power loss.

Assumptions remain trusted local storage, cooperating writers using the declared
locks, quiescent sources, bounded resource observations and process-crash tests.
No hostile namespace race defense, network filesystem, distributed commit,
cryptographic producer attestation or external exactly-once guarantee is added.
The implemented Solana recovery journal remains application-owned; C does not
yet have a common persistence/recovery format.

## 5. Error Model and Application Mapping

Mechanical error families: `InvalidDeclaration`, `UnsupportedProfile`,
`UnsafePathOrType`, `InventoryMismatch`, `BindingMismatch`, `InputChanged`,
`LockBusyOrTimeout`, `DestinationConflict`, `IoFailure`, `ResourceLimit` and
`IncompleteObservation`. Retain operation/stage, path role, expected/observed
facts and underlying OS error where available. An error after publication must
not falsely say "nothing was written". Public path redaction, if ever needed,
is a separate presentation policy; bound internal evidence retains identities.

| Application | Candidate mechanism use | Semantic authority retained by application |
| --- | --- | --- |
| MaleCNS profile/cache | Digest/length/version checks; later process/lock observations | Integer signature, GCD normalization, global class merge, source admission, packet grammar, cache key, quarantine and reuse permission |
| MaleCNS sparse | Packet/output inventories and process measurements | Transpose/normalization, rational arithmetic, floating tolerances, summation order and clipping |
| Q2 | Task/result bindings, per-directory inventory and worker lifecycle | Generated-domain saturation, shard coverage, typed expressions, cross-fiber R/G/T, clause priority and actual-history replay |
| Solana | Flat state inventory; later stage/lock observations | Transaction order/version, continuity, source permissions, checkpoint anchors, reapproval, earliest conflict, pending completion and retry acceptance |

`IntegrityMatches` is therefore a mechanical observation, never a renamed
`ValidatedSource`, `SufficientState`, `CompatibleCheckpoint` or `Pass`.

## 6. Shadow Plan and Gates

### Gate 1: Contract-Only Review

This document records a narrow candidate, mappings and unresolved obligations.
There is no implemented shared crate or public contract. Before writing A0,
review the exact codec vectors, path/alias/backend support and detached inventory
scope. B additionally needs outcome race precedence and process-tree policy;
C needs lock interoperability and a separate lifecycle/recovery review. A0
agreement does not approve B/C or application migration.

### Gate 2A: First Read-Only Artifact Shadow

Choose one small Solana publication-inventory adapter, not a publisher. Leave
the original producer, validators and recovery path untouched. Run/copy their
declared fixed fixtures into a new shadow-owned workspace. A candidate A0
inspector checks the application-supplied exact inventory in parallel with a
separate Python byte/length/type reference. The old application still decides
semantic validity; no core-only integrity success is presented as its success.

The producer's original identity remains bound to its old bytes. The new shadow
executable has a separate observation identity, never the old ExecutionIdentity.
Do not replay an old checkpoint as if generated by a new executable. Compare
every unchanged application artifact byte for byte, including checkpoints and
receipts, not just projections/counts. Keep new shadow metadata detached. If a
later design changes producer identity, it needs a new closure and migration
decision; do not strip identity fields to manufacture equality.

Predeclare controls:

| Control | Required result |
| --- | --- |
| Exact fixed inventory and supported canonical manifest vectors | Rust/Python entries, lengths, digest and manifest bytes agree; all original files unchanged. |
| Same digest bytes assigned to different identity roles | Type-level noninterchangeability; serialized role/schema mismatch rejected. |
| Missing/extra/truncated/damaged/wrong-type files | Mechanical rejection with explicit path role and expected/observed facts, not an application theorem. |
| Traversal, drive/UNC/ADS/device paths, case aliases, links and existing output path | Reject without writes outside newly owned shadow space or replacement of original files. |
| Duplicate keys, unsupported floats/Unicode/version | Reject unsupported/noncanonical input; no silent normalization of old artifacts. |
| Object insertion order versus array order | Object insertion order must not change canonical bytes. Array reordering changes bytes/digest; reject if it violates declared bindings or the inventory's sorted-entry rule, not merely because it is an array permutation. |
| Actual kill during enumeration/hash/diagnostic writing | Incomplete observation cannot be admitted; fresh full verification agrees with clean reference; no partial observation is accepted as a receipt. |
| Input mutation/replacement or changed producer/schema binding | Refuse the changed observation; never authorize retry/reuse. |
| Well-hashed semantically invalid domain payload | A0 may correctly report matching bytes; the application must still reject it. This control tests the semantic boundary. |

Use the existing external Python fault controller; testing process death here
does not require extracting B. Avoid performance or reduction-of-validation
claims. Stop on any mismatch or unsupported confinement prerequisite.

### Later Gates, Not Work Authorized by This Document

After A0's first source-bound acceptance and boundary review, consider a second
artifact consumer: the MaleCNS prepared-cache inventory with unchanged packet
validation/key/quarantine rules. This is a second application, not an immediate
cache migration. Only after both adapters pass should an A library extraction
be proposed. No simultaneous all-application refactor.

B shadow later compares old/new process observations and application decisions
on the same bounded input while preserving both layers and domain reason codes.
C shadow requires a separately approved application shim with real kills at
staging, rename, verification and receipt boundaries, path conflicts and corrupt
input. Retain the old publication path as the control and require complete
bytewise comparisons, parent preservation and invalid-publication refusal.
The existing 18-point Solana matrix is a baseline to rerun, not evidence that a
future common C implementation already passes it.

## 7. Stop Conditions and Disposition

- Stop/shrink if the core needs `if application == ...`, parses packets/slots/
  R/G/T or adds producer trust, retry admission or domain success rules.
- Stop if shared locking cannot protect the declared resource/alias plan without
  changing an application's assumptions, or if cleanup/rebuild policy leaks in.
- Stop if canonicalization changes old bytes, unsupported paths are accepted,
  incomplete observations can count as complete, or evidence disappears on error.
- Stop if comparing a new producer requires pretending its executable identity
  did not change, relaxing old validators, skipping revalidation or replacing
  old receipts. Preserve old code/evidence and record the incompatibility.

The smallest proposed common core is **byte identity plus exact confined
inventory**, under a restricted encoding and filesystem profile. Process
observation and local publication are later candidates with distinct gates.
Application semantic acceptance, recovery/adoption and all scientific/chain
claims stay outside. No public Rust API is released by this review.
