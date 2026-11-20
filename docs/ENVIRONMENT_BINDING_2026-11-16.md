# Environment binding and compatibility assessment, 2026-11-16

Owner authorization: "Do the qualification binding."

**Status: complete. `tools/recherche doctor` PASS at the new checkout. This is a
host binding with a bounded compatibility assessment, not a new formal
qualification.**

## Why a binding was needed

The qualification 02 environment record,
`protocol/PILOT2_RUNTIME_ENVIRONMENT_MANIFEST_v0.2.8.json`, pins the Python
executable hash and the exact macOS version. Both changed:

| Item | Qualification 02 | Now |
|---|---|---|
| Checkout | `.` | `.` |
| Python executable SHA-256 | `93a407ec…38c9f4e9` | `dcde6255…5becb6ce` |
| macOS | 26.6.2 | 27.2.1 (Mac17,2, Apple M5, Rosetta 2) |

Because the macOS version changed, moving the checkout back to the old path
would no longer satisfy the frozen record on this Mac.

## What is unchanged

Checked live against the frozen record: Python 3.11.15, all 134 Conda package
identities, the five critical-module hashes (astropy, numpy, pint, pint.fitter,
scipy), x86_64 process, 63 long-double mantissa bits, the thread-variable
policy, `pixi.lock`, `pixi.toml` and `pyproject.toml`. All 71 qualified source
files match the qualification 02 lock, and the IOC execution-freeze
verification passes.

The new Python executable was byte-compared with the preserved qualified copy
in `../Recherche Recovery/20260907T223404/stage6-original-environment/`. The
files have the same length and differ in 53 bytes, all inside the embedded
installation-prefix string. This matches the stage 6 relocation diagnosis.

## Binding

`protocol/RUNTIME_ENVIRONMENT_BINDING_20261116.json` records the superseded and
bound values for those two fields and names this checkout. The frozen manifest,
the execution freeze and every historical record are unedited.

`tools/recherche doctor` now validates the frozen manifest's structure, then
applies the binding and verifies the live environment. The binding is used only
when the checkout path matches and the manifest holds exactly the superseded
values; packages, modules, precision and variables are still verified exactly.
`doctor` reports `"environment_binding": "recherche-environment-binding-20261116"`.
`tools/install` now names the new canonical checkout. A further path, host or
macOS change needs a new binding record.

## Compatibility assessment

The B1257+12 known-system benchmark was repeated in a new work area,
`../Project Recherche Data/environment-binding-20261116/`, through
`tools/recherche` with network access denied. The saved benchmark evidence and
the master workbook were not modified.

- **Preparation** (PINT, clock and ephemeris resources, extended precision),
  repeated from the original PAR/TIM/clock inputs with the current tool: the
  prepared `context.npz` is byte-identical to the September file.
- **Exact-source repeat** of `run01` and `refinement01` using the saved source
  snapshots: 34 of 34 arrays bitwise identical and 261 of 261 JSON values
  identical, including calibration, 4,096 null maxima, all scans, both orbit
  fits and the final result. The only difference is the predecessor
  `result.json` hash, which covers the elapsed time.
- **Current-tool repeat**: calibration, null maxima, projection map, first scan
  and the whole of `refinement01` (orbit fit, post-fit residuals, final scan)
  are identical. The `run01` orbit fits differ because
  `tools/b1257_benchmark.py` was repaired after the saved `run01`, as the
  benchmark report describes; this is a source difference, not an environment
  difference.

Evidence: `results/qualification/environment-binding-20261116.json`, with the
full comparisons beside the repeat in the work area.

## Other changes in this release

- `tools/recherche` puts the native Git first on PATH only when the
  `/usr/bin/git` shim cannot start from the Intel runtime (the Command Line
  Tools `libxcrun` on this host has no x86_64 slice).
- `tests/test_environment_binding.py` covers the binding rules. The suite
  passes: 452 passed, 8 deselected.

## Limits

Update, 2026-11-17: Qualification 03 passed 21/21 on this host with a
host-native environment manifest, so the first two limits below no longer
apply. See `QUALIFICATION_03_2026-11-16.md`. The binding record remains only
for verifying work frozen against the qualification 02 manifest.

- The 21/21 qualification 02 record was produced on the original host and is
  not re-run here; `historical_host_qualification_transferred` remains false.
- The pilot 2 `develop` and formal conductor commands validate the frozen
  manifest inside qualified source and remain bound to the original host. They
  need a source change and requalification, or a new formal qualification, to
  run here.
- No new observed search, calibration or formal qualification case was run.
- `../Recherche Releases/operational-20260908/runtime.tar.gz` restores the old
  prefix. Rebuild with `tools/install` or `tools/agent_setup.py --install`.
