# Recherche operator guide

**Fresh GitHub checkout or another AI harness:** start with
[AGENT_README.md](../AGENT_README.md) and `python3 tools/agent_setup.py --install`.
The installation/restore instructions below preserve the original qualified
host and its path-bound manifests. They are not the fresh-checkout bootstrap.

Automatic per-target calibration is available through `tools/recherche calibration`.
See [the calibration guide](AUTOMATIC_CALIBRATION_2026-09-08.md) for profile
ingestion, threshold/mask/sensitivity generation and cache reuse.

Owner: John Fadool. Updated 2026-09-08. Run installation checks after a restore,
host update or dependency change; back up after completed workloads.

The supported installation is this repository on the current Mac, using its
Intel `.pixi` Python and `tools/recherche`. Qualification 02 passed all 21 gates, and
Qualification 03 repeated that on the relocated checkout on 17 November 2026.
The qualified scientific source is unchanged by operational packaging.
Observed-data searches require their own approved workload and are not enabled
by stage 6. No additional qualification is needed for routine status checks.

## Install or restore

**16 November 2026:** the installation moved to
`.` on macOS 27.2.1
and was rebound there; see
[the environment binding report](ENVIRONMENT_BINDING_2026-11-16.md). The paths
below describe the original September release. Its `runtime.tar.gz` restores the
old prefix. Use the refreshed package described in
[the 16 November release](OPERATIONAL_RELEASE_2026-11-16.md), or rebuild the
environment with `tools/install`.

The release package is `../Recherche Releases/operational-20260908/`.
It contains source/history, the qualified Intel runtime, Pixi, locked dependency
declarations, an admitted-input archive and checksums. Keep it with its receipts.
The source must be restored at the canonical location shown below. Python embeds
its installation prefix, and the qualification binds the resulting executable
hash. Arbitrary relocation is not supported by this release. Before restoring,
move an existing installation to a named recovery location; keep it until the
replacement passes verification. The canonical checkout path must be absent
before `git clone`. The input destination must also be new.

```sh
release='../Recherche Releases/operational-20260908'
cd "$release"
shasum -a 256 -c SHA256SUMS
checkout='.'
data='/absolute/path/to/Recherche Data'
git clone "$release/recherche.bundle" "$checkout"
cd "$checkout"
tar -xzf "$release/runtime.tar.gz" -C "$checkout"
mkdir "$data"
tar -xf "$release/inputs.tar" -C "$data"
tools/recherche doctor --data-root "$data"
```

Expected: `PASS`, 134 packages, 63 long-double mantissa bits, 21 inputs and
10 resources. The runtime archive supports offline restore without a package
cache. To reconstruct the environment instead, run
`RECHERCHE_PIXI="$release/pixi" tools/install`; it uses `pixi install --locked`
and may download exact locked packages when the local cache is empty. Scientific commands
deny network access. Apple Silicon requires Rosetta to run the Intel environment.
The environment manifest is bound to the qualified macOS version; a different
host, OS version or checkout path needs a new environment binding and compatibility
review before treating it as accepted. The installer reports a path mismatch
before installing packages. This limitation was demonstrated during stage 6;
restoring at the canonical path preserves the qualified executable identity.

On the existing installation, these are the only setup commands:

```sh
cd '.'
tools/install
data='../Project Recherche Data/operational-20260908'
tools/recherche doctor --data-root "$data"
```

`doctor` verifies scientific source, manifests, Python, installed packages,
precision and optional input/resource hashes. It performs zero scientific fits.
Do not manually repair package caches or edit manifests to make a mismatch pass.
Restore the release at its canonical location and run the locked installer.

## Run and monitor a development workload

The current working input root is
`../Project Recherche Data/operational-20260908/`. Qualification roots remain
historical evidence. To create another working root from admitted inputs:

```sh
tools/recherche init-data --from-data-root "$data" --data-root '/absolute/new/data-root'
```

It copies only admitted inputs and metadata; the destination must not exist.
For the smallest ordinary development check:

```sh
tools/recherche develop --data-root "$data" --case-family main
```

The command generates a fresh attempt ID and prints the result on completion.
`--solver-check` selects the two retained annual fixtures and ordinary control;
omit the selector for the four standard development fixtures. Use these broader
checks only when a repair warrants them. Do not reuse completed attempt IDs.

From another terminal, substitute the printed run directory:

```sh
tools/recherche status --run-root "$data/development-runs/RUN_ID"
```

`state`, `completed`/`total`, process state, heartbeat and RSS show progress.
Check long work every 30 minutes. Investigate a missing process before terminal
state, no case progress across an interval, or a stale inner health heartbeat.
A long case can leave the outer checkpoint unchanged while the worker remains
healthy. Do not restart a run because a single checkpoint is delayed.

Press Ctrl-C in the foreground terminal to stop. A controlled stop returns 130
and retains partial evidence. Diagnose the specific error and start a fresh
development attempt after repair; never overwrite the interrupted record.

## Read results and back up

Each development directory contains `status.json`, the terminal inventory and
its bound artifacts. Read the scientific result as well as execution status:
execution completion alone does not establish a scientific PASS. Qualification
02's verified result is linked from `QUALIFICATION_02_2026-09-08.md`.
The 365.25-day period remains excluded by the qualified eligibility rule.

Once the data root has no active runs:

```sh
tools/recherche backup --data-root "$data" --output '/absolute/new/Recherche-data.tar'
```

Expected: `PASS` plus a `.receipt.json` beside the archive. This checks the exact
file set, archived content hashes and unchanged source hashes. Use a new archive
name each time. Restore to an empty directory with `tar -xf`, then run `doctor`.
Completed run manifests retain their original absolute paths; restored terminal
records are evidence, not resumable attempts. Generate new development attempts
for a relocated working root.

For source changes, preserve history separately:

```sh
git bundle create '/absolute/new/Recherche-source.bundle' --all
git bundle verify '/absolute/new/Recherche-source.bundle'
```

Keep the qualified release package and original qualification results. If an
upgrade fails, return to the previous checkout and its original `.pixi`
environment or restore the bundle and run `tools/install`. Keep new run evidence.

## Maintenance and failures

IPTA's 14 compatible datasets are now complete, including the seven subsequently
released holds. Use the [current closeout](IPTA_HOLD_RESOLUTION_2026-09-09.md)
and master rather than the initial J1721 preparation state. The separate locked
TEMPO2 runtime and legacy conventions remain described in
[the adapter report](IPTA_BOUNDED_ADAPTER_2026-09-09.md).

| Symptom | Action |
|---|---|
| Pinned environment missing | Run `tools/install`; use bundled Pixi if absent from PATH. |
| Environment or precision differs | Restore the locked environment at the canonical path; verify Intel Python/Rosetta and host version. |
| Input hash differs | Restore the admitted input archive into a new root and verify it. |
| Qualified source differs | Inspect the local diff; use the packaged source for qualified operation. |
| Backup says a run is active | Let it complete or stop it deliberately before backing up. |
| Fit or solver failure | Preserve the attempt, diagnose locally with the relevant development fixture, then repair. |

Pin dependency updates deliberately. After code changes, run affected checks;
run the current suite before a new release. Do not repeat qualification for
documentation or operator-only changes. Changes to scientific code or environment
need a bounded assessment of which evidence must be renewed. The owner decides
new formal or observed-data workloads; report the concrete issue and saved run
path if that decision is needed.
