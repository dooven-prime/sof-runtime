I have now completed the full workflow. All artifacts and receipts have been retrieved by locator plus SHA-256, and the provenance has been explained. Let me compile the complete report.

The full pipeline is complete: realize → report → validate → compare → validate → interpret → validate, with all artifacts retrieved and provenance explained. Let me present the comprehensive findings.

---

# SOF Runtime Evaluation Report — `mcp-matrix-deepseek-c-20260813`

## 1. Discovered Workflow

The strongest admitted workflow was the **full pipeline** (`workflow: full_pipeline`), executed end-to-end:

```
realize (reference + target)
  → report (reference + target)
  → validate (sofrs + sofrs_receipt for both)
  → compare (reference vs target)
  → validate (sofaudit + sofaudit_receipt)
  → interpret (audit + context + policy)
  → validate (sofaction + sofaction_receipt)
  → retrieve final artifact/receipt by locator + SHA-256
  → explain provenance
```

Both realizations were **canonical_compilable** (not extension-only), so reporting was eligible and the full chain was admitted.

## 2. Ordered Artifact Chain & Semantic Run IDs

| Stage | Artifact | Semantic Run ID |
|-------|----------|-----------------|
| Realize (reference) | `finite-state.transition.reference` | `semrun:sha256:33a4c1e9...d7350` |
| Realize (target) | `finite-state.transition.target` | `semrun:sha256:ca93b4f2...ce20` |
| Report (reference) | `...reference.sofreport` | `semrun:sha256:06866cb0...ec66` |
| Report (target) | `...target.sofreport` | `semrun:sha256:168d82c1...ec80a` |
| Validate ref report | sofrs | `semrun:sha256:930105cc...0483` |
| Validate ref receipt | sofrs_receipt | `semrun:sha256:59da3d20...b08752` |
| Validate tgt report | sofrs | `semrun:sha256:f6b482f8...2ba1e` |
| Validate tgt receipt | sofrs_receipt | `semrun:sha256:48439775...66e2` |
| Compare | SOFAUDIT | `semrun:sha256:9062f244...ceedb` |
| Validate audit | sofaudit | `semrun:sha256:e931186b...cfec5` |
| Validate audit receipt | sofaudit_receipt | `semrun:sha256:41e62483...4148c` |
| Interpret | SOFAction | `semrun:sha256:6ae0cd40...b3e9df` |
| Validate action | sofaction | `semrun:sha256:b67df2e4...05faf` |
| Validate action receipt | sofaction_receipt | `semrun:sha256:10190272...3569a` |
| Explain (interpretation) | — | `semrun:sha256:96647d69...4ecfe6` |

## 3. Artifact & Receipt Locators / Digests

**Reference report** — `matrix/deepseek-c/reference/report/report/result.sofreport.json`
- sha256: `a1385b3ed6c431a250d5d073f4789937fc574b6b08428ea97274451e3b0b98e5`
- report_id: `example.finite-state-adapter.finite-state.transition.reference.sofreport`

**Reference receipt** — `matrix/deepseek-c/reference/report/report/validation-receipt.json`
- sha256: `d212154d76719aa99e4ae0c7644e666dc277652d07bb9e01af03193f17181597`
- receipt_id: `receipt.example.finite-state-adapter.finite-state.transition.reference.sofreport.sofrs-v2`

**Target report** — `matrix/deepseek-c/target/report/report/result.sofreport.json`
- sha256: `cbe82171fd431ab06523904cb6bfcfc9b8c1bf354c9b84f41c55ba7fee0460b0`
- report_id: `example.finite-state-adapter.finite-state.transition.target.sofreport`

**Target receipt** — `matrix/deepseek-c/target/report/report/validation-receipt.json`
- sha256: `e31f0791bde41bfccd0c179a7120b8fd2abbc7c99c9b588f55fc98a838695128`
- receipt_id: `receipt.example.finite-state-adapter.finite-state.transition.target.sofreport.sofrs-v2`

**SOFAUDIT** — `matrix/deepseek-c/comparison/result.sofaudit.json`
- sha256: `4d3eb110bd9d4d711709e706ad5a88424360cad4ed75a55916fe3a7dcdbb7478`
- audit_id: `comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport`

**SOFAUDIT receipt** — `matrix/deepseek-c/comparison/validation-receipt.json`
- sha256: `53191fff8453c743c904e260f04e9933e7b02e4ec67238e7ad73d3ac6b21d5f7`
- receipt_id: `receipt.comparison...sofaudit-v2`

**SOFAction (final artifact)** — `matrix/deepseek-c/interpretation/result.sofaction.json`
- sha256: `592dc0d1651a4229c47ae421c3f20c95c8d91e6fccdeadb80eba9fb6a8f56d99`
- action_record_id: `action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport`

**SOFAction receipt (final receipt)** — `matrix/deepseek-c/interpretation/validation-receipt.json`
- sha256: `30a41df2c98fd082cf9bc5a732e0eb46d51401f14ec71bf79624ae79283d83b8`
- receipt_id: `receipt.action.comparison...sofaction-v2`

All retrievals succeeded with matching digests (no mismatch rejected).

## 4. Strongest Justified Claim at Each Stage

- **Realize:** Both cases `canonical_compilable: true`, eligibility `canonical_compilable`. Claim: the external adapter's declared transition family has **certified thresholded direct support** (Computational Certificate, protocol_conformance).
- **Report:** Both SOFRS v2 reports assembled and validated **PASS** (all 8 checks each: schema-validation, artifact-closure, claim-compatibility, claim-external-basis-binding, compiler-output-recompilation, cutoff-provenance, record-kind-boundary, report-assembly-recomputation).
- **Compare:** SOFAUDIT validated **PASS** (8 checks). Coordinate `operator.support.summary` = **MISMATCH** (reference support_count=2, target support_count=3, delta=1, absolute-difference). Alignment is **TOTAL** identity bijection on observable (`advance`) and sector (`idle`,`busy`,`done`) labels. Regime `strict_vs_strict`. Claim: "The selected direct-support coordinate was recomputed under declared identity alignment" (Computational Certificate, comparison_audit).
- **Interpret:** SOFAction validated **PASS** (8 checks). Context and policy both **admitted** (applicable, complete). Claim: policy-relative interpretation producing a bounded candidate set (Computational Certificate, decision_trace_certificate).

## 5. Bounded Candidate Actions

From the interpretation (policy rule `mismatch-review`, triggered by MISMATCH state):
1. **`investigate:operator.support.summary`** — disposition **Investigate**
2. **`requestevidence:operator.support.summary`** — disposition **RequestEvidence**

Both have `authorization_state: not_requested`, `reversibility: unknown`, and are explicitly **candidate dispositions, not execution commands or correctness claims**. No action was selected, recommended, authorized, or executed.

## 6. Unavailable / Unresolved States

- **Associative module** — UNAVAILABLE (no route/word carriers, no cutoff run policy) in both reports.
- **Closure module** — UNAVAILABLE (no closure carriers, no saturation_audit) in both reports.
- **External basis** — `basis.object.level` (object-level-recomputation) and `basis.semantic.adequacy` (domain-semantic-adequacy) = **NOT_ASSESSED** in both reports; basis_status **PARTIAL**.
- **Object-level oracle** in comparison = **NOT_ASSESSED** (no independent recomputation).
- **Interpretation uncertainty** — status **bounded** (no unresolved reasons).
- **Reference authority** — `DECLARED` baseline only, not a truth oracle.

## 7. Explicit Negative Boundaries

- **Realization:** "Realization validation does not establish adapter scientific adequacy." Unsupported capabilities (route filtration, positive-word depth, Lie/Hall depth, deformation chart) are not inferred.
- **Report:** "This receipt validates faithful SOFRS assembly... it does not establish adapter scientific adequacy, cross-report alignment, or downstream interpretation." Claim does not establish route, word, Lie/Hall, causal, or domain-adequacy conclusions.
- **Compare:** "This comparison does not establish reference truth, defect status, severity, or action." "A mismatch is not by itself a defect or action." Identity alignment does not establish cross-domain semantic equivalence. "The selected reference is not thereby a truth oracle."
- **Interpret:** "difference is not defect, severity, or action without the admitted context and policy"; "candidate actions are not execution commands, authorization, feasibility, or causal-effect claims"; "post-action facts require a new Paper XIII audit." Context `contract_status: nonconforming`; constraint `human-review-required` binding ("No candidate is an execution command and no action is authorized by this context").
- **General:** "Validation PASS establishes the declared contract and artifact closure only." "CandidateAction is not a recommendation, authorization, execution command, or causal-effect certificate." "Protocol conformance does not establish domain adequacy."

## 8. Final Provenance (explain)

The `explain` on the interpretation run directory confirmed `workflow: full_pipeline`, tracing both realizations (reference source digest `3d6e6716...`, target source digest `a4a46d47...`), both validated reports, the validated SOFAUDIT (MISMATCH on `operator.support.summary`), and the validated SOFAction with its two bounded candidates. The comparison run directory explanation confirmed `workflow: comparison` with `interpretation: null` (no interpretation at that stage). All stages were discovered from the artifact/receipt graph, not directory names.

**Conclusion:** The strongest admitted workflow (full pipeline) completed successfully with all artifacts validated PASS and retrieved by locator + SHA-256. The final justified outcome is a **bounded candidate set** of two non-authorized dispositions (Investigate, RequestEvidence) for the MISMATCH on `operator.support.summary` — with no action selected, authorized, or executed, and all scientific-truth, defect, severity, and causal-effect claims explicitly excluded.
