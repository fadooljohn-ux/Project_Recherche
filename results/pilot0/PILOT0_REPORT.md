# Pilot 0 completion report

## Decision

Pilot 0 **successfully validates the bounded timing, injection, recovery,
cross-check, and provenance machinery on PSR J1744-1134**. It also finds two
load-bearing limitations that must govern the next phase: the current residual
periodogram is uncalibrated and annual signals are nearly singular with fitted
astrometry. Pilot 0 therefore supports proceeding to a calibration phase, but
does **not** yet authorize a blind real-data companion search or a discovery
claim.

## Program scorecard

| Capability tested | Outcome | What the outcome means |
|---|---|---|
| Published-solution reproduction (G2) | **PASS** | Controlled release data and PINT reproduce the timing baseline |
| Zero-injection integrity (C0) | **PASS** | The injection/refit path preserves authoritative times at zero delay |
| Initial strong-control grader (C1) | **FAIL, CORRECTED** | The strongest-peak gate was unreliable and WaveX conflicted with PLRedNoise |
| Corrected strong control (C1-R1) | **PASS** | Compatible joint recovery reproduced 20 us with independent covariance agreement |
| Lower-amplitude control (C2) | **PASS / ROBUST** | A 5 us, 100-day injection transferred robustly through the corrected model |
| Annual stress (C3) execution | **PASS** | All frozen hard gates and solver checks completed |
| Annual recovery diagnostic | **ROBUST** | A known annual injection transfers after matched-null subtraction |
| Annual identifiability | **NOT ESTABLISHED** | Near-unit astrometric covariance prevents an independent annual claim |
| False-alarm calibration | **NOT TESTED** | The present periodogram cannot assign candidate significance |
| Completeness/sensitivity map | **NOT TESTED** | Three controlled injections do not define detection efficiency |
| Blind real-data search readiness | **HOLD** | Pilot 1 calibration and a new authorization are required |

The Pilot 0 grade is **METHODS PILOT COMPLETE; SCIENTIFIC SEARCH NOT YET
AUTHORIZED**. This is a gate-based result rather than an average score.

## What Pilot 0 established

1. The MacBook Pro can execute the controlled single-pulsar workload with a
   large resource margin. The most demanding frozen case used 338.5 MiB and
   50.84 seconds, far below the 16 GiB and 60-minute caps.
2. High-precision TOA injection is accurate to better than 0.000009
   microseconds in all nonzero cases.
3. The project-owned deterministic circular-signal component coexists with the
   released `PLRedNoise` model and agrees with an explicit full-covariance
   solver.
4. A full timing refit can absorb approximately 71% of a 100-day waveform and
   99.99% of a one-year waveform. Residual amplitude alone is therefore not a
   reliable measure of the physical signal.
5. The C1 failure was caught, retained, and corrected under a new freeze. This
   demonstrates that the protocol can reject invalid methods rather than merely
   producing favorable results.

## Scientific limits carried forward

- The residual periodogram uses diagonal uncertainty weights and does not model
  correlated noise. Its strongest peak and exact-frequency power are
  diagnostics, not false-alarm-calibrated statistics.
- A 365.25-day circular component is correlated up to 0.99997 with astrometric
  parameters and can displace ecliptic latitude by hundreds of formal standard
  deviations. Annual candidates require exclusion, external astrometric
  constraints, or a validated joint prior strategy.
- The pilot covers one pulsar and three nonzero injections at one phase. It does
  not measure population sensitivity, completeness, or occurrence rates.
- No additional pulsar, real-data candidate search, or companion interpretation
  is authorized by this report.

## Next phase: Pilot 1 calibration

Pilot 1 should be frozen and reviewed in design form before execution. Its
minimum scope is:

1. Define a compact period-amplitude-phase injection grid that samples interior
   periods, known boundary behavior, and an annual exclusion zone.
2. Replace or augment the diagonal residual periodogram with a
   correlated-noise-aware likelihood or generalized least-squares statistic.
3. Run matched nulls and injections to estimate empirical false-alarm rates,
   recovery probability, amplitude/phase bias, and astrometric displacement.
4. Predefine candidate vetoes, annual handling, and the criterion for opening a
   blind real-data analysis.
5. Benchmark the batch on the MacBook, then move the unchanged repository and
   external data root to the Mac mini/NAS when the grid becomes operationally
   larger.

The immediate next action is review and merge of the C3/Pilot 0 record. The
first post-merge action should be a design-only Pilot 1 protocol and cost/run
count estimate; no batch execution should begin until that protocol is frozen.
