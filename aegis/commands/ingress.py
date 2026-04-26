"""
Ingress TLS enable command implementation.

Enables TLS (HTTPS via Let's Encrypt) on an existing Aegis Stack project
that already has the ingress component.
"""

from pathlib import Path

import typer

from ..cli.validation import validate_copier_project, validate_git_repository
from ..constants import AnswerKeys, ComponentNames
from ..core.copier_manager import load_copier_answers
from ..core.manual_updater import PROJECT_SLUG_PLACEHOLDER, ManualUpdater
from ..i18n import t

# Default placeholder email from copier template
_PLACEHOLDER_EMAIL = "your.email@example.com"


def ingress_enable_command(
    domain: str | None = typer.Option(
        None,
        "--domain",
        "-d",
        help="Domain name for TLS certificate (e.g., example.com)",
    ),
    email: str | None = typer.Option(
        None,
        "--email",
        "-e",
        help="Email for Let's Encrypt certificate notifications",
    ),
    project_path: str = typer.Option(
        ".",
        "--project-path",
        "-p",
        help="Path to the Aegis Stack project (default: current directory)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """
    Enable TLS (HTTPS) on a project with the ingress component.

    Configures Let's Encrypt certificates via Traefik. If the ingress
    component is not yet added, it will be added automatically first.

    Examples:

        - aegis ingress-enable --domain example.com --email admin@example.com

        - aegis ingress-enable -p ../my-project -d example.com -y

        - aegis ingress-enable (interactive prompts)
    """
    typer.echo(t("ingress.title"))
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project and git repo
    validate_copier_project(target_path, "ingress-enable")
    validate_git_repository(target_path)

    typer.echo(t("ingress.project", path=target_path))

    # Load current answers
    answers = load_copier_answers(target_path)

    # Step 1: Ensure ingress component is enabled
    ingress_enabled = answers.get(AnswerKeys.INGRESS, False)
    if not ingress_enabled:
        typer.echo(f"\n{t('ingress.not_found')}")
        if not yes and not typer.confirm(t("ingress.add_confirm"), default=True):
            typer.secho(t("shared.operation_cancelled"), fg="red")
            raise typer.Exit(0)

        updater = ManualUpdater(target_path)
        result = updater.add_component(ComponentNames.INGRESS)
        if not result.success:
            typer.secho(
                t("ingress.add_failed", error=result.error_message),
                fg="red",
                err=True,
            )
            raise typer.Exit(1)

        typer.secho(t("ingress.added"), fg="green")
        # Reload answers after component addition
        answers = load_copier_answers(target_path)

    # Step 2: Check if TLS is already enabled
    if answers.get("ingress_tls") is True:
        typer.secho(f"\n{t('ingress.tls_already')}", fg="green")
        current_domain = answers.get("ingress_domain", "")
        current_email = answers.get("author_email", "")
        if current_domain:
            typer.echo(t("ingress.domain_label", domain=current_domain))
        if current_email and current_email != _PLACEHOLDER_EMAIL:
            typer.echo(t("ingress.acme_email", email=current_email))
        raise typer.Exit(0)

    # Step 3: Collect TLS configuration
    # Domain
    if domain is None and not yes:
        domain = typer.prompt(
            t("ingress.domain_prompt"),
            default="",
        )
        if domain == "":
            domain = None

    # Email for Let's Encrypt
    if email is None:
        # Try to use existing author_email if it's not the placeholder
        existing_email = answers.get("author_email", "")
        if existing_email and existing_email != _PLACEHOLDER_EMAIL:
            email = existing_email
            typer.echo(t("ingress.email_reuse", email=email))
        elif not yes:
            email = typer.prompt(t("ingress.email_prompt"))
        else:
            typer.secho(
                t("ingress.email_required"),
                fg="red",
                err=True,
            )
            raise typer.Exit(1)

    # Step 4: Confirm
    typer.echo(f"\n{t('ingress.tls_config')}")
    if domain:
        typer.echo(t("ingress.domain_label", domain=domain))
    else:
        typer.echo(t("ingress.domain_none"))
    typer.echo(t("ingress.acme_email", email=email))

    if not yes and not typer.confirm(f"\n{t('ingress.tls_confirm')}", default=True):
        typer.secho(t("shared.operation_cancelled"), fg="red")
        raise typer.Exit(0)

    # Step 5: Update answers and regenerate files
    typer.echo(f"\n{t('ingress.enabling')}")

    updater = ManualUpdater(target_path)

    # Build updated answers
    updated_answers = {
        **updater.answers,
        "ingress_tls": True,
        "author_email": email,
    }
    if domain:
        updated_answers["ingress_domain"] = domain
    else:
        updated_answers["ingress_domain"] = ""

    # Regenerate shared files (docker-compose.yml, docker-compose.dev.yml,
    # docker-compose.prod.yml, .env.example, etc.)
    updater._regenerate_shared_files(updated_answers)

    # Re-render traefik/traefik.yml explicitly (it's a component file, not shared)
    traefik_template = f"{PROJECT_SLUG_PLACEHOLDER}/traefik/traefik.yml"
    traefik_content = updater._render_template_file(traefik_template, updated_answers)
    traefik_path = target_path / "traefik" / "traefik.yml"

    if traefik_content is not None and traefik_path.exists():
        traefik_path.write_text(traefik_content)
        typer.echo(t("ingress.updated_file", file="traefik/traefik.yml"))
    elif traefik_content is not None:
        traefik_path.parent.mkdir(parents=True, exist_ok=True)
        traefik_path.write_text(traefik_content)
        typer.echo(t("ingress.created_file", file="traefik/traefik.yml"))

    # Save updated answers
    updater._save_answers(updated_answers)

    # Success output
    typer.secho(f"\n{t('ingress.success')}", fg="green", bold=True)
    if domain:
        typer.echo(t("ingress.available_at", domain=domain))
    else:
        typer.echo(t("ingress.https_configured"))

    typer.echo(f"\n{t('ingress.next_steps')}")
    typer.echo(t("ingress.next_deploy"))
    typer.echo(t("ingress.next_ports"))
    if domain:
        typer.echo(t("ingress.next_dns", domain=domain))
    typer.echo(t("ingress.next_certs"))
