"""
Tests for dynamic migration generator module.

These tests validate the migration generation functionality that creates
Alembic migration files on-demand for services like auth and AI.
"""

from pathlib import Path

from aegis.core.migration_generator import (
    AI_MIGRATION,
    AUTH_MIGRATION,
    MIGRATION_SPECS,
    ColumnSpec,
    IndexSpec,
    TableSpec,
    generate_migration,
    generate_migrations_for_services,
    get_existing_migrations,
    get_next_revision_id,
    get_previous_revision,
    get_services_needing_migrations,
    get_versions_dir,
    service_has_migration,
)


class TestGetServicesNeedingMigrations:
    """Test detection of which services need migrations based on context."""

    def test_auth_only(self) -> None:
        """Test auth service needs migrations."""
        context = {"include_auth": True, "include_ai": False, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == ["auth"]

    def test_auth_with_yes_string(self) -> None:
        """Test auth service with 'yes' string (cookiecutter format)."""
        context = {"include_auth": "yes", "include_ai": "no", "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == ["auth"]

    def test_ai_with_sqlite(self) -> None:
        """Test AI service with sqlite backend needs migrations."""
        context = {"include_auth": False, "include_ai": True, "ai_backend": "sqlite"}
        result = get_services_needing_migrations(context)
        assert result == ["ai"]

    def test_ai_with_memory_no_migrations(self) -> None:
        """Test AI service with memory backend does NOT need migrations."""
        context = {"include_auth": False, "include_ai": True, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == []

    def test_both_services(self) -> None:
        """Test both auth and AI services need migrations."""
        context = {"include_auth": True, "include_ai": True, "ai_backend": "sqlite"}
        result = get_services_needing_migrations(context)
        assert result == ["auth", "ai"]

    def test_neither_service(self) -> None:
        """Test no services need migrations."""
        context = {"include_auth": False, "include_ai": False, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == []


class TestGetVersionsDir:
    """Test getting the alembic versions directory."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        """Test that correct versions path is returned."""
        result = get_versions_dir(tmp_path)
        assert result == tmp_path / "alembic" / "versions"


class TestGetExistingMigrations:
    """Test detection of existing migration files."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test returns empty list when no migrations exist."""
        result = get_existing_migrations(tmp_path)
        assert result == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test returns empty list when versions dir doesn't exist."""
        result = get_existing_migrations(tmp_path / "nonexistent")
        assert result == []

    def test_finds_migrations(self, tmp_path: Path) -> None:
        """Test finds existing migration files."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)

        # Create some migration files
        (versions_dir / "001_auth.py").touch()
        (versions_dir / "002_ai.py").touch()
        (versions_dir / "__init__.py").touch()  # Should be ignored

        result = get_existing_migrations(tmp_path)
        assert result == ["001", "002"]

    def test_sorts_by_filename(self, tmp_path: Path) -> None:
        """Test migrations are sorted by filename."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)

        # Create in non-sorted order
        (versions_dir / "003_third.py").touch()
        (versions_dir / "001_first.py").touch()
        (versions_dir / "002_second.py").touch()

        result = get_existing_migrations(tmp_path)
        assert result == ["001", "002", "003"]


class TestGetNextRevisionId:
    """Test getting the next revision ID."""

    def test_first_migration(self, tmp_path: Path) -> None:
        """Test returns '001' for first migration."""
        result = get_next_revision_id(tmp_path)
        assert result == "001"

    def test_increments_existing(self, tmp_path: Path) -> None:
        """Test increments from existing migrations."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").touch()
        (versions_dir / "002_ai.py").touch()

        result = get_next_revision_id(tmp_path)
        assert result == "003"


class TestGetPreviousRevision:
    """Test getting the previous revision ID."""

    def test_no_migrations(self, tmp_path: Path) -> None:
        """Test returns None when no migrations exist."""
        result = get_previous_revision(tmp_path)
        assert result is None

    def test_returns_last_revision(self, tmp_path: Path) -> None:
        """Test returns the most recent revision."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").touch()
        (versions_dir / "002_ai.py").touch()

        result = get_previous_revision(tmp_path)
        assert result == "002"


class TestServiceHasMigration:
    """Test detection of existing service migrations."""

    def test_no_migrations(self, tmp_path: Path) -> None:
        """Test returns False when no migrations exist."""
        result = service_has_migration(tmp_path, "auth")
        assert result is False

    def test_migration_exists(self, tmp_path: Path) -> None:
        """Test returns True when service migration exists."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").touch()

        result = service_has_migration(tmp_path, "auth")
        assert result is True

    def test_different_service(self, tmp_path: Path) -> None:
        """Test returns False for different service."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").touch()

        result = service_has_migration(tmp_path, "ai")
        assert result is False


class TestGenerateMigration:
    """Test individual migration generation."""

    def test_unknown_service(self, tmp_path: Path) -> None:
        """Test returns None for unknown service."""
        result = generate_migration(tmp_path, "unknown")
        assert result is None

    def test_generates_auth_migration(self, tmp_path: Path) -> None:
        """Test generates auth migration file."""
        result = generate_migration(tmp_path, "auth")

        assert result is not None
        assert result.exists()
        assert result.name == "001_auth.py"

        # Verify content
        content = result.read_text()
        assert "revision = '001'" in content
        assert "down_revision = None" in content
        assert "op.create_table" in content
        assert "'user'" in content
        assert "'email'" in content

    def test_generates_ai_migration(self, tmp_path: Path) -> None:
        """Test generates AI migration file."""
        result = generate_migration(tmp_path, "ai")

        assert result is not None
        assert result.exists()
        assert result.name == "001_ai.py"

        # Verify content
        content = result.read_text()
        assert "'conversation'" in content
        assert "'conversation_message'" in content
        assert "op.create_index" in content

    def test_creates_versions_directory(self, tmp_path: Path) -> None:
        """Test creates versions directory if it doesn't exist."""
        assert not (tmp_path / "alembic" / "versions").exists()

        generate_migration(tmp_path, "auth")

        assert (tmp_path / "alembic" / "versions").exists()


class TestGenerateMigrationsForServices:
    """Test batch migration generation."""

    def test_generates_in_order(self, tmp_path: Path) -> None:
        """Test generates migrations in specified order."""
        result = generate_migrations_for_services(tmp_path, ["auth", "ai"])

        assert len(result) == 2
        assert result[0].name == "001_auth.py"
        assert result[1].name == "002_ai.py"

        # Verify down_revision chain
        auth_content = result[0].read_text()
        ai_content = result[1].read_text()

        assert "down_revision = None" in auth_content
        assert "down_revision = '001'" in ai_content

    def test_skips_existing_migrations(self, tmp_path: Path) -> None:
        """Test skips services that already have migrations."""
        # Create existing auth migration
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").write_text("# existing")

        result = generate_migrations_for_services(tmp_path, ["auth", "ai"])

        # Should only generate AI
        assert len(result) == 1
        assert result[0].name == "002_ai.py"

    def test_skips_unknown_services(self, tmp_path: Path) -> None:
        """Test skips unknown services without error."""
        result = generate_migrations_for_services(tmp_path, ["unknown", "auth"])

        assert len(result) == 1
        assert result[0].name == "001_auth.py"

    def test_empty_list(self, tmp_path: Path) -> None:
        """Test handles empty service list."""
        result = generate_migrations_for_services(tmp_path, [])
        assert result == []


class TestMigrationSpecs:
    """Test migration specification definitions."""

    def test_auth_spec_exists(self) -> None:
        """Test auth migration spec is defined."""
        assert "auth" in MIGRATION_SPECS
        assert AUTH_MIGRATION.service_name == "auth"
        assert len(AUTH_MIGRATION.tables) == 1
        assert AUTH_MIGRATION.tables[0].name == "user"

    def test_ai_spec_exists(self) -> None:
        """Test AI migration spec is defined."""
        assert "ai" in MIGRATION_SPECS
        assert AI_MIGRATION.service_name == "ai"
        assert len(AI_MIGRATION.tables) == 2

        table_names = [t.name for t in AI_MIGRATION.tables]
        assert "conversation" in table_names
        assert "conversation_message" in table_names

    def test_ai_has_foreign_key(self) -> None:
        """Test AI conversation_message has foreign key to conversation."""
        message_table = next(
            t for t in AI_MIGRATION.tables if t.name == "conversation_message"
        )
        assert len(message_table.foreign_keys) == 1
        assert message_table.foreign_keys[0].ref_table == "conversation"


class TestDataclasses:
    """Test dataclass definitions."""

    def test_column_spec_defaults(self) -> None:
        """Test ColumnSpec default values."""
        col = ColumnSpec("test", "sa.String()")
        assert col.nullable is True
        assert col.primary_key is False
        assert col.default is None

    def test_index_spec_defaults(self) -> None:
        """Test IndexSpec default values."""
        idx = IndexSpec("test_idx", ["col1"])
        assert idx.unique is False

    def test_table_spec_defaults(self) -> None:
        """Test TableSpec default values."""
        table = TableSpec("test", [ColumnSpec("id", "sa.Integer()")])
        assert table.indexes == []
        assert table.foreign_keys == []
