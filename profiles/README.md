# Compiler And Assembly Profiles

`compiler/` contains Paper X Compiler Report Profile instances. They enter
`Compile_v1` and select eligible compiler items.

`assembly/` contains Paper XII Assembly Profile instances. They enter only
SOFRS assembly and cannot create, remove, duplicate, or retype a normative
CompilerOutput item.

`comparison/` contains explicit Paper XIII comparison-profile fixtures for
runtime examples. A comparison profile is an input to Level 2, not a hidden
producer constant; callers must pass it together with an explicit alignment
artifact.

`gridworld-f4-support-v2.0.json` exercises the generic runtime evaluator with
two already-registered canonical coordinates: direct operator support and
length-two word support. It does not import the published GridWorld Object
Certificate or promote runtime observations to object truth.

The diagnostic analogue compiler and assembly profiles instantiate the
published Paper XII analogue branch. `ai-observable-identity-v2.0.json`
selects the upstream `analogue` coordinate family for two reports with an
explicitly identical probe vocabulary. It compares declared values only and
assigns no CandidateAction, outcome, or causal meaning to
`repair_probe_result`.

Only fields expressible under the corresponding pinned contracts belong here.
Experimental carrier selection belongs in a RunRequest or extension contract
until the carrier is accepted and versioned in `rime-lite`.
