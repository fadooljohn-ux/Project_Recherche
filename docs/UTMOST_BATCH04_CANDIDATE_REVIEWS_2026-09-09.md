# Four periodic timing candidates in UTMOST batch 04

Project Recherche · 9 September 2026 · Private bounded review

## Abstract

Twenty-five source-separated UTMOST DR1 searches produced 21 NO_TRIGGER results
and four original threshold crossings. All four consumed results reproduce in
an independent GLS calculation. Expanded red-noise models weaken every candidate.
J1752-2806 retains an interesting conditional noise-family comparison, but is
noise-sensitive and lacks informative independent confirmation. All four remain
INCONCLUSIVE_NOISE_SENSITIVE; none establishes a planetary discovery or global
significance. The master register preserves the original crossings separately
from these assessments.

## Data and method

The original frozen circular searches cover eligible 30–400-day periods with a
conditional 1% allowance shared across 25 datasets. The review reuses those
observations, covariances and timing designs. Each saved scope fixes a seed,
301 local periods within ±10% of the original peak, eight noise alternatives,
512 null realizations and 256 injections before review calculations.
The published red-noise basis is compared with 32 and 64 modes; 64-mode
alternatives change amplitude by factors 0.5/2 or spectral index by −1/+1.
A frequency-to-the-minus-four covariance scaling tests single-band degeneracy;
it cannot distinguish propagation from an orbital delay.

We reproduce the original peak, refine locally, delete every observing day in
turn, compare early and late joint coefficients, remove the recorded clock
anomaly interval MJD 58105–58108, and compare the nearest annual harmonic.
The noise-family objective is chi-square plus log determinant of the covariance
and projected timing normal matrix, keeping the same linear-timing prior measure.
Null and signal noise models are reselected in every simulation. The statistic
at the refined **original candidate** is compared with each simulated global
maximum across the original eligible grid plus local grid and refined period.
A different global residual peak is not silently substituted for the candidate.

Simulations are conditional on the selected noise-only model. The plus-one tail
(k+1)/513 is a finite diagnostic, not a survey-wide FAP, planet probability or
sigma. Original thresholds are not reapplied as discovery thresholds after
changing covariance. Injections use the original fitted waveform and selected
null covariance; period recovery within two days measures this bounded procedure.
No further simulations are launched to improve a grade.

Saved public TPA observations supply a fixed-period comparison, with the phase
reference aligned to UTMOST. These are later, non-overlapping observations already
searched in the TPA campaign. No new blind TPA search is performed. The reported
power is for the exact fitted UTMOST waveform, known TPA covariance and a 1%
fixed-period test. Period and phase extrapolation uncertainty is not integrated,
so coefficient contrasts and power remain conditional diagnostics.

## Original and refined results

| Pulsar | Original period (d) | Original Δχ² / threshold | Refined period (d) | Timing amplitude (µs) |
|---|---:|---:|---:|---:|
| J1359-6038 | 95.9650 | 41.741 / 26.204 | 96.0589 | 22.895 |
| J0908-4913 | 93.1500 | 27.852 / 26.163 | 92.6780 | 49.775 |
| J1048-5832 | 105.0066 | 36.722 / 26.142 | 104.8082 | 199.588 |
| J1752-2806 | 81.7850 | 57.672 / 26.498 | 81.7519 | 137.172 |

The amplitudes are sinusoidal timing delays under the original model; they are
not companion radii or validated orbital parameters.

## Robustness and independent measurements

| Pulsar | Minimum day-deletion Δχ² | Early/late consistency p | Red32 / red64 Δχ² at candidate | Family statistic | Null exceedances | Plus-one tail | TPA conditional power |
|---|---:|---:|---:|---:|---:|---:|---:|
| J1359-6038 | 36.715 | 0.5875 | 7.219 / 7.211 | 7.211 | 480/512 | 93.762% | 91.2% |
| J0908-4913 | 20.924 | 0.0008852 | 6.461 / 6.431 | 6.461 | 495/512 | 96.686% | 79.4% |
| J1048-5832 | 31.711 | 0.2291 | 1.525 / 1.520 | 1.525 | 512/512 | 100.000% | 2.8% |
| J1752-2806 | 49.308 | 0.752 | 1.805 / 2.281 | 25.908 | 0/512 | 0.195% | 29.0% |

### J1359-6038

The approximately 96-day signal survives individual-day and time checks but falls from Δχ² 41.76 to about 7.21 with broader red-noise coverage.

TPA has 91.2% conditional detection power but does not corroborate the waveform (fixed-period Δχ² 1.903; coefficient-contrast p 0.00568). This is informative non-corroboration, not a conclusive exclusion.

Injected periods were recovered within two days in 137/256 cases; 249/256 injected realizations exceeded the candidate's observed family statistic.

### J0908-4913

The approximately 93-day signal weakens from Δχ² 28.29 to about 6.43 with broader red-noise coverage. Early and late coefficients also differ (conditional p 0.000885); one observing-day deletion lowers Δχ² to 20.92.

TPA has 79.4% conditional detection power but does not corroborate the waveform (fixed-period Δχ² 2.318; coefficient-contrast p 0.000526). Extrapolation and noise uncertainty limit exclusion.

Injected periods were recovered within two days in 124/256 cases; 252/256 injected realizations exceeded the candidate's observed family statistic.

### J1048-5832

The approximately 105-day signal collapses from Δχ² 36.74 to about 1.52 with broader red-noise coverage. No simulated global maximum falls below its candidate comparison statistic.

TPA has only 2.8% conditional detection power. Its weak fixed-period response cannot confirm or meaningfully rule out this waveform.

Injected periods were recovered within two days in 71/256 cases; 256/256 injected realizations exceeded the candidate's observed family statistic.

### J1752-2806

The approximately 81.75-day signal survives every day deletion and has compatible early/late coefficients. However, its Δχ² falls from 57.67 to 1.81–2.28 under 32/64-mode red noise. The model-selected comparison retains statistic 25.91, with 0/512 null exceedances, because the preferred signal model returns to the released covariance while the preferred null uses steeper 64-mode noise. This model dependence warrants NOISE_SENSITIVE despite the interesting conditional tail.

TPA has only 29.0% conditional detection power and no fixed-period support. That non-detection is underpowered and does not settle the candidate.

Injected periods were recovered within two days in 151/256 cases; 17/256 injected realizations exceeded the candidate's observed family statistic. The 1/513 (0.195%) plus-one tail is the resolution floor of this diagnostic, not zero FAP or a discovery significance. Low injected exceedance power (17/256) also shows the limitations of this selection procedure.

## Assessment and evidence

All four grades are **NOT_ESTABLISHED / NOISE_SENSITIVE** for significance and
robustness. Independent confirmation is **NOT_CORROBORATED** for J1359-6038 and
J0908-4913, and **UNDERPOWERED** for J1048-5832 and J1752-2806. Their disposition is
INCONCLUSIVE_NOISE_SENSITIVE. J1752-2806 merits retaining as a follow-up priority
if more informative independent observations become available; this review does
not authorize another search or automatic expansion of the noise family.

Every original result, periodogram, calibration and threshold remains unchanged.
The reusable review runner is `tools/utmost_candidate_review.py`; it refuses
completed simulations. Target scopes and steps 1–4 are saved under:

- [J1359-6038 evidence](../results/research/j1359-deep-review-20260909/scope.json) and `step1.json` through `step4.json`; simulation arrays remain in the corresponding external data directory.
- [J0908-4913 evidence](../results/research/j0908-deep-review-20260909/scope.json) and `step1.json` through `step4.json`; simulation arrays remain in the corresponding external data directory.
- [J1048-5832 evidence](../results/research/j1048-deep-review-20260909/scope.json) and `step1.json` through `step4.json`; simulation arrays remain in the corresponding external data directory.
- [J1752-2806 evidence](../results/research/j1752-deep-review-20260909/scope.json) and `step1.json` through `step4.json`; simulation arrays remain in the corresponding external data directory.

The [batch closeout](UTMOST_BATCH04_2026-09-09.md) records input repair and run history. The [grading manifest](../results/research/candidate-grading-utmost-batch04-20260909/assessments.json) binds each original result and review step by SHA-256. No publication or visibility change accompanies this report.
