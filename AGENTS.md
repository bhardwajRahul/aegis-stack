# Repository Guidelines

## Project Structure & Modules
- `aegis/`: CLI source (Typer app). Entry point: `aegis.__main__:app` (script: `aegis`).
- `aegis/templates/`: Cookiecutter project templates used by the CLI.
- `tests/`: Pytest suite (CLI and template validation).
- `docs/` + `mkdocs.yml`: MkDocs documentation sources and config.
- `Makefile`: Local dev commands for lint, typecheck, tests, docs.
- `pyproject.toml`: Dependencies and tooling config (ruff, mypy, pytest).

## Build, Test, and Development
- Install: `uv sync --all-extras` (or `make install`) — sets up dev + docs extras.
- Lint: `make lint` — ruff checks; Auto-fix/format: `make fix` or `make format`.
- Type check: `make typecheck` — mypy (strict).
- Tests: `make test` — runs pytest; all checks: `make check`.
- Docs: `make docs-serve` (localhost:8001) or `make docs-build`.
- CLI smoke test: `make cli-test`.

## Coding Style & Naming
- Formatter/Lint: ruff (PEP 8-ish). Line length 88, double quotes, spaces for indent.
- Imports: ruff-isort rules; keep sections clean and sorted.
- Typing: Python 3.11, mypy strict; prefer precise types and return annotations.
- Naming: `snake_case` for modules/functions, `CapWords` for classes, `SCREAMING_SNAKE_CASE` for constants.
- Pre-commit: `pre-commit install` then commit; hooks run ruff+format and mypy.

## Testing Guidelines
- Framework: pytest (asyncio auto). Test paths under `tests/`.
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration` available.
- Quick run: `uv run pytest -q -m "not slow"`; full matrix: `make test-stacks` or `make test-stacks-build`.
- Template tests live in `tests/cli/` and validate generated projects and Docker configs.

## Commit & Pull Requests
- Style: Prefer Conventional Commits (e.g., `feat:`, `fix:`, `docs:`, `ci:`). Imperative, present tense.
- Scope examples: `feat(cli): add components list`.
- PRs: include description, rationale, linked issues, and screenshots or CLI output for UX/docs changes.
- Before pushing: run `make check`. For template changes, run `make test-template`.

## Security & Configuration
- Secrets: never commit `.env`; use `.env.example` as reference.
- Supply chain: `uv run pip-audit` for dependency advisories.
- Containers/Redis helpers: see `make redis-*` targets for local experiments.

