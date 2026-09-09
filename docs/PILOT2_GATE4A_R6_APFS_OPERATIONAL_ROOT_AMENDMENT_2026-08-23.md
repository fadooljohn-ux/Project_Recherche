# Pilot 2 Gate 4A-R6 APFS operational-root amendment

Date: 2026-08-23

Status: **AMENDMENT COMPLETE — commit, provisioning, preflight, and science remain unauthorized**

## 1. Decision

Remove WARMASTER from the active Pilot 2 runtime. Use one dedicated APFS
operational data root outside the Git repository. WARMASTER may be mounted only
as a temporary, read-only source for exact scientific inputs during a separately
authorized provisioning attempt, then must be unmounted before Gate 4 preflight.

This is a prospective destination and intake amendment. It changes no harness,
science module, operator command, scientific control, threshold, case inventory,
resource-binding implementation, or interpretation rule.

## 2. Preserved terminal and historical evidence

Gate 4A-R2 provisioning attempt 1 is terminal and consumed. Its state remains:

- terminal successor root:
  `${RECHERCHE_ARCHIVE_ROOT}/Pulsar-Timing-Pilot-v0.2.8-gate4`
- observed successor contents: 10 directories and 36 regular files;
- intended contents present with exact hashes: 13 files, comprising the schema-2
  marker, two B1937+21 inputs, and ten R5 resources;
- forbidden EXFAT/macOS AppleDouble contents: 23 `._*` files;
- terminal evidence root:
  `. Gate4 Evidence/pilot2-gate4a-r2-root-provision-attempt-1`
  exists and is empty;
- attempt-1 temporary restore root: absent;
- attempt-1 evidence files published: 0 of 4;
- network connections and downloaded bytes: 0, enforced by the fixed
  `/usr/bin/sandbox-exec` denial profile;
- IOC preflight, context constructions, production manifests, freezes, and
  science: 0.

The failure layer is **OPERATIONAL filesystem compatibility**, not harness,
validation, or science. Attempt 1 may not be deleted, repaired, completed,
regraded, reused, or presented as a successful restore or authority package.

No canonical per-path terminal inventory or evidence payload was published
before attempt 1 failed. This amendment is the authoritative preservation
receipt for the aggregate terminal state observed above; the next commit-only
gate will bind that receipt to its exact document hash, commit, and tree. It
does not invent a missing terminal inventory or receipt hash. That absence is
part of the terminal deficiency and can never be backfilled as attempt-1
evidence.

The R2 and R5 statements that the provisioning attempt was unconsumed remain
true historical statements as of those documents. The later attempt-1 terminal
event supersedes only their prospective unconsumed status; their bytes and all
other historical findings remain unchanged.

The following also remain immutable historical evidence and retain every
WARMASTER path they recorded:

- the historical v0.2.1 root and schema-1 marker;
- all v0.2.1, v0.2.2, and v0.2.7 terminal records and freezes;
- Gate 4A-R1, the R2 HOLD, R3, and R5;
- `protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.7.json`; and
- `results/pilot2/injection_v027_startup_failure_audit.json`.

This amendment does not rewrite history to remove WARMASTER. It removes
WARMASTER only from the prospective operational path.

## 3. Bound repository and governing identities

- repository branch: `agent/pilot2-v028-design`
- repository commit: `385d824b529643fff4d3ce473ba74eee366981d0`
- repository tree: `3f109b5015c56cc351ae4d3e9a8b4aed0a8433a6`
- operational IOC plan SHA-256:
  `e1a1d97cfeb3482bb413feee53ce7d2426ff7f9542b2f51cb271ad0b8bd19ec9`
- Gate 4A-R1 SHA-256:
  `835e1c955b4c238d97ef1a77dfffff0b1ac855dcb11cd0f4ceb29a8a17de9fa5`
- Gate 4A-R2 HOLD SHA-256:
  `bb41d3d1267010ef9fac0546d83b94f19df22c39b11d8ec1f6e955714e29c89c`
- Gate 4A-R3 SHA-256:
  `7df99e1bcf4d537eb5522e29b9689ed1b44fe98784dba0c6004f1f229a4038f4`
- Gate 4A-R5 SHA-256:
  `bf187853c5fa011329bb0ff4ead3667fc63fd240bc72ccaa78d76ff8737cdc4b`

The internal operational filesystem was observed as APFS with
`393526251520` available bytes. The existing v0.2.8 complete-data-root cap is
1.5 GiB. This storage observation is readiness evidence only and must be
remeasured before provisioning and preflight.

## 4. Exact prospective APFS identity

- canonical operational root:
  `../Project Recherche Data/Pulsar-Timing-Pilot-v0.2.8-gate4-apfs`
- data-root ID: `pilot2-b1937-v028-gate4-apfs-root-01`
- generation: `Pulsar-Timing-Pilot-v0.2.8-gate4-apfs`
- project: `project-recherche-pulsar-pilot`
- schema version: `2`
- exact sorted, indented marker byte count: `188`
- intended marker SHA-256:
  `c814ff28bb07b80c9a9d616a4d79bd45bd2b857984d0e924ac5a23853042486b`

The canonical root is a sibling of, not an ancestor or descendant of, the Git
repository. It remains compatible with the existing `configured_data_root()`,
IOC authority, science-module, and release-contract path checks. No source-code
change is required for relocation.

The new attempt-2 evidence and restore boundaries are:

- evidence root:
  `. Gate4 Evidence/pilot2-gate4a-r6-apfs-root-provision-attempt-2`
- temporary restore root:
  `/private/var/folders/kz/pc_8c86j76zgt8fntx54hf9w0000gn/T/pilot2-gate4a-r6-apfs-restore-attempt-2`
- restored data-root ID:
  `pilot2-b1937-v028-gate4-apfs-restore-attempt-2`

All three roots must be absent at the future attempt-2 entry check. None was
accessed or created by this design amendment.

## 5. WARMASTER role after this amendment

WARMASTER has exactly two permitted prospective roles:

1. `temporary_read_only_source` for the 12 exact HIST files incorporated into
   the attempt-2 intake below; and
2. passive, preserved storage for historical and terminal evidence, including
   attempt 1.

Passive preservation permits no new evidence write to WARMASTER. Every new
attempt-2 receipt must be written only to the APFS evidence root in Section 4.

WARMASTER is prohibited as:

- the operational data root or a runtime fallback;
- an IOC authority, manifest, setup-log, restore, run, ledger, result, or
  evidence destination;
- a PINT, Astropy, clock, IERS, DE440, predecessor, or context-open path after
  intake;
- a source accessed during Gate 4 preflight, Gate 5 freeze/audit, Gate 6
  qualification, Gate 7 IOC declaration, or Gate 8 science.

After source-after identity verification, WARMASTER must be unmounted. The
operator must record its absence immediately before invoking the existing IOC
`preflight` command, and it must remain unmounted through the operational run.
No new mount manager, daemon, wrapper command, or controller is authorized.

## 6. Exact 21-input operational closure

The future APFS root must contain exactly 21 admitted input files plus its
separately created schema-2 marker at provisioning closeout. The 21 inputs are
two B1937+21 controlled inputs, ten R5 offline resources, and nine immutable
predecessor records.

### 6.1 Two B1937+21 controlled inputs

`HIST` remains the historical v0.2.1 root on WARMASTER. These two files are
copied to the same relative paths under the APFS root:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `controlled/nanograv15yr-v2.1.0/wideband/par/B1937+21_PINT_20230131.wb.par` | 44,433 | `1791d09c03bce63381018035ffcd0052406e1f3394aa119b5f469eff99b5a083` |
| `controlled/nanograv15yr-v2.1.0/wideband/tim/B1937+21_PINT_20230131.wb.tim` | 360,761 | `4dde72540e60e1950b284360cf6517e75ddad5a79564b2cab683f9c974d7901d` |

### 6.2 Ten direct-bound offline resources

The complete ten-row resource table, metadata, sources, destinations, sizes,
hashes, consumers, roles, controlled roots, seven required classes, and
rejections in Gate 4A-R5 Sections 3 and 4 are incorporated unchanged by exact
document hash. Only the destination prefix changes from the terminal WARMASTER
successor to the APFS root in Section 4 above.

Source distribution remains:

- five exact read-only HIST files from WARMASTER;
- five exact ENV files from the pinned `astropy-iers-data` package; and
- zero downloads, substitutions, refreshes, normalization, or synthesis.

### 6.3 Nine immutable predecessor records

The current v0.2.8 executor resolves these records beneath `data_root`. Omitting
them would allow Gate 4 context qualification but would make later science fail
at `verify_predecessors()`. They therefore belong in the operational closure;
this corrects an intake omission without changing executor code or scientific
controls. They are predecessor/inventory closure, not additional R5 resource
rows: the resource manifest remains exactly the ten rows in Section 6.2.

The five historical records are read from HIST and copied to their same
relative paths. For every row, the exact physical source is
`HIST/<Relative path>` and the exact destination is
`<APFS operational root>/<Relative path>`; no alternate source is admitted:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `run_records/pilot2/calibration-threshold-lock-v0.2.1.json` | 652 | `6e624af784aabd92ce8b28babdaed4c863ca12c94caad756da005f14bf9b5117` |
| `run_records/pilot2/sealed-gaussian-evaluation-v0.2.1.json` | 1,253 | `f3a8677ea28255c7c06afd815fad1d911fcadde9a1fb0a4b2bf464f78aa59034` |
| `run_records/pilot2/structured-tail-evaluation-v0.2.1.json` | 2,439 | `540f5d12496a02687253b3d0a64e63208c8df53d8cdae3f3935cc8da4fc0f252` |
| `run_records/pilot2/injection-evaluation-v0.2.1.json` | 389,085 | `06cf10aa00231ecac05abccbe491b21c074371d749f8cc88dccff8cf034fba8c` |
| `run_records/pilot2/calibration-v0.2.1-ledger.json` | 3,470,620 | `cb13ffc749cd4bec1ab41dfcfe056850507d52546c9425e2b4fbfff49c1bc621` |

The four repository records are copied from the clean committed repository to
their same relative paths under the APFS root:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.2.json` | 3,214 | `9e247d3d3c2eba0edc936b2db778683257ae5888c1bd581f682dc074ba768d03` |
| `results/pilot2/injection_v022_crash_audit.json` | 2,702 | `6d58ef1be4a03969be41ee3e0d916adaa252ee5bfa42d7c23244f203f878b473` |
| `protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.7.json` | 6,080 | `8c45fe999b0c871d0cc383d47829aa175863a08d25bf00afef29f043f5dba5f8` |
| `results/pilot2/injection_v027_startup_failure_audit.json` | 2,407 | `c9d00f3c021091c18722d1a288c91e218f447ce1f9ac3f507dda0b9fdc70ab9d` |

Before the first attempt-2 write, all 21 sources must be regular files with
exact byte counts and hashes. Each requires source-before, destination,
source-after, and restored-copy parity. A missing or changed source stops before
writes and terminally closes attempt 2.

## 7. Attempt-2 create-once and evidence rules

The future one-shot provisioning authority must bind, before its first write:

- a clean committed form of this exact amendment;
- the new APFS path, data-root ID, generation, and marker bytes;
- all 21 exact source identities and their source class: HIST, ENV, or REPO;
- absence of the APFS successor, attempt-2 evidence, and attempt-2 restore roots;
- the terminal non-reuse of attempt 1;
- the fixed network-denial identity and zero-network/zero-science policy; and
- exact expected bytes for all four evidence files.

The future R7 stage statement and immutable one-shot attempt program must freeze
those four canonical JSON payloads before the first filesystem write. In
particular, `gate4-authority.json` must contain fixed `created_at` and
`expires_at` values, and its restore-receipt hash must name the exact
predeclared `restore-boundary.json` bytes. The two manifest hashes in that
restore receipt are derived deterministically from the predeclared 22-file
inventory, so there is no circular evidence dependency.

Outcome fields in the four predeclared payloads are expected values, not
pre-awarded results. After each check, the attempt program must construct the
observed payload in memory, require byte-for-byte equality with the frozen
payload, and only then publish those exact bytes create-once. It may not
generate a timestamp, hash, ordering, or other evidence field after the first
write. A mismatch terminally fails attempt 2 without publishing a false PASS.

The provisioning program must explicitly recompute the content-addressed
intake binding because the current harness validator checks only the Gate 4
qualification-ID prefix. The existing harness schema is not expanded.

Only after every entry check passes may attempt 2:

1. create the exact APFS successor and attempt-2 evidence roots;
2. write the exact schema-2 marker;
3. copy only the 21 input files above;
4. require an exact 22-file provisioning inventory with no extra file,
   AppleDouble sidecar, symlink, fallback, or unsupported object;
5. verify every source-after identity;
6. unmount WARMASTER and record that it is absent;
7. perform one fresh filesystem-only restore into the exact attempt-2 temporary
   root and require full 22-file parity; and
8. write exactly `gate4-authority.json`, `restore-boundary.json`,
   `successor-root-inventory.json`, and `resource-intake.json` to the evidence
   root, byte-identical to the predeclared payloads.

Attempt 2 must then stop before IOC `preflight`. It may not create production
resource/environment manifests, context setup logs, a freeze, a science run
root, or any scientific artifact.

Any entry mismatch, source change, path escape, unexpected object, copy/hash
mismatch, failed unmount/absence check, restore mismatch, network attempt,
science counter, or write outside the three exact attempt-2 roots terminally
fails attempt 2. There is no merge, cleanup-and-retry, fallback, resume, or
reuse.

## 8. Amendment ledger and no-spiral check

| Type | Prospective change | Historical state preserved |
|---|---|---|
| `REPLACE` | WARMASTER successor destination becomes the exact APFS root | R1/R5 and failed attempt-1 paths remain unchanged |
| `REPLACE` | New APFS root ID, generation, marker, evidence, and restore identities | Attempt-1 identity remains terminal and consumed |
| `NARROW` | WARMASTER becomes temporary read-only source only | Historical and terminal evidence remains stored there |
| `ADD` | Nine already-configured predecessor records join the operational intake | Their original files, hashes, and scientific meaning remain unchanged |
| `CLARIFY` | WARMASTER must be unmounted before preflight and operation | Prior uses remain historical truth |

No design spiral occurred. This amendment removes an operational dependency
and supplies files already required by the accepted v0.2.8 config. It adds no
command, harness, runner, observer, service, broker, scheduler, retry path,
resolver, science calculation, case, threshold, or interpretation.

Subagent governance remains: Luna unrestricted, Terra requires explicit owner
authorization, and Sol is prohibited.

## 9. Current authority and stop

This gate creates only this amendment. It authorizes:

- repository and governing-document reads;
- read-only inspection of current code/config and committed predecessor files;
- APFS filesystem-type and free-space observation; and
- creation and read-only review of this one document.

It authorizes no WARMASTER or other science-root access, deletion or cleanup of
attempt 1, source/test/config edit, test or command execution, root creation,
copy, unmount, provisioning, evidence package, preflight, manifest, freeze,
commit, push, backup, or science.

Stop after reporting this document's exact SHA-256 and the one-file worktree
state.

## 10. Next bounded gate — commit this amendment only

After owner review, one commit-only gate may commit this exact amendment as the
sole payload, report its commit and tree, and stop with a clean worktree.

It may not edit this document or any other file; access WARMASTER or a science
root; run tests; create the APFS, evidence, or restore roots; copy data;
provision; invoke preflight; create manifests or freezes; or execute science.

Only after that clean commit may the owner separately authorize the Gate 4A-R7
single APFS provisioning attempt 2 defined in Section 7.
