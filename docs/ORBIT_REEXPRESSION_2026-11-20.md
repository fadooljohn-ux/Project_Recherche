# Small-eccentricity re-expression of near-circular orbits (2026-11-20)

Owner instruction: "Yes built it" (in answer to whether to build the orbit
re-expression). This is method development. **No search was run.**

## What it does

A nearly circular orbit released in the DD or DDH form has a periastron time
(T0) and angle (OM) that are almost perfectly degenerate, so the linear
treatment of the inner orbit fails its local-linearity check and the target
is held. `tools/orbit_reexpress.py` rewrites the released model in the
small-eccentricity form (ELL1, or ELL1H when the release has H3/STIG):

    TASC = T0 - (OM mod 360)/360 * PB    EPS1 = ECC sin OM    EPS2 = ECC cos OM

A1 is referred to TASC when XDOT is present; every other parameter is carried
unchanged. It refuses anything it does not map (OMDOT, PBDOT, EDOT, GAMMA,
FB terms, T2, an unfitted T0/OM/ECC).

Two rules keep it from being a loosened check:

- **Equivalence check.** The re-expressed model's arrival times must match
  the released model's to within 0.1 TOA sigma after the same projection the
  search applies (the bound of the local-linearity check). The timing
  library's ELL1 carries terms to third order in eccentricity.
- **All existing checks still apply** to every parameter of the re-expressed
  model, unchanged. TASC has no released uncertainty (the released T0 and OM
  uncertainties are almost fully correlated), so it takes the uncertainty
  under the search covariance; EPS1 and EPS2 take first-order propagated
  uncertainties.

Use: `tools/recherche mpta-binary select ... --reexpress` records the
conversion for every listed target (and fails there, before any observation
is read, if a target is not convertible); `prepare` applies it. The module's
hash is bound into receipts and freezes. The normal path is unchanged, but
`tools/mpta_binary.py` was edited, so its hash differs from the one recorded
by batches 01 and 02 (their version is at commit `75c2730`).

## Simulated test

`tests/test_orbit_reexpress.py` (19 tests, simulated orbits only): for
eccentricities 7e-7 to 1.3e-4 and three periastron angles (including a large
negative one) the two forms agree to better than 0.01 sigma of a 100 ns TOA;
an orbit with eccentricity 0.02 is caught by the equivalence check.

## Development check on the seven near-circular held targets

Preparation only, in a development root that must not be frozen or run
(`../Project Recherche Data/mpta-reexpress-dev-20261120/`). Preparation reads
the arrival times and computes residuals for the fitted-shift check; no
periodogram was computed.

| Target | Outcome | Detail |
|---|---|---|
| J1933−6211 | Clears every check | Equivalence 1e-7 sigma; fitted shifts up to 1.6 (cap 3); range would be 128–400 d |
| J2322−2650 | Clears every check | Equivalence 1e-7 sigma; fitted shifts up to 1.2; range would be 30–400 d |
| J1101−6424 | Still held | T0/OM problem gone; STIGMA fails linearity (100 sigma) |
| J1903−7051 | Still held | T0/OM problem gone; STIGMA fails linearity |
| J1732−5049 | Still held | SINI stepped by three uncertainties exceeds 1 |
| J2236−5527 | Still held | SINI stepped by three uncertainties exceeds 1 |
| J1751−2857 | Cannot be searched | Inner period 110.7 d; ten inner periods exceeds 400 d |

So the re-expression clears **two** targets, not the "up to about ten"
estimated beforehand: the three with periastron advance are not mapped (and
two of those have no period range anyway), and four of the seven then meet
the Shapiro-delay holds, which need the nonlinear Shapiro treatment.

## Status

At the time of this check J1933−6211 and J2322−2650 had not been searched.
They were then searched once each on the owner's instruction: see
[batch 03](MPTA_BINARY03_2026-11-20.md). Evidence:
`results/research/orbit-reexpress-20261120/closeout.json`.
