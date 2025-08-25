"""
Tests for database configuration in Aegis Stack projects.

This module tests that database configuration is properly generated
and accessible in projects that include the database component.
"""

from pathlib import Path

from aegis.core.template_generator import TemplateGenerator


class TestDatabaseConfiguration:
    """Test database configuration generation and access."""

    def test_database_config_included_when_component_selected(self) -> None:
        """Test that database config is included when database component selected."""
        generator = TemplateGenerator("test-db-project", ["database"])
        context = generator.get_template_context()

        assert context["include_database"] == "yes"

    def test_database_config_excluded_when_component_not_selected(self) -> None:
        """Test database config excluded when component not selected."""
        generator = TemplateGenerator("test-basic-project", [])
        context = generator.get_template_context()

        assert context["include_database"] == "no"

    def test_database_config_values_are_correct(self, temp_output_dir: Path) -> None:
        """Test that generated database configuration has correct default values."""
        from tests.cli.test_utils import (
            assert_database_config_present,
            assert_file_exists,
            run_aegis_init,
        )

        result = run_aegis_init("test-database-config", ["database"], temp_output_dir)

        assert result.success
        assert result.project_path is not None

        # Check that config.py exists and contains database settings
        config_file = result.project_path / "app" / "core" / "config.py"
        assert_file_exists(result.project_path, "app/core/config.py")

        config_content = config_file.read_text()
        assert_database_config_present(config_content)

    def test_database_config_absent_without_component(
        self, temp_output_dir: Path
    ) -> None:
        """Test database config absent when component not selected."""
        from tests.cli.test_utils import (
            assert_database_config_absent,
            assert_file_exists,
            run_aegis_init,
        )

        result = run_aegis_init(
            "test-no-database",
            [],  # No components
            temp_output_dir,
        )

        assert result.success
        assert result.project_path is not None

        # Check that config.py exists but doesn't contain database settings
        config_file = result.project_path / "app" / "core" / "config.py"
        assert_file_exists(result.project_path, "app/core/config.py")

        config_content = config_file.read_text()
        assert_database_config_absent(config_content)

    def test_database_config_imports_any_type(self, temp_output_dir: Path) -> None:
        """Test that config.py imports Any type for DATABASE_CONNECT_ARGS."""
        from tests.cli.test_utils import run_aegis_init

        result = run_aegis_init("test-database-types", ["database"], temp_output_dir)

        assert result.success
        assert result.project_path is not None

        config_file = result.project_path / "app" / "core" / "config.py"
        config_content = config_file.read_text()

        # Verify Any type is imported for type hints
        assert "from typing import Any" in config_content
        assert "dict[str, Any]" in config_content

    def test_database_file_generated_with_component(
        self, temp_output_dir: Path
    ) -> None:
        """Test db.py file generated when database component selected."""
        from tests.cli.test_utils import (
            assert_db_file_structure,
            assert_file_exists,
            run_aegis_init,
        )

        result = run_aegis_init("test-database-file", ["database"], temp_output_dir)

        assert result.success
        assert result.project_path is not None

        # Check that db.py exists
        assert_file_exists(result.project_path, "app/core/db.py")

        db_file = result.project_path / "app" / "core" / "db.py"
        db_content = db_file.read_text()
        # Use enhanced validation that checks complete structure
        assert_db_file_structure(db_content)

    def test_database_file_not_generated_without_component(
        self, temp_output_dir: Path
    ) -> None:
        """Test db.py file not generated without database component."""
        from tests.cli.test_utils import run_aegis_init

        result = run_aegis_init(
            "test-no-database-file",
            [],  # No components
            temp_output_dir,
        )

        assert result.success
        assert result.project_path is not None

        # Check that db.py does not exist
        db_file = result.project_path / "app" / "core" / "db.py"
        assert not db_file.exists()
