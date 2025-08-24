"""
Template generation and context building for Aegis Stack projects.

This module handles the generation of cookiecutter context and manages
the template rendering process based on selected components.
"""

from pathlib import Path
from typing import Any

from .components import COMPONENTS


class TemplateGenerator:
    """Handles template context generation for cookiecutter."""

    def __init__(self, project_name: str, selected_components: list[str]):
        """
        Initialize template generator.

        Args:
            project_name: Name of the project being generated
            selected_components: List of component names to include
        """
        self.project_name = project_name
        self.project_slug = project_name.lower().replace(" ", "-").replace("_", "-")
        # Always include core components
        all_components = ["backend", "frontend"] + selected_components
        # Remove duplicates, preserve order
        self.components = list(dict.fromkeys(all_components))
        self.component_specs = {
            name: COMPONENTS[name] for name in self.components if name in COMPONENTS
        }

    def get_template_context(self) -> dict[str, Any]:
        """
        Generate cookiecutter context from components.

        Returns:
            Dictionary containing all template variables
        """
        # Store the originally selected components (without core)
        selected_only = [c for c in self.components if c not in ["backend", "frontend"]]

        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            # Component flags for template conditionals - cookiecutter needs yes/no
            "include_redis": "yes" if "redis" in self.components else "no",
            "include_worker": "yes" if "worker" in self.components else "no",
            "include_scheduler": "yes" if "scheduler" in self.components else "no",
            "include_database": "yes" if "database" in self.components else "no",
            # Derived flags for template logic
            "has_background_infrastructure": any(
                name in self.components for name in ["worker", "scheduler"]
            ),
            "needs_redis": "redis" in self.components,
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
        for component_name in self.components:
            if component_name in self.component_specs:
                spec = self.component_specs[component_name]
                if spec.pyproject_deps:
                    deps.extend(spec.pyproject_deps)
        return sorted(set(deps))  # Sort and deduplicate

    def get_template_files(self) -> list[str]:
        """
        Get list of template files that should be included.

        Returns:
            List of template file paths
        """
        files = []
        for component_name in self.components:
            if component_name in self.component_specs:
                spec = self.component_specs[component_name]
                if spec.template_files:
                    files.extend(spec.template_files)
        return list(dict.fromkeys(files))  # Preserve order, remove duplicates

    def get_entrypoints(self) -> list[str]:
        """
        Get list of entrypoints that will be created.

        Returns:
            List of entrypoint file paths
        """
        entrypoints = ["app/entrypoints/webserver.py"]  # Always included

        # Check component specs for actual entrypoint files
        for component_name in self.components:
            if component_name in self.component_specs:
                spec = self.component_specs[component_name]
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
        if "worker" not in self.components:
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
