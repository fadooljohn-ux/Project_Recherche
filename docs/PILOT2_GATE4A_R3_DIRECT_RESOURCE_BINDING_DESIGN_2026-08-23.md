# Pilot 2 Gate 4A-R3 direct resource-binding correction

Date: 2026-08-23

Status: **DESIGN COMPLETE — implementation remains unauthorized**

## 1. Decision in plain language

Keep the existing IOC harness, operator commands, resource-manifest schema, and
scientific context path. Replace the age-dependent PINT file-URL cache binding
inside the existing offline boundary with finite direct bindings to the exact
local clock, IERS, leap-second, and DE440 files listed below.

This is a resource-binding correction only. Gate 4A-R2 remains on HOLD before
provisioning, and its single provisioning attempt remains unconsumed.

## 2. Bound baseline

- repository branch: `agent/pilot2-v028-design`
- repository commit: `0ecae661da41548f3e2e7d8038f31f7af7a3a5f4`
- repository tree: `f220002954b7e83df35891a429170a11aba5f1e4`
- operational IOC plan SHA-256:
  `e1a1d97cfeb3482bb413feee53ce7d2426ff7f9542b2f51cb271ad0b8bd19ec9`
- Gate 4-R1 correction SHA-256:
  `c05c851b23fadf30b603741f63eb63ed8e4b7568dccdd25509ac05e1be29fab9`
- Gate 4A-R1 design SHA-256:
  `835e1c955b4c238d97ef1a77dfffff0b1ac855dcb11cd0f4ceb29a8a17de9fa5`
- Gate 4A-R2 HOLD SHA-256:
  `bb41d3d1267010ef9fac0546d83b94f19df22c39b11d8ec1f6e955714e29c89c`
- pinned consumers: PINT `1.1.5`, Astropy `8.0.1`

The historical v0.2.1 root remains immutable. The successor, evidence, and
restore roots remain absent.

## 3. Exact future resource closure

The schema-1 manifest keeps the existing two controlled roots:

- `controlled/clock-overrides`
- `derived/cache-v0.2.8`

Its entries will be exactly these ten regular files:

| Controlled relative path | Bytes | SHA-256 | Resolution role |
|---|---:|---|---|
| `controlled/clock-overrides/time_ao.dat` | 492,183 | `7e1755bb794d84bb7e585d556dcf46fffde159ea5d7f9543cd54e7fcb55bf86d` | `observatory_clock` |
| `controlled/clock-overrides/time_gbt.dat` | 400,170 | `060493be69cd421ce383a91631f089c22e8ed58fb322fdd9f1c4ed3ff2d2797b` | `observatory_clock` |
| `controlled/clock-overrides/gps2utc.clk` | 339,264 | `f4409a787ef168bbb4d2eceb4cd14c958d549c099607b3fdd301797546d28638` | `gps_clock` |
| `controlled/clock-overrides/tai2tt_bipm2019.clk` | 36,459 | `3d1e27041f0c7a6c7aa79d2d6d5b90235ac2e73d436defcfc6e8d6fcdd78f512` | `bipm_clock` |
| `derived/cache-v0.2.8/iers/finals2000A.all` | 3,756,992 | `f707ea5031a467f1a3b2f0645fac2f627095ed0cb41d34c515b495cb81a5a25d` | `iers_a` |
| `derived/cache-v0.2.8/iers/ReadMe.finals2000A` | 3,429 | `7c6182cc0fd0cbece39711f648d15e48b49168925602e360a5709c5ccc8d5a12` | `iers_a` |
| `derived/cache-v0.2.8/iers/eopc04.1962-now` | 5,158,836 | `f04b166d36f9dde242d3aaae8349a53b8b0b69d287941dcbbfd05cadcb00c673` | `iers_b` |
| `derived/cache-v0.2.8/iers/ReadMe.eopc04` | 3,275 | `42d7890543fae69df024219d1d36f242b4fcd847f6f8a756c7d37c5dfd100243` | `iers_b` |
| `derived/cache-v0.2.8/iers/Leap_Second.dat` | 1,352 | `6cb6f5d4b819f2e568e25db4b0b26d89dedf031fdffb18bc94d40f4e94e268d7` | `leap_seconds` |
| `derived/cache-v0.2.8/ephemerides/de440.bsp` | 119,799,808 | `a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5` | `solar_system_ephemeris` |

The source provenance and license dispositions remain those recorded in the
Gate 4A-R2 intake. DE440 remains approved for this local scientific use only;
this design makes no broader redistribution claim.

The two parser READMEs extend that intake by two exact dependencies from the
same pinned `astropy-iers-data==0.2026.8.3.0.53.6` package data directory as
the three IERS data files. Both are BSD-3-Clause package content; their sizes
and hashes above were remeasured from the bound Pixi environment. The later
intake record must carry these source paths, package identity, and license
disposition before provisioning.

The PINT `index.txt`, duplicate global-clock cache files, Astropy URL-cache
paths, and URL sidecars are rejected from the future manifest. They remain R2
candidate evidence, not admitted resources. Nothing is deleted by this design.

The exact required resource classes will be `observatory_clock`, `gps_clock`,
`bipm_clock`, `iers_a`, `iers_b`, `leap_seconds`, and
`solar_system_ephemeris`. Parser READMEs share their corresponding IERS role.

## 4. Exact future binding inside the existing boundary

### PINT clocks

Add one private, four-name adapter inside
`src/pulsar_pilot/pilot2_offline_resources.py`:

1. allow only `time_ao.dat`, `time_gbt.dat`, `gps2utc.clk`, and
   `tai2tt_bipm2019.clk`, with no path separators;
2. install the adapter temporarily at both live PINT call sites,
   `pint.observatory.find_clock_file` and
   `pint.observatory.topo_obs.find_clock_file`;
3. accept only PINT's default lookup or the exact controlled clock directory,
   reject a non-null URL base and every TEMPO, TEMPO2, or other directory;
4. call the saved original function with the exact controlled directory passed
   explicitly as `clock_dir`, while preserving the scientific format and flag
   arguments; and
5. reject every unknown filename instead of falling back.

Preserve PINT 1.1.5's full six-argument signature: `name`, `format`,
`bogus_last_correction`, `url_base`, `clock_dir`, and
`valid_beyond_ends`.

Save the primary callable and patch it before any possible `topo_obs` import.
If `topo_obs` is already loaded, save and patch its imported alias. If it loads
later, require its alias to be the adapter. Restore both call sites to their
exact pre-entry callables; if the module first loaded inside the boundary,
replace its surviving alias with the saved primary callable on exit.

The direct `clock_dir` branch returns before PINT constructs its global
`Index`. Therefore clock resolution has no cache-age rule, refresh, download,
or cache write. The current `_reset_pint_clock_state()` remains immediately
before the boundary. `PINT_CLOCK_OVERRIDE` may remain temporarily bound and
restored as a defensive identity, but it is not the resolution mechanism.

After that existing reset, snapshot PINT's `_gps_clock`,
`_bipm_clock_versions`, and every observatory `_clock` value. Restore those
exact boundary-entry values on success or exception. In the real context they
will normally be the deliberately empty values established by the reset.

Remove the existing file-URL repository and `XDG_CACHE_HOME` resolution role.
Do not modify installed PINT source.

### IERS-A and IERS-B

Read the controlled IERS-B file with `ReadMe.eopc04`, temporarily install that
table in PINT's pinned Astropy `IERS_B.iers_table` cache, then read the
controlled IERS-A file with `ReadMe.finals2000A` through `IERS_Auto.read`.
This retains Astropy's normal replacement of overlapping A values with final
B values. Install the resulting table through `earth_orientation_table.set`
for the boundary lifetime. Do not call `IERS_Auto.open` and do not use a
package-data or download fallback.

Set `iers.conf.auto_download = False` before installing the tables and retain
that value for the full active-table lifetime. Do not relax `auto_max_age`; a
stale controlled table fails instead of refreshing.

Save and restore the prior `IERS_B.iers_table`, `IERS_Auto.iers_table`, Earth
orientation ScienceState, and `iers.conf.auto_download` values on both success
and exception. Snapshot the pinned raw `earth_orientation_table._value`
identity without calling `.get()`, because `.get()` can materialize an
uncontrolled `IERS_Auto` table. Permit only `None` or an already materialized
in-memory table at entry, restore that raw identity without validation or file
access, and fail closed if the private state shape differs.

### Leap seconds

Parse only the controlled `Leap_Second.dat` with
`LeapSeconds.from_iers_leap_seconds`. Save the current ERFA table, reset ERFA
to its built-in table, and update it from the controlled table so pre-1972
pseudo-leap entries are preserved.

For pinned Astropy 8.0.1 only, temporarily set
`astropy.time.core._LEAP_SECONDS_CHECK` to its existing `DONE` enum after the
controlled update. This bounded compatibility shim prevents Astropy's first
UTC conversion from opening package or remote fallback files. Save and restore
the prior flag and exact ERFA table. A changed or missing private symbol fails
closed; it does not justify a general resolver.

### DE440

Save PINT's complete `loaded_ephems` mapping and Astropy's current
solar-system-ephemeris state without invoking an accessor that can open a
kernel. PINT's mapping must have no live `de440` entry. Astropy's pinned raw
entry state must have `_value == "builtin"` and `_kernel is None`; otherwise
fail closed before resource binding. Then call the supported
`pint.solar_system_ephemerides.load_kernel("DE440", path=...)` with the exact
controlled `de440.bsp`. Require the resulting loaded path to resolve to that
file. This prevents an old in-memory entry, cache lookup, built-in ephemeris,
or network mirror from winning.

On exit, close the controlled kernel and restore the prior PINT mapping and
Astropy state exactly. Restoration may not perform network or unmanifested
resource access. A symbolic or file-backed prior Astropy state that would need
resolution is rejected at entry, not reopened during exit.

### Ordering and restoration

Keep the existing `OfflineRuntimeBoundary` and the existing
`pilot2_runtime_core.prepare_context` call path. Boundary entry will:

1. snapshot environment, function, cache, ERFA, and ScienceState identities
   without opening a resource;
2. install the finite clock adapter;
3. enter the existing network denial and resource-open tracer;
4. bind IERS, leap seconds, and DE440 under those guards; and
5. run all current model, TOA, and time-dependent construction before exit.

Exit restores every process-global value in reverse order while the guards are
still active, then performs a final exact-trace and zero-network check before
removing the guards. Any entry, body, or exit failure unwinds transactionally
and fails the context. No fallback or partially modified library state is
permitted.

## 5. Later implementation and acceptance limit

A separately approved Gate 4A-R4 may change exactly two files:

- `src/pulsar_pilot/pilot2_offline_resources.py`
- `tests/test_pilot2_science_module.py`

Focused disposable tests must prove:

- no PINT index construction at any file age and no refresh/download/cache
  write;
- only the four allowlisted clock names and exact controlled paths are used;
- controlled IERS-A/B substitution, controlled leap seconds, and direct DE440
  are selected with no fallback;
- all patched functions, environment values, Astropy/PINT caches, ERFA data,
  and ScienceState values are restored after success and injected failure;
- two boundary entries produce the same exact ten-resource trace and context
  binding;
- network and every science counter remain zero; and
- the manifest schema and operator surface remain unchanged.

Tests may use only disposable roots and focused library fakes or local fixtures.
They may not access `/Volumes`, create the successor or production evidence,
run the real B1937+21 context, create a manifest or freeze, or execute science.

If implementation requires `pilot2_runtime_core.py`, the IOC harness, a new
command or context constructor, a generalized resolver, a service, a second
science path, an installed-package edit, or a third source/test file, stop as a
design spiral.

For this HOLD only, the owner-approved R3 correction prospectively supersedes
Gate 4-R1's narrower phrase that limited `pilot2_offline_resources.py` to
manifest construction. Gate 4A-R2 specifically routes this binding repair into
the existing offline boundary. The filename, two-file cap, zero-science rule,
operator surface, and every other Gate 4-R1 restriction remain unchanged.
This clarification grants no present implementation authority.

## 6. Governance and stop

This design remains true to the operational IOC plan: AI supervises the
minimalist harness, the operator controls every gate, and the purpose remains
reaching an operational state to conduct the already defined science. It adds
no scientific question, threshold, inventory, case, fit, or interpretation.

The current authorization permits this one document only. It permits no code
or test edit, resource copy, provisioning, root creation, preflight, manifest,
freeze, commit, push, or science. Stop after reporting this file's SHA-256.

The next prospective stage is Gate 4A-R4: commit the approved R3 design, make
the two-file implementation above, run only its focused disposable acceptance,
and stop before any provisioning or real-root access. It requires separate
owner approval.
