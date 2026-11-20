# Leakage test for the 13 NANOGrav binaries without Shapiro terms

**20 November 2026. Owner instruction "2. Test first. Run the leakage test on
the 13." Synthetic delays on the real sampling only: no observed residuals
loaded, no observed periodogram, nothing calibrated or searched.**

## What the test asks

These thirteen released models carry no Shapiro-delay terms. The delay is
still in the data. The released orbit has absorbed most of it; the question
is how much of the rest could appear as a periodic signal in the outer-period
search.

## Method

`tools/omitted_shapiro_leakage.py`, the September test
([record](ELL1_OMITTED_SHAPIRO_PREPARATION_2026-09-09.md)) generalized to
targets with no optical constraint:

- Companion mass from the binary mass function for pulsar masses 1.4 and
  2.0 M☉ at inclinations 30°, 60°, 75°, 85° and 88°: ten physically
  consistent scenarios per target.
- For each, the Shapiro delay at the real arrival times, projected with
  every nuisance column the search uses, then scanned across the whole
  search grid of the development preparation.
- Declared before the run: leakage is negligible when the largest
  statistic over the scenarios up to 85° is at most 0.1 (search thresholds
  are about 21–25). The 88° scenarios are reported as stress cases.

## Result: 3 of 13 pass

| Target | Inner period (days) | Largest statistic up to 85° | At 88° | Outcome |
|---|---:|---:|---:|---|
| J1745+1017 | 0.73 | 0.013 | 0.020 | negligible |
| J0605+3757 | 55.7 | 0.014 | 0.019 | negligible |
| J1643−1224 | 147.0 | 0.030 | 0.052 | negligible |
| J1955+2908 | 117.4 | 0.21 | 0.25 | not negligible |
| J0610−2100 | 0.29 | 0.24 | 0.34 | not negligible |
| J0406+3039 | 6.96 | 1.9 | 2.4 | not negligible |
| J2229+2643 | 93.0 | 2.3 | 2.6 | not negligible |
| J2033+1734 | 56.3 | 5.6 | 7.9 | not negligible |
| J0709+0458 | 4.37 | 7.1 | 11 | not negligible |
| J1910+1256 | 58.5 | 18 | 24 | not negligible |
| J1022+1001 | 7.81 | 60 | 103 | not negligible |
| J1455−3330 | 76.2 | 238 | 529 | not negligible |
| J0437−4715 | 5.74 | 454 | 917 | not negligible |

In every case the largest value is the 85° scenario: the test is driven by
how edge-on the orbit is allowed to be.

**Control.** J1738+0333, run through the same generic grid, gives 7.6 and
would fail. In September, with its measured inclination of 32.6°, the same
calculation gave 0.04 and it was searched. So the generic grid is
conservative: a target fails here unless something limits its inclination.

## Reading

- **J1745+1017, J0605+3757 and J1643−1224** meet the September rule on the
  generic grid and can be proposed for a search.
- **The other ten are held.** For them an unmodelled Shapiro delay could
  produce a statistic from 0.2 to several hundred if the orbit is close to
  edge-on. That is not evidence that it does; it means the search could not
  tell.
- Two routes could release some of the ten, neither built or run:
  1. **Literature inclinations**, as for J1738+0333 and J1012+5307 in
     September. J0437−4715 has a well-known published inclination;
     the others would need a literature check.
  2. **An omitted-Shapiro nuisance basis**: project the whole family of
     possible Shapiro delays, as the Shapiro basis does for fitted ones.
     This costs some sensitivity and would need its own verification.

## Limits

- A grid of ten scenarios, not a posterior or a continuous bound.
- Phase and nuisance design fixed at the released (or re-expressed) model.
- The statistic is the deterministic part only; it also has a cross term
  with noise or a real signal.
- The 0.1 limit and the 85° deciding inclination are choices made for this
  test, declared before it ran. September's precedent was 0.04 accepted
  and 1.24 not.

## Evidence

`results/research/omitted-shapiro-leakage-20261120/leakage.json`;
`tools/omitted_shapiro_leakage.py`, `tests/test_omitted_shapiro_leakage.py`.
Preparations used: `../Project Recherche Data/ng15-binary-dev3-20261120`
(development root; not to be calibrated, frozen or run).
