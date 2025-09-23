"""
Template generation and context building for Aegis Stack projects.

This module handles the generation of cookiecutter context and manages
the template rendering process based on selected components.
"""

from pathlib import Path
from typing import Any

from .component_utils import extract_base_component_name, extract_engine_info
from .components import COMPONENTS, CORE_COMPONENTS
from .services import SERVICES


class TemplateGenerator:
    """Handles template context generation for cookiecutter."""

    def __init__(
        self,
        project_name: str,
        selected_components: list[str],
        scheduler_backend: str = "memory",
        selected_services: list[str] | None = None,
    ):
        """
        Initialize template generator.

        Args:
            project_name: Name of the project being generated
            selected_components: List of component names to include
            scheduler_backend: Scheduler backend: "memory", "sqlite", "postgres"
            selected_services: List of service names to include
        """
        self.project_name = project_name
        self.project_slug = project_name.lower().replace(" ", "-").replace("_", "-")
        self.scheduler_backend = scheduler_backend
        self.selected_services = selected_services or []

        # Always include core components
        all_components = CORE_COMPONENTS + selected_components
        # Remove duplicates, preserve order
        self.components = list(dict.fromkeys(all_components))

        # Extract database engine from database[engine] format for template context
        self.database_engine = None
        for component in self.components:
            if extract_base_component_name(component) == "database":
                self.database_engine = extract_engine_info(component)
                if self.database_engine:
                    break

        # Extract scheduler backend from scheduler[backend] format or use passed param
        # If scheduler[backend] syntax is used, it overrides the passed parameter
        for component in self.components:
            if extract_base_component_name(component) == "scheduler":
                backend = extract_engine_info(component)
                if backend:
                    self.scheduler_backend = backend
                    break

        # Build component specs using base names
        self.component_specs = {}
        for name in self.components:
            base_name = extract_base_component_name(name)
            if base_name in COMPONENTS:
                self.component_specs[base_name] = COMPONENTS[base_name]

    def get_template_context(self) -> dict[str, Any]:
        """
        Generate cookiecutter context from components.

        Returns:
            Dictionary containing all template variables
        """
        # Store the originally selected components (without core)
        selected_only = [c for c in self.components if c not in CORE_COMPONENTS]

        # Check for components using base names
        has_database = any(c.startswith("database") for c in self.components)

        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            # Component flags for template conditionals - cookiecutter needs yes/no
            "include_redis": "yes" if "redis" in self.components else "no",
            "include_worker": "yes" if "worker" in self.components else "no",
            "include_scheduler": "yes"
            if any(c.startswith("scheduler") for c in self.components)
            else "no",
            "include_database": "yes" if has_database else "no",
            # Database engine selection
            "database_engine": self.database_engine or "sqlite",
            # Scheduler backend selection
            "scheduler_backend": self.scheduler_backend,
            # Legacy scheduler persistence flag for backwards compatibility
            "scheduler_with_persistence": (
                "yes" if self.scheduler_backend != "memory" else "no"
            ),
            # Derived flags for template logic
            "has_background_infrastructure": any(
                name in self.components for name in ["worker", "scheduler"]
            ),
            "needs_redis": "redis" in self.components,
            # Service flags for template conditionals
            "include_auth": "yes" if "auth" in self.selected_services else "no",
            "include_ai": "yes" if "ai" in self.selected_services else "no",
            # AI provider selection for dynamic dependency generation
            "ai_providers": self._get_ai_providers_string(),
            # Dependency lists for templates
            "selected_components": selected_only,  # Original selection for context
            "docker_services": self._get_docker_services(),
            "pyproject_dependencies": self._get_pyproject_deps(),
        }

    def _get_docker_services(self) -> list[str]:
        """
        Collect all docker services needed.

        Returns:
            List of docker service names
        """
        services = []
        for component_name in self.components:
            if component_name in self.component_specs:
                spec = self.component_specs[component_name]
                if spec.docker_services:
                    services.extend(spec.docker_services)
        return list(dict.fromkeys(services))  # Preserve order, remove duplicates

    def _get_pyproject_deps(self) -> list[str]:
        """
        Collect all Python dependencies.

        Returns:
            Sorted list of Python package dependencies
        """
        deps = []
        # Collect component dependencies
        for component_name in self.components:
            if component_name in self.component_specs:
                spec = self.component_specs[component_name]
                if spec.pyproject_deps:
                    deps.extend(spec.pyproject_deps)

        # Collect service dependencies
        for service_name in self.selected_services:
            if service_name in SERVICES:
                service_spec = SERVICES[service_name]
                if service_spec.pyproject_deps:
                    # Process service dependencies with dynamic substitution
                    for dep in service_spec.pyproject_deps:
                        if service_name == "ai" and "{AI_PROVIDERS}" in dep:
                            # Substitute AI providers dynamically
                            providers = self._get_ai_providers_string()
                            dep = dep.replace("{AI_PROVIDERS}", providers)
                        deps.append(dep)

        return sorted(set(deps))  # Sort and deduplicate

    def get_template_files(self) -> list[str]:
        """
        Get list of template files that should be included.

        Returns:
            List of template file paths
        """
        files = []
        # Collect component template files
        for component_name in self.components:
            base_name = extract_base_component_name(component_name)
            if base_name in self.component_specs:
                spec = self.component_specs[base_name]
                if spec.template_files:
                    files.extend(spec.template_files)

        # Collect service template files
        for service_name in self.selected_services:
            if service_name in SERVICES:
                service_spec = SERVICES[service_name]
                if service_spec.template_files:
                    files.extend(service_spec.template_files)

        return list(dict.fromkeys(files))  # Preserve order, remove duplicates

    def _get_ai_providers_string(self) -> str:
        """
        Get AI providers as comma-separated string for pydantic-ai-slim dependency.

        Returns:
            Comma-separated string of provider names (e.g., "openai,anthropic,google")
        """
        if "ai" not in self.selected_services:
            return "groq,google"  # Default providers

        # Import here to avoid circular imports
        from ..cli.interactive import get_ai_provider_selection

        providers = get_ai_provider_selection("ai")
        return ",".join(providers)

    def get_entrypoints(self) -> list[str]:
        """
        Get list of entrypoints that will be created.

        Returns:
            List of entrypoint file paths
        """
        entrypoints = ["app/entrypoints/webserver.py"]  # Always included

        # Check component specs for actual entrypoint files
        for component_name in self.components:
            base_name = extract_base_component_name(component_name)
            if base_name in self.component_specs:
                spec = self.component_specs[base_name]
                if spec.template_files:
                    for template_file in spec.template_files:
                        if (
                            template_file.startswith("app/entrypoints/")
                            and template_file not in entrypoints
                        ):
                            entrypoints.append(template_file)

        return entrypoints

    def get_worker_queues(self) -> list[str]:
        """
        Get list of worker queue files that will be created.

        Returns:
            List of worker queue file paths
        """
        queues: list[str] = []

        # Only check if worker component is included
        if not any(c.startswith("worker") for c in self.components):
            return queues

        # Discover queue files from the template directory
        template_root = (
            Path(__file__).parent.parent / "templates" / "cookiecutter-aegis-project"
        )
        worker_queues_dir = (
            template_root
            / "{{cookiecutter.project_slug}}"
            / "app"
            / "components"
            / "worker"
            / "queues"
        )

        if worker_queues_dir.exists():
            for queue_file in worker_queues_dir.glob("*.py"):
                if queue_file.stem != "__init__":
                    queues.append(f"app/components/worker/queues/{queue_file.name}")

        return sorted(queues)
