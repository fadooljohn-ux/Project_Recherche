# Project Recherche: agent instructions

Read [AGENT_README.md](AGENT_README.md) for setup and operation. It applies to
Codex, Claude Code, Devin and other agents with shell/filesystem access.
Current release: v0.1.0. Current scientific state is summarized in README.md,
the canonical master workbook and docs/FUTURE_DATA_SOURCES.md.

- Follow the user's current scope. When preparation and execution are authorized,
  diagnose concrete errors, repair them locally and continue. Avoid unrelated
  redesign, repeated tests or new approval cycles for routine repairs.
- Use the pinned Intel macOS `.pixi` science environment and `tools/recherche`.
  Install/check this edition with `tools/agent_setup.py`. Native ARM Python and
  arbitrary dependency upgrades do not preserve the precision contract.
- Consult `outputs/recherche-master-20260908/Project-Recherche-Master.xlsx`
  before selecting observations. Completed run destinations are consumed.
  No scientific job is queued by cloning or installing this release.
- Preserve formal failures, qualification evidence, original result hashes,
  record IDs and operator notes. Separate development, calibration, observed
  execution and scientific interpretation. Never substitute simulations for data.
- Update the master after each concluded run, including stopped/failed attempts.
  If registration fails, repair bookkeeping alone. Do not rerun science.
- Review compelling candidates using docs/CANDIDATE_DEEP_REVIEW.md and grade
  significance, robustness and independent confirmation separately.
- For long healthy runs, use sparse monitoring (normally 30 minutes) and notify
  on completion, failure or meaningful changes. Stop monitoring completed work.
- Keep raw inputs, credentials and local absolute paths outside published files.
  Use repository-relative references or documented environment variables.
- Read docs/PUBLICATION_PROVENANCE.md before interpreting historical hashes.
  Redacted receipts are archival derivatives, not executable frozen bindings.
  Check publication integrity with `python3 tools/check_publication.py`.
- Do not contact data owners, publish new material, change repository visibility,
  or modify unrelated projects without the user's applicable authorization.

The original chronological operating history is preserved in a separate private
archive. The release docs retain scientific closeouts, including limitations;
historical private-status statements describe their original reporting dates.
