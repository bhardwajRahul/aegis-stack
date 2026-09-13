"""``generate_revisions`` runs the project's own generator, in its venv."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from aegis.core.migration_generator import (
    MigrationGenerationError,
    generate_revisions,
)


def _versions(tmp_path: Path) -> Path:
    versions = tmp_path / "alembic" / "versions"
    versions.mkdir(parents=True)
    return versions


def test_runs_migrate_gen_in_the_project_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UV_PYTHON", "3.11")
    versions = _versions(tmp_path)

    def fake_run(cmd: list[str], **_kw: object) -> Mock:
        (versions / "001_auth.py").write_text("")
        return Mock(returncode=0, stderr="", stdout="001_auth.py\n")

    with patch(
        "aegis.core.migration_generator.subprocess.run", side_effect=fake_run
    ) as run:
        written = generate_revisions(
            tmp_path, ["auth", "finance"], python_version="3.13"
        )

    cmd = run.call_args.args[0]
    assert cmd[:4] == ["uv", "run", "--project", str(tmp_path)]
    assert "--python" in cmd and cmd[cmd.index("--python") + 1] == "3.13"
    assert cmd[-5:] == ["python", "-m", "app.cli.migrate_gen", "auth", "finance"]
    env = run.call_args.kwargs["env"]
    assert "VIRTUAL_ENV" not in env
    # the tool's own interpreter pin must not reach the project's resolve
    assert "UV_PYTHON" not in env
    assert written == [versions / "001_auth.py"]


def test_returns_only_files_this_call_wrote(tmp_path: Path) -> None:
    versions = _versions(tmp_path)
    (versions / "001_auth.py").write_text("")

    def fake_run(cmd: list[str], **_kw: object) -> Mock:
        (versions / "002_blog.py").write_text("")
        return Mock(returncode=0, stderr="", stdout="")

    with patch("aegis.core.migration_generator.subprocess.run", side_effect=fake_run):
        assert generate_revisions(tmp_path, ["blog"]) == [versions / "002_blog.py"]


def test_no_services_runs_nothing(tmp_path: Path) -> None:
    with patch("aegis.core.migration_generator.subprocess.run") as run:
        assert generate_revisions(tmp_path, []) == []
    run.assert_not_called()


def test_failure_raises_with_the_generator_output(tmp_path: Path) -> None:
    _versions(tmp_path)
    with (
        patch(
            "aegis.core.migration_generator.subprocess.run",
            return_value=Mock(
                returncode=1, stderr="ImportError: no module named plaid", stdout=""
            ),
        ),
        pytest.raises(MigrationGenerationError, match="plaid"),
    ):
        generate_revisions(tmp_path, ["finance"])


def test_alembic_pin_matches_the_template(tmp_path: Path) -> None:
    """``_pin_alembic`` writes what a rendered project would have pinned."""
    from aegis.core.migration_generator import ALEMBIC_PIN

    template = Path("aegis/templates/copier-aegis-project/{{ project_slug }}")
    assert f'"{ALEMBIC_PIN}"' in (template / "pyproject.toml.jinja").read_text()


def test_bootstrap_pins_alembic_once(tmp_path: Path) -> None:
    from aegis.core.migration_generator import ALEMBIC_PIN, _pin_alembic

    pyproject = tmp_path / "pyproject.toml"
    # Every database project names alembic in its poe tasks; only the
    # dependency list decides whether it is installed.
    pyproject.write_text(
        '[project]\ndependencies = [\n    "fastapi",\n]\n'
        '\n[tool.poe.tasks.migrate]\ncmd = "uv run alembic upgrade head"\n'
    )
    _pin_alembic(tmp_path)
    _pin_alembic(tmp_path)
    assert pyproject.read_text().count(ALEMBIC_PIN) == 1
