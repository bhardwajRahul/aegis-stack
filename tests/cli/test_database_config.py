"""
Tests for database configuration in Aegis Stack projects.

This module tests that database configuration is properly generated
and accessible in projects that include the database component.
"""

from typing import TYPE_CHECKING

from aegis.core.template_generator import TemplateGenerator

if TYPE_CHECKING:
    from tests.cli.conftest import ProjectFactory


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

    def test_database_config_values_are_correct(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that generated database configuration has correct default values."""
        from tests.cli.test_utils import (
            assert_database_config_present,
            assert_file_exists,
        )

        # Use cached project with database component
        project_path = project_factory("base_with_database")

        # Check that config.py exists and contains database settings
        config_file = project_path / "app" / "core" / "config.py"
        assert_file_exists(project_path, "app/core/config.py")

        config_content = config_file.read_text()
        assert_database_config_present(config_content)

    def test_database_config_absent_without_component(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test database config absent when component not selected."""
        from tests.cli.test_utils import (
            assert_database_config_absent,
            assert_file_exists,
        )

        # Use cached base project (no components)
        project_path = project_factory("base")

        # Check that config.py exists but doesn't contain database settings
        config_file = project_path / "app" / "core" / "config.py"
        assert_file_exists(project_path, "app/core/config.py")

        config_content = config_file.read_text()
        assert_database_config_absent(config_content)

    def test_database_config_imports_any_type(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that config.py imports Any type for DATABASE_CONNECT_ARGS."""
        # Use cached project with database component
        project_path = project_factory("base_with_database")

        config_file = project_path / "app" / "core" / "config.py"
        config_content = config_file.read_text()

        # Verify Any type is imported for type hints
        assert "from typing import Any" in config_content
        assert "dict[str, Any]" in config_content

    def test_database_file_generated_with_component(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test db.py file generated when database component selected."""
        from tests.cli.test_utils import (
            assert_db_file_structure,
            assert_file_exists,
        )

        # Use cached project with database component
        project_path = project_factory("base_with_database")

        # Check that db.py exists
        assert_file_exists(project_path, "app/core/db.py")

        db_file = project_path / "app" / "core" / "db.py"
        db_content = db_file.read_text()
        # Use enhanced validation that checks complete structure
        assert_db_file_structure(db_content)

    def test_database_file_not_generated_without_component(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test db.py file not generated without database component."""
        # Use cached base project (no components)
        project_path = project_factory("base")

        # Check that db.py does not exist
        db_file = project_path / "app" / "core" / "db.py"
        assert not db_file.exists()
