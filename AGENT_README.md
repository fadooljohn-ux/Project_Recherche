# Project Recherche: operating instructions for AI agents

Start here if you are using Codex, Claude Code, Devin, or another agent with a
shell and filesystem access. Read `AGENTS.md` for the owner's current direction,
then this guide. The latest owner instruction takes precedence over older
chronological authorization entries. You do not need this conversation to operate
the repository. No particular AI service or model is required.

## Current state — 21 November 2026

- **Edition v0.2.0.** The public repository is a redacted snapshot of a private
  archive ([provenance](docs/PUBLICATION_PROVENANCE.md)). A release or
  documentation update authorizes no new scientific workload, download, data
  request or repository change; those need the owner's instruction.
- **403 registered searches of 320 pulsars, plus four nonlinear-orbit searches.
  No new planet is confirmed.** Ten fixed-noise crossings went through the
  second-stage joint-noise test; none survived. J2043+1711 stays open
  (inconclusive; needs independent data). The combined limit covers 310
  pulsars ([tables](docs/POPULATION_LIMITS_2026-11-19.md)).
- Every eligible isolated pulsar in the eight releases on record has been
  searched. Binaries: MeerKAT 18 searched and 14 held; NANOGrav, Parkes and
  European batches of November 2026 are complete. Verified but unsearched:
  NANOGrav J1745+1017, J0605+3757, J1643-1224 (leakage test passed) and
  J1640+2224. Not built: an International (IPTA) binary adapter.
- Every `run01` destination is consumed. No job is active or queued. Roots
  named `*-dev*` are development roots and must not be calibrated, frozen or
  run.
- The dated entries below this section are a chronological record. Where they
  disagree with this section or with `AGENTS.md`, this section and the latest
  owner instruction govern.

## Handoff of 10 September 2026 (historical)

- At this date Recherche was private. The post-release binary work of
  9–10 September 2026 was developed in the Publication checkout and merged
  into the private archive on 16 November 2026.
- There are **783 registered targets, 286 observed identities and 360
  search/refinement records**. Eight retained candidate identities have reviews;
  **no new planet is confirmed**. Dataset counts are not unique-pulsar counts.
- The latest IPTA continuation released seven preparation holds and completed
  seven NO_TRIGGER searches. All 14 compatible IPTA datasets, including the
  earlier J1721 case, have now been searched. Previous results are preserved.
- The supported isolated-pulsar pools in the source queue are complete.
  UTMOST-NS still lacks verified combined timing inputs. UTMOST J1825-0935 is a
  separate legacy-model gap. A bounded ELL1 white-dwarf binary pilot completed
  J1614−2230 and J1909−3744 with NO_TRIGGER; J0613−0200 is held for nonlinear
  Shapiro uncertainty. General binary support remains incomplete.
- The subsequent 48-target binary inventory selected three further systems;
  J0740+6620, J1857+0943 and J2043+1711 all reached the nonlinear Shapiro limit.
  No new search ran. Across both pilots there are two searches, four nonlinear
  holds and 45 other adapter exclusions at that closeout.
- A subsequent [omitted-Shapiro assessment](docs/ELL1_OMITTED_SHAPIRO_ASSESSMENT_2026-09-09.md)
  identifies five candidate white-dwarf systems within the missing-parameter
  exclusions. J1012+5307 and J1738+0333 are the initial development pair.
  The [conditional branch is now implemented and both preparations passed](docs/ELL1_OMITTED_SHAPIRO_PREPARATION_2026-09-09.md).
  The [follow-on binary pilot03](docs/BINARY_PILOT03_2026-09-09.md) selected fixed
  optical Shapiro parameters for J1012 and reused the original J1738 preparation.
  Both were calibrated and searched once: J1738 returned NO_TRIGGER; J1012 crossed
  at 138.911 days but is INCONCLUSIVE_NOISE_SENSITIVE after broader red-noise checks.
  The four earlier measured-Shapiro holds remain unchanged. Do not repeat consumed
  searches. Assess red-noise frequency coverage before further binary batches.
- The [frequency-coverage improvement and binary pilot04](docs/BINARY_PILOT04_2026-09-09.md)
  are complete. New preparations explicitly cover the searched red-noise band or
  record that no released red component exists. J1125+7819 returned NO_TRIGGER
  (peak 9.611; threshold 17.590). J1012 received covariance-only verification,
  with no repeated observed search. The subsequent J0509 run is below.
- The [bounded joint-noise improvement](docs/JOINT_NOISE_IMPROVEMENT_2026-09-10.md)
  is complete on exposed J1012/J1752 observations. Both fall below their new
  development thresholds; original-size injections have poor recovery under the
  tested noise models. Stronger recovery depends on period. The finite-grid
  procedure is not generally qualified or automatically applied to every source.
  Future UTMOST preparation now enforces explicit red-frequency coverage.
- The [native EPTA J1012 follow-up](docs/EPTA_J1012_FOLLOWUP_2026-09-10.md)
  is complete. Native T2/H3/H4 checks passed after excluding one arrival outside
  measured clock coverage in a derived dataset (originals retained). The 5,324
  remaining TOAs do not corroborate the fixed 138.911-day NG15 waveform under
  three declared noise models. J1012 remains INCONCLUSIVE_NOISE_SENSITIVE;
  independent confirmation is now NOT_CORROBORATED. This target-specific route
  does not qualify general orthometric binaries or authorize an EPTA period scan.
- [Binary pilot05](docs/BINARY_PILOT05_2026-09-10.md) completed J0509+0856 with
  NO_TRIGGER: 52.905 days, statistic 18.049 against 18.851. Its released model
  contains no red component. Reduced chi-square 1.684 is below the coarse flag
  cutoff but shows excess scatter under that model; retain this limitation.
  J0557+1551 subsequently completed below.
- [Binary pilot06](docs/BINARY_PILOT06_2026-09-10.md) completed J0557+1551 with
  NO_TRIGGER: peak 8.438 at 49.624 days versus threshold 19.410; 95/96 diagnostic
  injections recovered. The saved five-system queue is complete: four NO_TRIGGER
  and the retained noise-sensitive J1012 crossing, with no confirmed new planet.
  The subsequent ELL1H assessment is below.
- The [ELL1H compatibility assessment](docs/ELL1H_COMPATIBILITY_2026-09-10.md)
  is complete: J2145-0750 and J2317+1439 are H3-only adapter candidates;
  J1802-2124 remains a missing-Shapiro-model hold. Model-only analytic checks
  passed for the two explicit NHARMS=3 models. No actual TOA fit, calibration
  or search ran in that assessment. The subsequent implementation is below.
- The [H3-only extension and J2145 preparation](docs/ELL1H_J2145_PREPARATION_2026-09-10.md)
  are complete. Use `shapiro_mode: h3_only` with `tools/recherche binary-pilot`
  only for explicit fitted H3 / NHARMS=3 ELL1H models. J2145 passed on its first
  attempt: 400 TOAs, rank 184/184, maximum orbital shift 0.104 published sigma,
  red modes 30 to 128, reduced chi-square 0.994109. Preserve the prepared profile
  in `RECHERCHE_DATA/ell1h-j2145-preparation-20260910`. The subsequent calibration
  is below; no observed search ran during preparation.
  J2317 preparation and J1802 model clarification remain separate next scopes.
- [J2145 calibration](docs/ELL1H_J2145_CALIBRATION_2026-09-10.md) is complete:
  threshold 21.203245 from 4096 nulls, 390/402 eligible cells, 12 annual/half-year
  exclusions, median worst-phase 95% amplitude 0.685459 us and 90/96 bounded
  injection recoveries. The fixed-noise profile and scientific source are
  unchanged. The subsequent observed launch is below. Preserve the calibration
  and avoid repeating it.
- [J2145's frozen observed search](docs/ELL1H_J2145_OBSERVED_2026-09-10.md)
  completed with NO_TRIGGER: peak 15.548556 at 345.265855 days versus 21.203245.
  The independent likelihood check passed; no execution failure or noise flag
  occurred. The master updated at closeout. Its run01 destination is consumed.
  J2317's subsequent timing/noise preparation is below.
- [J2317 H3-only preparation](docs/ELL1H_J2317_PREPARATION_2026-09-10.md)
  passed on attempt01: 708 TOAs, 312 barycentric day bins, rank 328/328 and
  reduced chi-square 1.006933. All six orbital fit terms, including the weak
  signed H3 coefficient, are retained. NO_RELEASED_RED_COMPONENT remains an
  explicit limitation. The unchanged adapter required no repair. Preserve
  `RECHERCHE_DATA/ell1h-j2317-preparation-20260910`; subsequent calibration is below.
- [J2317 calibration](docs/ELL1H_J2317_CALIBRATION_2026-09-10.md) is complete:
  threshold 22.902100 from 4096 nulls, 929/940 eligible cells, 11 annual/half-year
  exclusions and 95/96 bounded injection recoveries. Median worst-phase 95%
  amplitude is 0.402931 us under the supplied noise model. No released red
  component is present. Inputs and code are unchanged. Its observed launch is
  below; preserve the completed calibration.
- [J2317's frozen search](docs/ELL1H_J2317_OBSERVED_2026-09-10.md) completed
  with NO_TRIGGER: peak 12.711083 at 84.212684 days versus threshold 22.902100.
  Independent likelihood verification passed with no execution failure or
  automated noise flag. Its run01 destination is consumed and the master updated.
  Both assessed H3-only candidates are now searched. The subsequent J1802
  source/model clarification is below.
- [J1802 source/model clarification](docs/J1802_MODEL_CLARIFICATION_2026-09-10.md)
  is complete: both release configurations explicitly remove H3/H4; wideband
  cites its F-test. Both exclude phase 0.15–0.35. Narrowband includes red noise
  that wideband omits. The source omission is explained; preparation adequacy
  remains untested and its hold is retained. Next recommend a target-specific
  omitted-Shapiro ELL1H preparation with timing/DM, orbital and noise checks.
  No fit, calibration or search ran. Three Work log rows were added; all prior
  records and four nonlinear holds remain unchanged.
- [J1802 bounded preparation](docs/ELL1H_J1802_PREPARATION_2026-09-10.md)
  completed: the explicit omitted-Shapiro ELL1H interface passes (126 TOAs,
  66/66 timing rank), but PREPARATION_ADEQUACY_HOLD blocks calibration. Orbital
  harmonics improve chi-square by 40.659 under the released noise; a red-grid
  alternative improves the null objective by 16.991 at its boundary. No noise
  alternative is promoted. The preserved profile is not ready to calibrate.
  Use the saved diagnostics and gated adapter; do not repeat preparation.
  Next recommend bounded joint orbital/Shapiro and noise comparison. No outer
  observed scan or calibration ran; four Work log rows preserve all prior records.
- [J1802 joint orbital/noise comparison](docs/J1802_JOINT_MODEL_COMPARISON_2026-09-10.md)
  is complete; hold retained. Across 57 noise models and nine physical scenarios,
  omission/physical treatments prefer slope 0, while free harmonics prefer 6.
  Physical Shapiro improves the local objective by at most 0.583; physical and
  harmonic treatments exceed the checked orbital-shift range. Extra harmonics
  retain 46.5–74.7% worst-phase template information at five declared periods.
  No profile is promoted, calibration or outer-period observed scan run. Next
  recommend parking J1802 and prioritizing the four remaining binary holds.
- The [four-hold priority assessment](docs/BINARY_HOLD_PRIORITIES_2026-09-10.md)
  is complete: J1857+0943, J0740+6620, J0613−0200, then J2043+1711. Eight original
  input hashes and four failure records were verified; no fit, preparation,
  calibration or observed search ran. Five Work log entries preserve all prior
  records. Next recommend a bounded J1857 nonlinear-Shapiro compatibility
  prototype retaining timing/DM uncertainty and explicit noise treatment.
  Implementation has not started; the four holds and J1802 hold remain.
- The [J1857 native nonlinear prototype](docs/J1857_NONLINEAR_PROTOTYPE_2026-09-10.md)
  is conditionally compatible: 364 TOAs/DMs, seven native orbital terms and 160
  linear nuisance terms; rank 167/167, reduced chi-square 0.990714. All ten fits
  across five declared noise settings converged without boundary or numerical
  holds. The released spectrum extended from 30 to 64 modes is preferred.
  Original pilot02 failure remains preserved; this successor is not an
  operational profile. Use `tools/recherche j1857-nonlinear` for the bounded
  prototype only. Its attempt01 is consumed. Next recommend a reusable nonlinear
  statistic and small synthetic verification/cost benchmark before calibration.
  No calibration or outer-period search ran; four Work log entries were added.
  J0740, J0613 and J2043 remain held; J1802 stays parked.
- All completed `run01` destinations are consumed. No observed job is active or
  queued. The existing 30-minute monitor is paused.

Authoritative current records:
[master workbook](outputs/recherche-master-20260908/Project-Recherche-Master.xlsx),
[source queue](docs/FUTURE_DATA_SOURCES.md),
[latest prototype](docs/J1857_NONLINEAR_PROTOTYPE_2026-09-10.md), and
[machine-readable closeout](results/research/j1857-nonlinear-prototype-20260910/closeout.json).
Historical reports describe their original closeout, not necessarily today's state.

The [sensitivity atlas](outputs/sensitivity-atlas-20260909/index.html) is a saved
342-dataset/273-identity isolated-pulsar snapshot, not an additional search or an
occurrence-rate limit. `tools/recherche sensitivity-atlas --help` describes the
read-only builder; regenerating it requires the original hash-bound evidence and
periodograms, which a public clone may not contain. Binary sensitivities are kept
separate. See the [post-release plan](docs/POST_RELEASE_SCIENCE_PLAN_2026-09-09.md)
and [binary operating procedure](docs/BINARY_PILOT01_2026-09-09.md).

## Location change — 16 November 2026

On the owner's instruction, every Recherche folder was moved out of
`../` into one workspace,
`../`. Folder names are unchanged, so
relative references such as `../Project Recherche Data` still resolve:

```text
../
  Project Recherche/                 # this Git checkout
  Project Recherche Data/            # inputs, preparation, caches, runs
  Project Recherche Publication/     # public-repository checkout
  Recherche Recovery/                # verified archives and workbook backups
  Recherche Releases/
  RELOCATION_2026-11-16.tsv          # every symbolic link retargeted by the move
```

- `Project Recherche Gate4 Evidence/` held only one empty directory and was
  removed on 16 November 2026. Four historical records still name its old path.
- Historical records, manifests and reports keep their original
  `../...` absolute paths as evidence. Read
  them with the prefix mapping above; do not rewrite them.
- Absolute symbolic links inside `Project Recherche Data/` were retargeted to
  the new location. No file content was changed.
- Both runtimes were rebuilt here on 16 November 2026: `.pixi` from the
  unchanged `pixi.lock` with `pixi install --locked` (134 packages), and
  `.agent-venv` with `python3 tools/agent_setup.py --install`, which needs
  Rosetta 2 to run the Intel Python. `agent_setup.py --check` returned
  `AGENT_RUNTIME_READY` with 71 unchanged qualified source files. The runtimes
  built at the old path were deleted after that check.
- The environment binding and compatibility assessment were completed on
  16 November 2026 on the owner's instruction:
  [report](docs/ENVIRONMENT_BINDING_2026-11-16.md). `tools/recherche doctor`
  and `tools/install` pass here through
  `protocol/RUNTIME_ENVIRONMENT_BINDING_20261116.json`, which rebinds only the
  Python executable hash and macOS version (26.6.2 to 27.2.1). The frozen
  manifest is unedited, and the B1257 benchmark reproduced bit for bit. Because
  the macOS version changed, moving the checkout back would not restore the old
  identity. Another path, host or macOS change needs a new binding.
- **Qualification 03 passed 21/21 gates here on 17 November 2026**
  ([record](docs/QUALIFICATION_03_2026-11-16.md)). It uses the host-native
  manifest `protocol/PILOT2_RUNTIME_ENVIRONMENT_MANIFEST_QUALIFICATION03.json`
  and the 62-file source lock `results/qualification/qualification03-readiness.json`;
  the retired runner and executor versions are in `archive/retired-source/`.
  The attempt is consumed. The binding record above now applies only to work
  frozen against the qualification 02 manifest.
- The owner kept the union-bound threshold on 17 November 2026; the empirical
  per-search rule was reverted and `tools/target_calibration.py` is
  byte-identical to its earlier version. Calibration cache keys also hash every
  file under `src/`, so retiring the nine runner and executor files changed the
  keys: a saved profile now misses the old cache and recalibrates once, with
  the same seed and rule, at the original cost. Old cache entries are retained.
- The owner resumed work on 17 November 2026 with "Proceed with nonlinear work".
  The [reusable nonlinear statistic](docs/NONLINEAR_STATISTIC_2026-11-17.md) is
  implemented in `tools/nonlinear_statistic.py` and verified on simulated
  J1857 data (`tools/recherche nonlinear-verification`; `attempt01` consumed,
  no holds). On the owner's ±5σ domain decision,
  [J1857 is prepared, calibrated and frozen](docs/J1857_NONLINEAR_CALIBRATION_2026-11-17.md):
  threshold 22.176555, 207/218 eligible cells, 93/96 injection recoveries.
  On the owner's instruction ("Launch") the observed search ran once on
  17 November 2026: **NO_TRIGGER**, peak 10.257274 at 161.50 days against the
  threshold, an ordinary value for noise. `run01` is consumed; do not rerun
  and do not repeat preparation or calibration. The frozen tool files may be
  edited again, but a later target needs its own preparation, calibration and
  freeze.
- On the owner's instruction the three remaining held targets were
  [verified, prepared, calibrated, frozen and searched once](docs/HELD_NONLINEAR_SEARCHES_2026-11-17.md)
  (18 November 2026 UTC): J0740+6620 **NO_TRIGGER** (peak 8.19 against
  22.31), J0613−0200 **NO_TRIGGER** (14.39 against 25.02), J2043+1711
  **PERIODIC_SIGNAL_CANDIDATE** (26.87 against 24.00 at 37.48 days). The J2043
  review found the crossing does not survive restoring the released chain's
  red noise (about 18–19); it is graded INCONCLUSIVE_NOISE_SENSITIVE, the
  ninth such candidate. All three `run01` destinations are consumed; do not
  rerun, re-prepare or recalibrate. J0613's orbit box is cut at declared
  physical floors (`physical_floors` in its scope) and the fit iteration
  limit is now 200. No nonlinear hold remains; J1802 stays parked.
- The owner chose a grid-profile joint-noise test applied as a second stage to
  fixed-noise crossings. [Stages 1 and 2 are complete](docs/JOINT_NOISE_STAGE_2026-11-18.md):
  `tools/recherche joint-noise-stage prepare|calibrate|freeze|run`
  (`tools/joint_noise_stage.py`, 105-member noise grid, five off-grid null
  generators). J1752−2806 (10.75 against 23.06), J1012+5307 (18.86 against
  40.56) and the quiet control J1738+0333 (11.31 against 22.10) each ran once
  and are below threshold; their `run01` destinations are consumed. Stage 3
  (owner: "Proceed with stage 3") put **J2043+1711** through it with the orbit
  linearised and checked by `tools/recherche joint-noise-nonlinear-check
  simulate|observed`: **18.42 against 23.00, below threshold** (nonlinear
  check 18.45). Its grade stays INCONCLUSIVE_NOISE_SENSITIVE and its `run01`
  is consumed. On "Run them through" the six other September candidates ran
  once each: J1453+1902 18.61 against 22.35, J1939+2134 10.45 against 29.07,
  J1327−6222 6.13 against 23.26, J1359−6038 13.63 against 23.79, J0908−4913
  11.31 against 25.37, J1048−5832 7.72 against 24.69. All below threshold,
  grades unchanged, `run01` consumed. J1939 (18,191 TOAs) uses the exact
  `"compression": "diagonal_subspace"` reduction and a wider white-scale
  grid, both declared before its run. No recorded fixed-noise crossing
  survives the second stage. **Standing rule (owner, 18 November 2026):**
  every new fixed-noise crossing goes through the second stage once, with its
  noise grid and generators declared before the run, before it is graded; see
  [the rule](docs/CANDIDATE_GRADING.md#second-stage-rule). The six rows in
  Candidate grades now carry their second-stage tails. Any new search needs a
  new owner instruction. After `calibrate`, run
  `tools/recherche joint-noise-sensitivity --data … --root …`: it writes the
  [period-by-period sensitivity curve](docs/JOINT_NOISE_STAGE_2026-11-18.md#sensitivity-curve)
  on simulated data, and `freeze` refuses without it. Editing
  `tools/joint_noise_stage.py` or the files it binds invalidates existing
  preparations (all current ones are consumed). For a target with a released
  noise chain the config must declare a joint chain generator and
  `family.receiver_white` (copy `config/j1453-joint-noise-receiver-white.json`).
  `tools/recherche detection-limits --out FILE CURVE…` turns saved curves
  into [detection limits](docs/DETECTION_LIMITS_2026-11-19.md); use relative
  paths. [Independent-data options](docs/INDEPENDENT_DATA_SOURCES_2026-11-19.md)
  for J2043 and J1453 are research only; no request has been made. A
  [split-test simulation](docs/J2043_SPLIT_TEST_POWER_2026-11-20.md) for J2043
  (`tools/split_test_power.py`, simulated data) found little power; no
  observed split test is authorized.
  `tools/recherche population-limits --atlas ATLAS --out FILE` combines the
  saved atlas into a [population limit](docs/POPULATION_LIMITS_2026-11-19.md);
  `--extra FILE` adds curve files such as the 18 MeerKAT binaries, built with
  `PYTHONPATH=src:tools .pixi/envs/default/bin/python tools/binary_curves.py
  results/observed/mpta-binary0* --out FILE` (done 2026-11-20: 289 pulsars; 2026-11-21: 310 pulsars with every binary
  batch, `results/research/population-limits-20261121/`).
  [Binary inventory](docs/BINARY_INVENTORY_2026-11-20.md)
  (`tools/binary_inventory.py`, par files only) and
  [other public data](docs/NEW_DATA_SOURCES_2026-11-20.md) are proposals; no
  target list is approved and no download has been made.
  `tools/recherche ng15-binary select|prepare|calibrate|freeze|run --data ROOT`
  is the NANOGrav wideband binary tool with `--reexpress` and `--shapiro-basis`
  ([record](docs/NG15_BINARY_TOOL_2026-11-20.md)); only a preparation-only
  development check has run (`--development` roots refuse calibration).
  [Batch 01](docs/NG15_BINARY01_2026-11-20.md): seven searched (NO_TRIGGER,
  consumed), one held. [Leakage test](docs/OMITTED_SHAPIRO_LEAKAGE_2026-11-20.md)
  for targets without Shapiro terms: `tools/omitted_shapiro_leakage.py`.
  Parkes/European binaries: `tools/pta_binary.py` with `tools/orbit_translate.py`
  ([record](docs/PTA_BINARY_ADAPTERS_2026-11-21.md)).
  `tools/tempo2_compare.py` checks prepared residuals against native tempo2
  ([result](docs/TEMPO2_COMPARISON_2026-11-21.md)); run it on any new
  Parkes/European preparation before proposing a search.
  [Batch 01](docs/PTA_BINARY01_2026-11-21.md): 12 Parkes and 6 European
  binaries searched (all NO_TRIGGER, consumed).
  [Remaining targets](docs/REMAINING_TARGETS_2026-11-19.md) is a proposal
  now owner-approved (32 MeerKAT binaries). Use
  `tools/recherche mpta-binary select|prepare|calibrate|freeze|run --data ROOT`
  with a new batch root per batch; [batch 01](docs/MPTA_BINARY01_2026-11-19.md)
  and [batch 02](docs/MPTA_BINARY02_2026-11-19.md) searched seven and held 25;
  the approved list is exhausted. A hold is not a non-detection; never loosen a
  check to clear one.
  `select --reexpress` rewrites near-circular DD/DDH orbits in the ELL1 form with
  an equivalence check ([re-expression](docs/ORBIT_REEXPRESSION_2026-11-20.md));
  [batch 03](docs/MPTA_BINARY03_2026-11-20.md) searched the two it clears
  (J1933-6211, J2322-2650; both NO_TRIGGER, consumed). List now: 9 searched,
  23 held. `select --shapiro-basis` replaces free Shapiro parameters with a
  verified nuisance basis ([Shapiro treatment](docs/SHAPIRO_BASIS_2026-11-20.md));
  [batch 04](docs/MPTA_BINARY04_2026-11-20.md) searched the nine it clears (all
  NO_TRIGGER, consumed). List now: 18 searched, 14 held. Plain-language account:
  [summary](docs/PLAIN_LANGUAGE_SUMMARY_2026-11-20.md).
- `tools/recherche` puts the native Git first on PATH when the `/usr/bin/git`
  shim cannot start from the Intel runtime (this host's Command Line Tools
  `libxcrun` has no x86_64 slice). Commands run outside the wrapper, such as
  `pytest`, need `PATH="/Library/Developer/CommandLineTools/usr/bin:$PATH"`;
  with it and `PYTHONPATH=src` the suite passes (356 passed, 3 deselected after
  the six retired runner test files moved to `archive/retired-tests/`).

Code audit fixes of 16 November 2026 are summarised in
[the audit disposition](docs/CODE_AUDIT_DISPOSITION_2026-11-16.md): tool
integrity checks no longer use `assert`, external data is located through
`RECHERCHE_DATA_ROOT`, the `openpyxl` workbook backend is the default, and CI
runs the suite.

## 1. Clone and install

```sh
git clone https://github.com/fadooljohn-ux/Project_Recherche.git
cd Project_Recherche
git status --short
python3 tools/agent_setup.py --install
python3 tools/agent_setup.py --check
```

The public repository needs no authentication. Prerequisites:
macOS, Python 3 for bootstrap, [Pixi](https://pixi.sh/latest/installation/), and
Rosetta 2 on Apple Silicon. IPTA preparation also needs Apple's command-line
compiler tools (`clang++`). Set `RECHERCHE_PIXI` to an existing Pixi executable
if it is not on PATH. Allow downloads during installation and data acquisition.
Scientific commands run through the offline wrapper afterward.

The bootstrap installs the committed `pixi.lock` with `--locked`; it does not
resolve new scientific dependencies. It separately installs hash-pinned public
operator dependencies from `tools/requirements-agent.txt` into `.agent-venv`.
The scientific runtime remains `.pixi/envs/default/bin/python`, Python 3.11,
Intel x86_64 with **63 long-double mantissa bits**. Do not use a native ARM Python
or the unrelated old `.venv` for science. Keep numerical-library threads at one;
`tools/recherche` sets these variables for you.

Expected bootstrap result: `AGENT_RUNTIME_READY`, 71 unchanged qualified source
files, correct precision, working public workbook backend, zero scientific fits.
The local `.agent-setup.json` is ignored by Git. The check does not admit inputs,
run qualification, or transfer the historical host's qualification to a new Mac.
Use a bounded installation/data compatibility check before making scientific
claims on a newly provisioned machine. Do not edit historical manifests to make
`doctor` pass on a different host.

**Platform boundary:** the scientific lock and network-denial launcher currently
support macOS only. A Linux/Windows/cloud agent can read and maintain the project,
but must use an accessible macOS worker (for example through SSH) for this
scientific runtime. There is no validated Linux/Windows scientific installation.
Harness independence does not imply operating-system portability.

The old `tools/install` and `tools/recherche doctor` deliberately retain the
original path-bound restoration checks. For exact restoration of that historical
installation, use [the operator guide](docs/OPERATOR_GUIDE.md). For a fresh clone
at another path, use `agent_setup.py` above. Neither route silently changes the
qualification record.

## 2. Restore or acquire inputs

Git contains code, locks, protocols, reports, the master workbook and selected
result/calibration evidence. It does **not** contain the full raw TOAs, large
covariance/profile arrays, complete clock/ephemeris collections or installed
runtimes. A clone is not a complete data restoration.

Use one of these routes:

1. Obtain the owner's source-specific data archive and checksum receipt, verify
   them, and restore into a new external directory. Preserve historical receipts
   and their original absolute paths as evidence. Recreate local runtime links;
   do not rewrite old result hashes or try to resume completed records.
2. Acquire the exact public release/revision named in the relevant source report
   and compare hashes against its saved intake manifest. Rebuild preparation and
   calibration into a **new** dataset/run ID when that work is authorized.
   Another release is new input provenance, not a substitute for missing bytes.

A useful layout is:

```text
workspace/
  Project_Recherche/             # this Git checkout
  Project Recherche Data/        # external inputs, preparation, caches, runs
  Recherche Recovery/            # verified archives and workbook backups
```

Always supply explicit absolute `--data` and `--cache` paths where the command
supports them. Historical defaults name consumed batches. Some older campaign
scripts are fixed historical recipes; inspect their configuration before adapting
them to new work. `tools/recherche init-data` restores the original admitted
rehabilitation fixtures only; it is not a general pulsar downloader.

| Source | Acquisition and adapter instructions |
|---|---|
| MPTA and known systems | [MPTA batch](docs/MPTA_BATCH01_2026-09-08.md), [B1257](docs/B1257_BENCHMARK_2026-09-08.md), [other companions](docs/FIVE_COMPANION_BENCHMARK_2026-09-08.md) |
| TPA | [Initial intake](docs/TPA_BATCH01_2026-09-08.md), [final inventory disposition](docs/TPA_BATCH10_2026-09-08.md) |
| NANOGrav 15-year | [Batch intake and search](docs/NANOGRAV15_BATCH01_2026-09-08.md) |
| PPTA / EPTA / InPTA | [Combined campaign](docs/PTA_CAMPAIGN_01_2026-09-09.md) |
| UTMOST DR1 | [Inventory](docs/UTMOST_INVENTORY_2026-09-09.md), [adapter](docs/UTMOST_PREPARATION01_2026-09-09.md) |
| UTMOST-NS | [Authenticated acquisition and missing inputs](docs/UTMOST_NS_AUTHENTICATED_INTAKE_2026-09-09.md) |
| IPTA DR2 Version B | [Pinned release and input manifest](docs/IPTA_DR2_COMPATIBILITY_2026-09-09.md), [TEMPO2 adapter](docs/IPTA_BOUNDED_ADAPTER_2026-09-09.md), [current acceptance checks](docs/IPTA_HOLD_RESOLUTION_2026-09-09.md) |

IPTA's pinned upstream is `https://gitlab.com/IPTA/DR2.git`, commit
`96a7c69caaf5da5cd22532784a3063b98b500dbe`. For a relocated acquisition set:

```sh
export RECHERCHE_IPTA_RELEASE_ROOT='/absolute/IPTA-DR2/release'
```

This relocates the release clock lookup; each file must still match the saved
intake hash. Copy a selected target's `VersionB/TARGET/` tree into
`DATA/TARGET/original/`. Keep its active TIM includes. Install the separate locked
TEMPO2/libstempo runtime into `DATA/runtime/` by copying
`tools/tempo2_runtime/pixi.toml` and `pixi.lock` there and running:

```sh
pixi install --locked --manifest-path "$DATA/runtime/pixi.toml"
```

The root scientific environment and TEMPO2 runtime are intentionally separate.
TEMPO2's legacy ephemeris reader needs a path without spaces; the adapter creates
an alias under `$HOME/.cache/recherche-tempo2`. On a home path containing spaces,
use a worker account with a space-free home path. Do not substitute a modern
PINT import for legacy `T2CMETHOD TEMPO`; the conventions differ.

Never use unavailable public observations as a reason to substitute simulations
and label them observed recovery. Do not contact authors or send messages without
owner authorization. Portal credentials and temporary tokens never belong in Git.

## 3. Select, prepare, calibrate, freeze, search

Before selection, check canonical names/aliases, dataset identity and prior
input hashes in the master. A pulsar may have multiple datasets; combined PTA
releases often reuse actual measurements. Record overlap explicitly. A completed
pool is not a pool of fresh targets for a new agent.

For a new authorized workload, save a short scope record before computing the
observed periodogram: targets, release revision and hashes, timing/noise model,
period limits, seeds, shared false-alarm allowance, masks, stop boundary and
output IDs. A request to prepare is different from a request to launch; when the
owner has already authorized both, carry both through without another approval
cycle. Diagnose actual errors, make localized repairs and continue.

Use `tools/recherche COMMAND --help` for current argument spelling:

| Command | Purpose / boundary |
|---|---|
| `calibration ingest`, `run`, `check` | Prepared-array profile creation; automatic threshold, projection mask and sensitivity; cache verification. No observed search. |
| `mpta-batch`, `tpa-batch`, `ng15-batch` | Source-specific inventory/preparation/calibration/freeze/run workflows; inspect each help before use. |
| `pta-campaign` | Historical source-separated PPTA/EPTA/InPTA campaign recipe. Do not rerun its defaults. |
| `utmost-inventory`, `utmost-prepare` | Inventory, prepared timing/noise model and calibration. |
| `utmost-search freeze`, `run` | Freeze prepared UTMOST inputs, then consume one observed destination. |
| `ipta-prepare` | Check released inputs, fit-window inclusion, timing/noise covariance and independent likelihood. No period search. |
| `ipta-search freeze`, `run` | Bind an accepted preparation and calibration, then search once. |
| `ipta-campaign run` | Sequential/resumable orchestration from a saved `campaign.json`; skips COMPLETE targets and repairs bookkeeping separately. |
| `master-workbook` | Register saved results only; never reruns science. |
| `status --run-root PATH` | Original harness progress; adapter campaigns instead write their own `progress.json` and logs. |

A generic **calibration-only** recipe for an already prepared context:

```sh
tools/recherche calibration ingest \
  --context "$CONTEXT" --target "$TARGET" \
  --timing-model 'Exact source and preparation conventions' \
  --noise-model 'Exact covariance source and assumptions' \
  --minimum-period 30 --maximum-period 400 --output "$NEW_PROFILE"
tools/recherche calibration run --profile "$NEW_PROFILE/profile.json" --cache "$CACHE"
tools/recherche calibration check --profile "$NEW_PROFILE/profile.json" --cache "$CACHE"
```

`CONTEXT` must contain `times`, `covariance`, `design`, `baseline_design` with the
units, row order and nested column spaces specified in the
[calibration array contract](docs/AUTOMATIC_CALIBRATION_2026-09-08.md).
This ingestion does not include observed residuals. A source adapter must provide
those separately. Generic ingestion defaults to one search; for a multi-target
campaign use its adapter to bind `search_count` to the full selected campaign
before calibration. Do not apply a one-target allowance independently to a batch.

An IPTA execution recipe, **only for a separately authorized new run**:

```sh
tools/recherche ipta-prepare --data "$DATA" --target "$TARGET"
# Build the profile using DATA/campaign.json (selected targets and seeds).
PYTHONPATH=src:tools .pixi/envs/default/bin/python tools/ipta_campaign.py profile \
  --data "$DATA" --target "$TARGET" --prepared "$PREPARED"
tools/recherche calibration run --profile "$DATA/$TARGET/profile/profile.json" --cache "$CACHE"
# CACHE_ENTRY is the verified hash-named directory printed by calibration.
tools/recherche ipta-search freeze --data "$NEW_EXECUTION" \
  --profile "$DATA/$TARGET/profile/profile.json" --cache "$CACHE_ENTRY" --preparation "$PREPARED"
tools/recherche ipta-search run --data "$NEW_EXECUTION"
```

A minimal new campaign manifest has `selected: ["TARGET"]` and
`seeds: {"TARGET": INTEGER}`; use the authorized full selection and distinct seeds.
The adapter fixes 30–min(2000, half-span) days and binds the actual selected count.
`PREPARED` is the newly accepted `attemptNN` receipt directory. The current IPTA
pool is already consumed: this recipe is a reference, not a queued reanalysis.

The automatic mask is a projection/identifiability mask across the full grid,
not merely a universal annual veto. Recalibrate when observations, timing design,
noise covariance, policy or runtime binding change. The historical B1937 annual
mask and thresholds remain part of that completed search's evidence.

## 4. Monitor and recover without duplicating work

Run one large dataset at a time; use batches of up to 25 for suitable smaller
sources. Dense PTA covariance calculations need substantial memory and disk.
The recent 13,659-TOA case ran on a 32 GB Mac; source inputs, profiles, frozen
copies and backups can occupy several gigabytes. Large cases can take minutes
without a new outer progress line. Inspect the actual process and worker log.

Use a 30-minute heartbeat for healthy long jobs, with notifications for meaningful
progress changes, completion, failures or required input. No monitor is installed
by this repository: use your harness scheduler or the worker's process supervisor.
Keep a PID, log path and terminal exit status. Do not launch a duplicate runner
when reconnecting. Resume only genuinely missing authorized work.

| Failure | Response |
|---|---|
| Missing clock, ephemeris, include or noise product | Obtain the exact required input and verify its hash; never use a silent fallback. |
| Input/model mismatch | Preserve the failed attempt, diagnose the specific convention and create a new preparation attempt after repair. |
| Historical RMS/χ² differs | For IPTA retain the descriptive flag and use the independent likelihood acceptance checks; do not tune noise or thresholds to match a summary. |
| Calibration cache changed/corrupt | Preserve the cache and diagnose its binding. Do not overwrite it or change the frozen result. |
| Search directory exists | Inspect it and the master. A completed directory is consumed. Do not delete it to rerun. |
| Workbook update fails after science | Repair the workbook update alone using the saved result. A spreadsheet error is not a reason to repeat science. |
| Process exits without terminal result | Register INCOMPLETE/FAILED as appropriate; preserve logs and consumed paths before repairing. |

Do not run the full historical test/qualification suite merely to read results,
update documentation or fix bookkeeping. Use the affected engineering check.
A scientific solver/environment change needs an explicit assessment of which
prior evidence it affects. Preserve the original failed formal qualification.

## 5. Close out every run in the canonical workbook

The canonical workbook is
`outputs/recherche-master-20260908/Project-Recherche-Master.xlsx`.
Never rerun its initial `build.mjs` over the current register. Preserve existing
search rows, operator notes and candidate grades. Record failed/stopped attempts
as well as successful terminal results. Check [master rules](docs/MASTER_WORKBOOK.md).

Source wrappers register observed results after execution. To repair bookkeeping:

```sh
tools/recherche master-workbook "$NEW_EXECUTION" --ipta-observed
# Other observed modes: --utmost-observed, --pta-observed,
# --ng15-observed, --tpa-observed; no mode selects MPTA.
```

The wrapper uses the public, hash-pinned `openpyxl` backend installed by
bootstrap. This is the single supported path since 16 November 2026. The
original updater, which borrows the Codex app's private Node runtime, runs only
with `RECHERCHE_WORKBOOK_BACKEND=codex-node` and is kept for its legacy
preparation and candidate modes. The two write different work-log record IDs,
so do not alternate them on the same closeout. The public backend checks result/freeze/grid hashes, rejects
changed existing results, preserves historical rows and notes, uses an exclusive
lock and content-addressed backup, and replaces the workbook atomically. Existing
records are idempotent. It retains formulas and requests recalculation
when Excel/LibreOffice opens the file; it does not fabricate cached formula values.
Its JSON receipt gives the number of added records without relying on those caches.

For preparation, diagnosis, failures or source reconciliation, create a review
context and register it without science:

```json
{
  "evidence": "/absolute/closeout.json",
  "entries": [["UNIQUE-ID", "Work type", "Target or scope", "STATUS", "Outcome", "Next action or limitation"]],
  "target_updates": []
}
```

`target_updates` may contain `target`, `next_step`, `dataset_status`. Evidence
should contain `master_before_sha256` when it was prepared against a specific
workbook version. Then run:

```sh
tools/recherche master-workbook --review /absolute/workbook-context.json
```

The public fallback covers observed results and review/work-log entries; it does
not emulate the older source-specific JavaScript preparation builders or grading
editor. New candidates receive REVIEW_PENDING rows automatically. To finish their
three-measure grades without the bundled editor, edit only the matching Candidate
grades row using openpyxl/Excel, bind the review evidence, preserve all other rows,
and verify/reopen the resulting workbook. Follow the exact column meanings in
[the grading specification](docs/CANDIDATE_GRADING.md). Never place an uncalibrated
conditional tail in the global FAP or sigma columns.

After each campaign, reconcile the source queue and add a Work log closeout with
searched/held/excluded totals. The portable fallback deliberately does not infer
source exhaustion from a single target result. Update the front page's dated
summary when totals change. Keep old closeout reports as historical evidence.

## 6. Interpret, review, archive and hand off

`NO_TRIGGER` means no eligible grid cell exceeded that fixed conditional
threshold. It does not rule out weaker planets, masked periods, eccentric orbits,
or other datasets. A threshold crossing is a periodic candidate, not a discovery.
Known-companion model-assisted recovery, blind searches and injected simulations
must be labeled separately.

A valid compelling crossing requires the [bounded deep review](docs/CANDIDATE_DEEP_REVIEW.md):
noise alternatives and simulations, observing-day/time/frequency consistency,
and independent-source comparisons where possible. Grade statistical significance,
signal robustness and independent confirmation separately. Use existing candidate
reports as format examples. A noise-sensitive result may remain inconclusive;
there is no requirement to make it positive or negative.

Before handoff, verify terminal status and result bindings, register the outcome,
update the current source queue, write a short report and archive external inputs
and outputs with a file-hash verification receipt. Preserve runtime links and
explain how to reconstruct them on another host. Do not upload multi-gigabyte
inputs or credentials into Git. Commit code, docs, workbook and selected evidence;
push only when the owner authorizes it. Never change repository visibility implicitly.

Report what changed, what ran, the result and limitations, where the evidence
lives, and what remains. Stop completed monitors. Keep fixes small and maintainable;
avoid unrelated redesigns and repeated tests. Do not touch Project Trammel files,
processes or mounts.

For an agent that does not automatically read repository instructions, the owner
can start it with: “Read AGENTS.md and AGENT_README.md, inspect the current master
and source queue, then carry out this bounded task: …”.
