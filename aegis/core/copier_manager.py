"""
Copier template engine integration.

This module provides Copier template generation functionality alongside
the existing Cookiecutter engine. It's designed to maintain feature parity
during the migration period.
"""

from pathlib import Path
from typing import Any

import typer
import yaml
from copier import run_copy, run_update
from packaging.version import Version

from aegis import __version__

from ..config.defaults import (
    DEFAULT_PYTHON_VERSION,
    GITHUB_TEMPLATE_URL,
    version_to_git_tag,
)
from ..constants import AnswerKeys, StorageBackends
from .migration_generator import (
    generate_migrations_for_services,
    get_services_needing_migrations,
)
from .post_gen_tasks import cleanup_components, run_post_generation_tasks
from .template_generator import TemplateGenerator
from .verbosity import is_verbose, verbose_print


def is_git_repo(path: Path) -> bool:
    """
    Check if path is inside a git repository.

    Args:
        path: Path to check

    Returns:
        True if path has a .git directory (is a git repo root)
    """
    return (path / ".git").exists()


def generate_with_copier(
    template_gen: TemplateGenerator,
    output_dir: Path,
    vcs_ref: str | None = None,
    skip_llm_sync: bool = False,
    dev_mode: bool = False,
) -> Path:
    """
    Generate project using Copier template engine.

    Args:
        template_gen: Template generator with project configuration
        output_dir: Directory to create the project in
        vcs_ref: Git reference (tag, branch, or commit) to generate from
        skip_llm_sync: Whether to skip LLM catalog sync after generation

    Returns:
        Path to the generated project

    Note:
        This function uses the Copier template which is currently incomplete
        (missing conditional _exclude patterns). Projects will include all
        components regardless of selection until template is fixed.
    """
    import subprocess

    # Get template context from template generator
    template_context = template_gen.get_template_context()

    # Determine Python version early - may need to override for RAG compatibility
    # When RAG is enabled, chromadb requires onnxruntime which lacks Python 3.14 wheels
    python_version = template_context.get("python_version", DEFAULT_PYTHON_VERSION)
    ai_rag = template_context.get(AnswerKeys.AI_RAG, "no") == "yes"
    if ai_rag and python_version and Version(python_version) >= Version("3.14"):
        python_version = "3.13"

    # Convert template context to Copier data format
    # Copier uses boolean values instead of "yes"/"no" strings
    copier_data = {
        "project_name": template_context["project_name"],
        "project_slug": template_context["project_slug"],
        "project_description": template_context.get(
            "project_description",
            "A production-ready async Python application built with Aegis Stack",
        ),
        "author_name": template_context.get("author_name", "Your Name"),
        "author_email": template_context.get("author_email", "your.email@example.com"),
        "github_username": template_context.get("github_username", "your-username"),
        "version": template_context.get("version", "0.1.0"),
        "python_version": python_version,  # Uses override for RAG + Python 3.14
        "aegis_version": template_context.get("aegis_version", "0.0.0"),
        # Convert yes/no strings to booleans
        AnswerKeys.SCHEDULER: template_context[AnswerKeys.SCHEDULER] == "yes",
        AnswerKeys.SCHEDULER_BACKEND: template_context[AnswerKeys.SCHEDULER_BACKEND],
        AnswerKeys.SCHEDULER_WITH_PERSISTENCE: template_context[
            AnswerKeys.SCHEDULER_WITH_PERSISTENCE
        ]
        == "yes",
        AnswerKeys.WORKER: template_context[AnswerKeys.WORKER] == "yes",
        AnswerKeys.WORKER_BACKEND: template_context.get(
            AnswerKeys.WORKER_BACKEND, "arq"
        ),
        AnswerKeys.REDIS: template_context[AnswerKeys.REDIS] == "yes",
        AnswerKeys.DATABASE: template_context[AnswerKeys.DATABASE] == "yes",
        AnswerKeys.DATABASE_ENGINE: template_context.get(
            AnswerKeys.DATABASE_ENGINE, StorageBackends.SQLITE
        ),
        AnswerKeys.CACHE: False,  # Default to no
        AnswerKeys.INGRESS: template_context.get(AnswerKeys.INGRESS, "no") == "yes",
        AnswerKeys.OBSERVABILITY: template_context.get(AnswerKeys.OBSERVABILITY, "no")
        == "yes",
        AnswerKeys.AUTH: template_context.get(AnswerKeys.AUTH, "no") == "yes",
        AnswerKeys.AI: template_context.get(AnswerKeys.AI, "no") == "yes",
        AnswerKeys.COMMS: template_context.get(AnswerKeys.COMMS, "no") == "yes",
        AnswerKeys.AI_FRAMEWORK: template_context.get(
            AnswerKeys.AI_FRAMEWORK, "pydantic-ai"
        ),
        AnswerKeys.AI_PROVIDERS: template_context.get(
            AnswerKeys.AI_PROVIDERS, "openai"
        ),
        AnswerKeys.AI_BACKEND: template_context.get(
            AnswerKeys.AI_BACKEND, StorageBackends.MEMORY
        ),
        AnswerKeys.AI_WITH_PERSISTENCE: template_context.get(
            AnswerKeys.AI_WITH_PERSISTENCE, "no"
        )
        == "yes",
        AnswerKeys.AI_RAG: template_context.get(AnswerKeys.AI_RAG, "no") == "yes",
        AnswerKeys.AI_VOICE: template_context.get(AnswerKeys.AI_VOICE, "no") == "yes",
        AnswerKeys.OLLAMA_MODE: template_context.get(AnswerKeys.OLLAMA_MODE, "none"),
    }

    # Detect dev vs production mode for template sourcing
    # - Dev mode (--dev flag): Use plain file path to read from working tree
    # - Development: Use git+file:// URL to access local git repo at HEAD
    # - Production (pip/uvx install): Use GitHub URL (no local git repo)
    from .copier_updater import get_template_root, resolve_version_to_ref

    template_root = get_template_root()

    if dev_mode:
        # Dev mode: read directly from working tree (uncommitted changes)
        # WARNING: Projects generated in dev mode cannot be updated with aegis update
        template_source = str(template_root)
        resolved_ref = None  # No version pinning in dev mode
    elif is_git_repo(template_root):
        # Development mode: local git repository available
        # Always use git+file:// URL so projects are updatable
        template_source = f"git+file://{template_root}"
        if vcs_ref:
            # Specific version requested - resolve to git reference
            resolved_ref = resolve_version_to_ref(vcs_ref, template_root)
        else:
            # No version specified - use HEAD so project has valid _commit
            # This is CRITICAL for aegis update to work properly
            resolved_ref = "HEAD"
    else:
        # Production mode: installed via pip/uvx (no .git directory)
        # Use GitHub URL for template source with CLI version as default ref
        # This ensures CLI v0.4.1 uses template v0.4.1, not HEAD
        template_source = GITHUB_TEMPLATE_URL
        resolved_ref = vcs_ref if vcs_ref else version_to_git_tag(__version__)

    # Store template version in answers for future reference
    # This allows aegis update to show "v0.4.1" instead of commit hash
    if resolved_ref is None:
        # Dev mode - no version tracking
        copier_data["_template_version"] = "dev"
    elif resolved_ref.startswith("v"):
        # Version tag (e.g., "v0.4.1") -> strip 'v' prefix
        copier_data["_template_version"] = resolved_ref[1:]
    else:
        # Branch or commit hash - store as-is
        copier_data["_template_version"] = resolved_ref

    # Generate project - Copier creates output_dir/project_slug via {{ project_slug }}/ wrapper
    # NOTE: _tasks removed from copier.yml - we run them ourselves below
    # Suppress Copier output unless --verbose flag is passed
    run_copy(
        template_source,
        output_dir,  # Copier creates project_slug subdirectory from template
        data=copier_data,
        defaults=True,  # Use template defaults, overridden by our explicit data
        unsafe=False,  # No tasks in copier.yml anymore - we run them ourselves
        vcs_ref=resolved_ref,  # Use specified version if provided
        quiet=not is_verbose(),  # Silent unless --verbose
    )

    # Copier creates the project in output_dir/project_slug
    project_path = output_dir / template_context["project_slug"]

    # Store template version in answers file for future reference
    # Copier only writes fields defined in copier.yml, so we add this manually
    # This allows 'aegis update' to show "v0.4.1" instead of commit hash
    template_version = copier_data.get("_template_version")
    if template_version:
        answers_file = project_path / ".copier-answers.yml"
        if answers_file.exists():
            answers = yaml.safe_load(answers_file.read_text())
            answers["_template_version"] = template_version
            answers_file.write_text(yaml.safe_dump(answers, default_flow_style=False))

    # Clean up unwanted component files based on selection
    # This must happen BEFORE post-generation tasks (which run linting on the remaining files)
    cleanup_components(project_path, copier_data)

    # Run post-generation tasks with explicit working directory control
    # This ensures consistent behavior with Cookiecutter
    include_auth = copier_data.get(AnswerKeys.AUTH, False)
    include_ai = copier_data.get(AnswerKeys.AI, False)
    ai_backend = copier_data.get(AnswerKeys.AI_BACKEND, StorageBackends.MEMORY)
    database_engine = copier_data.get(
        AnswerKeys.DATABASE_ENGINE, StorageBackends.SQLITE
    )

    # Type narrowing: ensure booleans for include_auth and include_ai
    is_auth_included: bool = include_auth is True
    is_ai_included: bool = include_ai is True

    # Type narrowing: ai_backend should always be a string, but narrow from Any
    ai_backend_str: str = str(ai_backend) if ai_backend else StorageBackends.MEMORY

    ai_needs_migrations = is_ai_included and ai_backend_str != StorageBackends.MEMORY
    needs_migration_files = is_auth_included or ai_needs_migrations
    # Only run migrations automatically for SQLite (file-based, no server needed)
    # PostgreSQL requires a running server, so skip auto-migration
    is_sqlite = database_engine == StorageBackends.SQLITE
    run_migrations = needs_migration_files and is_sqlite

    # Generate migrations for services that need them (always, regardless of engine)
    if needs_migration_files:
        # Get ai_voice from copier_data (it's a boolean after conversion)
        ai_voice_enabled: bool = copier_data.get(AnswerKeys.AI_VOICE, False) is True
        context = {
            "include_auth": is_auth_included,
            "include_ai": is_ai_included,
            "ai_backend": ai_backend_str,
            "ai_voice": ai_voice_enabled,
        }
        services = get_services_needing_migrations(context)
        if services:
            generated = generate_migrations_for_services(project_path, services)
            for migration_path in generated:
                print(f"Generated migration: {migration_path.name}")

    # AI needs seeding when using persistence backend AND sqlite (postgres needs running server)
    ai_needs_seeding = ai_needs_migrations and is_sqlite

    # Type narrowing: python_version from copier_data can be Any, so narrow to str | None
    python_version_value = copier_data.get("python_version")
    python_version_str: str | None = (
        python_version_value if isinstance(python_version_value, str) else None
    )

    # Skip LLM sync for postgres (requires running database server)
    should_skip_llm_sync = skip_llm_sync or not is_sqlite

    run_post_generation_tasks(
        project_path,
        include_migrations=run_migrations,
        python_version=python_version_str,
        seed_ai=ai_needs_seeding,
        skip_llm_sync=should_skip_llm_sync,
        project_slug=template_context["project_slug"],
    )

    # Initialize git repository for Copier updates
    # Copier requires a git-tracked project to perform updates

    try:
        subprocess.run(
            ["git", "init"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        # Configure git user AFTER init (local config requires .git to exist)
        # This is needed for commits to work in CI environments
        subprocess.run(
            ["git", "config", "user.name", "Aegis Stack"],
            cwd=project_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "noreply@aegis-stack.dev"],
            cwd=project_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit from Aegis Stack"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        verbose_print("Git repository initialized")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to initialize git repository: {e}")
        print("Run 'git init && git add . && git commit' manually")

    # Show docs/GitHub links
    typer.echo()
    typer.secho("Docs: https://lbedner.github.io/aegis-stack", dim=True)
    typer.secho("GitHub: https://github.com/lbedner/aegis-stack", dim=True)

    # CRITICAL: Fix _src_path in .copier-answers.yml for future updates to work
    #
    # Problem: Copier stores a temp directory path during generation (e.g.,
    # /private/var/folders/...) which won't exist later when running updates.
    #
    # Solution: Update _src_path to point to the actual template repository:
    # - Development: git+file:// URL for local git repo
    # - Production: GitHub URL for remote repo
    #
    # IMPORTANT: We do NOT modify _commit - Copier sets this correctly when using
    # git+file:// URL. Manually overwriting _commit breaks Copier's 3-way merge
    # algorithm for updates. See: https://copier.readthedocs.io/en/stable/updating/
    try:
        answers_file = project_path / ".copier-answers.yml"
        if answers_file.exists():
            with open(answers_file) as f:
                answers = yaml.safe_load(f)

            # Fix _src_path based on dev vs production mode
            # We already determined template_root above
            if is_git_repo(template_root):
                # Development mode: use local git repo
                answers["_src_path"] = f"git+file://{template_root}"
            else:
                # Production mode: use GitHub URL
                answers["_src_path"] = GITHUB_TEMPLATE_URL

            with open(answers_file, "w") as f:
                yaml.safe_dump(answers, f, default_flow_style=False, sort_keys=False)

            # Commit the updated .copier-answers.yml
            try:
                subprocess.run(
                    ["git", "add", ".copier-answers.yml"],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        "Fix .copier-answers.yml _src_path for template updates",
                    ],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                # If commit fails (e.g., no changes), that's OK
                pass

    except Exception:
        # If we can't fix _src_path, that's OK - project generation succeeded
        # but updates won't work. This can happen in non-git environments.
        pass

    return project_path


def is_copier_project(project_path: Path) -> bool:
    """
    Check if a project was generated with Copier.

    Args:
        project_path: Path to the project directory

    Returns:
        True if project has .copier-answers.yml file
    """
    answers_file = project_path / ".copier-answers.yml"
    return answers_file.exists()


def load_copier_answers(project_path: Path) -> dict[str, Any]:
    """
    Load existing Copier answers from a project.

    Args:
        project_path: Path to the project directory

    Returns:
        Dictionary of Copier answers

    Raises:
        FileNotFoundError: If .copier-answers.yml doesn't exist
        yaml.YAMLError: If answers file is corrupted
    """
    answers_file = project_path / ".copier-answers.yml"

    if not answers_file.exists():
        raise FileNotFoundError(
            f"No .copier-answers.yml found in {project_path}. "
            "This doesn't appear to be a Copier-generated project."
        )

    try:
        with open(answers_file) as f:
            answers = yaml.safe_load(f)
            if answers is None:
                return {}
            return answers
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse .copier-answers.yml: {e}") from e


def update_with_copier(
    project_path: Path,
    additional_data: dict[str, Any] | None = None,
    conflict_mode: str = "rej",
) -> None:
    """
    Update an existing Copier-generated project with new data.

    This function uses Copier's update mechanism to add new components
    or update existing project configuration.

    Args:
        project_path: Path to the existing project directory
        additional_data: New data to merge (e.g., {"include_scheduler": True})
        conflict_mode: How to handle conflicts - "rej" (separate files) or "inline" (markers)

    Raises:
        FileNotFoundError: If project doesn't have .copier-answers.yml
        Exception: If Copier update fails

    Example:
        # Add scheduler component to existing project
        update_with_copier(
            Path("my-project"),
            {"include_scheduler": True, "scheduler_backend": "memory"}
        )
    """
    # Validate it's a Copier project
    if not is_copier_project(project_path):
        raise FileNotFoundError(
            f"Project at {project_path} was not generated with Copier.\n"
            f"The 'aegis add' command only works with Copier-generated projects.\n"
            f"To add components, regenerate the project with the new components included."
        )

    # Load existing answers to validate state
    try:
        load_copier_answers(project_path)
    except yaml.YAMLError as e:
        raise Exception(
            f"Failed to read project configuration: {e}\n"
            f"The .copier-answers.yml file may be corrupted."
        ) from e

    # Prepare update data
    update_data = additional_data or {}

    # Run Copier update
    # NOTE: We do NOT pass src_path - Copier will read it from .copier-answers.yml
    # This is the key to making updates work!
    try:
        run_update(
            dst_path=str(project_path),
            data=update_data,
            defaults=True,  # Use existing answers as defaults
            overwrite=True,  # Allow overwriting files
            conflict=conflict_mode,  # How to handle conflicts
            unsafe=True,  # Allow running tasks (uv sync, make fix)
            vcs_ref="HEAD",  # Use latest template (no versioning needed yet)
        )
    except Exception as e:
        raise Exception(
            f"Failed to update project: {e}\n"
            f"This may be due to conflicts with manually modified files.\n"
            f"Check for .rej files in the project directory for details."
        ) from e
