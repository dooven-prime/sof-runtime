Workflow complete. Here is the final research report.

---

# SOF Runtime Evaluation — `deepseek-flash-a`

**Workspace:** `mcp-matrix-deepseek-flash-a-20260921`
**Discovered operations (MCP tool names):** `sof_realize` → `sof_report` → `sof_compare` → `sof_interpret`, with `sof_validate`, `sof_explain`, `sof_get_artifact`, `sof_get_receipt`, `sof_get_contract` as cross-cutting support tools. No tool selects, authorizes, executes, observes outcomes, or certifies causal effects, so the **strongest admitted workflow terminates at `interpret`** (interpretation + bounded candidate set). I did not attempt anything beyond that.

## Ordered artifact chain (all staged under `matrix/deepseek-flash-a/`)

| # | Stage | Artifact locator (workspace-relative) | SHA-256 | Semantic run ID |
|---|-------|--------------------------------------|---------|-----------------|
| 1 | realize (ref) | `reference/realization/candidate.json` | `3559dd19203b73a1…cf9573f3` | `semrun:sha256:aeabaabcfedb406874f1af0020bc6b05961b341fd7d22eb6d29935c5ba73c837` |
| 2 | realize (tgt) | `target/realization/candidate.json` | `c120c334d96cf906…16129907` | `semrun:sha256:9d843fc02d206aacbb3200da62984a326c4f821f22402980a219db8b030cb45b` |
| 3 | report (ref) | `reference-report/report/result.sofreport.json` | `7ab8b7ae1ab9aadd…ef2f06974` | `semrun:sha256:e2ad97ef753faa507d3107ad711af5ac6cc6feafdf1868c8adfd8cb3297ff683` |
| 4 | report (tgt) | `target-report/report/result.sofreport.json` | `8bdcb00bb9000d3f…16e17223` | `semrun:sha256:f8cfea7cb126343fd4f6ec72fbd56428c4c136ef4863bfbf28b3d0a0a6ba031b` |
| 5 | compare | `comparison/result.sofaudit.json` | `5002028932d1ccd9…3dddd80a8` | `semrun:sha256:41ae5d3ffa2f69714ed47f6b6dd699abd9cf2254814b2a61ba11ed8b5e3f7c5f` |
| 6 | interpret | `interpretation/result.sofaction.json` | `1acc22bcd9053f9b…27e4fdee3` | `semrun:sha256:bbf3fdd6aefe255e76632baae3d01afdf2ef4b435205a0de994cd6a5b0e89695` |

Accompanying receipts: realize run receipts (`reference/run-receipt.json` `384ece07…`, `target/run-receipt.json` `ef0ce42d…`); report receipts (`410c8cfeae0cc8a5…` ref, `bf947922e3eaf697…` tgt); comparison receipt `041ea6326f0d1c5e…`; final receipt `interpretation/validation-receipt.json` `5b4c2913dc354e52…`.

## Canonical-compilation eligibility (checked before reporting)
Both realizations returned `eligibility: "canonical_compilable"` and `canonical_compilable: true` (reference source `finite-state.transition.reference`; target source `finite-state.transition.target`), so both were eligible to enter report assembly. Neither was extension-only.

## Validation results (declared-contract closure only)
- `sofrs` (both reports): PASS — protocol conformance only.
- `sofrs_receipt` (both report receipts): PASS.
- `sofaudit`: PASS. `sofaudit_receipt`: PASS — aligned comparison conformance only.
- `sofaction`: PASS. `sofaction_receipt`: PASS — candidate-protocol conformance only, `authorization/execution/effect/outcome_semantics = NONE`.

## Strongest justified claim at each stage
1. **Realize:** `claim.direct-support` → *Computational Certificate* — "the external adapter's declared transition family has certified thresholded direct support," scoped to the finite-state basis and supplied matrices. Negative boundary: does not establish route, word, Lie/Hall, causal, or domain-adequacy conclusions; realization validation does not establish adapter scientific adequacy.
2. **Report:** SOFRS v2.1 protocol conformance; certified direct support — reference `support_pairs = [[busy,done],[idle,busy]]` (count 2); target `support_pairs = [[busy,done],[done,idle],[idle,busy]]` (count 3), both under the adapter-declared threshold "absolute matrix entry > 1e-12." `object_transition_boundary`: `intervention_semantics NONE`, `source_state_transition_authority NONE`, `implementation_purity_status NOT_ESTABLISHED_BY_SOFRS`.
3. **Compare:** SOFAUDIT *Computational Certificate* on the comparison relation, under declared identity alignment (observable + sector bijections) and profile `sof-runtime.external-adapter.identity.v2`. Coordinate `operator.support.summary` = **MISMATCH**, absolute-difference delta 1. Reference is explicitly `NOT_A_CAUSAL_BASELINE` / `COMPARISON_ROLE_ONLY`; negative boundary: does not establish reference truth, defect status, severity, or action.
4. **Interpret:** SOFACTION *Computational Certificate* over the admitted context/policy. Candidate set (not selection/authorization/recommendation):
   - `investigate:operator.support.summary` — disposition **Investigate**
   - `requestevidence:operator.support.summary` — disposition **RequestEvidence**

   Both `authorization_state: "not_requested"`. Rule `mismatch-review`, policy `finite-state-review-policy` r1, context `finite-state-review-context-v1`.

## Unavailable / unresolved / not-assessed states (not coerced)
- **Modules UNAVAILABLE:** `associative` (no `route_carrier`/`word_carrier`, no `route_space`/`word_space`/`depth_field`, missing `all_of: cutoff`) and `closure` (no closure carriers, missing `all_of: saturation_audit`). Only `sof-basic` is ENABLED.
- **External basis registry `basis_status: PARTIAL`:** `basis.source.identity` SATISFIED; `basis.structure.level` SATISFIED; **`basis.object.level` NOT_ASSESSED**; **`basis.semantic.adequacy` NOT_ASSESSED**. Object-level oracle `NOT_ASSESSED`.
- **ActionContext:** `contract_status: "nonconforming"` (the evaluated subject's declared status), recorded separately from `context_admission.status: "admitted"` (completeness `complete`, applicability `applicable`, `contract_validation: "admitted"`). No missing context/policy fields.
- The comparison is one declared coordinate only; a mismatch is not by itself a defect or action.

## Final retrieval (by locator + exact digest)
- Retrieved **`interpretation/result.sofaction.json`** at `sha256:1acc22bcd9053f9bbe74a0f0302f9fdd5d9c601605bb68993bd6d3d27e4fdee3` — digest matched.
- Retrieved **`interpretation/validation-receipt.json`** at `sha256:5b4c2913dc354e5267fa00a9552aa9f60d76bc79e09b9152836d6bfe5ad1e826` — digest matched (receipt_id `receipt.action…sofaction-v2_1`, `receipt_scope: SOFACTION_PROTOCOL_CONFORMANCE_ONLY`, `status: PASS`).

## Provenance explanation (`sof_explain` on the interpretation run)
Stage graph discovered from the artifact/receipt graph (not directory names): two `realization` stages (each `canonical_compilable: true`, adapter `example.finite-state-adapter` v1.0, source_mapping `adapter-derived`), two `report` stages (`strict_sof`, PASS), one `comparison` stage (`operator.support.summary` = MISMATCH, alignment `example.finite-state.identity.{observable,sector}`, PASS), one `interpretation` stage (context `finite-state-review-context-v1`, policy `finite-state-review-policy`, PASS). `workflow: "full_pipeline"`; `why_unresolved_or_unavailable` empty for the comparison; interpretation uncertainty `bounded` with no listed reasons.

## Explicit negative boundaries observed
- Validation PASS certifies the declared contract closure only and does **not** upgrade scientific claims.
- Protocol conformance (SOFRS/SOFAUDIT/SOFACTION) does **not** establish domain adequacy, reference truth, defect status/severity, implementation purity, or causality.
- Candidate actions are **not** selection, recommendation, authorization, execution commands, feasibility claims, or causal-effect certificates; outcomes require a new audit.
- Identity alignment does not establish cross-domain semantic equivalence; the reference is a declared baseline only, not a truth oracle.

I did not infer alignment, invent policy inputs, assume any missing capability, coerce unavailable states to zero/normal, or claim any outcome, effect, selection, or authorization.
