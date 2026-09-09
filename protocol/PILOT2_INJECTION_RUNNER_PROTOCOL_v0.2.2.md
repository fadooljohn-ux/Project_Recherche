# Pilot 2 B1937+21 injection runner protocol v0.2.2

## Authority and version boundary

This protocol defines the implementation behavior of the prospective v0.2.2
injection runner. It authorizes zero-case testing only. The runner cannot load
predecessor artifacts or the timing-model execution context unless a separate
execution freeze exists, hash-matches the implementation and inventory, and
explicitly authorizes execution.

The v0.2.1 terminal failure, ledger, threshold, and injection artifacts remain
immutable. The v0.2.2 runner does not modify or replace them. Passed v0.2.1
threshold, sealed-Gaussian, and structured-tail result artifacts may be reused
only through their exact frozen SHA-256 bindings. The failed v0.2.1 injection
records are development evidence and never an acceptance set.

## Independent artifacts

The runner writes only versioned v0.2.2 paths:

- `run_records/pilot2/calibration-v0.2.2-ledger.json`;
- `run_records/pilot2/calibration-v0.2.2-health.json`;
- `run_records/pilot2/injection-v0.2.2-setup.log`;
- `run_records/pilot2/injection-evaluation-v0.2.2.json`;
- `derived/pilot2/calibration-v0.2.2/injections/`; and
- `derived/pilot2/calibration-v0.2.2-dashboard/index.html`.

No v0.2.1 path is a write target.

## Inventory and execution order

The inventory contains 344 new cases and 35 deterministic solver audits. All
case IDs and seeds are disjoint from v0.2.1. The fixed order is:

1. 240 main detection-recovery cases;
2. 60 high-information phase-reference controls;
3. 28 annual identifiability cases, finalized by complete period group; and
4. 16 search-boundary cases.

The locked predecessor threshold uses a strict greater-than trigger and cannot
be retuned.

## Grading

The terminal stage passes only if every hard gate passes:

- exact family counts of 240, 60, 28, and 16;
- all 344 records contain the canonical TOA-adjustment metric separately from
  the uncentered target diagnostic;
- maximum canonical TOA-adjustment error is at most 0.001 microseconds;
- all ordinary and joint fits converge;
- exactly 35 solver audits complete with zero failures;
- existing strong-control recovery, frequency recovery, median-amplitude-bias,
  monotonicity, bracketing, and annual-eligibility gates pass;
- all 60 phase-reference controls trigger;
- phase-reference p90 error is at most the unchanged 0.1 radians;
- no unexpected material warning occurs; and
- wall time, memory, and storage remain within their frozen caps.

Phase error across all triggered main sensitivity cases remains a reported
diagnostic and is not substituted for the phase-reference hard gate. Signed
phase error and phase-uncertainty telemetry remain mandatory in every new case
record.

## Ledger, resume, and recovery

Each completed case is recorded atomically with path, byte count, and SHA-256.
A checkpoint is added every 25 cases. Resume requires exact inventory and
implementation hashes, an unchanged execution binding, and verification of
every already-recorded artifact. An altered or missing artifact blocks resume.

Interrupted runs remain `running` with `runtime_active=false` after orderly
shutdown and are resumable. A terminal failed grade writes the result artifact,
marks the stage failed, records a hard stop, and prevents another begin-stage
operation. No reroll or seed replacement is allowed.

## Health-only supervision

While running, the health record exposes process state, PID, active-stage
elapsed time, completed cases out of 344, checkpoint count, heartbeat time, and
hard-stop presence. It contains no threshold, trigger statistic, candidate,
phase error, fit result, or other scientific outcome. The heartbeat interval is
30 seconds, the stale tripwire is 90 seconds, and passive external review is
scheduled no more often than every 30 minutes. A manual-refresh command is
recorded in the health JSON, and the desktop dashboard refreshes every 30
seconds.

## Stop rules

The runner fails closed before science setup on an absent or mismatched
authorization, implementation freeze, inventory, predecessor binding, or data
root. During execution it stops on artifact mismatch, changed execution
binding, nonconvergence, failed solver audit, missing canonical metric,
unexpected warning, nonfinite or failed grade, changed threshold lock, or
resource-cap breach.

A passing v0.2.2 injection stage does not execute the promotion grade and does
not authorize observed residual access or an observed periodic search.
