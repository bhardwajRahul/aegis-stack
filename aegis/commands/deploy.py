"""
Deploy command implementations for Aegis Stack.

Provides commands for deploying Aegis projects to remote servers.
"""

import shlex
import subprocess
from pathlib import Path

import typer
import yaml

# Deploy config file name
DEPLOY_CONFIG_FILE = ".aegis/deploy.yml"
DEPLOY_CONFIG_EXAMPLE = """\
# Aegis Deploy Configuration
# Run 'aegis deploy-init' to create this file interactively

server:
  host: your-server-ip
  user: root
  path: /opt/{project_name}

docker:
  context: {project_name}-remote

# Optional: domain for TLS (uncomment to enable)
# domain: example.com
# acme_email: admin@example.com
"""


def _get_project_root(project_path: str | None = None) -> Path:
    """Find the project root by looking for pyproject.toml."""
    if project_path:
        return Path(project_path)
    current = Path.cwd()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path.cwd()


def _get_project_name(project_path: str | None = None) -> str:
    """Get project name from pyproject.toml."""
    project_root = _get_project_root(project_path)
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        import tomllib

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("name", project_root.name)
    return project_root.name


def _load_deploy_config(project_path: str | None = None) -> dict | None:
    """Load deploy configuration from .aegis/deploy.yml."""
    project_root = Path(project_path) if project_path else _get_project_root()
    config_path = project_root / DEPLOY_CONFIG_FILE

    if not config_path.exists():
        return None

    with open(config_path) as f:
        return yaml.safe_load(f)


def _save_deploy_config(config: dict) -> None:
    """Save deploy configuration to .aegis/deploy.yml."""
    project_root = _get_project_root()
    config_dir = project_root / ".aegis"
    config_dir.mkdir(exist_ok=True)

    config_path = config_dir / "deploy.yml"
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _compose_prefix(deploy_path: str) -> str:
    """Return the docker compose command prefix for remote execution."""
    safe_path = shlex.quote(deploy_path)
    return (
        f"cd {safe_path} && "
        f"docker compose -f docker-compose.yml -f docker-compose.prod.yml"
        f" --profile prod"
    )


def _run_remote(host: str, user: str, command: str) -> subprocess.CompletedProcess:
    """Run a command on the remote server via SSH."""
    return subprocess.run(["ssh", f"{user}@{host}", command])


def deploy_init_command(
    host: str | None = typer.Option(
        None, "--host", "-h", help="Server IP address or hostname"
    ),
    user: str = typer.Option("root", "--user", "-u", help="SSH user for deployment"),
    path: str | None = typer.Option(
        None, "--path", "-p", help="Deployment path on server"
    ),
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    Initialize deployment configuration for this project.

    Creates .aegis/deploy.yml with server connection settings.

    Examples:\\n
        - aegis deploy-init --host 192.168.1.100\\n
        - aegis deploy-init --host myserver.com --user deploy\\n
    """
    project_name = _get_project_name(project_path)
    project_root = _get_project_root(project_path)

    # Interactive prompts if not provided
    if not host:
        host = typer.prompt("Server IP or hostname")

    if not path:
        path = f"/opt/{project_name}"

    config = {
        "server": {
            "host": host,
            "user": user,
            "path": path,
        },
        "docker": {
            "context": f"{project_name}-remote",
        },
    }

    _save_deploy_config(config)

    typer.secho(f"\nDeploy configuration saved to {DEPLOY_CONFIG_FILE}", fg="green")
    typer.echo(f"   Host: {host}")
    typer.echo(f"   User: {user}")
    typer.echo(f"   Path: {path}")
    typer.echo(f"   Docker Context: {project_name}-remote")

    # Check if .aegis is in .gitignore
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if ".aegis/" not in content and ".aegis" not in content:
            typer.secho(
                "\nNote: Consider adding .aegis/ to .gitignore to avoid committing deploy config",
                fg="yellow",
            )


def deploy_setup_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    Provision a remote server for deployment.

    Installs Docker, configures firewall, and prepares the server.
    Run this once on a fresh server before deploying.

    Examples:\\n
        - aegis deploy-setup\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            "No deploy configuration found. Run 'aegis deploy-init' first.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]

    project_root = Path(project_path) if project_path else _get_project_root()
    setup_script = project_root / "scripts" / "server-setup.sh"

    if not setup_script.exists():
        typer.secho(
            f"Server setup script not found: {setup_script}",
            fg="red",
            err=True,
        )
        typer.echo("Make sure your project was created with the ingress component.")
        raise typer.Exit(1)

    typer.secho(f"Setting up server at {user}@{host}...", fg="blue", bold=True)

    # Add host key to known_hosts if needed
    typer.echo("Checking SSH connectivity...")
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            f"{user}@{host}",
            "echo ok",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        if "Host key verification failed" in result.stderr:
            typer.echo("Adding server to known_hosts...")
            keyscan_result = subprocess.run(
                ["ssh-keyscan", "-H", host],
                capture_output=True,
                text=True,
            )
            if keyscan_result.returncode != 0:
                typer.secho(
                    f"Failed to scan SSH host key: {keyscan_result.stderr}",
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)
            known_hosts = Path.home() / ".ssh" / "known_hosts"
            with open(known_hosts, "a") as f:
                f.write(keyscan_result.stdout)
        else:
            typer.secho(f"SSH connection failed: {result.stderr}", fg="red", err=True)
            raise typer.Exit(1)

    # Copy and run setup script
    typer.echo("Copying setup script to server...")
    scp_result = subprocess.run(
        ["scp", str(setup_script), f"{user}@{host}:/tmp/server-setup.sh"]
    )
    if scp_result.returncode != 0:
        typer.secho("Failed to copy setup script", fg="red", err=True)
        raise typer.Exit(1)

    typer.echo("Running server setup (this may take a few minutes)...")
    ssh_result = subprocess.run(
        [
            "ssh",
            f"{user}@{host}",
            "chmod +x /tmp/server-setup.sh && /tmp/server-setup.sh",
        ]
    )
    if ssh_result.returncode != 0:
        typer.secho("Server setup failed", fg="red", err=True)
        raise typer.Exit(1)

    typer.secho("\nServer setup complete!", fg="green", bold=True)
    typer.echo("Next: Run 'aegis deploy' to deploy your application")


def deploy_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
    build: bool = typer.Option(
        True, "--build/--no-build", help="Build images before deploying"
    ),
) -> None:
    """
    Deploy the project to the configured server.

    Syncs files, builds Docker images, and starts services.

    Examples:\\n
        - aegis deploy\\n
        - aegis deploy --no-build\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            "No deploy configuration found. Run 'aegis deploy-init' first.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    project_root = Path(project_path) if project_path else _get_project_root()

    typer.secho(f"Deploying to {host}...", fg="blue", bold=True)

    # Sync files to server
    typer.echo("Syncing files to server...")
    mkdir_result = subprocess.run(
        ["ssh", f"{user}@{host}", f"mkdir -p {shlex.quote(deploy_path)}"]
    )
    if mkdir_result.returncode != 0:
        typer.secho(
            f"Failed to create remote directory '{deploy_path}'",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    rsync_result = subprocess.run(
        [
            "rsync",
            "-avz",
            "--exclude",
            ".git",
            "--exclude",
            "__pycache__",
            "--exclude",
            ".venv",
            "--exclude",
            "*.pyc",
            "--exclude",
            ".pytest_cache",
            "--exclude",
            ".ruff_cache",
            "--exclude",
            "data/",
            "--exclude",
            ".env",
            "--exclude",
            ".aegis/",
            f"{project_root}/",
            f"{user}@{host}:{deploy_path}/",
        ]
    )
    if rsync_result.returncode != 0:
        typer.secho("Failed to sync files", fg="red", err=True)
        raise typer.Exit(1)

    # Copy .env file if exists
    env_file = project_root / ".env"
    if env_file.exists():
        typer.echo("Copying .env file...")
        env_result = subprocess.run(
            ["scp", str(env_file), f"{user}@{host}:{deploy_path}/.env"]
        )
        if env_result.returncode != 0:
            typer.secho("Failed to copy .env file", fg="red", err=True)
            raise typer.Exit(1)

    # Stop existing services before redeploying
    typer.echo("Stopping existing services...")
    compose_prefix = _compose_prefix(deploy_path)
    _run_remote(host, user, f"{compose_prefix} down --remove-orphans")

    # Build and start services on the remote server via SSH
    # Uses docker-compose.prod.yml override to remove dev volume mounts
    typer.echo("Building and starting services on server...")
    build_flag = "--build" if build else ""
    compose_cmd = f"{compose_prefix} up -d {build_flag}"
    compose_result = subprocess.run(["ssh", f"{user}@{host}", compose_cmd])
    if compose_result.returncode != 0:
        typer.secho("Failed to start services", fg="red", err=True)
        raise typer.Exit(1)

    # Restart Traefik to ensure it re-discovers all containers.
    # Traefik's Docker event stream can silently break after container recreations.
    # Only restart if the ingress component is present (traefik service exists).
    prefix = _compose_prefix(deploy_path)
    traefik_check = subprocess.run(
        ["ssh", f"{user}@{host}", f"{prefix} ps traefik --quiet 2>/dev/null"],
        capture_output=True,
    )
    if traefik_check.returncode == 0:
        _run_remote(host, user, f"{prefix} restart traefik")

    typer.secho("\nDeployment complete!", fg="green", bold=True)
    typer.echo(f"   Application running at: http://{host}")
    typer.echo(f"   Overseer dashboard: http://{host}/dashboard/")
    typer.echo("   View logs: aegis deploy-logs")
    typer.echo("   Check status: aegis deploy-status")


def deploy_logs_command(
    follow: bool = typer.Option(
        True, "--follow/--no-follow", "-f", help="Follow log output"
    ),
    service: str | None = typer.Option(
        None, "--service", "-s", help="Show logs for specific service"
    ),
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    View logs from the deployed application.

    Examples:\\n
        - aegis deploy-logs\\n
        - aegis deploy-logs --no-follow\\n
        - aegis deploy-logs --service webserver\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            "No deploy configuration found. Run 'aegis deploy-init' first.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    follow_flag = "-f" if follow else ""
    service_arg = service if service else ""
    cmd = f"{_compose_prefix(deploy_path)} logs {follow_flag} {service_arg}"
    _run_remote(host, user, cmd)


def deploy_status_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    Check the status of deployed services.

    Examples:\\n
        - aegis deploy-status\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            "No deploy configuration found. Run 'aegis deploy-init' first.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    typer.secho(f"Service status on {host}:", fg="blue", bold=True)
    _run_remote(host, user, f"{_compose_prefix(deploy_path)} ps")


def deploy_stop_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    Stop all deployed services.

    Examples:\\n
        - aegis deploy-stop\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            "No deploy configuration found. Run 'aegis deploy-init' first.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    typer.secho("Stopping services...", fg="yellow")
    result = _run_remote(host, user, f"{_compose_prefix(deploy_path)} down")
    if result.returncode == 0:
        typer.secho("Services stopped", fg="green")
    else:
        typer.secho("Failed to stop services", fg="red", err=True)
        raise typer.Exit(1)


def deploy_restart_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    Restart all deployed services.

    Examples:\\n
        - aegis deploy-restart\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            "No deploy configuration found. Run 'aegis deploy-init' first.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    typer.secho("Restarting services...", fg="yellow")
    result = _run_remote(host, user, f"{_compose_prefix(deploy_path)} restart")
    if result.returncode == 0:
        typer.secho("Services restarted", fg="green")
    else:
        typer.secho("Failed to restart services", fg="red", err=True)
        raise typer.Exit(1)


def deploy_shell_command(
    service: str = typer.Option(
        "webserver", "--service", "-s", help="Service to connect to"
    ),
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    Open a shell in a deployed container.

    Examples:\\n
        - aegis deploy-shell\\n
        - aegis deploy-shell --service redis\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            "No deploy configuration found. Run 'aegis deploy-init' first.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    # Use -t for interactive TTY
    subprocess.run(
        [
            "ssh",
            "-t",
            f"{user}@{host}",
            f"{_compose_prefix(deploy_path)} exec {service} /bin/bash",
        ]
    )
