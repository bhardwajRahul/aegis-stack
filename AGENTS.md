# Repository Guidelines

## Project Structure & Module Organization
- `aegis/`: Typer CLI source; entrypoint `aegis.__main__:app`.
- `aegis/templates/`: Cookiecutter templates consumed by CLI generators.
- `tests/`: Pytest suite, includes CLI and template regression checks.
- `docs/` + `mkdocs.yml`: MkDocs content and configuration.
- `Makefile`, `pyproject.toml`: central automation and tooling settings.

## Build, Test, and Development Commands
- `uv sync --all-extras` or `make install`: provision dev + docs dependencies with uv.
- `make lint`: run ruff lint; use `make fix` / `make format` for autofix.
- `make typecheck`: strict mypy pass.
- `make test`: pytest all suites; `make cli-test` for smoke CLI invocation.
- `make check`: aggregate lint, typecheck, tests; `make docs-serve` for live docs.

## Coding Style & Naming Conventions
- Python 3.11, strict typing; prefer precise annotations.
- Formatting via ruff; 88 char line length, double quotes, spaces for indent.
- Imports sorted by ruff-isort; maintain logical sections (stdlib, third-party, local).
- Naming: functions/modules snake_case, classes CapWords, constants SCREAMING_SNAKE_CASE.

## Testing Guidelines
- Tests live under `tests/`; name files `test_*.py` and follow pytest fixtures.
- Use pytest markers `slow` / `integration` to segment longer suites.
- Template changes require `make test-template`; quick loop `uv run pytest -q -m "not slow"`.
- Maintain coverage of generated projects when updating `aegis/templates/`.

## Commit & Pull Request Guidelines
- Commit messages follow Conventional Commits, e.g., `feat(cli): add stack scaffold`.
- Before pushing, run `make check` and attach relevant CLI/doc output in PRs.
- PR descriptions should state rationale, link issues, and note template impacts or migration steps.
- Install pre-commit hooks (`pre-commit install`) to enforce lint/type gates locally.

## Security & Configuration Tips
- Never commit secrets; keep `.env` out of VCS and update `.env.example`.
- Review dependencies with `uv run pip-audit` when bumping packages.
- Leverage `make redis-*` targets for local container helpers without polluting system services.
