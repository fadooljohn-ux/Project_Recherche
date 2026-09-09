# Pilot 2 Gate 4A-R2 resource-intake readiness closeout

Date: 2026-08-23

Gate outcome: **HOLD BEFORE PROVISIONING — ATTEMPT NOT CONSUMED**

## 1. Authority and stop boundary

The owner's `Proceed` authorized only the stated Gate 4 readiness repair:

1. commit the already approved Gate 4A-R1 successor-root decision;
2. resolve the exact offline-resource intake as far as the existing evidence
   permits; and
3. stop before successor, evidence, or restore-root creation, tests, IOC
   preflight, production manifests, freezes, or science.

The approved design was committed. The intake was then resolved read-only to
exact local bytes, provenance, consumer behavior, and prospective destination
paths. Two binding conflicts prevent an honest frozen intake. This receipt
preserves that HOLD; it does not consume the single Gate 4A-R2 provisioning
attempt.

## 2. Bound repository and preserved external state

Entry repository identity:

- branch: `agent/pilot2-v028-design`
- commit: `937328c33f5b6ec4a0223e06e838cc68468447d9`
- tree: `883c09b81493955b9d2053e18990f4c4ccbe857c`
- sole entry worktree item:
  `docs/PILOT2_GATE4A_R1_SUCCESSOR_ROOT_AND_OFFLINE_RESOURCE_DECISION_2026-08-16.md`
- approved-design SHA-256:
  `835e1c955b4c238d97ef1a77dfffff0b1ac855dcb11cd0f4ceb29a8a17de9fa5`

Approved-design commit:

- commit: `e6a71dbab04c051015d96c4412df99def81e81c4`
- tree: `613ae3acb03c1ec220946fecc9c864202d628451`

Preserved external identities:

- historical root:
  `${RECHERCHE_ARCHIVE_ROOT}/Pulsar-Timing-Pilot-v0.2.1`
- historical marker SHA-256:
  `b71e614da3507e517c1f53b73dd527ce87e5d0cfe1392cd27ec3fff13c3dd5dd`
- successor root: absent
- Gate 4A-R2 evidence root: absent
- Gate 4A-R2 temporary restore root: absent

The historical root was read only for the named resource candidates. No byte
was modified, deleted, acquired, or copied.

## 3. Exact local candidate inventory

`HIST` below means:

`${RECHERCHE_ARCHIVE_ROOT}/Pulsar-Timing-Pilot-v0.2.1`

| Resource and role | Exact existing source | Bytes | SHA-256 | Provenance and disposition |
|---|---|---:|---|---|
| PINT global index | `HIST/derived/cache/astropy/download/url/ab808bf3494c2db41db0ce9ec1404af4/contents` | 3,875 | `55acc602c95d7aa1aa1e9d55dc1f8705f3ea9fee22ea185e60c23ffb71366a87` | URL sidecar binds IPTA `pulsar-clock-corrections/main/index.txt`; upstream repository is BSD-3-Clause. Candidate. |
| Arecibo release override | `HIST/controlled/nanograv15yr-v2.1.0/clock/time_ao.dat` | 492,183 | `7e1755bb794d84bb7e585d556dcf46fffde159ea5d7f9543cd54e7fcb55bf86d` | NANOGrav controlled input; byte-identical to the cached IPTA copy. Candidate. |
| Arecibo global copy | `HIST/derived/cache/astropy/download/url/36fe8d7a16ab23eeb27a998de5b7eea4/contents` | 492,183 | `7e1755bb794d84bb7e585d556dcf46fffde159ea5d7f9543cd54e7fcb55bf86d` | URL sidecar binds IPTA `tempo/clock/time_ao.dat`; BSD-3-Clause. Candidate. |
| Green Bank release override | `HIST/controlled/nanograv15yr-v2.1.0/clock/time_gbt.dat` | 400,170 | `060493be69cd421ce383a91631f089c22e8ed58fb322fdd9f1c4ed3ff2d2797b` | Historical controlled release copy. Candidate only for `PINT_CLOCK_OVERRIDE`. |
| Green Bank global copy | `HIST/derived/cache/astropy/download/url/599e3ebbfc317e090244ee1ef4c79374/contents` | 457,220 | `0611182d913e2462a9636fa52d229d633a7e9e3aa467ec45e4c8a233ed677d08` | URL sidecar binds the newer IPTA `tempo/clock/time_gbt.dat`; BSD-3-Clause. Candidate only for the global-repository role. |
| GPS-to-UTC | `HIST/derived/cache/astropy/download/url/d3c81b5766f4bfb84e65504c8a453085/contents` | 339,264 | `f4409a787ef168bbb4d2eceb4cd14c958d549c099607b3fdd301797546d28638` | URL sidecar binds IPTA `T2runtime/clock/gps2utc.clk`; BSD-3-Clause. Candidate for override and global roles. |
| TAI-to-BIPM2019 release override | `HIST/controlled/nanograv15yr-v2.1.0/clock/tai2tt_bipm2019.clk` | 36,459 | `3d1e27041f0c7a6c7aa79d2d6d5b90235ac2e73d436defcfc6e8d6fcdd78f512` | Historical controlled copy; byte-identical to cached IPTA copy. Candidate. |
| TAI-to-BIPM2019 global copy | `HIST/derived/cache/astropy/download/url/933016e2bd847bd221b3d1497cadbb1a/contents` | 36,459 | `3d1e27041f0c7a6c7aa79d2d6d5b90235ac2e73d436defcfc6e8d6fcdd78f512` | URL sidecar binds IPTA `T2runtime/clock/tai2tt_bipm2019.clk`; BSD-3-Clause. Candidate. |
| DE440 kernel | `HIST/derived/cache/astropy/download/url/dabea460521989808aedfb52df4e07e4/contents` | 119,799,808 | `a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5` | URL sidecar binds the authoritative NAIF/JPL `de440.bsp`. Public authoritative source verified; exact redistribution status remains unbound, so local-use candidate only. |
| IERS-A | `.pixi/envs/default/lib/python3.11/site-packages/astropy_iers_data/data/finals2000A.all` | 3,756,992 | `f707ea5031a467f1a3b2f0645fac2f627095ed0cb41d34c515b495cb81a5a25d` | `astropy-iers-data==0.2026.8.3.0.53.6`, BSD-3-Clause. Exact byte identified; destination/runtime binding unresolved. |
| IERS-B | `.pixi/envs/default/lib/python3.11/site-packages/astropy_iers_data/data/eopc04.1962-now` | 5,158,836 | `f04b166d36f9dde242d3aaae8349a53b8b0b69d287941dcbbfd05cadcb00c673` | Same pinned package and license. Exact byte identified; destination/runtime binding unresolved. |
| Leap-second table | `.pixi/envs/default/lib/python3.11/site-packages/astropy_iers_data/data/Leap_Second.dat` | 1,352 | `6cb6f5d4b819f2e568e25db4b0b26d89dedf031fdffb18bc94d40f4e94e268d7` | Same pinned package and license. Exact byte identified; destination/runtime binding unresolved. |

The historical `ao2gps.clk` and `gbt2gps.clk` files are excluded from this
candidate allowlist. Static inspection of PINT 1.1.5 binds the selected Arecibo
and Green Bank observatories to `time_ao.dat` and `time_gbt.dat`, with the
separate `gps2utc.clk` correction. The two `*2gps.clk` files remain preserved
historical inputs and may be admitted only if the later real resource-open
trace proves they are consumed.

Authoritative provenance checked during this intake:

- IPTA clock repository and BSD-3-Clause license:
  `https://github.com/ipta/pulsar-clock-corrections`
- IPTA live resource status:
  `https://ipta.github.io/pulsar-clock-corrections/status.html`
- authoritative NAIF/JPL DE440 directory:
  `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/`
- NASA scientific-data license guidance:
  `https://science.data.nasa.gov/about/license`

No resource byte was fetched from these sites.

## 4. Deterministic destination candidates resolved without writing

The four direct release-clock destinations are finite:

- `controlled/clock-overrides/time_ao.dat`
- `controlled/clock-overrides/time_gbt.dat`
- `controlled/clock-overrides/gps2utc.clk`
- `controlled/clock-overrides/tai2tt_bipm2019.clk`

For the exact canonical successor path, `Path.as_uri()` makes the local PINT
repository base:

`file://${EXTERNAL_VOLUME}/Vera%27s%20Folder/Project%20Recherche/Pulsar-Timing-Pilot-v0.2.8-gate4/derived/cache-v0.2.8/`

The corresponding prospective Astropy cache-content paths are:

| Logical resource | Prospective relative path |
|---|---|
| global `index.txt` | `derived/cache-v0.2.8/astropy/download/url/aa7dc3a945fb1b6f48750cad3ed0b5d9/contents` |
| global `time_ao.dat` | `derived/cache-v0.2.8/astropy/download/url/0bd48d155a0b9251158f3e24173f1f46/contents` |
| global `time_gbt.dat` | `derived/cache-v0.2.8/astropy/download/url/f8f60f90e28f97382f57e49b3d981841/contents` |
| global `gps2utc.clk` | `derived/cache-v0.2.8/astropy/download/url/8aa87c33eb747ed5cf7dd7c12a442431/contents` |
| global `tai2tt_bipm2019.clk` | `derived/cache-v0.2.8/astropy/download/url/3e9dc2c8c13f8325f7e93f329f639685/contents` |
| DE440 | `derived/cache-v0.2.8/astropy/download/url/dabea460521989808aedfb52df4e07e4/contents` |

Only `contents` is a candidate. An Astropy `url` sidecar is not required for a
cache hit and would be an unlisted extra file under the existing exact-tree
validator.

These paths are candidate design evidence, not a frozen production resource
manifest. No IERS destination is declared because doing so now would conceal
the unresolved consumer binding below.

## 5. Blocking conflicts

### R1 — PINT index resolution is time-dependent

PINT 1.1.5 constructs its global `Index` even when `PINT_CLOCK_OVERRIDE`
provides the release clock. The index uses a one-day `if_expired` policy. The
current `LocalPintRepository` makes `derived/cache-v0.2.8` both the file-URL
repository and `XDG_CACHE_HOME`.

A preseeded cache-only layout can be exact on the first day but becomes
time-dependent when the index expires. Adding raw repository files makes the
recursive resource inventory contain files that a cache-hit context does not
open. Allowing refresh creates cache writes and makes first and later traces
different. Therefore the present repository/cache contract cannot prove one
stable, exact resource-open set over time.

### R2 — the exact IERS bytes are identified but not controlled

The existing boundary disables IERS auto-download but does not redirect
Astropy to project-controlled IERS files. Astropy therefore reads the pinned
package copies outside the two traced data-root resource trees. Copying the
three exact files into either resource tree without a consumer binding would
make them manifested-but-unopened and fail the exact trace.

The current environment manifest records the package artifact identity but
does not verify these three installed data-file bytes individually. Treating
that package record as an exact live-file check would overstate the evidence.

### R3 — DE440 use is indirect and redistribution remains bounded

The exact local DE440 byte and future cache key are known. The runtime asks for
`DE440` without an explicit local path, so the existing contract still relies
on an Astropy cache hit. This can be qualified later only after R1 is resolved.
The present record permits local scientific use only and does not assert a
kernel-specific external redistribution license.

## 6. Disposition

- approved Gate 4A-R1 design commit: **PASS**
- exact local candidate discovery: **PASS**
- exact source sizes and SHA-256 identities: **PASS**
- IPTA and pinned IERS license/provenance closure: **PASS**
- deterministic PINT repository/cache binding: **HOLD**
- exact controlled IERS binding: **HOLD**
- DE440 local cache binding and redistribution classification: **HOLD**
- Gate 4A-R2 provisioning attempt: **NOT STARTED; ATTEMPT UNCONSUMED**

This is an environment/resource-binding HOLD, not a harness failure and not a
scientific failure.

## 7. Governance and anti-spiral accounting

- harness or science source files changed: `0`
- test files changed: `0`
- new commands, runners, resolvers, observers, services, brokers, retry paths,
  or control planes: `0`
- test or preflight invocations: `0`
- successor/evidence/restore roots created: `0`
- production manifests or freezes created: `0`
- scientific cases, fits, or solver audits executed: `0`
- observed-residual or observed-periodic-search access: `0`
- runtime resource downloads: `0`
- authoritative web research calls: `3`

The work remains inside Gate 4 entry preparation and reuses the accepted
minimalist harness. No design spiral occurred.

## 8. Next bounded stage — Gate 4A-R3 resource-binding correction design

The next prospective stage is one short design only. It must select the
smallest supported binding inside the existing `pilot2_offline_resources.py`
boundary that:

1. makes PINT index resolution independent of cache age without modifying
   installed PINT source;
2. binds the three exact IERS bytes above to the same context used by preflight
   and science;
3. binds DE440 to the exact local byte without a network or cache fallback;
4. preserves the current manifest schemas and operator surface if possible;
5. changes no science construction, thresholds, inventory, or outcomes; and
6. stops as a design spiral if a new command, context constructor, control
   plane, general resolver framework, or second science path is required.

Its sole permitted write would be one short prospective design document.
Implementation, tests, provisioning, preflight, manifests, freezes, and science
would remain separately unauthorized.
