# The translated models against tempo2

**21 November 2026. Owner instruction: "Yes, compare first". Preparation
products and tempo2 pre-fit residuals only: no periodogram, nothing
calibrated, frozen or searched.**

## What was compared

For every Parkes and European binary that passed the third development
check ([record](PTA_BINARY_ADAPTERS_2026-11-21.md)), tempo2 itself (the
isolated runtime the International adapter uses) was run on the **original**
released par and tim files, without a fit. Its residuals were subtracted
from the residuals the search's preparation produced after translation,
Shapiro re-centring, re-expression and refinement. The difference was then
projected exactly as the search projects data (all timing, dispersion,
instrumental and orbital columns, under the search covariance).

Agreement: the largest remaining difference is at most 0.1 of the TOA
uncertainty, the bound already used for the re-expression and
local-linearity checks. Tool: `tools/tempo2_compare.py` with the worker
`tools/tempo2_residuals_export.py`.

## Result: 19 of 20 agree

| Release | Target | Model steps | Before projection (µs rms) | After projection (TOA sigma) |
|---|---|---|---:|---:|
| European | J0613−0200 | translated, re-centred, Shapiro basis | 0.019 | 0.005 |
| European | J0900−3144 | translated | 0.013 | 0.003 |
| European | J1751−2857 | translated, re-expressed, refined | 0.010 | 0.001 |
| European | J1804−2717 | translated | 0.015 | 0.015 |
| European | J1910+1256 | translated, re-expressed, refined | 0.013 | 0.001 |
| European | J1918−0642 | re-expressed, refined, Shapiro basis | 0.014 | 0.002 |
| Parkes | J0125−2327 | none | 0.003 | 0.003 |
| Parkes | J0900−3144 | none | 0.009 | 0.002 |
| Parkes | J1545−4550 | re-centred | 0.074 | 0.002 |
| Parkes | J1933−6211 | none | 0.005 | 0.003 |
| Parkes | J1902−5105 | re-centred, Shapiro basis | 0.004 | 0.001 |
| Parkes | J1045−4509 | translated | 0.129 | 0.000 |
| Parkes | J1446−4701 | translated | 0.086 | 0.004 |
| Parkes | J2129−5721 | translated | 0.284 | 0.002 |
| Parkes | J1643−1224 | translated, re-expressed, refined | 0.035 | 0.004 |
| Parkes | J0614−3329 | translated, re-expressed, refined, Shapiro basis | 0.047 | 0.004 |
| Parkes | J1125−6014 | translated, Shapiro basis | 0.142 | 0.001 |
| Parkes | J1857+0943 | translated, Shapiro basis | 0.095 | 0.010 |
| Parkes | J1909−3744 | translated, Shapiro basis | 0.047 | 0.061 |
| Parkes | **J1603−7202** | translated | **2.12** | **0.44 — differs** |

The translation, the Shapiro re-centring and the refinement are therefore
confirmed against tempo2 on real observing times for every case type that
occurs, including both re-centred targets.

## The one disagreement, and a new guard

**J1603−7202 (Parkes)** carries a chromatic Gaussian event in its released
model (`GAUSEP_1` and three related terms: the known 2006 dispersion
event). tempo2 applies it; the pinned timing library does not implement it
and drops it without an error. The preparation checks did not catch this
(null reduced chi-square 0.96).

The adapter now **holds any target whose released model contains a term the
timing library does not implement** (`pta_binary.unimplemented_terms`).
Applied to all checked targets, it holds:

| Target | Term | Meaning |
|---|---|---|
| Parkes J1603−7202 | GAUS… | chromatic event not modelled |
| Parkes J1909−3744 | TNGROUPNOISE | a system-specific noise term of the release would be missing from the search covariance |
| Parkes J0613−0200 | DM_C1YR, DM_S1YR | annual dispersion terms (already held for another reason) |

J1909−3744 agrees with tempo2 in its residuals (0.061), because a noise
term does not change residuals; but the search would have used an
incomplete noise model, so it is held.

**Earlier searches are not affected.** The guard was run over the
September isolated-pulsar searches of the Parkes, European and Indian
releases: none of those models contains an unimplemented term.

## Where this leaves the Parkes and European binaries

| Release | Verified and ready to propose | Held |
|---|---|---|
| Parkes | 12: J0125−2327, J0900−3144, J1545−4550, J1933−6211, J1902−5105, J1045−4509, J1446−4701, J2129−5721, J1643−1224, J0614−3329, J1125−6014, J1857+0943 | J1603−7202, J1909−3744, J2145−0750, J0613−0200 |
| European | 6: J0613−0200, J0900−3144, J1751−2857, J1804−2717, J1910+1256, J1918−0642 | J0751+1807, J1909−3744, J1857+0943, J1738+0333, J1012+5307 |

None is searched. A search needs a new root, calibration and a new owner
instruction. J0900−3144 appears in both releases; the two data sets are
separate telescopes' records and would be separate searches.

## Limits

- The comparison is of pre-fit residuals. It tests the deterministic model
  and the clock and ephemeris chain, not the noise covariance (hence the
  separate guard).
- tempo2 was run with the release's clock files in the same arrangement the
  September adapter used.
- Not compared: targets held before this step, NANOGrav (its files are in
  the timing library's own format and need no translation), and the
  MeerKAT binaries.

## Evidence

`results/research/tempo2-compare-20261121/` (`epta.json`, `ppta.json`,
`trial.json`); working folders `tempo2-compare-*-20261121` under
`../Project Recherche Data/`; `tools/tempo2_compare.py`,
`tools/tempo2_residuals_export.py`, `tests/test_tempo2_compare.py`.
