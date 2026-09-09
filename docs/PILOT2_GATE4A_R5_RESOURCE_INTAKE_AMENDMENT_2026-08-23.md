# Pilot 2 Gate 4A-R5 corrected resource-intake amendment

Date: 2026-08-23

Status: **AMENDMENT COMPLETE — provisioning remains unauthorized**

## 1. Decision in plain language

The accepted direct-binding correction reduces the future offline resource set
to ten exact local files. A later, separately authorized provisioning attempt
may copy only those files into the already designed successor root. It may not
use PINT's dated index/cache layout, download a replacement, or invent a byte.

This is a prospective intake amendment subordinate to the operational IOC plan.
It does not edit or regrade the Gate 4A-R2 HOLD. That receipt remains **HOLD
BEFORE PROVISIONING**, and its predeclared single provisioning attempt remains
**not started and unconsumed**. No real-root qualification or Gate 4 PASS is
claimed here.

## 2. Bound implementation and governing identities

- branch: `agent/pilot2-v028-design`
- accepted implementation commit:
  `f4c29328d7f3b6a6e8b036eb628c74e3cd31b1d6`
- accepted implementation tree:
  `8267dc158101b71b529f24c45ccc3cdf9ea2cd8c`
- parent R3-design commit:
  `a4595a2ba0b3ac4c0f42851102147a51ee9ed6b7`
- implementation payload SHA-256:
  `96f1fe7a63d1b0aa8c973eccfff30a6688cdab151874323033d74d61fc77e4b9`
- `src/pulsar_pilot/pilot2_offline_resources.py` SHA-256:
  `9737bc31f8be0cc0e530973a0e299ec2faa2c16b26fc3434808854bead9204f8`
- `tests/test_pilot2_science_module.py` SHA-256:
  `3970cfaac299740b43c44a0b0a6caf68450f117eea053060b697bd02c68f6133`
- operational IOC plan SHA-256:
  `e1a1d97cfeb3482bb413feee53ce7d2426ff7f9542b2f51cb271ad0b8bd19ec9`
- Gate 4-R1 correction SHA-256:
  `c05c851b23fadf30b603741f63eb63ed8e4b7568dccdd25509ac05e1be29fab9`
- Gate 4A-R1 successor-root decision SHA-256:
  `835e1c955b4c238d97ef1a77dfffff0b1ac855dcb11cd0f4ceb29a8a17de9fa5`
- Gate 4A-R2 HOLD SHA-256:
  `bb41d3d1267010ef9fac0546d83b94f19df22c39b11d8ec1f6e955714e29c89c`
- Gate 4A-R3 design SHA-256:
  `7df99e1bcf4d537eb5522e29b9689ed1b44fe98784dba0c6004f1f229a4038f4`
- pinned consumers: PINT `1.1.5`, Astropy `8.0.1`

Gate 4A-R4 disposable acceptance recorded 7/7 focused checks and 12/12 of
the complete Gate 4 test subset passing, with lint, format, and diff checks
clean. The committed payload is byte-identical to that accepted diff. These
are disposable implementation results, not real-root qualification.

## 3. Exact ten-file intake

The source shorthands below are exact:

- `HIST` = `${RECHERCHE_ARCHIVE_ROOT}/Pulsar-Timing-Pilot-v0.2.1`
- `ENV` = `./.pixi/envs/default/lib/python3.11/site-packages/astropy_iers_data/data`

The table order is the canonical future entry order produced by
`build_resource_manifest()`: lexicographic order of controlled relative path.
The logical names, destinations, sources, sizes, and hashes are exact and may
not be substituted.

| Logical name | Controlled relative destination | Exact local source | Bytes | SHA-256 |
|---|---|---|---:|---|
| `gps-to-utc-clock` | `controlled/clock-overrides/gps2utc.clk` | `HIST/derived/cache/astropy/download/url/d3c81b5766f4bfb84e65504c8a453085/contents` | 339,264 | `f4409a787ef168bbb4d2eceb4cd14c958d549c099607b3fdd301797546d28638` |
| `tai-to-tt-bipm2019-clock` | `controlled/clock-overrides/tai2tt_bipm2019.clk` | `HIST/controlled/nanograv15yr-v2.1.0/clock/tai2tt_bipm2019.clk` | 36,459 | `3d1e27041f0c7a6c7aa79d2d6d5b90235ac2e73d436defcfc6e8d6fcdd78f512` |
| `arecibo-observatory-clock` | `controlled/clock-overrides/time_ao.dat` | `HIST/controlled/nanograv15yr-v2.1.0/clock/time_ao.dat` | 492,183 | `7e1755bb794d84bb7e585d556dcf46fffde159ea5d7f9543cd54e7fcb55bf86d` |
| `green-bank-observatory-clock` | `controlled/clock-overrides/time_gbt.dat` | `HIST/controlled/nanograv15yr-v2.1.0/clock/time_gbt.dat` | 400,170 | `060493be69cd421ce383a91631f089c22e8ed58fb322fdd9f1c4ed3ff2d2797b` |
| `de440-kernel` | `derived/cache-v0.2.8/ephemerides/de440.bsp` | `HIST/derived/cache/astropy/download/url/dabea460521989808aedfb52df4e07e4/contents` | 119,799,808 | `a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5` |
| `iers-leap-seconds` | `derived/cache-v0.2.8/iers/Leap_Second.dat` | `ENV/Leap_Second.dat` | 1,352 | `6cb6f5d4b819f2e568e25db4b0b26d89dedf031fdffb18bc94d40f4e94e268d7` |
| `iers-b-parser-readme` | `derived/cache-v0.2.8/iers/ReadMe.eopc04` | `ENV/ReadMe.eopc04` | 3,275 | `42d7890543fae69df024219d1d36f242b4fcd847f6f8a756c7d37c5dfd100243` |
| `iers-a-parser-readme` | `derived/cache-v0.2.8/iers/ReadMe.finals2000A` | `ENV/ReadMe.finals2000A` | 3,429 | `7c6182cc0fd0cbece39711f648d15e48b49168925602e360a5709c5ccc8d5a12` |
| `iers-b-eopc04` | `derived/cache-v0.2.8/iers/eopc04.1962-now` | `ENV/eopc04.1962-now` | 5,158,836 | `f04b166d36f9dde242d3aaae8349a53b8b0b69d287941dcbbfd05cadcb00c673` |
| `iers-a-finals2000a` | `derived/cache-v0.2.8/iers/finals2000A.all` | `ENV/finals2000A.all` | 3,756,992 | `f707ea5031a467f1a3b2f0645fac2f627095ed0cb41d34c515b495cb81a5a25d` |

The following metadata strings are also exact future intake and schema-1
manifest values:

| Logical name | `source_url_or_publication` | `license_or_redistribution_status` | `consumer` | `resolution_role` |
|---|---|---|---|---|
| `gps-to-utc-clock` | `IPTA pulsar-clock-corrections T2runtime/clock/gps2utc.clk` | `BSD-3-Clause IPTA byte; local project use` | `PINT 1.1.5` | `gps_clock` |
| `tai-to-tt-bipm2019-clock` | `NANOGrav 15-year v2.1.0 controlled clock; byte-identical to IPTA pulsar-clock-corrections T2runtime/clock/tai2tt_bipm2019.clk` | `BSD-3-Clause IPTA byte; local project use` | `PINT 1.1.5` | `bipm_clock` |
| `arecibo-observatory-clock` | `NANOGrav 15-year v2.1.0 controlled clock; byte-identical to IPTA pulsar-clock-corrections tempo/clock/time_ao.dat` | `BSD-3-Clause IPTA byte; local project use` | `PINT 1.1.5` | `observatory_clock` |
| `green-bank-observatory-clock` | `NANOGrav 15-year v2.1.0 controlled clock` | `Historical controlled input; local scientific use only; redistribution not asserted` | `PINT 1.1.5` | `observatory_clock` |
| `de440-kernel` | `NAIF/JPL DE440 planetary ephemeris kernel` | `Local scientific use only; external redistribution not asserted` | `PINT 1.1.5 / Astropy 8.0.1` | `solar_system_ephemeris` |
| `iers-leap-seconds` | `astropy-iers-data==0.2026.8.3.0.53.6 package data` | `BSD-3-Clause astropy-iers-data package content` | `Astropy 8.0.1 / ERFA` | `leap_seconds` |
| `iers-b-parser-readme` | `astropy-iers-data==0.2026.8.3.0.53.6 package data` | `BSD-3-Clause astropy-iers-data package content` | `Astropy 8.0.1 / PINT 1.1.5` | `iers_b` |
| `iers-a-parser-readme` | `astropy-iers-data==0.2026.8.3.0.53.6 package data` | `BSD-3-Clause astropy-iers-data package content` | `Astropy 8.0.1 / PINT 1.1.5` | `iers_a` |
| `iers-b-eopc04` | `astropy-iers-data==0.2026.8.3.0.53.6 package data` | `BSD-3-Clause astropy-iers-data package content` | `Astropy 8.0.1 / PINT 1.1.5` | `iers_b` |
| `iers-a-finals2000a` | `astropy-iers-data==0.2026.8.3.0.53.6 package data` | `BSD-3-Clause astropy-iers-data package content` | `Astropy 8.0.1 / PINT 1.1.5` | `iers_a` |

The five `ENV` files were reverified locally during R5 as regular files with
the exact sizes and hashes above. Their package metadata identifies
`astropy-iers-data==0.2026.8.3.0.53.6`; its installed BSD-3-Clause license file
has SHA-256
`05d8ec3643773431cb5447b10711f119d79955470cdfbb8ca2e670a4432a153c`.
The five `HIST` identities remain documented R2 evidence and were not reread in
this design-only stage.

The provenance publications remain:

- IPTA clock corrections: `https://github.com/ipta/pulsar-clock-corrections`
- NAIF/JPL planetary kernels: `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/`

No external byte was fetched during this amendment.

## 4. Exact closure and manifest rules

1. The two controlled roots remain exactly `controlled/clock-overrides` and
   `derived/cache-v0.2.8`.
2. The resource tree must contain exactly the ten regular files above, in no
   other location, with no symlink or unsupported filesystem object.
3. The exact seven required resource classes, in order, are
   `observatory_clock`, `gps_clock`, `bipm_clock`, `iers_a`, `iers_b`,
   `leap_seconds`, and `solar_system_ephemeris`.
4. A later `resource-intake.json` and Gate 4 authority must reproduce the table
   order and every logical name, path, metadata string, consumer, role, byte
   count, and hash exactly. Non-empty but different metadata is not acceptable.
5. The existing schema-1 resource-manifest format and the existing operator
   surface remain unchanged. The future `manifest_id` must be named by the
   separately approved Gate 4 authority and bound to the canonical successor
   path and data-root ID; R5 creates no manifest.
6. Source-before, destination, source-after, and restored-copy identities must
   agree exactly in the later provisioning receipt. A changed source stops
   before destination use.
7. No byte may be downloaded, synthesized, refreshed, normalized, or edited.

The following are rejected from the future closure: PINT `index.txt`, duplicate
global clock-cache copies, Astropy URL-cache paths or URL sidecars,
`ao2gps.clk`, `gbt2gps.clk`, package/cache fallback files, and every unlisted
extra file. They remain preserved historical or R2 candidate evidence; nothing
is deleted by this amendment.

## 5. Later single provisioning-attempt contract

A separately approved attempt must retain the exact successor identities from
Gate 4A-R1:

- destination: `${RECHERCHE_ARCHIVE_ROOT}/Pulsar-Timing-Pilot-v0.2.8-gate4`
- data-root ID: `pilot2-b1937-v028-gate4-root-01`
- generation: `Pulsar-Timing-Pilot-v0.2.8-gate4`
- schema-2 marker SHA-256:
  `cd8845c3c24e0930c27825f7902bfee510db404467b10cba7f0afdc63400f66c`
- evidence root: `. Gate4 Evidence/pilot2-gate4a-r2-root-provision-attempt-1/`
- temporary restore root: `/private/var/folders/kz/pc_8c86j76zgt8fntx54hf9w0000gn/T/pilot2-gate4a-r2-restore-attempt-1`

Before the first write, the later authority must bind a committed form of this
exact amendment, an exact clean repository commit/tree containing the accepted
implementation above, the historical marker, all ten source identities, the
three absent destination roots, and zero-network/zero-science policy. Any
mismatch stops before writes and terminally closes that authorized provisioning
attempt; no automatic retry follows.

Only after every entry check passes may the one create-once attempt:

1. create the exact successor and evidence roots;
2. write the exact schema-2 marker;
3. perform the already approved selective historical copy;
4. install only the ten intake resources above;
5. record source-before, destination, source-after, and restored-copy parity;
6. perform the one fresh temporary restore rehearsal; and
7. create exactly `gate4-authority.json`, `restore-boundary.json`,
   `successor-root-inventory.json`, and `resource-intake.json` in the evidence
   root.

It must then stop before the IOC `preflight` command. It may not create the
production resource/environment manifests or a freeze, construct the B1937+21
context, create a science run root, or execute science.

Any source change, path escape, unexpected file, provenance gap, copy/hash
mismatch, marker mismatch, network attempt, science counter, or write outside
the three exact roots terminally fails that attempt. There is no merge,
overwrite, cleanup-and-retry, fallback, resume, or reuse of a partial root.

## 6. Current versus required

| Item | Current R5 evidence | Required before Gate 4 | State |
|---|---|---|---|
| R2 HOLD | Preserved unchanged; attempt unconsumed | Preserve permanently | PASS |
| Direct resource binding | Exact committed R4 candidate; disposable acceptance PASS | Same bytes in clean authorized release | PASS for intake |
| Ten-resource intake | Exact paths, metadata, sizes, hashes, consumers, roles, and dispositions bound here | Source/destination/restore parity receipt | READY FOR PROVISIONING AUTHORITY |
| Five local IERS/package sources | Live read-only size/hash/license verification | Reverify before first write | PASS for intake |
| Five historical sources | Exact R2 documented identities; not reread in R5 | Reverify before first write | NOT STARTED |
| Successor/evidence/restore roots | Not accessed in R5 | Fresh and absent at entry | UNVERIFIED |
| Gate 4 context and manifests | Not run or created | Two zero-science passes and exact manifests | NOT STARTED |

The remaining blocker is no longer resource-binding design. It is the
separately authorized, one-shot provisioning and parity receipt.

## 7. R5 governance and stop

- new files created: `1` — this amendment only
- existing files changed: `0`
- source or test files changed: `0`
- tests, preflight, or context invocations: `0`
- `/Volumes` or historical-root accesses: `0`
- successor, evidence, or restore roots created: `0`
- resources copied, acquired, downloaded, or deleted: `0`
- production manifests or freezes created: `0`
- scientific cases, draws, fits, scans, or audits executed: `0`
- observed-data access: `0`
- commits, pushes, backups, or publications: `0`

This amendment reuses the accepted offline boundary and changes no harness,
operator command, manifest schema, context constructor, scientific path,
threshold, inventory, or interpretation. No design spiral occurred.

Current authority stops after validating and reporting this document's exact
SHA-256. Provisioning and every real-root action remain unauthorized.

## 8. Next bounded gate — commit this amendment only

After owner review, one clean-candidate commit stage may commit only this exact
amendment on top of
`f4c29328d7f3b6a6e8b036eb628c74e3cd31b1d6`, report the resulting commit and
tree, and stop with a clean worktree.

It may not edit the amendment, code, tests, or any existing document; run tests;
access `/Volumes`; create a successor, evidence, or restore root; provision a
resource; create a manifest or freeze; invoke preflight; or execute science.
The Gate 4A-R2 single provisioning attempt remains a later, separately approved
gate.
