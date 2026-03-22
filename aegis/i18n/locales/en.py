"""English locale — canonical message definitions for Aegis Stack CLI."""

MESSAGES: dict[str, str] = {
    # ── Validation ─────────────────────────────────────────────────────
    "validation.invalid_name": (
        "Invalid project name. Only letters, numbers, hyphens, "
        "and underscores are allowed."
    ),
    "validation.reserved_name": "'{name}' is a reserved name.",
    "validation.name_too_long": (
        "Project name too long. Maximum 50 characters allowed."
    ),
    "validation.invalid_python": (
        "Invalid Python version '{version}'. Must be one of: {supported}"
    ),
    # ── Init command ───────────────────────────────────────────────────
    "init.title": "Aegis Stack Project Initialization",
    "init.location": "Location:",
    "init.template_version": "Template Version:",
    "init.dir_exists": "Directory '{path}' already exists",
    "init.dir_exists_hint": "Use --force to overwrite or choose a different name",
    "init.overwriting": "Overwriting existing directory: {path}",
    "init.services_require": "Services require components: {components}",
    "init.compat_errors": "Service-component compatibility errors:",
    "init.suggestion_add": (
        "Suggestion: Add missing components --components {components}"
    ),
    "init.suggestion_remove": (
        "Or remove --components to let services auto-add dependencies."
    ),
    "init.suggestion_interactive": (
        "Alternatively, use interactive mode to auto-add service dependencies."
    ),
    "init.auto_detected_scheduler": (
        "Auto-detected: Scheduler with {backend} persistence"
    ),
    "init.auto_added_deps": "Auto-added dependencies: {deps}",
    "init.auto_added_by_services": "Auto-added by services:",
    "init.required_by": "required by {services}",
    "init.config_title": "Project Configuration",
    "init.config_name": "Name:",
    "init.config_core": "Core:",
    "init.config_infra": "Infrastructure:",
    "init.config_services": "Services:",
    "init.component_files": "Component Files:",
    "init.entrypoints": "Entrypoints:",
    "init.worker_queues": "Worker Queues:",
    "init.dependencies": "Dependencies to be installed:",
    "init.confirm_create": "Create this project?",
    "init.cancelled": "Project creation cancelled",
    "init.removing_dir": "Removing existing directory: {path}",
    "init.creating": "Creating project: {name}",
    "init.error": "Error creating project: {error}",
    # ── Interactive: section headers ───────────────────────────────────
    "interactive.component_selection": "Component Selection",
    "interactive.service_selection": "Service Selection",
    "interactive.core_included": (
        "Core components ({components}) included automatically"
    ),
    "interactive.infra_header": "Infrastructure Components:",
    "interactive.services_intro": (
        "Services provide business logic functionality for your application."
    ),
    # ── Component descriptions ──────────────────────────────────────────
    "component.backend": "FastAPI backend server",
    "component.frontend": "Flet frontend interface",
    "component.redis": "Redis cache and message broker",
    "component.worker": "Background task processing (arq, Dramatiq, or TaskIQ)",
    "component.scheduler": "Scheduled task execution infrastructure",
    "component.database": "Database with SQLModel ORM (SQLite or PostgreSQL)",
    "component.ingress": "Traefik reverse proxy and load balancer",
    "component.observability": "Logfire observability, tracing, and metrics",
    # ── Service descriptions ────────────────────────────────────────────
    "service.auth": "User authentication and authorization with JWT tokens",
    "service.ai": "AI chatbot service with multi-framework support",
    "service.comms": "Communications service with email, SMS and voice",
    # ── Interactive: component prompts ─────────────────────────────────
    "interactive.add_prompt": "Add {description}?",
    "interactive.add_with_redis": "Add {description}? (will auto-add Redis)",
    "interactive.worker_configured": "Worker with {backend} backend configured",
    # ── Interactive: scheduler ─────────────────────────────────────────
    "interactive.scheduler_persistence": "Scheduler Persistence:",
    "interactive.persist_prompt": (
        "Do you want to persist scheduled jobs? "
        "(Enables job history, recovery after restarts)"
    ),
    "interactive.scheduler_db_configured": ("Scheduler + {engine} database configured"),
    "interactive.bonus_backup": "Bonus: Adding database backup job",
    "interactive.backup_desc": (
        "Scheduled daily database backup job included (runs at 2 AM)"
    ),
    # ── Interactive: database engine ───────────────────────────────────
    "interactive.db_engine_label": "{context} Database Engine:",
    "interactive.db_select": "Select database engine:",
    "interactive.db_sqlite": "SQLite - Simple, file-based (good for development)",
    "interactive.db_postgres": (
        "PostgreSQL - Production-ready, multi-container support"
    ),
    "interactive.db_reuse": "Using previously selected database: {engine}",
    # ── Interactive: worker backend ────────────────────────────────────
    "interactive.worker_label": "Worker Backend:",
    "interactive.worker_select": "Select worker backend:",
    "interactive.worker_arq": "arq - Async, lightweight (default)",
    "interactive.worker_dramatiq": (
        "Dramatiq - Process-based, ideal for CPU-bound work"
    ),
    "interactive.worker_taskiq": (
        "TaskIQ - Async, framework-style with per-queue brokers"
    ),
    # ── Interactive: auth ──────────────────────────────────────────────
    "interactive.auth_header": "Authentication Services:",
    "interactive.auth_level_label": "Authentication Level:",
    "interactive.auth_select": "What type of authentication?",
    "interactive.auth_basic": "Basic - Email/password login",
    "interactive.auth_rbac": "With Roles - + role-based access control (experimental)",
    "interactive.auth_org": "With Organizations - + multi-tenant support (experimental)",
    "interactive.auth_selected": "Selected auth level: {level}",
    "interactive.auth_db_required": "Database Required:",
    "interactive.auth_db_reason": (
        "Authentication requires a database for user storage"
    ),
    "interactive.auth_db_details": "(user accounts, sessions, JWT tokens)",
    "interactive.auth_db_already": "Database component already selected",
    "interactive.auth_db_confirm": "Continue and add database component?",
    "interactive.auth_cancelled": "Authentication service cancelled",
    "interactive.auth_db_configured": "Authentication + Database configured",
    # ── Interactive: AI service ────────────────────────────────────────
    "interactive.ai_header": "AI & Machine Learning Services:",
    "interactive.ai_framework_label": "AI Framework Selection:",
    "interactive.ai_framework_intro": "Choose your AI framework:",
    "interactive.ai_pydanticai": (
        "PydanticAI - Type-safe, Pythonic AI framework (recommended)"
    ),
    "interactive.ai_langchain": (
        "LangChain - Popular framework with extensive integrations"
    ),
    "interactive.ai_use_pydanticai": "Use PydanticAI? (recommended)",
    "interactive.ai_selected_framework": "Selected framework: {framework}",
    "interactive.ai_tracking_context": "AI Usage Tracking",
    "interactive.ai_tracking_label": "LLM Usage Tracking:",
    "interactive.ai_tracking_prompt": (
        "Enable usage tracking? (token counts, costs, conversation history)"
    ),
    "interactive.ai_sync_label": "LLM Catalog Sync:",
    "interactive.ai_sync_desc": (
        "Syncing fetches latest model data from OpenRouter/LiteLLM APIs"
    ),
    "interactive.ai_sync_time": (
        "This requires network access and takes ~30-60 seconds"
    ),
    "interactive.ai_sync_prompt": ("Sync LLM catalog during project generation?"),
    "interactive.ai_sync_will": ("LLM catalog will be synced after project generation"),
    "interactive.ai_sync_skipped": (
        "LLM sync skipped - static fixture data will be available"
    ),
    "interactive.ai_provider_label": "AI Provider Selection:",
    "interactive.ai_provider_intro": (
        "Choose AI providers to include (multiple selection supported)"
    ),
    "interactive.ai_provider_options": "Provider Options:",
    "interactive.ai_provider_recommended": "(Recommended)",
    "interactive.ai_provider.openai": "OpenAI - GPT models (Paid)",
    "interactive.ai_provider.anthropic": "Anthropic - Claude models (Paid)",
    "interactive.ai_provider.google": "Google - Gemini models (Free tier)",
    "interactive.ai_provider.groq": "Groq - Fast inference (Free tier)",
    "interactive.ai_provider.mistral": "Mistral - Open models (Mostly paid)",
    "interactive.ai_provider.cohere": "Cohere - Enterprise focus (Limited free)",
    "interactive.ai_provider.ollama": "Ollama - Local inference (Free)",
    "interactive.ai_no_providers": (
        "No providers selected, adding recommended defaults..."
    ),
    "interactive.ai_selected_providers": "Selected providers: {providers}",
    "interactive.ai_deps_optimized": (
        "Dependencies will be optimized for your selection"
    ),
    "interactive.ai_ollama_label": "Ollama Deployment Mode:",
    "interactive.ai_ollama_intro": "How do you want to run Ollama?",
    "interactive.ai_ollama_host": (
        "Host - Connect to Ollama running on your machine (Mac/Windows)"
    ),
    "interactive.ai_ollama_docker": (
        "Docker - Run Ollama in a Docker container (Linux/Deploy)"
    ),
    "interactive.ai_ollama_host_prompt": (
        "Connect to host Ollama? (recommended for Mac/Windows)"
    ),
    "interactive.ai_ollama_host_ok": (
        "Ollama will connect to host.docker.internal:11434"
    ),
    "interactive.ai_ollama_host_hint": ("Make sure Ollama is running: ollama serve"),
    "interactive.ai_ollama_docker_ok": (
        "Ollama service will be added to docker-compose.yml"
    ),
    "interactive.ai_ollama_docker_hint": (
        "Note: First startup may take time to download models"
    ),
    "interactive.ai_rag_label": "RAG (Retrieval-Augmented Generation):",
    "interactive.ai_rag_warning": (
        "Warning: RAG requires Python <3.14 (chromadb/onnxruntime limitation)"
    ),
    "interactive.ai_rag_compat_note": (
        "Enabling RAG will generate a project requiring Python 3.11-3.13"
    ),
    "interactive.ai_rag_compat_prompt": (
        "Enable RAG despite Python 3.14 incompatibility?"
    ),
    "interactive.ai_rag_prompt": (
        "Enable RAG for document indexing and semantic search?"
    ),
    "interactive.ai_rag_enabled": "RAG enabled with ChromaDB vector store",
    "interactive.ai_voice_label": "Voice (Text-to-Speech & Speech-to-Text):",
    "interactive.ai_voice_prompt": (
        "Enable voice capabilities? (TTS and STT for voice interactions)"
    ),
    "interactive.ai_voice_enabled": "Voice enabled with TTS and STT support",
    "interactive.ai_db_already": ("Database already selected - usage tracking enabled"),
    "interactive.ai_db_added": ("Database ({backend}) added for usage tracking"),
    "interactive.ai_configured": "AI service configured",
    # ── Shared: validation ──────────────────────────────────────────────
    "shared.not_copier_project": ("Project at {path} was not generated with Copier."),
    "shared.copier_only": (
        "The 'aegis {command}' command only works with Copier-generated projects."
    ),
    "shared.regenerate_hint": (
        "To add components, regenerate the project with the new components included."
    ),
    "shared.git_not_initialized": "Project is not in a git repository",
    "shared.git_required": "Copier updates require git for change tracking",
    "shared.git_init_hint": (
        "Projects created with 'aegis init' should have git initialized automatically"
    ),
    "shared.git_manual_init": (
        "If you created this project manually, run: "
        "git init && git add . && git commit -m 'Initial commit'"
    ),
    "shared.empty_component": "Empty component name is not allowed",
    "shared.empty_service": "Empty service name is not allowed",
    # ── Shared: next steps / review ──────────────────────────────────
    "shared.next_steps": "Next steps:",
    "shared.next_make_check": "   1. Run 'make check' to verify the update",
    "shared.next_test": "   2. Test your application",
    "shared.next_commit": "   3. Commit the changes with: git add . && git commit",
    "shared.review_header": "Review changes:",
    "shared.review_docker": "   git diff docker-compose.yml",
    "shared.review_pyproject": "   git diff pyproject.toml",
    "shared.operation_cancelled": "Operation cancelled",
    "shared.interactive_ignores_args": (
        "Warning: --interactive flag ignores component arguments"
    ),
    "shared.no_components_selected": "No components selected",
    "shared.no_services_selected": "No services selected",
    # ── Add command ──────────────────────────────────────────────────
    "add.title": "Aegis Stack - Add Components",
    "add.project": "Project: {path}",
    "add.error_no_args": (
        "Error: components argument is required (or use --interactive)"
    ),
    "add.usage_hint": "Usage: aegis add scheduler,worker",
    "add.interactive_hint": "Or: aegis add --interactive",
    "add.auto_added_deps": "Auto-added dependencies: {deps}",
    "add.validation_failed": "Component validation failed: {error}",
    "add.load_config_failed": "Failed to load project configuration: {error}",
    "add.already_enabled": "Already enabled: {components}",
    "add.all_enabled": "All requested components are already enabled!",
    "add.components_to_add": "Components to add:",
    "add.scheduler_backend": "Scheduler backend: {backend}",
    "add.confirm": "Add these components?",
    "add.updating": "Updating project...",
    "add.adding": "Adding {component}...",
    "add.added_files": "Added {count} files",
    "add.skipped_files": "Skipped {count} existing files",
    "add.success": "Components added successfully!",
    "add.failed_component": "Failed to add {component}: {error}",
    "add.failed": "Failed to add components: {error}",
    "add.invalid_format": "Invalid component format: {error}",
    "add.bracket_override": (
        "Bracket syntax 'scheduler[{engine}]' overrides --backend {backend}"
    ),
    "add.invalid_scheduler_backend": ("Invalid scheduler backend: '{backend}'"),
    "add.valid_backends": "Valid options: {options}",
    "add.postgres_coming": "Note: PostgreSQL support coming in future release",
    "add.auto_added_db": ("Auto-added database component for scheduler persistence"),
    # ── Remove command ────────────────────────────────────────────────
    "remove.title": "Aegis Stack - Remove Components",
    "remove.project": "Project: {path}",
    "remove.error_no_args": (
        "Error: components argument is required (or use --interactive)"
    ),
    "remove.usage_hint": "Usage: aegis remove scheduler,worker",
    "remove.interactive_hint": "Or: aegis remove --interactive",
    "remove.no_selected": "No components selected for removal",
    "remove.validation_failed": "Component validation failed: {error}",
    "remove.load_config_failed": "Failed to load project configuration: {error}",
    "remove.cannot_remove_core": "Cannot remove core component: {component}",
    "remove.not_enabled": "Not enabled: {components}",
    "remove.nothing_to_remove": "No components to remove!",
    "remove.auto_remove_redis": (
        "Auto-removing redis (no standalone functionality, only used by worker)"
    ),
    "remove.scheduler_persistence_warn": "IMPORTANT: Scheduler Persistence Warning",
    "remove.scheduler_persistence_detail": (
        "Your scheduler uses SQLite for job persistence."
    ),
    "remove.scheduler_db_remains": (
        "The database file at data/scheduler.db will remain."
    ),
    "remove.scheduler_keep_hint": (
        "To keep your job history: Leave the database component"
    ),
    "remove.scheduler_remove_hint": (
        "To remove all data: Also remove the database component"
    ),
    "remove.components_to_remove": "Components to remove:",
    "remove.warning_delete": (
        "WARNING: This will DELETE component files from your project!"
    ),
    "remove.commit_hint": "Make sure you have committed your changes to git.",
    "remove.confirm": "Remove these components?",
    "remove.removing_all": "Removing components...",
    "remove.removing": "Removing {component}...",
    "remove.removed_files": "Removed {count} files",
    "remove.failed_component": "Failed to remove {component}: {error}",
    "remove.success": "Components removed successfully!",
    "remove.failed": "Failed to remove components: {error}",
    # ── Manual updater ─────────────────────────────────────────────────
    "updater.processing_files": "Processing {count} component files...",
    "updater.updating_shared": "Updating shared template files...",
    "updater.running_postgen": "Running post-generation tasks...",
    "updater.deps_synced": "Dependencies synced (uv sync)",
    "updater.code_formatted": "Code formatted (make fix)",
    # ── Project map ──────────────────────────────────────────────────
    "projectmap.new": "NEW",
    # ── Post-generation: setup tasks ──────────────────────────────────
    "postgen.setup_start": "Setting up your project environment...",
    "postgen.deps_installing": "Installing dependencies with uv...",
    "postgen.deps_success": "Dependencies installed successfully",
    "postgen.deps_failed": "Project generation failed: dependency installation failed",
    "postgen.deps_failed_detail": (
        "The generated project files remain in place, but the project is not usable."
    ),
    "postgen.deps_failed_hint": (
        "Fix the dependency issue (check Python version compatibility) and try again."
    ),
    "postgen.deps_warn_failed": "Warning: Dependency installation failed",
    "postgen.deps_manual": "Run 'uv sync' manually after project creation",
    "postgen.deps_timeout": (
        "Warning: Dependency installation timeout - run 'uv sync' manually"
    ),
    "postgen.deps_uv_missing": "Warning: uv not found in PATH",
    "postgen.deps_uv_install": "Install uv first: https://github.com/astral-sh/uv",
    "postgen.deps_warn_error": "Warning: Dependency installation failed: {error}",
    "postgen.env_setup": "Setting up environment configuration...",
    "postgen.env_created": "Environment file created from .env.example",
    "postgen.env_exists": "Environment file already exists",
    "postgen.env_missing": "Warning: No .env.example file found",
    "postgen.env_error": "Warning: Environment setup failed: {error}",
    "postgen.env_manual": "Copy .env.example to .env manually",
    # ── Post-generation: database/migrations ────────────────────────────
    "postgen.db_setup": "Setting up database schema...",
    "postgen.db_success": "Database tables created successfully",
    "postgen.db_alembic_missing": "Warning: Alembic config file not found at {path}",
    "postgen.db_alembic_hint": (
        "Skipping database migration. Please ensure the config file exists "
        "and run 'alembic upgrade head' manually."
    ),
    "postgen.db_failed": "Warning: Database migration setup failed",
    "postgen.db_manual": "Run 'alembic upgrade head' manually after project creation",
    "postgen.db_timeout": (
        "Warning: Migration setup timeout - run 'alembic upgrade head' manually"
    ),
    "postgen.db_error": "Warning: Migration setup failed: {error}",
    # ── Post-generation: LLM fixtures/sync ────────────────────────────
    "postgen.llm_seeding": "Seeding LLM fixtures...",
    "postgen.llm_seed_success": "LLM fixtures seeded successfully",
    "postgen.llm_seed_failed": "Warning: LLM fixture seeding failed",
    "postgen.llm_seed_manual": (
        "You can seed fixtures manually by running the fixture loader"
    ),
    "postgen.llm_seed_timeout": "Warning: LLM fixture seeding timeout",
    "postgen.llm_seed_error": "Warning: LLM fixture seeding failed: {error}",
    "postgen.llm_syncing": "Syncing LLM catalog from external APIs...",
    "postgen.llm_sync_success": "LLM catalog synced successfully",
    "postgen.llm_sync_failed": "Warning: LLM catalog sync failed",
    "postgen.llm_sync_manual": (
        "Run '{slug} llm sync' manually to populate the catalog"
    ),
    "postgen.llm_sync_timeout": "Warning: LLM catalog sync timeout",
    "postgen.llm_sync_error": "Warning: LLM catalog sync failed: {error}",
    # ── Post-generation: formatting ───────────────────────────────────
    "postgen.format_timeout": (
        "Warning: Formatting timeout - run 'make fix' manually when ready"
    ),
    "postgen.format_error": "Warning: Auto-formatting skipped: {error}",
    "postgen.format_error_manual": "Run 'make fix' manually to format code",
    "postgen.format_start": "Auto-formatting generated code...",
    "postgen.format_success": "Code formatting completed successfully",
    "postgen.format_partial": (
        "Some formatting issues detected, but project created successfully"
    ),
    "postgen.format_manual": "Run 'make fix' manually to resolve remaining issues",
    "postgen.format_hint": "Run 'make fix' to format code when ready",
    "postgen.llm_sync_skipped": "LLM catalog sync skipped",
    "postgen.llm_fixtures_outdated": "Static fixture data loaded (may be outdated)",
    "postgen.llm_sync_hint": "Run '{slug} llm sync' later to get latest model data",
    "postgen.llm_fixtures_fallback": (
        "Static fixture data is available but may be outdated"
    ),
    "postgen.ready": "Project ready to run!",
    "postgen.next_steps": "Next steps:",
    "postgen.next_cd": "   cd {path}",
    "postgen.next_serve": "   make serve",
    "postgen.next_dashboard": "   Open Overseer: http://localhost:8000/dashboard/",
    # ── Post-generation: project map ──────────────────────────────────
    "projectmap.title": "Project Structure:",
    "projectmap.components": "Components",
    "projectmap.services": "Business logic",
    "projectmap.models": "Database models",
    "projectmap.cli": "CLI commands",
    "projectmap.entrypoints": "Run targets",
    "projectmap.tests": "Test suite",
    "projectmap.migrations": "Migrations",
    "projectmap.auth": "Authentication",
    "projectmap.ai": "AI conversations",
    "projectmap.comms": "Communications",
    "projectmap.docs": "Documentation",
    # ── Post-generation: footer ───────────────────────────────────────
    "postgen.docs_link": "Docs: https://lbedner.github.io/aegis-stack",
    "postgen.star_prompt": (
        "If Aegis Stack made your life easier, consider leaving a star:"
    ),
}
