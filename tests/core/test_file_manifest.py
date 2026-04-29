"""
Tests for the declarative file manifest module (R1 of plugin refactor).

These tests lock in the contract of ``aegis/core/file_manifest.py``
independent of its caller (``cleanup_components``). When R2/R3
generalise the spec model, ``cleanup_components`` will change shape
but the manifest contract should not.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from aegis.core.file_manifest import (
    FileManifest,
    apply_cleanup_path,
    iter_cleanup_paths,
)


@dataclass
class _FakeSpec:
    """Minimal spec stand-in for testing — just needs ``name`` and ``files``."""

    name: str
    files: FileManifest = field(default_factory=FileManifest)


class TestFileManifest:
    """The dataclass itself."""

    def test_defaults_empty(self) -> None:
        m = FileManifest()
        assert m.primary == []
        assert m.extras == {}

    def test_independent_instances(self) -> None:
        """Default lists must not be shared across instances."""
        a = FileManifest()
        b = FileManifest()
        a.primary.append("x")
        assert b.primary == []


class TestIterCleanupPaths:
    """The reducer that drives Pattern A cleanup."""

    def test_selected_yields_nothing(self) -> None:
        spec = _FakeSpec(name="auth", files=FileManifest(primary=["app/x", "app/y"]))
        assert list(iter_cleanup_paths(spec, selected=True)) == []

    def test_deselected_yields_primary(self) -> None:
        spec = _FakeSpec(name="auth", files=FileManifest(primary=["app/x", "app/y"]))
        assert list(iter_cleanup_paths(spec, selected=False)) == ["app/x", "app/y"]

    def test_empty_manifest_yields_nothing(self) -> None:
        spec = _FakeSpec(name="empty")
        assert list(iter_cleanup_paths(spec, selected=False)) == []

    def test_spec_without_files_attr_yields_nothing(self) -> None:
        """Specs that haven't been migrated to FileManifest don't break the reducer."""

        class _Bare:
            name = "bare"

        assert list(iter_cleanup_paths(_Bare(), selected=False)) == []

    def test_extras_not_yielded_in_r1(self) -> None:
        """R1 scope: extras are documentation-only; cleanup is primary-only.

        See file_manifest.py module docstring. R2 lights up extras-driven
        cleanup uniformly under the unified spec model.
        """
        spec = _FakeSpec(
            name="ai",
            files=FileManifest(
                primary=["app/services/ai"],
                extras={"ai_rag": ["app/services/rag"]},
            ),
        )
        assert list(iter_cleanup_paths(spec, selected=False)) == ["app/services/ai"]


class TestApplyCleanupPath:
    """The path-applier — file or directory, idempotent on missing."""

    def test_removes_file(self, tmp_path: Path) -> None:
        target = tmp_path / "app" / "thing.py"
        target.parent.mkdir(parents=True)
        target.write_text("x")

        apply_cleanup_path(tmp_path, "app/thing.py")

        assert not target.exists()
        assert target.parent.exists()  # parent dir untouched

    def test_removes_directory_recursively(self, tmp_path: Path) -> None:
        target = tmp_path / "app" / "services" / "auth"
        target.mkdir(parents=True)
        (target / "__init__.py").write_text("")
        (target / "sub").mkdir()
        (target / "sub" / "nested.py").write_text("")

        apply_cleanup_path(tmp_path, "app/services/auth")

        assert not target.exists()

    def test_missing_path_is_noop(self, tmp_path: Path) -> None:
        # Must not raise — matches the behaviour of remove_file / remove_dir.
        apply_cleanup_path(tmp_path, "does/not/exist.py")
        apply_cleanup_path(tmp_path, "does/not/exist/")

    def test_removes_symlink(self, tmp_path: Path) -> None:
        real = tmp_path / "real.py"
        real.write_text("x")
        link = tmp_path / "link.py"
        link.symlink_to(real)

        apply_cleanup_path(tmp_path, "link.py")

        assert not link.exists()
        assert real.exists()  # the target is untouched


class TestRealRegistryShape:
    """Sanity check against the actual SERVICES / COMPONENTS registries.

    Not a behaviour test — guards against silent breakage if a spec stops
    declaring a manifest.
    """

    def test_every_non_core_spec_has_a_manifest(self) -> None:
        from aegis.core.components import COMPONENTS, ComponentType
        from aegis.core.services import SERVICES

        for name, spec in COMPONENTS.items():
            if spec.type == ComponentType.CORE:
                continue
            assert isinstance(spec.files, FileManifest), (
                f"component {name} missing FileManifest"
            )
            assert spec.files.primary, f"component {name} has empty primary"

        for name, spec in SERVICES.items():
            assert isinstance(spec.files, FileManifest), (
                f"service {name} missing FileManifest"
            )
            assert spec.files.primary, f"service {name} has empty primary"

    @pytest.mark.parametrize(
        "registry_name",
        ["scheduler", "worker", "redis", "database", "ingress", "observability"],
    )
    def test_component_primary_paths_are_relative(self, registry_name: str) -> None:
        from aegis.core.components import COMPONENTS

        for path in COMPONENTS[registry_name].files.primary:
            assert not path.startswith("/"), f"{registry_name}: {path!r} is absolute"
            assert ".." not in path, f"{registry_name}: {path!r} traverses parent"
