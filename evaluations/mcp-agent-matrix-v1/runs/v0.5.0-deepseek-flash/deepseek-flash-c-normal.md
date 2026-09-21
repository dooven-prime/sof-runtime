Workflow complete through all admitted stages. Below is the full report.

## Discovered workflow

The MCP surface exposes six operations whose frozen contracts (`service-request.schema.json` `sha256:875c53bb…`, `service-response.schema.json` `sha256:f21a15b5…`, `service-error.schema.json` `sha256:28d876cd…`, `job.schema.json` `sha256:a4ab8f87…`) define a strict pipeline: `realize → report → compare → interpret`, with `validate` and `explain` as supporting operations. I executed the **strongest admitted workflow** the declared inputs allow (`workflow: full_pipeline`): two realizations → two reports → one comparison → one interpretation, validating each artifact and its receipt.

## Ordered artifact chain (workspace `mcp-matrix-deepseek-flash-c-20260921`)

| # | Stage | Operation | Locator (workspace-relative / URI) | SHA-256 | Semantic run ID |
|---|-------|-----------|-----------------------------------|---------|-----------------|
| 1 | Realize (reference) | `realize` | `matrix/deepseek-flash-c/reference/realization/…` (candidate.json) | `3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3` | `semrun:sha256:aeabaabcfedb406874f1af0020bc6b05961b341fd7d22eb6d29935c5ba73c837` |
| 2 | Realize (target) | `realize` | `matrix/deepseek-flash-c/target/realization/…` (candidate.json) | `c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907` | `semrun:sha256:9d843fc02d206aacbb3200da62984a326c4f821f22402980a219db8b030cb45b` |
| 3 | Report (reference) | `report` | `matrix/deepseek-flash-c/reference/report/report/result.sofreport.json` | `7ab8b7ae1ab9aadd239218b6bf3efc429a4f29b3e473d6eaa47ffb4ef2f06974` | `semrun:sha256:e2ad97ef753faa507d3107ad711af5ac6cc6feafdf1868c8adfd8cb3297ff683` |
| 3r | Report receipt (ref) | `report` | `matrix/deepseek-flash-c/reference/report/report/validation-receipt.json` | `410c8cfeae0cc8a5bebdd671a5e3dbc2138aff7b39fb75ed425e734bcf53a58d` | (report run) |
| 4 | Report (target) | `report` | `matrix/deepseek-flash-c/target/report/report/result.sofreport.json` | `8bdcb00bb9000d3ff5761030ae1e0cc74660abada49074406bb9632116e17223` | `semrun:sha256:f8cfea7cb126343fd4f6ec72fbd56428c4c136ef4863bfbf28b3d0a0a6ba031b` |
| 4r | Report receipt (tgt) | `report` | `matrix/deepseek-flash-c/target/report/report/validation-receipt.json` | `bf947922e3eaf6977bf7bd6f51a9d5b66e9e603a46acbbca2becdd1b1333f95f` | (report run) |
| 5 | Compare | `compare` | `matrix/deepseek-flash-c/comparison/result.sofaudit.json` | `5002028932d1ccd90630fb314253634f66faece795acff369b7adfb3dddd80a8` | `semrun:sha256:41ae5d3ffa2f69714ed47f6b6dd699abd9cf2254814b2a61ba11ed8b5e3f7c5f` |
| 5r | Audit receipt | `compare` | `matrix/deepseek-flash-c/comparison/validation-receipt.json` | `041ea6326f0d1c5eda15a61e3819bffc1f3cd4be2cc19daf6ce27291acf52440` | (compare run) |
| 6 | Interpret | `interpret` | `matrix/deepseek-flash-c/action/result.sofaction.json` | `1acc22bcd9053f9bbe74a0f0302f9fdd5d9c601605bb68993bd6d3d27e4fdee3` | `semrun:sha256:bbf3fdd6aefe255e76632baae3d01afdf2ef4b435205a0de994cd6a5b0e89695` |
| 6r | Action receipt | `interpret` | `matrix/deepseek-flash-c/action/validation-receipt.json` | `5b4c2913dc354e5267fa00a9552aa9f60d76bc79e09b9152836d6bfe5ad1e826` | (interpret run) |
| 7 | Explain | `explain` | `matrix/deepseek-flash-c/action` | — | `semrun:sha256:0eabd5a7fa44324bd92ed53e80e4d721c7dc04e6732ba07a22067971c0ea106b` |

Report IDs: reference `example.finite-state-adapter.finite-state.transition.reference.sofreport`; target `example.finite-state-adapter.finite-state.transition.target.sofreport`. Audit ID / action record ID: `comparison.…reference.sofreport.example.…target.sofreport` (full single-string IDs as returned).

Validation jobs I ran: reference `sofrs` `semrun:sha256:63149dbb…` and `sofrs_receipt` `semrun:sha256:109c13762…`; target `sofrs` `semrun:sha256:4ffb0b8b…` and `sofrs_receipt` `semrun:sha256:a04cff81…`; `sofaudit` `semrun:sha256:d725933e…` and `sofaudit_receipt` `semrun:sha256:f46db75a…`; `sofaction` `semrun:sha256:0fc16b71…` and `sofaction_receipt` `semrun:sha256:2c00a9717…`. All returned validators `status: PASS`.

## Canonical compilation eligibility (checked before reporting)

- Reference `source_id: finite-state.transition.reference` → `eligibility: canonical_compilable`, `canonical_compilable: true`
- Target `source_id: finite-state.transition.target` → `eligibility: canonical_compilable`, `canonical_compilable: true`

Both were eligible, so both legitimately advanced to report assembly. (Had either returned `extension_only`, the correct stop would have been at realization.)

## Strongest justified claim at each stage

- **Realization:** Both candidates are *canonical-compilable* under the frozen adapter contract. Claim limit: this is eligibility, not scientific adequacy.
- **Report (SOFRS v2.1, `strict_sof`):** Protocol conformance `PASS`. The one claim `claim.direct-support` is `CERTIFIED` as a *Computational Certificate* (`certificate_class: protocol_conformance`, `claim_target: representation_interface`): "the external adapter's declared transition family has certified thresholded direct support." Finding: `present: true`; threshold `absolute matrix entry > 1e-12`; reference support pairs `[busy→done, idle→busy]`, target support pairs `[busy→done, done→idle, idle→busy]`.
- **Compare (SOFAUDIT v2.1, regime `strict_vs_strict`, `basis_status: COMPLETE`):** Aligned comparison `CERTIFIED` for the single requested coordinate `operator.support.summary` under the declared identity alignment: comparison_state **`MISMATCH`**, reference `support_count = 2`, target `support_count = 3`, metric `absolute-difference` delta `1`. `matched_states: [ALIGNED, MISMATCH]`.
- **Interpret (SOFAction v2.1):** Policy-relative interpretation under the supplied profile (`finite-state-review-policy`, rule `mismatch-review`), producing a **bounded CandidateAction set** — not a decision.

## Unavailable / unresolved states (not coerced)

- Report `modules`: `sof-basic` ENABLED; **`associative` UNAVAILABLE** (no route/word carrier, no route/word/depth space, missing `cutoff` run policy); **`closure` UNAVAILABLE** (no closure carrier/space, missing `saturation_audit`). Six `degradation_items` (`omit_module` / `emit_unavailable`).
- `external_basis_registry.basis_status: PARTIAL`: `basis.source.identity` SATISFIED; `basis.structure.level` SATISFIED; **`basis.object.level` (object-level-recomputation) NOT_ASSESSED**; **`basis.semantic.adequacy` (domain-semantic-adequacy) NOT_ASSESSED** (empty evidence artifacts).
- Audit `object_level_oracle.status: NOT_ASSESSED` (no independent recomputation artifacts).
- `object_transition_boundary`: `implementation_purity_status: NOT_ESTABLISHED_BY_SOFRS`, `intervention_semantics: NONE`, `source_state_transition_authority: NONE`.
- **ActionContext `contract_status: "nonconforming"`** — recorded as the evaluated subject's declared status. Separately, `context_admission.status: "admitted"` (applicability `applicable`, completeness `complete`, `missing_fields: []`). These are two distinct fields; I report both and do not reconcile or upgrade them.

## Bounded candidates (not selected, not recommended, not authorized)

Both `authorization_state: "not_requested"`, both targeting `operator.support.summary`:
- `investigate:operator.support.summary` — disposition `Investigate`
- `requestevidence:operator.support.summary` — disposition `RequestEvidence`

## Final retrievals (locator + digest matched)

- Artifact `matrix/deepseek-flash-c/action/result.sofaction.json` @ `1acc22bcd9053f9bbe74a0f0302f9fdd5d9c601605bb68993bd6d3d27e4fdee3` — retrieved and digest-verified.
- Receipt `matrix/deepseek-flash-c/action/validation-receipt.json` @ `5b4c2913dc354e5267fa00a9552aa9f60d76bc79e09b9152836d6bfe5ad1e826` — retrieved and digest-verified (`receipt_scope: SOFACTION_PROTOCOL_CONFORMANCE_ONLY`, `status: PASS`, all 9 checks PASS).

## Explicit negative boundaries

- **Realization:** validation does not establish adapter scientific adequacy; only canonical-compilable realizations may enter Manifest/IR/CompilerOutput/SOFRS.
- **Report:** `claim.direct-support` does not establish route, word, Lie/Hall, causal, or domain-adequacy conclusions; the receipt establishes SOFRS protocol conformance only and neither induces nor authorizes a state transition nor establishes implementation purity.
- **Compare:** the comparison establishes neither reference truth, defect status, severity, nor action; the reference is `COMPARISON_ROLE_ONLY` / `NOT_A_CAUSAL_BASELINE`; causal and defect-attribution status are `OUT_OF_SCOPE_FOR_SOFAUDIT`; "a mismatch is not by itself a defect or action."
- **Interpret:** `execution_boundary` marks selection, authorization, execution, effect, and outcome semantics as `OUT_OF_SCOPE_FOR_SOFACTION`; candidates are not execution commands, recommendations, feasibility, or causal-effect claims; "difference is not defect, severity, or action"; post-action facts require a new audit.
- **Explain:** a structured source-addressed view, not an independent scientific conclusion; PASS establishes contract/closure only.

I have not selected, recommended, authorized, executed, or claimed any outcome or causal effect, and I did not infer alignment, policy inputs, or missing capabilities. The `operator.support.summary` MISMATCH and the two candidates are reported strictly as observed, policy-relative, bounded outputs of the validated contracts.
