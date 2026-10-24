# Source Advancement and Checkpoint Invalidation v0

Offline source-compatibility prototype, not a performance experiment or reorg
implementation. [Contract](CONTRACT.md), [plan](plan.v0.json) and
[readout](READOUT_V0.md) define its scope. Frozen projection/replay v0/v1 and
prefix-attribution sources and receipts are unchanged.

## What Is Implemented

| Proposed transition | Behavior |
|---|---|
| Same admitted credential, exact committed evidence, appended slots | Inherit prefix; decode/project only suffix |
| Changed credential or changed raw prefix evidence, equal canonical records | Require explicit permitted reapproval and full prefix reprojection |
| Different committed canonical records or listed status | Refuse inheritance; report earliest conflict and affected checkpoint |
| Missing evidence, unknown permission, bad anchors or continuity | UNRESOLVED; publish no new state |

The source identity binds a credential; execution identity binds program,
projection and policy; checkpoint identity binds one captured state and its
parent. A capture manifest has its own identity. Same source does not mean
same capture/checkpoint. Equal output does not confer provider trust.

Credentials and admission rules in this prototype are **pinned local test
permissions**, not authenticated RPC-provider credentials. Changing policy
or program invalidates execution-identity compatibility; no migration is
silently performed. The `reapprove` request cannot bypass an unknown source
or a missing permitted credential-pair rule.

## Local Build and Offline Controls

From the repository root, with Rust 1.89+, Python and `psutil`:

```powershell
cargo build --release --locked --manifest-path plugins/rust/solana-source-advancement/Cargo.toml
python -B -m unittest discover -s tests/cross_language -p test_solana_source_advancement.py -v
python -B -O -m unittest discover -s tests/cross_language -p test_solana_source_advancement.py -v
```

These controls generate their small upstream input locally. The selected real
data-derived acceptance also requires the exact previously saved capture:

```powershell
python -B -m applications.solana_source_advancement.acceptance runs/solana-incremental/capture-devnet-64-v1/manifest.json runs/solana-source-advancement/my-acceptance-v0
python -B -O -m applications.solana_source_advancement.verify runs/solana-incremental/capture-devnet-64-v1/manifest.json runs/solana-source-advancement/my-acceptance-v0
```

Use a new run directory. No network request occurs. The producer derives
16/32/64-slot windows and explicitly synthetic source/contradiction fixtures
from the frozen real payloads. Their new envelopes are not additional genuine
RPC captures. All original captured input remains untouched. This is not a
self-contained public dataset package; the compact selected
[receipt](results/acceptance.v0.json) binds local raw inputs, requests, states,
Rust logs and Python outputs retained under ignored `runs/`.

## Request and Publication

The application-local binary accepts `REQUEST_JSON NEW_STATE_DIRECTORY`.
Request schema `sof-runtime.source-advancement-request.v0` declares `mode`
(`init`, `append`, `reapprove`), policy path/digest, candidate manifest and,
except for initialization, the old capture/state/checkpoint anchor. Examples
are generated under the acceptance run's `requests/` directory. They bind
specific local paths and must not be treated as generic live-provider policy.

The old checkpoint hash must come from a prior successful execution of this
contract. Merely hashing arbitrary state does not establish that basis.
Legacy incremental-replay v1 checkpoints are not accepted as this new schema.
The new experiment initializes its own source-bound checkpoint chain; no
published/frozen state is silently rewritten or migrated.

All input, policy and checkpoint guards are checked, including stream hashes
before and after use. A successful conversion publishes a new directory with
`checkpoint.json`, `transition.json`, canonical projection and slot segments.
The checkpoint links the old checkpoint and transition record. Its identity
changes even when its canonical projection does not.

Failed validation does not publish that directory or a success receipt.
Structured stdout records refusal, source transition where validated, request
and checkpoint identities, earliest conflict when meaningful, and reason.
A missing source may leave a source field unavailable; the bound request is
not promoted into trusted evidence. Sibling writer locks/diagnostic logs can
exist after refusal; they are not committed application state. Output paths
inside parent state or either input capture are rejected before lock creation.

## Why Prefix Inheritance Is Sufficient Here

The prior validated anchor and byte checks establish the old prefix under
the same execution contract. For ordinary append, identical raw responses,
listed status and projection/configuration determine the same prefix records;
no new prefix projection is needed. Reapproval instead establishes exact
canonical-record equality by actual reprojection and separately checks the
policy permission. Validating the suffix and chain then makes concatenation
equal to full replay. Publication occurs only after all those checks and
post-consumption stability succeed. SHA-256 identities and the declared
single-writer/trusted-anchor assumptions remain part of this argument.

This is a sufficient inheritance argument for the declared system, not a
universal weakest source-trust criterion. The independent Python model always
reconstructs the full relevant records; it does not use Rust results to define
expected outputs. Tests are bounded controls, not proofs of consensus validity.

## Boundaries

No live ingestion, provider authentication, finality verification, chain-tip
selection, fork switching, rollback, active-state pointer, remote sink,
distributed recovery or transaction-version expansion. Conflict invalidates
compatibility **with this candidate**; it does not erase historical validity
of the old checkpoint. Publication-stage crash recovery, power-loss durability
and code/policy migration need their own contracts. No speedup is claimed.
