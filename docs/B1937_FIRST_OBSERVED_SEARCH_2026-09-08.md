# B1937+21 first observed search

Owner instruction, 2026-09-08: connect the B1937+21 observed-search entry point to
the repaired runtime, bind the existing threshold and annual mask, and prepare a
clearly defined first search. Automated calibration for future data ingestion is
deferred until after this search is complete.

**Status: completed; verified scientific disposition `NO_TRIGGER`.**
The owner subsequently authorized execution with “Launch”. The single observed
search completed on 2026-09-08 at 16:25:43 Asia/Taipei (08:25:43 UTC), in
8.494 seconds. Its consumed intent and terminal evidence are preserved.

## Fixed scientific scope

- Target: B1937+21, NANOGrav 15-year v2.1.0 wideband timing products already local.
- Input root: `../Project Recherche Data/operational-20260908/`.
- Data: 660 active arrival-time measurements with the paired dispersion-measure
  coordinates, spanning approximately 5,798 days. The qualified released model,
  white/red-noise covariance, clock resources and DE440 ephemeris are retained.
- Detector: the qualified covariance-weighted, timing-model-projected circular
  signal scanner; one scan of the observed residual vector from the repaired model.
- Grid: the exact qualification grid, 953 frequencies spanning 30–2,000 days.
- Threshold: **22.485020743823544**, with strict `>` comparison. The threshold
  lock is bound by its original hash. No recalibration or false-alarm-probability
  estimate is part of this run.
- Mask: qualification 02's complete annual mask, bound through its result and
  contributing annual-case hashes. The excluded 365.25-day sample maps to its
  nearest period-grid cell, using the existing mapping function and tie rule.
  No new exclusion width or interpolation is inferred from the seven samples.
  Neighboring annual periods are not automatically certified by this sparse mask.
- Candidate selection: strongest unmasked grid cell. A larger masked peak is
  reported as context and cannot suppress the unmasked peak. No alternate peaks,
  frequency refinement or automatic retries are included.

If the selected statistic does not exceed the threshold, stop with `NO_TRIGGER`.
This means no qualifying signal in this search, not proof of no companions.

If it exceeds the threshold, perform one ordinary fit, one joint timing/signal
fit at the selected fixed frequency, and one explicit full-covariance audit.
Use the existing fit-iteration settings and amplitude/phase/chi-square agreement
limits. Apply the existing 0.8 signal/astrometry correlation limit to the fitted
signal. Report `PERIODIC_SIGNAL_CANDIDATE`, `NUMERICAL_HOLD`, or
`IDENTIFIABILITY_HOLD` as appropriate. Unexpected material warnings produce
`WARNING_HOLD`. An orbital or planet discovery is not inferred automatically.

Maximum science work is one scan, two primary fits and one solver audit. Resource
limits remain six hours, 16 GiB RSS and 1.5 GiB of run output, checked between
numerical operations. Runtime status updates every 30 seconds; a long run can
use the usual 30-minute external monitoring cadence.

## Implementation and operation

The adapter is `tools/b1937_search.py`, reached through `tools/recherche observed`.
It calls the existing repaired context builder, scanner, fitters, annual mapping,
solver comparison and offline resource boundary. All 71 qualified scientific
source files remain unchanged. The older Pilot 1 observed-search entry point is
not repurposed; only its existing pure mask/selection helpers are reused.

Preparation and checking hash the inputs and read saved synthetic qualification
evidence. They do not construct or scan the observed residual vector.

```sh
cd '.'
package='../Project Recherche Data/observed-preparation-20260908/first-search.json'
tools/recherche observed check --package "$package"
```

The future execution command is recorded in the preparation receipt. It requires
`--authorize-package` with the exact package SHA-256. That argument is an explicit
operator acknowledgment of the prepared package, not an authorization generated
by the preparation command. No additional approval-document workflow is needed.

Execution consumes a durable intent at
`DATA_ROOT/b1937-observed-search-intent.json` before loading the observed vector.
A duplicate start is rejected even if the earlier attempt stopped or failed.
The output is `DATA_ROOT/observed-runs/pilot2-ioc-observed-b1937-20260908-01/`.
`tools/recherche status --run-root PATH` uses the existing process/status format.
Ctrl-C preserves a controlled-stop record; errors preserve failure and accounting
records. No failure authorizes resuming or rerunning the observed search.

Terminal output includes the bound manifest, complete periodogram, selected peak,
conditional fit/audit report, residual-vector digest, resource trace, warnings,
actual operation counts, ledger, status and a terminal artifact inventory.
Review the scientific disposition as well as execution completion. The observed
input vector itself is not exported by this command.

## Deferred work

After this observed run and its interpretation are complete, address automated
per-pulsar ingestion and calibration as the next expansion. Do not implement it,
add targets or generalize the current first-search adapter during preparation.

## Preparation verification

The current suite passed 424 checks (8 historical checks deselected). Six focused
adapter checks cover exact grid reconstruction, masked-peak selection, threshold
equality, nonfinite input, execution acknowledgment before data access, duplicate
intent rejection and terminal preservation after a setup failure. These focused
checks also passed after adding explicit file/directory synchronization to the
exclusive intent write; the numerical analysis was unchanged by that adjustment.

One synthetic integration case exercised the actual new analysis function through
the repaired context, TOA construction, scanner and both solvers. It used a
separate seed and a 2-microsecond signal at the grid cell nearest 1,000 days.
It completed in approximately 150 seconds with one scan, two primary fits and one
solver audit; the signal was recovered at the injected grid cell and all fit/audit
checks passed. No observed residual vector was supplied to this check.

The 365.25-day exclusion maps to zero-based grid index 65, period
364.6792403682897 days. The complete 953-cell grid and exact mask mapping are
included in the prepared package. Its check command recomputes the bindings from
saved qualification records and verifies current source, inputs and environment.

Compact receipt: `results/qualification/b1937-observed-preparation.json`.
The package, synthetic evidence and detailed logs live under
`../Project Recherche Data/observed-preparation-20260908/`.

## Observed terminal result, 2026-09-08

The single scan evaluated all 953 frequencies. The strongest eligible peak was
also the global maximum: index 195, period **138.38134846979844 days**, statistic
**12.756696672532273**. It did not exceed the unchanged **22.485020743823544**
threshold. Disposition: **NO_TRIGGER**. No candidate was generated and the
conditional ordinary/joint fits and solver audit were correctly not executed.
Actual accounting: one scan, zero primary fits, zero solver audits.

This means no qualifying circular periodic signal was found in the specified
30–2,000-day search with its frozen noise model and annual exclusion. It does not
establish absence of planets or other companions. No false-alarm probability or
companion upper limit was estimated. The 138.38-day maximum is below threshold
and is not a candidate detection.

All 10 terminal-listed artifacts matched the exact file set, sizes and hashes.
The package, source, inputs, threshold, mask and single intent matched their
bindings. The selected peak and threshold decision were independently reproduced
from the saved periodogram without another scan or fit. The ledger is inactive;
resource verification passed, network attempts were zero and unexpected material
warnings were zero. Both formal qualification results remain unchanged.

- Execution source: `244719ca6fbb685dad3a4421677cdfe68ff6250a`.
- Package SHA-256: `9d739084cee43fd98a45fda67e254c647361b994c2d306f37378312d6388edb3`.
- Terminal receipt: `results/observed/b1937-20260908-terminal-verification.json`.
- Backup receipt: `results/observed/b1937-20260908-backup.json`.
- Archive: `../Recherche Recovery/20260907T223404/b1937-first-observed-terminal-20260908.tar`.

The archive's 15 files were verified by content and source-after hashes. The
30-minute monitor is paused following terminal review. No run is active. Future
pulsar ingestion/calibration automation is now the next deferred expansion for
owner consideration; it has not been started by this launch or closeout.
