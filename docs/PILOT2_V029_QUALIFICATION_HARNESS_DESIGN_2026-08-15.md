# Pilot 2 v0.2.9 Qualification-Harness Disposition

- **Status:** Gate 1A design proposal; implementation and execution locked
- **Date:** 2026-08-15
- **Controlling plan:** `PROJECT_RECHERCHE_OPERATIONAL_IOC_PLAN_2026-08-15.md`
- **Scope:** the five preserved historical-state conflicts only

## 1. Decision and authority boundary

This disposition **does require v0.2.9**. It adds a new, forward-only
qualification-harness contract and aggregate result semantics. It does not
amend v0.2.8, reopen any terminal attempt, or reinterpret the preserved 341/5
v0.2.8 result as a PASS.

Gate 0 was accepted by the owner on 2026-08-15. That acceptance authorizes this
design only. This document does not authorize source implementation, test
execution, data-root access, context construction, manifests, freezes, audit,
science, observed data, or IOC-harness work.

Gate 1A entered at Git commit
`d5a4c1c01ca257db4d2d1c08011c77140e6126a5`, tree
`42bd20f46f5a53e8f529f7f3c6dfd1c651500582`, with no Pilot 2 or pytest process
active. Its authority inputs are:

- controlling-plan SHA-256:
  `63e1975923c9ec54e95d447ae833b6dee69ac5a2a0c68c8e16a66b7308b1bb40`;
- v0.2.8 turnover SHA-256:
  `2ba56db02dd018a988172c096674dc77df4dd75f0c0913d8c3a4514e6403ad96`;
- v0.2.8 validation-record SHA-256:
  `cca76a534f5b41ba812c0798a31ce634af218d5e6e670e07610964e67703d5f5`.

## 2. Exact conflict ledger

The historical-contract set `H` is exactly these five currently collected node
IDs. `.pytest_cache` is not an authority source; these routes are fixed by this
design and must also be found by live collection.

| Route | Exact pytest node ID | Historical contract | Required current-tree drift witness |
|---|---|---|---|
| `HIST-V022-01` | `tests/test_pilot2_injection_runner_v022.py::test_execution_lock_precedes_predecessor_and_context_loading` | The v0.2.2 gate is locked before predecessor or context loading. | The later execution freeze makes the gate non-locked; the hash-bound locked assertion fails for that cause. |
| `HIST-V022-02` | `tests/test_pilot2_injection_runner_v022.py::test_zero_case_dry_run_executes_no_science` | The pre-authorization zero-case dry run passes with `execution_gate_locked=true`. | The dry run remains zero-science but returns failure because that one gate criterion is false. |
| `HIST-V022-03` | `tests/test_pilot2_injection_runner_v022.py::test_implementation_freeze_is_hash_bound_and_execution_locked` | Implementation and readiness pass while execution remains locked. | Implementation and readiness still pass, but the later execution freeze makes the final locked assertion fail. |
| `HIST-V027-01` | `tests/test_pilot2_injection_runner_v027.py::test_absent_execution_freeze_never_loads_predecessors_or_context` | With no v0.2.7 execution freeze, neither predecessor nor context loading is reached. | The later execution freeze advances to the deliberately trapped predecessor-loading path. |
| `HIST-V01-01` | `tests/test_release.py::test_initial_v01_release_freeze_is_self_consistent` | The initial v0.1 release tree matches its frozen repository ledger. | The unchanged verifier reports only the later `README.md` hash drift, so its PASS assertion fails. |

No sixth route may be inferred, configured, or accepted without a new design
version and owner approval.

### Cause-exact drift signatures

Before classification, every path already tracked in the Gate 1A tree must
retain its exact Git mode and blob. The prospective candidate may only add the
Gate 0 plan, this design, the authorized v0.2.9 files in Section 9, and new
validation evidence. The structured current-tree signatures are then exactly:

| Route | Pytest phase and kind | Required structured signature |
|---|---|---|
| `HIST-V022-01` | `call`, `AssertionError` | Source `tests/test_pilot2_injection_runner_v022.py:237`; expression `assert gate["status"] == "locked"`; observed `fail`; expected `locked`. |
| `HIST-V022-02` | `call`, `AssertionError` | Source `tests/test_pilot2_injection_runner_v022.py:249`; expression `assert result["status"] == "pass"`; observed `fail`; expected `pass`; the exact current v0.2.2 execution freeze is present and the snapshot freeze is absent. |
| `HIST-V022-03` | `call`, `AssertionError` | Source `tests/test_pilot2_injection_runner_v022.py:262`; expression `assert verify_execution_gate()["status"] == "locked"`; observed `fail`; expected `locked`. |
| `HIST-V027-01` | `call`, `_pytest.outcomes.Failed` | Exact message `predecessors loaded before authorization`; the exact current v0.2.7 execution freeze is present, the snapshot freeze is absent, and no context sentinel is reached. |
| `HIST-V01-01` | `call`, `AssertionError` | Source `tests/test_release.py:14`; expression `assert result["status"] == "pass"`; observed `fail`; expected `pass`; a direct comparison of the unchanged initial-release ledger has mismatch set exactly `["README.md"]`. |

The observer constructs this signature from `TestReport.when`, outcome,
exception kind, repository-relative `reprcrash` location, exact assertion
expression/operands or `pytest.fail` message, and the route state predicate.
Normalization may only convert line endings to LF, remove ANSI control bytes,
and replace the already verified current/snapshot absolute root with its
repository-relative form. It may not remove a line number, exception kind,
assertion value, message, or additional mismatch. A parse failure is not an
equivalent signature.

## 3. Immutable snapshot provenance

Historical contracts run from complete Git trees, not reconstructed source
fragments and not edited copies.

| Contract | Main-line provenance commit | Exact tree | Required provenance relation |
|---|---|---|---|
| v0.2.2 pre-authorization | `cc7ae9dde3a556e2481e227239b7c1fd5055df66` | `e80c980f40efddf8cda692e2bfe9304d362900d8` | Its child `b46d799f03337ead02d2a36cb6a4542e6de88692` adds only `protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.2.json`. |
| v0.2.7 pre-authorization | `5e993e138c409b92dcc326da988c8610e957c58f` | `9f3d39bc24749a9000d0a524f1a496dd1bedc1e3` | Its child `90627cec0b5258ed04a000559b4210087ccdddac` adds only `protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.7.json`. |
| initial v0.1 release | `6f6d0c5572b51b9c6f010be0a1df56312514dd31` | `56df442a58c51c4a126628fdc15fa0c7c75f82d9` | The commit is on the current main-line ancestry and carries the exact initial-release tree. |

The parallel v0.1 provenance commit
`99fa2e932134a53a18adb52f901a9ccecc502da1` has the same tree but is not the
main-line binding.

Required byte bindings are:

| Contract | Test SHA-256 | Runtime/verifier SHA-256 | Additional state binding |
|---|---|---|---|
| v0.2.2 | `b7151dd7c70949c18efcd9a02905a989ab8475cbf24ac8fb9b24a0fcc4000658` | `57f93c591bb5158e475a4a380d8ae7c0dab2a6d9758b32ff150e650f2d2da927` | Snapshot execution freeze absent; current freeze present with SHA-256 `9e247d3d3c2eba0edc936b2db778683257ae5888c1bd581f682dc074ba768d03`. |
| v0.2.7 | `1938ca7618e86ca8377970dcacde63d21dd2bb14228d45c5ad0fb93ff224bc46` | `b9fbd1ed53ffa39baee1a1141d302a615fafd008e02de13575e2915869e33c3d` | Snapshot execution freeze absent; current freeze present with SHA-256 `8c45fe999b0c871d0cc383d47829aa175863a08d25bf00afef29f043f5dba5f8`. |
| v0.1 | `7b75b4499961e2d16c0e4f2be72f5ec6dec1f91bb0f0a8fdccd908ef198fe011` | `9fdbe50cbcbfbf1fddc213dcc471b8342e2456dda22ee2f14dd85a7b415d73ec` | Freeze SHA-256 `95486696ad1a689e49490afbe7d1891fdfe09e093e9aaec7448cc6214d127eb8`; snapshot README `59c3d04c3bcd707df6ddb9337b76b0a027d17883a8b67ba6638f5c5f9b4f6c69`; current README `2ee518cd58f5f57485b647f33e7035bd1864051972856573277632c4754ac963`. |

All three trees and the Gate 1A current tree share `pixi.toml` SHA-256
`b4d190ee09a878c93ae5e3e74bd3ca630754b9343ba7f62d5b52f4d32f5c1613`
and `pixi.lock` SHA-256
`7412baa7d224dfdc419066b706f27257684931df9a0ad0f57949e1fe31cf68c8`.

### Snapshot-fixture equivalence rule

The implementation must read the local Git object database without changing
branches, tags, the index, or worktrees. For each snapshot it must:

1. verify the named commit, its tree, its ancestry, and the stated child delta;
2. materialize the complete tree into a fresh system temporary directory;
3. prove tracked path, mode, Git blob, and route-bound SHA-256 parity before use;
4. use the snapshot's absolute `src` path as the only Project Recherche source
   path for that lane; and
5. prove all tracked bytes are unchanged after the lane.

A missing object, mismatched path/mode/blob/hash, extra or missing tracked file,
or unavailable local tree is `FAIL_SNAPSHOT_IDENTITY`. The harness must not
fetch from a network or substitute a hand-authored fixture. Any proposed exact
fixture fallback requires a new Gate 1A amendment.

## 4. One governed command

The only operator command is:

```text
PYTHONPATH=src pixi run --as-is python -m pulsar_pilot.pilot2_qualification_harness_v029 qualify
```

It accepts no node, snapshot, data-root, output, allow-failure, or arbitrary
pytest arguments. In particular, `-k`, `-m`, `--deselect`, user node IDs, and
snapshot overrides are forbidden.

The formal qualification command requires a clean, committed prospective
v0.2.9 candidate and its already provisioned, hash-bound Pixi environment.
`--as-is` forbids environment installation and lockfile update; an absent or
incomplete environment fails before qualification and must not trigger network
access. The command records the exact HEAD, tree, interpreter, Python, Pixi,
pytest, `pixi.toml`, and `pixi.lock` identities. It clears `PYTEST_ADDOPTS`,
`PYTEST_PLUGINS`, and `RECHERCHE_DATA_ROOT`; disables third-party plugin
autoload, pytest cache, and bytecode writes; and places basetemp, the
observation-only hook output, and all snapshot fixtures outside the repository.
Repository pytest configuration remains authoritative. Disposable-fixture
acceptance uses this same absolute interpreter; it may not provision another
environment.

The harness launches pytest only. It does not import or call a Pilot 2 runner,
executor, context constructor, or science entry point. No historical lane may
resolve a current Project Recherche package by import-path accident.

Collection has a 120-second deadline, the complete current lane a 900-second
deadline, each historical lane a 120-second deadline, and the entire governed
command a 1,800-second deadline. There are no retries. On a lane deadline, the
harness terminates the subprocess group, waits at most five seconds, kills any
survivor, retains partial stdout/stderr and the last complete observer record,
and returns `FAIL_TEST_TIMEOUT`. A signal, operator interrupt, or missing
terminal record never becomes PASS.

## 5. Execution lanes and exact accounting

Let `C` be the exact, sorted live collection of the complete current test suite,
and let `H` be the five routes in Section 2.

1. **Collection lane.** Collect `C` with a structured, observation-only pytest
   hook. Record its count and SHA-256. Require every member of `H` exactly once.
2. **Current lane.** Run the complete current suite once, with no selection or
   deselection. Every node in `C` must produce one terminal raw outcome.
3. **Historical lanes.** Run the three v0.2.2 nodes in the v0.2.2 tree, the one
   v0.2.7 node in the v0.2.7 tree, and the one v0.1 node in the v0.1 tree.
4. **Classification.** A node in `C - H` must pass current state. Each node in
   `H` must have both its exact cause-specific current failure and a PASS in its
   bound historical tree.
5. **Aggregate.** The primary qualification partition is `(C - H)` evaluated
   current plus `H` evaluated historically. Its union must equal `C`, its two
   sets must be disjoint, and every node must be counted exactly once. The five
   current failures are retained as additional drift-witness observations, not
   hidden and not counted twice in the primary partition.

The raw current pytest exit is expected to be nonzero only because its failure
set is exactly `H`. The governed command returns zero only when the aggregate
status is `PASS`.

For the known preserved baseline this yields the semantic form below; `N` is
live-collected rather than frozen at the prior count of 346 because v0.2.9 adds
new harness tests:

```text
current raw:              N - 5 pass, 5 exact archival-drift failures
historical raw:           5 pass
primary accounted:        N
unaccounted:              0
duplicate primary routes: 0
qualification failures:   0
archival drift witnesses: 5
aggregate:                PASS
```

## 6. Machine-exact status taxonomy

Successful observation statuses are exactly:

- `PASS_CURRENT`
- `PASS_HISTORICAL_CONTRACT`
- `PASS_ARCHIVAL_DRIFT_DETECTED`

Fail-closed statuses are exactly:

- `FAIL_CURRENT_TEST`
- `FAIL_HISTORICAL_CONTRACT`
- `FAIL_DRIFT_NOT_EXACT`
- `FAIL_SNAPSHOT_IDENTITY`
- `FAIL_ENVIRONMENT_IDENTITY`
- `FAIL_COLLECTION_DRIFT`
- `FAIL_UNACCOUNTED_NODE`
- `FAIL_DUPLICATE_ROUTE`
- `FAIL_UNKNOWN_ROUTE`
- `FAIL_TEST_SKIP`
- `FAIL_TEST_XFAIL`
- `FAIL_TEST_XPASS`
- `FAIL_TEST_ERROR`
- `FAIL_TEST_TIMEOUT`
- `FAIL_TEST_SIGNAL`
- `FAIL_INCOMPLETE_REPORT`
- `FAIL_AMBIENT_OPTION`
- `FAIL_REPOSITORY_CHANGED`
- `FAIL_ZERO_SCIENCE_BOUNDARY`

`PASS_ARCHIVAL_DRIFT_DETECTED` requires the exact node, test/runtime hashes,
snapshot/current state predicate, cause-specific failure signature, and
historical PASS. An arbitrary failure in one of the five nodes is
`FAIL_DRIFT_NOT_EXACT`. Any `FAIL_*` makes the aggregate `FAIL` and the command
nonzero.

The aggregate JSON must retain raw node outcomes, phase, normalized failure
signature, subprocess exit status, stdout/stderr hashes, snapshot and
environment identities, accounting sets, and all boundary counters. Absolute
temporary paths, durations, and timestamps remain in raw evidence but are
excluded from a separately hashed canonical semantic record so independent
temporary-root runs can be compared.

## 7. Preservation and zero-science boundary

- Existing tests, source, README, releases, results, incidents, protocols,
  freezes, and audits remain byte-for-byte unchanged.
- The current suite is run whole; no test is silently omitted or reworded.
- Historical trees are temporary read-only evidence fixtures. Test-created
  caches may exist only outside the repository and are not promoted into a
  snapshot.
- Start and end HEAD, tree, index, tracked bytes, and clean status must match.
- `RECHERCHE_DATA_ROOT` must be absent. The command accepts no external data
  root, especially none under `/Volumes`; its designated writable locations
  are its own system-temp evidence and basetemp directories.
- Network requests, resource acquisition, Pilot 2 operational context
  construction, Pilot 2 qualification cases, science-entry calls, controlled
  or observed artifact loads, and observed-residual reads are prohibited.
  Their aggregate counters must all be zero.
- Hermetic unit tests may perform their already-versioned synthetic random
  draws, fits, or scans entirely inside basetemp. Those are test computations,
  not an authorized Pilot 2 workload; they must not read a controlled/observed
  artifact or cross the external-root or science-entry guards.
- Raw and aggregate records are written to a fresh, non-overwriting system-temp
  evidence directory. Gate 1B closeout may preserve those exact bytes and
  hashes in a new validation record; it may not rerun or repair a failed
  attempt in place.

## 8. Finite Gate 1B acceptance tests

Positive acceptance requires:

1. exact commit/tree/ancestry, single-file authorization-delta, full-tree, file,
   environment, import-path, and five-route identity checks PASS;
2. live collection and an unselected current run cover the same `C`;
3. current raw failures equal `H`, every failure cause matches its route, all
   other current nodes pass, and all five historical executions pass;
4. the primary partition proves `accounted == C`, unaccounted and duplicates
   are zero, and the aggregate returns `PASS` with zero qualification failures;
5. two independent materializations of every historical fixture in disposable
   system-temp roots prove identical tracked-tree identity, import resolution,
   route outcomes, and canonical semantics under the same bound interpreter;
   and
6. start/end repository identity is unchanged and every operational Pilot 2
   workload, science-entry, controlled/observed-artifact, external-root, and
   network counter is zero.

Negative acceptance must inject and reject each of these finite conditions:

1. missing/wrong commit, tree, blob, mode, bound hash, ancestry, or child delta;
2. missing, extra, duplicate, renamed, or unknown historical route;
3. live collection changes between collection and outcome accounting;
4. current nonhistorical failure, or a historical current result that passes,
   skips, xfails, xpasses, errors, times out, is signalled, or has the wrong
   failure signature;
5. historical failure, skip, xfail, xpass, error, timeout, signal, or incomplete
   result;
6. current package leakage into a snapshot lane or environment/lock drift;
7. ambient pytest filtering, deselection, plugin injection, or user override;
8. missing raw output or outcome for any collected node;
9. repository/index/tracked-byte mutation during the command; and
10. data-root configuration, external-path access, network use, Pilot 2 science
    entry, operational case execution, controlled/observed-artifact load,
    operational context load, or observed-data read. Hermetic synthetic unit
    computations remain permitted only within the boundary above.

Acceptance tests use fake/local repositories and system temporary directories.
They may not access a real data root or execute a scientific workload.

## 9. Prospective Gate 1B implementation surface

If this design is separately approved, Gate 1B may add only:

- `src/pulsar_pilot/pilot2_qualification_harness_v029.py`;
- `src/pilot2_qualification_pytest_observer_v029.py`;
- `tests/test_pilot2_qualification_harness_v029.py`; and
- new v0.2.9 validation evidence produced after the acceptance suite and
  governed command complete.

The exact route registry belongs in the versioned harness source; it is not a
resource, environment, execution, or science manifest. The named top-level
observer is copied byte-for-byte into an isolated temporary observer directory
so a historical lane can use only its snapshot-local Project Recherche
package. No other helper and no v0.2.8 runtime port, refactor, or expansion is
authorized.

## 10. Non-goals and stop rule

This design does not remediate scientific code, alter the 344-case inventory or
thresholds, construct real context, bind resources, create a manifest or
freeze, conduct an audit, access a data root, configure a Mac mini or NAS,
implement the minimalist IOC harness, run a synthetic qualification, inspect
observed residuals, or authorize science.

**Gate 1A stops with this document.** No source or test execution follows
without separate owner approval of this exact design. A design ambiguity or
identity mismatch is HOLD, not permission to improvise. Gate 1B, if approved,
stops after repository and disposable-temp validation with zero science and
before real-root access, manifests, freezes, audit, or IOC work.
