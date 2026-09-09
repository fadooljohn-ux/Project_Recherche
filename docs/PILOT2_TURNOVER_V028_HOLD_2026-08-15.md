# Project Recherche Pilot 2 turnover — v0.2.8 HOLD

Captured: 2026-08-15, Asia/Taipei

Program: Project Recherche / Neutron Star Program / Pilot 2 B1937+21

Purpose: context-reset handoff for a new conversation in this project

Status: **v0.2.8 implementation candidate on HOLD; all execution locked**

## 1. Mandatory instruction for the new conversation

Read this document completely before proposing or performing work. Begin with
the read-only startup checks in Section 14, then restate:

1. the repository identity and whether it matches this turnover;
2. the current gate and the single active blocker;
3. what is preserved, what is locked, and what would require new authority; and
4. one bounded proposed next stage.

Do not infer authority from this turnover, an old `next_gate` field, an audit
PASS, a prior execution authorization, or the existence of a runner command.
This document is an orientation and routing record only.

Work only in `.`. Do not
route work from UI grouping, another workspace, or unrelated project context.

## 2. Repository identity before the turnover-only commit

| Field | Verified value |
|---|---|
| Repository | `.` |
| Branch | `agent/pilot2-v028-design` |
| HEAD | `bde6464530df15e6ecc835a89135efef827d677a` |
| Tree | `c4f17c4e022c6c1f832741747ed8546f1f62078b` |
| Upstream | `origin/agent/pilot2-v028-design` |
| Upstream commit | `bde6464530df15e6ecc835a89135efef827d677a` |
| Ahead/behind | `0/0` |
| Worktree | Clean before this document was added |
| Tag at HEAD | None |
| Matching Pilot 2 process | None found during the turnover check |

No external data root was inspected. No test, context construction, random
draw, fit, scan, science case, observed-data action, or runner execution was
performed while preparing this turnover.

## 3. Current state in one paragraph

v0.2.8 has a frozen zero-science design and a committed implementation
candidate. Its 34 focused controls passed, and two independent temporary-root
dry runs each passed all 13 criteria with every science counter at zero. The
full repository suite is nevertheless HOLD at 341 passed and 5 failed because
preserved historical tests conflict with later immutable repository state.
There is no v0.2.8 implementation freeze, readiness freeze, execution freeze,
runtime resource manifest, runtime environment manifest, real-root context
preflight, independent release audit, or science authorization. The live
repository gate reports `locked` and does not load predecessors.

Do not collapse these distinct claims:

- the controls are implemented;
- the focused controls passed;
- the implementation is not qualified;
- the package is not frozen or audited; and
- nothing is executable.

## 4. Two-stage North Star

Stage 1 is one valid, independently audited, frozen **344-case synthetic
science qualification** for B1937+21. Its declared inventory contains 240 main,
60 phase-reference, 28 annual, and 16 boundary cases, plus 35 deterministic
solver audits and 688 primary fits. Stage 1 requires a terminal audit PASS and
zero observed-residual access.

Stage 2 is Initial Operational Capability on the dedicated Mac mini/NAS setup:
a minimal operator-run, fully offline, single-target harness with controlled
inputs, single-writer execution, health-only monitoring, recovery, and verified
backup/restore. Stage 2 begins only after Stage 1 terminal closeout passes.

Neither stage grants autonomous authorization, survey scope, multi-target
scope, discovery authority, automatic unblinding, or permission to rerun a
terminal failure.

Use these exact phrases to prevent ambiguity:

- `344-case synthetic science qualification`;
- `zero-science real-root context preflight`; and
- `observed-data search`.

Do not request authorization for an unspecified “science run.”

## 5. Evidence precedence and stale-routing warning

For current routing, use this order:

1. this turnover document;
2. `docs/PILOT2_V028_REPOSITORY_TEMPORARY_VALIDATION_2026-08-11.md` and its
   JSON record for the current gate evidence;
3. `docs/PROJECT_RECHERCHE_TWO_STAGE_ROADMAP.md` for the North Star and
   non-negotiable rules, excluding its stale final current-position paragraph;
4. the frozen v0.2.8 design for its requirements, excluding its already
   consumed implementation `next_gate`;
5. the active-lineage index for historical dispositions and inventory lineage,
   excluding its stale v0.2.8 current-state paragraphs; and
6. all older documents as immutable evidence, never as current authorization.

The following statements are stale but preserved:

- `README.md` says v0.2.8 implementation remains unauthorized;
- `docs/release-index/PILOT2_ACTIVE_LINEAGE.md` says v0.2.8 is design-only and
  no v0.2.8 source or tests exist;
- the roadmap places the project before S1-M0;
- the historical science-stage North Star still routes toward v0.2.7; and
- the v0.2.8 config and candidate report name repository/temporary validation
  as the next gate even though that validation is complete.

Do not rewrite hash-bound evidence merely to make its prose current. This
turnover supersedes only those live-routing statements, not their historical
content or hashes.

## 6. Immutable release lineage

| Version | Preserved disposition | Consequence |
|---|---|---|
| v0.2.1 | Terminal scientific hard stop | No rerun or regrade; retained results are predecessors only |
| v0.2.2 | Terminal implementation crash after one consumed attempt | Entire v0.2.2 case/seed namespace remains retired |
| v0.2.3 | Never executed; Sol HOLD | Its exact 344-case inventory is unconsumed and may carry forward unchanged |
| v0.2.4 | Never executed; Sol HOLD | Preserve audit evidence; no cases consumed |
| v0.2.5 | Never executed; Sol HOLD | Preserve audit evidence; no cases consumed |
| v0.2.6 | Never executed; Sol HOLD | Preserve audit evidence; no cases consumed |
| v0.2.7 | Terminal startup failure at 0/344 | Never resume, repair, rerun, retune, reroll, replace, or regrade |
| v0.2.8 | Committed implementation candidate; validation HOLD | Preserve the candidate and HOLD evidence; no freeze, preflight, or execution |

The active successor inventory SHA-256 is
`811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`.
No member of this v0.2.3-derived inventory was consumed by v0.2.3 through
v0.2.8. The independent v0.2.2 namespace remains retired.

Historical protocols, freezes, source, tests, audits, incidents, results, and
terminal records are evidence. Do not clean up, rename, move, deduplicate,
modernize, or delete them. Some historical modules are also live dependencies.

## 7. v0.2.8 implementation map

The candidate introduced these forward-only controls:

- `pilot2_trusted_data.py`: duplicate-rejecting JSON/YAML and exact types;
- `pilot2_offline_resources.py`: local manifests, resource tracing, and network
  denial/counting;
- `pilot2_release_contract.py`: exact design, remediation, implementation,
  readiness, audit, execution, root, environment, and predecessor bindings;
- `pilot2_durable_ledger.py`: exact state machine, terminal verification,
  durable writes, artifact checks, and OS single-writer lock;
- `pilot2_runtime_core.py`: context, recovery, annual-mask, heartbeat, and
  prospective execution mechanics;
- `pilot2_injection_runner_v028.py`: version identity, locked CLI, candidate
  report, and temporary-root dry run;
- `pilot2_injection_executor_v028.py`: thin v0.2.8 record identity; and
- `tests/test_pilot2_controls_v028.py`: focused negative and recovery tests.

The runtime core intentionally imports historical v0.2.2 grading helpers,
v0.2.3 inventory/executor logic, and v0.2.7 record validators. Those modules
must not be refactored in place. Do not create another copied runner stack to
solve the current blocker.

## 8. Current validation scorecard

| Gate | Outcome |
|---|---|
| Strict JSON/YAML and exact schemas | PASS |
| Science-control hash binding | PASS |
| Audit/root/launch/predecessor binding tests | PASS |
| Ledger, terminal, annual-mask, recovery, and writer-lock tests | PASS |
| Offline manifest, trace, and network-denial tests | PASS |
| Focused v0.2.8 suite | PASS — 34/34 |
| Independent temporary roots | PASS — 2/2, each 13/13 |
| Cases, draws, fits, and scans | PASS — all zero |
| External-root and observed-data access | PASS — none |
| Full repository suite | HOLD — 341 passed, 5 failed, 0 deselected |
| Repository execution gate | LOCKED |
| Real-root context preflight | NOT AUTHORIZED / NOT RUN |
| Resource/environment manifests | ABSENT |
| Implementation/readiness/execution freezes | ABSENT |
| Independent release audit | NOT RUN |
| Science execution | LOCKED / NOT RUN |

Candidate implementation SHA-256:
`28410aca9032ce5cf77e8243482607f72ebf2aff99b877e8e8b63d36ec46a523`

Candidate science-control SHA-256:
`433b30c70eae51aec1f2149dff4de4a5a128b09458d7f34ee57906b2a8a227d5`

## 9. The single active blocker

The frozen v0.2.8 design requires one current full-suite command to pass with
zero failures and no ad hoc deselections. The current command produces five
historical-state conflicts:

- three failures in `tests/test_pilot2_injection_runner_v022.py`, whose
  historical tests assume the later v0.2.2 execution freeze is absent;
- one failure in `tests/test_pilot2_injection_runner_v027.py`, whose historical
  test assumes the later v0.2.7 execution freeze is absent; and
- one v0.1 release-verifier failure because current `README.md` differs from
  its historical frozen hash.

These failures must not be “fixed” by editing the frozen tests, reverting the
README to an obsolete state, weakening assertions, monkeypatching the suite
globally, or hiding tests through ad hoc deselection. The 341/5 result is not
readiness evidence.

No v0.2.9 document, code, or commit exists at turnover.

## 10. Proposed next bounded stage — not yet authorized

The recommended successor is a small, forward-only, zero-science disposition,
presumptively v0.2.9, limited to the qualification-harness conflict.

Its design objective should be one governed command that accounts for every
test without altering frozen evidence:

1. run current qualification tests against current state;
2. run historical-contract tests against their immutable historical snapshots
   or equivalent exact fixtures;
3. treat intentional historical drift detection as an expected archival
   outcome rather than a current-release failure; and
4. produce one aggregate zero-failure record with no test silently omitted.

Before implementation, the new conversation should propose a short design and
explicit acceptance criteria. It must decide whether this requires v0.2.9 and
explain the evidence-preservation boundary. Do not port, refactor, or expand
the v0.2.8 runtime unless the harness design proves it necessary.

This stage ends after repository and disposable temporary-root validation. It
does not include `/Volumes`, controlled science inputs, context construction,
resource acquisition, manifests derived from a real root, freezes, audit,
science, observed data, or IOC work.

## 11. Remaining Stage 1 sequence after the blocker

Each item requires its own satisfied entry gate and clearly stated authority:

1. successor repository/temporary-root validation passes;
2. separately authorized zero-science real-root context preflight passes twice
   under network denial, producing exact resource/environment manifests;
3. implementation and readiness freezes are created;
4. one conservative read-only Sol audit of the exact frozen commit passes;
5. a separate execution freeze binds the full package, root, environment,
   audit, launch, monitoring, and backup evidence;
6. the user explicitly authorizes that exact 344-case synthetic qualification;
7. the run executes once in a managed session with health-only monitoring; and
8. a read-only terminal audit closes Stage 1.

An audit is advisory and never an authorization. No Fable dependency is part
of this path. Use Sol audits conservatively at release/milestone gates, not as
a routine loop after every implementation turn.

## 12. Authorization semantics

The user uses `Proceed` as authorization for the next stage that Codex has
explicitly laid out. There is no hidden ritual or special wording requirement.
The practical boundary is therefore the stated stage itself:

- if the stated next stage is design-only, `Proceed` authorizes design only;
- if it is zero-science implementation, `Proceed` does not authorize science;
- if a ready and fully gated execution stage is explicitly stated, `Proceed`
  can authorize that stated stage; and
- a failed entry gate stops the stage even when later work was conditionally
  authorized.

Every handoff response must end with a scorecard and the next bounded stage so
the meaning of a future `Proceed` remains unambiguous.

## 13. Anti-spiral operating rules

1. Keep one active blocker at a time. The current blocker is the test harness.
2. Map every new control to a named open finding or acceptance criterion.
3. Do not add orchestration, services, launch agents, dashboards, NAS design,
   or IOC features during the current Stage 1 blocker.
4. Do not produce another copied version stack. Prefer the smallest
   forward-only harness or declarative record.
5. Do not reopen already passing v0.2.8 controls without evidence of a defect.
6. Do not convene repeated audits during routine implementation. Audit once at
   the stated milestone.
7. Treat a failed gate as evidence. Stop, record it, and propose a successor;
   do not quietly weaken, rerun, retune, or reinterpret it.
8. Keep the next design short: one problem statement, one bounded solution,
   explicit non-goals, acceptance tests, and a stop rule.
9. End each turn with: changed state, scorecard, unresolved blocker, and one
   explicit next stage.
10. If work no longer moves the North Star measurably, stop and ask the user
    before expanding scope.

## 14. Read-only startup checklist

Run only from the repository root:

```bash
pwd
git status --short --branch
git rev-parse HEAD
git rev-parse HEAD^{tree}
git rev-parse origin/agent/pilot2-v028-design
pgrep -fl 'pilot2|pulsar_pilot' || true
```

The implementation baseline before this document is
`bde6464530df15e6ecc835a89135efef827d677a`; its tree is
`c4f17c4e022c6c1f832741747ed8546f1f62078b`. The current HEAD may be exactly
one later turnover-only commit. If so, verify that its only changed path from
the baseline is this document:

```bash
git diff --name-status \
  bde6464530df15e6ecc835a89135efef827d677a..HEAD
```

Any other difference must be explained before work proceeds.

Verify the live repository gate without supplying a data root:

```bash
PYTHONPATH=src pixi run python \
  -m pulsar_pilot.pilot2_injection_runner_v028 verify-gate
```

Expected status: `locked`. Expected failures: absent v0.2.8 implementation,
readiness, and execution freezes. Expected `predecessors_loaded`: `false`.

Confirm the still-absent prospective artifacts:

```bash
test ! -e protocol/PILOT2_RUNTIME_RESOURCE_MANIFEST_v0.2.8.json
test ! -e protocol/PILOT2_RUNTIME_ENVIRONMENT_MANIFEST_v0.2.8.json
test ! -e protocol/PILOT2_INJECTION_RUNNER_FREEZE_v0.2.8.json
test ! -e protocol/PILOT2_INJECTION_EXECUTION_READINESS_FREEZE_v0.2.8.json
test ! -e protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.8.json
```

Do not set a data-root variable, inspect `/Volumes`, invoke the runner's `run`
command, or rerun the full suite merely to rediscover the recorded five
failures during initial orientation.

## 15. Authoritative file hashes

| File | SHA-256 |
|---|---|
| `docs/PROJECT_RECHERCHE_TWO_STAGE_ROADMAP.md` | `47d6d7fdc2983ddf66b230522753faa189e00e92d86c68bdc5db8e2515bb9dc7` |
| `docs/audits/TOP_DOWN_ASSEMBLY_AUDIT_2026-08-11.md` | `a90b7d57d7ad804507293156e3ff87f3588e4e791564f9628d1148398b27d9b3` |
| `results/pilot2/top_down_assembly_audit_2026-08-11.json` | `0838898236f7a7927604b3efdaacdae2b467516441808e7b8e1c74b503f15614` |
| `docs/REPOSITORY_REDUNDANCY_REGISTER_2026-08-11.md` | `34839f43976c82dbaf33adaeb720c762ae2f974d9f30a370524ab59fdc33865d` |
| `protocol/PILOT2_INJECTION_REMEDIATION_DESIGN_FREEZE_v0.2.8.json` | `762e0bbb9c3c9cff377390d3932242752ff926e658c0e989e8fc3daaffa44f7f` |
| `docs/PILOT2_V028_REPOSITORY_TEMPORARY_VALIDATION_2026-08-11.md` | `cca76a534f5b41ba812c0798a31ce634af218d5e6e670e07610964e67703d5f5` |
| `results/pilot2/injection_v028_repository_temporary_validation.json` | `d31627defb9c9cf88cb7dbe854883c86168fe0e6af46d16333fe6a9d15a7a487` |
| `docs/incidents/PILOT2_V027_STARTUP_FAILURE_2026-08-11.md` | `d8da24c398c750885a9268c418e18b3eaaaf9d7e3919e85fec0da45bbbff6958` |
| `results/pilot2/injection_v027_startup_failure_audit.json` | `c9d00f3c021091c18722d1a288c91e218f447ce1f9ac3f507dda0b9fdc70ab9d` |

## 16. Paste-ready prompt for the new conversation

> Work only in `.`.
> Read `docs/PILOT2_TURNOVER_V028_HOLD_2026-08-15.md` completely. Perform only
> its read-only startup checks. Do not access an external data root, run tests
> or science, invoke a runner, edit files, or use another workspace's context.
> Report whether repository identity matches, restate the current v0.2.8 HOLD,
> identify the single test-harness blocker, list all locked stages, and propose
> one bounded next stage with entry/exit gates. Wait for my direction before
> changing anything.

## 17. Turnover completion rule

The new conversation has successfully reconstructed context only when it can
state, without contradiction:

- v0.2.8 is implemented but held, not design-only, ready, frozen, audited, or
  executable;
- the five full-suite failures are preservation conflicts, not permission to
  edit or hide historical evidence;
- no real-root preflight or science has occurred under v0.2.8;
- the North Star remains synthetic qualification first and IOC second; and
- the next proposed stage is one small, zero-science, preservation-safe
  qualification-harness disposition requiring fresh user authorization.
