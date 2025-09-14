"""
Tests for scheduler backend detection and expansion logic.

Tests the new functions added to __main__.py for handling scheduler[backend] syntax.
"""

from aegis.cli.utils import detect_scheduler_backend, expand_scheduler_dependencies


class TestSchedulerBackendDetection:
    """Test scheduler backend detection from component lists."""

    def test_detect_scheduler_sqlite_backend(self) -> None:
        """Test detecting scheduler[sqlite] backend."""
        components = ["scheduler[sqlite]", "redis"]
        backend = detect_scheduler_backend(components)
        assert backend == "sqlite"

    def test_detect_scheduler_postgres_backend(self) -> None:
        """Test detecting scheduler[postgres] backend."""
        components = ["worker", "scheduler[postgres]"]
        backend = detect_scheduler_backend(components)
        assert backend == "postgres"

    def test_detect_memory_backend_no_scheduler(self) -> None:
        """Test detecting memory backend when no scheduler present."""
        components = ["redis", "worker"]
        backend = detect_scheduler_backend(components)
        assert backend == "memory"

    def test_detect_memory_backend_plain_scheduler(self) -> None:
        """Test detecting memory backend with plain scheduler."""
        components = ["scheduler", "redis"]
        backend = detect_scheduler_backend(components)
        assert backend == "memory"

    def test_detect_sqlite_backend_legacy_detection(self) -> None:
        """Test detecting sqlite backend via legacy scheduler+database detection."""
        components = ["scheduler", "database", "redis"]
        backend = detect_scheduler_backend(components)
        assert backend == "sqlite"

    def test_direct_backend_overrides_legacy(self) -> None:
        """Test that direct scheduler[backend] overrides legacy detection."""
        components = ["scheduler[postgres]", "database", "redis"]
        backend = detect_scheduler_backend(components)
        assert backend == "postgres"  # Direct syntax wins over legacy


class TestSchedulerDependencyExpansion:
    """Test automatic expansion of scheduler[backend] dependencies."""

    def test_expand_scheduler_sqlite_adds_database(self) -> None:
        """Test that scheduler[sqlite] adds database[sqlite]."""
        components = ["scheduler[sqlite]", "redis"]
        expanded = expand_scheduler_dependencies(components)

        assert "scheduler[sqlite]" in expanded
        assert "database[sqlite]" in expanded
        assert "redis" in expanded
        assert len(expanded) == 3

    def test_expand_scheduler_postgres_adds_database(self) -> None:
        """Test that scheduler[postgres] adds database[postgres]."""
        components = ["scheduler[postgres]"]
        expanded = expand_scheduler_dependencies(components)

        assert "scheduler[postgres]" in expanded
        assert "database[postgres]" in expanded
        assert len(expanded) == 2

    def test_expand_memory_scheduler_no_database(self) -> None:
        """Test that plain scheduler doesn't add database."""
        components = ["scheduler", "redis"]
        expanded = expand_scheduler_dependencies(components)

        assert expanded == ["scheduler", "redis"]  # No changes

    def test_expand_with_existing_database(self) -> None:
        """Test expansion when database already exists."""
        components = ["scheduler[sqlite]", "database[postgres]", "redis"]
        expanded = expand_scheduler_dependencies(components)

        # Should not add another database
        assert "scheduler[sqlite]" in expanded
        assert "database[postgres]" in expanded  # Existing one preserved
        assert "redis" in expanded
        assert len(expanded) == 3
        assert "database[sqlite]" not in expanded  # Not added

    def test_expand_multiple_scheduler_backends(self) -> None:
        """Test expansion with multiple scheduler backends (edge case)."""
        components = ["scheduler[sqlite]", "scheduler[postgres]"]
        expanded = expand_scheduler_dependencies(components)

        # Should add databases for both backends, but avoid duplicate databases
        # when both schedulers have same backend
        assert "scheduler[sqlite]" in expanded
        assert "scheduler[postgres]" in expanded
        # At least one database should be added, but logic may prevent duplicates
        assert any("database[" in comp for comp in expanded)
        assert len(expanded) >= 3  # At least original 2 + 1 database

    def test_expand_preserves_order(self) -> None:
        """Test that expansion preserves component order."""
        components = ["redis", "scheduler[sqlite]", "worker"]
        expanded = expand_scheduler_dependencies(components)

        # Should preserve original order, with database appended
        assert expanded == ["redis", "scheduler[sqlite]", "worker", "database[sqlite]"]
