# Source Advancement v0: Local Readout

Status: **PASS_LOCAL_SOURCE_ADVANCEMENT_CONTROLS**. The saved comparisons
were rechecked as `VERIFIED_LOCAL_SAVED_SOURCE_TRANSITIONS`. This is offline
compatibility validation, not live source admission or reorg handling.

## Scope

The unchanged 64-slot real capture supplies payloads for explicitly derived
16/32/64-slot windows. New RPC envelopes, local source credentials and policy
rows are synthetic fixtures, clearly marked as such. They do not represent
fresh retrievals or two independently authenticated providers. No network
access occurs. The original capture and all older selected closures remain
unchanged.

The policy pins exact credential/admission hashes and permits declared
reapproval pairs. Equality of canonical bytes does not bypass that permission.
Three identities are kept separate: credential-relative source identity;
program/projection/policy execution identity; exact checkpoint-frame identity.

## Twenty Saved Scenarios

| Scenario group | Result |
|---|---|
| Initialize 16, append to 32, append to 64, fresh full 64 | Four successes; continuous and full projection byte-identical |
| Changed credential without reapproval | UNRESOLVED; no publication |
| Changed credential with permitted explicit reapproval | Success after all 64 prefix blocks are reprojected |
| Same credential, changed unprojected raw metadata, without reapproval | UNRESOLVED; equal output is insufficient |
| Same raw revision with permitted reapproval | Success; source unchanged, checkpoint rebound |
| Two changed transaction reports in committed prefix | Refused at earliest differing slot 378967392 |
| Listed/unlisted status divergence | Refused at slot 378967388 |
| Missing admission/payload, broken continuity, smaller range, unknown credential | Five UNRESOLVED results |
| Bad parent/policy anchor, corrupt parent segment, foreign execution, existing destination | Five UNRESOLVED results |

Totals: **6 successes, 2 prefix-conflict refusals, 12 UNRESOLVED**. The overall
control PASS means these outcomes matched their independent Python decisions,
not that every proposed transition was admitted.

Each refusal left the old state byte-for-byte unchanged, published no new
checkpoint directory or success receipt, and left no ordinary validation-error
staging directory. Existing destinations were retained. A continuity failure
in a late suffix was checked after staging earlier new slots: the private
stage was discarded rather than partially publishing them.

The transaction-report mutations retain the reported blockhash while changing
a projected fee. They are deliberately contradictory source reports, not
validated alternative Solana blocks or evidence of a fork. The result rejects
their reuse without making a consensus or reorg claim.

## Exact Prefix/Suffix Work

| Operation | Inherited slots | Candidate prefix blocks decoded | Candidate suffix blocks decoded |
|---|---:|---:|---:|
| Initialize 16 | 0 | 0 | 16 |
| Append to 32 | 16 | 0 | 16 |
| Append to 64 | 32 | 0 | 32 |
| Fresh full 64 | 0 | 0 | 64 |
| Credential reapproval, same complete data | 64 | 64 | 0 |
| Raw-evidence revision reapproval | 64 | 64 | 0 |

Old captured blocks are never reprojected by the Rust inheritance path, but
their evidence/segment hashes remain checked. Candidate prefix reprojection
is intentionally required by reapproval. The Python model reconstructs full
records independently for decision and output comparisons. This is work
accounting, not a performance benchmark.

Continuous advancement, full replay and both equal-record reapprovals produce
the same 1,994,158-byte canonical projection:

```text
a8053b902e3824651851bd612b741d4358ae5112ff8397ca3ea2cde6770d1f92
```

Source and execution identities remain stable across ordinary append, while
each checkpoint changes. Credential reapproval changes source identity but
not execution identity. Raw metadata reapproval can preserve both source and
execution identities while changing checkpoint identity. Continuous and fresh
full runs also have different checkpoints despite identical output, because
parent history and transition binding differ.

## Checks and Evidence

Eight focused test methods passed under ordinary and optimized Python,
including forbidden credential-pair reapproval despite equal data, strict
cursor handling, and destination alias rejection before even a lock file can
enter an old state/capture. Two inherited Rust parser tests also passed; they
are not new source-trust proofs. Peak working-set observations are retained
for diagnostics only; this result makes no throughput or memory-bound claim.

The selected compact [receipt](results/acceptance.v0.json) binds 20 actual
Rust process outcomes, separate Python decisions/full reference outputs and
1,972 saved files. The complete local run is
`runs/solana-source-advancement/acceptance-v0-final/`.
An earlier `acceptance-v0/` development run is retained but is not selected;
the final run includes the strengthened output-path guard.

The verifier rechecked code/data identities, request/result log binding,
all case decisions, successful checkpoint/transition fields and complete
canonical outputs. It did not reexecute the worker or independently attest
execution. The compact receipt is not a self-contained public capture package.

## Boundary

The old checkpoint remains historically valid for its old capture. A conflict
only blocks its inheritance into the proposed source/capture. There is no
automatic rollback, correction application, active checkpoint pointer,
provider-credibility equivalence, signature/consensus/finality verification
or live reorg capability. New policy/code identities and interrupted advancement
publication require separate migration/recovery rules. Those boundaries are
unchanged by this local PASS.
