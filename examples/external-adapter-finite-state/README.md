# External Adapter Reference Workflow

This is a third-party-style Level 1A/1B integration. The adapter author supplies
only:

- `source/input.json`: domain-native finite-state data;
- `adapter.py`: `describe`, `inspect_source`, `realize`, and `evidence`.

The adapter never writes a Capability Manifest, Typed SOF IR, CompilerOutput,
SOFRS report, or validation receipt. `sof-runtime` owns those objects and
source-addresses them in the run directory.

Run Level 1A from the `sof-runtime` repository:

```text
sof realize examples/external-adapter-finite-state --run-dir runs/external-adapter-finite-state
```

Level 1A produces:

```text
runs/external-adapter-finite-state/
  source/input.json
  adapter/{implementation,declaration,inspection}.json
  realization/{candidate,evidence}.json
  run-receipt.json
```

For this example the candidate matches the current canonical operator
contract. Level 1B can therefore be run explicitly:

```text
sof report runs/external-adapter-finite-state \
  --out-dir runs/external-adapter-finite-state
```

That adds the runtime-owned compiler and report artifacts. An extension-only
adapter would stop after Level 1A and would not produce these files.

## Known non-claims

- This is a finite protocol control, not a universal adapter SDK.
- The runtime does not infer missing carriers, word depth, Lie depth, or
  domain adequacy.
- A passing SOFRS receipt establishes contract and artifact closure only.
- Comparison and action semantics are separate Level 2 and Level 3 workflows.

## Full reference workflow

The `reference/` and `target/` cases use the same adapter with different source
snapshots. They exercise the bounded Level 2 and Level 3 controls:

```text
two external adapters
  -> two SOFRS reports
  -> explicitly aligned/profiled SOFAUDIT
  -> policy-relative SOFaction
  -> Investigate / RequestEvidence candidates
```

Run the complete workflow from the repository root:

```text
sof full-pipeline \
  examples/external-adapter-finite-state/reference \
  examples/external-adapter-finite-state/target \
  examples/external-adapter-finite-state/action/context.json \
  examples/external-adapter-finite-state/action/policy.json \
  --alignment examples/external-adapter-finite-state/comparison/alignment.json \
  --comparison-profile profiles/comparison/external-adapter-identity-v2.0.json \
  --run-dir runs/full-pipeline
```

The final artifact contains a candidate set only; it performs no action
selection, authorization, execution, or effect claim.

The example intentionally sets `ActionContext.contract_status` to
`nonconforming`. This is a supplied status of the evaluated finite-state
subject, not a claim that the ActionContext machine contract is invalid.
`context_admission.contract_validation = admitted` records the separate fact
that the ActionContext object passed the declared protocol checks. Neither
field establishes domain-level defect or contract correctness.
