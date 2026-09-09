# Amendments

## A001 — Specify Gate G2 numerical floor

- **Recorded:** 2026-08-09, before the first G2 refit.
- **Change:** Freeze the numerical comparison floor at 64 units in the last
  place of each released parameter value, evaluated as a NumPy `longdouble` in
  that parameter's native PINT unit. Gate G2 uses the larger of this floor and
  three times the released parameter uncertainty.
- **Reason:** The v0.1 scope required a frozen numerical tolerance but did not
  encode its formula. The 64-ULP floor handles representation-level roundoff;
  it does not widen the scientific 3-sigma acceptance band.
- **Additional clarification:** The 5-percent RMS comparison uses the released
  model's residual RMS recomputed from the controlled TOAs in the locked
  environment, because the release parameter file records chi-squared but not
  RMS.
- **Scientific scope:** No target, data, fit parameter, injection, phase, seed,
  or scientific acceptance multiplier changed.

## A002 — Freeze Stage C trigger and authorize C0 only

- **Recorded:** 2026-08-09, after G2 review/merge and before the first C0 run.
- **Authorization:** C0 matched null only. C1-C3 remain blocked.
- **Trigger grid:** Weighted generalized Lomb-Scargle over post-refit TOA
  residuals from 30 days to half the observation span, requiring at least two
  cycles. Frequencies are spaced at one fifth of an independent Fourier bin;
  one independent bin is the inverse observation span.
- **Weights and grader:** Use diagonally scaled TOA uncertainties for the
  exploratory trigger. At its strongest frequency, fit a weighted linear
  constant-plus-sine-plus-cosine model and record amplitude and diagonal
  chi-squared improvement.
- **Null disposition:** C0 has no injected frequency, recovery requirement, or
  calibrated detection threshold. Its strongest peak is recorded as a
  diagnostic artifact and later serves as an empirical comparator for C1.
- **Claim boundary:** Correlated-noise calibration, Gaussian false-alarm
  probability, and discovery interpretation remain prohibited.
- **Reason:** The v0.1 scope specified a weighted periodogram and one-Fourier-bin
  grading but did not freeze the search range, sampling, or null disposition.

## A003 — Authorize C1 and freeze waveform and joint grader

- **Recorded:** 2026-08-09, after C0 review/merge and before the first C1 run.
- **Authorization:** C1 strong positive control only. C2-C3 remain blocked.
- **Research framing:** Project Recherche is a real research-method and analysis
  tool under validation, not an educational exercise. Pilot-stage claim limits
  describe evidentiary maturity, not the project's intended use.
- **Waveform:** Add a positive arrival-time delay of
  `A sin(2 pi (TDB_MJD - 56078.0) / P + phase)` using pre-injection barycentric
  `tdbld` values. C1 retains the frozen P=100 days, A=20 microseconds, and
  phase=1.0471975511965976 radians. Maximum application error is 0.001
  microseconds.
- **Blind recovery gate:** The strongest frozen-grid periodogram feature must
  fall within one independent Fourier bin of the injected frequency and exceed
  the exact-frequency C0 power and amplitude.
- **Joint grader:** Add a PINT `WaveX` component at exactly 0.01 per day with
  epoch 56078.0 MJD TDB. Fit its sine and cosine coefficients jointly with the
  same 179 timing parameters and fixed release noise model.
- **Matched-null comparison:** In the same locked execution, run the identical
  joint `WaveX` fit on C0 TOAs. C1 must produce larger joint amplitude and
  larger full-model chi-squared improvement than this C0 joint comparator.
- **Transfer measurement:** Report phase-aware C1-minus-C0 complex amplitudes
  before and during the joint model fit, plus standard-timing-model absorption.
- **Claim boundary:** No false-alarm probability or discovery interpretation is
  assigned by C1.

## A004 — Authorize C1-R1 corrective recovery gate

- **Recorded:** 2026-08-09, after the failed C1 record was reviewed and merged,
  and before the first C1-R1 run.
- **Authorization:** C1-R1 only. The C1 injection waveform is unchanged. C2-C3
  remain blocked.
- **Root-cause correction:** Replace PINT `WaveX`, which PINT 1.1.5 identifies
  as incompatible with the release `PLRedNoise` component, with the
  project-owned `ProjectCircularSignal`. This is a two-parameter deterministic
  physical delay component, not a second red-noise representation. The release
  covariance model remains fixed.
- **Joint recovery gate:** Fit `CSSIN` and `CSCOS` at the fixed 0.01-per-day
  frequency and MJD 56078.0 TDB epoch jointly with the same 179 timing
  parameters. After phase-aware subtraction of the same-run C0 coefficients,
  require 95-105 percent amplitude recovery, absolute phase error no greater
  than 0.01 radians, and greater chi-squared improvement than C0.
- **Independent cross-check:** Repeat the injected-data joint fit with
  `WidebandTOAFitter` using the explicit full covariance matrix. Require the
  full-covariance and normal low-rank solvers to agree within 0.01
  microseconds in amplitude, 0.001 radians in phase, and 0.1 in chi-squared.
- **Residual-frequency gate:** The exact 100-day diagonal periodogram power and
  amplitude must exceed their authoritative C0 values. The global strongest
  peak is retained as an uncalibrated diagnostic and is not an acceptance gate.
- **Warning gate:** No material warning may be dispositioned away. The expected
  controlled clock overrides and documented PINT covariance-axis label remain
  the only pre-dispositioned warnings.
- **Claim boundary:** C1-R1 validates recovery machinery only. It assigns no
  false-alarm probability and supports no discovery claim.

## A005 — Authorize C2 lower-amplitude boundary diagnostic

- **Recorded:** 2026-08-09, after the passing C1-R1 record was reviewed and
  merged, and before the first C2 run.
- **Authorization:** C2 only: the frozen 100-day, 5-microsecond circular delay.
  C3 remains blocked.
- **Scientific role:** C2 measures lower-amplitude transfer through the now
  validated recovery machinery. It is a boundary diagnostic, not a hard
  positive-control gate or a calibrated detection-efficiency trial.
- **Hard execution gates:** Require exact configuration/code/environment
  freeze, accurate injection and unchanged TOA count, converged ordinary and
  compatible C0/C2 joint fits, preserved `PLRedNoise` with no `WaveX`, explicit
  full-covariance completion and solver agreement, no material warnings,
  finite diagnostic periodogram, and compliance with resource caps.
- **Recovery classification:** After phase-aware C0 subtraction, classify
  recovery as `robust` for 0.8-1.2 amplitude fraction and no more than 0.1
  radians phase error; `partial` for 0.25-1.5 amplitude fraction and no more
  than 0.5 radians phase error when the robust bounds are not met; otherwise
  `inconsistent`. This classification is diagnostic and cannot change the
  hard execution outcome.
- **Frequency diagnostics:** Report whether exact 100-day residual amplitude
  and power exceed C0. Retain the global strongest peak as uncalibrated context.
  Neither comparison is a false-alarm probability or hard gate.
- **Next gate:** C3 may be considered only after the complete C2 diagnostic is
  reviewed and merged, regardless of which preregistered recovery class C2
  produces.

## A006 — Authorize C3 annual-absorption and identifiability stress test

- **Recorded:** 2026-08-09, after the robust C2 diagnostic was reviewed and
  merged, and before the first C3 run.
- **Authorization:** C3 only: the frozen 365.25-day, 20-microsecond circular
  delay. This is the final Pilot 0 injection case.
- **Scientific role:** Separate three questions that are easily conflated at a
  one-year period: whether the ordinary timing model absorbs the injection,
  whether matched-null joint fitting transfers the known injection, and
  whether an unknown annual signal is independently identifiable from
  astrometry.
- **Matched controls:** Run same-execution C0 and C3 ordinary fits, compatible
  low-rank joint fits, and explicit full-covariance joint fits. Recovery is the
  phase-aware C3-minus-C0 coefficient difference within each solver.
- **Recovery classification:** Retain the C2 preregistered `robust`, `partial`,
  and `inconsistent` amplitude/phase bands. Classification is diagnostic, not
  a hard execution gate.
- **Astrometric displacement:** Compare C3 and same-run C0 ordinary-fit values
  for PX, ELONG, ELAT, PMELONG, and PMELAT in units of the C0 postfit
  uncertainty. Classify the maximum as `small` below 3 sigma, `material` from
  3 to below 10 sigma, and `severe` at 10 sigma or above.
- **Ordinary-model absorption:** Classify the phase-aware residual transfer as
  `limited` below 50-percent absorption, `material` from 50 to below 80
  percent, and `strong` at 80 percent or above.
- **Annual identifiability:** Record the low-rank correlation submatrix joining
  CSSIN/CSCOS to the five astrometric parameters. Classify maximum absolute
  correlation as `low` below 0.5, `moderate` from 0.5 to below 0.8, and
  `strong` at 0.8 or above. Strong coupling precludes an independent annual
  identification claim even if matched-null injection transfer is robust.
- **Solver stability:** Compare low-rank and explicit full-covariance
  matched-null recovery. Classify `stable` within 0.01 microseconds, 0.001
  radians, and 0.1 in chi-squared-improvement difference; otherwise
  `sensitive`. Completion and finite outputs are hard gates; agreement class is
  diagnostic.
- **Claim boundary:** No false-alarm probability or companion interpretation is
  permitted. C3 completes Pilot 0 injection validation but does not authorize a
  blind real-data search.
