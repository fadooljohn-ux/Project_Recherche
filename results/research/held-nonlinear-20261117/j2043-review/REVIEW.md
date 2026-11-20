# J2043+1711 candidate review — 37.48 d feature

18 November 2026 (UTC). Post-hoc review diagnostics on an already-searched dataset.
Nothing here is a detection, a confirmation or a new significance. The frozen
search result (`nonlinear-held-20261117/j2043/run01`) is untouched and was not rerun.

## Verdict: WEAKENED — inconclusive and noise-sensitive

The feature is real in the data and I could not explain it away, but the threshold
crossing does not survive admitting uncertainty in the noise model. The single
strongest reason: the frozen search fixed the noise at the released par-file values,
which are the maximum-posterior sample of NANOGrav's own wideband noise chain **with
its red-noise term removed** (log10 A = −14.34, γ = 3.05). Putting that term back
lowers the statistic from 26.87 to 18.18. Across 500 joint white+red samples of the
released chain the statistic has median 19.2 and is below the frozen threshold
(23.998) in 91% of them. The data themselves mildly prefer some red noise
(Δ ln L up to +5.6) and show excess power in the lowest Fourier modes.

Against that, the feature has several properties a noise spike or artefact would not
obviously have: it is reproduced independently, appears in the narrowband TOAs,
keeps the same amplitude and phase in every quarter of the span, is not carried by a
few epochs, is not in the DM series, and matches no alias or cadence period I tested.
With red noise modelled it is still a roughly 4σ local feature (0.078 ± 0.019 µs).
It is not independently confirmed and cannot be with data on disk.

## Checks and outcomes

Statistic means Δχ² for a sine+cosine pair. "Linear" means my own generalised
least-squares fit with the orbit linearised (8 orbital derivative columns plus the
234 nuisance columns). Threshold 23.998 is the frozen union bound; 20.46 is the
calibration's empirical 99% null quantile.

### 1. Independent reproduction

| Check | Outcome |
|---|---|
| Null χ², my linear fit | 714.3922 for 676 dof (frozen: 714.3922) |
| Linear vs frozen periodogram, all 542 cells | largest difference 0.017 |
| Fine grid (1201 periods, 36.4–38.6 d), nonlinear `NonlinearScan` | peak 26.872 at 37.4806 d, amplitude 0.0892 µs; 0 unconverged, 0 on domain bound |
| Fine grid, linear | peak 26.867 at 37.4806 d; amplitude 0.0892 ± 0.0174 µs; phase 2.830 ± 0.209 rad (atan2(cos, sin) at MJD 57413) |
| Nonlinear minus linear at the peak | +0.005 |
| Period interval (Δχ² drop of 1) | 37.42–37.54 d |
| Orbit at the peak (published σ) | A1 +0.68, TASC −0.81, EPS1 +0.85, EPS2 +0.42, M2 −0.59, SINI −0.53, PB +0.006, PBDOT +0.05 |
| Orbit held fixed instead of re-fitted | statistic 24.31 (re-fitting the orbit raises it by 2.6; 13% of the template overlaps the orbital columns) |
| Harmonics and sub-harmonics (P/4, P/3, P/2, 2P, 3P) | 1.9, 1.5, 1.4, 3.5, 3.3 — nothing |
| "Three cells above threshold" | one peak seen through 5× oversampling, not three features |

### 2. Sampling and aliases

| Check | Outcome |
|---|---|
| Sampling | 459 TOAs on 223 epochs, all Arecibo, all inside a 2.6 h sidereal window; median gap 7 d; no gaps of 36.5–38.5 d |
| Spectral window at 1/37.48 d | 0.076 (largest sidelobe below 0.2 c/d is 0.16 at 20.5 d) |
| Daily aliases of the best-fit model | 1.0245 d, 0.9714 d, 0.5054 d, 0.4921 d respond at 99%, 99%, 96%, 95% of the 37.48 d response |
| Data statistic at those aliases | 26.73, 26.09, 25.91, 24.49 — **the true period is not determined; 37.48 d is only the alias inside the search band** |
| Integer combinations m·f_orb + k·f_sidereal + j·f_year within half a resolution element | 1 hit of 630 tried (3, −2, +3; 37.55 d); 0.38 expected by chance |
| Lunar periods, 1 yr, 0.5 yr, binary period and its harmonics | no match; window at the difference frequencies 0.001–0.08 |
| Injected 719 d sinusoid | 3.8–8.9% of its power appears at 37.48 d; the 13.7 feature at 719 d could contribute about 1 |
| Injected 1 yr sinusoid | absorbed by astrometry; would need 50–60 µs to produce the peak |
| Injected 0.5 yr, 215 d, 689 d | 7–11% leakage each; none has the power needed |
| DMX bin widths | 0.10–0.17 d (one bin per epoch); unrelated to 37.48 d |
| 8 orbital harmonics freed (16 dof) | harmonics Δχ² 15.1 (nothing); statistic falls to 18.3, but 60 fake orbital periods give a median 20.6 (5–95%: 15.2–26.9), so the drop is generic loss of freedom, not an orbital origin |
| Extended scan 3–30 d (outside the search band) | highest 15.8 at 6.61 d; mean cell value 2.36 against 2.0 expected |

### 3. Noise-model sensitivity

| Check | Outcome |
|---|---|
| Null χ² | 714.39 / 676, upper tail 0.148 |
| χ² split | time rows 245.2 for 220.6 effective dof (ratio 1.11); DM rows 469.1 for 455.4 (1.03); L-wide time rows 220.6 for 191.8 (**1.15**, implied error scale 1.07) |
| Errors inflated on all rows | below threshold at ×1.058 (χ² 638, lower tail 0.15, allowed); below 20.46 at ×1.146 (χ² 544, excluded) |
| Errors inflated on time rows only | below threshold at ×1.058 (Δ ln L +0.6); maximum likelihood ×1.055 (interval 1.01–1.105) |
| Errors inflated on L-wide time rows only | below threshold at ×1.063; maximum likelihood ×1.075 (1.025–1.13); released chain gives EFAC 1.21 ± 0.06 against 1.18 used |
| Extra EQUAD on time rows | below threshold at 28 ns, below 20.46 at 48 ns; likelihood flat to 45 ns |
| Extra epoch-common achromatic term (jitter-like) | below threshold at 32 ns, below 20.46 at 56 ns; likelihood flat to 55 ns |
| ECORR | none in the wideband model; the row above is the nearest equivalent |
| Power-law red noise, γ = 13/3 | below threshold at log10 A = −15.5; statistic 19.6 at −15.0, 17.2 at −14.6, 14.4 at −14.0 |
| Red noise, other slopes | below threshold at log10 A = −15.1 (γ 3.5), −14.7 (γ 2.5), −14.45 (γ 1.5 and 0.5) |
| Likelihood for red noise | best Δ ln L +5.6 (γ 3.5, log10 A −14.5), +5.3 (γ 13/3, −14.8), +5.3 (γ 2.5, −14.1) |
| Lowest Fourier modes as free terms | 1 mode (3306 d): Δχ² 10.3 for 2 dof, statistic → 21.0; 3 modes: 23.3 for 6 dof, statistic → 17.3; 10 modes: 47.2 for 20 dof, statistic → 11.7 |
| Which modes matter (γ 13/3, −14.6) | modes 1–3 alone give 18.1; modes 4–111 alone give 24.8; modes 11–111 alone give 26.8 |
| Generic sensitivity loss vs observed drop | a noiseless copy of the signal keeps 82–89% under these models; the data keep 64–78% (5th–16th percentile of 1500 real-signal simulations) |
| Released wideband chain, red term | log10 A median −14.99 (5–95%: −19.2 to −13.98); γ median 3.65; 51% of samples above −15 |
| Statistic over 400 chain red-noise samples (released white noise) | median 19.9; 71% below threshold; 54% below 20.46 |
| Statistic over 500 joint white+red chain samples | median 19.2 (5–95%: 14.8–25.0); **91% below threshold**; 63% below 20.46 |
| Statistic over 500 white-only chain samples | median 24.3 (5–95%: 19.5–29.8); 46% below threshold |
| At the chain's maximum-posterior sample | white part equals the par file exactly (26.85); with its red term 18.18 |
| Largest outlier (z = −4.87, MJD 57231, L-wide) removed | 26.27 |
| White-noise false alarms, my simulations | maximum ≥ 26.87 in 3 of 4000 (all cells) and 5 of 20000 (cells below 100 d); calibration had 0 of 4096 |
| False alarms of the frozen search when red noise from the chain is present | ≥ 23.998 below 100 d in 13% of 40000; but only 0.7% (≥ 26.87: 0.17%) of the 3539 whose long-period periodogram and low-mode power look like the observed one |

Reading of this block: red noise at levels the released chain allows removes the
crossing mainly by lowering the weight of the data and shifting the amplitude
(0.089 → 0.077–0.083 µs), not by generating a 37.48 d peak. Red noise that is
consistent with the quiet long-period periodogram raises the short-period
false-alarm rate of the frozen search by a factor of a few, to a few tenths of a
percent. So noise sensitivity removes the crossing but does not by itself explain
the feature.

### 4. Chromaticity and DM

| Check | Outcome |
|---|---|
| Where the information is | 91% in L-wide time rows, 8% in 430 MHz time rows, 1% in DM rows; 430 MHz TOAs are mostly consumed fixing the per-epoch DMX |
| L-wide-only template | 26.86, amplitude 0.080 ± 0.016 µs |
| 430-only template | 23.73, amplitude 0.71 ± 0.15 µs in antiphase |
| ν⁻⁴ template | 23.37 |
| ν⁻² template in time rows only | 1.37 (absorbed by DMX) |
| Two bands fitted separately | 28.37 for 4 dof; consistency χ² 1.50 for 2 dof (p 0.47); 430: 0.54 ± 0.44 µs, L-wide: 0.098 ± 0.046 µs |
| DMX series, periodicity at 37.48 d | scaled statistic 0.8–1.1, 48–50th percentile of 30–60 d cells; amplitude (3.6 ± 4.2)–(5.0 ± 6.4) × 10⁻⁶ pc cm⁻³ |
| 430-only alternative against the DMX series | needs 0.71 µs at 430 MHz; DMX allows 0.08 ± 0.10 to 0.11 ± 0.14 µs — excluded at 4–6.6σ unless true DM varies at 37.48 d to cancel it |
| DMX residuals vs fitted model | r = −0.08 (σ 0.07); DM-row residuals vs model r = −0.002 |
| DM measurements ignored | 26.69 |
| DM measurement errors ×2, ×0.5 | 26.73, 27.64 |
| DMJUMPs fixed | 26.49 |
| Only epochs with both receivers (425 TOAs) | 27.19 |
| DMX held at released values | 10.76, amplitude 0.036 µs — expected, not a discrepancy: the released DMX values were fitted without the signal and post-fit residuals keep only 0.41 of an achromatic signal |

Reading: there is no 37.48 d signal in DM. Achromaticity cannot be tested here:
with two bands and one free DMX per epoch, an achromatic signal and an
L-band-only signal are the same thing in these data.

### 5. Consistency across subsets and influence

| Split (amplitude µs, phase rad) | Outcome |
|---|---|
| First / second half | 0.078 ± 0.024, 2.84 / 0.103 ± 0.027, 2.79; consistency p 0.79 |
| Thirds | 0.081, 0.096, 0.086; phases 2.83, 2.84, 2.82; p 0.997 |
| Quarters | 0.094, 0.064, 0.112, 0.092; phases 2.79, 3.06, 2.95, 2.53; p 0.95 |
| Orbital phase halves | 0.115 ± 0.028 / 0.068 ± 0.024; p 0.45 |
| Near / far from superior conjunction | 0.077 ± 0.047 / 0.092 ± 0.020; p 0.96 |
| Season halves | 0.076 ± 0.026 / 0.103 ± 0.027; p 0.80 |
| Hour-angle halves | 0.100 ± 0.020 / 0.063 ± 0.030; p 0.46 |
| High / low S/N | 0.088 ± 0.018 / 0.114 ± 0.052; p 0.88 |
| Odd / even epochs | 0.110 ± 0.028 / 0.079 ± 0.027; p 0.60 |
| ASP / PUPPI | 9 ASP TOAs carry 0.6% of the information; not informative |
| Receiver | see block 4; not an independent split |
| Observatory | not possible, Arecibo only |
| Leave one epoch out (223) | statistic 23.76–30.06; 2 epochs each take it below threshold (drops 3.10 and 3.06) |
| Remove top 1 / 3 / 5 / 10 / 20 epochs | 23.8 / 19.8 / 15.8 / 9.5 / 2.9 |
| Same measure for a simulated real signal (300) | observed concentration is *lower* than typical: top-1 share 0.12 against median 0.20; 97% of simulations are more concentrated |
| Leave one calendar year out | 15.4 (without 2016, 45 epochs) to 28.7; amplitude stays 0.081–0.098 µs |
| Growth with span (first 30…100% of epochs) | 1.5, 7.5, 7.5, 12.7, 14.8, 20.4, 19.4, 26.9; amplitude 0.075–0.091 µs throughout |
| Without the 6 TOAs with |z| > 2.5 | 18.0 (trimming extremes always lowers it; not calibrated) |

Reading: amplitude and phase agree in every split I tried, and the feature is
spread over the whole span rather than carried by a few TOAs. The crossing itself is
thin: removing either of two epochs takes it under the threshold.

### 6. Other local datasets

| Dataset | Outcome |
|---|---|
| NANOGrav 15-yr narrowband TOAs (7397 TOAs, in the NG15 archive on disk; same observations, separate TOA reduction, ECORR noise model, also no red noise) | **run**: null χ² 7199.5 for 7150 dof; highest eligible cell is again 37.482 d, statistic 23.54; at 37.4806 d amplitude 0.083 ± 0.017 µs, phase 2.77 ± 0.22; with red noise (−15.0, 13/3) 17.6, (−14.34, 3.05) 15.5; lowest mode Δχ² 9.5, three modes 21.5 |
| IPTA DR2 (versions A and B) | holds only the NANOGrav 9-yr TOAs of this pulsar (to MJD 56592) — a subset of the same observations; not run |
| EPTA DR2, PPTA, MPTA, InPTA, UTMOST, TPA folders | no J2043+1711 data |

The narrowband result rules out an artefact of the wideband TOA or DM
measurement. It is not independent confirmation: the telescope, the observations
and the noise realisation are the same. An independent check needs other
telescopes' TOAs (Green Bank, CHIME, FAST, Effelsberg/LEAP or later NANOGrav data
after Arecibo) covering several 37.48 d cycles at about 0.1 µs epoch precision,
ideally not locked to one sidereal time so the daily aliases separate. None is on
disk.

### 7. Physical plausibility

| Quantity | Value |
|---|---|
| Inner binary from the released parameters | pulsar 1.59 M☉, companion 0.190 M☉, separation 0.0308 au |
| Circular 37.48 d orbit, 0.0892 µs | a = 0.266 au (8.6 inner separations); m sin i = 4.0 × 10⁻⁴ M⊕ = 2.4 × 10²¹ kg ≈ 0.032 lunar masses ≈ 2.5 Ceres |
| With the red-modelled amplitude 0.078 µs | 3.5 × 10⁻⁴ M⊕ |
| Stability (Holman & Wiegert 1999, circular binary, μ = 0.107) | critical radius 1.98 inner separations; period ratio 25.3 — stable |
| Daily aliases | 1.0245 d and shorter lie inside the 1.48 d binary; not viable as a circumbinary orbit |

Dynamically allowed, but the implied body would be about 50 times lighter than the
lightest known pulsar planet. The fitted amplitude is below the calibrated 95%
worst-phase amplitude (0.125 µs), so if real it is biased high by selection.

## Limits of this review

- Everything except check 1 uses the linearised statistic. It agrees with the
  nonlinear one to 0.017 on the frozen grid; I did not rerun the nonlinear scan
  under each alternative noise model.
- Thresholds were not recalibrated under any alternative noise model. Comparisons
  with 23.998 and 20.46 under changed noise are indicative only.
- Red noise uses 111 Fourier modes (to 1/30 d), not NANOGrav's 30. This matters
  little for steep spectra and somewhat for γ ≤ 1.5.
- The chain was used after discarding its first quarter; I did not check its
  convergence. I did not compute a Bayes factor for red noise.
- Simulations are Gaussian with the orbit at its published value. Non-Gaussian
  tails were probed only through the jackknife and outlier removal.
- The conditional false-alarm rates rest on small counts (6 of 3539 for ≥ 26.87).
- Only circular (sinusoidal) signals were considered. No eccentric fit.
- No test separates an achromatic signal from an L-band-only one.
- The 37.48 d period is one of several daily aliases; these data cannot choose.
- These diagnostics were chosen after seeing the result. Project-wide trials
  (roughly 360 search records so far) are not accounted for in any tail quoted.
- Not done: master workbook update, candidate grading, any change to the
  repository, any network access. The epoch-averaged narrowband residual file
  and the IPTA DR2 subset were not analysed.

## Files produced (all in this folder)

| File | Content |
|---|---|
| `REVIEW.md` | this report |
| `common.py` | read-only loaders, plain GLS, vectorised periodogram |
| `01_reproduce.py`, `01_reproduce.json`, `01.log`, `01_fine.npz`, `01_extended.npz` | reproduction, fine grid, harmonics, 3–30 d scan |
| `01b_orbit_fixed.py`, `01b_orbit_fixed.json` | orbit fixed vs re-fitted |
| `02_load_meta.py`, `02.log`, `meta.npz`, `loadout/pint.log` | native model loaded through the repository loader (network denied, 0 attempts); per-TOA flags, DMX table |
| `03_explore.py`, `03.log`, `epochs.npz` | sampling, backends, epochs |
| `04_sampling.py`, `04_sampling.json`, `04.log`, `04_window.npz`, `04_wide.npz` | window, aliases, leakage, 0–2.1 c/d scan, orbital harmonics |
| `04b_harmonic_control.py`, `04b_harmonic_control.json`, `04b.log` | fake-period control |
| `05_noise.py`, `05_noise.json`, `05.log` | χ² split, error inflation, EQUAD, epoch term, red-noise grid, outlier, null tail |
| `05b_red.py`, `05b_red.json`, `05b.log`, `05b_chain_stat.npz` | low-mode tests, band-limited red noise, released chain red posterior |
| `05c_predictive.py`, `05c_predictive.json`, `05c.log` | false alarms under red noise; real-signal control |
| `05d_conditional.py`, `05d_conditional.json`, `05d.log` | conditional short-period false alarms |
| `05e_chain_full.py`, `05e_chain_full.json`, `05e.log`, `05e_chain_full.npz` | statistic over joint white+red chain samples |
| `06_dm.py`, `06_dm.json`, `06.log` | chromatic templates, DM treatments, DMX series |
| `07_subsets.py`, `07_subsets.json`, `07.log`, `07_jackknife.npz` | subset splits, jackknife, growth |
| `08_narrowband.py`, `08_narrowband.json`, `08.log`, `08_narrowband.npz`, `loadout_nb/pint.log` | narrowband cross-check |
| `09_physical.py`, `09_physical.json`, `09.log` | masses, stability, DMX amplitude limit |
| `ng15-extract/` | J2043+1711 files and READMEs extracted from the local NG15 v2.1.0 archive (par, tim, noise chains, DMX, residuals) |

Inputs were read only. `git status` in the repository is unchanged, nothing under
`nonlinear-held-20261117/` or `binary-pilot02-20260909/` was modified, and the
J0613 calibration process was left running.
