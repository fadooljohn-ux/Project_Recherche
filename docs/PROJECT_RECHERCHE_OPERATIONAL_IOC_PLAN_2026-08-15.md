# Project Recherche operational IOC and science-readiness plan

Effective: 2026-08-15, Asia/Taipei

Program: Project Recherche / Neutron Star Program / Pilot 2 B1937+21

Status: **controlling prospective planning document; execution remains locked**

Purpose: guide all future Project Recherche work from the preserved v0.2.8 HOLD
to a barebones operational capability able to conduct separately authorized
science.

## 1. Authority and evidence precedence

This document records the owner's 2026-08-15 amendments and is the controlling
source for prospective architecture, sequencing, scope, and IOC definition. It
is a planning authority, not an implementation freeze, execution freeze, or
science authorization.

Use the following precedence:

1. this document for future planning and the amended IOC definition;
2. `docs/PILOT2_TURNOVER_V028_HOLD_2026-08-15.md` for the current repository
   identity, v0.2.8 HOLD, lineage, and recorded validation state;
3. `docs/PILOT2_V028_REPOSITORY_TEMPORARY_VALIDATION_2026-08-11.md` and its JSON
   record for the current v0.2.8 validation evidence;
4. `docs/PROJECT_RECHERCHE_TWO_STAGE_ROADMAP.md` for preserved requirements that
   are not superseded here; and
5. older releases, freezes, incidents, tests, results, and audits as immutable
   historical evidence, never as current authorization.

This document supersedes the earlier roadmap's prospective definition of IOC as
a separate feature-rich post-qualification infrastructure program. It does not
alter historical bytes or hashes, reopen a terminal attempt, or convert any
recorded HOLD into PASS.

## 2. Owner amendments

The controlling amendments are:

1. IOC is a **barebones minimalist harness plus a scientifically thorough
   science module**.
2. The harness is **AI-supervised but operator-controlled**.
3. Project Trammel is a read-only architectural reference for the minimalist
   harness. Its code, data, release identity, and science are not Recherche
   authority and must not be copied blindly.
4. The program objective is an **operational state able to conduct science**,
   not an indefinitely expanding readiness or hardening program.

These amendments change the destination and the architecture, but not the
preservation rules or the requirement for explicit authority at every material
gate.

### 2.1 Subagent model policy

This model-specific delegation policy controls all future Project Recherche
work and supersedes any earlier prospective subagent-model assignment:

- **Luna subagents are fully authorized with no model-use restrictions.** They
  may be spawned, resumed, delegated to, and given follow-up work without a
  separate model authorization.
- **Terra subagents require explicit owner authorization.** A Terra subagent
  may not be spawned, resumed, delegated to, or given follow-up work unless the
  owner has expressly authorized Terra for the stated bounded stage.
- **Sol subagents are completely unauthorized.** They may not be spawned,
  resumed, delegated to, or given follow-up work for Project Recherche.
- An unknown or unverifiable subagent model fails closed as unauthorized until
  its identity and applicable authority are established.

"Fully authorized" removes only the model-selection approval requirement for
Luna. It does not enlarge the active project stage, grant execution or science
authority, override a stop boundary, or permit a subagent to issue authority.
All subagents remain bound by this plan, the current owner authorization,
preservation rules, operator control, and the active gate. Historical outputs
from models now disallowed remain historical evidence only; they do not
authorize new work.

## 3. Current state and required state

| Item | Current v0.2.8 state | Required state |
|---|---|---|
| Repository candidate | Committed on `agent/pilot2-v028-design` | Preserved; successor work is forward-only |
| Focused controls | PASS — 34/34 | Retain without gratuitous reopening |
| Disposable-root checks | PASS — 2/2, each 13/13 | Retain as evidence; repeat only for a successor |
| Full repository suite | HOLD — 341 passed, 5 failed, 0 deselected | One governed zero-failure accounting command |
| Execution gate | `locked`; predecessors not loaded | Remain locked until all later gates pass |
| Science module | Substantial candidate machinery exists | Exact, identified, thoroughly qualified module |
| Operational harness | Candidate runner/control machinery exists but is not accepted IOC | Minimal foreground operator-run conductor |
| AI supervision | Outcome-free health record is partially defined | One complete read-only operational status contract |
| Real-root preflight | Not authorized and not run | Two authorized zero-science passes under network denial |
| Resource/environment manifests | Absent | Exact, hash-bound, locally reproducible manifests |
| Freezes and independent audit | Absent | Exact implementation/readiness/execution freezes and milestone audit |
| 344-case qualification | Not run under v0.2.8 | One authorized integrated run and terminal audit PASS |
| IOC | Not achieved | Integrated harness plus science module operationally accepted |
| Observed-data science | Not authorized | Separately designed, frozen, audited, and authorized |

The single active blocker at adoption of this plan remains the five historical-
state conflicts in the repository qualification harness. Downstream missing
manifests, freezes, audits, and execution authority are later gates, not reasons
to widen the immediate stage.

## 4. Definitions

### 4.1 Scientifically thorough science module

The science module owns scientific computation and interpretation. It is not
made minimal merely because the harness is minimal. Its qualification baseline
retains:

- the exact unconsumed 344-case B1937+21 inventory: 240 main, 60
  phase-reference, 28 annual, and 16 boundary cases;
- 688 authorized primary timing-model fits and 35 deterministic solver audits;
- TOA-level injection, covariance-aware scanning, complete refitting, and
  frozen recovery diagnostics;
- frequency, amplitude, phase, convergence, absorption, solver-parity, and
  annual astrometric-correlation checks;
- a durable periodwise annual-identifiability mask;
- locked thresholds, unchanged scientific gates, exact denominators, and
  fail-closed grading;
- exact environment, input, resource, calibration, inventory, and predecessor
  bindings; and
- zero observed-residual or observed-periodic-search access during synthetic
  qualification.

The module must expose one versioned runtime identity and one authoritative
entry path used by development qualification, integrated tests, and operational
execution. A hash list alone is insufficient: an end-to-end parity test must
prove that the accepted science construction reaches the real harness without a
mock, alias, retired implementation, or alternative runtime route.

### 4.2 Barebones minimalist harness

The harness is a small foreground conductor. It owns lifecycle and evidence,
not scientific decisions. Its minimum responsibilities are:

1. verify one exact release, authority, root, environment, resources, science
   identity, and frozen workload;
2. run a zero-science preflight before creating a science run root;
3. create one new run identity and refuse reuse of a consumed or terminal one;
4. acquire one local single-writer lock before the first runtime mutation;
5. invoke the single authoritative science-module path;
6. maintain exact case accounting, checkpoint evidence, and create-once events;
7. publish one metadata-only operational status record;
8. handle operator interruption and failures according to the frozen stop rule;
9. seal terminal scientific evidence and create a hashed terminal inventory;
   and
10. exit in one machine-verifiable terminal state.

The target operator surface is finite:

- `verify-gate` — read-only authority and identity check;
- `preflight` — zero-science readiness check;
- `prepare` — create one authorized run identity after preflight;
- `run` — foreground execution; and
- `status` — read-only operational observation.

An explicit `stop` service, dashboard, daemon, scheduler, automatic recovery
plane, or background controller is not required for IOC. The foreground
operator interrupt is the default stop mechanism. A thin display may be added
only if it reads the exact same status contract and does not become a second
control plane.

### 4.3 AI-supervised, operator-controlled

AI supervision is advisory and read-only during a run. It may:

- read the status contract and permitted process metadata;
- report stage, checkpoint, elapsed time, CPU, RSS, heartbeat age, and errors;
- identify a stale heartbeat, stopped process, resource excursion, or declared
  critical failure; and
- recommend that the operator continue observing, stop, or begin an incident
  disposition.

AI may not autonomously:

- issue authority;
- prepare, launch, interrupt, resume, or close out a run;
- alter inputs, thresholds, inventory, configuration, or code;
- inspect sealed scientific outcomes during execution;
- unseal, rerun, retune, reroll, replace, top up, or regrade an attempt; or
- convert an audit or health observation into execution permission.

The operator owns prepare, launch, stop, incident disposition, closeout, and
authorized result review. The owner grants the exact authority for each stage;
the owner and operator may be the same person.

### 4.4 Initial Operational Capability

IOC is achieved only when the integrated pair—scientifically qualified module
plus minimalist harness—can reproducibly accept and complete one separately
authorized, frozen, single-target science workload on the designated macOS
system with:

- exact offline controlled inputs and resources;
- operator-controlled foreground execution;
- AI-readable, outcome-free health supervision;
- single-writer and create-once run identity controls;
- exact accounting and terminal evidence;
- one verified backup/restore boundary appropriate to the run; and
- no silent dependency, science-path, threshold, or configuration change.

The 344-case synthetic qualification is the first integrated proof workload.
It is methods science, not an observed-data discovery claim. Passing it and its
terminal audit can establish IOC; it does not itself authorize an observed-data
search.

IOC does not require launchd, a privileged controller, root-owned namespaces,
service-account architecture, hostile same-UID defenses, autonomous failover,
automatic restart, multi-target operations, survey capability, discovery
authority, or a feature-complete operator interface.

### 4.5 Operational state to conduct science

The program reaches the requested operational state when IOC is accepted and
the same frozen harness can accept a separately authorized science module or
mode without rebuilding the control plane. An observed-data search remains a
separate scientific design, freeze, audit, and authority gate.

## 5. Non-negotiable preservation and science rules

- v0.2.7 remains a terminal startup failure at 0/344 and may never be resumed,
  repaired, rerun, retuned, rerolled, replaced, or regraded.
- v0.2.8 and its 341/5 HOLD remain preserved. Its historical tests and evidence
  may not be edited, weakened, hidden, deselected, or rewritten to manufacture
  qualification.
- A remediation is prospective and versioned. The presumptive next release is
  v0.2.9, subject to the successor design gate.
- The exact v0.2.3-derived 344-case inventory remains the default successor
  inventory. Any scientific change requires a separate justification and new
  freeze before case execution.
- No observed residual access occurs during synthetic qualification.
- No scientific outcome appears in the status or AI supervision channel.
- Qualification must reach the real science-module entry path. Mocked lifecycle
  success or mere scorecard existence is insufficient.
- An audit is advisory and never execution authority.
- Every science run requires an exact frozen package, satisfied entry gates,
  separate execution freeze, and explicit user authorization.
- A formal terminal failure is immutable evidence. It is never quietly repaired
  or rerun under the same identity.

## 6. Recovery and stop baseline

The minimalist IOC baseline permits no autonomous restart, recovery, takeover,
or resume.

Default rule: an operator interruption or operational failure terminally
consumes that run identity and produces a closeout inventory. The harness may
adopt a fully written artifact before terminalization only if the exact rule was
predeclared, tested, and frozen; it may never recompute a consumed case or seed.

Any broader operator-directed resume capability is a separate design decision.
It must be justified by measured operational need and approved before the
harness freeze. It is not silently inherited from v0.2.8.

## 7. Forward work sequence

Every gate below has its own authority and stop boundary. Passing one gate does
not authorize the next.

### Gate 0 — Adopt this plan

Entry: the owner amendments are stated and the v0.2.8 HOLD is reconstructed.

Deliverables:

- this one planning document;
- confirmation that it is prospective and that older evidence is preserved;
- owner review of the IOC, AI/operator, recovery, and science-module definitions;
  and
- an explicit decision to begin Gate 1A.

Exit: owner accepts or amends this plan. No code or test state changes.

### Gate 1A — Design the successor qualification-harness disposition

Entry: Gate 0 accepted.

Produce one short v0.2.9 design containing:

- the exact five historical-state conflicts;
- one governed command that accounts for every current and historical test;
- current-state tests evaluated against current state;
- historical contracts evaluated against immutable snapshots or exact fixtures;
- a machine-exact status taxonomy distinguishing archival drift detection from
  current-release failure;
- fixture provenance, hash binding, and equivalence rules;
- proof that no test is silently omitted;
- explicit non-goals; and
- finite acceptance tests and a stop rule.

Exit: design reviewed and separately approved. No source implementation, full
suite, data-root access, or science.

### Gate 1B — Implement and validate the qualification harness

Entry: Gate 1A approved.

Implement only the approved forward-only disposition. Validate it in the
repository and disposable system temporary roots. Preserve all old tests and
records byte-for-byte. The governed command must return zero unaccounted tests
and zero current qualification failures.

Exit: successor repository and temporary-root validation PASS with zero science
counters. Stop before any real-root access, manifests, freezes, or audit.

### Gate 2 — Bind and qualify the science-module contract

Entry: Gate 1B PASS.

Deliverables:

- one versioned science-module identity and authoritative runtime entry point;
- complete transitive binding of constructors, scanners, fitters, graders,
  calibration, thresholds, inventory, configuration, and dependencies;
- parity tests proving development and operational construction are identical;
- end-to-end tests that execute the real entry path and verify the scientific
  scorecard content, not just its existence;
- exact 344-case, 688-fit, 35-audit accounting; and
- no change to frozen scientific thresholds or inventory unless separately
  justified and approved.

Exit: the science-module contract and implementation are qualified for
integration using bounded pre-execution evidence. Full scientific acceptance
remains Gate 6 plus Gate 7. No operational run or observed-data access.

### Gate 3 — Implement the minimalist operational harness

Entry: Gates 1B and 2 PASS.

Implement only the responsibilities and operator surface in Section 4.2. Reuse
the accepted v0.2.8 controls where they are smaller and correct; do not port
historical stacks or create a second science implementation.

Acceptance includes:

- foreground operator launch and interrupt;
- authority, identity, single-writer, and pre-root fail-closed checks;
- exact science entry-point parity;
- one status record with state, stage, completed/total, checkpoint, elapsed
  time, PID/process state, CPU, RSS, heartbeat age, and errors;
- an invariant that status contains no scientific outcomes;
- duplicate launch and consumed-identity refusal;
- terminalization of operator stop and injected operational failures;
- exact terminal inventory and sealed evidence; and
- no daemon, service, automatic takeover, or hidden AI write path.

Exit: finite synthetic/fault tests PASS. No real root and no science workload.

### Gate 4 — Integrated zero-science qualification

Entry: Gates 1B through 3 PASS and separate real-root-preflight authority.

Sequence:

1. run repository and disposable-root validation;
2. construct the exact designated real-root context twice under process-level
   network denial;
3. record zero connection attempts, downloads, cases, draws, fits, scans,
   observed access, run-root creation, and science artifacts;
4. create exact resource and environment manifests from the passed context;
5. verify designated host, root, storage, and one backup/restore boundary; and
6. repeat the harness preflight against the resulting exact manifests.

Exit: two independently recorded zero-science context passes and complete
manifests. Stop before freezes, audit, or science.

### Gate 5 — Freeze and milestone audit

Entry: Gate 4 PASS.

Create implementation and execution-readiness freezes binding the science
module, harness, qualification command, repository, inventory, resources,
environment, root, operator surface, AI status contract, stop rule, and backup
evidence. Conduct one conservative read-only milestone audit of the exact
frozen commit under the subagent model policy in Section 2.1.

Exit: audit PASS with no open P0/P1 and no material unsupported P2. HOLD/FAIL is
preserved and remediated prospectively. An audit PASS does not authorize Gate 6.

### Gate 6 — Authorize and run the integrated 344-case qualification

Entry: Gate 5 PASS, separate execution freeze, and explicit user authority for
the exact 344-case synthetic qualification.

Execution boundary:

- one foreground operator-controlled run identity;
- one single-writer process;
- AI read-only health supervision at the user-selected cadence;
- health reports limited to stage, checkpoint, elapsed time, CPU/RSS,
  heartbeat/process state, and errors;
- zero observed-residual or observed-periodic-search access;
- no automatic restart, retuning, reroll, promotion, or unblinding; and
- any formal failure terminally closes the run identity.

Exit: one terminal sealed result and complete inventory. No result
interpretation until separately authorized closeout.

### Gate 7 — Terminal audit and IOC declaration

Entry: Gate 6 terminal state.

Perform one read-only closeout binding:

- 344/344 unique cases;
- 688 primary fits and 35 solver audits;
- every scientific and integrity gate;
- annual-identifiability mask;
- science-module and harness identity;
- execution binding, ledger, events, status history, and terminal inventory;
- resource and environment manifests;
- health-only supervision record; and
- backup evidence.

A terminal scientific failure remains a valid scientific failure and does not
authorize retuning or rerun. IOC is declared only if the integrated scientific,
operational, evidence, and audit scorecards all PASS and the owner accepts the
IOC record.

### Gate 8 — Activate separately authorized science

Entry: IOC accepted.

Define the first operational science objective precisely. If it is an
observed-data search, create a separate observed-mode science design, leakage
boundary, frozen inputs, interpretation rules, independent audit, and execution
freeze. Reuse the accepted harness without expanding it unless a demonstrated
requirement forces a prospective change.

Exit: the exact science stage is ready for explicit owner authorization. IOC
never grants autonomous science, survey, discovery, or multi-target authority.

## 8. Anti-spiral rules

1. Maintain one active blocker and one bounded stage at a time.
2. Every new control must map to a named acceptance criterion or observed
   failure.
3. Keep the harness minimal and the science module thorough; never move science
   complexity into the conductor.
4. Do not build launchd, privileged control, services, automatic recovery,
   dashboards, multi-host orchestration, or hostile-process defenses for IOC.
5. Do not create another copied release stack when a shared authoritative entry
   point suffices.
6. Do not reopen passing controls without evidence of a defect.
7. Use one milestone audit, not repeated routine audit loops.
8. A failed formal gate is evidence. Preserve it and proceed prospectively.
9. End each work stage with changed state, current versus required scorecard,
   unresolved blocker, and one explicit next stage.
10. If work no longer advances operational science capability measurably, stop
    and request owner direction before expanding scope.

## 9. Authorization semantics

`Proceed` authorizes only the next stage that Codex has explicitly stated,
including its entry gate, deliverables, exclusions, and stop boundary.

- If the stated stage is design-only, no code is authorized.
- If it is zero-science implementation, no data root or science is authorized.
- If a real-root preflight is stated, it authorizes only zero-science context
  construction and manifest production.
- If an exact execution stage is fully stated and gated, `Proceed` can authorize
  that execution stage only.
- A failed entry or acceptance gate stops the authorized stage even if later
  work was described conditionally.

No old `next_gate`, runner command, freeze, audit PASS, or prior authorization
substitutes for the current explicitly stated stage.

## 10. Immediate next stage after plan adoption

The next proposed stage is **Gate 1A only: design the successor
qualification-harness disposition**.

Entry gate:

- owner accepts this plan;
- repository identity still matches the v0.2.8 turnover except for this new
  planning document or an explained planning-only commit;
- worktree changes are reconciled; and
- no Pilot 2 process is active.

Deliverable: one short v0.2.9 design addressing only the five qualification-
harness conflicts, historical snapshot/fixture semantics, complete test
accounting, acceptance tests, non-goals, and stop rule.

Explicit exclusions: source implementation, test execution, data-root access,
context construction, resource acquisition, manifests, freezes, audit, science,
observed data, Mac mini/NAS configuration, and IOC harness implementation.

Stop boundary: publish the design for owner review and wait for separate
authorization before Gate 1B.

## 11. Prospective minimal-harness reset amendment — 2026-08-16

The current reset instruction is to retire/remove both the v0.2.9 and v0.2.10
qualification-harness code, observer, and test stacks while
preserving the v0.2.9 historical docs/results and the external v0.2.10 terminal
evidence. The recovery anchor is commit
`b8190d3b2d4dee2b7dc38fb8c2cff66fc7f131bb`. Pilot 2 science/runtime code,
configuration, snapshots, and the existing governance amendment remain
outside the reset surface.

The successor design uses exactly the existing five foreground commands:
`verify-gate`, `preflight`, `prepare`, `run`, and `status`. It uses direct
lifecycle tests and supersedes the old Gate 1 qualification route; it does not
use a custom pytest observer, full-suite-in-harness execution, nested
sandboxes, snapshot gymnastics, daemons, brokers, or retries. This implemented
stage has zero science, zero data-root, and zero network authority, with no
science adapter binding; it points forward to direct science-module binding
only under separate owner authorization.

This amendment supersedes the immediate next-stage proposal above. The
replacement implementation stage stopped before commit as required. The
owner's subsequent `Proceed` authorized only the clean reset commit; science
adapter binding, data-root access, network access, and science execution remain
locked.

## 12. Prospective Gate 2 sequencing clarification — 2026-08-16

This append-only clarification resolves the conflict between Gate 2's
pre-execution exit boundary and its two execution-dependent evidence bullets.
It applies prospectively and does not alter any historical HOLD, terminal
attempt, test result, science threshold, inventory, or execution record.

Gate 2 now qualifies only the pre-execution science-module contract. Its exit
requires:

- one exact module/release identity and one authoritative chain:
  `pilot2_ioc_harness run -> pilot2_science_module:SCIENCE_MODULE.run ->
  pilot2_runtime_core.execute`;
- complete prospective transitive binding rules for the harness, adapter,
  runtime, constructors, scanners, fitters, graders, calibration, thresholds,
  inventory, configuration, dependency locks, and the resource/environment
  manifests later supplied and verified at Gate 4;
- exact contract accounting of 344 cases, 688 primary fits, and 35 solver
  audits;
- finite zero-science tests covering authority, root binding, fresh-only and
  no-resume behavior, foreground status, interruption/failure terminalization,
  outcome-free receipts, and evidence closure; and
- no alternative runner, dry-run science route, mocked claim of scientific
  parity, or copied science stack.

The prior Gate 2 bullets requiring real scientific-construction parity and
scorecard-content proof are not waived. They are reassigned as follows:

1. Gate 6 is the first permitted real harness-to-adapter-to-runtime execution.
   Under Gate 5 PASS, a separate execution freeze, and explicit owner
   authorization, it must prove that the actual PINT construction, scanners,
   fitters, graders, all 344 cases, 688 primary fits, and 35 solver audits use
   the exact frozen authoritative path.
2. Gate 7 must inspect the sealed terminal scorecard content, every scientific
   and integrity gate, annual mask, execution binding, ledger, receipt, and
   terminal inventory before IOC can be declared.

A mocked or reduced-case integration test may support plumbing diagnosis, but
it cannot satisfy either relocated requirement and is not a substitute for
Gate 6 or Gate 7. Gates 3, 4, and 5 remain mandatory and sequential before any
Gate 6 authority. This clarification grants no code, test, real-root, manifest,
freeze, audit, process-launch, science, result-review, IOC, or observed-data
authority.

The accepted Gate 2A-R1/R2 evidence at commit
`6b2e831f5e5d8b92741a06ce5dd0c74c518964d6` may support a later Gate 2
closeout, but this planning amendment does not itself mark Gate 2 PASS. The
next possible action is owner review of this exact amendment and SHA-256.
Nothing begins automatically.
