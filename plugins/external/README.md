# External Plugin Protocol

An external plugin is a replaceable computation backend, not a semantic
authority. It receives one `sof.run-request.v1` JSON object on standard input
and emits one extension payload on standard output. The orchestrator, not the
plugin, stores the payload, invokes the independent validator, and emits the
final `sof.run-response.v1`.

- Write logs to standard error.
- Return zero only when one UTF-8 JSON payload was produced.
- Bind the payload to the request's `semantic_run_id` and `execution_id`.
- Declare the same `semantic_environment` only when algorithm mode,
  arithmetic semantics, dependency lock, and feature flags are genuinely
  equivalent; process and language placement belong to `runtime_environment`.
- Do not emit execution status, `CERTIFIED`, Compiler Output, or report state.
- Treat `artifact_directory` as an orchestrator-owned boundary in protocol v1.

The executable may be implemented in Rust, Julia, C++, Java, or another
language. It does not need to import the Python package.

## Rust conformance fixture

`plugins/rust/positive-word-support/` is a minimal Rust implementation of the
same Markov positive-word semantics as the Python reference plugin. It uses
the same plugin identity and semantic-environment declaration because its BFS
algorithm and exact support arithmetic are semantically equivalent. Language,
process, runtime, and operating-system details remain execution metadata.

The executable supports three protocol/conformance entry points:

```text
sof-positive-word-support                    RunRequest stdin -> bundle stdout
sof-positive-word-support --canonicalize     JSON stdin -> sof-cjson-v1 bytes
sof-positive-word-support --canonical-sha256 JSON stdin -> lowercase SHA-256
```

`--fail` is a deterministic nonzero-exit fixture. The Rust process never
writes artifacts and never interprets `artifact_directory` as a writable
path; the Python orchestrator alone creates the content-addressed artifact
closure. Build it with `python tools/build_rust_plugins.py`. Set `CARGO` when
Cargo is not on `PATH`.

This is one Python/Rust conformance pair under one carrier contract. It is not
a claim that every plugin, number representation, or language implementation
already conforms.
