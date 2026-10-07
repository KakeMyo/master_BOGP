# Codex project guidance

## Project

This repository is a research workspace for Bayesian-optimization-controlled
genetic programming. Preserve research drafts, source references, and result
artifacts unless the user explicitly asks to remove or replace them.

## Python environment

- Use the repository-local `.venv`; never commit it.
- Install development dependencies with
  `python -m pip install -e ".[dev]"` from an activated virtual environment,
  or invoke that environment's Python executable directly.
- The package requires Python 3.9 or newer as declared in `pyproject.toml`.

## Verification

- Run focused tests for the code being changed.
- For a full check, run `python -m pytest -q` from the repository root.
- Report tests that could not run, including missing optional system tools such
  as a TeX distribution.

## Repository hygiene

- Do not commit credentials, `.env` files, virtual environments, caches,
  temporary Office files, or generated LaTeX intermediates.
- `outputs/`, `results/`, and `slides/` are intentionally local/generated.
  Confirm with the user before changing this policy or committing generated
  artifacts from those directories.
- Treat PDFs, presentations, spreadsheets, and reference material outside the
  ignored directories as intentional research inputs unless told otherwise.
- Before committing a file near GitHub's per-file size limit, check its size and
  discuss Git LFS rather than adding it silently.

## Git workflow

- Pull the current branch before starting work on a second computer.
- Keep unrelated work on separate branches; use the `codex/` prefix for new
  Codex-created branches.
- Do not overwrite, discard, rebase, or commit unrelated user changes.
- At handoff, summarize the branch, commit, pushed state, and any remaining
  uncommitted or ignored files.
