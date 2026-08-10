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

Only fields expressible under the corresponding pinned contracts belong here.
Experimental carrier selection belongs in a RunRequest or extension contract
until the carrier is accepted and versioned in `rime-lite`.
