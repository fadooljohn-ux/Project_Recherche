# UTMOST batch 04 — 9 September 2026

The owner authorized preparation of the next 25 UTMOST datasets and launch
when ready. Select from the remaining 32 coverage candidates using the saved
ranking, current master and consumed UTMOST destinations. Preserve the 54
completed UTMOST datasets and all other historical searches.

Use the existing repaired adapter, 30–400-day circular search, actual 25-target
conditional 1% allowance, target calibrations and frozen timing masks. Prepare
and calibrate before freeze, then execute each selection once. Update the
canonical workbook after every terminal run, including a failed attempt.
Diagnose actual errors and continue within scope. Valid candidates receive
the standing bounded deep review and three-measure evidence grading.
Keep private; binary support and additional batches remain deferred.

Data: `../Project Recherche Data/utmost-batch04-20260909/`.
Preparation evidence: `results/research/utmost-batch04-20260909/`.
Observed evidence: `results/observed/utmost-batch04-20260909/`.

```sh
tools/recherche utmost-prepare inventory --data '../Project Recherche Data/utmost-batch04-20260909' --batch-size 25
tools/recherche utmost-prepare prepare --data '../Project Recherche Data/utmost-batch04-20260909'
tools/recherche utmost-prepare calibrate --data '../Project Recherche Data/utmost-batch04-20260909'
tools/recherche utmost-search freeze --data '../Project Recherche Data/utmost-batch04-20260909'
tools/recherche utmost-search run --data '../Project Recherche Data/utmost-batch04-20260909' --target TARGET
```

Status: COMPLETE — 25 observed searches and four bounded candidate reviews closed out.

## Preparation

The selection contains two targets new to Recherche, J0630-2834 and J1034-3224,
and 23 previously searched pulsars with new UTMOST observations. These are
additional dataset searches, not repetitions of consumed UTMOST data. Seven
coverage candidates remain unprepared after this selection.

Preparation produced 3,570 TOAs over 3,040 target-specific observing days.
All final null reduced chi-squared values lie between 0.889842 and 1.049925;
none has a preparation noise-adequacy warning.

J1048-5832 initially failed an integer pulse-offset spread check (three cycles).
The release supplies all 232 pulse counts and requests TRACK -2. Its large
published red-noise model permits residuals spanning multiple rotations; treating
that span as a pulse-count mismatch was an adapter error. The repair uses complete
supplied integer pulse counts directly, retaining integer and fractional phase
precision and removing only a constant. It does not wrap this residual to the
nearest pulse. Missing required TRACK -2 counts and noninteger counts still fail;
datasets without counts retain the compact-cluster ambiguity check.

The repaired J1048 null reduced chi-squared is 1.004999. A direct comparison with
PINT's `Residuals(track_mode='use_pulse_numbers')` agrees to 1.71e-11 cycles after
constant removal. See [PINT's documented pulse tracking](https://nanograv-pint.readthedocs.io/en/latest/_autosummary/pint.residuals.Residuals.html).
This is a development/import check, not an observed planet search or formal
qualification. The failed attempt and diagnostic are preserved, and all five
earlier preparations were retained before rebuilding. Their centered residuals
are exactly unchanged. The shared solver and calibration source remain unchanged.

Evidence: `results/research/utmost-batch04-20260909/preparation-summary.json`,
`independent-pulse-check.json`, and the `pre-repair/` directory.

## Calibration

Completed 102,400 fixed-noise null realizations and 75 deterministic template
checks. Thresholds span 26.121–26.5502. Of 4996 grid cells,
138 are excluded by fixed timing-projection masks. The search retains its
30–400-day circular model and shared 1% conditional allowance for 25 targets.
Full values are in `results/research/utmost-batch04-20260909/calibration-summary.json`.
These are calibration/development results, not observed planet recoveries.

## Observed execution and review closeout

All 25 frozen datasets executed once: **21 NO_TRIGGER and four CANDIDATE**
results, zero observed execution failures and zero noise-adequacy flags.
Candidates are J1359-6038, J0908-4913, J1048-5832 and J1752-2806. Each received
the standing four-step review, including 512 nulls, 256 injections and a
fixed-period comparison against previously searched, independent TPA observations.
All retain INCONCLUSIVE_NOISE_SENSITIVE. J1752 has an interesting conditional
0/512 exceedance result, but no noise-robust global significance or confirmation.
See the [four-candidate scientific report](UTMOST_BATCH04_CANDIDATE_REVIEWS_2026-09-09.md).

The master updated after each observed run and again for review context and
three-measure grades. It now records 743 targets, 277 observed targets and 331
search/refinement records; seven valid historical candidate records have current
assessments, with zero new discoveries. All 306 prior scientific rows and 888
historical result files are preserved. Input and workbook backups are verified;
the shared qualified solver and calibration source remain unchanged.

UTMOST coverage is now 79 completed datasets: 74 NO_TRIGGER and five original
crossings, all reviewed as noise-sensitive. Seven coverage candidates remain
unprepared; 214 inventory exclusions remain preserved. Consumed run destinations
must not be reused. Monitoring is paused after closeout; a new batch needs owner
direction. Final verification is in
`results/observed/utmost-batch04-20260909/closeout.json`.

| Pulsar | Outcome | Peak period (days) | Δχ² | Threshold |
|---|---|---:|---:|---:|
| J0630-2834 | NO_TRIGGER | 66.8569 | 7.293 | 26.265 |
| J1034-3224 | NO_TRIGGER | 31.1783 | 8.688 | 26.314 |
| J1359-6038 | CANDIDATE | 95.9650 | 41.741 | 26.204 |
| J0908-4913 | CANDIDATE | 93.1500 | 27.852 | 26.163 |
| J1600-5044 | NO_TRIGGER | 41.0930 | 12.918 | 26.255 |
| J1048-5832 | CANDIDATE | 105.0066 | 36.722 | 26.142 |
| J1456-6843 | NO_TRIGGER | 48.1799 | 12.549 | 26.550 |
| J1057-5226 | NO_TRIGGER | 34.8041 | 8.666 | 26.245 |
| J1202-5820 | NO_TRIGGER | 52.7410 | 7.863 | 26.184 |
| J1056-6258 | NO_TRIGGER | 125.4133 | 9.640 | 26.284 |
| J1829-1751 | NO_TRIGGER | 121.0207 | 4.495 | 26.132 |
| J1013-5934 | NO_TRIGGER | 30.3471 | 11.078 | 26.142 |
| J1136-5525 | NO_TRIGGER | 75.1529 | 7.506 | 26.204 |
| J1428-5530 | NO_TRIGGER | 43.7130 | 8.684 | 26.275 |
| J1605-5257 | NO_TRIGGER | 49.9078 | 13.361 | 26.314 |
| J1326-6700 | NO_TRIGGER | 97.3866 | 15.993 | 26.204 |
| J1012-5857 | NO_TRIGGER | 139.0333 | 13.186 | 26.294 |
| J1651-4246 | NO_TRIGGER | 41.7793 | 8.913 | 26.153 |
| J1840-0809 | NO_TRIGGER | 141.2315 | 8.072 | 26.142 |
| J0820-4114 | NO_TRIGGER | 143.4338 | 5.433 | 26.121 |
| J1932+1059 | NO_TRIGGER | 39.2128 | 7.100 | 26.255 |
| J1752-2806 | CANDIDATE | 81.7850 | 57.672 | 26.498 |
| J1745-3040 | NO_TRIGGER | 33.0741 | 10.122 | 26.184 |
| J1913-0440 | NO_TRIGGER | 33.9926 | 8.765 | 26.194 |
| J0953+0755 | NO_TRIGGER | 71.3646 | 8.284 | 26.294 |
