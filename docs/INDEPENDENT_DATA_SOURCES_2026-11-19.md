# Independent data for J2043+1711 and J1453+1902: where it could come from

**19 November 2026. Web research by a subagent on the owner's instruction
("Do some research on the best sources for independent data for J2043 and
J1453"). Nothing was downloaded and no contact was made. The recording agent
did not re-check the sources; items the subagent could not verify are marked.**

## Finding

No sub-microsecond timing set from a telescope other than Arecibo is publicly
downloadable today for either pulsar. The only independent data precise enough
is FAST (Chinese Pulsar Timing Array, CPTA DR1), which is published but whose
TOAs are not posted; they would have to be requested.

## J2043+1711 (37.48 days, about 0.09 µs)

| Source | Status | Useful |
|---|---|---|
| FAST / CPTA DR1 | In the 57-pulsar sample: 65 epochs over 2.6 years (within April 2019 – September 2022), rms 121 ns, no red noise detected. TOAs not posted; the paper points to FAST's data-request policy. | Yes; the only one. About two-week cadence samples a 37.5-day period; sensitivity of a few tens of ns. Overlaps Arecibo in 2019–2020 but is a different telescope. |
| Nançay | Timing model in the Fermi third pulsar catalogue: 189 TOAs, MJD 55520–57922, rms 1.448 (units not stated). Par file public, TOAs not. | No; about 15 times too coarse. |
| Fermi-LAT gamma-ray PTA | Public (Zenodo 10.5281/zenodo.6374291, CC BY 4.0, 12.5 years). Inclusion of J2043 not confirmed from the README. | No; gamma-ray rms about 30 µs. |
| IPTA DR2 | Public; 1,382 TOAs, MJD 55757–56593. | Not independent: NANOGrav 9-year Arecibo data. |
| NANOGrav 20-year (GBT, CHIME) | Forthcoming, no date. Whether J2043 moved to GBT after 2020 is unverified. | Possibly; not public. |
| MeerKAT MPTA 4.5-year | Public, but J2043 is not among its 83 pulsars. | Not available. |
| EPTA DR3 / IPTA DR3 | In preparation; membership unverified. | Unknown. |

Papers: Guillemot et al. 2012 (discovery; Nançay, Westerbork, Arecibo);
Fonseca et al. 2016 (NANOGrav 9-year masses); NANOGrav 12.5-year wideband
(flags red noise in J2043); Donlon et al. 2025 (anomalous acceleration,
interpreted as a flyby or a very wide companion; unrelated to a 37-day
signal).

## J1453+1902 (118.4 days, about 1 µs)

| Source | Status | Useful |
|---|---|---|
| FAST / CPTA DR1 | In the sample: 63 epochs over 3.2 years, rms 258 ns; red and DM noise are upper limits. Same access as above. | Yes, decisive: a 1 µs sinusoid at 118 days would stand far above 258 ns residuals over about ten cycles. The 258 ns rms already argues against a persistent 1 µs signal unless the fit absorbed it. |
| NANOGrav 20-year (CHIME, possibly GBT) | Forthcoming. Whether J1453 is still timed is unverified. | Plausible at the 1 µs level; not public. |
| MeerKAT MPTA | Not among its 83 pulsars. | Not available. |
| IPTA DR2 | Arecibo-only NANOGrav data (inclusion unverified). | Not independent. |
| LOFAR | An archive entry suggests it has been observed; no timing release found. | Probably too coarse. |

Papers: Lorimer et al. 2007 (Arecibo drift-scan discovery; solitary; rules
out Earth-mass companions); NANOGrav 11-, 12.5- and 15-year data papers.

## Ranked options

Both pulsars:

1. Ask the CPTA (authors of the DR1 noise paper, arXiv:2506.04850) or use the
   FAST data-request route for the DR1 TOAs and par files. Terms of FAST's
   proprietary period were not verified.
2. Ask the NANOGrav timing working group for post-2020 CHIME or GBT TOAs, or
   whether each pulsar is still timed.
3. J2043 only: Nançay for its TOAs from 2011 on, as a long but coarse check.

Otherwise wait for NANOGrav 20-year and IPTA DR3; neither has a date. Fermi,
MPTA and IPTA DR2 do not help.

Any request or download is the owner's decision and has not been made.

## Sources

- CPTA DR1 single-pulsar noise analysis: https://arxiv.org/abs/2506.04850
- CPTA DR1 gravitational-wave paper: https://arxiv.org/abs/2306.16216
- FAST data policy: https://fast.bao.ac.cn
- MPTA 4.5-year release: https://arxiv.org/abs/2412.01148
- Fermi gamma-ray PTA: https://arxiv.org/abs/2204.05226, https://zenodo.org/record/6374291
- Fermi 3PC page for J2043+1711: https://fermi.gsfc.nasa.gov/ssc/data/access/lat/3rd_PSR_catalog/3PC_HTML/J2043+1711.html
- Guillemot et al. 2012: https://arxiv.org/abs/1202.1128
- Fonseca et al. 2016: https://arxiv.org/abs/1603.00545
- Donlon et al. 2025: https://arxiv.org/abs/2407.06482
- Lorimer et al. 2007: https://arxiv.org/abs/0705.0685
- NANOGrav 15-year data paper: https://arxiv.org/abs/2306.16217
- NANOGrav 12.5-year wideband: https://arxiv.org/abs/2005.06495
- IPTA DR2: https://arxiv.org/abs/1909.04534
- IPTA DR3 status: https://arxiv.org/abs/2602.14014
