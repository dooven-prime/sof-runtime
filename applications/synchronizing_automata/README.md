# Synchronizing Automata Adapter

This application is the first end-to-end `sof-runtime` vertical slice. It maps
a complete deterministic finite automaton to singleton coordinate sectors and
labelled deterministic transition operators.

The adapter declares a positive-word source alphabet. The rank-collapse extension then
computes the finite closure of images of the full state set under positive
words, the shortest first hit of each rank threshold, and a shortest witness
word. A separate validator recomputes the reachable subset orbit and all first
hits before the result may be retained as checked extension evidence.

## Boundary

Image-rank first-hit depth is an independent extension computed from labelled
words. It is not pairwise word accessibility, routed-product depth, support
graph distance, or Lie/Hall depth. The adapter declares no route or Lie/Hall
capability and the compiler must not infer either one. Until `rime-lite`
accepts a rank-collapse carrier contract, the extension does not produce a
canonical Typed SOF IR or Compiler Output. A successful run instead terminates
in a source-addressed candidate promotion package with explicit exclusions and
carrier-separation statements.

Run the checked example from the repository root:

```bash
sof run rank-collapse examples/automata/cerny4.json --run-dir runs/cerny4
sof validate runs/cerny4/run-response.json
sof validate-promotion runs/cerny4/promotion-package.json runs/cerny4/run-response.json
```

For the declared Cerny four-state fixture, the independently checked shortest
reset depth is 9 and the deterministic reference implementation returns the
word `baaabaaab`.
