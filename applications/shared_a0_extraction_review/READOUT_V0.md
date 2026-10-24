# Shared A0 Extraction Review v0: Local Readout

2026-10-25. Status: `PASS_LOCAL_SHARED_A0_EXTRACTION_EXPERIMENT`.
The [scope review](../../docs/internal/SHARED_A0_EXTRACTION_REVIEW_V0.md) and
[SOF guard](../../docs/internal/SOF_COMPATIBILITY_GUARD_V0.md) remain the gates.
This is bounded local engineering evidence for one internal extraction, not
production adoption or a public Rust runtime API.

## Single Rust Mechanism Source

The internal, non-published `a0-mechanical-core` 0.1.0 has exactly three
top-level modules: identity, codec and inventory. The NTFS backend is private
to inventory and its source remains byte-identical to the prior candidate.
Inspector 0.3.0 delegates file inspection to that path dependency; duplicate
identity/codec/NTFS files are removed from the inspector. Application profile
checks, observation envelopes and test pause hooks stay in the adapter.

The nominal identity types and explicit declaration constructors remain.
The restricted encoder now rejects unsupported Values at its own boundary;
all supported canonical bytes stay the same. Historical domain and SOF JSON
are never parsed/re-emitted through this codec. Independent Python inspection
references are retained, not replaced with calls into Rust.

## Regression Results

| Control | Result |
| --- | --- |
| Solana matrix | 43 cases, 54 paired old/new observations, same mechanical outcomes and failure class/code. |
| MaleCNS matrix | 27 cases, 35 paired old/new observations, same mechanical outcomes and failure class/code. |
| Matching canonical bytes | All 19 matching observation pairs have identical entries, manifest bytes/digests, bindings digests, byte passes and backend. |
| Actual fault controls | Nine named process kills and eight changed-window controls retain refusal/incomplete semantics. |
| Domain-invalid controls | Both accurately hashed invalid payloads still match A0 and are rejected by their unchanged application checks. |
| Rust core | Three unit tests, including exact codec vectors/unsupported-output refusal, and two nominal-identity compile-fail doctests pass. |
| Python controls | Existing 12 Solana and 11 MaleCNS test methods pass in ordinary and -O modes; three review-comparator/boundary tests pass. |

Comparisons intentionally do not equate new observer identities, PID, timing,
local paths or filesystem-instance IDs. Those are new attempt observations,
not fields to strip out of a historical identity. The comparator rejects changed
manifest bytes, missing cases and changed failure classifications.

The original acceptance programs retain their no-auto-extraction/no-permission
fields: their own PASS still grants no cache use, source approval or extraction
authority. The separately authorized extraction experiment is assessed here,
not retroactively authorized by either old shadow receipt.

## SOF Compatibility Gate

Both source-bound runs pass the same 131 unit/conformance/golden/regression
tests with zero skips. The exact membership, lengths and hashes of 304 protected
files are unchanged, including the Python SOF implementation, vendored contracts,
profiles, service/reference artifacts, packaging declaration and test closure.
The standalone installed-wheel check also passes. Vendored digest verification
still checks 25 files, and the service implementation closure remains
`e28268f199dff38b7b5d4a41d7b855b0f564425c418638f39c498d9eb00f1448`.
Existing MCP evaluation and matrix checks pass without rewriting their records.

Two failed baseline attempts are deliberately retained. The first imported a
different editable checkout and failed the service-start test. Explicit source
binding fixed that item, but exposed the temporary venv's same-version pip
installation refusal, leaving no sof.exe. The review-only launch profile now
pins PYTHONPATH and forces actual wheel installation inside that test venv.
The independent wheel test removes PYTHONPATH before CLI execution. The final
before and after suites use this identical profile and both pass. No protected
runtime/test code, expected artifact, skip policy or old receipt was changed
to resolve those environmental failures.

## Identity and Evidence

Prior 0.1.0 and 0.2.0 source/executable snapshots and receipts retain their
original hashes. All original Solana producers/checkpoints and MaleCNS source,
cache packet, outputs and receipts remain unchanged. The new inspector SHA-256
is `f7e2154160a521732243b1f1790ce93e5adda2562fbd4b5b4724de4c10c9eb0e`.
It is not substituted for either original producer identity.

Full local result:
`runs/shared-a0-extraction-v0/acceptance-final/review.v0.json`, SHA-256
`4c1315b7515c1b65680da8975025da9378e80f112111d31fca7914e994407cbc`.
It binds 2,144 local evidence objects and the separately hashed before capture.
The [selected summary](results/review-summary.v0.json) is an entry point, not a
self-contained public replay package. Saved verification rechecks source and
protected-byte bindings, both shadow closures and old/new comparisons; it does
not reexecute Rust, the SOF suite or independently attest past kill events.

## Disposition

Keep this as an internal shared A0 experiment used only by read-only shadows.
No production SOF/Solana/cache path, installed facade, contract or registry has
been switched. There is no common lock, process executor, publication lifecycle,
retry admission, quarantine or checkpoint inheritance. No application PASS,
authentication, immutable snapshot credential, power-loss, performance or
all-interleavings guarantee is added. Broader migration or B/C still requires
its own scope, contract and acceptance evidence.
