# Source Transition Publication Recovery v0

## Scope and Authority

Single-host, fixed-capture, trusted-local-filesystem, process-crash recovery.
Reuse the unchanged source-advancement v0 policy, projection and three distinct
identities. This is an application-owned adapter, not a shared runtime core,
live-source contract, provider authentication, reorg, rollback, migration,
power-loss durability or external exactly-once delivery.

The new executable includes the unchanged v0 source. Its own executable hash
is the execution identity: old v0-binary checkpoints cannot silently migrate.
Every attempt, including retry of a published result, re-executes the source
validation/projection into private calculation storage. This deliberately
retains correctness checks and is NOT an incremental-computation optimization.
Its calculation work is additional to recoverable publication work.

## Transaction Identity and Persistent State

The CLI receives the existing exact request and an absolute output directory.
Before creating any lock or transaction file, reject output parents inside
the candidate capture, old capture or old state. Reserve one sibling lock and
one sibling control directory. Reject symlinks and foreign control inventory.

The immutable intent binds exact request bytes, executable, normalized output
path, policy and the complete input/parent file inventory and hashes. An empty
reserved control directory or a valid prefix of intent.pending can result from
death before intent publication; it can only be filled with the current exact
intent. Once published, intent must match, including on later retries. Changed
inputs, policy, executable, request or parent never inherit this transaction.
Intent is binding metadata, not a credential replacing source validation.

The control directory owns only intent(.pending), calculation scratch, stage,
ready(.pending) and receipt(.pending). Calculation scratch is disposable and
may be regenerated. Cleanup is confined to that owned subtree, bounded in
depth and refuses symlinks. It never deletes old state or source files.

## Publication State Machine

1. **INTENT:** exact intent published under an exclusive destination lock.
2. **CALCULATED:** unchanged v0 semantics produces a complete private model.
3. **STAGING:** final slot segments, aggregate, transition, checkpoint and empty
   writer lock are individually written/synced as pending, then renamed.
4. **READY:** every stage file matches the newly calculated full inventory;
   ready binds intent, inventory and source result. Recheck all inputs/parent.
5. **PUBLISHED:** rename the complete stage directory to the absent final path.
   This directory rename is the process-crash linearization point. An internal
   staged checkpoint is not a committed published source transition.
6. **RECEIPTED:** publish one deterministic success receipt after validating
   the final directory. If killed after rename, retry validates the full final
   inventory against fresh calculation and completes/returns the same receipt.

Keep the parent writer lock during final copying/checks/publication after v0
validation has released it; compare its entire inventory to the intent before
continuing. A reader must validate a complete final inventory/checkpoint, never
admit a hidden stage or partial receipt. No active-state pointer is updated.
The parent remains historically valid and byte-identical.

## Recovery and Refusal

A finalized staged/published file must exactly equal fresh expected bytes.
Only a registered .pending file equal to a prefix of the expected bytes may be
completed. Unknown files, inconsistent ready/receipt, corrupt final files,
foreign/incomplete final directories and mismatched intent produce UNRESOLVED
without overwriting the evidence. Existing final output without this operation's
intent/ready is not admitted. Valid complete output with lost stdout is an
idempotent retry, not a second transition. Refusal does not erase a previously
published directory; it means publication is not confirmed by this attempt.

File sync and same-parent rename are used, but no directory-fsync/power-loss
guarantee is made, especially on Windows. Storage or source changes between
checks and publication are outside an adversarial-filesystem guarantee; pre/
post identity checks and single-writer local locks remain mandatory.

## Acceptance

Use fixed real-capture-derived append and equal-record credential-reapproval
requests. Independently reconstruct every successful projection in Python.
Kill actual Rust processes at each declared boundary; fresh processes must
recover the exact uninterrupted state bytes and deterministic receipt. Preserve
parent and captures throughout. Test repeated interruption, lost response,
concurrent writer, changed inputs/intent, partial and corrupt publication,
unknown inventory and changed policy/request. None may yield false success.

Record logs, marker, exit code, before/after identities, complete inventories,
source/code/binary hashes and independent reference results. Ordinary and -O
Python controls must agree; the controller removes PYTHONOPTIMIZE. A saved
closure verifier rechecks files and Python semantics but does not attest that
the saved kill occurred or rerun workers. Full runs remain local; selected
compact receipts are not self-contained public evidence.
