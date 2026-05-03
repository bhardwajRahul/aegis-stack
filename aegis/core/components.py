"""
Component registry and specifications for Aegis Stack.

This module defines all available components, their dependencies, and metadata
used for project generation and validation.
"""

from dataclasses import dataclass
from enum import Enum

from .file_manifest import FileManifest
from .plugins.spec import PluginKind, PluginSpec


class ComponentType(Enum):
    """Component type classifications."""

    CORE = "core"  # Always included (backend, frontend)
    INFRASTRUCTURE = "infra"  # Redis, workers - foundation for services to use


class SchedulerBackend(str, Enum):
    """Scheduler backend options for task persistence."""

    MEMORY = "memory"  # In-memory (no persistence, default)
    SQLITE = "sqlite"  # SQLite database (requires database component)
    POSTGRES = "postgres"  # PostgreSQL (future support)


# Core components that are always included in every project
CORE_COMPONENTS = ["backend", "frontend"]


@dataclass(kw_only=True)
class ComponentSpec(PluginSpec):
    """Component-flavoured PluginSpec — back-compat alias for pre-R2 callers.

    Subclasses ``PluginSpec`` and pins ``kind`` to ``COMPONENT`` by default.
    Legacy field names ``requires`` / ``recommends`` continue to work for
    *read* access via the property aliases on ``PluginSpec``; constructions
    in this file use the canonical ``required_components`` /
    ``recommended_components`` names. R2 of the plugin system refactor.

    ``kw_only=True`` is required: ``PluginSpec`` has a required ``kind`` field
    followed by defaulted fields, and overriding ``kind`` with a default in
    this subclass would otherwise violate the "required field after default"
    dataclass rule. Pre-R2 callers all used keyword construction (verified
    by AST scan), so no real call sites are affected.
    """

    kind: PluginKind = PluginKind.COMPONENT


# Component registry - single source of truth
COMPONENTS: dict[str, ComponentSpec] = {
    "backend": ComponentSpec(
        name="backend",
        type=ComponentType.CORE,
        description="FastAPI backend server",
        pyproject_deps=["fastapi==0.116.1", "uvicorn==0.35.0"],
        template_files=["app/components/backend/"],
        # backend is a CORE component; never cleaned up.
    ),
    "frontend": ComponentSpec(
        name="frontend",
        type=ComponentType.CORE,
        description="Flet frontend interface",
        pyproject_deps=["flet==0.28.3"],
        template_files=["app/components/frontend/"],
        # frontend is a CORE component; never cleaned up.
    ),
    "redis": ComponentSpec(
        name="redis",
        type=ComponentType.INFRASTRUCTURE,
        description="Redis cache and message broker",
        docker_services=["redis"],
        pyproject_deps=["redis==5.0.8"],
        files=FileManifest(
            primary=[
                "app/components/frontend/dashboard/cards/redis_card.py",
                "app/components/frontend/dashboard/modals/redis_modal.py",
            ],
        ),
    ),
    "worker": ComponentSpec(
        name="worker",
        type=ComponentType.INFRASTRUCTURE,
        description="Background task processing (arq, Dramatiq, or TaskIQ)",
        required_components=["redis"],  # Hard dependency
        pyproject_deps=["arq==0.25.0"],
        docker_services=["worker-system", "worker-load-test"],
        template_files=["app/components/worker/"],
        files=FileManifest(
            # Mirrors cleanup_components() lines 316-333 (worker NOT enabled).
            # task_history_section.py is intentionally NOT here — cleanup
            # leaves it. worker_taskiq.py IS here — cleanup removes it.
            primary=[
                "app/components/worker",
                "app/cli/load_test.py",
                "app/services/load_test.py",
                "app/services/load_test_models.py",
                "app/services/load_test_workloads.py",
                "tests/services/test_load_test_models.py",
                "tests/services/test_load_test_service.py",
                "tests/services/test_worker_health_registration.py",
                "app/components/backend/api/worker.py",
                "app/components/backend/api/worker_taskiq.py",
                "tests/api/test_worker_endpoints.py",
                "app/components/frontend/dashboard/cards/worker_card.py",
                "app/components/frontend/dashboard/modals/worker_modal.py",
            ],
        ),
    ),
    "scheduler": ComponentSpec(
        name="scheduler",
        type=ComponentType.INFRASTRUCTURE,
        description="Scheduled task execution infrastructure",
        pyproject_deps=["apscheduler==3.10.4"],
        docker_services=["scheduler"],
        template_files=["app/components/scheduler.py", "app/entrypoints/scheduler.py"],
        files=FileManifest(
            primary=[
                "app/entrypoints/scheduler.py",
                "app/components/scheduler",
                "tests/components/test_scheduler.py",
                "docs/components/scheduler.md",
                "app/components/backend/api/scheduler.py",
                "tests/api/test_scheduler_endpoints.py",
                "app/components/frontend/dashboard/cards/scheduler_card.py",
                "app/components/frontend/dashboard/modals/scheduler_modal.py",
                "tests/services/test_scheduled_task_manager.py",
            ],
            # scheduler persistence cleanup is option-driven
            # (scheduler_backend == MEMORY), not a simple AnswerKey toggle —
            # it stays inline in cleanup_components() for R1.
        ),
    ),
    "database": ComponentSpec(
        name="database",
        type=ComponentType.INFRASTRUCTURE,
        description="Database with SQLModel ORM (SQLite or PostgreSQL)",
        pyproject_deps=["sqlmodel>=0.0.14", "sqlalchemy>=2.0.0"],
        # Note: async driver (aiosqlite or asyncpg) selected based on database_type in copier.yml
        template_files=["app/core/db.py"],
        files=FileManifest(
            primary=[
                "app/core/db.py",
                "app/components/frontend/dashboard/cards/database_card.py",
                "app/components/frontend/dashboard/modals/database_modal.py",
            ],
        ),
    ),
    "ingress": ComponentSpec(
        name="ingress",
        type=ComponentType.INFRASTRUCTURE,
        description="Traefik reverse proxy and load balancer",
        docker_services=["traefik"],
        recommended_components=["backend"],
        files=FileManifest(
            primary=[
                "traefik",
                "app/components/frontend/dashboard/cards/ingress_card.py",
                "app/components/frontend/dashboard/modals/ingress_modal.py",
            ],
        ),
    ),
    "observability": ComponentSpec(
        name="observability",
        type=ComponentType.INFRASTRUCTURE,
        description="Logfire observability, tracing, and metrics",
        pyproject_deps=["logfire[fastapi,httpx]"],
        template_files=["app/components/backend/middleware/logfire_tracing.py"],
        files=FileManifest(
            primary=[
                "app/components/backend/middleware/logfire_tracing.py",
                "app/components/frontend/dashboard/cards/observability_card.py",
                "app/components/frontend/dashboard/modals/observability_modal.py",
            ],
        ),
    ),
}


def get_component(name: str) -> ComponentSpec:
    """Get component specification by name."""
    if name not in COMPONENTS:
        raise ValueError(f"Unknown component: {name}")
    return COMPONENTS[name]


def get_components_by_type(component_type: ComponentType) -> dict[str, ComponentSpec]:
    """Get all components of a specific type."""
    return {
        name: spec for name, spec in COMPONENTS.items() if spec.type == component_type
    }


def list_available_components() -> list[str]:
    """Get list of all available component names."""
    return list(COMPONENTS.keys())
