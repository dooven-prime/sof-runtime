I have completed the full workflow. The final artifact and receipt were retrieved successfully by locator plus SHA-256, and the explanation confirms the full pipeline provenance. Let me compile the complete report.

---

# SOF Runtime Evaluation Report — `deepseek-a`

## Workspace
`mcp-matrix-deepseek-a-20260813`

## Discovered Workflow (full pipeline, strongest admitted)
`realize → report → validate(sofrs, sofrs_receipt) → compare → validate(sofaudit, sofaudit_receipt) → interpret → validate(sofaction, sofaction_receipt) → retrieve → explain`

Both realizations were **canonical_compilable**, so the full pipeline was eligible (not extension-only). All stages succeeded.

---

## Ordered Artifact Chain & Semantic Run IDs

### Stage 1 — Realize (reference)
- **source_id**: `finite-state.transition.reference`
- **eligibility**: `canonical_compilable` (canonical_compilable=true)
- **semantic_run_id**: `semrun:sha256:33a4c1e9469d76b5a1c699a85347c11d117921a9b452822a605d623ee54d7350`
- **run dir**: `matrix/deepseek-a/reference/run`
- Artifacts: realization_candidate `3559dd19…`, adapter_declaration `7284ed39…`, source_inspection `2e2f51bb…`, realization_evidence `383b067c…`, realization_receipt `412615a5…`

### Stage 2 — Realize (target)
- **source_id**: `finite-state.transition.target`
- **eligibility**: `canonical_compilable` (canonical_compilable=true)
- **semantic_run_id**: `semrun:sha256:ca93b4f28c981b90c383f55928fb0a3cf0db4e1c6273fdfc5c2d6532da38ce20`
- **run dir**: `matrix/deepseek-a/target/run`
- Artifacts: realization_candidate `c120c334…`, adapter_declaration `7284ed39…`, source_inspection `2e2f51bb…`, realization_evidence `383b067c…`, realization_receipt `721556b5…`

### Stage 3 — Report (reference)
- **report_id**: `example.finite-state-adapter.finite-state.transition.reference.sofreport`
- **semantic_run_id**: `semrun:sha256:06866cb0d7e13067476887e68266bfc548a9df65a648c8099e45b7c3ada4ec66`
- **report locator**: `matrix/deepseek-a/reference/report/report/result.sofreport.json`
- **report digest**: `a1385b3ed6c431a250d5d073f4789937fc574b6b08428ea97274451e3b0b98e5`
- **receipt locator**: `matrix/deepseek-a/reference/report/report/validation-receipt.json`
- **receipt digest**: `d212154d76719aa99e4ae0c7644e666dc277652d07bb9e01af03193f17181597`

### Stage 4 — Report (target)
- **report_id**: `example.finite-state-adapter.finite-state.transition.target.sofreport`
- **semantic_run_id**: `semrun:sha256:168d82c12d49f39faed1fd262d342c438eceb31e3392fb9fe538cb3f007ec80a`
- **report locator**: `matrix/deepseek-a/target/report/report/result.sofreport.json`
- **report digest**: `cbe82171fd431ab06523904cb6bfcfc9b8c1bf354c9b84f41c55ba7fee0460b0`
- **receipt locator**: `matrix/deepseek-a/target/report/report/validation-receipt.json`
- **receipt digest**: `e31f0791bde41bfccd0c179a7120b8fd2abbc7c99c9b588f55fc98a838695128`

### Stage 5 — Validate (reference report + receipt)
- sofrs validation: **PASS** — `semrun:sha256:930105cc7b68a0f8a926c0e5482f6884f59774519a5d24111dced056f9050483`
- sofrs_receipt validation: **PASS** — `semrun:sha256:59da3d200920acf8b0e1a5a7930ac5b62a3354729219012ad0d09f33c1b08752`
- Receipt: `receipt.example.finite-state-adapter.finite-state.transition.reference.sofreport.sofrs-v2`

### Stage 6 — Validate (target report + receipt)
- sofrs validation: **PASS** — `semrun:sha256:f6b482f8ce01a8f264c1656351b23a142af25d217272ada13537aece3e92ba1e`
- sofrs_receipt validation: **PASS** — `semrun:sha256:48439775b69cd2de3b297dfde463db3df5201448991b92f0e2bcadf71cd366e2`
- Receipt: `receipt.example.finite-state-adapter.finite-state.transition.target.sofreport.sofrs-v2`

### Stage 7 — Compare
- **audit_id**: `comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport`
- **semantic_run_id**: `semrun:sha256:9062f244c392ccd5e2ab5737854105bb3d912743365139904d2f5e6a8b2ceedb`
- **audit locator**: `matrix/deepseek-a/comparison/result.sofaudit.json`
- **audit digest**: `4d3eb110bd9d4d711709e706ad5a88424360cad4ed75a55916fe3a7dcdbb7478`
- **receipt locator**: `matrix/deepseek-a/comparison/validation-receipt.json`
- **receipt digest**: `53191fff8453c743c904e260f04e9933e7b02e4ec67238e7ad73d3ac6b21d5f7`
- Alignment used: `case/comparison/alignment.json` (identity bijection on observable `advance` and sectors `idle/busy/done`, TOTAL)
- Comparison profile: `comparison-profile.json` (`sof-runtime.external-adapter.identity.v2`)

### Stage 8 — Validate (audit + receipt)
- sofaudit validation: **PASS** — `semrun:sha256:e931186b802f648717d367a27d77b5fb471bf835e17e68db546d7db3c59cfec5`
- sofaudit_receipt validation: **PASS** — `semrun:sha256:41e62483ffd536821f22b50b68cb0185ee41f356d338055f6909f5d740e4148c`
- Receipt: `receipt.comparison…sofaudit-v2`

### Stage 9 — Interpret
- **action_record_id**: `action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport`
- **semantic_run_id**: `semrun:sha256:6ae0cd406c7d4f009a42f018c08752775bc826958ec0455fc17d3b3661b3e9df`
- **action locator**: `matrix/deepseek-a/interpretation/result.sofaction.json`
- **action digest**: `592dc0d1651a4229c47ae421c3f20c95c8d91e6fccdeadb80eba9fb6a8f56d99`
- **receipt locator**: `matrix/deepseek-a/interpretation/validation-receipt.json`
- **receipt digest**: `30a41df2c98fd082cf9bc5a732e0eb46d51401f14ec71bf79624ae79283d83b8`
- Context: `case/action/context.json` (`finite-state-review-context-v1`, contract_status=nonconforming, admitted)
- Policy: `case/action/policy.json` (`finite-state-review-policy`, admitted)

### Stage 10 — Validate (action + receipt)
- sofaction validation: **PASS** — `semrun:sha256:b67df2e44747c754b8fa3bdf0fb0134381040c838ec50ca2c345d7cda9605faf`
- sofaction_receipt validation: **PASS** — `semrun:sha256:1019027228a02105d64b95c40e37c6b405c4b1afd9be009b6d696a639823569a`
- Receipt: `receipt.action.comparison…sofaction-v2`

### Stage 11 — Retrieve (final artifact + receipt)
- **SOFAction retrieved** by locator `matrix/deepseek-a/interpretation/result.sofaction.json` + sha256 `592dc0d1…` — **digest matched**
- **SOFAction receipt retrieved** by locator `matrix/deepseek-a/interpretation/validation-receipt.json` + sha256 `30a41df2…` — **digest matched**

### Stage 12 — Explain
- **semantic_run_id**: `semrun:sha256:96647d6937d3883fb313f7701ceaf01d66c5226e30bcc3c581f0a0c21d4ecfe6`
- **workflow**: `full_pipeline`; run_id = action_record_id

---

## Strongest Justified Claim at Each Stage
- **Realize**: Both cases are `canonical_compilable` (eligible for full pipeline). Claim: certified thresholded direct support for the declared transition family (protocol conformance only).
- **Report**: SOFRS v2 reports assembled and validated (PASS) under `sof-runtime.strict-conformance` compiler and `sof-runtime.strict-conformance.assembly.v2`.
- **Compare**: Coordinate `operator.support.summary` = **MISMATCH** (reference support_count=2, target support_count=3, delta=1, absolute-difference). Claim CERTIFIED as comparison_audit under declared identity alignment.
- **Interpret**: Policy-relative interpretation produced a bounded candidate set (defect_candidate assessment, mismatch-review rule).

## Bounded Candidate Actions (not selected/authorized)
1. `investigate:operator.support.summary` — disposition **Investigate**
2. `requestevidence:operator.support.summary` — disposition **RequestEvidence**

Both have `authorization_state: not_requested`, `selection_status: downstream`, and are explicitly **not** execution commands, recommendations, or causal-effect claims.

---

## Unavailable / Unresolved States
- **Modules `associative` and `closure`**: UNAVAILABLE in both reports (missing route/word carriers, cutoff, saturation_audit) — degradation items emitted.
- **External basis**: `basis.object.level` (object-level-recomputation) and `basis.semantic.adequacy` (domain-semantic-adequacy) = **NOT_ASSESSED**; basis_status = PARTIAL.
- **Object-level oracle**: NOT_ASSESSED (no independent recomputation).
- **Reference authority**: DECLARED baseline only — not a truth oracle.
- **Action reversibility**: unknown; **post-action outcomes**: require a new Paper XIII audit.

## Explicit Negative Boundaries (preserved)
- Comparison does not establish reference truth, defect status, severity, or action.
- A mismatch is not a certified defect; candidate actions are not execution commands/authorization/feasibility/causal-effect claims.
- Protocol conformance does not establish domain adequacy; runtime is not the domain authority.
- Identity alignment does not establish cross-domain semantic equivalence.
- Validation PASS certifies declared contract closure only, not scientific truth.
- No action was selected, recommended, authorized, or executed; no outcome or causal effect is claimed.
