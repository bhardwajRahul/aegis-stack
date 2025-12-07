"""
Tests for worker backend detection and validation logic.

Tests the functions for handling worker[backend] syntax (arq vs taskiq).
"""

from aegis.cli.utils import detect_worker_backend
from aegis.constants import WorkerBackends


class TestWorkerBackendDetection:
    """Test worker backend detection from component lists."""

    def test_detect_worker_arq_backend_explicit(self) -> None:
        """Test detecting worker[arq] backend."""
        components = ["worker[arq]", "redis"]
        backend = detect_worker_backend(components)
        assert backend == "arq"

    def test_detect_worker_taskiq_backend(self) -> None:
        """Test detecting worker[taskiq] backend."""
        components = ["scheduler", "worker[taskiq]"]
        backend = detect_worker_backend(components)
        assert backend == "taskiq"

    def test_detect_arq_backend_default(self) -> None:
        """Test detecting arq backend when no bracket syntax used."""
        components = ["worker", "redis"]
        backend = detect_worker_backend(components)
        assert backend == "arq"

    def test_detect_arq_when_no_worker(self) -> None:
        """Test default arq when no worker component present."""
        components = ["redis", "scheduler"]
        backend = detect_worker_backend(components)
        assert backend == "arq"  # Default even without worker

    def test_worker_backend_with_other_components(self) -> None:
        """Test worker backend detection with multiple components."""
        components = ["redis", "scheduler[sqlite]", "worker[taskiq]", "database"]
        backend = detect_worker_backend(components)
        assert backend == "taskiq"


class TestWorkerBackendsConstants:
    """Test WorkerBackends constants."""

    def test_arq_constant(self) -> None:
        """Test ARQ constant value."""
        assert WorkerBackends.ARQ == "arq"

    def test_taskiq_constant(self) -> None:
        """Test TASKIQ constant value."""
        assert WorkerBackends.TASKIQ == "taskiq"

    def test_all_backends_list(self) -> None:
        """Test ALL backends list contains expected values."""
        assert WorkerBackends.ARQ in WorkerBackends.ALL
        assert WorkerBackends.TASKIQ in WorkerBackends.ALL
        assert len(WorkerBackends.ALL) == 2
