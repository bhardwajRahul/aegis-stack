"""
Tests for TemplateGenerator class.

Tests the template context generation, particularly the AI service
auto-detection logic that selects sqlite backend when database component
is available.
"""

from pathlib import Path

from aegis.constants import StorageBackends
from aegis.core.template_generator import TemplateGenerator


class TestTemplateGeneratorAIAutoDetection:
    """Test AI backend auto-detection based on available components.

    When AI service is selected without explicit backend (no bracket syntax),
    the system should auto-detect and use sqlite if database is available.
    """

    def test_ai_without_database_defaults_to_memory(self) -> None:
        """AI service without database should use memory backend."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=[],  # No database
            selected_services=["ai"],
        )
        assert gen.ai_backend == StorageBackends.MEMORY

    def test_ai_with_database_auto_detects_sqlite(self) -> None:
        """AI service with database should auto-detect sqlite backend.

        This is the critical test for the auto-detection feature:
        when user specifies --services ai --components database,
        the AI backend should automatically use sqlite.
        """
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database"],
            selected_services=["ai"],
        )
        assert gen.ai_backend == StorageBackends.SQLITE

    def test_ai_explicit_memory_overrides_auto_detection(self) -> None:
        """Explicit ai[memory] should use memory even with database.

        User explicitly specifying memory backend should override auto-detection.
        """
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database"],
            selected_services=["ai[memory]"],
        )
        assert gen.ai_backend == StorageBackends.MEMORY

    def test_ai_explicit_sqlite_works(self) -> None:
        """Explicit ai[sqlite] should use sqlite."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=[],  # No database component
            selected_services=["ai[sqlite]"],
        )
        assert gen.ai_backend == StorageBackends.SQLITE

    def test_ai_with_database_bracket_syntax(self) -> None:
        """AI with database[sqlite] component should auto-detect sqlite."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database[sqlite]"],
            selected_services=["ai"],
        )
        assert gen.ai_backend == StorageBackends.SQLITE

    def test_no_ai_service_defaults_to_memory(self) -> None:
        """Without AI service, ai_backend should be memory (default)."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database"],
            selected_services=[],  # No AI service
        )
        assert gen.ai_backend == StorageBackends.MEMORY

    def test_context_includes_correct_ai_backend(self) -> None:
        """Template context should include the auto-detected ai_backend."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database"],
            selected_services=["ai"],
        )
        context = gen.get_template_context()
        assert context["ai_backend"] == StorageBackends.SQLITE
        assert context["ai_with_persistence"] == "yes"

    def test_context_memory_backend_no_persistence(self) -> None:
        """Memory backend should set ai_with_persistence to 'no'."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=[],
            selected_services=["ai"],
        )
        context = gen.get_template_context()
        assert context["ai_backend"] == StorageBackends.MEMORY
        assert context["ai_with_persistence"] == "no"


class TestTemplateGeneratorMultipleServices:
    """Test AI auto-detection with multiple services."""

    def test_ai_with_auth_and_database(self) -> None:
        """AI + auth + database should auto-detect sqlite for AI."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database"],
            selected_services=["ai", "auth"],
        )
        assert gen.ai_backend == StorageBackends.SQLITE

    def test_ai_with_comms_and_database(self) -> None:
        """AI + comms + database should auto-detect sqlite for AI."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database"],
            selected_services=["ai", "comms"],
        )
        assert gen.ai_backend == StorageBackends.SQLITE


class TestTemplateGeneratorCommsService:
    """Test comms service handling in template context.

    These tests verify that include_comms is correctly set in the
    template context when comms service is selected.
    """

    def test_comms_service_sets_include_comms(self) -> None:
        """Comms service should set include_comms to 'yes' in context."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=[],
            selected_services=["comms"],
        )
        context = gen.get_template_context()
        assert context["include_comms"] == "yes"

    def test_no_comms_service_sets_include_comms_no(self) -> None:
        """Without comms service, include_comms should be 'no'."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=[],
            selected_services=[],
        )
        context = gen.get_template_context()
        assert context["include_comms"] == "no"

    def test_comms_with_auth_both_included(self) -> None:
        """Both comms and auth services should be included when selected."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database"],
            selected_services=["comms", "auth"],
        )
        context = gen.get_template_context()
        assert context["include_comms"] == "yes"
        assert context["include_auth"] == "yes"

    def test_all_services_included(self) -> None:
        """All services should be included when all selected."""
        gen = TemplateGenerator(
            project_name="test-project",
            selected_components=["database"],
            selected_services=["comms", "auth", "ai"],
        )
        context = gen.get_template_context()
        assert context["include_comms"] == "yes"
        assert context["include_auth"] == "yes"
        assert context["include_ai"] == "yes"


class TestCopierAnswersTemplate:
    """Test that the .copier-answers.yml.jinja template includes all service flags.

    This is a regression test to ensure new services are added to the answers template.
    Without this, services may work on first init but break on subsequent add/remove operations.
    """

    def test_copier_answers_template_includes_all_services(self) -> None:
        """The .copier-answers.yml.jinja template must include all service flags.

        CRITICAL: If a service flag is missing from this template, the service
        will work on first init but break when add-service/remove-service
        operations regenerate shared files (because the flag won't be saved).
        """
        # Find the template file
        template_path = (
            Path(__file__).parent.parent.parent
            / "aegis"
            / "templates"
            / "copier-aegis-project"
            / "{{ project_slug }}"
            / ".copier-answers.yml.jinja"
        )

        assert template_path.exists(), f"Template not found: {template_path}"

        template_content = template_path.read_text()

        # All service include flags that should be in the template
        required_service_flags = [
            "include_auth",
            "include_ai",
            "include_comms",  # This was missing and caused the bug!
        ]

        for flag in required_service_flags:
            assert flag in template_content, (
                f"Service flag '{flag}' is missing from .copier-answers.yml.jinja - this will cause add/remove operations to break for this service!"
            )
