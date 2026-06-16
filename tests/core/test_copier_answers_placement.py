"""Guard: ``.copier-answers.yml`` must land INSIDE the generated project.

Copier 9.15 changed where the answers file is written for templates that use
``_subdirectory`` + a ``{{ project_slug }}`` wrapper: it moved the file from
inside the project directory to the OUTPUT PARENT. ``aegis update`` reads it at
``project_path / ANSWERS_FILENAME``, so the misplaced file makes every freshly
generated project look "not generated with Copier" and breaks updates.

This test fails the moment a copier version that misplaces the file enters the
resolved environment (e.g. the ``<9.15`` cap in pyproject.toml gets loosened and
the lock re-resolves). It does NOT, on its own, catch a brand-new copier release
while the cap holds — that is the job of the separate "latest copier" drift
canary in CI (.github/workflows/ci.yml).
"""

from __future__ import annotations

from pathlib import Path

from aegis.constants import AnswerKeys
from aegis.core.copier_manager import generate_with_copier
from aegis.core.template_generator import TemplateGenerator


def test_answers_file_lands_inside_project(tmp_path: Path) -> None:
    """A base stack must carry ``.copier-answers.yml`` in its own root."""
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    template_gen = TemplateGenerator(
        project_name="placement_probe",
        selected_components=[],
        scheduler_backend="memory",
        selected_services=[],
    )
    generate_with_copier(template_gen, output_dir, dev_mode=True)

    # Copier creates the project under its slug, not the raw project name.
    project_slug = template_gen.get_template_context()["project_slug"]
    project_path = output_dir / project_slug
    answers_inside = project_path / AnswerKeys.ANSWERS_FILENAME
    answers_in_parent = output_dir / AnswerKeys.ANSWERS_FILENAME

    assert answers_inside.exists(), (
        f"{AnswerKeys.ANSWERS_FILENAME} is missing from the project dir "
        f"({project_path}). Copier likely wrote it to the output parent "
        f"({output_dir}); this breaks `aegis update`. Check the copier version "
        f"and the `copier<9.15` cap in pyproject.toml."
    )
    assert not answers_in_parent.exists(), (
        f"{AnswerKeys.ANSWERS_FILENAME} leaked into the output parent "
        f"({output_dir}) instead of the project dir. This is the copier 9.15 "
        f"placement regression; keep the `copier<9.15` cap in pyproject.toml."
    )
