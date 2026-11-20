# Nonlinear Shapiro-delay treatment (2026-11-20)

Owner instruction: "Proceed with 1" (build the nonlinear Shapiro-delay
treatment). This is method development. **No search was run.**

## Why

The search removes the inner orbit by projecting one derivative column per
free orbital parameter. That is valid only where the arrival times are linear
in the parameter. Shapiro-delay shape parameters (M2/SINI, H3/STIGMA, H3/H4)
are often too uncertain or too curved, so twelve targets were held on them.

## What it does (`tools/shapiro_basis.py`)

The free Shapiro parameters are frozen at the released values, and the whole
set of values the data could still allow is removed instead of a tangent:

1. **Neighbourhood.** Every physical combination of the Shapiro parameters
   whose change in arrival times, after the projection the search applies, is
   within 3 sigma of the released model under the search covariance (expected
   chi-square change at most 9), together with the box of three released
   uncertainties. Sampled on a 41-point grid per parameter.
2. **Basis.** The leading principal directions of those arrival-time changes
   are added to the design as nuisance columns (2–5 columns in practice).
3. **Acceptance.** At 64 independent random points of the neighbourhood, what
   the basis leaves unremoved must be below 0.1 TOA sigma, the same bound as
   the local-linearity check. The values the data prefer (chi-square minimum
   over the whole sampled grid, no periodogram) must lie inside the
   neighbourhood, or the target is held.

All existing checks still apply unchanged to the other orbital parameters.
Use: `tools/recherche mpta-binary select ... --shapiro-basis [TARGET ...]`
(and `--reexpress [TARGET ...]`; no names means every listed target).

## Differences from the linear method that the owner should know

- **The neighbourhood is joint, not a per-parameter box.** For one linear
  parameter it is exactly ±3 uncertainties under the search covariance (a
  test checks this). For two correlated parameters it follows their
  correlation. A per-parameter box was tried first and rejected: for poorly
  constrained inclinations it reaches edge-on orbits with a large companion
  mass, which the data exclude by hundreds of sigma.
- **Physical limits.** SINI stops at 1 − 5e-7 and STIGMA at 0.999 (both
  cos i ≈ 1e-3); STIGMA stops at 0.02 below because the H3/STIGMA form is
  singular face-on; M2 is non-negative.
- **Cost.** Each basis column removes one more direction from the data, at
  harmonics of the inner orbit. The calibration and the reported limits
  account for it.

## Two corrections made during development

The first development run (`mpta-shapiro-dev-20261120`, kept) exposed two
flaws in the treatment itself, both corrected before the second run:

- STIGMA was sampled down to 0, where the delay is not finite (two targets
  failed with a numerical error). Bounded at 0.02.
- The basis columns were orthogonal to the rest of the design, which hid the
  correlation between the Shapiro freedom and A1/EPS1/EPS2. Those parameters'
  uncertainties were then too small and two targets showed spurious large
  shifts. The columns now keep that correlation (same span, verified by the
  tests), so the uncertainties are marginal, as in the linear method.

Neither change touches a threshold.

## Simulated test

`tests/test_shapiro_basis.py` (10 tests, simulated Shapiro delays only):
fresh points anywhere in the neighbourhood are removed to the bound,
including an edge-on-reaching case; a linear parameter gets a ±3 sigma
neighbourhood and one column; too few components, data outside the
neighbourhood, a missing uncertainty and an unphysical value are holds.

## Development check on the twelve Shapiro-held targets

Preparation only, in a development root that must not be frozen or run
(`../Project Recherche Data/mpta-shapiro-dev2-20261120/`). Preparation reads
arrival times and residuals; no periodogram was computed.

| Target | Outcome | Basis columns | Left unremoved (TOA sigma) | Range would be (days) |
|---|---|---:|---:|---|
| J1614−2230 | Clears | 2 | 0.078 | 86.9–400 |
| J2145−0750 | Clears | 5 | 0.000 | 68.4–400 |
| J1036−8317 | Clears | 2 | 0.075 | 30.0–400 |
| J1514−4946 | Clears | 2 | 0.072 | 30.0–400 |
| J1543−5149 | Clears | 3 | 0.021 | 80.6–400 |
| J1101−6424 (re-expressed) | Clears | 2 | 0.050 | 96.1–400 |
| J1903−7051 (re-expressed) | Clears | 4 | 0.034 | 110.5–400 |
| J1732−5049 (re-expressed) | Clears | 4 | 0.078 | 52.6–400 |
| J2236−5527 (re-expressed) | Clears | 3 | 0.018 | 126.9–400 |
| J1909−3744 | Still held | – | – | Data prefer SINI at the low edge of the sampled range (expected chi-square change 14.8) |
| J1327−0755 | Still held | – | – | Data prefer H3 at the high edge (expected chi-square change 21.3) |
| J1435−6100 | Still held | – | – | EPS1 needs a shift of 8.2 checked uncertainties (cap 3) |

Null reduced chi-square is 0.98–1.02 for the nine. The three holds mean the
released orbit disagrees with the data under the search covariance by more
than the checked neighbourhood; they are not non-detections.

## Status

None of the nine has been searched with MeerKAT data. J1614−2230 and
J2145−0750 were each searched once in NANOGrav data. Searching needs a new
batch root and a new owner instruction. Evidence:
`results/research/shapiro-basis-20261120/closeout.json`.

## Update: searched

[Batch 04](MPTA_BINARY04_2026-11-20.md) (owner: "Yes search all 9.") searched the
nine cleared targets once each in a new frozen root: all `NO_TRIGGER`.
