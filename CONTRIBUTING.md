# Contributing to Project Recherche

Contributions should improve reliable operation, reproducibility or supported
data ingestion. Keep changes focused and maintainable. Start with
[AGENT_README.md](AGENT_README.md) for the runtime and operating procedure.

## Set up

Use macOS with Pixi and Rosetta on Apple Silicon:

```sh
python3 tools/agent_setup.py --install
python3 tools/agent_setup.py --check
```

The scientific environment is locked to Intel macOS Python 3.11. Keep workbook
dependencies separate. Do not update dependency locks as a side effect of a fix.

## Report an issue or propose a change

Include the release/commit, relevant command, expected and actual behavior,
runtime details, and a minimal reproducible example. For data-dependent errors,
identify the upstream release, target, input hashes and timing/noise conventions.
Remove credentials, personal paths and identifying machine details from logs.
Use GitHub's no-reply commit address if you do not want to publish your email.

Open a focused pull request explaining the problem, resulting behavior and
checks actually run. For a bug, reproduce the specific failure and verify the
repair. Documentation changes need link/content checks; bookkeeping changes
use temporary workbook copies. Do not launch a survey or repeat historical
qualification just to validate an unrelated edit.

## Preserve scientific evidence

- Keep completed results, failed attempts, IDs, input hashes and operator notes.
  Use new output IDs for new work; repair workbook updates without rerunning science.
- Consult the master before selecting observations and update it after every
  completed, stopped or failed run. Record dataset overlap and exclusions.
- Label observed searches, model-assisted recovery and simulations separately.
  A threshold crossing is a candidate; apply the documented deep review and
  three-measure grading before making stronger claims.
- Explain which prior evidence a solver, noise-model or runtime change affects.
  The release's hash manifest is an integrity record, not a transferable
  scientific qualification.
- Keep large/raw observations and credentials outside Git. Cite their original
  releases, verify redistribution terms, and provide acquisition instructions.

Historical files in this release are publication derivatives where paths were
redacted. Read [publication provenance](docs/PUBLICATION_PROVENANCE.md) before
using their hashes. Future release manifests must be regenerated for intentional
changes; never rewrite original scientific hashes to hide a mismatch.

Contributions are distributed under the repository's [MIT license](LICENSE).
Use [CITATION.cff](CITATION.cff) when citing this software and cite the original
observational data separately.
