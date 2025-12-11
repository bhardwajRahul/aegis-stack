"""
Tests for AI backend detection and dependency expansion utilities.

Tests the detect_ai_backend() and expand_ai_dependencies() functions.
"""

from aegis.cli.utils import detect_ai_backend, expand_ai_dependencies


class TestDetectAIBackend:
    """Test AI backend detection from service list."""

    def test_detect_memory_explicit(self):
        """Test detecting explicit memory backend."""
        services = ["ai[memory]"]
        backend = detect_ai_backend(services)
        assert backend == "memory"

    def test_detect_sqlite_explicit(self):
        """Test detecting explicit sqlite backend."""
        services = ["ai[sqlite]"]
        backend = detect_ai_backend(services)
        assert backend == "sqlite"

    def test_detect_default_memory(self):
        """Test that plain 'ai' defaults to memory."""
        services = ["ai"]
        backend = detect_ai_backend(services)
        assert backend == "memory"

    def test_detect_no_ai_service(self):
        """Test detection when AI service not present."""
        services = ["auth"]
        backend = detect_ai_backend(services)
        assert backend == "memory"  # Default

    def test_detect_empty_list(self):
        """Test detection with empty service list."""
        services = []
        backend = detect_ai_backend(services)
        assert backend == "memory"  # Default

    def test_detect_ai_among_multiple_services(self):
        """Test detecting AI backend among multiple services."""
        services = ["auth", "ai[sqlite]", "comms"]
        backend = detect_ai_backend(services)
        assert backend == "sqlite"


class TestExpandAIDependencies:
    """Test AI dependency expansion."""

    def test_expand_ai_sqlite_adds_database(self):
        """Test that ai[sqlite] expands to add database[sqlite]."""
        services = ["ai[sqlite]"]
        existing_components = ["backend"]

        auto_added = expand_ai_dependencies(services, existing_components)

        assert "database[sqlite]" in auto_added

    def test_expand_ai_memory_no_database(self):
        """Test that ai[memory] does NOT add database."""
        services = ["ai[memory]"]
        existing_components = ["backend"]

        auto_added = expand_ai_dependencies(services, existing_components)

        assert auto_added == []

    def test_expand_plain_ai_no_database(self):
        """Test that plain 'ai' (memory default) does NOT add database."""
        services = ["ai"]
        existing_components = ["backend"]

        auto_added = expand_ai_dependencies(services, existing_components)

        assert auto_added == []

    def test_expand_ai_sqlite_skips_existing_database(self):
        """Test that ai[sqlite] doesn't add database if already present."""
        services = ["ai[sqlite]"]
        existing_components = ["backend", "database"]

        auto_added = expand_ai_dependencies(services, existing_components)

        assert auto_added == []  # Database already exists

    def test_expand_ai_sqlite_skips_database_with_engine(self):
        """Test that ai[sqlite] skips database[sqlite] if it already exists."""
        services = ["ai[sqlite]"]
        existing_components = ["backend", "database[sqlite]"]

        auto_added = expand_ai_dependencies(services, existing_components)

        assert auto_added == []  # Database already exists

    def test_expand_empty_services(self):
        """Test expansion with empty service list."""
        services = []
        existing_components = ["backend"]

        auto_added = expand_ai_dependencies(services, existing_components)

        assert auto_added == []

    def test_expand_no_ai_service(self):
        """Test expansion when AI service not present."""
        services = ["auth", "comms"]
        existing_components = ["backend"]

        auto_added = expand_ai_dependencies(services, existing_components)

        assert auto_added == []
