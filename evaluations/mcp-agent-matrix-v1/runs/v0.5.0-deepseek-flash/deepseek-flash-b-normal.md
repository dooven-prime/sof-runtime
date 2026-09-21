All stages are complete and every artifact/receipt retrieved with matching SHA-256. Here is the full evaluation report.

## Discovered workflow (via MCP tool schemas only)

The six tools form a strict, staged chain. Stages are discovered from the artifact/receipt graph, not directory names:

`sof_realize` → `sof_report` → `sof_validate` → `sof_compare` → `sof_interpret` → `sof_validate` → `sof_explain`, plus digest-addressed retrieval (`sof_get_artifact`, `sof_get_receipt`) and contract reading (`sof_get_contract`).

I ran it as a full pipeline on **reference** and **target** cases in parallel where independent. Both realizations returned `canonical_compilable: true` / `eligibility: canonical_compilable`, so I proceeded (an extension-only realization would have legitimately stopped at `realize`).

## Ordered artifact chain (workspace-relative locators + digests)

| # | Stage | Artifact | Locator | SHA-256 |
|---|-------|----------|---------|---------|
| 1 | realize ref | candidate | `matrix/deepseek-flash-b/reference/realize/realization/candidate.json` | `3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3` |
| | | evidence | `.../reference/realize/realization/evidence.json` | `383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158` |
| | | receipt | `.../reference/realize/run-receipt.json` | `384ece07a5f3e02ca9c167d6d9ae86f66b03c89c15483606fee4f30ee3b8c7bc` |
| 2 | realize tgt | candidate | `matrix/deepseek-flash-b/target/realize/realization/candidate.json` | `c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907` |
| | | receipt | `.../target/realize/run-receipt.json` | `ef0ce42d5b1ac11ef9fd98fee8d30c17d48e47a342e6bb3895cfaafeaa82cfa3` |
| 3 | report ref | SOFRS | `matrix/deepseek-flash-b/reference/report/report/result.sofreport.json` | `7ab8b7ae1ab9aadd239218b6bf3efc429a4f29b3e473d6eaa47ffb4ef2f06974` |
| | | receipt | `.../reference/report/report/validation-receipt.json` | `410c8cfeae0cc8a5bebdd671a5e3dbc2138aff7b39fb75ed425e734bcf53a58d` |
| 4 | report tgt | SOFRS | `matrix/deepseek-flash-b/target/report/report/result.sofreport.json` | `8bdcb00bb9000d3ff5761030ae1e0cc74660abada49074406bb9632116e17223` |
| | | receipt | `.../target/report/report/validation-receipt.json` | `bf947922e3eaf6977bf7bd6f51a9d5b66e9e603a46acbbca2becdd1b1333f95f` |
| 5 | compare | SOFAUDIT | `matrix/deepseek-flash-b/comparison/result.sofaudit.json` | `5002028932d1ccd90630fb314253634f66faece795acff369b7adfb3dddd80a8` |
| | | receipt | `.../comparison/validation-receipt.json` | `041ea6326f0d1c5eda15a61e3819bffc1f3cd4be2cc19daf6ce27291acf52440` |
| 6 | interpret | SOFACTION | `matrix/deepseek-flash-b/action/result.sofaction.json` | `1acc22bcd9053f9bbe74a0f0302f9fdd5d9c601605bb68993bd6d3d27e4fdee3` |
| | | receipt | `.../action/validation-receipt.json` | `5b4c2913dc354e5267fa00a9552aa9f60d76bc79e09b9152836d6bfe5ad1e826` |

**Key IDs**
- Reference report: `example.finite-state-adapter.finite-state.transition.reference.sofreport`
- Target report: `example.finite-state-adapter.finite-state.transition.target.sofreport`
- Audit: `comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport`
- Action record: `action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport`

**Full semantic run IDs (`semrun:sha256:...`)**
- realize ref: `aeabaabcfedb406874f1af0020bc6b05961b341fd7d22eb6d29935c5ba73c837`
- realize tgt: `9d843fc02d206aacbb3200da62984a326c4f821f22402980a219db8b030cb45b`
- report ref: `e2ad97ef753faa507d3107ad711af5ac6cc6feafdf1868c8adfd8cb3297ff683`
- report tgt: `f8cfea7cb126343fd4f6ec72fbd56428c4c136ef4863bfbf28b3d0a0a6ba031b`
- validate sofrs ref: `63149dbb63e6a4396e19cd1cf2c786e3b324cb3e7a75fe5a04a8d16a72e5c20e`
- validate sofrs_receipt ref: `109c137629e128bb6e266bae0fdb7d97f54ef78bf972478bdba7cdf3b960ad64`
- validate sofrs tgt: `4ffb0b8bb9dcd6145734326bf90d8780c982ad5a2da32ac9a98526042d14adc8`
- validate sofrs_receipt tgt: `a04cff817dd8c9478951f2018b6626771c873313c60d237307e286ccffa3b71b`
- compare: `41ae5d3ffa2f69714ed47f6b6dd699abd9cf2254814b2a61ba11ed8b5e3f7c5f`
- validate sofaudit: `d725933e7110929817be2fa2710714ce8db277da3a083358749ab00db7efe357`
- validate sofaudit_receipt: `f46db75aab3d4b80b962d502d956bb40fa79fb4a7d61aafa0c2266cb5f51364b`
- interpret: `bbf3fdd6aefe255e76632baae3d01afdf2ef4b435205a0de994cd6a5b0e89695`
- validate sofaction: `0fc16b714fcd23c6668c3811894158ef4877118790348e751fde006f768b7704`
- validate sofaction_receipt: `2c00a9717e3840413c1ab0ec94d4961bf65f326e9ab66a2e6e21c5560f660cc6`
- explain: `0eabd5a7fa44324bd92ed53e80e4d721c7dc04e6732ba07a22067971c0ea106b`

Job IDs: realize ref `job:c2ecf5e045fc4fc89e9a127ad3e53378`, realize tgt `job:d2a73c21f6d44766b5f8d3613fa71b93`, report ref `job:168d85da9b724ddc8133ad488039203c`, report tgt `job:2df9186c68fd48248e8cc0561b35ee7e`, compare `job:bfcdc182058c45c9beed90f85b8023dc`, interpret `job:43ba69d25d744ebf8bf1699de2b99213`.

I used only the explicit inputs: `case/comparison/alignment.json` (digest `5b9e8e73d6df573d858855ad3527ebc1739599b7d6fdc478eaf13f285a436502`), `comparison-profile.json` (`bb84d2840a55b3278e509418ffd53a1b98a96fe5ee0c7304d0f5f109d52e9bd1`), context (`0e466dcb6b88dd4e24e832bf32db890ce2a1f82433ae27eb164907acd647f59d`), policy (`525f71da29007a65f46f32c323bdfc931c35c4486abb5681095404f40d5d2891`). No `compiler_profile`/`assembly_profile` overrides were supplied, so I passed none.

## Strongest justified claim at each stage

- **Realize** — Strongest: `canonical_compilable` structural eligibility (reference and target). Adapter-derived; recorded non-claims: realization validation does not establish adapter scientific adequacy. Declared capabilities: complete finite sectorization, labelled transition operators; **declared unsupported**: route filtration, positive-word depth, Lie/Hall depth, deformation chart.
- **Report (SOFRS 2.1)** — Strongest: `claim.direct-support` = **CERTIFIED** (`protocol_conformance`, classification_source `independent_validator`), under assembly profile `sof-runtime.strict-conformance.assembly.v2` / compiler profile `sof-runtime.strict-conformance`. This is protocol conformance only.
- **Compare (SOFAUDIT 2.1)** — Strongest: `comparison_relation` **CERTIFIED**; coordinate `operator.support.summary` = **MISMATCH, OBSERVED** (absolute-difference = 1; reference `support_count` 2 vs target `support_count` 3). Alignment `example.finite-state.identity.*` is TOTAL/bijective (identity, `map_kind: bijection`), regime `strict_vs_strict`.
- **Interpret (SOFACTION 2.1)** — Strongest: `Computational Certificate` for a **candidate_action_set only**. Not a selection, recommendation, authorization, execution, outcome, or effect claim.

## Unavailable / unresolved states (not coerced or zeroed)

- Both reports: modules `associative` and `closure` are **UNAVAILABLE** — unsatisfied capability requirements (no route_carrier/word_carrier, no closure carriers), unsatisfied object-kind requirements (no route_space/word_space/depth_field; no associative_closure/star_closure), and unsatisfied run-policy requirements (`missing all_of: cutoff`; `missing all_of: saturation_audit`). Only module `sof-basic` is ENABLED.
- External basis registry `basis_status: PARTIAL`; `basis.object.level` (object-level-recomputation) and `basis.semantic.adequacy` (domain-semantic-adequacy) = **NOT_ASSESSED**; `basis.source.identity` and `basis.structure.level` = SATISFIED. Negative boundary: protocol conformance does not establish domain adequacy.
- `object_level_oracle.status: NOT_ASSESSED` (no independent recomputation).
- Report `object_transition_boundary`: `artifact_role: INFORMATIONAL_REPORT`, `intervention_semantics: NONE`, `source_state_transition_authority: NONE`, `implementation_purity_status: NOT_ESTABLISHED_BY_SOFRRS`.
- ActionContext `contract_status: nonconforming` (this describes the evaluated subject); recorded separately, `context_admission.status: admitted` (applicability: applicable, completeness: complete). Policy `policy_admission.status: admitted`; `selection_status: downstream`.

## Bounded candidates (candidate set only)

Policy rule `mismatch-review` admits two dispositions (both `authorization_state: not_requested`, carrier `operator`, target `operator.support.summary`, `reversibility: unknown`):

1. `investigate:operator.support.summary` — disposition **Investigate**
2. `requestevidence:operator.support.summary` — disposition **RequestEvidence**

I neither selected nor ranked them; both are preconditions-gated ("a domain owner confirms the candidate is applicable").

## Final retrieval (locator + SHA-256) and provenance

- Retrieved **final artifact** `.../matrix/deepseek-flash-b/action/result.sofaction.json` @ `1acc22bcd9053f9bbe74a0f0302f9fdd5d9c601605bb68993bd6d3d27e4fdee3` — digest matched; content returned (`content_encoding: json`).
- Retrieved **final receipt** `.../matrix/deepseek-flash-b/action/validation-receipt.json` @ `5b4c2913dc354e5267fa00a9552aa9f60d76bc79e09b9152836d6bfe5ad1e826` — digest matched. Status **PASS**; 13-artifact closure digest `2522e2cedde1a0746bbb30ef000256dbba8b2f9af261acf0d7062cc45a11fbef`; scope `SOFACTION_PROTOCOL_CONFORMANCE_ONLY`, version 2.1.
- `sof_explain` on `matrix/deepseek-flash-b/action` traces `workflow: full_pipeline`, source-addressed stages (two realizations → two reports → comparison → interpretation), validation PASS at each stage, and the same negative boundaries. All validator checks reported `PASS` (report: artifact-closure, assembly-faithfulness, claim-compatibility, degradation-semantics, forbidden-semantic-role-scan, generation-input-closure, native-v2.1-generation, report-non-intervention, schema-validation; audit adds aligned-difference-without-attribution and reference-role-boundary; action adds candidate-non-execution, candidate-set-regeneration, verified-authority-non-authorization, downstream-artifact-role-isolation).

## Explicit negative boundaries

- `sof_runtime` validates declared contract closure and artifact digests; **it does not become the domain authority**. Validation PASS certifies protocol conformance only and does not upgrade scientific claims.
- A validation PASS is **not** self-authenticating scientific proof; the audit receipt establishes aligned comparison conformance only — neither defect attribution nor causality.
- A mismatch is a policy-relative review status, **not a certified defect**, severity, or action. "Difference is not defect without the admitted context and policy."
- The reference is a `declared_baseline_only` comparison role — **not a truth oracle**, not a causal baseline.
- CandidateActions are **not** recommendations, authorizations, execution commands, feasibility statements, correctness claims, or causal-effect certificates.
- Selection, authorization, execution, outcome, and effect are **OUT_OF_SCOPE** for SOFAction; post-action facts would require a **new Paper XIII audit**.
- I did **not** select, recommend, authorize, execute, or claim any outcome or causal effect; I did **not** infer alignment or capability, coerce unavailable states to zero, or promote protocol conformance to scientific truth.
