"""
Update command implementation.

Updates an existing Aegis Stack project to a newer template version using
Copier's git-aware update mechanism.
"""

import os
import subprocess
from pathlib import Path

import typer

from ..core.copier_manager import is_copier_project, load_copier_answers
from ..core.copier_updater import (
    analyze_conflict_files,
    cleanup_backup_tag,
    create_backup_point,
    format_conflict_report,
    get_changelog,
    get_current_template_commit,
    get_latest_version,
    get_template_root,
    is_version_downgrade,
    resolve_version_to_ref,
    rollback_to_backup,
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
    template_path: str | None = typer.Option(
        None,
        "--template-path",
        "-t",
        help="Use custom template path instead of installed version",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
    allow_downgrade: bool = typer.Option(
        False,
        "--allow-downgrade",
        help="Allow updating to older template versions (use with caution)",
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

        - aegis update --template-path ~/workspace/aegis-stack

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

    # Get template root (with optional custom path)

    # Precedence: --template-path flag > AEGIS_TEMPLATE_PATH env var > default
    effective_template_path = template_path or os.getenv("AEGIS_TEMPLATE_PATH")

    try:
        template_root = get_template_root(effective_template_path)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)

    if effective_template_path:
        source = "flag" if template_path else "AEGIS_TEMPLATE_PATH"
        typer.echo(f"📦 Using custom template ({source}): {template_root}")

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

        # Check for downgrade attempt
        if target_commit and is_version_downgrade(
            current_commit, target_commit, template_root
        ):
            if not allow_downgrade:
                typer.echo("")
                typer.secho("❌ Downgrade detected", fg="red", err=True)
                typer.echo(f"   Current: {current_commit[:8]}...", err=True)
                typer.echo(f"   Target:  {target_commit[:8]}...", err=True)
                typer.echo(
                    "   Use --allow-downgrade to proceed (not recommended)", err=True
                )
                raise typer.Exit(1)

            # Downgrade allowed - show warning
            typer.echo("")
            typer.secho(
                "⚠️  WARNING: Downgrading to older template version", fg="yellow"
            )
            typer.echo(f"   Current: {current_commit[:8]}...")
            typer.echo(f"   Target:  {target_commit[:8]}...")

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

    # Create backup point before update
    typer.echo("")
    typer.echo("📸 Creating backup point...")
    backup_tag = create_backup_point(target_path)
    if backup_tag:
        typer.echo(f"   Backup created: {backup_tag}")
    else:
        typer.secho("⚠️  Could not create backup point", fg="yellow")

    # Perform update using Copier
    typer.echo("")
    typer.echo("🔄 Updating project...")

    try:
        # Import here to avoid circular dependency
        import yaml
        from copier import run_update

        # Prepare .copier-answers.yml for the update
        # If custom template path was provided, update _src_path
        # so Copier reads the template from the correct location.
        # This is necessary because Copier's git detection only works reliably
        # when reading _src_path from the answers file, not when passed as src_path.
        if effective_template_path:
            answers_file = target_path / ".copier-answers.yml"
            if answers_file.exists():
                with open(answers_file) as f:
                    answers = yaml.safe_load(f) or {}

                # Update _src_path to point to custom template
                # Use git+file:// URL format so Copier recognizes it as git-tracked
                answers["_src_path"] = f"git+file://{template_root}"

                with open(answers_file, "w") as f:
                    yaml.safe_dump(
                        answers, f, default_flow_style=False, sort_keys=False
                    )

                # Commit the updated answers (Copier requires clean repo)
                try:
                    subprocess.run(
                        ["git", "add", ".copier-answers.yml"],
                        cwd=target_path,
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            "Update template path for aegis update",
                        ],
                        cwd=target_path,
                        check=True,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError:
                    # If commit fails (e.g., no changes), that's OK
                    pass

        # Run Copier update with git-aware merge
        # NOTE: We do NOT pass src_path - Copier reads it from .copier-answers.yml
        # This is critical for Copier's git tracking detection to work correctly
        run_update(
            dst_path=str(target_path),
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
        tasks_success = run_post_generation_tasks(
            target_path, include_auth=include_auth
        )

        # Show update result
        typer.echo("")
        if tasks_success:
            typer.secho("✅ Update completed successfully!", fg="green")
        else:
            typer.secho(
                "⚠️  Update completed with some post-generation task failures",
                fg="yellow",
            )
            typer.echo("   Some setup tasks failed. See details above.")
        typer.echo("")
        typer.echo("📝 Next Steps:")
        typer.echo("   1. Review changes: git diff")
        typer.echo("   2. Check for conflicts (*.rej files)")
        typer.echo("   3. Run tests: make check")
        typer.echo("   4. Commit changes: git add . && git commit")

        # Check for conflict files and display enhanced report
        conflicts = analyze_conflict_files(target_path)
        if conflicts:
            typer.echo("")
            report = format_conflict_report(conflicts)
            typer.secho(report, fg="yellow")

        # Cleanup backup tag on success
        if backup_tag:
            cleanup_backup_tag(target_path, backup_tag)

    except Exception as e:
        typer.echo("")

        # Check if this is a Copier downgrade error
        error_msg = str(e)
        if "downgrad" in error_msg.lower() and not allow_downgrade:
            typer.secho(f"❌ Update failed: {e}", fg="red", err=True)
            typer.echo("")
            typer.echo("💡 This appears to be a downgrade.")
            typer.echo("   Use --allow-downgrade to proceed (not recommended)")
        else:
            typer.secho(f"❌ Update failed: {e}", fg="red", err=True)

        # Offer rollback if backup exists
        if backup_tag:
            typer.echo("")
            if yes or typer.confirm("🔄 Rollback to previous state?"):
                success, message = rollback_to_backup(target_path, backup_tag)
                if success:
                    typer.secho(f"✅ {message}", fg="green")
                    cleanup_backup_tag(target_path, backup_tag)
                else:
                    typer.secho(f"❌ {message}", fg="red", err=True)
                    typer.echo(f"   Manual rollback: git reset --hard {backup_tag}")
            else:
                typer.echo(f"💡 Manual rollback: git reset --hard {backup_tag}")

        typer.echo("")
        typer.echo("💡 Troubleshooting:")
        typer.echo("   - Ensure you have a clean git tree")
        typer.echo("   - Check that the version/commit exists")
        typer.echo("   - Review Copier documentation for update issues")
        raise typer.Exit(1)
