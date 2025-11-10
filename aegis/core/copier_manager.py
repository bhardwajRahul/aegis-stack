"""
Copier template engine integration.

This module provides Copier template generation functionality alongside
the existing Cookiecutter engine. It's designed to maintain feature parity
during the migration period.
"""

from pathlib import Path
from typing import Any

import yaml
from copier import run_copy, run_update

from ..config.defaults import DEFAULT_PYTHON_VERSION
from .post_gen_tasks import cleanup_components, run_post_generation_tasks
from .template_generator import TemplateGenerator


def generate_with_copier(template_gen: TemplateGenerator, output_dir: Path) -> Path:
    """
    Generate project using Copier template engine.

    Args:
        template_gen: Template generator with project configuration
        output_dir: Directory to create the project in

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
        "python_version": cookiecutter_context.get(
            "python_version", DEFAULT_PYTHON_VERSION
        ),
        # Convert yes/no strings to booleans
        "include_scheduler": cookiecutter_context["include_scheduler"] == "yes",
        "scheduler_backend": cookiecutter_context["scheduler_backend"],
        "scheduler_with_persistence": cookiecutter_context["scheduler_with_persistence"]
        == "yes",
        "include_worker": cookiecutter_context["include_worker"] == "yes",
        "include_redis": cookiecutter_context["include_redis"] == "yes",
        "include_database": cookiecutter_context["include_database"] == "yes",
        "include_cache": False,  # Default to no
        "include_auth": cookiecutter_context.get("include_auth", "no") == "yes",
        "include_ai": cookiecutter_context.get("include_ai", "no") == "yes",
        "ai_providers": cookiecutter_context.get("ai_providers", "openai"),
    }

    # Get copier template path - point directly at template directory
    # This prevents copying aegis-stack repo files into generated projects
    # The repo root path is set later in .copier-answers.yml for git-aware updates
    template_path = Path(__file__).parent.parent / "templates" / "copier-aegis-project"

    # Generate project - Copier creates the project_slug directory automatically
    # NOTE: _tasks removed from copier.yml - we run them ourselves below
    run_copy(
        str(
            template_path
        ),  # Use template directory (not repo root) to avoid copying extra files
        output_dir,
        data=copier_data,
        defaults=True,  # Use template defaults, overridden by our explicit data
        unsafe=False,  # No tasks in copier.yml anymore - we run them ourselves
        vcs_ref=None,  # Don't use git for template versioning - prevents git submodule errors in CI
    )

    # Copier creates the project in output_dir/project_slug
    project_path = output_dir / cookiecutter_context["project_slug"]

    # Clean up unwanted component files based on selection
    # This must happen BEFORE post-generation tasks (which run linting on the remaining files)
    cleanup_components(project_path, copier_data)

    # Run post-generation tasks with explicit working directory control
    # This ensures consistent behavior with Cookiecutter
    include_auth = copier_data.get("include_auth", False)
    python_version = copier_data.get("python_version")
    run_post_generation_tasks(
        project_path, include_auth=include_auth, python_version=python_version
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
        print("✅ Git repository initialized")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to initialize git repository: {e}")
        print("💡 Run 'git init && git add . && git commit' manually")

    # CRITICAL: Update .copier-answers.yml for future updates to work
    # We need to:
    # 1. Store git commit hash (_commit) - tells Copier which template version was used
    # 2. Update template path (_src_path) - point to repo root, not subdirectory
    #    (repo root has .git so Copier can detect version changes)
    try:
        # Get current commit hash from aegis-stack repo
        template_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=template_root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()

        # Update .copier-answers.yml with commit hash AND repo root path
        answers_file = project_path / ".copier-answers.yml"
        if answers_file.exists():
            with open(answers_file) as f:
                answers = yaml.safe_load(f)

            # Update _commit field (was None, now has actual hash)
            answers["_commit"] = commit_hash

            # Update _src_path to point to repo root (where .git exists)
            # The copier.yml at repo root has _subdirectory setting to find actual template
            answers["_src_path"] = str(template_root)

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
                        "Update .copier-answers.yml with template version",
                    ],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                # If commit fails (e.g., no changes), that's OK
                pass

    except Exception:
        # If we can't get commit hash, that's OK - updates won't work but
        # project generation succeeded. This can happen in non-git environments.
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
