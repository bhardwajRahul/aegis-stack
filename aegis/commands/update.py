"""
Update command implementation.

Updates an existing Aegis Stack project to a newer template version using
Copier's git-aware update mechanism.
"""

from pathlib import Path

import typer

from ..core.copier_manager import is_copier_project, load_copier_answers
from ..core.copier_updater import (
    get_changelog,
    get_current_template_commit,
    get_latest_version,
    get_template_root,
    resolve_version_to_ref,
    validate_clean_git_tree,
)
from ..core.post_gen_tasks import run_post_generation_tasks
from ..core.version_compatibility import get_cli_version, get_project_template_version


def update_command(
    to_version: str | None = typer.Option(
        None,
        "--to-version",
        help="Update to specific version (default: latest)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without applying",
    ),
    project_path: str = typer.Option(
        ".",
        "--project-path",
        "-p",
        help="Path to the Aegis Stack project (default: current directory)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Update project to a newer template version.

    This command uses Copier's git-aware update mechanism to merge template
    changes into your project while preserving your customizations.

    Examples:

        - aegis update

        - aegis update --to-version 0.2.0

        - aegis update --dry-run

        - aegis update --project-path ../my-project

    Note: This command requires a clean git working tree.
    """

    typer.echo("🛡️  Aegis Stack - Update Template")
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project
    if not is_copier_project(target_path):
        typer.echo(
            f"❌ Project at {target_path} was not generated with Copier.", err=True
        )
        typer.echo(
            "   The 'aegis update' command only works with Copier-generated projects.",
            err=True,
        )
        typer.echo(
            "   Projects generated before v0.2.0 need to be regenerated.",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"📁 Project: {target_path}")

    # Check git status
    is_clean, git_message = validate_clean_git_tree(target_path)
    if not is_clean:
        typer.echo(f"❌ {git_message}", err=True)
        typer.echo(
            "   Commit or stash your changes before running 'aegis update'.",
            err=True,
        )
        typer.echo(
            "   Copier requires a clean git tree to safely merge changes.", err=True
        )
        raise typer.Exit(1)

    typer.echo("✅ Git tree is clean")

    # Get current template version
    current_commit = get_current_template_commit(target_path)
    if not current_commit:
        typer.secho(
            "⚠️  Warning: Cannot determine current template version", fg="yellow"
        )
        typer.echo("   Project may have been generated from an untagged commit")

    current_version = get_project_template_version(target_path)
    cli_version = get_cli_version()

    # Get template root
    template_root = get_template_root()

    # Resolve target version
    if to_version:
        target_ref = resolve_version_to_ref(to_version, template_root)
        target_version_display = to_version
    else:
        # Default to latest
        latest = get_latest_version(template_root)
        if latest:
            target_ref = f"v{latest}"
            target_version_display = f"{latest} (latest)"
        else:
            target_ref = "HEAD"
            target_version_display = "HEAD (latest commit)"

    # Display version information
    typer.echo("")
    typer.echo("📦 Version Information:")
    typer.echo(f"   Current CLI:      {cli_version}")
    if current_version:
        typer.echo(f"   Current Template: {current_version}")
    elif current_commit:
        typer.echo(f"   Current Template: {current_commit[:8]}... (commit)")
    else:
        typer.echo("   Current Template: unknown")
    typer.echo(f"   Target Template:  {target_version_display}")

    # Check if already up to date (version-based)
    if current_version and to_version and current_version == to_version:
        typer.echo("")
        typer.secho("✅ Project is already at the requested version", fg="green")
        return

    # Check if already at target commit (for HEAD/branch updates)
    if current_commit and target_ref:
        from ..core.copier_updater import resolve_ref_to_commit

        target_commit = resolve_ref_to_commit(target_ref, template_root)

        if target_commit and current_commit == target_commit:
            typer.echo("")
            typer.secho("✅ Project is already at the target commit", fg="green")
            typer.echo(f"   Current: {current_commit[:8]}...")
            typer.echo(f"   Target:  {target_commit[:8]}...")
            return

    # Get and display changelog
    if current_commit:
        typer.echo("")
        typer.echo("📋 Changelog:")
        typer.echo("-" * 50)
        changelog = get_changelog(current_commit, target_ref, template_root)
        typer.echo(changelog)
        typer.echo("-" * 50)

    # Dry run mode
    if dry_run:
        typer.echo("")
        typer.secho("🔍 DRY RUN MODE - No changes will be applied", fg="cyan")
        typer.echo("")
        typer.echo("To apply this update, run:")
        if to_version:
            typer.echo(f"  aegis update --to-version {to_version}")
        else:
            typer.echo("  aegis update")
        return

    # Confirmation
    if not yes:
        typer.echo("")
        if not typer.confirm("🚀 Apply this update?"):
            typer.echo("❌ Update cancelled")
            raise typer.Exit(0)

    # Perform update using Copier
    typer.echo("")
    typer.echo("🔄 Updating project...")

    try:
        # Import here to avoid circular dependency
        from copier import run_update

        # Run Copier update with git-aware merge
        run_update(
            dst_path=str(target_path),
            src_path=str(template_root),
            defaults=True,  # Use existing answers as defaults
            overwrite=True,  # Allow overwriting files
            conflict="rej",  # Create .rej files for conflicts
            unsafe=False,  # Disable _tasks (we run them ourselves)
            vcs_ref=target_ref,  # Use specified version
        )

        # Load answers to determine what services are enabled
        answers = load_copier_answers(target_path)
        include_auth = answers.get("include_auth", False)

        # Run post-generation tasks
        typer.echo("🔨 Running post-generation tasks...")
        run_post_generation_tasks(target_path, include_auth=include_auth)

        # Success!
        typer.echo("")
        typer.secho("✅ Update completed successfully!", fg="green")
        typer.echo("")
        typer.echo("📝 Next Steps:")
        typer.echo("   1. Review changes: git diff")
        typer.echo("   2. Check for conflicts (*.rej files)")
        typer.echo("   3. Run tests: make check")
        typer.echo("   4. Commit changes: git add . && git commit")

        # Check for conflict files
        rej_files = list(target_path.rglob("*.rej"))
        if rej_files:
            typer.echo("")
            typer.secho(
                f"⚠️  Found {len(rej_files)} conflict file(s) - manual resolution required",
                fg="yellow",
            )
            typer.echo("   Conflicts:")
            for rej_file in rej_files[:5]:  # Show first 5
                typer.echo(f"   - {rej_file.relative_to(target_path)}")
            if len(rej_files) > 5:
                typer.echo(f"   ... and {len(rej_files) - 5} more")

    except Exception as e:
        typer.echo("")
        typer.secho(f"❌ Update failed: {e}", fg="red", err=True)
        typer.echo("")
        typer.echo("💡 Troubleshooting:")
        typer.echo("   - Ensure you have a clean git tree")
        typer.echo("   - Check that the version/commit exists")
        typer.echo("   - Review Copier documentation for update issues")
        raise typer.Exit(1)
