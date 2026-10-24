# Internal Runtime/A0 Engineering Milestone

2026-10-25. **Internal review branch, not a formal release.** No package version,
release tag, GitHub Release, crate publication or production migration is created.
The package remains at its existing declared version; prototype crate/schema
versions describe their own inputs, not a repository release.

## Included Scope

This first source checkpoint includes the previously local dependency chain:
MaleCNS profile/cache/sparse prototypes, Q2 shard controls, offline Solana
projection/replay/source-transition/recovery prototypes, and the two A0 shadows
with the internal shared mechanical library. It includes source, tests, scoped
contracts/plans/readouts, required Cargo.lock files, the tiny synthetic fixture
and selected historical evidence records/indexes.

There are two maintained lanes:

```text
SOF compatibility: Python SDK/CLI, contracts, reports and validation
Rust data runtime: independently scoped offline prototypes and measurements
Shared A0: internal identity / restricted codec / exact flat NTFS inventory
           used by read-only shadows only
```

No SOF carrier/contract changes are required for Solana. No checkpoint approval,
cache permission, mathematical reducer or application PASS moves into A0. Locks,
process execution and publication/retry semantics remain outside the shared core.

## Artifact and Identity Rules

- Do not commit `runs/`, raw captures/carriers/packets, target directories,
  executables, wheels, private configuration or credentials.
- Keep selected old receipts/indexes and executable digest strings byte-for-byte.
  They describe their original source/execution, not this Git commit or a CI run.
- Do not update expected digests to make current source resemble an old producer.
  The old candidate source/binary snapshots remain local prerequisites for their
  full historical replay. They are not silently bundled as a new public package.
- Existing domain JSON remains raw bytes. The restricted A0 codec does not own
  its normalization. Git attributes preserve historical selected result bytes.
- The [SOF byte baseline](../../evaluations/internal-runtime-a0-milestone/sof-compatibility-baseline.json)
  is an explicit projection of the already frozen before capture, not a new test
  receipt. CI compares all 304 protected file identities against it.

The [evidence index](../../evaluations/internal-runtime-a0-milestone/evidence-index.json)
lists retained records and their scope. The
[commit scope](../../evaluations/internal-runtime-a0-milestone/commit-scope.json)
lists the initial checkpoint's proposed paths; it excludes itself from its digest inventory to avoid
self-reference. Git binds the complete committed tree. Neither is a release
manifest, external attestation or a full raw-data archive.

The [local selected-check index](../../evaluations/internal-runtime-a0-milestone/local-checks.json)
records the current Windows-host runs separately from hosted Linux CI. The main
checkout remains clean at the shared base commit. All 303 common protected Git
blobs agree; two main-checkout profile working files have pre-existing CRLF/LF
differences from those blobs. Their bytes are recorded, not normalized in place.
The additional protected path is the tiny synthetic MaleCNS fixture.

The [CI follow-up index](../../evaluations/internal-runtime-a0-milestone/ci-followup.v0.json)
records the later harness-only correction. Initial indexes and failed hosted
evidence remain historical, rather than being overwritten to claim a pass.
The first Windows hosted run correctly refused the runner's default `RUNNER~1`
temporary path alias. CI now creates normal fixtures under a canonical job
output directory; explicit alias-rejection controls and production code remain
unchanged. The ordinary and optimized menus use this same scoped fixture policy.

## CI Gates

| Job/profile | Executed | Explicitly not established |
| --- | --- | --- |
| Linux SOF, Python 3.11/3.13 | Protected byte guard; unchanged SOF unit/conformance/golden/regression suites; original plugin protocol tests; vendored/service/evaluation/matrix checks | A0 NTFS behavior; every new prototype workload; historical large-input replay |
| Linux A0 portable | Shared Rust codec/identity/name tests and compile-fail controls, inspector build, review/CI reporting tests, unsupported-backend refusal | ADS/reparse/handle stability validation; refusing an unsupported platform is not filesystem conformance |
| Windows A0 NTFS | Actual local NTFS preflight, the two synthetic A0 test menus in ordinary/-O modes, ADS/hard-link/junction and kill/change controls within those menus | Local archived 43/27 full-acceptance runs and MaleCNS full-carrier benchmark; these require ignored external/local inputs |
| Linux wheel | Existing installed public SOF workflow | A Rust replacement of the Python runtime or a new runtime release |

Jobs upload fresh selected-check reports and logs. A skipped required test, zero
tests, unavailable NTFS prerequisite or resource interruption cannot produce a
coverage PASS. Wrong-platform NTFS selection fails unresolved instead of silently
skipping. `not_executed` fields retain all out-of-menu/local-data work. Historical
local PASS values are never copied into a new CI execution result.

The remaining prototype suites are committed for local declared use, not
implicitly described as exercised by these selected CI jobs. Windows process
counter attribution is platform-scoped independently of NTFS. No Linux execution
is claimed merely because a Windows-host portable profile succeeds.

## Dependencies and Build Entry

Each Rust prototype carries its Cargo.lock. CI builds/tests use `--locked`;
frozen adapters that intentionally build offline receive a preceding locked
fetch step. No lockfile is regenerated by CI. The shared crate is `publish=false`.

The existing Python package dependency ranges remain unchanged. Shadow CI adds
only the CI-specific pinned `psutil==7.0.0`; this is not a complete transitive
Python/environment lock or hermetic-build claim. Every selected CI profile
records `pip freeze`; Rust/compiler versions remain execution-environment facts.

`python tools/build_rust_plugins.py` retains the stable SOF plugin default.
`--engineering` opts into the Q2 enumerator and MaleCNS census. Other prototypes
are built by their explicit application commands, not registered automatically.

## Review and Promotion

Keep the main checkout untouched. Push a `codex/` internal review branch and, if
opened, use a Draft PR. Source inclusion and CI success are not approval for a
formal release, API stability, a production migration, performance generalization
or B/C extraction. Those decisions require separate review and scope.
