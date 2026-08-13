# AI Observable Adapter

This example treats a Transformer or LLM as an API-only black-box source. It
produces `diagnostic_analogue` SOFRS reports for four declared observable
families:

- `format`
- `semantic`
- `behavior`
- `repair_probe_result`

`repair_probe_result` records only whether a declared constrained probe changes
a bounded observable relative to its paired bare probe. It is not a
CandidateAction, recommendation, selection, authorization, execution, outcome,
or causal-effect claim.

Run the deterministic reference and target cases:

```bash
sof realize examples/ai-observable-adapter/reference runs/ai-observable/reference
sof report runs/ai-observable/reference
sof realize examples/ai-observable-adapter/target runs/ai-observable/target
sof report runs/ai-observable/target
```

Compare the two reports with the explicit analogue probe alignment:

```bash
sof compare \
  runs/ai-observable/reference/report/result.sofreport.json \
  runs/ai-observable/reference/report/validation-receipt.json \
  runs/ai-observable/target/report/result.sofreport.json \
  runs/ai-observable/target/report/validation-receipt.json \
  --alignment examples/ai-observable-adapter/comparison/alignment.json \
  --comparison-profile profiles/comparison/ai-observable-identity-v2.0.json \
  --out-dir runs/ai-observable/comparison
```

The SOFAUDIT is `analogue_vs_analogue`. Its single
`ai.observable.descriptor` coordinate contains the six declared probe values
and their coordinatewise differences. Missing or renamed descriptor keys are
rejected rather than inferred. Every SOFRS finding also retains
`success_count`, `applicable_count`, and `rate_percent`; the deterministic
example coordinates are therefore visibly `1/1`, not unqualified percentages.

The optional DeepSeek case reads `DeepSeek_Service_Key` from the process
environment. The source contract and adapter both pin
`https://api.deepseek.com/chat/completions`, and the HTTP client rejects
redirects so that the authorization header cannot be forwarded to another
host. The key and raw response text are not retained in artifacts:

```bash
sof realize examples/ai-observable-adapter/deepseek runs/ai-observable/deepseek
sof report runs/ai-observable/deepseek
```

The model ID and pinned endpoint remain explicit source inputs because provider
model names and backend behavior can change. `semantic.exact_answer` accepts
only the normalized exact expected answer, not mere token occurrence. The
example does not claim access to
weights, activations, routing, hidden states, latent mechanisms, global model
quality, defect status, or action authority.
