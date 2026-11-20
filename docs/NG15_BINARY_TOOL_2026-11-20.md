# NANOGrav 15-year binaries: the two orbit treatments wired in

**20 November 2026. Owner instruction "Proceed with Nanograv." A new tool
and a preparation-only development check. Nothing was calibrated, frozen or
searched; no periodogram was computed. Searching any target needs a new
root and a new owner instruction.**

## What was built

`tools/ng15_binary.py` (`tools/recherche ng15-binary
select|prepare|calibrate|freeze|run --data ROOT`). It uses the September
wideband preparation (`tools/binary_wideband.py`, unchanged: released noise
covariance, per-epoch dispersion, every free column projected) and adds,
per target and opt-in:

- `--reexpress`: the [small-eccentricity re-expression](ORBIT_REEXPRESSION_2026-11-20.md)
  of DD orbits, with its equivalence check;
- `--shapiro-basis`: the [verified Shapiro basis](SHAPIRO_BASIS_2026-11-20.md)
  in place of free Shapiro parameters.

The checks and limits are the ones used for the MeerKAT binaries (analytic
derivative within 0.1%, non-linearity and basis remainder below 0.1 TOA
sigma, fitted orbit within three checked uncertainties, full rank). Search
range: from the larger of 30 days and ten inner periods up to the smaller
of 2,000 days and half the span.

Three things specific to this release:

- **Unused orbital terms.** NANOGrav DD files list every DD term (OMDOT,
  PBDOT, GAMMA and others) even when it is zero and not fitted, and the
  re-expression refuses those names. The tool removes a term only when its
  value is exactly zero and it is not fitted, and records which; a non-zero
  or fitted term still refuses.
- **Sign of the Shapiro change.** Wideband residuals carry dispersion rows
  as well as arrival-time rows. Before building the basis the tool checks,
  on the data layout itself, that a change in orbital delay appears in the
  arrival-time residuals with a definite sign (to 0.1%) and leaves the
  dispersion rows untouched.
- **A derivative repair.** The pinned timing library's ELL1 Shapiro
  derivative omits a term for every orbital parameter. The September
  repair was applied only when M2 and SINI were fitted. With the Shapiro
  basis they are frozen, so the first run of the control J1614−2230 was
  held on the period derivative (0.12% against 0.1%). The repair is now
  applied whenever the model carries a Shapiro delay.

`--development` at selection marks a root that cannot be calibrated, frozen
or run.

## Development check (preparation only)

Root `../Project Recherche Data/ng15-binary-dev3-20261120`: the 24
unsearched NANOGrav binaries that passed the
[inventory screen](BINARY_INVENTORY_2026-11-20.md) without a model
translation, plus two controls.

**Controls.** J1738+0333 reproduces its September preparation (identical
times, design and residuals; covariance equal to 4 parts in 10⁸).
J1614−2230, searched in September with fitted Shapiro parameters, also
prepares with the Shapiro basis (2 columns, 0.009 TOA sigma unremoved).

**New targets: 22 of 24 pass the timing checks.**

| Target | Released → searched | Treatment | TOAs, span | Range would be (days) | Notes |
|---|---|---|---|---|---|
| J2017+0603 | ELL1 | Shapiro basis (4) | 154, 8.3 y | 30–1,520 | |
| J1741+1351 | ELL1 | Shapiro basis (3) | 208, 9.1 y | 163–1,653 | |
| J1811−2405 | ELL1 | Shapiro basis (3) | 103, 3.5 y | 63–631 | held in MeerKAT data |
| J1918−0642 | DD → ELL1 | both (2) | 487, 15.5 y | 109–2,000 | |
| J1012−4235 | DD → ELL1 | both (3) | 65, 3.4 y | 380–614 | |
| J2302+4442 | DD → ELL1 | both (5) | 236, 8.1 y | 1,259–1,485 | orbit shift 2.5 of 3 |
| J1630+3734 | DD → ELL1 | both (3) | 71, 3.5 y | 125–632 | null chi-square 1.44 |
| J1600−3053 | DD → ELL1 | both (5) | 481, 12.5 y | 143–2,000 | |
| J1745+1017 | ELL1 | none | 91, 4.5 y | 30–830 | no Shapiro terms |
| J0610−2100 | ELL1 | none | 214, 3.4 y | 30–615 | no Shapiro terms |
| J0406+3039 | ELL1 | none | 71, 3.6 y | 70–651 | no Shapiro terms |
| J0437−4715 | DD → ELL1 | re-expression | 117, 4.8 y | 57–868 | no Shapiro terms |
| J0709+0458 | DD → ELL1 | re-expression | 91, 4.6 y | 44–834 | no Shapiro terms |
| J1022+1001 | DD → ELL1 | re-expression | 116, 5.6 y | 78–1,014 | no Shapiro terms; null chi-square 1.38 |
| J0605+3757 | DD → ELL1 | re-expression | 47, 3.4 y | 557–615 | no Shapiro terms; narrow range |
| J2033+1734 | DD → ELL1 | re-expression | 133, 7.0 y | 563–1,273 | no Shapiro terms |
| J1910+1256 | DD → ELL1 | re-expression | 216, 11.4 y | 585–2,000 | no Shapiro terms |
| J1455−3330 | DD → ELL1 | re-expression | 357, 15.7 y | 762–2,000 | no Shapiro terms |
| J2229+2643 | DD → ELL1 | re-expression | 151, 7.0 y | 930–1,284 | no Shapiro terms |
| J1955+2908 | DD → ELL1 | re-expression | 173, 9.0 y | 1,173–1,652 | no Shapiro terms |
| J1643−1224 | DD → ELL1 | re-expression | 478, 15.7 y | 1,470–2,000 | no Shapiro terms |
| J1802−2124 | ELL1H | none | 126, 3.5 y | 30–631 | **see below: earlier hold stands** |

Held: **J1853+1303** (the data prefer Shapiro values outside the checked
region; expected chi-square change 10.2) and **J1640+2224** (the
re-expressed orbit needs a shift of 16 checked uncertainties in the time
of ascending node).

Other figures: the re-expressed models reproduce the released ones to
between 1e-8 and 0.01 of the TOA uncertainty (limit 0.1); the Shapiro
basis leaves at most 0.082; null reduced chi-square is 0.96–1.16 except
J1802−2124 (1.22), J1022+1001 (1.38) and J1630+3734 (1.44).

## What is not settled

1. **Fourteen of the 22 have no Shapiro terms in the release.** In
   September the owner adopted a conditional rule for such NANOGrav
   targets: an explicit omitted-Shapiro branch with synthetic leakage
   scenarios before calibration
   ([assessment](ELL1_OMITTED_SHAPIRO_ASSESSMENT_2026-09-09.md)). The new
   tool does not run that step. The MeerKAT batches searched such targets
   without it. Which rule applies here is the owner's decision; until
   then these fourteen pass the timing checks only.
2. **J1802−2124 keeps its September adequacy hold** (orbital structure and
   unresolved red noise). Passing this tool's checks does not lift it.
3. **Eight targets have measured Shapiro terms and pass everything this
   tool checks:** J2017+0603, J1741+1351, J1811−2405, J1918−0642,
   J1012−4235, J2302+4442, J1630+3734, J1600−3053.
4. Elevated null chi-square (J1022+1001, J1630+3734) means the released
   noise model does not fully describe the data; a search would carry the
   usual noise-adequacy flag and any crossing would go to the second stage.
5. Several ranges are narrow or long-period only because the inner orbit
   is wide (ten inner periods is the lower limit).

## A note on today's MeerKAT batch

The same derivative omission was present in
[batch 04](MPTA_BINARY04_2026-11-20.md) for the three ELL1 targets with
frozen M2 and SINI. It was inside the checks: the largest derivative error
was 0.04% (J1614−2230, limit 0.1%) and the part of an orbital-period error
left unprojected was at most 0.009 TOA sigma (limit 0.1). The results stand
and nothing is rerun. `tools/mpta_binary.py` is unchanged; a future MeerKAT
batch with such targets should apply the repair first.

## Earlier development roots

- `ng15-binary-dev-20261120`: selection stopped at the unused-term
  refusal; incomplete (no `selection.json`). A safety check blocked its
  removal, so it is left in place for the owner to delete.
- `ng15-binary-dev2-20261120`: superseded (before the derivative repair
  change). Same 22 passes; the J1614−2230 control was held.

None of the three roots may be calibrated, frozen or run.

## Evidence

`results/research/ng15-binary-dev-20261120/closeout.json`;
`tools/ng15_binary.py`, `tests/test_ng15_binary.py` (7 tests, synthetic
files only).
