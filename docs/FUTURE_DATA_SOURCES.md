# Pulsar timing source queue

Owner-directed order, saved 2026-09-08. Work through the eligible pool of one
source before moving to the next. Update this file and the master after each
batch. Keep exclusions, data gaps, prior runs and remaining targets visible.
Exhausting an eligible pool is not a claim that all sources have no planets or
that every target in its release has been searched.

| Order | Source | Release | State | Entry point |
|---|---|---|---|---|
| 1 | MeerTime Thousand Pulsar Array | 597-pulsar release, 2024 | ELIGIBLE POOL COMPLETE: 191 eligible, 191 searched, 0 incomplete, 0 prepared, 0 remaining; 406 excluded | https://zenodo.org/records/8430591 |
| 2 | NANOGrav | 15-year release, 68 pulsars | SINGLE POOL COMPLETE: 17 singles searched including prior B1937; 16 new dataset searches; 51 known binaries excluded; 0 remaining eligible | https://nanograv.org/science/data |
| 3 | Parkes Pulsar Timing Array | DR3, 32 pulsars | ELIGIBLE POOL COMPLETE: 7 datasets searched; 25 excluded for binary/wide-companion or coverage criteria | https://github.com/danielreardon/PPTA-DR3 |
| 4 | European Pulsar Timing Array | DR2, 25 pulsars | ELIGIBLE POOL COMPLETE: 8 DR2full datasets searched; 17 binary/wide-companion exclusions | https://www.epta.eu.org/epta-dr2.html |
| 5 | Indian Pulsar Timing Array | DR2, 27 pulsars | ELIGIBLE POOL COMPLETE: 3 datasets searched; 24 excluded for binary/wide-companion or coverage criteria | https://github.com/inpta/InPTA.DR2 |
| 6 | Molonglo UTMOST | DR1, 300 pulsars and four extended alternatives | COMPATIBLE POOL COMPLETE: 85 searched; 1 legacy-model gap (J1825-0935); 214 exclusions; 0 compatible unprepared | https://github.com/Molonglo/TimingDataRelease1 |
| 7 | Molonglo UTMOST-NS | 174 queried targets; 28,305 raw one-channel TOAs from 173 pulsars | ACQUIRED; combined timing inputs required. Standalone spans 99–815 days; 146 EW unions have sufficient raw duration but no eligible complete combined package is verified; 0 searches | https://pulsars.org.au/ |
| 8 | International Pulsar Timing Array | DR2 Version B, pinned 2021 final release; 65 pulsars | COMPATIBLE POOL COMPLETE: 14 NO_TRIGGER datasets including J1721; all seven batch02 holds resolved and searched; six coverage and 45 companion exclusions. Zero new isolated identities | https://gitlab.com/IPTA/DR2/-/tree/master/release/VersionB |

Release totals include targets that may not qualify for the current isolated,
circular-orbit search. Cross-match canonical IDs and aliases against the master,
then compare actual observation hashes and coverage. Another telescope's data
for an existing target can provide independent observations; label that overlap
rather than counting it as a new pulsar. Combined releases may share actual TOAs.

MPTA's separate 83-pulsar release has already yielded 18 completed original
searches within the current isolated-target scope. Its other dispositions remain
in the existing inventory. TPA is a different programme and release.

For each queued source retain: acquisition DOI/version and checksums, total and
eligible targets, selected/prepared/searched targets, exclusions with reasons,
remaining eligible pool, and links to batch closeouts. Advance the queue only
after these dispositions account for the usable pool; do not silently relax
model or data requirements to declare a source exhausted.

First TPA batch and its limitations: [preparation record](TPA_BATCH01_2026-09-08.md).
Second batch: [preparation record](TPA_BATCH02_2026-09-08.md).
First 25-target batch: [batch 03](TPA_BATCH03_2026-09-08.md).
Second 25-target batch: [batch 04](TPA_BATCH04_2026-09-08.md).
Third 25-target batch: [batch 05](TPA_BATCH05_2026-09-08.md).
Fourth 25-target batch: [batch 06](TPA_BATCH06_2026-09-08.md).
Fifth 25-target batch: [batch 07](TPA_BATCH07_2026-09-08.md).
Sixth 25-target batch: [batch 08](TPA_BATCH08_2026-09-08.md).
Seventh 25-target batch: [batch 09](TPA_BATCH09_2026-09-08.md).
Final six eligible targets: [batch 10](TPA_BATCH10_2026-09-08.md).
The current eligibility boundary excludes 406 unique targets, mostly for short
coverage or too few epochs, plus glitches and harmonic timing conventions.
These remain inventoried. Prior-search cross-matching covers the named JBO,
NANOGrav 11 and EPTA DR2 samples. Kerr et al.'s 151 young Parkes pulsars have not
been fully reconciled; absence from the three inventories is not proof that a
target has never been searched. Independent TPA observations remain useful.

NANOGrav 15 preliminary intake: [release and target preview](NANOGRAV15_PREVIEW_2026-09-08.md). No NG15 batch was launched during this review.

NG15 authorized 16-target batch: [scope and execution](NANOGRAV15_BATCH01_2026-09-08.md).

Combined source-separated campaign closeout: [report](PTA_CAMPAIGN_01_REPORT_2026-09-09.md). The owner authorized these three source batches together; all 18 conditional searches share the same campaign allowance.

UTMOST assessment: [inventory and compatibility](UTMOST_INVENTORY_2026-09-09.md).
Its 86 target-and-coverage candidates resolved to 85 completed searches and one
preparation compatibility gap. Batches 01-05 produced 80 NO_TRIGGER results and
five original threshold crossings, all retained as INCONCLUSIVE_NOISE_SENSITIVE.
The complete inventory reconciles as 85 searched + one model gap + 214 exclusions.
The compatible assessed pool is exhausted; this does not mean every pulsar was
searched or every possible timing model is supported.

J1825-0935 uses DE405 and legacy T2CMETHOD TEMPO. Pinned PINT would replace that
Earth-orientation convention, so the source is deferred until faithful model
support is available. Its failed preparation and master entry are preserved.
See [final batch closeout](UTMOST_BATCH05_2026-09-09.md),
[batch 04 reviews](UTMOST_BATCH04_CANDIDATE_REVIEWS_2026-09-09.md), and the
[dedicated J1752 report](../output/pdf/J1752-2806_Candidate_Report.pdf).
Earlier low-scatter warnings and pulse-number repairs remain in their batch
records. The newer UTMOST-NS release is not included. Binary support remains
deferred. Do not reselect the documented model gap as a fresh compatible batch.
Future releases require a new source-specific inventory and owner direction.

UTMOST-NS is authorized through acquisition, reconciliation, preparation and
execution in batches of up to 25. Authenticated acquisition is complete:
28,305 raw one-channel TOAs from 173 pulsars, after all 174 target queries.
[Authenticated assessment](UTMOST_NS_AUTHENTICATED_INTAKE_2026-09-09.md).
None meets the standalone duration criterion. The 146 EW overlaps provide
sufficient raw union duration, but no complete combined timing package is
verified for an eligible isolated target. The account's file index access is
denied, and publication pulse-count/fit/noise/exclusion products remain missing.
Preserve this source as awaiting combined inputs, not searched or exhausted.
The temporary API token is revoked. The data-request draft is unsent. J1752's
follow-up remains deferred until the first observed run completes.

IPTA DR2 Version B [compatibility review](IPTA_DR2_COMPATIBILITY_2026-09-09.md)
identifies 14 coverage candidates containing 40,088 TOAs. These are previously
searched pulsars with additional or overlapping observations, not 14 new
identities. All use legacy T2CMETHOD TEMPO, which pinned PINT changes on import.
J1721-2457 was selected for bounded adapter preparation: its 150 old
Nançay/Westerbork observing days are separate from our prior MeerKAT input.
Keep the six coverage exclusions and 45 companion exclusions in the inventory.

Subsequent owner-authorized [bounded adapter work](IPTA_BOUNDED_ADAPTER_2026-09-09.md)
prepared J1721-2457 successfully using the released legacy conventions. Timing,
white/red/DM covariance and published fit statistics agree. Attempt02's clock
resource failure is retained and repaired in attempt03. The subsequently
authorized [J1721 calibration](IPTA_J1721_CALIBRATION_2026-09-09.md) is complete:
30-2,000 days, threshold 22.495314, seven annual masked cells and saved sensitivity.
The authorized [J1721 observed search](IPTA_J1721_OBSERVED_2026-09-09.md)
completed once with NO_TRIGGER: peak 42.247206 days, delta chi-square 9.124107
versus threshold 22.495314; no noise flag. Its run01 is consumed. At that closeout, the other
13 coverage candidates remained unprepared; their subsequent batch is below. UTMOST-NS still awaits its missing
combined timing inputs.

The owner subsequently authorized all 13 remaining coverage datasets as
[IPTA batch 02](IPTA_BATCH02_2026-09-09.md). Each compatible dataset is searched
once with a shared 13-search conditional allowance; timing/noise incompatibilities
remain separate gaps. The canonical workbook is updated at each closeout; current
per-target state is recorded in `results/observed/ipta-batch02-20260909/progress.json`.

IPTA batch 02 closed with six observed NO_TRIGGER results and seven held
model-replay gaps: J0711-6830, J1730-2304, J1744-1134, J1843-1113, J1911+1347,
J1939+2134 and J2124-3358. Inputs are present; historical fit summaries remain
unreproduced. That original held closeout and its failed attempts remain preserved.

The subsequently authorized [bounded hold resolution](IPTA_HOLD_RESOLUTION_2026-09-09.md)
replaced an inappropriate historical-summary equality test with independent
fixed-model likelihood verification. All seven passed, were calibrated under
the original 13-search allowance and completed with NO_TRIGGER. Historical
summary differences remain descriptive flags. IPTA now has 14 searched datasets,
zero unresolved preparation holds, six coverage and 45 companion exclusions.
No new candidate or observed execution failure occurred. Current state:
`results/observed/ipta-hold-release-20260909/progress.json`.
The UTMOST-NS combined-input gap remains unchanged; no further run is queued.
