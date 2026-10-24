# SOF Compatibility Guard v0

2026-10-25. This is an internal acceptance gate for the Shared A0 extraction
experiment, not a change to any SOF definition, versioned contract or API.

## Two Lanes and One Candidate Mechanism

```text
sof-runtime: engineering repository and versioned delivery
  SOF Compatibility Lane
    existing Python facade, compiler, assembly, comparison, action and validators
    stable contracts, explicit version identities and reference artifacts
  Rust Data Runtime Lane
    independently accepted Solana projection/replay and Rust calculation kernels
  Shared Mechanical Core - experimental A0
    byte identity / restricted metadata codec / exact flat inventory
```

This is a responsibility diagram, not evidence that A0 runs on either existing
production path. Only the two read-only shadow adapters use this experiment.
SOF need not change its mathematics for Solana; Solana need not claim SOF
carrier status. The current Python implementation is not replaced or demoted.

## Protected Boundary

The pre-extraction capture binds the exact file membership, lengths and raw
SHA-256 bytes of `src/sof_runtime`, vendored `contracts`, `profiles`, `services`,
`workflows`, `examples`, and the existing unit/conformance/golden/regression
test trees, plus `pyproject.toml` and the declared service/evaluation tools and
records. Only Python bytecode/cache directories are excluded. The captured
list is explicit and re-enumerated: missing, extra or changed protected files
block acceptance. It is not regenerated to excuse drift.

In particular preserve:

- `sof_runtime.sdk`, `sof_runtime.api`, CLI signatures, capability gates and
  realization/report/comparison/interpretation/candidate boundaries;
- every vendored upstream contract and `upstream.lock.json` identity;
- old v2.0/v2.1 compiler, assembler, validator, report, audit and action bindings;
- original JSON encodings, reference fixture bytes and receipt closures;
- service job/semantic identities, explicit alignment/profile requirements,
  unavailable-capability handling and no-action/no-authorization boundaries.

A0's `ascii-json-u64.v0` owns only new A0 metadata. Historical SOF and application
files remain opaque raw bytes to it. No SOF encoder, schema, package export,
plugin registry, runtime call path or compatibility record is switched to A0.

## Executable Gate

The review harness captures a before snapshot and runs the unchanged suites
under `tests/unit`, `tests/conformance`, `tests/golden` and `tests/regression`.
After extraction the same tests run again; test identities, counts, skipped
tests and all protected bytes must agree, with zero failures or errors. Expected
reference bytes are never updated as part of this experiment.

The launch profile explicitly prepends this checkout's `src` and root to
PYTHONPATH and refuses a test-process import from another editable checkout.
It sets `PIP_FORCE_REINSTALL=1` so the unchanged temporary-venv wheel test
actually installs the same-version wheel and its console script there instead
of accepting source metadata as a venv installation. The test itself removes
PYTHONPATH for its installed CLI calls. No production environment or protected
test is modified; pre/post checks use the same declared launch profile.

The gate also runs unchanged vendored-digest, service-closure, MCP evaluation
and matrix validators. A post-extraction installed-wheel check exercises the
existing public workflow independently of repository imports. These are bounded
compatibility controls, not proof of every possible SOF behavior, upstream
scientific adequacy or production reliability.

Any protected byte/identity change, new test failure, changed skip set or altered
reference artifact **blocks** this extraction's acceptance, even if both A0
shadows pass. A separate authorized versioned reopening would be needed for a
semantic change; no such reopening is part of this work.

## Non-Promotion

No shared locking, process orchestration, publication, retry, quarantine,
checkpoint inheritance or application-level PASS moves into A0. No public Rust
API, SOF protocol revision or production migration follows automatically from
passing this gate. The original receipts and prior candidate source/executable
snapshots remain historical evidence with their original bindings.
