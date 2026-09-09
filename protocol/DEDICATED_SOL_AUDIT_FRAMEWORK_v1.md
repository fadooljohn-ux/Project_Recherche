# Dedicated Sol audit framework v1

## Purpose

Project Recherche uses a dedicated Sol subagent as its independent technical
auditor. The auditor is a passive reviewer and has no authority to edit the
package, execute science, authorize execution, clear its own findings, inspect
sealed scientific outcomes, rerun failed versions, or retune a threshold.

This framework removes external-review dependency while retaining separation
between implementation, audit, disposition, remediation, and execution.

## Independence contract

The primary implementation agent supplies a frozen audit target and a bounded
question set. A newly dispatched `gpt-5.6-sol` subagent reviews that target in
read-only mode. The audit prompt must prohibit file edits, science execution,
outcome inspection, remediation, and authorization.

The auditor's report is preserved verbatim before the primary agent responds to
it. The primary agent independently reproduces every P0, P1, and P2 finding and
records whether it is confirmed, partly confirmed, rejected with evidence, or
not reproducible. The auditor cannot be asked to approve its own remediation.

## Required audit scope

For a frozen science-runner package, the audit examines:

1. repository and version isolation;
2. inventory counts, IDs, seeds, ordering, and historical disjointness;
3. freeze and hash consistency;
4. authorization gates and preauthorization loading boundaries;
5. scientific-threshold immutability;
6. API and environment compatibility relevant to the remediation;
7. exception, hard-stop, resume, corruption, and checkpoint behavior;
8. health-record outcome isolation;
9. tests, exclusions, warnings, and validation claims;
10. observed-data, promotion, rerun, and retuning prohibitions.

The audit may inspect external records only when they are explicitly bound,
non-scientific, and necessary to verify process state or hashes. It may not
inspect incomplete-run case outcomes or observed residuals.

## Findings and disposition

Each finding contains a stable ID, severity, affected path and line when
applicable, evidence, impact, and recommended corrective action.

- **P0** — integrity or authorization breach.
- **P1** — execution-blocking correctness or fail-closed defect.
- **P2** — material auditability, recovery, or validation gap.
- **P3** — non-blocking clarity, maintainability, or documentation issue.

The audit disposition is `PASS` only when there are no open P0 or P1 findings
and no P2 finding that makes the execution-readiness claim materially
unsupported. Otherwise it is `HOLD`. A pass is advisory and never constitutes
science authorization.

## Required deliverables

The auditor returns:

- an executive `PASS` or `HOLD` disposition;
- a finding register;
- a gate-by-gate scorecard;
- evidence paths and relevant hashes;
- residual risks and test limitations;
- an attestation that no files were edited and no science was executed;
- the exact next gate.

The primary agent then produces a separate disposition mapping each finding to
independent verification evidence. Remediation and execution each require a
separate user instruction.

## Milestone use

Use this framework before initial execution of a new science-runner version,
after a terminal execution failure and before remediation, before promotion or
observed-data access, and before release or migration to dedicated hardware.
Routine implementation turns do not require an audit subagent.
