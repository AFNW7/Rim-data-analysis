# Repository Guidelines

## Project Structure & Module Organization
This repository is currently an empty workspace. Keep the root limited to project metadata such as `README.md`, `AGENTS.md`, and language manifests. Put source code in `src/`, tests in `tests/`, reusable assets in `assets/`, and helper automation in `scripts/`. As the project grows, organize modules by feature area, for example `src/ingest/`, `src/analysis/`, and `src/reporting/`.

## Build, Test, and Development Commands
No build system is committed yet, so new tooling should expose standard repo-local entry points. Preferred examples are `npm run build`, `pytest`, `ruff check .`, or `python -m build`, depending on the chosen stack. Keep commands runnable from the repository root and document them in both the manifest and `README.md`. Avoid workflows that depend on globally installed, machine-specific tools.

## Coding Style & Naming Conventions
Use UTF-8 text files and consistent LF line endings. Prefer 4 spaces for Python and 2 spaces for JSON, YAML, and Markdown. Use `snake_case` for Python modules and functions, `PascalCase` for classes, and `kebab-case` for script filenames. Choose descriptive folder names over abbreviations, and add formatter or linter configuration with the first language runtime you introduce.

## Testing Guidelines
Mirror the source layout inside `tests/`; for example, `src/analysis/stats.py` should have tests such as `tests/analysis/test_stats.py`. Add at least one normal-case and one failure-case test for each new feature. Keep unit tests fast, place heavier integration coverage under `tests/integration/`, and target at least 80% line coverage once coverage tooling is in place.

## Commit & Pull Request Guidelines
This workspace has no Git history yet, so establish a consistent convention now: `feat: add CSV loader`, `fix: handle empty input`, `docs: update contributor guide`. Keep commit subjects under 72 characters and scoped to one change. Pull requests should include a short description, linked issue if applicable, the commands used for verification, and screenshots or sample output when changes affect reports or visualizations.

## Security & Configuration Tips
Do not commit raw datasets with secrets, credentials, or personal data. Keep real environment values in untracked `.env` files and commit only a sanitized `.env.example`. When adding dependencies, pin versions and update this guide if the repository structure or workflow changes.
