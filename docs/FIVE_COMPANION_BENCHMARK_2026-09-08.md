# Five additional companion benchmarks

Authorized 2026-09-08 from the owner's list in IMG_5521.jpg. Preserve the completed
B1257 and B1937 results. Keep Recherche private while this work is underway.

Targets: B1620-26, J1719-1438, J2322-2650, J1701-3006H (M62H), J1544+4937.
Determine the published companion classification, acquire public time-series
observations and timing models, calibrate each suitable dataset, then attempt
observed companion recovery. A pass requires an observed signal compatible with
the published companion under the stated recovery method; data unavailability,
inadequate sensitivity or unsupported dynamics are separate outcomes.

Research mode: targeted evidence audit, single analyst. Search discovery and
updated papers, publisher supplements, collaboration repositories and public
timing-data releases. Stop source hunting for a target when the discovery/data
availability statements and relevant current archive searches establish a usable
source or a specific unresolved access gap. This is not a systematic review.
A published ephemeris alone is not an observed time series. Do not count a
simulation, a catalog lookup or a known inner stellar orbit as planet recovery.

This is a known-companion benchmark, not a blinded new-planet search. Any use of
published phase connection or a targeted period window must be disclosed. New
processing results go in a fresh external data root. Material searches, source
URLs and downloaded file hashes will be retained with the run evidence.

## Available observations and recovery method

The [MPTA 4.5-year release](https://doi.org/10.57891/j0vh-5g31) supplies actual
sub-banded TOAs and timing models for J1719-1438 and J2322-2650. The
[Donner et al. LOFAR release](https://doi.org/10.5281/zenodo.4290012) supplies
J1544+4937 TOAs; use the authors' outlier-rejected file, retaining the original.
Original release archives and selected files are external to Git under
`../Project Recherche Data/five-companion-benchmark-20260908/`.

For these hour-scale companions, the benchmark uses a published-model-assisted
pulse connection. The full timing solution establishes the integer pulse numbers;
the binary component is then removed and the residual vector recomputed while
keeping that pulse connection. The known period defines a +/-1% search window.
No exact published-period cell is inserted. This is a conditional reproduction
of known-companion timing signals, not an independent blind rediscovery. It does
not assess how often the software could find these systems without prior timing
solutions. No synthetic orbital waveform is supplied as observed data.

Use barycentric pre-binary times for short-period templates. Retain supplied
instrument corrections, replace global DM terms with per-observation dispersion
nuisance columns, and use supplied TOA errors scaled by
`max(1, sqrt(published CHI2R))`. MPTA models are converted from TCB to TDB using
PINT; J1544 already uses TDB. Use the pinned DE440 resources (replacing DE405
for J1544), published MeerKAT station clocks and TT(BIPM2020) for MPTA, and the
published TT(TAI) convention for J1544. These choices are recorded in each profile.

Before the observed scans, the recovery criteria are:

- Eligible grid peak exceeds that profile's automatically computed threshold.
- Local circular frequency refinement succeeds away from search/refinement boundaries.
- Fitted frequency agrees with the published value within one independent frequency bin.
- Fitted amplitude agrees within the larger of 5% or five conditional formal standard errors.

Record postfit reduced chi-square separately; values of two or more flag that
the simple fixed-noise model does not adequately describe the remaining residuals.
Passing signal-recovery criteria does not override such a model limitation.
This bounded benchmark measures period/amplitude recovery, not true masses,
inclinations, planetary composition, or fully interacting dynamical solutions.

J1544 preparation diagnosis: its weak LOFAR channels include uncertainties up to
662 microseconds, a substantial fraction of its 2.16-ms rotation. The full-sample
phase-arc check therefore failed before any search. High-precision channels
remain phase connected. For this target, retain only TOAs with reported
one-sigma uncertainty at most 5% of the spin period before constructing the
searched vector or calibration. This is an uncertainty-based selection, not
clipping on the recovered signal or selecting phases. Preserve the failed
preparation and report the number excluded. The selection does not modify the
completed MPTA results.

## Data gaps being checked

The [M62 discovery paper](https://arxiv.org/html/2403.12137v1#Sx2) states under
Data Availability that observations are shared on reasonable request to the
MeerTime/TRAPUM collaborations. A later openly downloadable TOA release has
not yet been located. No request has been sent to the authors.

The [GBT B1620-26 timing proposal](https://dss.gb.nrao.edu/project/GBT19A-411/public)
describes a 191-day white-dwarf orbit and an outer planetary orbit of roughly
50–100 years, with a dedicated three-body timing analysis. The proposal is
public; it is not a released phase-connected TOA dataset. The current short-period
recovery command cannot establish the outer planet from a catalog ephemeris or
a small set of folded profiles.

## Results, 2026-09-08

Three conditional known-companion recoveries completed. The remaining two have
unresolved data gaps; the owner's five-target condition for going public is
**not met**. Recherche remains private. No background benchmark is running.

| Target | Observed input | Recovered period (days, TDB) | Timing amplitude (microseconds) | Result |
| --- | --- | ---: | ---: | --- |
| J1719-1438 | 2,659 TOAs, 100 epochs, MPTA | 0.0907062852168 | 1821.208 | Known companion recovered |
| J2322-2650 | 1,967 TOAs, 76 epochs, MPTA | 0.322963999709 | 2783.980 | Known companion recovered |
| J1544+4937 | 245 of 330 TOAs, 51 retained epochs, LOFAR | 0.120772989420 | 32855.178 | Known companion recovered after uncertainty selection |
| M62H | No usable public TOA release located | — | — | Data needed; no observed scan |
| B1620-26 | No usable public phase-connected TOA release located | — | — | Data and outer-orbit model needed; no observed scan |

The three amplitudes differ from their supplied timing models by approximately
0.013%, 0.012% and 0.037%, respectively. Postfit reduced chi-square values are
1.0125, 0.9128 and 0.4314. J1544's value below unity is consistent with
conservative error scaling and selection; its uncertainties were not reduced
to force unity. The published-period comparisons use PINT-converted TDB periods
for the two originally TCB MPTA models.

Discovery references describe J1719's companion as a possible ultra-low-mass
carbon-white-dwarf remnant ([Bailes et al. 2011](https://arxiv.org/abs/1108.5201)),
J2322's as a planetary-mass companion
([Spiewak et al. 2018](https://arxiv.org/abs/1712.04445)), and J1544's as an
eclipsing black-widow companion with a minimum mass of 0.017 solar masses
([Bhattacharyya et al. 2013](https://arxiv.org/abs/1304.7101)). The supplied image's
single “confirmed planets” label is therefore too coarse for the scientific
report. These timing recoveries do not resolve companion formation or classification.

The ordinary adapter repair removes both PINT's binary component and its
top-level BINARY parameter, which avoids an invalid serialized model. The first
serialization failure and the failed PINT null-value setter attempt are retained.
J1544's two failed preparation/diagnosis directories are also retained. None
contained an observed periodogram search. Each usable dataset was scanned once.

Verification used a separate weighted least-squares solve of the full timing
design plus sine/cosine columns at each saved fitted frequency. It reproduced
all three amplitudes and chi-square values. Saved grid selection, calibration
cache hashes and exact execution-source snapshots were checked. No broad
qualification suite or old observed search was rerun.

Use `tools/recherche companion-benchmark prepare --target NAME` followed by
`tools/recherche companion-benchmark run --target NAME` only with fresh work
directories: current destinations are consumed and preserve their results.
`--data` selects a new external campaign root; `--resources` selects the prepared
offline resource root. The default roots reproduce the locations documented here.
The three admitted target names are listed by `--help`. This adapter is an
additional known-companion benchmark, not an expansion of the historical
B1937 formal qualification. The existing automatic calibration core and all
qualified scientific source files are unchanged.

## What is needed to finish

For M62H: the phase-connected TOAs, associated timing model, clock/backend
corrections and data-use terms from the MeerTime/TRAPUM collaboration, or a
subsequent public release. Public Pulsar Portal lookups for J1701-3006H, M62H
and NGC6266H returned no accessible folding ephemeris; that is a search finding,
not proof that the collaboration has no data.

For B1620-26: the long-span TOAs and timing/clock/backend model from its timing
team, with the inner white-dwarf orbit retained and the outer planetary signal
handled separately. Public portal lookups for J1623-2631 and B1620-26 returned
no accessible ephemeris. The GBT proposal and published parameter tables do not
supply the required observed time series. Obtaining a few raw observing sessions
would not reproduce the decades-long outer-orbit analysis on its own.

No author correspondence or publication has been sent. Evidence and acquisition
receipts: `results/observed/five-companion-20260908-closeout.json` and the external
data root above. These gaps remain open; they are not recorded as nondetections
or as passed tests.
