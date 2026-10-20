# Paper XL Q2 Source Snapshot

This is an exact source snapshot of the event-causal application maintained in
`dooven-prime/sof-runtime`. It accompanies the Paper XL candidate; it is not an
installed SOF runtime release, SOFRS adapter or independent certificate.
The source manifest binds file bytes, not a claimed public Git commit.

## Run Without a Checkout

Extract the archive, then run from its root with Python 3.11+:

```text
python -B run_evidence.py
python -B q2_cli.py check examples/origin_read_failure.json
```

The first command verifies the source inventory, runs all nine declared
controls and all 30 tests without skips, and emits a bounded result JSON. It
starts an interpreter with optimization disabled and fixed hash ordering.
It needs no pip installation, Git, network, sibling checkout or SOF service.
The optional `--output result.json` and `--environment environment.json` paths
must be outside the extracted source directory, keeping the snapshot read-only.

To check and separately replay the example, in PowerShell:

```powershell
python -B q2_cli.py check examples/origin_read_failure.json |
    python -B q2_cli.py verify examples/origin_read_failure.json --result -
```

For POSIX shells, the same pipeline can be written on one line. See
[Q2_LANGUAGE.md](Q2_LANGUAGE.md) for changing the typed request, reports,
guards, folds and candidate q. The CLI accepts these as data, not callbacks.

## What Is Included

`source-manifest.json` lists every payload file with its SHA-256 and size.
`frozen/paper39/` holds three unmodified, hash-checked release blobs from
Paper XXXIX content commit `b032b47ec47f28c8b2f65844abbe30dc3b38fef8`, plus its
license. These supply the existing differential tests without requiring Git.
They are regression inputs, not an implementation of Q2 and not a reopening
of XXXIX. `APPLICATION_README.md` retains the source application's broader
documentation, including its alternative Git-based development workflow.

The archive license is MIT. A source hash identifies bytes; it does not prove
the implementation correct. The record is local closure verification and
bounded consistency replay. The rejection verifier shares typing and
expression evaluation with the producer. No external independence, general
software proof, efficiency advantage or cross-domain usefulness is claimed.

The mathematical proofs remain in the owning Paper XL manuscript. Actual
public accessibility requires publication of this archive and its paper-owned
hash record at an immutable release location; merely preparing it is not
publication.
