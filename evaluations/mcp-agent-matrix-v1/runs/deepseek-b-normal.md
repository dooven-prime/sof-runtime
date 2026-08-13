The explanation confirms the full pipeline provenance. I now have all the information needed to report the complete workflow. Let me compile the final report.

The workflow is complete. Let me summarize the full evaluation.

---

# SOF Runtime Evaluation Report — `mcp-matrix-deepseek-b-20260813`

## Discovered Workflow (full_pipeline)

The strongest admitted workflow was executed end-to-end: **realize → report → compare → interpret**, with validation at each applicable stage, artifact/receipt retrieval by locator+SHA-256, and final provenance explanation.

## Ordered Artifact Chain & Semantic Run IDs

| Stage | Semantic Run ID | Artifact | Receipt |
|-------|----------------|----------|---------|
| **Realize (reference)** | `semrun:sha256:33a4c1e9469d76b5a1c699a85347c11d117921a9b452822a605d623ee54d7350` | `realization_candidate:3559dd19203b73a1` | `realization_receipt:412615a581371cda` |
| **Realize (target)** | `semrun:sha256:ca93b4f28c981b90c383f55928fb0a3cf0db4e1c6273fdfc5c2d6532da38ce20` | `realization_candidate:c120c334d96cf906` | `realization_receipt:721556b5be149dec` |
| **Report (reference)** | `semrun:sha256:06866cb0d7e13067476887e68266bfc548a9df65a648c8099e45b7c3ada4ec66` | `sofrs_report:a1385b3ed6c431a2` | `sofrs_validation_receipt:d212154d76719aa9` |
| **Report (target)** | `semrun:sha256:168d82c12d49f39faed1fd262d342c438eceb31e3392fb9fe538cb3f007ec80a` | `sofrs_report:cbe82171fd431ab0` | `sofrs_validation_receipt:e31f0791bde41bfc` |
| **Compare** | `semrun:sha256:9062f244c392ccd5e2ab5737854105bb3d912743365139904d2f5e6a8b2ceedb` | `sofaudit:4d3eb110bd9d4d71` | `sofaudit_validation_receipt:53191fff8453c743` |
| **Interpret** | `semrun:sha256:6ae0cd406c7d4f009a42f018c08752775bc826958ec0455fc17d3b3661b3e9df` | `sofaction:592dc0d1651a4229` | `sofaction_validation_receipt:30a41df2c98fd082` |

## Artifact & Receipt Locators/Digests

**Reference SOFRS report** — `matrix/deepseek-b/report/reference/report/result.sofreport.json`, sha256 `a1385b3ed6c431a250d5d073f4789937fc574b6b08428ea97274451e3b0b98e5`
**Reference SOFRS receipt** — `matrix/deepseek-b/report/reference/report/validation-receipt.json`, sha256 `d212154d76719aa99e4ae0c7644e666dc277652d07bb9e01af03193f17181597`

**Target SOFRS report** — `matrix/deepseek-b/report/target/report/result.sofreport.json`, sha256 `cbe82171fd431ab06523904cb6bfcfc9b8c1bf354c9b84f41c55ba7fee0460b0`
**Target SOFRS receipt** — `matrix/deepseek-b/report/target/report/validation-receipt.json`, sha256 `e31f0791bde41bfccd0c179a7120b8fd2abbc7c99c9b588f55fc98a838695128`

**SOFAUDIT** — `matrix/deepseek-b/audit/result.sofaudit.json`, sha256 `4d3eb110bd9d4d711709e706ad5a88424360cad4ed75a55916fe3a7dcdbb7478`
**SOFAUDIT receipt** — `matrix/deepseek-b/audit/validation-receipt.json`, sha256 `53191fff8453c743c904e260f04e9933e7b02e4ec67238e7ad73d3ac6b21d5f7`

**SOFAction** — `matrix/deepseek-b/interpret/result.sofaction.json`, sha256 `592dc0d1651a4229c47ae421c3f20c95c8d91e6fccdeadb80eba9fb6a8f56d99`
**SOFAction receipt** — `matrix/deepseek-b/interpret/validation-receipt.json`, sha256 `30a41df2c98fd082cf9bc5a732e0eb46d51401f14ec71bf79624ae79283d83b8`

All retrievals succeeded with matching digests (digest mismatch rejected otherwise).

## Strongest Justified Claim at Each Stage

- **Realize**: Both cases `canonical_compilable: true`, eligibility `canonical_compilable` (source_ids `finite-state.transition.reference` / `finite-state.transition.target`). This permits entry into Manifest/Typed IR/CompilerOutput/SOFRS assembly.
- **Report**: Both SOFRS v2 reports validated PASS. Each certifies `claim.direct-support` (protocol_conformance, Computational Certificate, CERTIFIED). Reference support pairs `[busy→done, idle→busy]` (count 2); target `[busy→done, done→idle, idle→busy]` (count 3). Modules `associative` and `closure` are **UNAVAILABLE** (degradation items emitted). External basis **PARTIAL**: source.identity & structure.level SATISFIED; object.level & semantic.adequacy NOT_ASSESSED.
- **Compare**: SOFAUDIT validated PASS. Coordinate `operator.support.summary` = **MISMATCH** (delta 1; reference 2 vs target 3 support pairs), under declared identity alignment (TOTAL, bijection). Claim CERTIFIED as comparison_audit. Object-level oracle NOT_ASSESSED; reference is DECLARED baseline only (not a truth oracle).
- **Interpret**: SOFAction validated PASS. Context admitted (contract_status `nonconforming`), policy admitted. Produced a bounded candidate set of 2.

## Bounded Candidates (no selection/authorization)

1. `investigate:operator.support.summary` — disposition **Investigate**
2. `requestevidence:operator.support.summary` — disposition **RequestEvidence**

Both `authorization_state: not_requested`, supported by interpretation `interp:...:operator.support.summary`, policy rule `mismatch-review`. No action was selected, recommended, or executed.

## Unavailable / Unresolved States

- Modules `associative` and `closure` **UNAVAILABLE** in both reports (missing carriers route/word/closure, missing cutoff/saturation_audit policies).
- External basis `basis.object.level` and `basis.semantic.adequacy` **NOT_ASSESSED** in both reports.
- Object-level oracle in the audit **NOT_ASSESSED** (no independent recomputation).
- Reference authority is **DECLARED** baseline only — not a truth oracle.
- Context `contract_status: nonconforming` (admitted for interpretation).

## Explicit Negative Boundaries

- Protocol conformance does **not** establish domain adequacy, route/word/Lie-Hall/causal conclusions, reference truth, defect status, severity, or action.
- A mismatch is a policy-relative review status, **not** a certified defect.
- Candidate actions are **not** execution commands, authorization, feasibility, or causal-effect claims.
- Identity alignment does **not** establish cross-domain semantic equivalence.
- Post-action outcomes would require a **new Paper XIII audit**.
- Validation PASS certifies the declared contract/artifact closure only; it does not upgrade scientific claims.

The workflow completed successfully through the strongest admitted path (full pipeline), with all applicable artifacts validated and the final SOFAction artifact and receipt retrieved by locator plus SHA-256.
