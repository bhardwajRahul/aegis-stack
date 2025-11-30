"""
Communications service CLI commands.

Command-line interface for email, SMS, and voice call functionality.
"""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

# Default TwiML URL for testing voice calls
TWILIO_DEMO_TWIML_URL = "http://demo.twilio.com/docs/voice.xml"

app = typer.Typer(help="Communications service commands (email, SMS, voice)")
console = Console()

# Email command group
email_app = typer.Typer(help="Email commands using Resend")
app.add_typer(email_app, name="email")

# SMS command group
sms_app = typer.Typer(help="SMS commands using Twilio")
app.add_typer(sms_app, name="sms")

# Call command group
call_app = typer.Typer(help="Voice call commands using Twilio")
app.add_typer(call_app, name="call")


@app.command()
def status() -> None:
    """Show communications service configuration status."""
    from app.services.comms.call import get_call_status, validate_call_config
    from app.services.comms.email import get_email_status, validate_email_config
    from app.services.comms.sms import get_sms_status, validate_sms_config

    typer.secho("Communications Service Status", fg=typer.colors.BLUE, bold=True)

    # Email status
    email_status = get_email_status()
    email_errors = validate_email_config()

    typer.secho("\nEmail (Resend)", fg=typer.colors.CYAN, bold=True)
    status_color = (
        typer.colors.GREEN if email_status["configured"] else typer.colors.RED
    )
    typer.echo(
        f"  Status: {typer.style('Configured' if email_status['configured'] else 'Not configured', fg=status_color)}"
    )
    typer.echo(
        f"  API Key: {typer.style('Set' if email_status['api_key_set'] else 'Not set', fg=typer.colors.GREEN if email_status['api_key_set'] else typer.colors.RED)}"
    )
    typer.echo(
        f"  From Email: {email_status['from_email'] or typer.style('Not set', fg=typer.colors.RED)}"
    )

    if email_errors:
        for error in email_errors:
            typer.secho(f"  Warning: {error}", fg=typer.colors.YELLOW)

    # SMS status
    sms_status = get_sms_status()
    sms_errors = validate_sms_config()

    typer.secho("\nSMS (Twilio)", fg=typer.colors.CYAN, bold=True)
    status_color = typer.colors.GREEN if sms_status["configured"] else typer.colors.RED
    typer.echo(
        f"  Status: {typer.style('Configured' if sms_status['configured'] else 'Not configured', fg=status_color)}"
    )
    typer.echo(
        f"  Account SID: {typer.style('Set' if sms_status['account_sid_set'] else 'Not set', fg=typer.colors.GREEN if sms_status['account_sid_set'] else typer.colors.RED)}"
    )
    typer.echo(
        f"  Auth Token: {typer.style('Set' if sms_status['auth_token_set'] else 'Not set', fg=typer.colors.GREEN if sms_status['auth_token_set'] else typer.colors.RED)}"
    )
    typer.echo(
        f"  Messaging Service: {typer.style('Set' if sms_status.get('messaging_service_sid_set') else 'Not set', fg=typer.colors.GREEN if sms_status.get('messaging_service_sid_set') else typer.colors.RED)}"
    )
    typer.echo(
        f"  Phone Number: {sms_status['phone_number'] or typer.style('Not set', fg=typer.colors.RED)}"
    )

    if sms_errors:
        for error in sms_errors:
            typer.secho(f"  Warning: {error}", fg=typer.colors.YELLOW)

    # Voice status
    call_status = get_call_status()
    call_errors = validate_call_config()

    typer.secho("\nVoice (Twilio)", fg=typer.colors.CYAN, bold=True)
    status_color = typer.colors.GREEN if call_status["configured"] else typer.colors.RED
    typer.echo(
        f"  Status: {typer.style('Configured' if call_status['configured'] else 'Not configured', fg=status_color)}"
    )
    typer.echo(
        f"  Account SID: {typer.style('Set' if call_status['account_sid_set'] else 'Not set', fg=typer.colors.GREEN if call_status['account_sid_set'] else typer.colors.RED)}"
    )
    typer.echo(
        f"  Auth Token: {typer.style('Set' if call_status['auth_token_set'] else 'Not set', fg=typer.colors.GREEN if call_status['auth_token_set'] else typer.colors.RED)}"
    )
    typer.echo(
        f"  Phone Number: {call_status['phone_number'] or typer.style('Not set', fg=typer.colors.RED)}"
    )

    if call_errors:
        for error in call_errors:
            typer.secho(f"  Warning: {error}", fg=typer.colors.YELLOW)

    # Summary
    typer.echo()
    services_configured = sum(
        [
            email_status["configured"],
            sms_status["configured"],
            call_status["configured"],
        ]
    )
    summary_color = (
        typer.colors.GREEN if services_configured == 3 else typer.colors.YELLOW
    )
    typer.secho(
        f"{services_configured}/3 services configured", fg=summary_color, bold=True
    )

    if services_configured < 3:
        typer.secho("\nQuick start:", dim=True)
        if not email_status["configured"]:
            typer.secho(
                "  Email: Sign up at https://resend.com (free tier available)", dim=True
            )
        if not sms_status["configured"] or not call_status["configured"]:
            typer.secho(
                "  SMS/Voice: Sign up at https://twilio.com/try-twilio (free trial)",
                dim=True,
            )


@email_app.command("send")
def email_send(
    to: str = typer.Argument(..., help="Recipient email address"),
    subject: str = typer.Option(..., "--subject", "-s", help="Email subject"),
    text: str | None = typer.Option(None, "--text", "-t", help="Plain text body"),
    html: str | None = typer.Option(None, "--html", help="HTML body"),
) -> None:
    """Send an email via Resend."""
    asyncio.run(_email_send(to, subject, text, html))


async def _email_send(
    to: str,
    subject: str,
    text: str | None,
    html: str | None,
) -> None:
    """Async implementation of email send."""
    from app.services.comms.email import (
        EmailConfigurationError,
        EmailError,
        send_email_simple,
    )

    if not text and not html:
        typer.secho("Error: Either --text or --html is required", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        result = await send_email_simple(
            to=to,
            subject=subject,
            text=text,
            html=html,
        )

        typer.secho("Email sent successfully!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"{typer.style('Message ID:', fg=typer.colors.CYAN)} {result.id}")
        typer.echo(f"{typer.style('To:', fg=typer.colors.CYAN)} {', '.join(result.to)}")
        typer.echo(f"{typer.style('Subject:', fg=typer.colors.CYAN)} {subject}")

    except EmailConfigurationError as e:
        typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except EmailError as e:
        typer.secho(f"Failed to send email: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@sms_app.command("send")
def sms_send(
    to: str = typer.Argument(..., help="Recipient phone number (E.164 format)"),
    body: str = typer.Argument(..., help="SMS message body"),
) -> None:
    """Send an SMS via Twilio."""
    asyncio.run(_sms_send(to, body))


async def _sms_send(to: str, body: str) -> None:
    """Async implementation of SMS send."""
    from app.services.comms.sms import SMSConfigurationError, SMSError, send_sms_simple

    try:
        result = await send_sms_simple(to=to, body=body)

        typer.secho("SMS sent successfully!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"{typer.style('Message SID:', fg=typer.colors.CYAN)} {result.sid}")
        typer.echo(f"{typer.style('To:', fg=typer.colors.CYAN)} {result.to}")
        typer.echo(
            f"{typer.style('Segments:', fg=typer.colors.CYAN)} {result.segments}"
        )

    except SMSConfigurationError as e:
        typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except SMSError as e:
        typer.secho(f"Failed to send SMS: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@call_app.command("make")
def call_make(
    to: str = typer.Argument(..., help="Recipient phone number (E.164 format)"),
    twiml_url: str = typer.Argument(
        TWILIO_DEMO_TWIML_URL, help="URL returning TwiML instructions"
    ),
    timeout: int = typer.Option(
        30, "--timeout", "-t", help="Seconds to wait for answer"
    ),
) -> None:
    """Make a voice call via Twilio."""
    asyncio.run(_call_make(to, twiml_url, timeout))


async def _call_make(to: str, twiml_url: str, timeout: int) -> None:
    """Async implementation of make call."""
    from app.services.comms.call import CallConfigurationError, CallError, make_call
    from app.services.comms.models import MakeCallRequest

    try:
        request = MakeCallRequest(to=to, twiml_url=twiml_url, timeout=timeout)
        result = await make_call(request)

        typer.secho("Call initiated successfully!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"{typer.style('Call SID:', fg=typer.colors.CYAN)} {result.sid}")
        typer.echo(f"{typer.style('To:', fg=typer.colors.CYAN)} {result.to}")
        typer.echo(f"{typer.style('Status:', fg=typer.colors.CYAN)} {result.status}")

    except CallConfigurationError as e:
        typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except CallError as e:
        typer.secho(f"Failed to make call: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command("providers")
def providers() -> None:
    """Show available communications providers."""
    table = Table(title="Communications Providers", width=70)
    table.add_column("Channel", style="cyan", width=10)
    table.add_column("Provider", style="green", width=10)
    table.add_column("Free Tier", style="yellow", width=12)
    table.add_column("Notes", style="blue", width=30)

    table.add_row(
        "Email",
        "Resend",
        "100/day",
        "Modern email API, great DX",
    )
    table.add_row(
        "SMS",
        "Twilio",
        "$15 trial",
        "Pay per message after trial",
    )
    table.add_row(
        "Voice",
        "Twilio",
        "$15 trial",
        "Pay per minute after trial",
    )

    console.print(table)

    typer.secho("\nSign up links:", dim=True)
    typer.secho("  Resend: https://resend.com", dim=True)
    typer.secho("  Twilio: https://twilio.com/try-twilio", dim=True)


if __name__ == "__main__":
    app()
