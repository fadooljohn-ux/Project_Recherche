# Project Recherche top-down assembly audit

Date: 2026-08-11

Target commit: `a1eeb553b69e9c8ee5a3bf1e4fd9b62da231d730`

Target tree: `7db4e8639ad057c2e93d7c863efa2c97b2ff7e69`

Program: Project Recherche / Neutron Star Program / Pilot 2 B1937+21

Disposition: **HOLD**

## Executive conclusion

The preserved v0.2.7 startup failure is a valid terminal operational failure,
not a scientific result. It stopped before case 1 with zero completed cases,
random draws, timing-model fits, periodic scans, promotion grades, or observed
residual access. The fail-closed network boundary worked as intended.

The project is not yet safe to authorize for another 344-case run. The assembly
confirmed six P1 execution blockers. The clock-index failure exposed the first
of them, but a clock-cache patch alone would not close the control-plane risks.
A new successor version must close all P1 findings without changing, resuming,
or repairing v0.2.7.

## Assembly and boundary

The assembly consisted of:

- one Sol critical auditor covering scientific integrity, authorization,
  startup, recovery, reproducibility, and terminal-state controls;
- one Terra repository auditor covering duplication, evidence retention, and
  active-lineage clarity; and
- one Terra roadmap auditor covering the full-run and IOC acceptance gates.

All three auditors had read permission only. They did not access `/Volumes`,
external science roots, network resources, scientific payloads, or observed
data. They did not execute tests or science and made no repository changes.
Primary reconciliation by the coordinating agent was also read-only.

## Audit scorecard

| Area | Grade | Outcome |
|---|---:|---|
| v0.2.7 failure preservation | A | PASS — terminal evidence remains preserved; no rerun found |
| Science and observed-data boundary | A | PASS — startup stopped before case 1; no observed access |
| Fail-closed network control | A | PASS — network request was rejected |
| Duplicate-JSON trust boundary | A | PASS — v0.2.7 recursively rejects duplicate JSON members |
| Offline context startability | F | HOLD — real PINT context path was not preflighted |
| Science-control configuration binding | F | HOLD — runtime grading inputs are not a closed hash-bound set |
| Execution authorization enforcement | F | HOLD — declared audit/root/launch fields are not verified |
| Ledger and terminal completion invariants | F | HOLD — false or incomplete terminal state can be accepted |
| Single-writer protection | F | HOLD — concurrent launches can race |
| Environment and resource reproducibility | F | HOLD — lockfile/runtime/resource closure is not frozen |
| Annual-mask durability | C | HOLD for Stage 1 closeout — mask is not serialized |
| Current full-suite test command | C | HOLD for freeze — current validation uses ad hoc deselections |
| Project state and operator routing | C | Needs correction — active Pilot 2 status is hard to discover |
| Evidence-preserving repository hygiene | B | No safe tracked deletions; prospective consolidation required |
| IOC definition | D | Now defined prospectively in the two-stage roadmap |

Overall: **HOLD**. A new release may proceed through remediation and zero-science
validation, but no science execution should be authorized until every P1 is
closed and the exact successor freeze passes a fresh read-only audit.

## Critical finding register

### ASM-001 — P1 — Offline startup dependency was not preflighted

The real execution path constructs the PINT context under network denial in
`pilot2_injection_runner_v027.py:1034-1077`. The zero-case dry run at
`pilot2_injection_runner_v027.py:1505-1529` validates ledger and gate state but
does not call that path. Preflight seeds only the `time_ao.dat` URL cache entry.
PINT then requested its global clock-correction index during `_load_release()`,
and v0.2.7 stopped correctly before case 1.

Required closure:

- use an immutable local-only clock-resolution path;
- inventory and hash every required clock, index, and ephemeris resource;
- run the exact real-release context-construction path under process-level
  network denial on the designated hardware and root; and
- assert zero cases, random draws, fits, scans, observed access, or science
  artifact creation.

### ASM-002 — P1 — Science-controlling configuration is not fully bound

The runner loads the base calibration, remediation, and runner YAML files.
Those inputs control solver tolerances, annual eligibility, acceptance gates,
and final grading. The base configuration is absent from the v0.2.7 execution
allowlist, and live execution does not call `verify_remediation_freeze()`.
Changing a science-control value can therefore escape the execution gate.

Required closure:

- define one exact set of all science-control files;
- include it in the implementation aggregate, implementation/readiness freeze,
  execution freeze, and live execution binding;
- verify the remediation freeze in the execution gate; and
- reject duplicate YAML keys and require exact typed schemas.

### ASM-003 — P1 — Declared execution authorization fields are not enforced

The execution freeze declares audit status and hashes, an authorized root,
marker hash, and launch contract. The verifier does not check those fields, and
its passing test fixture omits them.

Required closure:

- enforce an exact execution-freeze schema with no missing or extra fields;
- verify audit identity, hashes, and semantic PASS status;
- verify the authorized stable root identity and marker hash at launch;
- verify launch contract and environment identity; and
- fail before predecessor or science loading on any mismatch.

### ASM-004 — P1 — Ledger and terminal-result invariants are incomplete

The ledger loader requires only an object with matching inventory and
implementation hashes. Artifact verification checks completed case files but
not stage-result artifacts. Execution returns `already_complete` solely from a
ledger stage status, without proving that all 344 records and a valid terminal
result exist.

Required closure:

- enforce an exact typed ledger schema and state machine;
- validate unique membership of exactly 344 inventory cases for PASS;
- require no active attempt, all case artifact hashes, a terminal result hash,
  expected gate count and statuses, annual-mask artifact, and matching execution
  binding; and
- make impossible state combinations fail closed.

### ASM-005 — P1 — No single-writer execution lock

Ledger transitions are unlocked load-modify-save operations, and atomic writes
use a fixed temporary path. Two launches could consume the same attempt, race
on an artifact, or overwrite ledger state.

Required closure:

- acquire a root-and-version-specific OS advisory lock before any setup or
  ledger mutation;
- retain it for the complete process lifetime;
- record process identity without using it as the lock itself;
- reject a second live writer; and
- test simultaneous launch, interrupted owner, and stale-lock recovery.

### ASM-006 — P1 — Environment and runtime resources are not frozen

The execution allowlist excludes `pixi.lock`, environment/package attestation,
platform identity, and clock/index/ephemeris resources. A command string is not
a runtime fingerprint.

Required closure:

- bind `pixi.lock`, the relevant environment definition, interpreter identity,
  resolved package manifest, platform/architecture, Rosetta and precision
  status, PINT/Astropy/NumPy versions, environment-variable policy, and every
  runtime resource;
- demonstrate the closure from a fresh or restored environment; and
- treat any dependency or platform change as a new version and audit event.

## Secondary findings

### ASM-007 — P2 — Annual mask is not a durable run artifact

Annual eligibility is added after case artifacts are committed and remains in
memory. The final grader does not serialize the complete periodwise mask.
Stage 1 closeout must produce a contemporaneous artifact containing periods,
thresholds, contributing case IDs, maxima, decisions, and source hashes.

### ASM-008 — P2 — No single current all-tests-green command

The README advertises `pixi run test`, while the v0.2.7 validation deselects
three historical tests whose assumptions conflict with later immutable
evidence. Historical state tests should use immutable fixtures or an explicitly
archival suite. A successor freeze must name one current command with no ad hoc
deselections and zero failures.

### ASM-009 — P2 — Governance and current-state documentation drift

The frozen historical North Star predates the v0.2.7 terminal failure, and the
README foregrounds Pilot 0/1 without routing operators to Pilot 2. The committed
absolute authorized-root path also conflicts with the portable data-boundary
policy. The new roadmap is prospective and does not edit historical evidence.
Future freezes should use stable root identity plus launch-time attestation.

### ASM-010 — P2 — IOC was not objectively defined

The previous release verifier covers the J1744 initial-v0.1 milestone, not
current Pilot 2 operational capability. The companion roadmap now provides a
machine-verifiable IOC definition and acceptance gates.

### ASM-011 — P3 — Version-copy complexity

Six Pilot 2 runner generations and six test generations contain 10,349 lines.
The apparent redundancy cannot be removed while those files are frozen evidence
or live dependencies. Future releases should use a new immutable shared core
and thin version contracts without retrofitting historical versions.

## Passing controls retained

- v0.2.7 stopped before case 1 and was not resumed.
- Network access failed closed.
- Duplicate JSON member names are rejected before trusted parsing.
- Frozen repository allowlists are exact-set checked and confined to the repo.
- Attempt journaling precedes seed use and uses file and directory sync.
- Interrupted artifacts must pass complete typed validation or consume the
  attempt terminally.
- Live input bindings are recursively type/value checked and included in the
  execution binding.
- The 344-case inventory and the retired v0.2.2 seed boundary remain preserved.
- Observed-data, promotion, reroll, retuning, and discovery locks remain closed.

## Evidence-preserving disposition

Do not edit, rerun, repair, regrade, or resume v0.2.7. Do not delete historical
source, tests, configurations, protocols, audits, results, incidents, or
terminal records merely because later versions resemble them. The
preservation-aware classification is in
`docs/REPOSITORY_REDUNDANCY_REGISTER_2026-08-11.md`.

## Next gate

Planning and a new successor remediation are allowed. Science remains locked.
The controlling forward path is
`docs/PROJECT_RECHERCHE_TWO_STAGE_ROADMAP.md`.
