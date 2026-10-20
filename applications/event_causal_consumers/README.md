# Event-Causal Q2 and Forward-Operator Controls

**Implementation status:** `SYNTAX_WIDE_Q2_IMPLEMENTED`, 2026-10-20.
**Research status:** research implementation of the declared consumer grammar,
with a paper-owned candidate snapshot binding. No SOF compiler/Registry
promotion or SOFRS adapter is claimed.
**Execution status:** Python 3.11+ standard library. Q2 itself needs no Git,
network, forest/UFE implementation, or installed SOF runtime. The frozen-source
differential tests and older controls accept either pinned Git inputs or the
explicit offline blobs included in the Paper XL source snapshot.
**Paper evidence:** only the source snapshot and bounded records explicitly
bound by RIME `experiments/paper40/`. Directory membership alone is not
evidence. This is neither independent validation nor a machine proof.

The canonical mathematical manuscript is `papers/paper40/Paper XL.md` in the
sibling RIME repository. The earlier unnumbered `event_causal_consumers` notes
remain unpublished writing and implementation provenance. Opening the numbered
draft does not publish this local implementation or change `ECC_SYN_V1`.
This directory adds no compiler rule, runtime schema, CLI/API registration,
report capability, or scientific claim status.

## Standalone Evidence Snapshot

`SNAPSHOT_README.md` and `run_evidence.py` are the portable snapshot entry.
The paper-owned exporter includes the selected sources, both MIT notices,
and three exact XXXIX release blobs. In the extracted archive,
`python -B run_evidence.py` runs all 30 application tests with no skips and
replays the bounded controls without Git, network or either checkout.
The source allowlist and archive hash are owned by RIME `experiments/paper40/`.
The archive is an evidence mirror; this directory remains the maintained code.
No public tag/DOI or verified download is implied by creating that candidate.

## Syntax-Wide Q2

`q2_cli.py` accepts JSON expressions, not Python callbacks. The complete local
language is documented in [Q2_LANGUAGE.md](Q2_LANGUAGE.md): all frozen sorts,
products, records, lists, Options, four causal reads, pure operations,
conditionals, and chronological left folds with lexical bindings. Reports,
guards, and q are statically checked before exploring any states, including
unexecuted branches and empty registered domains.

`q2/model.py` independently enumerates the current partition plus bounded
fusion-event list from the singleton seed to graph closure. No raw-word
length cutoff is used; history words are predecessor witnesses, never state
keys. On the exact generated causal image, `q2/engine.py` checks R, then G,
then T on commonly enabled commands. A rejection includes two actual words,
the same selected F, full causal reads, typed q/report values, guards, and
the two actual successors for T.

`q2/replay.py` separately reconstructs the selected origin and absorption
subsequence by streaming each witness word. It does not call the producer's
step, decoder, saturation, or decision functions, and trusts no state IDs.
It shares the declared record types, static checker, and value interpreter:
this is not an externally independent validation. Replaying two histories
certifies their separation, not the producer's full-domain completeness.

From the runtime repository root:

~~~powershell
$request = 'applications/event_causal_consumers/examples/origin_read_failure.json'
python -B applications/event_causal_consumers/q2_cli.py check $request |
    python -B applications/event_causal_consumers/q2_cli.py verify $request --result -
python -B -m unittest discover -s applications/event_causal_consumers -p test_q2.py -v
~~~

The pipeline sends the produced rejection JSON directly to the verifier;
no pre-existing `rejection.json` file is required.

The CLI is a local script, not an installed `sof` command. It reads JSON and
writes a decision to stdout; it does not create a report, receipt, or source
artifact. Either JSON input may use `-` for stdin, but not both simultaneously.
Input SHA-256 binds the complete supplied request, including resource policy;
it is not an implementation/proof digest or a promotion certificate.

Local statuses are `PASS_EXACT`, `FAIL_READ`, `FAIL_GUARD`, `FAIL_SUCCESSOR`,
`EMPTY_REGISTERED_DOMAIN`, `INVALID_INPUT`, and `UNRESOLVED_LIMIT`. Exit codes
are 0 for completed decisions (including mathematical rejections), 1 for
invalid input/witnesses, and 2 for resource limits. Time/step/AST/state limits
are cooperative safety bounds, not a word budget or complexity theorem.
An incomplete run issues no exact pass or rejection. Empty registration is
vacuous and does not supply a source or nonempty SOF.

The implementation handles finite well-typed expressions generically. Tests
exercise every constructor, primitive, and base sort on the existing control
environments; they do not exhaust all syntax trees or prove the implementation
correct. No new defect census was added. The optional differential test reads
only the pinned XXXIX inputs described below, not current checkout sources.

Admission is relative to the supplied reports and command menu. On the same
three-point domain, the same q=(P,F) passes the packet-only consumer but fails
the origin-parent report. A single q preserving every read in the entire
language would have to be injective on the generated causal-summary image:
the four base reads already expose all of Gamma. This is not a claim that
the forest-to-Gamma decoder is injective or globally minimal.

## Historical Fixed-Control Scope

The runner saturates exactly three fixed environment/selected-event pairs:

| n | Defect | Seed | F |
|---|---|---|---|
| 2 | (0,0) | identity singleton seed | {0,1} |
| 3 | (0,2,0) | identity singleton seed | {0,1,2} |
| 4 | (0,0,1,2) | identity singleton seed | {0,1} |

Log states and forest states are explored separately to graph closure. Words
are predecessor witnesses, not saturation-key fields. The complete generated
decoder images must coincide. Semantic R/G/T tests run on the log-defined
causal image; operator tests construct partial basis columns on the generated
forest image. Positive controls additionally check every two-command product.
No floating-point matrices or tolerance-based equality is used.

A third comparison constructs a basis e_x-e_pivot for each candidate fiber's
zero-sum subspace and tests its invariance under every declared command and
report-value projector. Membership uses exact integer coefficient sums in
each fiber, not numerical rank. For the fixed four-point full-Gamma decoder,
60 fibers have size 1 and 12 have size 2, giving kernel dimension 12.
This is the kernel reformulation of the forward check, not a reducing-space
or star-closure claim.

Nine fixed report/state/command selections cover full Gamma, packet-only
consumers, the count-fold schema, and read/guard/successor failures. Negative
decisions are replayed from their actual history words. The displayed d/pd,
dd/pdd, and dp/dppd pairs are checked explicitly as well. A separate existing
seven-point invocation checks `dppd; ppd; p^5d` with F={3,5}: unrelated Carry
fusion must update every packet before the later selected Absorb.

The older `fixed_controls.py` runner uses explicitly coded fixed report/state functions. It
does **not** implement the typed consumer grammar, accept arbitrary user
callbacks as that grammar, or issue a syntax-wide Q2 admission certificate.
It remains a separate bounded operator/kernel control; it is not the
implementation behind the JSON engine.
There is no new defect census. The seven-point test is one continuation, not
an exhausted seven-point domain.

## Exact Source Input

`fixed_controls.py` reads only `contract.py`, `log_consumer.py`, and `forest.py`
from RIME content commit `b032b47ec47f28c8b2f65844abbe30dc3b38fef8`
(`paper39-v1.0`). Their exact blob SHA-256 values are pinned in the runner.
It loads the checked bytes in temporary module namespaces, restoring prior
module bindings afterwards; no source files or bytecode are materialized.
It never substitutes current checkout files or writes into the upstream
repository. The frozen
log and forest algorithms share record definitions; this comparison does
not manufacture an external independence claim.

Run from the SOF runtime repository root with an explicit upstream checkout:

~~~powershell
python -B applications/event_causal_consumers/fixed_controls.py --upstream-root ../rime-lite
$env:RIME_LITE_UPSTREAM = (Resolve-Path ../rime-lite).Path
python -B -m unittest discover -s applications/event_causal_consumers -p test_fixed_controls.py
~~~

The older runner writes JSON only to stdout. The Paper XL snapshot runner
also binds its output into the paper-owned bounded record; neither runner
creates a release receipt or public anchor.
An interrupted saturation returns `UNRESOLVED_LIMIT` and exit code 2, not an
exact pass or mathematical rejection. Missing Git blobs, digest drift,
invalid inputs, or mismatched implementations are errors. An empty registered
domain is not a supplied event or a nonempty SOF.

## Known Nonclaims

This is not an installed `ExpertAdapter`, canonical-compilable realization,
SOFRS report, Registry finding, or extension admission. No automatic report,
comparison, epistemic activation, action authorization, or source mutation
is performed. L_q is a forward quotient map, not a Paper VIII strict SOF
morphism. Adjoint, star-closure, spectral, and Lie/Hall preservation are not
inferred. Neither the controls nor the source model supplies old B0, typed
transfer, POS, or a reset bound.
