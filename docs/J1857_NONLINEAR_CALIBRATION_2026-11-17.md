# J1857+0943: nonlinear preparation, calibration and freeze

**17 November 2026 — prepared, calibrated, frozen and searched once on the
owner's instruction: `NO_TRIGGER` (see [Observed search](#observed-search)).**

Owner decision: "Proceed with the recommended ±5σ". This applies the
[nonlinear statistic](NONLINEAR_STATISTIC_2026-11-17.md) to J1857+0943
(B1855+09), whose pilot02 preparation failed the local-linearity check. That
failure record is preserved unchanged.

## Preparation

Scope: [config/j1857-nonlinear-calibration.json](../config/j1857-nonlinear-calibration.json),
through `tools/recherche nonlinear-calibration prepare`. Inputs, noise coverage
(64 red modes) and the 160 linear nuisance columns are those of the September
prototype. The orbit domain is five published standard errors in each of the
seven orbital/Shapiro terms; inclination stays physical.

- **Surrogate.** On the wider domain a cubic polynomial was not accurate
  enough (error up to 0.36). Adding terms up to seventh order in companion
  mass and inclination alone gives 145 terms and an error of 0.0065 at worst on
  150 unseen points (limit 0.02).
- **Null fit of the observed residuals** (no companion term, no period scan):
  chi-square 555.7905 for 561 degrees of freedom, reduced 0.9907, matching the
  prototype. The orbit moves by at most 0.02 standard errors and sits 4.18
  from the nearest bound. The fast statistic and the native fit agree to
  2.3e-6 in chi-square. Rank 167/167.

## Calibration

`tools/recherche nonlinear-calibration calibrate`, policy and seed from binary
pilot02 (three searches, 1% family false-alarm allowance, 4096 nulls).

| Quantity | Value |
|---|---:|
| Threshold | 22.176555 (union bound) |
| Empirical 99% null maximum, nonlinear statistic | 17.789518 |
| Empirical 99% null maximum, linearised statistic | 17.746141 |
| Trial periods, eligible / total | 207 / 218 |
| Excluded periods | 350.4–378.3 d and 181.0–184.5 d |
| Median worst-phase 95% amplitude | 0.376 microseconds |
| Bounded injection recoveries | 93 / 96 |
| Null fits ending on a domain bound | 0 / 4096 |

Every fit in the 847,872 eligible null cells converged. The threshold is the union bound, as
in every other Recherche search; the empirical quantile is recorded as a
cross-check. Worst-phase amplitude rises from 0.35 microseconds at 150 days to
0.47 at 600, 0.82 at 1200 and 1.34 at 1800 days. That amplitude curve uses the
linearised orbit; the injections were scored with the nonlinear statistic.

## Freeze

`execution-freeze.json` binds the profile, the saved observed residuals, the
calibration and seven code files. `run` refuses to start if any of them
changed, writes only to `run01`, and that destination can be used once.

## Limits

- Fixed released noise, extended to 64 modes; the noise parameters are not
  re-fitted. This is the same limitation behind the eight noise-sensitive
  candidates.
- Simulated nulls are generated at the published orbit.
- The 5-sigma domain is a numerical domain, not a prior or a posterior.
- A threshold crossing would be a candidate for review, not a detection.
- One target; not general nonlinear-binary qualification.

## Evidence

- `results/research/j1857-nonlinear-calibration-20261117/`: preparation
  receipt, scope, calibration, execution freeze and observed result.
- Working folder: `../Project Recherche Data/j1857-nonlinear-20261117/`.

## Observed search

The owner authorized the search on 17 November 2026 ("Launch"). It ran once
into `run01` at 16:01 UTC and that destination is consumed; a second run is
refused because `run01` exists.

| Quantity | Value |
|---|---|
| Status | `NO_TRIGGER` |
| Peak statistic | 10.257274 at 161.50 days |
| Threshold | 22.176555 |
| Peak amplitude | 0.190 µs |
| Eligible cells | 207 of 218 |
| Null fit chi-square | 555.7905 |
| Null and peak orbits on the domain bound | No |

The peak is ordinary for noise: 30.2% of the 4,096 simulated nulls have a
larger maximum (their median is 8.74). The five highest cells are adjacent
periods between 160.6 and 166.2 days. Every fitted orbit stays within 0.75
published sigma of the released values, so the 5-sigma domain did not limit
the result. The 11 excluded cells were not searched; their statistics (at most
5.9) are saved for the record only.

`result.json` sha256 `0893da8cf0bf94f15badca085430ffb18080aed07f377c70b95eac65f977746d`;
`periodogram.npz` sha256 `7a1ad648cd9bc0a99b5ac53e480bf296001b707f003d486aa2f6121cee2d2a74`.

This is a non-detection above the calibrated amplitudes for the eligible
periods only, under fixed released noise. It says nothing about the annual and
half-year bands, periods outside 123–2000 days, or the other held targets.

## Next step

None for J1857. Do not rerun. J0740+6620, J0613−0200 and J2043+1711 were
subsequently verified, calibrated and searched; see
[the held-target record](HELD_NONLINEAR_SEARCHES_2026-11-17.md).
