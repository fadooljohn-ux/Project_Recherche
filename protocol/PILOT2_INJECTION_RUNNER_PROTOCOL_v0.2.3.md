# Pilot 2 B1937+21 injection runner protocol v0.2.3

## Authority and historical boundary

This protocol defines a prospective v0.2.3 replacement for the v0.2.2 runner
that crashed during its first attempted case. It authorizes implementation and
zero-science validation only. No v0.2.3 execution freeze exists.

The entire v0.2.2 inventory is retired. The attempted case
`p2r2-inj-main-p00-a00-h00-n00` and seed `2691995251659989168` are consumed even
though no case record was written. v0.2.3 cannot resume or write any v0.2.2
path.

## Corrective implementation

Phase telemetry reads the fitted PINT `parameter_correlation_matrix` object
directly and extracts the `CSSIN`/`CSCOS` labeled block. It never uses
`get_parameter_correlation_matrix()`, whose installed behavior produced
formatted text and caused the v0.2.2 exception.

The compatibility test constructs a real PINT `CorrelationMatrix` and presents
the installed API shape in which the legacy getter returns text. The test
confirms that v0.2.3 uses only the object property. It generates no random draw,
fits no timing model, scans no data, and executes no injection.

## New inventory and paths

The 344 v0.2.3 case IDs and seeds are disjoint from both v0.2.1 and the entire
v0.2.2 inventory. The fixed family counts and order remain 240 main, 60
phase-reference, 28 annual, and 16 boundary cases, with 35 solver audits.
Scientific thresholds and grading rules are unchanged.

The runner writes only:

- `run_records/pilot2/calibration-v0.2.3-ledger.json`;
- `run_records/pilot2/calibration-v0.2.3-health.json`;
- `run_records/pilot2/injection-v0.2.3-setup.log`;
- `run_records/pilot2/injection-evaluation-v0.2.3.json`;
- `derived/pilot2/calibration-v0.2.3/injections/`; and
- `derived/pilot2/calibration-v0.2.3-dashboard/index.html`.

## Exception and recovery behavior

An unexpected execution exception writes a terminal failure result containing
only the exception type and message, active case ID, and completed-record count.
It records no partial scientific metric. The ledger then marks the stage failed,
writes a hard stop, clears the active stage, and rejects another begin-stage
operation.

Orderly user interruption remains resumable. Resume requires unchanged
inventory, implementation, execution-freeze, threshold-lock, and recorded-case
artifact hashes. Missing or changed artifacts fail closed.

## Health-only supervision

While running, the 30-second heartbeat exposes only process state, PID, elapsed
time, completed count out of 344, checkpoints, stage state, and hard-stop state.
The stale threshold remains 90 seconds and passive review interval remains 30
minutes. Scientific outcomes remain sealed until terminal completion.

## Execution boundary

Implementation and readiness freezes do not authorize science. A future
execution freeze must bind the v0.2.3 inventory, aggregate implementation,
readiness freeze, predecessor hashes, and the preserved v0.2.2 crash evidence.
Promotion, observed residual access, observed periodic search, and discovery
claims remain unauthorized regardless of the injection-stage outcome.
