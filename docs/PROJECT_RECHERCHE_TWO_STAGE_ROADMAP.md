# Project Recherche two-stage North Star roadmap

Effective: 2026-08-11

Scope: Project Recherche / Neutron Star Program / Pilot 2 B1937+21

Status: **Planning and remediation only; science execution is halted**

## Authority and relationship to historical records

This is the forward-looking North Star for the remainder of the science stage.
It has two stages:

1. complete one valid, frozen 344-case synthetic full science run; and
2. achieve Initial Operational Capability on the dedicated Mac mini/NAS setup.

This document does not modify any frozen package, reopen any terminal run, or
authorize science. The earlier `docs/PILOT2_SCIENCE_STAGE_NORTH_STAR.md` is
hash-bound historical evidence and must remain unchanged. For future successor
work, this roadmap supersedes its prospective current-position statements.

The 2026-08-11 assembly audit at
`docs/audits/TOP_DOWN_ASSEMBLY_AUDIT_2026-08-11.md` is the entry assessment.
Its six P1 findings are mandatory Stage 1 gates.

## Non-negotiable rules

- v0.2.7 is terminal and cannot be resumed, repaired, rerun, retuned, rerolled,
  replaced, or regraded.
- Every remediation creates a new version and evidence lineage.
- No observed residual access occurs in Stage 1.
- No scientific outcome appears in a health feed.
- Every execution requires an exact frozen package, audit PASS, separate
  execution freeze, and explicit user authorization for that stated stage.
- Any terminal failure is preserved; recovery proceeds only in a new version.
- Git contains code, controls, manifests, audits, and compact results. Raw and
  large science data remain in the controlled data root outside Git.

## Stage 1 — Complete one full frozen 344-case science run

### Stage 1 definition of done

Stage 1 is complete only when a new successor version executes the frozen
344-case B1937+21 synthetic inventory exactly once and an independent closeout
confirms:

- 344/344 unique case records;
- 688 primary timing-model fits;
- 35 solver audits;
- all preregistered integrity and scientific gates PASS;
- a durable periodwise annual-identifiability mask;
- a valid terminal result, ledger, execution binding, and artifact manifest;
- resource caps and health-only monitoring controls PASS; and
- zero observed residual or observed-search access.

The full synthetic run is a methods qualification. It is not a discovery claim
and does not itself authorize an observed-data search.

### S1-M0 — Preserve and rebaseline

Entry: v0.2.7 terminal evidence and the assembly audit are present.

Deliverables:

- verify the v0.2.7 incident and terminal artifact hashes;
- record that no run is active and v0.2.7 is permanently closed;
- create a successor remediation version and release-lineage index;
- bind the prior terminal evidence into the successor design; and
- state explicitly whether the never-executed 344-case inventory and seed
  namespace remain scientifically valid. Any inventory change requires a newly
  frozen inventory and separate justification.

Exit: successor design frozen; no ambiguity about version, inventory, or scope.

### S1-M1 — Close offline dependency and environment closure

Mandatory findings: ASM-001 and ASM-006.

Deliverables:

- complete local PINT/Astropy clock, global-index, ephemeris, and IERS resource
  inventory with origins, licenses, sizes, and SHA-256 hashes;
- immutable local-only resolver/cache layout with no first-use download;
- bind `pixi.lock`, environment definition, Python and package manifest,
  platform/architecture, Rosetta status, precision result, relevant environment
  variables, and designated-hardware identity; and
- a cache-population/provisioning step that is operational setup, not science.

Acceptance test:

- from a fresh or restored controlled environment, construct the exact real
  release context twice under process-level network denial;
- record zero connection attempts and zero downloaded bytes;
- verify exact model, TOA, clock, ephemeris, shape, and rank bindings; and
- assert zero cases, draws, fits, scans, observed access, or science artifacts.

Failure: preserve the preflight incident and remediate only in another version.

### S1-M2 — Close execution integrity controls

Mandatory findings: ASM-002 through ASM-005 and ASM-007.

Deliverables:

- closed hash set and exact typed schemas for every science-control YAML;
- live verification of remediation, implementation, readiness, and execution
  freezes;
- exact execution-freeze schema verifying audit PASS, stable root identity,
  marker, launch contract, environment, resources, predecessors, and scope;
- exact ledger schema and cross-field state machine;
- terminal PASS requiring all 344 cases, terminal result, annual mask, expected
  gate statuses, no active attempt, and matching execution binding;
- single-writer OS lock held before the first mutation through process exit;
- unique durable temporary-file strategy; and
- contemporaneous annual-mask artifact containing source case IDs and hashes.

Acceptance tests include missing/extra/duplicate/wrong-type fields, mutated
science configs, mismatched root/audit/launch/environment identity, missing or
corrupt terminal artifacts, false-complete ledgers, concurrent launches,
interruption, stale-lock handling, write failure, and resume invariants.

Exit: all six P1 findings closed with exploit-shaped negative tests.

### S1-M3 — Qualify the successor without science

Deliverables and gates:

- one documented current full-suite command passes with zero failures and no ad
  hoc deselections;
- focused integrity, authorization, offline-resource, concurrency, and recovery
  suites pass;
- formatting/static checks pass;
- temporary-root zero-case dry run passes;
- exact designated-root offline context-load preflight passes under its own
  explicit authorization and creates no science artifact;
- frozen validation manifest records commands, results, environment, resource
  hashes, and zero-science counters; and
- all historical failures remain unmodified.

Exit: implementation and readiness freezes are complete. Science remains locked.

### S1-M4 — Freeze and audit

Entry: S1-M3 PASS.

Deliverables:

- implementation freeze;
- execution-readiness freeze;
- complete read-only audit package; and
- independent Sol audit of the exact frozen commit.

Acceptance: no open P0 or P1, no material unsupported P2, all reported findings
have a verified disposition, and the worktree and frozen hashes match.

If audit HOLD/FAIL: preserve that version and remediate in a new version.

### S1-M5 — Authorize and execute

Entry: S1-M4 audit PASS.

Before execution:

- create a separate execution freeze binding the exact commit, freezes, audit,
  inventory, science controls, predecessors, root identity, resources,
  environment, hardware, launch contract, monitoring, and backup evidence;
- verify available storage, controlled-root availability, and backup snapshot;
- obtain explicit user authorization for this exact 344-case stage; and
- acquire the single-writer lock in one managed persistent foreground session.

During execution:

- 30-second operational heartbeat;
- 90-second stale threshold;
- checkpoint every 25 cases;
- 30-minute passive health review unless the user sets a different interval;
- health reports show process, time, memory, count, rate, and errors only; and
- no restart, reroll, retuning, promotion, or observed access.

Any failure closes the version terminally.

### S1-M6 — Terminal audit and Stage 1 closeout

Perform a read-only closeout against the Stage 1 definition of done. Bind the
terminal ledger, result, annual mask, case manifest, execution environment,
resource manifest, logs, health record, and backup evidence. Stage 1 passes only
if the closeout audit passes every item. A scientific-gate failure is preserved
as a scientific failure and is not converted into permission to retune or rerun.

## Stage 2 — Achieve Initial Operational Capability

### IOC definition

IOC means the designated Mac mini compute host and NAS/backup system can
reproducibly prepare and run a separately authorized, frozen, single-target
analysis with fully offline controlled inputs, single-writer execution,
outcome-sealed health monitoring, interruption recovery, immutable closeout,
and verified backup/restore—without manual cache repair or silent dependency
changes.

IOC does not mean autonomous authorization, a survey, multi-target operations,
automatic unblinding, discovery authority, or permission to rerun a failed
one-shot analysis.

### S2-M0 — Approve IOC architecture and acceptance contract

Entry: Stage 1 terminal closeout PASS.

Deliverables:

- Mac mini/NAS architecture and capacity plan;
- roles and responsibilities for owner, operator, and auditor;
- stable mounts and root identities;
- least-privilege service accounts;
- threat/failure model;
- retention, backup, restore, and incident policy; and
- machine-verifiable IOC acceptance manifest schema.

Exit: user approves the exact deployment and exclusions.

### S2-M1 — Build and migrate reproducibly

Deliverables:

- reproduce the locked environment on the Mac mini;
- validate architecture, Rosetta if still required, and precision gates;
- copy controlled inputs and runtime resources without changing their content;
- verify every source/root/package/resource hash after migration;
- configure the NAS controlled root as read-mostly input storage;
- place working state on the designated write-capable volume; and
- create an immutable versioned backup in a separate failure domain, not merely
  another share on the same NAS.

Acceptance: cold offline context load passes and a full restore into an isolated
staging root reproduces all controlled hashes.

### S2-M2 — Operational hardening

Deliverables:

- one governed command each for preflight, launch, status, and stop;
- persistent managed-session contract;
- single-writer and duplicate-launch prevention;
- outcome-free dashboard, heartbeat, checkpoint, and stale alerts;
- disk, mount, resource, cache, clock, and backup prechecks;
- durable logs and retention controls;
- operator runbook and incident runbook; and
- explicit release, rollback, and dependency-change policy.

Fault drills must prove correct behavior for network denial, mount loss, cache
corruption, duplicate launch, interrupted write, stale process, alert delivery,
and full restore. These drills execute no science.

### S2-M3 — IOC qualification

Qualification requires:

- two independent zero-science deployment rehearsals across a reboot or restore
  boundary;
- all code, input, resource, environment, and root manifests hash-match;
- no unlogged writes or network accesses;
- recovery-time and capacity targets meet the approved contract;
- current tests and operational drills pass;
- a read-only Sol release/IOC audit passes; and
- the user accepts the machine-verifiable IOC record.

Failure creates a preserved qualification incident and blocks IOC declaration.

### S2-M4 — IOC operations

After IOC, every science or observed-data action still requires a versioned
package, read-only audit, separate execution freeze, and explicit per-run user
authorization. The proposed minimum maintenance cadence is:

- before and after each freeze or run: backup and hash verification;
- monthly: backup-restore sample check;
- quarterly: offline resource and environment validation;
- annually: disaster-recovery rehearsal; and
- immediately after any dependency, platform, detector, threshold, or schema
  change: new release qualification and audit.

## Current position and next action

Current position: before S1-M0, with science halted and the assembly audit at
HOLD. The next authorized implementation stage, if directed, is S1-M0 plus the
design work for S1-M1 and S1-M2. It must not execute cases or access observed
data.
