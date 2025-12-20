"""
Template generation and context building for Aegis Stack projects.

This module handles the generation of cookiecutter context and manages
the template rendering process based on selected components.
"""

from pathlib import Path
from typing import Any

from ..config.defaults import DEFAULT_PYTHON_VERSION
from ..constants import (
    AIFrameworks,
    AnswerKeys,
    ComponentNames,
    StorageBackends,
    WorkerBackends,
)
from .ai_service_parser import is_ai_service_with_options, parse_ai_service_config
from .component_utils import (
    extract_base_component_name,
    extract_base_service_name,
    extract_engine_info,
)
from .components import COMPONENTS, CORE_COMPONENTS
from .services import SERVICES

# Service names for bracket syntax detection
SERVICE_AI = "ai"


class TemplateGenerator:
    """Handles template context generation for cookiecutter."""

    def __init__(
        self,
        project_name: str,
        selected_components: list[str],
        scheduler_backend: str = StorageBackends.MEMORY,
        selected_services: list[str] | None = None,
        python_version: str = DEFAULT_PYTHON_VERSION,
    ):
        """
        Initialize template generator.

        Args:
            project_name: Name of the project being generated
            selected_components: List of component names to include
            scheduler_backend: Scheduler backend: memory, sqlite, or postgres
            selected_services: List of service names to include
            python_version: Python version for generated project (default from pyproject.toml)
        """
        self.project_name = project_name
        self.project_slug = project_name.lower().replace(" ", "-").replace("_", "-")
        self.scheduler_backend = scheduler_backend
        self.selected_services = selected_services or []
        self.python_version = python_version

        # Always include core components
        all_components = CORE_COMPONENTS + selected_components

        # Add required components from selected services
        for service_name in self.selected_services:
            if service_name in SERVICES:
                service_spec = SERVICES[service_name]
                all_components.extend(service_spec.required_components)

        # Remove duplicates, preserve order
        self.components = list(dict.fromkeys(all_components))

        # Extract database engine from database[engine] format for template context
        self.database_engine = None
        for component in self.components:
            if extract_base_component_name(component) == ComponentNames.DATABASE:
                self.database_engine = extract_engine_info(component)
                if self.database_engine:
                    break

        # Extract scheduler backend from scheduler[backend] format or use passed param
        # If scheduler[backend] syntax is used, it overrides the passed parameter
        for component in self.components:
            if extract_base_component_name(component) == ComponentNames.SCHEDULER:
                backend = extract_engine_info(component)
                if backend:
                    self.scheduler_backend = backend
                    break

        # Extract worker backend from worker[backend] format
        self.worker_backend = WorkerBackends.ARQ  # Default to arq
        for component in self.components:
            if extract_base_component_name(component) == ComponentNames.WORKER:
                backend = extract_engine_info(component)
                if backend:
                    self.worker_backend = backend
                    break

        # Extract AI config from ai[framework, backend, providers, rag] format in services
        self.ai_backend = StorageBackends.MEMORY  # Default to memory
        self.ai_framework = AIFrameworks.PYDANTIC_AI  # Default to pydantic-ai
        self.ai_rag = False  # Default to no RAG
        user_specified_ai_backend = False

        for service in self.selected_services:
            if extract_base_service_name(service) == SERVICE_AI:
                if is_ai_service_with_options(service):
                    ai_config = parse_ai_service_config(service)
                    self.ai_backend = ai_config.backend
                    self.ai_framework = ai_config.framework
                    self.ai_rag = ai_config.rag_enabled
                    user_specified_ai_backend = True
                break

        # Auto-detect: if AI service selected AND database available AND no explicit backend,
        # use SQLite for persistence (analytics, conversation history, LLM tracking)
        if not user_specified_ai_backend:
            has_ai = any(
                extract_base_service_name(s) == SERVICE_AI
                for s in self.selected_services
            )
            has_database = any(
                extract_base_component_name(c) == ComponentNames.DATABASE
                for c in self.components
            )
            if has_ai and has_database:
                self.ai_backend = StorageBackends.SQLITE

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
        has_database = any(
            extract_base_component_name(c) == ComponentNames.DATABASE
            for c in self.components
        )

        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "python_version": self.python_version,
            # Component flags for template conditionals - cookiecutter needs yes/no
            AnswerKeys.REDIS: "yes"
            if ComponentNames.REDIS in self.components
            else "no",
            AnswerKeys.WORKER: "yes"
            if any(c.startswith(ComponentNames.WORKER) for c in self.components)
            else "no",
            AnswerKeys.SCHEDULER: "yes"
            if any(c.startswith(ComponentNames.SCHEDULER) for c in self.components)
            else "no",
            AnswerKeys.DATABASE: "yes" if has_database else "no",
            # Database engine selection
            "database_engine": self.database_engine or StorageBackends.SQLITE,
            # Scheduler backend selection
            AnswerKeys.SCHEDULER_BACKEND: self.scheduler_backend,
            # Worker backend selection
            AnswerKeys.WORKER_BACKEND: self.worker_backend,
            # Legacy scheduler persistence flag for backwards compatibility
            AnswerKeys.SCHEDULER_WITH_PERSISTENCE: (
                "yes" if self.scheduler_backend != StorageBackends.MEMORY else "no"
            ),
            # Derived flags for template logic
            "has_background_infrastructure": any(
                c.startswith(ComponentNames.WORKER)
                or c.startswith(ComponentNames.SCHEDULER)
                for c in self.components
            ),
            "needs_redis": ComponentNames.REDIS in self.components,
            # Service flags for template conditionals
            # Use base name extraction to handle bracket syntax (e.g., ai[langchain, sqlite])
            AnswerKeys.AUTH: "yes"
            if any(
                extract_base_service_name(s) == AnswerKeys.SERVICE_AUTH
                for s in self.selected_services
            )
            else "no",
            AnswerKeys.AI: "yes"
            if any(
                extract_base_service_name(s) == AnswerKeys.SERVICE_AI
                for s in self.selected_services
            )
            else "no",
            AnswerKeys.COMMS: "yes"
            if any(
                extract_base_service_name(s) == AnswerKeys.SERVICE_COMMS
                for s in self.selected_services
            )
            else "no",
            # AI backend selection for conversation persistence
            AnswerKeys.AI_BACKEND: self.ai_backend,
            # AI persistence flag for backwards compatibility with template conditionals
            AnswerKeys.AI_WITH_PERSISTENCE: (
                "yes" if self.ai_backend != StorageBackends.MEMORY else "no"
            ),
            # AI framework selection (pydantic-ai or langchain)
            AnswerKeys.AI_FRAMEWORK: self._get_ai_framework(),
            # AI provider selection for dynamic dependency generation
            AnswerKeys.AI_PROVIDERS: self._get_ai_providers_string(),
            # AI RAG (Retrieval-Augmented Generation) selection
            AnswerKeys.AI_RAG: "yes" if self.ai_rag else "no",
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
            base_name = extract_base_component_name(component_name)
            if base_name in self.component_specs:
                spec = self.component_specs[base_name]
                if spec.pyproject_deps:
                    # Handle worker backend-specific dependencies
                    if base_name == ComponentNames.WORKER:
                        if self.worker_backend == WorkerBackends.TASKIQ:
                            deps.extend(["taskiq>=0.11.11", "taskiq-redis>=1.0.2"])
                        else:
                            deps.extend(spec.pyproject_deps)  # arq deps from spec
                    else:
                        deps.extend(spec.pyproject_deps)

        # Collect service dependencies
        for service_name in self.selected_services:
            # Extract base service name for bracket syntax (e.g., "ai[langchain]" → "ai")
            base_service_name = extract_base_service_name(service_name)
            if base_service_name in SERVICES:
                service_spec = SERVICES[base_service_name]
                if service_spec.pyproject_deps:
                    # Process service dependencies with dynamic substitution
                    for dep in service_spec.pyproject_deps:
                        if (
                            base_service_name == AnswerKeys.SERVICE_AI
                            and "{AI_FRAMEWORK_DEPS}" in dep
                        ):
                            # Substitute AI framework + provider deps dynamically
                            ai_deps = self._get_ai_framework_deps()
                            deps.extend(ai_deps)
                        else:
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
        for service in self.selected_services:
            base_service = extract_base_service_name(service)
            if base_service in SERVICES:
                service_spec = SERVICES[base_service]
                if service_spec.template_files:
                    files.extend(service_spec.template_files)

        return list(dict.fromkeys(files))  # Preserve order, remove duplicates

    def _get_ai_providers_string(self) -> str:
        """
        Get AI providers as comma-separated string for pydantic-ai-slim dependency.

        Returns:
            Comma-separated string of provider names (e.g., "openai,anthropic,google")
        """
        # Check if AI service is selected (handle bracket syntax)
        has_ai = any(
            extract_base_service_name(s) == AnswerKeys.SERVICE_AI
            for s in self.selected_services
        )
        if not has_ai:
            return "openai"  # Default for PUBLIC provider

        # Import here to avoid circular imports
        from ..cli.interactive import get_ai_provider_selection

        providers = get_ai_provider_selection("ai")
        return ",".join(providers)

    def _get_ai_framework(self) -> str:
        """
        Get AI framework selection (pydantic-ai or langchain).

        Returns:
            Framework name string
        """
        # Check if AI service is selected (handle bracket syntax)
        has_ai = any(
            extract_base_service_name(s) == AnswerKeys.SERVICE_AI
            for s in self.selected_services
        )
        if not has_ai:
            return AIFrameworks.PYDANTIC_AI  # Default

        # Import here to avoid circular imports
        from ..cli.interactive import get_ai_framework_selection

        return get_ai_framework_selection("ai")

    def _get_ai_framework_deps(self) -> list[str]:
        """
        Get AI framework-specific dependencies based on framework and provider selection.

        Returns:
            List of Python package dependency strings
        """
        framework = self._get_ai_framework()
        providers_str = self._get_ai_providers_string()
        providers = providers_str.split(",")

        if framework == AIFrameworks.PYDANTIC_AI:
            # PydanticAI uses a single package with extras
            # Map provider names to pydantic-ai-slim extras
            # Providers using OpenAI-compatible APIs map to "openai" extra
            pydantic_extra_mapping = {
                "public": "openai",  # LLM7.io uses OpenAI-compatible API
                "openrouter": "openai",  # OpenRouter uses OpenAI-compatible API
                # Future OpenAI-compatible providers go here:
                # "together": "openai",
                # "fireworks": "openai",
            }

            pydantic_extras = []
            for provider in providers:
                provider = provider.strip()
                # Map to the correct extra, or use provider name directly
                extra = pydantic_extra_mapping.get(provider, provider)
                if extra not in pydantic_extras:
                    pydantic_extras.append(extra)

            extras_str = ",".join(pydantic_extras) if pydantic_extras else "openai"
            return [
                f"pydantic-ai-slim[{extras_str}]>=1.0.10",
                "httpx>=0.27.0",  # For API providers
            ]
        else:
            # LangChain uses separate packages per provider
            deps = ["langchain-core>=1.1.0"]

            # Map provider names to LangChain packages
            langchain_packages = {
                "openai": "langchain-openai>=1.1.0",
                "anthropic": "langchain-anthropic>=1.2.0",
                "google": "langchain-google-genai>=4.0.0",
                "groq": "langchain-groq>=1.1.0",
                "mistral": "langchain-mistralai>=1.1.0",
                "cohere": "langchain-cohere>=0.5.0",
            }

            for provider in providers:
                provider = provider.strip()
                if provider in langchain_packages:
                    deps.append(langchain_packages[provider])
                elif provider == "public" and "langchain-openai>=1.1.0" not in deps:
                    # Public provider uses OpenAI-compatible endpoint
                    deps.append("langchain-openai>=1.1.0")

            return deps

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
        if not any(c.startswith(ComponentNames.WORKER) for c in self.components):
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
                if queue_file.stem == "__init__":
                    continue
                # Filter based on worker backend
                # _taskiq.py files are for taskiq, others are for arq
                is_taskiq_file = queue_file.stem.endswith("_taskiq")
                if self.worker_backend == WorkerBackends.TASKIQ:
                    # Show taskiq files without the _taskiq suffix (how they'll appear after rename)
                    if is_taskiq_file:
                        final_name = queue_file.name.replace("_taskiq.py", ".py")
                        queues.append(f"app/components/worker/queues/{final_name}")
                else:
                    # Show arq files (non-taskiq files)
                    if not is_taskiq_file:
                        queues.append(f"app/components/worker/queues/{queue_file.name}")

        return sorted(queues)
