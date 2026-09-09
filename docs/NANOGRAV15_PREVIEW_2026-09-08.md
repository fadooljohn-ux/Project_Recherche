# NANOGrav 15-year preliminary look

Read-only scientific review, 2026-09-08. No preparation, calibration or observed
search was launched. The full release has not yet been downloaded or its input
hashes checked; the following is a published-table and current-master screen.

The public [v2.1.0 release](https://zenodo.org/records/16051178), dated 2025-07-17,
contains narrowband and wideband timing products, timing/noise models, clock
files and narrowband post-fit residuals. The 68 targets have observations from
2004 to mid-2020; individual baselines differ, reaching nearly 16 years.
[Timing paper and tables 5–6](https://arxiv.org/html/2306.16217v1).

The table-based single-target screen contains 17 pulsars. J1024−0719 is explicitly
excluded as a known long-period binary even though its table omits an orbital
period. The paper's headline binary count must not substitute for this per-target
check. Of these 17, B1937+21 already has a completed NG15 v2.1.0 wideband search
in Recherche. The remaining 16 comprise six targets absent from the master and
ten previously searched targets with other data. These are provisional intake
counts, not calibrated eligibility or claims of new-to-science targets.

## Six targets new to Recherche

| Target | Published span (yr) | Wideband TOAs | Published full wideband RMS (μs) |
|---|---:|---:|---:|
| J1911+1347 | 7.0 | 126 | 0.088 |
| J0645+5158 | 8.9 | 289 | 0.164 |
| J1923+2515 | 9.0 | 170 | 0.214 |
| J1944+0907 | 12.5 | 180 | 0.411 |
| J0340+4130 | 8.1 | 228 | 0.591 |
| J1453+1902 | 7.0 | 122 | 0.895 |

RMS is epoch-averaged post-fit scatter from paper table 6, not a detection limit.
The preliminary priority is J1911+1347, J0645+5158 and J1923+2515, followed by
J1944+0907, J0340+4130 and J1453+1902. Actual ranking should use calibrated
sensitivity with the complete covariance, design and observing cadence.

## Integration work

The released wideband route is a sensible starting point because the repaired
runtime already handled B1937+21 with joint arrival-time/dispersion coordinates.
However, `pilot2_runtime_core.prepare_context` and `target_calibration.import_b1937`
still bind that specific target. The TPA adapter is source-specific too. A small
NG15 preparation adapter must connect each target's joint timing/DM residuals,
full covariance, timing design, per-instrument noise parameters and clock files
to the existing calibration and detector. Qualified B1937 records stay preserved.
This is adapter work, not evidence that all 16 can run unchanged today.

The next bounded step is to acquire and hash v2.1.0, reconcile all 68 PAR/TIM
models against the master and known binary exceptions, and prepare the six new
targets for target-specific calibration. Freeze the period scope from their
cadence and span before observed scans; do not simply inherit TPA's 400-day cap.
Narrowband and wideband products are alternate reductions of shared observations,
not independent confirmation datasets. Longer records may support longer periods,
but red noise and timing-model degeneracy still set practical sensitivity.

NANOGrav is extensively studied. Additional years and independent telescope data
can add useful coverage without establishing that these stars were never searched
for planets. Detailed screen saved outside Git at
`../Project Recherche Data/nanograv15-preview-20260908/preview.json`.
