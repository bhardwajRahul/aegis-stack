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

from ..config.defaults import DEFAULT_PYTHON_VERSION, GITHUB_TEMPLATE_URL
from ..constants import AnswerKeys
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
    template_gen: TemplateGenerator, output_dir: Path, vcs_ref: str | None = None
) -> Path:
    """
    Generate project using Copier template engine.

    Args:
        template_gen: Template generator with project configuration
        output_dir: Directory to create the project in
        vcs_ref: Git reference (tag, branch, or commit) to generate from

    Returns:
        Path to the generated project

    Note:
        This function uses the Copier template which is currently incomplete
        (missing conditional _exclude patterns). Projects will include all
        components regardless of selection until template is fixed.
    """
    import subprocess

    # Get cookiecutter context from template generator
    cookiecutter_context = template_gen.get_template_context()

    # Determine Python version early - may need to override for RAG compatibility
    # When RAG is enabled, chromadb requires onnxruntime which lacks Python 3.14 wheels
    python_version = cookiecutter_context.get("python_version", DEFAULT_PYTHON_VERSION)
    ai_rag = cookiecutter_context.get(AnswerKeys.AI_RAG, "no") == "yes"
    if ai_rag and python_version and Version(python_version) >= Version("3.14"):
        python_version = "3.13"

    # Convert cookiecutter context to Copier data format
    # Copier uses boolean values instead of "yes"/"no" strings
    copier_data = {
        "project_name": cookiecutter_context["project_name"],
        "project_slug": cookiecutter_context["project_slug"],
        "project_description": cookiecutter_context.get(
            "project_description",
            "A production-ready async Python application built with Aegis Stack",
        ),
        "author_name": cookiecutter_context.get("author_name", "Your Name"),
        "author_email": cookiecutter_context.get(
            "author_email", "your.email@example.com"
        ),
        "github_username": cookiecutter_context.get("github_username", "your-username"),
        "version": cookiecutter_context.get("version", "0.1.0"),
        "python_version": python_version,
        # Convert yes/no strings to booleans
        AnswerKeys.SCHEDULER: cookiecutter_context[AnswerKeys.SCHEDULER] == "yes",
        AnswerKeys.SCHEDULER_BACKEND: cookiecutter_context[
            AnswerKeys.SCHEDULER_BACKEND
        ],
        AnswerKeys.SCHEDULER_WITH_PERSISTENCE: cookiecutter_context[
            AnswerKeys.SCHEDULER_WITH_PERSISTENCE
        ]
        == "yes",
        AnswerKeys.WORKER: cookiecutter_context[AnswerKeys.WORKER] == "yes",
        AnswerKeys.WORKER_BACKEND: cookiecutter_context.get(
            AnswerKeys.WORKER_BACKEND, "arq"
        ),
        AnswerKeys.REDIS: cookiecutter_context[AnswerKeys.REDIS] == "yes",
        AnswerKeys.DATABASE: cookiecutter_context[AnswerKeys.DATABASE] == "yes",
        AnswerKeys.CACHE: False,  # Default to no
        AnswerKeys.AUTH: cookiecutter_context.get(AnswerKeys.AUTH, "no") == "yes",
        AnswerKeys.AI: cookiecutter_context.get(AnswerKeys.AI, "no") == "yes",
        AnswerKeys.COMMS: cookiecutter_context.get(AnswerKeys.COMMS, "no") == "yes",
        AnswerKeys.AI_FRAMEWORK: cookiecutter_context.get(
            AnswerKeys.AI_FRAMEWORK, "pydantic-ai"
        ),
        AnswerKeys.AI_PROVIDERS: cookiecutter_context.get(
            AnswerKeys.AI_PROVIDERS, "openai"
        ),
        AnswerKeys.AI_BACKEND: cookiecutter_context.get(
            AnswerKeys.AI_BACKEND, "memory"
        ),
        AnswerKeys.AI_WITH_PERSISTENCE: cookiecutter_context.get(
            AnswerKeys.AI_WITH_PERSISTENCE, "no"
        )
        == "yes",
        AnswerKeys.AI_RAG: cookiecutter_context.get(AnswerKeys.AI_RAG, "no") == "yes",
    }

    # Detect dev vs production mode for template sourcing
    # - Development (no vcs_ref): Use direct file path for working directory changes
    # - Development (with vcs_ref): Use git+file:// URL to access specific version
    # - Production (pip/uvx install): Use GitHub URL (no local git repo)
    from .copier_updater import get_template_root, resolve_version_to_ref

    template_root = get_template_root()

    if is_git_repo(template_root):
        # Development mode: local git repository available
        if vcs_ref:
            # Specific version requested - use git+file:// URL to access git history
            # This is CRITICAL for aegis update to work properly
            template_source = f"git+file://{template_root}"
            resolved_ref = resolve_version_to_ref(vcs_ref, template_root)
        else:
            # No version specified - use direct file path for working directory
            # This allows uncommitted template changes to be picked up during dev
            template_source = str(
                Path(__file__).parent.parent / "templates" / "copier-aegis-project"
            )
            resolved_ref = None
    else:
        # Production mode: installed via pip/uvx (no .git directory)
        # Use GitHub URL for template source with HEAD as default ref
        template_source = GITHUB_TEMPLATE_URL
        resolved_ref = vcs_ref if vcs_ref else "HEAD"

    # Generate project - Copier creates the project_slug directory automatically
    # NOTE: _tasks removed from copier.yml - we run them ourselves below
    # Suppress Copier output unless --verbose flag is passed
    run_copy(
        template_source,
        output_dir,
        data=copier_data,
        defaults=True,  # Use template defaults, overridden by our explicit data
        unsafe=False,  # No tasks in copier.yml anymore - we run them ourselves
        vcs_ref=resolved_ref,  # Use specified version if provided
        quiet=not is_verbose(),  # Silent unless --verbose
    )

    # Copier creates the project in output_dir/project_slug
    project_path = output_dir / cookiecutter_context["project_slug"]

    # Clean up unwanted component files based on selection
    # This must happen BEFORE post-generation tasks (which run linting on the remaining files)
    cleanup_components(project_path, copier_data)

    # Run post-generation tasks with explicit working directory control
    # This ensures consistent behavior with Cookiecutter
    include_auth = copier_data.get(AnswerKeys.AUTH, False)
    include_ai = copier_data.get(AnswerKeys.AI, False)
    ai_backend = copier_data.get(AnswerKeys.AI_BACKEND, "memory")
    ai_needs_migrations = include_ai and ai_backend != "memory"
    include_migrations = include_auth or ai_needs_migrations

    # Generate migrations for services that need them
    if include_migrations:
        context = {
            "include_auth": include_auth,
            "include_ai": include_ai,
            "ai_backend": ai_backend,
        }
        services = get_services_needing_migrations(context)
        if services:
            generated = generate_migrations_for_services(project_path, services)
            for migration_path in generated:
                print(f"Generated migration: {migration_path.name}")

    # AI needs seeding when using persistence backend (same condition as migrations)
    ai_needs_seeding = ai_needs_migrations

    # python_version was already determined earlier (with RAG override if needed)
    run_post_generation_tasks(
        project_path,
        include_migrations=include_migrations,
        python_version=python_version,
        seed_ai=ai_needs_seeding,
    )

    # Initialize git repository for Copier updates
    # Copier requires a git-tracked project to perform updates

    try:
        # Configure git user in case CI environment doesn't have it set
        # This is needed for commits to work in CI
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
            ["git", "init"],
            cwd=project_path,
            check=True,
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
