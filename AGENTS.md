# Project Recherche: agent instructions

Read [AGENT_README.md](AGENT_README.md) for setup and operation. It applies to
any agent with shell and filesystem access. Current edition: v0.2.0
(21 November 2026). The scientific state is summarized in README.md, the
master workbook and the dated reports in docs/.

- Follow the user's current scope. A clone, install, release or documentation
  update authorizes no scientific workload, download or data request.
- Use the pinned Intel macOS `.pixi` science environment and `tools/recherche`.
  Install and check with `tools/agent_setup.py`. Native ARM Python and
  dependency upgrades do not preserve the precision contract.
- Consult `outputs/recherche-master-20260908/Project-Recherche-Master.xlsx`
  before selecting observations. Every completed `run01` destination is
  consumed: never rerun a consumed search. Roots named `*-dev*` are
  development roots and must not be calibrated, frozen or run.
- Fix thresholds, period ranges and noise models before any observed scan.
  One frozen search per target and destination. A target that fails a check
  is held with its reason; never loosen a check to clear a hold. A hold is
  not a non-detection.
- A fixed-noise threshold crossing is a trigger, not a candidate. Run it once
  through the second-stage joint-noise test, with the noise grid and null
  generators declared beforehand, before grading it
  (docs/CANDIDATE_GRADING.md). Grade significance, robustness and independent
  confirmation separately.
- For tempo2-format binary models, use `tools/orbit_translate.py` through
  `tools/pta_binary.py`, and compare any new preparation with tempo2
  (`tools/tempo2_compare.py`) before proposing a search. A released model with
  a term the timing library does not implement is held.
- Preserve formal failures, qualification evidence, result hashes, record IDs
  and operator notes. Keep development, calibration, observed execution and
  interpretation separate. Never substitute simulations for data.
- Update the master workbook after each concluded run, including stopped or
  failed attempts. If registration fails, repair bookkeeping alone; do not
  rerun science.
- Keep raw inputs, credentials and local absolute paths out of published
  files. Use repository-relative references or documented environment
  variables.
- GitHub Actions in this repository are manual (`workflow_dispatch`) only. Do
  not add push, pull-request or scheduled triggers.
- Read docs/PUBLICATION_PROVENANCE.md before interpreting historical hashes.
  Redacted receipts are archival derivatives, not executable frozen bindings.
  Check publication integrity with `python3 tools/check_publication.py`.
- Do not contact data owners, publish new material, change repository
  visibility or modify unrelated projects without the user's authorization.

The chronological owner-instruction log is kept in a separate private archive.
The dated reports in docs/ retain the scientific closeouts and their limits;
statements in them about private status, pending approvals or "not yet
searched" describe their own reporting dates.
