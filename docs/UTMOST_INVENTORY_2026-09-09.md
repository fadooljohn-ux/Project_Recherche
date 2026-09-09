# UTMOST DR1 inventory and compatibility assessment

Assessment date: 9 September 2026. **Complete; no search launched.**

The owner authorized inventory and compatibility assessment only. Binary-pulsar
and white-dwarf-companion support is deferred. This assessment does not select a
batch, change search thresholds, calibrate targets or execute observed searches.

## Result

**86 isolated pulsars pass the target and coverage screen. Of these, 56 have not
been searched by Recherche and 30 have previous searches with other data.**
They are conditional preparation candidates, not 86 calibrated or launchable
datasets. All have insufficient independent radio-frequency coverage for the
existing multi-band epoch-dispersion treatment. A source adapter and an explicitly
conditional single-band noise treatment are needed before preparation can finish.

| Main-release disposition | Unique pulsars |
|---|---:|
| Inventoried | 300 |
| Known binary / wide companion, excluded | 17 |
| Released glitch model, excluded after binary check | 7 |
| Insufficient duration or observing days among remaining isolated targets | 190 |
| Pass target and coverage screen; preparation conditional | 86 |
| Calibrated / ready to launch | 0 |

The first four disposition categories below the inventory total account for all
300 main-release targets exactly. Short duration affects 195 targets and too few
observing days affects 55; those nonexclusive counts overlap each other and the
binary/glitch categories. Absence of a glitch term is not proof that a pulsar has
never glitched or is free of timing irregularities.

## Acquisition and retained inputs

The complete public repository was downloaded outside Git from
[Molonglo/TimingDataRelease1](https://github.com/Molonglo/TimingDataRelease1),
pinned to commit `e6c36c26b54749d89d29c148da98f0919b3ce5a8`.
All 1,167 extracted files match the upstream Git blob hashes; the inventory
also records SHA-256 file hashes and the downloaded archive hash.

The release contains 300 main PAR/TIM pairs, four extended alternatives, 280
posterior CSVs, 276 diagnostic PDFs, and a Molonglo clock file. The main TIM files
contain 31,871 active TOAs before applying their released model windows. Four
TOAs lie outside those windows. The 86 conditional datasets contain 13,077 TOAs.

The extended alternatives belong to J0835-4510, J1257-1027, J1452-6036 and
J1703-4851. None adds a qualifying target under this screen. Their original
and extended observations must not be counted as independent pulsars or combined
without checking duplicates. There are 304 dataset variants but 300 pulsars.

External acquisition and original observations:
`../Project Recherche Data/utmost-inventory-20260909/`.
Repository receipts and per-dataset assessment:
[inventory JSON](../results/research/utmost-inventory-20260909/inventory.json),
[inventory CSV](../results/research/utmost-inventory-20260909/inventory.csv),
[file manifest](../results/research/utmost-inventory-20260909/file-manifest.json).

## Screening and prior work

The existing baseline criteria were retained: known isolated target, no released
glitch model or harmonic timing convention, at least 1,200 days of coverage and
40 distinct observing days. The inventory uses active TIM observations within
the inclusive PAR START/FINISH window. Observing days are integer source-site
MJDs, sufficient for this preliminary screen; prepared barycentric epochs must
be checked later. No periodogram, residual peak or observed candidate influenced
the inventory.

Canonical IDs and B-name aliases were checked against the retained ATNF catalogue
snapshot and the current master. The catalogue identity check resolved every
target. The conditional targets have spans of 1,201.7 to 1,500.9 days.

Of the 86 conditional targets, 56 have no Recherche search record. Fifty of those
were already inventoried for other releases; six are new to the master. Thirty
have retained searches using other data, so UTMOST would provide new dataset
coverage rather than new target identities. No UTMOST search is recorded in the
master. Across all 300 targets, 51 were not previously in the master; their
inventory rows are appended without changing older target dispositions.

Cross-matching reused the saved JBO800, NANOGrav 11 and EPTA prior-search
inventories. Fifty-six conditional targets are absent from all three. This
is a separate count from the 56 unsearched by Recherche; the two groups are not
identical. Kerr et al.'s 151-target sample and newer planet searches remain
unreconciled. No target is labelled never previously searched or scientifically
unexplored on this basis.

## Compatibility findings

1. **The timing-model parser accepts all 86 candidate PAR files.** This was a
   model-only check in the pinned Intel environment. No TOAs were transformed or
   fitted. Parsing is not proof that the physical timing/noise model is preserved.
2. **Global white-noise terms are ignored by direct PINT import.** None of the 86
   direct imports creates `ScaleToaError`; all 86 provide global EFAC/EQUAD in the
   source. A UTMOST adapter must translate `TNGlobalEF` and the mixed-case
   `TNGLobalEQ` spelling and verify the source's units and EFAC/EQUAD ordering.
   Forty-seven candidate models include released red-noise parameters; 39 use
   the released white-noise model. These are source choices, not independent
   demonstrations that no additional correlated noise exists.
3. **The observations are effectively single-band.** Candidate effective
   frequencies range from 832.68 to 840.23 MHz. None has 40 days with well-separated
   frequency measurements. Tiny frequency shifts caused by channel weighting
   must not be treated as independent low/high bands. The day-level frequency
   ratio check in the inventory is only a screening proxy, not a new calibrated
   scientific requirement. A periodic propagation delay can resemble an orbital
   delay in these data. Published timing noise can support a conditional search,
   but these measurements alone cannot establish an achromatic planet signal.
4. **Bind source clock, reference and time conventions explicitly.** PINT knows
   `mo` as `most` and requests `mo2gps.clk`. The release supplies that file, which
   covers the observation dates. Global PINT defaults are not a substitute for
   binding it. The models include legacy `EPHVER` and sometimes implicit time
   units; these require source-consistent handling, as do the released ephemeris
   and `TT(TAI)` clock convention. Direct parser warnings are retained.
5. **Verify source phase connection before calibration.** Only six of the 86
   candidate files contain pulse numbers for every retained observation. Other
   files rely on the published timing solution. Five main-release NTOA header
   counts differ from active in-window rows; use measured active rows and retain
   the discrepancies rather than inventing observations. No header discrepancy
   was used to manufacture an exclusion.

The [parser-check receipt](../results/research/utmost-inventory-20260909/model-parser-check.json)
retains every model warning. The qualified GLS solver and existing preparation
adapters were not modified. New code only inventories saved files and optionally
checks model parsing through `tools/recherche utmost-inventory`.

## Recommended next scope

Proceed, if directed, with a small UTMOST preparation step using representative
released white- and red-noise cases. Bind the actual Molonglo clock and time
conventions, translate the global noise terms, verify phase connection and
define the conditional single-band noise treatment. Then measure calibration
and sensitivity on that bounded selection before proposing a launch. No binary
or glitch support is needed to evaluate these 86 candidates.

Single-band limitations cannot be repaired by adding a second free dispersion
parameter to every one-band epoch: that could absorb the signal being searched
for. Strong candidates would need the standing deep review and independent
frequency or telescope evidence. The measurement uncertainties here are often
much larger than in high-precision PTA datasets, so target count is not a
prediction of discovery yield.

The newer UTMOST-NS work is a separate possible extension. Its published study
uses observations from 2021-2023 and combines earlier UTMOST data for some targets.
The Pulsar Portal responds, but a complete downloadable NS timing release was
not verified or inventoried in this assessment. No NS targets are included in
the counts above, and no collaborator has been contacted.

## References and closeout

- [Lower et al. (2020), UTMOST timing programme II](https://arxiv.org/abs/2002.12481).
- [Official release format and data](https://github.com/Molonglo/TimingDataRelease1).
- [Dunn et al. (2025), UTMOST-NS first results](https://doi.org/10.1093/mnras/staf1064).
- [Source queue](FUTURE_DATA_SOURCES.md).

The canonical master update appends the 51 previously absent target identities
and four assessment records. It preserves existing target rows, all 252 search
records, prior work-log rows and operator notes. Counts remain 221 observed
targets, two noise-sensitive historical candidates and zero confirmed new
planets. No calibration, injection, observed search or binary-support change
was performed. The project remains private.
