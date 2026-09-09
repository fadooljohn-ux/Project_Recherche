# C3 annual-absorption and identifiability stress report

## Decision

C3 **passes every frozen hard execution gate** and completes the Pilot 0
injection sequence, pending review. The matched-null transfer is robust and
stable across covariance solvers, but the annual waveform is **not independently
identifiable** from astrometric parameters in this timing model. This result
validates the test machinery while establishing a scientific exclusion: a
365.25-day candidate cannot support a real-signal claim through this fit alone.

## Scorecard

| Area | Test | Outcome |
|---|---|---|
| Protocol control | v0.7 config/code/environment freeze; C3 only | **PASS** |
| Injection integrity | 433 TOAs; maximum error <= 0.001 us | **PASS** (0.0000086 us) |
| Ordinary execution | Same-run C0 and C3 release-model fits converged | **PASS** |
| Joint execution | Same-run compatible C0 and C3 fits converged | **PASS** |
| Full-covariance execution | Independent C0 and C3 fits completed | **PASS** |
| Warning hygiene | No unexpected material warning | **PASS** |
| Reproducibility | Frozen inputs and external-output hashes verified | **PASS** |
| Resource envelope | <= 60 minutes and <= 16 GiB | **PASS** |
| Scientific authorization | Pilot 0 injections complete; no next case authorized | **PASS** |
| Ordinary-model absorption | Residual transfer after ordinary refit | **DIAGNOSTIC: STRONG** |
| Matched-null annual recovery | Frozen robust/partial/inconsistent classification | **DIAGNOSTIC: ROBUST** |
| Annual identifiability | Maximum signal-to-astrometry correlation | **DIAGNOSTIC: STRONG COUPLING** |
| Astrometric displacement | Maximum C3-minus-C0 shift | **DIAGNOSTIC: SEVERE** |
| Solver stability | Low-rank versus explicit full covariance | **DIAGNOSTIC: STABLE** |
| Exact-frequency comparison | Compare 365.25-day residual with C0 | **DIAGNOSTIC: AT OR BELOW C0** |
| Global strongest peak | Uncalibrated context only | **DIAGNOSTIC** |

Overall hard-gate outcome: **PASS**. The score is not averaged; every hard
execution gate passed. The diagnostic rows describe scientific behavior and do
not convert this result into an annual-signal detection capability.

## Three distinct annual outcomes

The 365.25-day injection had a 20-microsecond amplitude and the frozen phase of
1.0471975512 radians. Its outcome depends on the scientific question being
asked:

| Question | Measurement | C3 outcome |
|---|---:|---|
| Does the ordinary timing fit leave the waveform in residuals? | 0.0001237 recovery fraction | **No: 99.9876% absorbed or redistributed** |
| Can the compatible joint model transfer a known injection after subtracting the same-run null? | 19.9911 us; 0.999555 recovery; 0.000230 rad phase error | **Yes: robust** |
| Is an annual component independently distinguishable from astrometry? | maximum absolute correlation 0.999971 | **No: strong degeneracy** |

These are not contradictory results. Matched-null subtraction measures whether
the controlled injection propagates through a known model. Identifiability asks
whether an unknown real annual signal could be separated from other fitted
parameters. C3 passes the first test and fails the second scientific condition.

## Astrometric covariance and displacement

The strongest covariance was between the circular cosine coefficient and
ecliptic latitude, with correlation -0.9999705. The same coefficient was also
correlated 0.9996980 with parallax and -0.9967296 with ecliptic longitude. The
seven-parameter annual/astrometric covariance submatrix had condition number
approximately 2.04e8.

When the injected data were fitted without an explicit annual component, the
largest shifts relative to the same-run C0 model were:

| Parameter | Shift in C0 uncertainty units | Classification |
|---|---:|---|
| ELAT | 333.52 sigma | Severe |
| ELONG | 83.20 sigma | Severe |
| PX | 3.20 sigma | Material |
| PMELONG | 0.35 sigma | Small |
| PMELAT | 0.02 sigma | Small |

This is the main C3 scientific finding: annual power can be hidden by formally
precise but substantially displaced astrometric estimates.

## Independent covariance cross-check

The explicit full-covariance and primary low-rank solvers agreed on the
matched-null result to within:

- 0.000653 microseconds in amplitude;
- 0.0000145 radians in phase; and
- 0.0000732 in differential chi-squared improvement.

All are inside the frozen 0.01-microsecond, 0.001-radian, and 0.1 stability
tolerances. Both solvers independently reproduced the near-unit astrometric
correlations.

## Residual-frequency diagnostic

After the ordinary fit, the exact 365.25-day residual amplitude was only
0.01098 microseconds, below the same-run C0 comparator of 0.01329
microseconds. The exact-frequency power was also below C0. The strongest
periodogram feature occurred at 30.448 days, the already observed short-period
boundary feature.

Neither value is a detection statistic. This periodogram uses diagonal
uncertainty weights, does not model correlated noise, and has no calibrated
false-alarm probability.

## Resource and provenance checks

- Total runtime: 50.84 seconds.
- Peak memory: 338.5 MiB.
- Unexpected warnings: zero.
- Freeze record: `pilot0-v0.7-stage-c-c3`.
- Full record: `run_records/c3_annual_stress_20260809T025735Z.json` under
  `RECHERCHE_DATA_ROOT`.
- Full-record SHA-256:
  `90f9fd90115f8540b3ebd898e32d0972849f77f96c5f62bea42ebffc09a4d099`.

## Review disposition and next gate

- C3 hard-gate result: **pass**.
- Matched-null recovery: **robust**.
- Annual identifiability: **strongly degenerate with astrometry**.
- Pilot 0 injection sequence: **complete**.
- Review status: **pending**.
- Authorization for a blind real-data search: **false**.

After review and merge, the next phase is Pilot 1 design and calibration. It
must freeze a multi-period, multi-amplitude, multi-phase injection grid; use a
correlated-noise-aware search statistic; estimate empirical false-alarm and
recovery rates; and define an annual exclusion or external-astrometry rule
before any real-data candidate search is authorized.
