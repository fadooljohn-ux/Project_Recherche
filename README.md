# Project Recherche

Pulsar-timing analysis for periodic companion searches, known-system recovery
and automatic target-specific calibration.

**AI agents: start with [AGENT_README.md](AGENT_README.md).** It covers installation,
data acquisition, source adapters, calibration, execution, monitoring, repairs,
scientific interpretation and the master workbook. Codex, Claude Code, Devin and
other shell-capable agents use the same operating procedure.

## Current status — 9 September 2026

The **v0.1.0 publication edition** includes the operational macOS runtime,
scientific reports and cumulative register. Rehabilitation stages 1–6 are complete; Qualification 02 passed
**21/21 gates** over 344 synthetic cases. Later source adapters have their own
bounded verification and do not inherit unrestricted scientific qualification.

The [master workbook](outputs/recherche-master-20260908/Project-Recherche-Master.xlsx)
contains **754 registered targets, 277 observed identities and 351
search/refinement records**. Seven candidate identities have been retained for
review. **No new planetary discovery is confirmed.** A dataset search is not
necessarily a new pulsar or an independent set of observations.

The latest [IPTA hold-resolution campaign](docs/IPTA_HOLD_RESOLUTION_2026-09-09.md)
released all seven preparation holds and completed **seven NO_TRIGGER searches**,
with zero execution failures or noise-adequacy flags. An inappropriate comparison
of historical summary statistics was replaced by independent fixed-model
likelihood verification. Historical discrepancies remain recorded; detection
thresholds and the original campaign allowance were unchanged. IPTA now has
**14 completed compatible dataset searches**, including the earlier J1721 case.
All prior searches and failed attempts remain preserved. No run is active or queued.

## What it does

- Imports supported public timing releases with explicit clock, ephemeris,
  timing-model and noise conventions.
- Searches prepared residuals for circular periodic signals while projecting
  out the linear timing nuisance model.
- Automatically computes per-target conditional thresholds, timing-projection
  masks and on-grid sensitivity curves; verifies and reuses unchanged calibrations.
- Supports published chromatic timing structure and joint wideband TOA/DM data
  through the appropriate source adapters.
- Preserves input bindings, frozen searches, failed attempts, candidate reviews,
  result hashes and a single cumulative workbook.

Raw radio reduction, arbitrary timing-model conversion, unknown-noise inference,
general binary-pulsar searches and an unattended discovery survey are outside the
current implementation. Sensitivity and thresholds are conditional on the supplied
model. A NO_TRIGGER result does not exclude weaker planets or masked periods.

## Start operating

```sh
git clone https://github.com/fadooljohn-ux/Project_Recherche.git
cd Project_Recherche
python3 tools/agent_setup.py --install
python3 tools/agent_setup.py --check
tools/recherche calibration --help
```

Install Pixi first; Apple Silicon needs Rosetta. The scientific runtime is locked
**Intel macOS Python 3.11**, with 63 long-double mantissa bits. A fresh checkout
can use a different directory through the new bootstrap; historical qualification
remains bound to its recorded installation. Linux/Windows/cloud agents need a
macOS execution worker. No validated native Linux/Windows science runtime is supplied.

Automatic workbook closeout has a hash-pinned public `openpyxl` backend, installed
separately from the scientific runtime, so Codex's bundled spreadsheet library
is optional. The [agent guide](AGENT_README.md) explains its supported operations,
formula recalculation and the remaining manual review-grade editing step.

**Inputs are separate:** Git contains code, locks, reports, the workbook and
selected evidence. Full TOAs, large arrays and runtime resources must be restored
from verified archives or acquired from the pinned public releases. Setup performs
no scientific fits or new observed searches. Follow the agent guide to establish
a new workload and its input/model bindings before launching.

For installation and evidence handling, use
[the operator guide](docs/OPERATOR_GUIDE.md). Preserve consumed run destinations;
never rerun science to repair a workbook update.

## Source coverage

| Source | Completed compatible scope | Outcome / remaining limitation |
|---|---:|---|
| MPTA | 18 original-search datasets | NO_TRIGGER in 30–400 days; includes four chromatic-support targets |
| TPA | 191 | NO_TRIGGER; 406 inventory exclusions retained |
| NANOGrav 15-year | 17 including B1937 | J1453+1902 crossing reviewed as inconclusive/noise-sensitive |
| PPTA / EPTA / InPTA | 7 / 8 / 3 | One InPTA J1939+2134 crossing, reviewed as inconclusive/noise-sensitive |
| UTMOST DR1 | 85 | 80 NO_TRIGGER and five noise-sensitive crossings; one legacy-model gap, 214 exclusions |
| IPTA DR2 Version B | 14 | NO_TRIGGER; six coverage and 45 companion exclusions retained |
| UTMOST-NS | 0 | Acquired TOAs; verified combined timing/noise inputs still required |

The [source queue](docs/FUTURE_DATA_SOURCES.md) retains release links, exclusions,
source overlap, remaining input gaps and campaign reports. Compatible pools are
complete under the current search criteria; this does not mean every released
pulsar or every possible model was searched.

## Known-system benchmarks

These use actual public observations. Simulations and sensitivity injections are
identified separately in the linked reports.

| System | Observed result |
|---|---|
| B1257+12 | Two larger planets recovered near 66.622 and 98.056 days from 310 I-LOFAR TOAs; inner planet below demonstrated sensitivity |
| J1719−1438 | Known companion recovered near 0.0907062852 days |
| J2322−2650 | Known companion recovered near 0.3229639997 days |
| J1544+4937 | Known companion recovered near 0.1207729894 days |
| M62H / J1701−3006H and B1620−26 | Untested data/model gaps; not nondetections or passed benchmarks |

The latter three recoveries used published timing solutions and narrow period
windows: they are **model-assisted recovery**, not blind rediscovery. Timing
alone does not establish companion composition or true mass. Methods:
[B1257 benchmark](docs/B1257_BENCHMARK_2026-09-08.md) and
[five-companion benchmark](docs/FIVE_COMPANION_BENCHMARK_2026-09-08.md).

## Candidate reports

- [J1453+1902 scientific report](output/pdf/J1453%2B1902_Candidate_Report.pdf):
  the original 118.43-day crossing weakened under noise and consistency checks.
- [J1939+2134 scientific report](output/pdf/J1939%2B2134_Candidate_Report.pdf):
  the original InPTA 567-day crossing is strongly noise-sensitive; overlapping
  data do not establish independent confirmation.
- [J1752−2806 scientific report](output/pdf/J1752-2806_Candidate_Report.pdf):
  an approximately 81.7-day feature remains noise-model dependent, with
  underpowered independent TPA observations.

These are research candidates, not confirmed planets. The
[deep-review policy](docs/CANDIDATE_DEEP_REVIEW.md) applies to each valid compelling
crossing. [Three separate grades](docs/CANDIDATE_GRADING.md) describe statistical
significance, signal robustness and independent confirmation. Conditional
noise-simulation tails are not global discovery significance or planetary probabilities.

## Reference

| Document | Purpose |
|---|---|
| [Agent operating README](AGENT_README.md) | Complete handoff to another AI harness |
| [Owner instructions](AGENTS.md) | Current operating instructions |
| [Automatic calibration](docs/AUTOMATIC_CALIBRATION_2026-09-08.md) | Array contract, thresholds, masks, sensitivity and caching |
| [Master workbook rules](docs/MASTER_WORKBOOK.md) | Prevent duplicate work and preserve results |
| [Latest IPTA closeout](docs/IPTA_HOLD_RESOLUTION_2026-09-09.md) | Seven released holds and final compatible-pool results |
| [Operational release](docs/OPERATIONAL_RELEASE_2026-09-08.md) | Original stage-6 package |
| [Qualification 02](docs/QUALIFICATION_02_2026-09-08.md) | Passing formal qualification; original failed attempt retained |
| [Rehabilitation roadmap](docs/OPERATIONAL_REHABILITATION_ROADMAP_2026-09-07.md) | Recovery and maintenance direction |

Keep repairs localized and run only checks justified by the change. Documentation
and operator-only changes do not require repeating scientific qualification.

## Release and citation

See the [v0.1.0 release notes](RELEASE_NOTES.md),
[CITATION.cff](CITATION.cff) and [contribution guide](CONTRIBUTING.md).
This edition uses a clean Git history and redacted publication copies of historical
records. Their original hashes remain identified as historical; use the
[publication manifest](publication-manifest.json) to verify the distributed bytes.
See [provenance](docs/PUBLICATION_PROVENANCE.md) for the exact boundary.
