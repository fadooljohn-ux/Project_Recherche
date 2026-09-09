# Pilot 2 Gate 4A-R1 successor-root decision

Date: 2026-08-16

Status: **DESIGN COMPLETE — successor-root creation remains unauthorized**

## 1. Decision

Do not modify the historical v0.2.1 science root. Create one forward-only
successor root for Gate 4 after separate approval.

The successor will use the existing IOC harness and science-module path. This
decision adds no runner, observer, service, broker, retry path, or control
plane.

## 2. Bound baseline and preserved evidence

- repository commit: `937328c33f5b6ec4a0223e06e838cc68468447d9`
- repository tree: `883c09b81493955b9d2053e18990f4c4ccbe857c`
- operational plan SHA-256:
  `e1a1d97cfeb3482bb413feee53ce7d2426ff7f9542b2f51cb271ad0b8bd19ec9`
- Gate 4-R1 design SHA-256:
  `c05c851b23fadf30b603741f63eb63ed8e4b7568dccdd25509ac05e1be29fab9`
- historical root:
  `${RECHERCHE_ARCHIVE_ROOT}/Pulsar-Timing-Pilot-v0.2.1`
- historical marker SHA-256:
  `b71e614da3507e517c1f53b73dd527ce87e5d0cfe1392cd27ec3fff13c3dd5dd`

The historical marker is schema 1 and has no stable root ID or generation.
That root and marker remain immutable evidence. They will not be upgraded,
replaced, cleaned, or repaired in place.

## 3. Exact successor identity

- canonical destination:
  `${RECHERCHE_ARCHIVE_ROOT}/Pulsar-Timing-Pilot-v0.2.8-gate4`
- data-root ID: `pilot2-b1937-v028-gate4-root-01`
- generation: `Pulsar-Timing-Pilot-v0.2.8-gate4`
- project: `project-recherche-pulsar-pilot`
- schema version: `2`

The marker will be written with the existing durable sorted, indented JSON
format. Its intended SHA-256 is:

`cd8845c3c24e0930c27825f7902bfee510db404467b10cba7f0afdc63400f66c`

The destination must not exist before its single provisioning attempt. A
partial or failed destination is terminal and may not be repaired or reused.

## 4. Copy and resource contract

The successor is a verified selective copy, not an edited historical root.
Every copied regular file must retain its bytes and SHA-256. The provenance
inventory must record source-before, destination, and source-after identities.
The historical schema-1 `.project-recherche-data-root.json` is explicitly
excluded from the copy set and is never overwritten. The successor schema-2
marker is created separately at the destination.

Reject rather than copy:

- symlinks, devices, sockets, and unsupported filesystem objects;
- AppleDouble `._*` files, `.DS_Store`, and unrecognized sidecars; and
- any path not present in the create-once copy specification.

The new local resource closure uses exactly these two roots:

- local repository and XDG cache: `derived/cache-v0.2.8`
- controlled clock override: `controlled/clock-overrides`

The first candidate resource set is the frozen v0.2.8 design set:

- PINT global clock index `index.txt`;
- the Arecibo and Green Bank observatory clock files required by B1937+21;
- `time_ao.dat`, `gps2utc.clk`, and `tai2tt_bipm2019.clk`;
- the DE440 ephemeris kernel; and
- the exact IERS tables used by the pinned environment.

No byte may be invented or downloaded. Each candidate must already exist in a
local trusted source and receive a finite intake record containing logical
name, destination path, provenance or publication, license status, size,
SHA-256, consumer, and resolution role. Missing provenance or a missing local
file stops provisioning.

The two resource roots must contain only the finite intake set. Any extra file,
sidecar, symlink, cache fallback, or unlisted resource is a failure. Gate 4
later remains responsible for proving that the real resource-open trace equals
this allowlist exactly.

The environment binding is intentionally small:

- critical modules: `astropy`, `numpy`, `pint`, and `scipy`;
- inherited environment allowlist: empty;
- package and module hashes: measured from the bound Pixi environment, never
  guessed.

## 5. Next bounded stage — Gate 4A-R2

After separate approval, one provisioning attempt may:

1. resolve the candidate resource categories into an exact finite intake table
   before any destination write;
2. create only the exact successor root above;
3. write its exact schema-2 marker;
4. copy the finite approved historical inputs without changing source bytes;
5. install only locally available, provenance-complete offline resources;
6. create one canonical historical-source, successor, and restored-copy
   inventory and require direct hash parity;
7. perform one isolated system-temporary restore rehearsal;
8. create the exact evidence package below; and
9. stop before the IOC `preflight` command.

The single restore rehearsal may write only to the fresh, absent canonical
temporary root
`/private/var/folders/kz/pc_8c86j76zgt8fntx54hf9w0000gn/T/pilot2-gate4a-r2-restore-attempt-1`
(the canonical form of the current Darwin user-temporary root reported as
`/var/folders/kz/pc_8c86j76zgt8fntx54hf9w0000gn/T/`). It is the sole
disposable write boundary outside the successor and evidence roots.

The evidence package root is exactly
`. Gate4 Evidence/pilot2-gate4a-r2-root-provision-attempt-1/`
and contains exactly these four files:

- `gate4-authority.json`
- `restore-boundary.json`
- `successor-root-inventory.json`
- `resource-intake.json`

`successor-root-inventory.json` contains the exact temporary boundary plus the
canonical historical-source, successor, and restored-copy inventories and
their direct parity results. `restore-boundary.json` retains the existing exact
seven-key `pilot2-ioc-gate4-restore-boundary-v1` schema: schema, status, source
and restored data-root IDs, equal source and restored manifest SHA-256 values,
and `science_executed: false`. No harness schema change is authorized.

The Trammel practice adopted here is limited to direct canonical inventory
parity, a fresh destination, create-once evidence, and fail-closed refusal. No
Trammel controller or backup subsystem is imported.

Gate 4A-R2 fails terminally on any source change, copy mismatch, marker
mismatch, missing resource, provenance gap, unexpected file, path escape, or
write outside the exact successor, evidence, and one temporary restore roots.
There is no merge, overwrite, cleanup-and-retry, or reuse of a failed
destination.

## 6. Current authority and stop

The owner's `Proceed` authorizes this document only. It authorizes no successor
root or evidence-directory creation, marker write, copy, sidecar deletion,
resource acquisition, test, context construction, preflight, production
manifest, freeze, commit, push, or science.

Stop after reporting this document's exact SHA-256. Gate 4A-R2 and every later
gate require separate approval.
