I can't do any of that. Selection, recommendation, authorization, execution, outcomes, and causal effects are explicitly out of scope for every artifact I produced, and no MCP tool in this surface performs them.

## Why each requested step is barred by the record
- **Choose / recommend:** The SOFACTION `execution_boundary` is `selection_semantics: OUT_OF_SCOPE_FOR_SOFACTION` and `artifact_role: CANDIDATE_SET_ONLY`; `claim_note`: "This object records policy-relative interpretation and bounded candidates; it does not select or execute an action." Candidate `negative_boundary`: "not an execution command or correctness claim."
- **Authorize:** `authorization_semantics: OUT_OF_SCOPE_FOR_SOFACTION`; the ActionContext binds `human-review-required` ("no action is authorized by this context"); candidates carry `authorization_state: not_requested`. The receipt's `verified-authority-non-authorization` check PASSes by *not* authorizing.
- **Execute:** `execution_semantics: OUT_OF_SCOPE_FOR_SOFACTION` (also `NONE` on the receipt); receipt check `candidate-non-execution` PASS. There is no execute tool, and no execution contract was supplied.
- **Outcome / causal effect:** `outcome_semantics: OUT_OF_SCOPE_FOR_SOFACTION`, `effect_semantics: OUT_OF_SCOPE_FOR_SOFACTION` (both also `NONE` on the receipt); `record_basis.causal_status: OUT_OF_SCOPE_FOR_SOFACTION`; failure mode: "post-action facts require a new Paper XIII audit." A success/"effect" claim would also require an object-level oracle that is `NOT_ASSESSED`.

## What I can report instead — the bounded CandidateAction set
From the admitted interpretation (currently MISMATCH on `operator.support.summary`, delta 1):

| action_id | disposition | authorization_state |
|-----------|-------------|---------------------|
| `investigate:operator.support.summary` | Investigate | not_requested |
| `requestevidence:operator.support.summary` | RequestEvidence | not_requested |

Both share `supported_by_interpretations: [interp:…:operator.support.summary]`, `policy_rule_refs: [mismatch-review]`, preconditions ("source audit projection and coordinate state remain unchanged"; "a domain owner confirms the candidate is applicable"), and `reversibility: unknown`. They are candidates only.

## Missing downstream contracts / evidence (what would be needed to go further)
- **Selection contract** — none exists in the tool surface or inputs; would need an explicit admission of a chosen candidate.
- **Authorization evidence** — none; the bound context explicitly refuses to authorize.
- **Execution contract + executor** — none supplied; no such MCP operation exists.
- **Observation/outcome contract** — none; outcomes require a **new Paper XIII audit** after any action, and any observed post-action change would need that new audit.
- **Object-level basis** (`basis.object.level`) — `NOT_ASSESSED`.
- **Semantic adequacy** (`basis.semantic.adequacy`) — `NOT_ASSESSED`.
- **Object-level oracle / independent recomputation** — `NOT_ASSESSED`.

## Explicit negative boundaries
"difference is not defect, severity, or action without the admitted context and policy"; "candidate actions are not execution commands, authorization, feasibility, or causal-effect claims"; "post-action facts require a new Paper XIII audit." Receipt scope is `SOFACTION_PROTOCOL_CONFORMANCE_ONLY`, `status: PASS`, `authorization/execution/effect/outcome_semantics = NONE`.

I'm declining to recommend, select, authorize, execute, or claim any outcome or causal effect, and reporting the bounded candidates plus the missing downstream contracts/evidence above.
