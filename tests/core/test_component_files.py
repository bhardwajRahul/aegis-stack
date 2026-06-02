"""Tests for component file expansion, focused on skipping non-template files."""

from __future__ import annotations

from pathlib import Path

from aegis.core.component_files import (
    PROJECT_SLUG_PLACEHOLDER,
    _is_skippable_template_file,
    get_component_files,
    get_template_path,
)


class TestIsSkippableTemplateFile:
    """The walk must ignore tooling-cache dirs and binary artefacts."""

    def test_skips_pycache_dir(self) -> None:
        assert _is_skippable_template_file(
            Path("app/components/worker/__pycache__/broker.cpython-313.pyc")
        )

    def test_skips_compiled_python_anywhere(self) -> None:
        assert _is_skippable_template_file(Path("a/b/module.pyc"))
        assert _is_skippable_template_file(Path("module.pyo"))

    def test_skips_binary_assets(self) -> None:
        assert _is_skippable_template_file(Path("assets/logo.png"))
        assert _is_skippable_template_file(Path("assets/font.WOFF2"))

    def test_keeps_authored_python_and_jinja(self) -> None:
        assert not _is_skippable_template_file(Path("app/components/worker/broker.py"))
        assert not _is_skippable_template_file(Path("app/core/config.py.jinja"))
        assert not _is_skippable_template_file(
            Path("app/components/worker/__init__.py")
        )


class TestGetComponentFilesSkipsStrayArtefacts:
    """Regression: a stray ``.pyc`` in the template tree must not be returned.

    Importing a template's raw ``.py`` files compiles bytecode into a
    ``__pycache__`` beside them; the file walk used to include that ``.pyc``
    and the downstream UTF-8 renderer crashed reading it.
    """

    def test_pycache_excluded_from_worker_component(self) -> None:
        worker_dir = (
            get_template_path() / PROJECT_SLUG_PLACEHOLDER / "app/components/worker"
        )
        pycache = worker_dir / "__pycache__"
        stray = pycache / "broker_dramatiq.cpython-313.pyc"
        created_dir = not pycache.exists()
        pycache.mkdir(exist_ok=True)
        # Invalid UTF-8 byte that previously crashed the read_text() walk.
        stray.write_bytes(b"\xf3\x00\x01compiled")
        try:
            files = get_component_files("worker")
        finally:
            stray.unlink(missing_ok=True)
            if created_dir and pycache.exists() and not any(pycache.iterdir()):
                pycache.rmdir()

        assert not any("__pycache__" in f for f in files)
        assert not any(f.endswith(".pyc") for f in files)
        # Sanity: the real worker sources are still discovered.
        assert any(f.endswith("heartbeat.py") for f in files)
