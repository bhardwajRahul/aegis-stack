"""
Constants for Aegis Stack CLI.

This module centralizes magic strings and configuration keys used throughout
the CLI to improve maintainability and reduce duplication.
"""


class ComponentNames:
    """Standard component names used throughout the CLI."""

    REDIS = "redis"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    DATABASE = "database"
    BACKEND = "backend"
    FRONTEND = "frontend"
    INGRESS = "ingress"

    # Ordered list for interactive selection
    INFRASTRUCTURE_ORDER = [REDIS, WORKER, SCHEDULER, DATABASE, INGRESS]


class StorageBackends:
    """Storage backend options used by scheduler and database."""

    MEMORY = "memory"
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class WorkerBackends:
    """Worker backend options for task processing."""

    ARQ = "arq"
    TASKIQ = "taskiq"

    ALL = [ARQ, TASKIQ]


class AIFrameworks:
    """AI framework options for the AI service."""

    PYDANTIC_AI = "pydantic-ai"
    LANGCHAIN = "langchain"

    ALL = [PYDANTIC_AI, LANGCHAIN]


class AIProviders:
    """AI provider options for the AI service."""

    # Provider identifiers
    PUBLIC = "public"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    MISTRAL = "mistral"
    COHERE = "cohere"
    OLLAMA = "ollama"

    # All valid providers (used for validation)
    ALL = {PUBLIC, OPENAI, ANTHROPIC, GOOGLE, GROQ, MISTRAL, COHERE, OLLAMA}

    # Default providers for bracket syntax (non-interactive)
    DEFAULT = [PUBLIC]

    # Default providers for interactive mode (free tier recommendations)
    INTERACTIVE_DEFAULTS = [GROQ, GOOGLE]

    # Provider display information: (id, display_name, description, pricing, is_recommended)
    PROVIDER_INFO: list[tuple[str, str, str, str, bool]] = [
        (OPENAI, "OpenAI", "GPT models", "Paid", False),
        (ANTHROPIC, "Anthropic", "Claude models", "Paid", False),
        (GOOGLE, "Google", "Gemini models", "Free tier", True),
        (GROQ, "Groq", "Fast inference", "Free tier", True),
        (MISTRAL, "Mistral", "Open models", "Mostly paid", False),
        (COHERE, "Cohere", "Enterprise focus", "Limited free", False),
        (OLLAMA, "Ollama", "Local inference", "Free (local)", True),
    ]


class OllamaMode:
    """Ollama deployment mode options."""

    HOST = "host"  # Connect to Ollama running on host machine
    DOCKER = "docker"  # Run Ollama in Docker container
    NONE = "none"  # No Ollama (using cloud provider)

    ALL = [HOST, DOCKER, NONE]

    # Default URLs for each mode
    HOST_URL = "http://host.docker.internal:11434"  # For Mac/Windows Docker
    DOCKER_URL = "http://ollama:11434"  # For Docker service


class AnswerKeys:
    """Keys in Copier .copier-answers.yml configuration."""

    # Component include flags
    SCHEDULER = "include_scheduler"
    WORKER = "include_worker"
    REDIS = "include_redis"
    DATABASE = "include_database"
    CACHE = "include_cache"
    INGRESS = "include_ingress"

    # Service include flags
    AUTH = "include_auth"
    AI = "include_ai"
    COMMS = "include_comms"

    # Service names (used for selection/lookup)
    SERVICE_AUTH = "auth"
    SERVICE_AI = "ai"
    SERVICE_COMMS = "comms"

    # Configuration values
    SCHEDULER_BACKEND = "scheduler_backend"
    SCHEDULER_WITH_PERSISTENCE = "scheduler_with_persistence"
    WORKER_BACKEND = "worker_backend"
    DATABASE_ENGINE = "database_engine"
    AI_FRAMEWORK = "ai_framework"
    AI_PROVIDERS = "ai_providers"
    AI_BACKEND = "ai_backend"
    AI_WITH_PERSISTENCE = "ai_with_persistence"
    AI_RAG = "ai_rag"
    AI_VOICE = "ai_voice"
    OLLAMA_MODE = "ollama_mode"
    PROJECT_SLUG = "project_slug"
    SRC_PATH = "_src_path"

    @classmethod
    def include_key(cls, name: str) -> str:
        """Generate include key for component/service name."""
        return f"include_{name}"


class Messages:
    """User-facing CLI messages."""

    # Section headers and separators
    SEPARATOR_WIDTH = 40
    SEPARATOR = "=" * SEPARATOR_WIDTH

    SECTION_COMPONENT_SELECTION = "Component Selection"
    SECTION_SERVICE_SELECTION = "Service Selection"
    SECTION_COMPONENT_REMOVAL = "Component Removal"
    SECTION_SERVICE_REMOVAL = "Service Removal Selection"
    SECTION_SCHEDULER_PERSISTENCE = "Scheduler Persistence"
    SECTION_DATABASE_ENGINE = "Database Engine"
    SECTION_AI_FRAMEWORK = "AI Framework Selection"
    SECTION_AI_BACKEND = "AI Conversation Persistence"
    SECTION_AI_PROVIDERS = "AI Provider Selection"

    # Git validation
    GIT_NOT_INITIALIZED = "Project is not in a git repository"
    GIT_REQUIRED_HINT = "Copier updates require git for change tracking"
    GIT_INIT_HINT = (
        "Projects created with 'aegis init' should have git initialized automatically"
    )
    GIT_MANUAL_INIT = (
        "If you created this project manually, run: "
        "git init && git add . && git commit -m 'Initial commit'"
    )

    # Copier project validation
    NOT_COPIER_PROJECT = "Project was not generated with Copier"

    # Component/service parsing
    EMPTY_COMPONENT_NAME = "Empty component name is not allowed"
    EMPTY_SERVICE_NAME = "Empty service name is not allowed"

    # Interactive mode
    INTERACTIVE_IGNORES_ARGS = "Warning: --interactive flag ignores component arguments"
    NO_COMPONENTS_SELECTED = "No components selected"
    NO_SERVICES_SELECTED = "No services selected"

    # Next steps messages
    NEXT_STEPS_HEADER = "Next steps:"
    NEXT_STEP_MAKE_CHECK = "   1. Run 'make check' to verify the update"
    NEXT_STEP_TEST = "   2. Test your application"
    NEXT_STEP_COMMIT = "   3. Commit the changes with: git add . && git commit"

    REVIEW_CHANGES_HEADER = "Review changes:"
    REVIEW_DOCKER_COMPOSE = "   git diff docker-compose.yml"
    REVIEW_PYPROJECT = "   git diff pyproject.toml"

    @classmethod
    def copier_only_command(cls, command_name: str) -> str:
        """Generate message for Copier-only command."""
        return f"The 'aegis {command_name}' command only works with Copier-generated projects."

    @classmethod
    def print_section_header(cls, title: str, newline_before: bool = False) -> None:
        """Print a section header with separator."""
        import typer

        if newline_before:
            typer.echo()
        typer.echo(title)
        typer.echo(cls.SEPARATOR)

    @classmethod
    def print_next_steps(cls) -> None:
        """Print standard next steps message."""
        import typer

        typer.echo(f"\n{cls.NEXT_STEPS_HEADER}")
        typer.echo(cls.NEXT_STEP_MAKE_CHECK)
        typer.echo(cls.NEXT_STEP_TEST)
        typer.echo(cls.NEXT_STEP_COMMIT)

    @classmethod
    def print_review_changes(cls) -> None:
        """Print standard review changes message."""
        import typer

        typer.echo(f"\n{cls.REVIEW_CHANGES_HEADER}")
        typer.echo(cls.REVIEW_DOCKER_COMPOSE)
        typer.echo(cls.REVIEW_PYPROJECT)
