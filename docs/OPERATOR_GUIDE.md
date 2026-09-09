# Operator guide

Use [AGENT_README.md](../AGENT_README.md) for the complete source-specific workflow.
This guide covers the v0.1.0 publication edition.

## Install and check

```sh
git clone https://github.com/fadooljohn-ux/Project_Recherche.git
cd Project_Recherche
python3 tools/agent_setup.py --install
python3 tools/agent_setup.py --check
python3 tools/check_publication.py
tools/recherche calibration --help
```

Use macOS with Pixi, Rosetta on Apple Silicon, and Python 3 for bootstrap.
The locked scientific interpreter is Intel Python 3.11 with 63 long-double
mantissa bits. `tools/install` is a convenience alias for the bootstrap.
No raw timing observations or installed runtimes are supplied in Git.

## Paths and evidence

Choose your own checkout and data directories. For example, from the checkout:

```sh
export RECHERCHE_DATA_ROOT="$(pwd)/../Project Recherche Data"
mkdir -p "$RECHERCHE_DATA_ROOT"
```

Pass explicit `--data`, `--cache` and other input paths to each adapter as
described in the agent guide; the variable above is a shell convenience, not
a universal override for every historical recipe. Obtain inputs from the pinned
upstream releases, verify their hashes and prepare a new dataset/run ID.

Historical manifests and logs use logical repository/sibling paths and `${HOME}`
where host-specific paths were removed. These strings describe locations; they
are not automatically expanded by JSON readers. Restore/reacquire the required
inputs and create new runtime bindings instead of replaying redacted freezes.

Original qualification and failed attempts remain historical evidence for the
original installation. This edition's hash map verifies distributed source bytes;
it does not transfer host qualification. `tools/recherche doctor` retains the
legacy installation checks and is not the fresh-clone acceptance command.
See [publication provenance](PUBLICATION_PROVENANCE.md).

## Operate and close out

Consult the master and source queue, define the authorized selection and model,
prepare and calibrate, then freeze and execute only that selection. Use distinct
output IDs; never overwrite a completed search. Register every terminal outcome
in the canonical workbook. Repair failed workbook updates from saved results.
Keep large inputs and archives outside Git and use sparse monitoring for long jobs.
