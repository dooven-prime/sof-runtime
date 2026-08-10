# Reporting Contracts

`candidate-v2.0/` is a byte-pinned integration snapshot of the active Paper
XII SOFRS v2 candidate. Its provenance is recorded in
`../upstream-candidate.lock.json`.

This directory is deliberately not part of the canonical immutable
`upstream.lock.json` yet. The source Paper XII schemas are still uncommitted in
the `rime-lite` working tree, so no Git revision can reconstruct them. Runtime
conformance against these bytes is candidate integration evidence, not an
upstream publication or semantic promotion.

After Paper XII has a release-content commit, move the same byte identities
under a stable `reporting/v2.0/` path, add their committed upstream paths and
digests to `upstream.lock.json`, and remove the candidate lock.
