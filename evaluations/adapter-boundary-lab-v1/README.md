# Adapter Boundary Lab v1

This package is a deterministic boundary test for adapter-level observations.
It covers five finite fixtures:

1. `markov-positive`: a nonnegative exact-rational Markov operator where
   support-graph paths agree with positive matrix-power support;
2. `signed-cancellation`: signed matrix entries produce route-sum cancellation;
3. `multi-letter-word`: an unlabelled graph path does not establish support for
   an independently selected labelled word;
4. `cutoff-unreached`: a finite cutoff records `UNREACHED_AT_CUTOFF` and never
   substitutes exact infinity;
5. `threshold-sweep`: support classification changes with the declared strict
   threshold.

Run the lab from the repository root:

```text
python evaluations/adapter-boundary-lab-v1/run_lab.py
```

Check the committed result without rewriting it:

```text
python evaluations/adapter-boundary-lab-v1/run_lab.py --check
```

The runner writes the deterministic summary to
`evaluations/adapter-boundary-lab-v1/results/summary.json` unless `--output`
is supplied. It performs no SOFRS, SOFAUDIT, or SOFAction assembly. The
results are adapter-boundary evidence only and do not promote a carrier or
establish domain adequacy.

Every fixture declares its strongest justified claim and known nonclaims in
`fixtures.json`. The runner also checks those declarations against the
computed evidence so a fixture cannot silently broaden its interpretation.
The result binds the exact fixture manifest and runner with SHA-256 digests.

## Boundary Rules

- Nonnegative single-letter support can use the declared graph equivalence
  under exact rational arithmetic.
- Signed matrices require explicit cancellation-aware evaluation.
- Multiple operative letters require labelled word evaluation; union-graph
  reachability is not a word result.
- A finite cutoff is a finite observation, not an infinity certificate.
- Thresholded support is relative to its declared threshold and comparison
  rule.

## Known Nonclaims

The package does not establish mixing time, route depth, exact word depth,
rank collapse, Lie/Hall depth, scientific adequacy, global equivalence,
defect status, action selection, authorization, execution, outcome, or causal
effect. It also does not turn a passing fixture into a canonical SOF report.
