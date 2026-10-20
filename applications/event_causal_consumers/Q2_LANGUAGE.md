# Local Typed Q2 Language

**Version:** `ECC_SYN_V1`, local research input format, 2026-10-20.
This serializes the declared causal-consumer grammar now presented in RIME
`papers/paper40/Paper XL.md`. The move from the unnumbered proof notes changes
neither this syntax version nor its semantics.
It is not a Paper X Manifest/IR, SOFRS schema, extension admission, or new
published semantic contract. No arbitrary code, import, callback, external
query, or consumer-defined primitive is accepted.

## Request

~~~json
{
  "language": "ECC_SYN_V1",
  "environment": {"defect": [0, 2, 0], "seed": [0, 1, 2]},
  "selected": [0, 1, 2],
  "program": {
    "reports": [{"label": "origin", "expr": {"kind": "query", "name": "OriginSnapshot"}}],
    "commands": [{"label": "Raw(p)", "letter": "p", "guard": {"kind": "literal", "type": "Bool", "value": true}}],
    "q": {"kind": "query", "name": "CurrentPartition"}
  }
}
~~~

`n` is the length of `defect`. Entries belong to `0..n-1`; exactly one fiber
has size two, one is missing, and all others have size one. p(q)=q+1 mod n.
`seed` gives the distinct positions of the N singleton atoms, with 2<=N<=n.
Optional `atoms` declares N distinct integer/string labels, defaulting to
0..N-1. Bool is not an integer atom label. Optional `kernel_ports` explicitly
orders the two kernel coordinates; the default is increasing coordinate order.
`selected` is one nonempty set of declared atom labels, fixed for the request.
Registration requires its actual creation as a fresh fusion block.

All reports and q are closed expressions of any supported sort; each guard
is a closed Bool expression. Labels within reports and within commands must
be distinct. Equal underlying letters/expressions do not merge labels. Empty
report or command arrays are permitted. Unknown fields are input errors.

Optional `resources` keys and defaults:

~~~json
{"max_states": 100000, "max_steps": 10000000, "max_ast_nodes": 100000, "max_seconds": null}
~~~

The first three are positive integers; `max_seconds` is null or positive.
The JSON CLI also has `--max-input-bytes` (default 16777216). Duplicate keys,
nonfinite numbers, and non-UTF-8 JSON are rejected. Exhausted resources, Python
recursion/memory limits, and oversized integer serialization are unresolved,
not mathematical negatives. Limits are cooperative, not process isolation.

## Types and Literal Values

Base types: `Bool`, `Nat`, `Atom`, `Pos`, `Letter`, `Block`, `Partition`,
`Origin`, `AbsRecord`. Type constructors:

~~~json
["Prod", "Nat", "Bool"]
["List", "AbsRecord"]
["Option", ["Prod", "Pos", "Block"]]
~~~

Values are type-tagged internally. Bool, Nat, Atom, and Pos remain different
even if their host-language payloads compare equal. Literal JSON encodings:

| Type | Value |
|---|---|
| Bool / Nat | JSON boolean / nonnegative integer, no coercion |
| Atom / Pos / Letter | Declared atom label / position / `"p"` or `"d"` |
| Block | Array of distinct declared atom labels; order is immaterial |
| Prod(T,U) | Array of exactly two values |
| List(T) | Array of values of T, retaining order |
| Option(T) | `null` or `{"some": value}` |
| Partition | Array of `[position, block]`; nonempty disjoint blocks cover all atoms; positions distinct |

Partitions are canonicalized by position, blocks by declared atom enumeration.
Record fields (JSON objects use exactly these names):

~~~text
Entry     = Prod(Pos, Block)
Origin    = {label: Letter, parents: Prod(Entry, Entry), target: Pos}
AbsRecord = {carrier_at: Pos, carrier: Block, partner_at: Pos,
             partner: Block, target: Pos, merged: Block, label: Letter}
~~~

Records constructed as pure values do not manufacture registered log events.
Actual events used by the causal reads always come from the generated log.

## Constructors

Below e, l, z, and b denote expression objects, not executable strings.

| kind | Other required keys | Type rule |
|---|---|---|
| literal | type, value | Literal has the declared valid type |
| var | name | Must be bound in the lexical context |
| query | name | One of the four reads below |
| pair | left, right | Product of operand types |
| fst / snd | value | First / second product component |
| if | condition, then, else | Bool condition, equal branch types |
| fold | list, seed, acc, item, body | List(T), seed U; acc:U,item:T |- body:U |
| op | name, args; modulus only for mod | Pure operation table below |
| record | type, fields | Origin or AbsRecord, exact field names/types |
| field | value, name | Declared record projection |
| list | element_type, items | Finite homogeneous expression array |
| some | value | Option of value type |
| none | element_type | Empty Option of declared type |
| case | value, none, binder, some | Option(T); binder:T in some branch; equal branch types |

Fold is chronological **left** fold. It evaluates its list and seed once,
then evaluates the body at each item with the current accumulator. Bindings
are lexical; nested terms may capture outer variables or shadow them. acc
and item must be different identifiers. A fold body may also read the four
current causal queries; this is not an automatic incremental-fold claim.
All branches are statically checked, even if a conditional never selects one.
Composition, finite map/filter, and tuples are ordinary syntax expansions,
not calls to arbitrary external functions. General recursion is absent.

The only query names and result types are:

~~~text
CurrentPartition   : Partition
SelectedBlock      : Block
OriginSnapshot     : Origin
AbsorptionSequence : List(AbsRecord)
~~~

No query reads raw words, clocks, latest unrelated events, another consumer's
success, or an alternate history. The saturation engine's predecessor words
are for witness production only and are not accessible to expressions.

## Pure Operations

Every `op` uses an `args` array, with exactly the following signatures:

~~~text
eq            : (T,T) -> Bool
not           : Bool -> Bool
and, or       : (Bool,Bool) -> Bool
add           : (Nat,Nat) -> Nat
lt, le        : (Nat,Nat) -> Bool
mod           : Nat -> Nat             [positive literal integer modulus]
union,
intersection  : (Block,Block) -> Block
subset        : (Block,Block) -> Bool
cardinality   : Block -> Nat
cons          : (T,List(T)) -> List(T)
lookup        : (Partition,Pos) -> Option(Block)
entries       : Partition -> List(Entry)
carrier       : (Partition,Block) -> Option(Entry)
f_p, f_d      : Pos -> Pos
~~~

`carrier` returns None if there is not exactly one containing entry. `lookup`
returns None at a missing coordinate. These are ordinary Option values,
not disabled commands. `mod` has the extra `modulus` key; the modulus is not
an expression and must be positive. There is no Nat/Pos/Atom coercion.

For example, a count report is a genuine fold expression:

~~~json
{
  "kind": "fold",
  "list": {"kind": "query", "name": "AbsorptionSequence"},
  "seed": {"kind": "literal", "type": "Nat", "value": 0},
  "acc": "count",
  "item": "record",
  "body": {
    "kind": "op", "name": "add",
    "args": [{"kind": "var", "name": "count"}, {"kind": "literal", "type": "Nat", "value": 1}]
  }
}
~~~

`q2_examples.py` builds the nine pre-existing control specifications entirely
as JSON data. Its Carry/Absorb guards fold over all packet entries and compare
their actual action targets with the selected carrier's target. Thus Carry
does not incorrectly mean that no unrelated fusion occurs elsewhere.

## Decisions and Replay

`check` explores the independent log state to closure, computes the generated
causal image, and checks R/G/T globally in that priority order. R compares
all reports on each q fiber; G compares each guard; T compares next q for
commonly enabled commands. An incomplete run returns `UNRESOLVED_LIMIT`,
without an exact-domain claim or rejection witness.

A failure contains `witness.clause` and `witness.left/right`. Each side carries
the actual raw word, all four causal reads, typed q/report values and guard
values. T additionally carries the word extended by the named actual letter
and its next q. All are recomputed by `verify_rejection` from seed and the
same F. A modified payload is not trusted, including Bool/integer substitution.

Rejection replay shares the declared types and expression interpreter but
does not import producer updates, decoding, saturation, or decision logic.
It verifies a concrete separation only; its result explicitly says
`domain_completeness_verified: false`. No state ID, serialized forest, or
asserted success flag replaces a real history. A valid rejection is not a
SOFRS report, promotion receipt, or proof of the all-parameter mathematics.
