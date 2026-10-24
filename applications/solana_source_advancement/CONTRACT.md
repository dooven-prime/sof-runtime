# Source Advancement and Checkpoint Invalidation v0

Single-machine, fixed-capture, offline compatibility experiment. It does not
change v0/v1 replay or SOF contracts, add transaction versions, qualify RPC
providers, choose a chain tip, implement reorg/rollback, or verify consensus.

## Three Identities

- Source identity hashes a typed credential binding locator, genesis,
  evidence class, revision and scope. It is stable across captured windows
  admitted under that exact credential. A new credential is a new identity,
  even when all projected records agree.
- Execution identity binds this implementation, projection law and fixed
  admission policy. It does not identify a source, window or checkpoint.
  Code/policy changes are not silently accepted as source advancement.
- Checkpoint identity hashes exact checkpoint-frame bytes, including source
  and execution identities, captured-input identity, ordered committed slots
  and parent checkpoint. Appending changes checkpoint identity; retaining a
  valid prefix does not mean reusing the old frame as the new checkpoint.

Local policy pins exact credential and capture-admission hashes. These are
explicit offline test permissions, not authentication of a live provider or
equivalence of different providers' credibility. No equality of output grants
an absent permission. The policy's digest is a required input.

## Prefix Inheritance

An initialization fully validates and projects its admitted capture. A later
request supplies the old capture, old state and externally bound checkpoint
hash from a prior successful execution of this same contract. Legacy v1 state
is not silently migrated. Every old source and segment byte is revalidated.

The candidate must begin at the same slot/anchor, cover every committed slot,
use the same genesis and projection/configuration, and provide a complete
admitted source evidence closure. Missing data, range/continuity uncertainty,
foreign execution identity, absent policy permission or invalid bytes yield
UNRESOLVED and no new published state.

With identical source identity and identical raw evidence for every committed
slot, append inherits verified prefix segments without decoding/projecting
their block responses. Only the new suffix is projected. Raw identity is not
inferred from mtime, length alone or projected-output equality.

Changed source identity or changed prefix raw evidence triggers full ascending
prefix reprojection. If all canonical records match, advancement still needs
the explicit `reapprove` request and an allowed credential-pair rule. This
creates a new binding to the candidate evidence; it does not trust the old
credential for the new source. A changed but unprojected metadata field also
needs reapproval; projection is not the entire source evidence.

The first differing committed canonical segment or explicit listed/unlisted
status yields REJECTED_PREFIX_CONFLICT, with the earliest conflicting slot,
conflict kind, old/candidate identities and affected checkpoint hash. Conflict
detection scans in increasing slot order. This invalidates inheritance for
the proposed candidate, not the historical checkpoint for its old capture.
No automatic correction, rollback or consensus/finality conclusion follows.

## Publication and Evidence

The old state is held under its writer lock and never rewritten. All candidate
suffixes and continuity checks must pass before publication. A new sibling
staging directory holds copied prefix segments and new suffix segments. Every
copied byte is checked, inputs and checkpoint are checked again, then the
complete new state is published to a previously absent destination. Failed
validation has no success receipt and cannot replace the old state. V0 has no
active-state pointer, crash-recovery protocol for this publication step,
cross-process hostile-storage guarantee, power-loss or external sink claim.

Each request is bound by its own SHA-256 and includes exact policy and optional
parent checkpoint anchors. Success retains a transition record and parent
identity. Refusals retain reason, compatibility disposition and the earliest
validated conflict where available; they are not successful replay receipts.

Offline controls derive multiple windows from the frozen 64-slot real capture,
alongside explicitly synthetic mutations. Their RPC envelopes and source
credentials are test fixtures, not additional real RPC captures or independent
provider evidence. The original real-capture bytes remain unchanged. A separate
Python full-projection model checks decisions and complete resulting states.
