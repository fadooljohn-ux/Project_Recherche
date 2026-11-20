# J0740+6620, J2043+1711 and J0613−0200: nonlinear verification, calibration and searches

**17–18 November 2026 (UTC). Each target was verified on simulated data,
prepared, calibrated, frozen and searched once. J0740 and J0613: `NO_TRIGGER`.
J2043: threshold crossing, reviewed and graded `INCONCLUSIVE_NOISE_SENSITIVE`.
All three `run01` destinations are consumed; do not rerun.**

Owner instruction, 17 November 2026: "Proceed with the surrogate checks for the
three candidates along with preparation and calibration. Once complete launch."
These are the three NANOGrav 15-year wideband targets left held after
[J1857+0943](J1857_NONLINEAR_CALIBRATION_2026-11-17.md), using the same
[nonlinear statistic](NONLINEAR_STATISTIC_2026-11-17.md), the same criteria and
the same ±5σ orbit domain. The earlier pilot02 preparation holds are preserved
unchanged.

## What differs from J1857

- **Orbit terms.** Eight instead of seven: `PBDOT` is fitted in these models and
  was added. `SINI` stays last in the list.
- **Surrogate.** Cubic in all eight terms, plus companion mass and inclination
  alone to seventh order (J0740, J2043; 190 terms) or thirteenth order (J0613;
  259 terms, 1200 training points).
- **J0613 box cut.** Five published standard errors below J0613's companion
  mass is negative, and above its inclination is unphysical. The box is cut at
  companion mass ≥ 0 and cos i ≥ 0.05 (inclination ≤ 87.1°) through
  `physical_floors` in the scope, implemented by `BoundedOrbit` in
  `tools/nonlinear_verification.py`. Without floors the behaviour is unchanged.
- **Iteration limit.** J0613's first verification held (`UNCONVERGED_CELLS`):
  one simulated null fit needed 61 iterations against a limit of 60, with no
  change in value. The default limit in `tools/nonlinear_statistic.py` is now
  200 and the second verification passed with none unconverged. The hold
  receipt is kept. J0740 and J2043 were verified with the limit at 60 (they
  used at most 31), and calibrated and searched with 200.
- **Noise.** J0740 and J2043 have no red-noise term in the released model
  (`NO_RELEASED_RED_COMPONENT`). J0613's released 30 red modes are extended to
  256 at the released amplitude and slope.

## Verification on simulated data

No observed residuals were scanned. All three: `NONLINEAR_STATISTIC_VERIFIED`,
no holds.

| Quantity | J0740+6620 | J2043+1711 | J0613−0200 |
|---|---:|---:|---:|
| Surrogate error, worst of 150 unseen points (limit 0.02) | 0.00006 | 0.00001 | 0.0196 |
| Statistic minus native reference, worst | 0.00001 | 0.00001 | 0.0008 |
| Simulated nulls / trial periods | 512 / 233 | 512 / 542 | 512 / 903 |
| Unconverged cells | 0 | 0 | 0 |
| Cells ending on a domain bound | 0 | 0.001% | 0.86% |
| Strong injections located | 20 / 20 | 20 / 20 | 20 / 20 |
| Seconds per simulated vector | 0.72 | 1.66 | 3.68 |

J0613's surrogate error is just inside the limit; this was disclosed to the
owner before calibration.

## Preparation

Null fit of the observed residuals only; no period scan.

| Quantity | J0740+6620 | J2043+1711 | J0613−0200 |
|---|---:|---:|---:|
| TOAs (paired TOA/DM rows) | 360 (720) | 459 (918) | 423 (846) |
| Linear nuisance columns | 120 | 234 | 185 |
| Null chi-square / degrees of freedom | 601.348 / 592 | 714.392 / 676 | 656.693 / 653 |
| Fast minus native chi-square | 3.9e-6 | 8.0e-6 | −1.1e-7 |
| Distance of fitted orbit to nearest bound (σ) | 4.32 | 4.45 | 3.60 |

## Calibration

Policy and seeds from binary pilot02 (three searches, 1% family false-alarm
allowance, 4096 nulls; seeds 2026093000, 2026093002, 2026092900). The
threshold is the larger of the empirical 99% null maximum and the union bound;
the union bound won for all three.

| Quantity | J0740+6620 | J2043+1711 | J0613−0200 |
|---|---:|---:|---:|
| Threshold (union bound) | 22.309642 | 23.998097 | 25.019010 |
| Empirical 99% null maximum | 18.489080 | 20.457685 | 21.301753 |
| Largest of 4096 null maxima | 27.64 | 25.44 | 33.04 |
| Period range searched (days) | 47.7–1152.5 | 30.0–1653.0 | 30.0–2000.0 |
| Trial periods, eligible / total | 222 / 233 | 530 / 542 | 891 / 903 |
| Excluded periods (days) | 329.3–411.6, 180.1–185.9 | 337.3–393.6, 179.7–185.7 | 348.9–382.9, 181.0–184.7 |
| Median worst-phase 95% amplitude (µs) | 0.443 | 0.129 | 0.294 |
| Bounded injection recoveries | 94 / 96 | 94 / 96 | 92 / 96 |
| Null fits ending on a domain bound | 0 | 0 | 18 |

The amplitude curve uses the linearised orbit; injections were scored with the
nonlinear statistic.

## Observed searches

Each ran once into `run01` after its freeze, which binds the profile, the saved
observed residuals, the calibration and seven code files.

| Quantity | J0740+6620 | J2043+1711 | J0613−0200 |
|---|---:|---:|---:|
| Status | `NO_TRIGGER` | `PERIODIC_SIGNAL_CANDIDATE` | `NO_TRIGGER` |
| Peak statistic | 8.191 | 26.871 | 14.391 |
| Peak period (days) | 62.98 | 37.482 | 41.45 |
| Peak amplitude (µs) | 0.189 | 0.089 | 0.169 |
| Threshold | 22.310 | 23.998 | 25.019 |
| Eligible cells above threshold | 0 | 3 (adjacent) | 0 |
| Simulated nulls with a larger maximum | 65.9% | 0 of 4096 | 20.2% |
| Null or peak orbit on the domain bound | No | No | No |
| Completed (UTC, 18 November) | 01:08 | 02:10 | 05:28 |

| File | sha256 |
|---|---|
| J0740 `execution-freeze.json` | `444cd3120cabbc354b5a65fa7b1b4518f46823c592c3d4fb943078395b948218` |
| J0740 `result.json` | `71470b86bda2b6b414842fa3febc4296ce337e6b62598fb2ffa6ce876e52fbea` |
| J0740 `periodogram.npz` | `056fd7328089a1f63efc1ee8034091d3e7be50a6dd6ff33e45cb7ca6dcce14e9` |
| J2043 `execution-freeze.json` | `d5f61dfd8fe123cf68de75b3961fc2b25c0d3d1d2255b67df5f2d184b81fb003` |
| J2043 `result.json` | `6d6742492c8c5a5f8a23ef7d2babb61a64c51e0d6c8f2375d3da65e3ce08f222` |
| J2043 `periodogram.npz` | `991a8c81c4526c25fe7f1e8d64d50cbd3700e9d298ac65e39d021492cb84c085` |
| J0613 `execution-freeze.json` | `19f05a51397fd25c8e135341f9d7269fef8c803f0530acde2634da03ade1c472` |
| J0613 `result.json` | `f185c90a94c7def6027f98256a8ecba3228da6f91866872921d44dbc19b3e31d` |
| J0613 `periodogram.npz` | `36d1e0b3c3551f8f043a59d06eed80210d3ce7fcf781e278f7e186ed197dde74` |

J0740 and J0613 are non-detections above the calibrated amplitudes for the
eligible periods only, under fixed released noise. Their peaks are ordinary
for noise. Fitted orbits stay within 0.5 (J0740) and 0.8 (J0613) published
sigma of the released values in every eligible cell.

## J2043+1711 candidate and review

The crossing is one peak near 37.48 days seen through oversampling, not three
features. The owner asked for a further review ("Assign a subagent to conduct
further review for J2043"). A subagent performed it without rerunning the
frozen search; its report and scripts are in
`results/research/held-nonlinear-20261117/j2043-review/`
([REVIEW.md](../results/research/held-nonlinear-20261117/j2043-review/REVIEW.md)).
The recording agent did not independently rerun its numbers.

**Verdict: weakened — inconclusive and noise-sensitive.**

- **Noise.** The released par-file noise is NANOGrav's maximum-posterior
  wideband noise sample with its red-noise term removed. Restoring that term
  lowers the statistic from 26.87 to 18.18. Over 500 joint white-and-red
  samples of the released chain the median is 19.2 and 91% fall below the
  threshold. Inflating errors by 5.8% also removes the crossing.
- **In its favour.** Reproduced independently (26.87; 0.0892 ± 0.0174 µs);
  same amplitude and phase in halves, thirds and quarters of the span; not
  carried by a few epochs; absent from the DM series; present in the
  narrowband TOAs (23.54). With red noise modelled it is still roughly a
  4σ local feature (0.078 ± 0.019 µs).
- **Against.** Daily aliases (1.0245 and 0.9714 days) fit nearly as well, so
  the period is not determined. Removing either of two epochs takes it below
  threshold. All TOAs are from Arecibo and the narrowband set shares the same
  observations, so nothing on disk is independent. Thresholds were not
  recalibrated under the alternative noise, and the checks were chosen after
  seeing the result.
- **If real.** A circular 37.48-day orbit at 0.266 au implies
  m sin i ≈ 4.0 × 10⁻⁴ Earth masses, about 50 times lighter than the lightest
  known pulsar planet. It is dynamically stable around the inner binary.

Grades (see [candidate grading](CANDIDATE_GRADING.md)): statistical
significance `NOT_ESTABLISHED`; robustness `NOISE_SENSITIVE`; independent
confirmation `UNAVAILABLE`; disposition `INCONCLUSIVE_NOISE_SENSITIVE`. No
simulation tail was computed against the observed statistic with red noise
admitted, so the workbook's exceedance fields are blank. This is the ninth
candidate with this disposition and the same underlying cause: noise held
fixed at released values.

**Update, 18 November 2026.** The [second-stage joint-noise test](JOINT_NOISE_STAGE_2026-11-18.md#stage-3-nonlinear-orbit-and-j20431711),
with its noise grid declared before the run, gives 18.42 against a threshold
of 23.00. The crossing does not survive; the grade is unchanged and the
workbook's exceedance fields are now filled (53 of 1,024).

## Limits

- Fixed released noise; the noise parameters are not re-fitted. J2043 shows
  what this costs.
- Simulated nulls are generated at the published orbit.
- The 5-sigma domain is a numerical domain, not a prior or a posterior; J0613's
  is cut at the declared physical floors.
- Annual and half-year bands and periods outside each stated range were not
  searched.
- Three targets; not general nonlinear-binary qualification.

## Evidence

- `results/research/held-nonlinear-20261117/`: per-target verification
  receipt and scope, preparation receipt and scope, calibration, execution
  freeze and observed result; J0613's first-verification hold receipt;
  `closeout.json` (file hashes); `assessments.json` (J2043 grade); the J2043
  review.
- Scopes: `config/{j0740,j2043,j0613}-nonlinear-{verification,calibration}.json`.
- Working folders: `../Project Recherche Data/nonlinear-held-20261117/` and
  `../Project Recherche Data/j2043-review-20261118/`.

## Next step

None for these targets under the current method; do not rerun. No nonlinear
hold remains. The open decision for the owner is whether to build a
noise-marginalised statistic (noise fitted jointly with the signal, thresholds
calibrated across noise models) before searching anything else; see
[joint-noise improvement](JOINT_NOISE_IMPROVEMENT_2026-09-10.md) for the
September start in that direction and
[the second-stage test](JOINT_NOISE_STAGE_2026-11-18.md) built on 18 November. An independent check of J2043 needs TOAs
from another telescope, which are not on disk.
