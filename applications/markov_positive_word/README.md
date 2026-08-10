# Markov Positive-Word Adapter

This application is the second end-to-end `sof-runtime` vertical slice. It
maps an exact finite rational Markov matrix to singleton coordinate sectors
and one labelled nonnegative operator `P`.

The extension records, for every ordered off-diagonal state pair `(i, j)`,
the first positive depth `d` for which `(P^d)_{ij}` is nonzero. The producer
uses per-source breadth-first search on the support graph. A separate
validator reconstructs the support relation from canonical artifacts and
uses Floyd-Warshall to recompute every first-hit depth.

This application deliberately differs from synchronizing automata. Its source
is an exact rational stochastic matrix, its operative alphabet has one letter,
and its finding is a coordinate-pair support census. It does not use a
transformation monoid, reachable image subsets, reset words, or rank collapse.
Both applications nevertheless use the same RunRequest, content-addressed
artifact, structured failure, independent-validation, RunResponse, and
promotion-package contracts.

## Boundary

The producer/validator equivalence is exactly

```text
support-graph path <=> positive matrix-power entry
```

and is admitted only because the current source is single-letter,
entrywise-nonnegative, exact rational, and uses strict numerator `> 0` as its
positivity rule. Nonnegativity ensures that support in a positive power cannot
be removed by route-sum cancellation in this declared class. The equivalence
does not extend automatically to signed matrices, multiple letters or linear
combinations, complex weights, route-sum cancellation, or tolerance-relative
near-zero tests.

The extension does not infer a
mixing time, a routed-product depth, an algebra-saturation depth, rank
collapse, or Lie/Hall accessibility. The raw finding remains a Computational
Observation; a passing independent validator supports the candidate promotion
package but does not grant upstream semantic acceptance.

Run the checked example from the repository root:

```bash
sof validate-source examples/markov/cycle4-lazy.json
sof admit examples/markov/cycle4-lazy.json --out runs/cycle4-lazy/manifest.json
sof run positive-word-support examples/markov/cycle4-lazy.json --run-dir runs/cycle4-lazy
sof validate runs/cycle4-lazy/run-response.json
sof validate-promotion runs/cycle4-lazy/promotion-package.json runs/cycle4-lazy/run-response.json
```

For the four-state lazy cycle fixture, all 12 ordered off-diagonal pairs are
reachable and the maximum first-positive support depth is 3.
