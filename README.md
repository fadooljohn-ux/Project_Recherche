# Project Recherche

Recherche searches public pulsar-timing data for planets and other small
companions. A planet makes its pulsar wobble, so the pulses arrive slightly
early and then slightly late, over and over. The project looks for that
repeating pattern, decides in advance how strong it must be to count, looks
once, and reports what could have been seen when nothing is found.

**AI agents: start with [AGENT_README.md](AGENT_README.md).**
A plain-language account is in
[docs/PLAIN_LANGUAGE_SUMMARY_2026-11-20.md](docs/PLAIN_LANGUAGE_SUMMARY_2026-11-20.md).

## Status — 21 November 2026 (edition v0.2.0)

- **No new planet is confirmed.**
- **403 registered searches of 320 pulsars**, plus four searches made with a
  nonlinear orbit method, across eight public data releases.
- Ten first-stage threshold crossings were re-tested with the pulsar's noise
  fitted at the same time. **None survived.** One case, J2043+1711 (37.48
  days, 0.09 µs), is neither confirmed nor excluded: its signal is at the
  half-detection level of that test and only another telescope's data can
  settle it.
- **Combined limit, 310 pulsars**
  ([tables and caveats](docs/POPULATION_LIMITS_2026-11-19.md)): companions of
  10 Earth masses or more with periods of 30–240 days orbit fewer than about
  1.1% of the pulsars searched (95% confidence); Earth-mass companions fewer
  than about 2%; companions with periods of 400–2,000 days fewer than about
  9–10%, if the released noise models are right.
- Known systems are recovered: the two larger planets of B1257+12 and the
  low-mass companions of J1719−1438, J2322−2650 and J1544+4937.

## What the software does

| Capability | What it is | Where |
|---|---|---|
| One-shot companion search | A generalized least-squares periodogram for a circular companion, with every timing, dispersion and instrumental term fitted at the same time. Settings and code are fingerprinted and frozen; each search runs once. | `tools/recherche`, `src/pulsar_pilot/` |
| Automatic calibration | Thresholds from thousands of noise-only simulations per target, a mask for periods the timing model absorbs, and the amplitude detected 95% of the time at each period. | `tools/target_calibration.py`, [guide](docs/AUTOMATIC_CALIBRATION_2026-09-08.md) |
| Second-stage noise test | For any first-stage crossing: the noise is re-fitted together with the signal on a grid declared beforehand, with per-receiver white noise. A crossing is only a trigger until it passes this. | `tools/joint_noise_stage.py`, [record](docs/JOINT_NOISE_STAGE_2026-11-18.md), [rule](docs/CANDIDATE_GRADING.md) |
| Limits | Per-pulsar detection limits, an interactive sensitivity atlas, and a combined limit on how common companions can be. | `tools/detection_limits.py`, `tools/population_limits.py`, [atlas](outputs/sensitivity-atlas-20260909/index.html) |
| Pulsars in binaries | The known orbit is removed with its uncertainty, after checks that the linear treatment is accurate; targets that fail are held, not searched. | `tools/mpta_binary.py`, `tools/ng15_binary.py`, `tools/pta_binary.py` |
| Nearly circular orbits | Orbits written with a periastron time are re-expressed in the small-eccentricity form, refined against the released model, and checked for equivalence. | `tools/orbit_reexpress.py`, `tools/orbit_refine.py`, [record](docs/ORBIT_REEXPRESSION_2026-11-20.md) |
| Shapiro delay | Uncertain Shapiro-delay parameters are replaced by a verified set of nuisance terms; a leakage test covers models that omit the delay. | `tools/shapiro_basis.py`, `tools/omitted_shapiro_leakage.py`, [record](docs/SHAPIRO_BASIS_2026-11-20.md) |
| Nonlinear orbit fit | A full nonlinear fit of the inner orbit for targets where no linear treatment is adequate. | `tools/nonlinear_statistic.py`, [record](docs/NONLINEAR_STATISTIC_2026-11-17.md) |
| tempo2 models | Orbits written in tempo2's general `T2` model are translated, with a correction for tempo2's Shapiro-delay convention, and compared numerically against tempo2 itself. | `tools/orbit_translate.py`, `tools/tempo2_compare.py`, [comparison](docs/TEMPO2_COMPARISON_2026-11-21.md) |
| Known-system recovery | Benchmarks on pulsars with known planets or low-mass companions. | [B1257+12](docs/B1257_BENCHMARK_2026-09-08.md), [five companions](docs/FIVE_COMPANION_BENCHMARK_2026-09-08.md) |
| Record keeping | A master workbook of every target, search, review and decision, with hashes of inputs and results. | [workbook](outputs/recherche-master-20260908/Project-Recherche-Master.xlsx), [guide](docs/MASTER_WORKBOOK.md) |

## Data searched

| Release | Isolated pulsars | Binaries (outer companion) |
|---|---|---|
| MeerTime Thousand Pulsar Array | 191 | — |
| Molonglo UTMOST DR1 | 85 | — |
| MeerKAT timing array, 4.5-year | 18 | 18 searched, 14 held |
| NANOGrav 15-year | 17 | 9 with the September procedure, 4 nonlinear, 7 with the November treatments |
| International timing array DR2 | 14 | — |
| European timing array DR2 | 8 | 6 |
| Parkes timing array DR3 | 7 | 12 |
| Indian timing array DR2 | 3 | — |

Counts are searches of data sets; a pulsar can appear in more than one
release. The batch records are in [docs/](docs/); the latest are
[MeerKAT binaries](docs/MPTA_BINARY04_2026-11-20.md),
[NANOGrav binaries](docs/NG15_BINARY01_2026-11-20.md) and
[Parkes and European binaries](docs/PTA_BINARY01_2026-11-21.md).
[What remains unsearched](docs/REMAINING_TARGETS_2026-11-19.md),
[binaries on disk](docs/BINARY_INVENTORY_2026-11-20.md) and
[other public data](docs/NEW_DATA_SOURCES_2026-11-20.md) are recorded
separately.

## Rules the results depend on

1. Thresholds, period ranges and noise models are fixed before the observed
   data are scanned. Each frozen search runs once; a consumed search is never
   rerun.
2. A target whose model cannot be verified is held with the reason recorded.
   No check is loosened to clear a hold. A hold is not a non-detection.
3. A first-stage crossing is a trigger, not a candidate. It is graded only
   after the second-stage noise test, and significance, robustness and
   independent confirmation are graded separately.
4. Failures, stopped runs and superseded attempts are kept.

## What the results do not say

- They cover circular orbits at the periods searched, mostly 30–400 days for
  isolated pulsars and up to 2,000 days for some binaries.
- Masses are minimum masses; the orbit's tilt is unknown.
- First-stage limits assume the released noise models are right. The
  long-period limits are the least robust.
- The pulsars are those with enough good public data, not a random sample.
- This is an independent project and has not been peer reviewed.

## Using it

Scientific runs need the pinned Intel macOS Python 3.11 environment (Rosetta 2
on Apple Silicon); see [AGENT_README.md](AGENT_README.md) for installation,
data acquisition and operation. Raw timing data and large intermediate
products are not in the repository; each source report names the upstream
release to acquire.

```sh
python3 tools/agent_setup.py --install
python3 tools/agent_setup.py --check
PYTHONPATH=src:tools .pixi/envs/default/bin/python -m pytest -q
```

Installing or cloning starts no scientific job. GitHub Actions in this
repository run only when started by hand.

## History and provenance

Development history, qualification records and earlier status reports are in
[docs/](docs/); [Qualification 03](docs/QUALIFICATION_03_2026-11-16.md) is the
current formal qualification of the core search (21 of 21 gates). Later
adapters and treatments carry their own bounded verification and do not
inherit it. The public edition is a redacted snapshot of a private archive;
see [docs/PUBLICATION_PROVENANCE.md](docs/PUBLICATION_PROVENANCE.md) and
[RELEASE_NOTES.md](RELEASE_NOTES.md).

Licence: MIT. To cite, see [CITATION.cff](CITATION.cff).
