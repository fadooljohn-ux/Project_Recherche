# Project Recherche: operating instructions for AI agents

Start here if you are using Codex, Claude Code, Devin, or another agent with a
shell and filesystem access. Read `AGENTS.md` for the owner's current direction,
then this guide. The latest owner instruction takes precedence over older
chronological authorization entries. You do not need this conversation to operate
the repository. No particular AI service or model is required.

## Current handoff — 9 September 2026

- This is the v0.1.0 publication edition. A release or documentation update
  does not authorize a new scientific workload or repository visibility change.
- There are **754 registered targets, 277 observed identities and 351
  search/refinement records**. Seven retained candidate identities have reviews;
  **no new planet is confirmed**. Dataset counts are not unique-pulsar counts.
- The latest IPTA continuation released seven preparation holds and completed
  seven NO_TRIGGER searches. All 14 compatible IPTA datasets, including the
  earlier J1721 case, have now been searched. Previous results are preserved.
- The supported isolated-pulsar pools in the source queue are complete.
  UTMOST-NS still lacks verified combined timing inputs. UTMOST J1825-0935 is a
  separate legacy-model gap. General binary support remains deferred.
- All completed `run01` destinations are consumed. No observed job is active or
  queued. The existing 30-minute monitor is paused.

Authoritative current records:
[master workbook](outputs/recherche-master-20260908/Project-Recherche-Master.xlsx),
[source queue](docs/FUTURE_DATA_SOURCES.md),
[latest closeout](docs/IPTA_HOLD_RESOLUTION_2026-09-09.md), and
[machine-readable closeout](results/observed/ipta-hold-release-20260909/closeout.json).
Historical reports describe their original closeout, not necessarily today's state.

## 1. Clone and install

```sh
git clone https://github.com/fadooljohn-ux/Project_Recherche.git
cd Project_Recherche
git status --short
python3 tools/agent_setup.py --install
python3 tools/agent_setup.py --check
```

Authenticate if required by the repository visibility. Prerequisites:
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

Expected bootstrap result: `AGENT_RUNTIME_READY`, 71 verified publication source
files (65 unchanged and six diagnostic-message substitutions), correct precision, working public workbook backend, zero scientific fits.
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

`tools/install` invokes the same portable bootstrap. The historical
`tools/recherche doctor` checks the original installation contract; redacted
manifests are archival records, not runnable bindings for this checkout. Use
[the operator guide](docs/OPERATOR_GUIDE.md) and the new bootstrap for this edition.

## 2. Restore or acquire inputs

Git contains code, locks, protocols, reports, the master workbook and selected
result/calibration evidence. It does **not** contain the full raw TOAs, large
covariance/profile arrays, complete clock/ephemeris collections or installed
runtimes. A clone is not a complete data restoration.

Use one of these routes:

1. Obtain the owner's source-specific data archive and checksum receipt, verify
   them, and restore into a new external directory. Preserve historical receipts
   as evidence in the private archive; use logical paths in shared copies. Recreate local runtime links;
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

The wrapper uses the existing bundled spreadsheet backend when available, or the
public `openpyxl` fallback installed by bootstrap. Force the public backend with
`RECHERCHE_WORKBOOK_BACKEND=portable`. It checks result/freeze/grid hashes, rejects
changed existing results, preserves historical rows and notes, uses an exclusive
lock and content-addressed backup, and replaces the workbook atomically. Existing
records are idempotent. The fallback retains formulas and requests recalculation
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
avoid unrelated redesigns and repeated tests. Do not modify unrelated projects, processes or storage mounts.

For an agent that does not automatically read repository instructions, the owner
can start it with: “Read AGENTS.md and AGENT_README.md, inspect the current master
and source queue, then carry out this bounded task: …”.

## Publication evidence

Read [PUBLICATION_PROVENANCE.md](docs/PUBLICATION_PROVENANCE.md). Historical
path-bearing receipts are redacted copies; saved original hashes are deliberately
not rewritten. They cannot be resumed as if they were original frozen packages.
Use `python3 tools/check_publication.py` to verify this release snapshot. A new
run requires newly acquired inputs, local bindings and a new output ID.
