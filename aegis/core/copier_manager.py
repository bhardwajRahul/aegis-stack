"""
Copier template engine integration.

This module provides Copier template generation functionality alongside
the existing Cookiecutter engine. It's designed to maintain feature parity
during the migration period.
"""

from pathlib import Path

from copier import run_copy

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
        "python_version": cookiecutter_context.get("python_version", "3.11"),
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

    # Get copier template path
    template_path = Path(__file__).parent.parent / "templates" / "copier-aegis-project"

    # Generate project - Copier creates the project_slug directory automatically
    run_copy(
        str(template_path),
        output_dir,
        data=copier_data,
        defaults=True,  # Use template defaults, overridden by our explicit data
        unsafe=True,  # Allow tasks to run (post-generation hooks)
        vcs_ref="HEAD",
    )

    # Copier creates the project in output_dir/project_slug
    return output_dir / cookiecutter_context["project_slug"]
