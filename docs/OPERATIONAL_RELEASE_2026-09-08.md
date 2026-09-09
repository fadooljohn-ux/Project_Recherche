# Operational release, 2026-09-08

Owner authorization: “Proceed with stage 6”.

**Status: stage 6 complete; local operational acceptance PASS.**

Stage 6 packages the qualified application for this Mac at
`.`.
The qualification 02 scientific source remains unchanged: all 71 Python files
match the qualification readiness inventory. All eight receipt-bound terminal
artifacts from qualification 01 and qualification 02 remain unchanged.

## Operator surface

- `tools/install`: install only locked dependencies and run environment verification.
- `tools/recherche doctor [--data-root PATH]`: verify the qualified implementation,
  Python, package closure, precision and optional admitted inputs/resources.
- `tools/recherche init-data --from-data-root SOURCE --data-root NEW`: initialize
  a separate working root, including the development launch receipt.
- `tools/recherche backup --data-root PATH --output NEW.tar`: back up inactive data
  with exact inventory, content and source-after verification.
- Existing `develop`, `status` and formal conductor commands remain unchanged.

[The operator guide](OPERATOR_GUIDE.md) gives installation, launch, status, stop,
result retrieval, backup, restore and maintenance commands. Routine development
inputs are at `../Project Recherche Data/operational-20260908/`; formal roots
remain historical evidence. Monitoring is paused because no long run is active.

## Acceptance evidence

A fresh locked installation at the canonical prefix passed with OS network
access denied: 134 packages, exact Python executable hash, 63-bit long-double
mantissa, 21 inputs and 10 resources. It used the existing package cache without
manual repair. The runtime archive additionally supports cache-free offline
restore at the canonical prefix. An actual archive restore matched all 16,815
files and links and passed the same environment/input checks.

Input restore and fresh input initialization passed. Direct fault checks rejected
an altered input and an active-run backup. The first operator launch exposed a
missing provisioning receipt in the new setup command; that command was repaired
and a fresh launch completed. No scientific source changes were required.

The single ordinary development fixture on the reconstructed environment and
restored inputs completed in 188.521 seconds: one case, two primary fits, one
solver audit, one draw and one scan. All fits converged and the audit passed.
All 11 terminal artifacts matched their inventories. This installation check
is development evidence; the existing 21/21 formal qualification remains the
scientific acceptance evidence. No formal rerun or observed search was performed.

## Restore limitation and maintenance

The initial temporary-prefix install correctly failed the frozen Python hash.
The only binary difference was Python's embedded installation prefix and padding;
the Conda package identity was unchanged. This release therefore supports its
canonical checkout path and qualified macOS host. The installer detects other
paths before installing. The guide documents this limitation explicitly.

A different path, host or OS version needs an updated environment binding and
bounded compatibility assessment. Scientific identity checks were not weakened.
The qualified environment was preserved before replacement in
`../Recherche Recovery/20260907T223404/stage6-original-environment/`.

Compact acceptance receipt: `results/qualification/stage6-operational-verification.json`.

The local release package is `../Recherche Releases/operational-20260908/`:
source/history bundle, Intel runtime archive, Pixi executable, admitted inputs,
operator guide, checksums and verification receipts. Keep it as the recovery
baseline. Backup completed workloads to a new filename; never overwrite terminal
attempts. Dependency or scientific code changes require targeted verification
before a new release. Operator-only documentation does not require qualification.

Stage 6 completes the authorized rehabilitation roadmap for the qualified local
synthetic workflow. Observed-data searches remain outside the authorization.
