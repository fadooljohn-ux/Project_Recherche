# PPTA, EPTA and InPTA campaign 01

The owner authorized acquisition, preparation/calibration, frozen execution and a consolidated review of all eligible data from the three sources. Campaign identity retains the intake date, 20260908. Work continued on 9 September local time.

## Fixed scope

18 datasets from 12 distinct isolated pulsars: seven PPTA DR3 v2, eight EPTA DR2full and three InPTA DR2. Source datasets remain separate. EPTA DR2full+ is excluded because it incorporates InPTA observations. Repeated pulsars provide comparison opportunities, not additional unique-target counts.

Each dataset gets one circular search from 30 days to min(2,000 days, half its prepared TDB span), oversampling 5. All calibrations use search_count=18 and a shared 0.01 conditional family-wise false-alarm allowance. The existing calibration runtime calculates the threshold, timing-projection mask and sensitivity from each dataset before observed execution. Nulls: 4,096 per dataset. Thresholds and grids are not tuned to observed peaks.

## Acquisition and adapter

Inputs are outside Git under `../Project Recherche Data/pta-campaign01-20260908/`. `intake.json` binds the source inventory and historical results. The latest PPTA CSIRO collection 59423 (v2) contains identical selected timing files to v1. The EPTA Zenodo archive 8164425 supplies matching timing/noise data and the corrected Nancay clock. InPTA is pinned to commit e2806fcb2c238ec38dd80784dfcb1e6c82f54728.

`tools/pta_campaign.py` adapts these releases to the existing calibrated GLS scanner. Spin phases retain Intel extended precision; prepared covariance and design use the existing float64 contract. Released astrometric columns are projected, and InPTA's data-derived DMX estimates are projected as nuisance parameters even though the released file marks them fixed. Empty timing columns are removed. PINT's approximate TCB-to-TDB conversion is followed by linear timing projection, not a new global nonlinear timing solution.

Localized compatibility repairs:

- Normalize leading whitespace and expand INCLUDE files. Assign valueless Tempo2 metadata flags value 1 so PINT can read them; preserve original TOAs and files.
- Deduplicate identical repeated chromatic scalar settings in J1939's Parkes model.
- Implement published white variance as EFAC squared times measurement variance plus EQUAD squared; PINT's native order differs.
- Convert EPTA TempoNest DM amplitudes to the PINT timing-amplitude convention at 1400 MHz using sqrt(12 pi squared)/(2.41e-4 times 1400 squared). Retain released Fourier counts and other noise amplitudes.
- Retain Parkes band-limited noise covariance where the PAR contains TNBandNoise. Do not subtract fitted noise waveforms.
- Preserve LEAP's released zero clock correction before the first jump by replacing its discarded MJD=0 sentinel with MJD=40000. Extend the final Effelsberg daily clock sample by half a day at the last value, covering the remaining observing day only. Other clock ranges remain enforced.
- Cast PINT's Fourier noise basis to float64 before its dense product to avoid an unoptimized long-double calculation. Compare a small covariance block directly against the extended-precision product.

## Interpretation

These are conditional searches under fixed released noise models. InPTA DMX files supply EFAC scaling but no complete red-noise hyperparameter model. A threshold crossing is a candidate for review, not a confirmed planet. Report noise-adequacy diagnostics and compare overlapping pulsars without merging the original observations. Preserve candidates from earlier source datasets when later datasets have no trigger.

The existing master workbook is updated after run closeout. Historical searches and the J1453+1902 noise-sensitive candidate review remain preserved.

## Sources

- [PPTA DR3 repository](https://github.com/danielreardon/PPTA-DR3), [DR3 data](https://doi.org/10.25919/j4xr-wp05).
- [EPTA release with noise and clocks](https://doi.org/10.5281/zenodo.8164425), [noise methodology](https://arxiv.org/abs/2306.16225).
- [InPTA DR2](https://github.com/inpta/InPTA.DR2).

## Progress

All four steps are complete. All 18 source datasets were calibrated, frozen and searched. 17 yielded NO_TRIGGER and 1 crossed threshold. Candidate diagnostics, cross-source comparisons and the master workbook are complete. See [combined report](PTA_CAMPAIGN_01_REPORT_2026-09-09.md).

EPTA compatibility closeout: normalize lowercase comment markers, join wrapped
`-padd` flags to their TOA, and include PINT's `delta_pulse_number` in residual
phase before unwrapping. This restores the published phase corrections. The
initial preparation pass retained three EPTA failures, all diagnosed locally;
calibration uses the corrected preparation. No failed preparation is counted as
an observed search.

The EPTA archive checksum matches its Zenodo MD5
`8816ddc72d1790a2e183ab8741795306`. Preparation/calibration failures remain in
external logs. The existing `Recherche observed search` heartbeat was updated
for this campaign at a 30-minute interval; it will pause after closeout.

One EPTA J1744-1134 row uses the explicit marker `C????` before a complete TOA;
it was already omitted by the numerical-row inventory. The adapter now treats
that marked row as a comment. Previously calibrated profiles are reused only
when their normalized TIM remains byte-identical under this parser extension;
the receipt retains the original preparation implementation hash. This avoids
repeating unaffected calibration work.

The J1744-1134 count discrepancy came from `end` directives inside two included
TIM files. The normalizer now ends that included file and resumes the parent
include list, rather than ending the entire flattened dataset. Observations
explicitly superseded below a file's `end` remain excluded. The preliminary
inventory counted lowercase `end` incorrectly; the final prepared receipt,
reconciled with the release model's NTOA, supplies the authoritative count.
Only this changed normalized input is prepared and calibrated again.

The corrected J1744-1134 prepared count is **1,949 TOAs**, independently matched
by a case-insensitive, file-scoped active-row count. The preliminary 1,961
count included 12 rows below a lowercase `end`. The PAR's older NTOA field is
1,931 and is not used to discard any additional observations. Both source
metadata counts are retained; 1,949 is the campaign's actual input count.

### Observed-import correction (9 September)

The first consumed EPTA grids exposed a concrete adapter defect during review.
Tempo2 treats any line beginning with uppercase `C` as a comment, including
`C../data/...` and `CJ...`; PINT's reader had accepted 14 such rows in
J1730-2304, three in J1744-1134, and four in J1911+1347. The adapter also
passed two J1730 `-addsat` flags through as metadata. Tempo2 applies these
as site-arrival-time offsets in seconds before barycentering. The corrected
normalizer now applies both released conventions, using decimal arithmetic
for the timestamp offset. Evidence: [Tempo2 reader](https://github.com/ipta/tempo2/blob/master/readTimfile.C).

All three affected attempts are retained unchanged and superseded, including
the original NO_TRIGGER J1911 result. The other 15 datasets contain neither
issue. Corrections use separate `pta-campaign01-repair01-20260909` inputs,
calibration and consumed output directories. Corrected TOA counts are 1,315,
1,946 and 882 respectively. Period policy, source noise and the allowance for
18 valid datasets are unchanged; these are import repairs, with no peak-based
row rejection or threshold adjustment. Final closeout must use the corrected
three results and explicitly retain the invalidated attempts in its history.

The corrected EPTA searches all returned NO_TRIGGER; null reduced chi-square
is 0.978 (J1730), 0.989 (J1744), and 0.988 (J1911). The two first-pass EPTA
crossings are import artifacts. Review orchestration also encountered a
radio-frequency subset with no residual degrees of freedom after nuisance
projection. That subset is now reported as UNIDENTIFIABLE; it is not assigned
a statistic or divided by zero. The original diagnostic failure log is retained.
