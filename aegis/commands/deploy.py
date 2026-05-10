"""
Deploy command implementations for Aegis Stack.

Provides commands for deploying Aegis projects to remote servers,
with backup/rollback strategy and post-deploy health checks.
"""

import re
import shlex
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import typer
import yaml

from ..i18n import t

_BACKUP_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}$")

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

# Optional: backup settings (defaults shown)
# backup:
#   keep_count: 5
#   include_database: true

# Optional: health check after deploy (defaults shown)
# health_check:
#   retries: 3
#   auto_rollback: true
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


def _run_remote_capture(
    host: str, user: str, command: str
) -> subprocess.CompletedProcess:
    """Run a command on the remote server via SSH and capture output."""
    return subprocess.run(
        ["ssh", f"{user}@{host}", command], capture_output=True, text=True
    )


def _install_pubkey_on_server(
    pubkey: str, host: str, user: str
) -> subprocess.CompletedProcess:
    """Append a public key to the remote user's authorized_keys, idempotently.

    The pubkey is matched by full body via ``grep -F``; re-running with the
    same key is a no-op. Caller is responsible for ensuring SSH access to
    ``user@host`` already works.
    """
    pubkey_clean = pubkey.strip()
    quoted = shlex.quote(pubkey_clean)
    command = (
        "mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
        "touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && "
        f"grep -qxF {quoted} ~/.ssh/authorized_keys || "
        f"echo {quoted} >> ~/.ssh/authorized_keys"
    )
    return subprocess.run(
        ["ssh", f"{user}@{host}", command], capture_output=True, text=True
    )


def _remove_pubkey_from_server(
    marker: str, host: str, user: str
) -> subprocess.CompletedProcess:
    """Remove any authorized_keys line containing ``marker``.

    Used to roll back a failed deploy-cd-setup. ``marker`` is the trailing
    comment on the pubkey (e.g. ``github-actions-deploy@owner/repo``).
    """
    quoted = shlex.quote(marker)
    command = (
        "if [ -f ~/.ssh/authorized_keys ]; then "
        f"  grep -vF {quoted} ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp || true; "
        "  mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys; "
        "fi"
    )
    return subprocess.run(
        ["ssh", f"{user}@{host}", command], capture_output=True, text=True
    )


def _get_backup_config(config: dict) -> dict:
    """Extract backup config with defaults."""
    backup = config.get("backup", {}) or {}
    return {
        "keep_count": backup.get("keep_count", 5),
        "include_database": backup.get("include_database", True),
    }


def _get_health_config(config: dict) -> dict:
    """Extract health check config with defaults."""
    hc = config.get("health_check", {}) or {}
    return {
        "retries": hc.get("retries", 3),
        "auto_rollback": hc.get("auto_rollback", True),
    }


def _create_backup(
    host: str, user: str, deploy_path: str, include_db: bool = True
) -> str | None:
    """Create a timestamped backup on the remote server.

    Returns the backup timestamp on success, None on failure.
    """
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    safe_path = shlex.quote(deploy_path)
    backup_dir = f"{deploy_path}/backups/{timestamp}"
    safe_backup = shlex.quote(backup_dir)

    typer.echo(t("deploy.creating_backup", timestamp=timestamp))

    # Create backup directory and copy files
    commands = [
        f"mkdir -p {safe_backup}/files",
        f"rsync -a --exclude backups {safe_path}/ {safe_backup}/files/",
    ]
    result = _run_remote_capture(host, user, " && ".join(commands))
    if result.returncode != 0:
        typer.secho(t("deploy.backup_failed", error=result.stderr), fg="red", err=True)
        return None

    # Database backup if PostgreSQL is running
    if include_db:
        compose_prefix = _compose_prefix(deploy_path)
        # Check if postgres service exists and is running
        pg_check = _run_remote_capture(
            host, user, f"{compose_prefix} ps postgres --quiet 2>/dev/null"
        )
        if pg_check.returncode == 0 and pg_check.stdout.strip():
            typer.echo(t("deploy.backup_db"))
            db_cmd = (
                f"{compose_prefix} exec -T postgres"
                f" sh -c 'pg_dump -U $POSTGRES_USER $POSTGRES_DB'"
                f" > {safe_backup}/db_backup.sql"
            )
            db_result = _run_remote_capture(host, user, db_cmd)
            if db_result.returncode != 0:
                typer.secho(
                    t("deploy.backup_db_failed"),
                    fg="yellow",
                )

    # Write manifest
    manifest = (
        f"timestamp: {timestamp}\\n"
        f"source: {deploy_path}\\n"
        f"created: {datetime.now(UTC).isoformat()}"
    )
    _run_remote_capture(
        host, user, f"echo -e {shlex.quote(manifest)} > {safe_backup}/manifest.yml"
    )

    typer.secho(t("deploy.backup_created", timestamp=timestamp), fg="green")
    return timestamp


def _prune_backups(host: str, user: str, deploy_path: str, keep_count: int) -> None:
    """Remove old backups, keeping only the most recent N."""
    safe_path = shlex.quote(f"{deploy_path}/backups")
    result = _run_remote_capture(host, user, f"ls -1t {safe_path} 2>/dev/null")
    if result.returncode != 0 or not result.stdout.strip():
        return

    backups = [b.strip() for b in result.stdout.strip().splitlines() if b.strip()]
    if len(backups) <= keep_count:
        return

    to_remove = backups[keep_count:]
    for old_backup in to_remove:
        if not _BACKUP_TIMESTAMP_RE.match(old_backup):
            continue  # skip unexpected directory names
        safe_old = shlex.quote(f"{deploy_path}/backups/{old_backup}")
        _run_remote_capture(host, user, f"rm -rf {safe_old}")
        typer.echo(t("deploy.backup_pruned", name=old_backup))


def _rollback_to_backup(
    host: str, user: str, deploy_path: str, backup_timestamp: str
) -> bool:
    """Rollback to a specific backup. Returns True on success."""
    safe_path = shlex.quote(deploy_path)
    backup_dir = f"{deploy_path}/backups/{backup_timestamp}"
    safe_backup = shlex.quote(backup_dir)

    # Verify backup exists
    check = _run_remote_capture(host, user, f"test -d {safe_backup}")
    if check.returncode != 0:
        typer.secho(
            t("deploy.rollback_not_found", timestamp=backup_timestamp),
            fg="red",
            err=True,
        )
        return False

    compose_prefix = _compose_prefix(deploy_path)

    typer.echo(t("deploy.rollback_stopping"))
    _run_remote(host, user, f"{compose_prefix} down --remove-orphans")

    typer.echo(t("deploy.rollback_restoring", timestamp=backup_timestamp))
    restore_result = _run_remote_capture(
        host,
        user,
        f"rsync -a --delete --exclude backups {safe_backup}/files/ {safe_path}/",
    )
    if restore_result.returncode != 0:
        typer.secho(
            t("deploy.rollback_restore_failed", error=restore_result.stderr),
            fg="red",
            err=True,
        )
        return False

    # Check for database backup
    db_check = _run_remote_capture(host, user, f"test -f {safe_backup}/db_backup.sql")
    if db_check.returncode == 0:
        typer.echo(t("deploy.rollback_db"))
        # Start only postgres first
        _run_remote(host, user, f"{compose_prefix} up -d postgres")
        typer.echo(t("deploy.rollback_pg_wait"))
        for _ in range(30):  # 60 seconds max (30 * 2s)
            ready = _run_remote_capture(
                host,
                user,
                f"{compose_prefix} exec -T postgres pg_isready -U postgres -q",
            )
            if ready.returncode == 0:
                break
            time.sleep(2)
        else:
            typer.secho(
                t("deploy.rollback_pg_timeout"),
                fg="yellow",
            )
        db_restore = _run_remote_capture(
            host,
            user,
            f"cat {safe_backup}/db_backup.sql |"
            f" {compose_prefix} exec -T postgres"
            f" sh -c 'psql -U $POSTGRES_USER $POSTGRES_DB'",
        )
        if db_restore.returncode != 0:
            typer.secho(t("deploy.rollback_db_failed"), fg="yellow")

    typer.echo(t("deploy.rollback_starting"))
    start_result = _run_remote(host, user, f"{compose_prefix} up -d --build")
    if start_result.returncode != 0:
        typer.secho(t("deploy.rollback_start_failed"), fg="red", err=True)
        return False

    return True


def _run_health_check(
    host: str, user: str, retries: int = 3, interval: int = 5
) -> bool:
    """Run health check against the deployed application.

    Hits the public Traefik entrypoint on the droplet (port 80) rather
    than the webserver container's internal port 8000 — that port isn't
    published to the host in prod compose, so the old `localhost:8000`
    check always produced a false negative. Going through Traefik also
    validates the full routing path the real users hit (container health
    + docker labels + Traefik registration).
    """
    typer.echo(t("deploy.health_waiting"))
    time.sleep(10)

    for attempt in range(1, retries + 1):
        typer.echo(t("deploy.health_attempt", n=attempt, total=retries))
        result = _run_remote_capture(
            host,
            user,
            "curl -sf --max-time 10 http://localhost/health/ -o /dev/null",
        )
        if result.returncode == 0:
            typer.secho(t("deploy.health_passed"), fg="green")
            return True

        if attempt < retries:
            typer.echo(t("deploy.health_retry", interval=interval))
            time.sleep(interval)

    typer.secho(t("deploy.health_all_failed"), fg="red", err=True)
    return False


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


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
        host = typer.prompt(t("deploy.prompt_host"))

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

    typer.secho(f"\n{t('deploy.init_saved', file=DEPLOY_CONFIG_FILE)}", fg="green")
    typer.echo(t("deploy.init_host", host=host))
    typer.echo(t("deploy.init_user", user=user))
    typer.echo(t("deploy.init_path", path=path))
    typer.echo(t("deploy.init_docker_context", context=f"{project_name}-remote"))

    # Check if .aegis is in .gitignore
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if ".aegis/" not in content and ".aegis" not in content:
            typer.secho(
                t("deploy.init_gitignore"),
                fg="yellow",
            )


def deploy_setup_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
    public_key: str | None = typer.Option(
        None,
        "--public-key",
        help=(
            "Path to a public key to install in the deploy user's "
            "authorized_keys (idempotent). Use this so you don't have to "
            "ssh-copy-id by hand before deploying."
        ),
    ),
) -> None:
    """
    Provision a remote server for deployment.

    Installs Docker, configures firewall, and prepares the server.
    Run this once on a fresh server before deploying.

    Examples:\\n
        - aegis deploy-setup\\n
        - aegis deploy-setup --public-key ~/.ssh/id_ed25519.pub\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            t("deploy.no_config"),
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
            t("deploy.setup_script_missing", path=setup_script),
            fg="red",
            err=True,
        )
        typer.echo(t("deploy.setup_script_hint"))
        raise typer.Exit(1)

    typer.secho(t("deploy.setup_title", target=f"{user}@{host}"), fg="blue", bold=True)

    # Add host key to known_hosts if needed
    typer.echo(t("deploy.checking_ssh"))
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
            typer.echo(t("deploy.adding_host_key"))
            keyscan_result = subprocess.run(
                ["ssh-keyscan", "-H", host],
                capture_output=True,
                text=True,
            )
            if keyscan_result.returncode != 0:
                typer.secho(
                    t("deploy.ssh_keyscan_failed", error=keyscan_result.stderr),
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)
            known_hosts = Path.home() / ".ssh" / "known_hosts"
            with open(known_hosts, "a") as f:
                f.write(keyscan_result.stdout)
        else:
            typer.secho(t("deploy.ssh_failed", error=result.stderr), fg="red", err=True)
            raise typer.Exit(1)

    # Copy and run setup script
    typer.echo(t("deploy.copying_script"))
    scp_result = subprocess.run(
        ["scp", str(setup_script), f"{user}@{host}:/tmp/server-setup.sh"]
    )
    if scp_result.returncode != 0:
        typer.secho(t("deploy.copy_failed"), fg="red", err=True)
        raise typer.Exit(1)

    typer.echo(t("deploy.running_setup"))
    ssh_result = subprocess.run(
        [
            "ssh",
            f"{user}@{host}",
            "chmod +x /tmp/server-setup.sh && /tmp/server-setup.sh",
        ]
    )
    if ssh_result.returncode != 0:
        typer.secho(t("deploy.setup_failed"), fg="red", err=True)
        raise typer.Exit(1)

    # Verify installation on remote server
    deploy_path = config["server"]["path"]
    typer.echo("")
    typer.echo(t("deploy.setup_verify"))
    docker_ver = _run_remote_capture(host, user, "docker --version")
    typer.echo(t("deploy.setup_verify_docker", version=docker_ver.stdout.strip()))
    compose_ver = _run_remote_capture(host, user, "docker compose version")
    typer.echo(t("deploy.setup_verify_compose", version=compose_ver.stdout.strip()))
    uv_ver = _run_remote_capture(host, user, "PATH=$HOME/.local/bin:$PATH uv --version")
    typer.echo(t("deploy.setup_verify_uv", version=uv_ver.stdout.strip()))
    typer.echo(t("deploy.setup_verify_app_dir", path=deploy_path))

    if public_key:
        pubkey_path = Path(public_key).expanduser()
        if not pubkey_path.exists():
            typer.secho(
                t("deploy.pubkey_missing", path=str(pubkey_path)),
                fg="red",
                err=True,
            )
            raise typer.Exit(1)
        pubkey_body = pubkey_path.read_text().strip()
        typer.echo(t("deploy.installing_pubkey", user=user))
        install_result = _install_pubkey_on_server(pubkey_body, host, user)
        if install_result.returncode != 0:
            typer.secho(
                t("deploy.pubkey_install_failed", error=install_result.stderr),
                fg="red",
                err=True,
            )
            raise typer.Exit(1)
        typer.secho(t("deploy.pubkey_installed"), fg="green")

    typer.secho(f"\n{t('deploy.setup_complete')}", fg="green", bold=True)
    typer.echo(t("deploy.setup_next"))


def deploy_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
    build: bool = typer.Option(
        True, "--build/--no-build", help="Build images before deploying"
    ),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Create backup before deploying"
    ),
    health_check: bool = typer.Option(
        True,
        "--health-check/--no-health-check",
        help="Run health check after deploying",
    ),
) -> None:
    """
    Deploy the project to the configured server.

    Syncs files, builds Docker images, and starts services.
    Automatically creates a backup before deploying and runs a health
    check afterward. If the health check fails, auto-rollback restores
    the previous version.

    Examples:\\n
        - aegis deploy\\n
        - aegis deploy --no-build\\n
        - aegis deploy --no-backup --no-health-check\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            t("deploy.no_config"),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]
    backup_cfg = _get_backup_config(config)
    health_cfg = _get_health_config(config)

    project_root = Path(project_path) if project_path else _get_project_root()

    typer.secho(t("deploy.deploying", host=host), fg="blue", bold=True)

    # Step 1: Create backup before deploying
    backup_timestamp: str | None = None
    if backup:
        # Check if there's an existing deployment to back up
        check = _run_remote_capture(
            host, user, f"test -f {shlex.quote(deploy_path)}/docker-compose.yml"
        )
        if check.returncode == 0:
            backup_timestamp = _create_backup(
                host,
                user,
                deploy_path,
                include_db=backup_cfg["include_database"],
            )
            if backup_timestamp:
                _prune_backups(host, user, deploy_path, backup_cfg["keep_count"])
        else:
            typer.echo(t("deploy.no_existing"))

    # Step 2: Sync files to server
    typer.echo(t("deploy.syncing"))
    mkdir_result = subprocess.run(
        ["ssh", f"{user}@{host}", f"mkdir -p {shlex.quote(deploy_path)}"]
    )
    if mkdir_result.returncode != 0:
        typer.secho(
            t("deploy.mkdir_failed", path=deploy_path),
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
            ".env.deploy",
            "--exclude",
            ".aegis/",
            "--exclude",
            "backups/",
            f"{project_root}/",
            f"{user}@{host}:{deploy_path}/",
        ]
    )
    if rsync_result.returncode != 0:
        typer.secho(t("deploy.sync_failed"), fg="red", err=True)
        raise typer.Exit(1)

    # Step 3: Copy .env file (prefer .env.deploy for production values)
    deploy_env_file = project_root / ".env.deploy"
    dev_env_file = project_root / ".env"
    if deploy_env_file.exists():
        env_file = deploy_env_file
    elif dev_env_file.exists():
        env_file = dev_env_file
    else:
        env_file = None

    if env_file is not None:
        typer.echo(t("deploy.copying_env", file=env_file.name))
        safe_path = shlex.quote(f"{deploy_path}/.env")
        env_result = subprocess.run(
            ["scp", str(env_file), f"{user}@{host}:{safe_path}"]
        )
        if env_result.returncode != 0:
            typer.secho(t("deploy.env_copy_failed"), fg="red", err=True)
            raise typer.Exit(1)

    # Step 4: Stop existing services
    typer.echo(t("deploy.stopping"))
    compose_prefix = _compose_prefix(deploy_path)
    _run_remote(host, user, f"{compose_prefix} down --remove-orphans")

    # Step 5: Build and start services
    typer.echo(t("deploy.building"))
    build_flag = "--build" if build else ""
    compose_cmd = f"{compose_prefix} up -d {build_flag}"
    compose_result = subprocess.run(["ssh", f"{user}@{host}", compose_cmd])
    if compose_result.returncode != 0:
        typer.secho(t("deploy.start_failed"), fg="red", err=True)
        if backup_timestamp and health_cfg["auto_rollback"]:
            typer.secho(t("deploy.auto_rollback"), fg="yellow")
            _rollback_to_backup(host, user, deploy_path, backup_timestamp)
        raise typer.Exit(1)

    # Step 6: Restart Traefik if present
    prefix = _compose_prefix(deploy_path)
    traefik_check = subprocess.run(
        ["ssh", f"{user}@{host}", f"{prefix} ps traefik --quiet 2>/dev/null"],
        capture_output=True,
    )
    if traefik_check.returncode == 0:
        _run_remote(host, user, f"{prefix} restart traefik")

    # Step 7: Health check + auto-rollback
    if health_check:
        healthy = _run_health_check(
            host,
            user,
            retries=health_cfg["retries"],
        )
        if not healthy:
            if backup_timestamp and health_cfg["auto_rollback"]:
                typer.secho(
                    t("deploy.auto_rollback"),
                    fg="yellow",
                    bold=True,
                )
                success = _rollback_to_backup(host, user, deploy_path, backup_timestamp)
                if success:
                    typer.secho(
                        t("deploy.rolled_back", timestamp=backup_timestamp),
                        fg="green",
                    )
                else:
                    typer.secho(
                        t("deploy.rollback_failed"),
                        fg="red",
                        err=True,
                    )
                raise typer.Exit(1)
            else:
                typer.secho(
                    t("deploy.health_failed_hint"),
                    fg="yellow",
                )
                raise typer.Exit(1)

    typer.secho(f"\n{t('deploy.complete')}", fg="green", bold=True)
    typer.echo(t("deploy.app_running", host=host))
    typer.echo(t("deploy.overseer", host=host))
    typer.echo(t("deploy.view_logs"))
    typer.echo(t("deploy.check_status"))


def deploy_backup_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    Create a backup of the currently deployed application.

    Snapshots application files and optionally the database
    on the remote server.

    Examples:\\n
        - aegis deploy-backup\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            t("deploy.no_config"),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]
    backup_cfg = _get_backup_config(config)

    typer.secho(t("deploy.creating_backup_on", host=host), fg="blue", bold=True)

    timestamp = _create_backup(
        host,
        user,
        deploy_path,
        include_db=backup_cfg["include_database"],
    )
    if not timestamp:
        raise typer.Exit(1)

    _prune_backups(host, user, deploy_path, backup_cfg["keep_count"])
    typer.secho(f"\n{t('deploy.backup_complete')}", fg="green", bold=True)


def deploy_backups_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    List available deployment backups.

    Shows timestamps, sizes, and whether a database dump is included.

    Examples:\\n
        - aegis deploy-backups\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            t("deploy.no_config"),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    safe_path = shlex.quote(f"{deploy_path}/backups")
    result = _run_remote_capture(host, user, f"ls -1t {safe_path} 2>/dev/null")

    if result.returncode != 0 or not result.stdout.strip():
        typer.echo(t("deploy.no_backups"))
        return

    backups = [b.strip() for b in result.stdout.strip().splitlines() if b.strip()]

    typer.secho(
        f"{t('deploy.backups_header', host=host, count=len(backups))}\n",
        fg="blue",
        bold=True,
    )
    ts = t("deploy.col_timestamp")
    sz = t("deploy.col_size")
    db = t("deploy.col_database")
    typer.echo(f"  {ts:<24} {sz:<12} {db}")
    typer.echo(f"  {'─' * 24} {'─' * 12} {'─' * 10}")

    for backup_name in backups:
        backup_dir = f"{deploy_path}/backups/{backup_name}"
        safe_dir = shlex.quote(backup_dir)

        # Get size
        size_result = _run_remote_capture(
            host, user, f"du -sh {safe_dir} 2>/dev/null | cut -f1"
        )
        size = size_result.stdout.strip() if size_result.returncode == 0 else "?"

        # Check for DB dump
        db_check = _run_remote_capture(host, user, f"test -f {safe_dir}/db_backup.sql")
        has_db = "yes" if db_check.returncode == 0 else "no"

        typer.echo(f"  {backup_name:<24} {size:<12} {has_db}")

    typer.echo(f"\n{t('deploy.rollback_hint')}")


def deploy_rollback_command(
    backup: str | None = typer.Option(
        None, "--backup", "-b", help="Backup timestamp to rollback to (default: latest)"
    ),
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
) -> None:
    """
    Rollback to a previous deployment backup.

    Restores application files and database from a backup snapshot.
    Uses the latest backup if no specific timestamp is provided.

    Examples:\\n
        - aegis deploy-rollback\\n
        - aegis deploy-rollback --backup 2026-03-10_183045\\n
    """
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(
            t("deploy.no_config"),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    # Find backup to use
    if not backup:
        safe_path = shlex.quote(f"{deploy_path}/backups")
        result = _run_remote_capture(
            host, user, f"ls -1t {safe_path} 2>/dev/null | head -1"
        )
        if result.returncode != 0 or not result.stdout.strip():
            typer.secho(t("deploy.no_backups_available"), fg="red", err=True)
            raise typer.Exit(1)
        backup = result.stdout.strip()

    typer.secho(
        t("deploy.rolling_back", backup=backup, host=host),
        fg="yellow",
        bold=True,
    )

    success = _rollback_to_backup(host, user, deploy_path, backup)
    if success:
        # Restart Traefik if present
        prefix = _compose_prefix(deploy_path)
        traefik_check = subprocess.run(
            ["ssh", f"{user}@{host}", f"{prefix} ps traefik --quiet 2>/dev/null"],
            capture_output=True,
        )
        if traefik_check.returncode == 0:
            _run_remote(host, user, f"{prefix} restart traefik")

        typer.secho(f"\n{t('deploy.rollback_complete')}", fg="green", bold=True)
        typer.echo(t("deploy.check_status"))
        typer.echo(t("deploy.view_logs"))
    else:
        typer.secho(t("deploy.rollback_failed_final"), fg="red", err=True)
        raise typer.Exit(1)


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
            t("deploy.no_config"),
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
            t("deploy.no_config"),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    typer.secho(t("deploy.status_header", host=host), fg="blue", bold=True)
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
            t("deploy.no_config"),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    typer.secho(t("deploy.stop_stopping"), fg="yellow")
    result = _run_remote(host, user, f"{_compose_prefix(deploy_path)} down")
    if result.returncode == 0:
        typer.secho(t("deploy.stop_success"), fg="green")
    else:
        typer.secho(t("deploy.stop_failed"), fg="red", err=True)
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
            t("deploy.no_config"),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    host = config["server"]["host"]
    user = config["server"]["user"]
    deploy_path = config["server"]["path"]

    typer.secho(t("deploy.restart_restarting"), fg="yellow")
    result = _run_remote(host, user, f"{_compose_prefix(deploy_path)} restart")
    if result.returncode == 0:
        typer.secho(t("deploy.restart_success"), fg="green")
    else:
        typer.secho(t("deploy.restart_failed"), fg="red", err=True)
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
            t("deploy.no_config"),
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


# ─────────────────────────── deploy-cd-setup ───────────────────────────


_GH_DEPLOY_KEY_SECRET = "DEPLOY_SSH_KEY"
_GH_DEPLOY_HOST_SECRET = "DEPLOY_HOST"
_GH_DEPLOY_USER_SECRET = "DEPLOY_USER"


def _detect_github_repo(project_root: Path) -> str | None:
    """Parse owner/repo from ``git remote get-url origin`` in project_root.

    Returns ``None`` if not a git repo, no origin, or origin isn't GitHub.
    Accepts both SSH (``git@github.com:owner/repo.git``) and HTTPS
    (``https://github.com/owner/repo.git``) forms.
    """
    result = subprocess.run(
        ["git", "-C", str(project_root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    match = re.match(
        r"^(?:git@github\.com:|https://github\.com/)([^/]+)/([^/]+?)(?:\.git)?/?$",
        url,
    )
    return f"{match.group(1)}/{match.group(2)}" if match else None


def _check_gh_cli() -> None:
    """Verify ``gh`` CLI is installed and authenticated; exit on failure."""
    try:
        version = subprocess.run(["gh", "--version"], capture_output=True)
    except FileNotFoundError:
        typer.secho(t("deploy.cd_gh_not_installed"), fg="red", err=True)
        raise typer.Exit(1) from None
    if version.returncode != 0:
        typer.secho(t("deploy.cd_gh_not_installed"), fg="red", err=True)
        raise typer.Exit(1)
    try:
        auth = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    except FileNotFoundError:
        typer.secho(t("deploy.cd_gh_not_installed"), fg="red", err=True)
        raise typer.Exit(1) from None
    if auth.returncode != 0:
        typer.secho(t("deploy.cd_gh_not_authed"), fg="red", err=True)
        raise typer.Exit(1)


def _list_gh_secrets(repo: str) -> set[str]:
    """Return the set of secret names already configured on ``repo``."""
    result = subprocess.run(
        ["gh", "secret", "list", "--repo", repo],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return set()
    return {line.split("\t", 1)[0] for line in result.stdout.splitlines() if line}


def _set_gh_secret(name: str, value: str, repo: str) -> subprocess.CompletedProcess:
    """Set a single GitHub Actions secret via ``gh secret set``."""
    return subprocess.run(
        ["gh", "secret", "set", name, "--repo", repo, "--body", value],
        capture_output=True,
        text=True,
    )


def _set_gh_secret_from_file(
    name: str, file_path: Path, repo: str
) -> subprocess.CompletedProcess:
    """Set a GitHub Actions secret with the contents of ``file_path``."""
    with open(file_path) as f:
        return subprocess.run(
            ["gh", "secret", "set", name, "--repo", repo],
            stdin=f,
            capture_output=True,
            text=True,
        )


def _key_fingerprint(key_path: Path) -> str:
    """Return ``ssh-keygen -lf`` fingerprint, or empty string on failure."""
    result = subprocess.run(
        ["ssh-keygen", "-lf", str(key_path)],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _project_python_minor(project_root: Path) -> str | None:
    """Extract a major.minor Python version (e.g. ``3.13``) from the project's
    ``pyproject.toml``'s ``requires-python``.

    Returns ``None`` if the file or constraint is missing/unparseable, in
    which case callers should omit the ``uv python install`` step and let
    uv resolve from the lock file.
    """
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    import tomllib

    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    constraint = data.get("project", {}).get("requires-python", "")
    match = re.search(r"(\d+)\.(\d+)", constraint)
    return f"{match.group(1)}.{match.group(2)}" if match else None


def _render_deploy_workflow(on_tag: bool, python_version: str | None = None) -> str:
    """Render the GitHub Actions deploy.yml content.

    Always includes ``workflow_dispatch``. ``on_tag`` additionally fires on
    ``v*`` tag pushes. When ``python_version`` is set, an explicit
    ``uv python install`` step is emitted before ``uv sync`` to pin the
    runtime, mirroring ci.yml.
    """
    triggers = ["  workflow_dispatch:"]
    if on_tag:
        triggers.append("  push:")
        triggers.append("    tags:")
        triggers.append("      - 'v*'")
    on_block = "\n".join(triggers)
    py_step = (
        f"""
    - name: Set up Python
      run: uv python install {python_version}
"""
        if python_version
        else ""
    )
    return f"""name: Deploy

on:
{on_block}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v6

    - name: Load deploy SSH key
      uses: webfactory/ssh-agent@v0.9.1
      with:
        ssh-private-key: ${{{{ secrets.{_GH_DEPLOY_KEY_SECRET} }}}}

    - name: Trust server host key
      run: ssh-keyscan -H ${{{{ secrets.{_GH_DEPLOY_HOST_SECRET} }}}} >> ~/.ssh/known_hosts

    - name: Install uv
      uses: astral-sh/setup-uv@v7
      with:
        enable-cache: true
        cache-dependency-glob: "uv.lock"
{py_step}
    - name: Install dependencies
      run: uv sync --all-extras

    - name: Deploy
      run: uv run aegis deploy --yes
"""


def deploy_cd_setup_command(
    project_path: str | None = typer.Option(
        None, "--project-path", help="Path to the project (default: current directory)"
    ),
    repo: str | None = typer.Option(
        None,
        "--repo",
        help="GitHub repo as owner/name (default: auto-detect from git remote origin)",
    ),
    on_tag: bool = typer.Option(
        False,
        "--on-tag",
        help="Also trigger the deploy workflow on pushes to v* tags",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing GitHub secrets and deploy.yml workflow",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print planned actions without making any changes",
    ),
    keep_key: str | None = typer.Option(
        None,
        "--keep-key",
        help=(
            "Path to copy the generated private key to before cleanup. "
            "Default: no local copy (the key only lives in GitHub secrets)."
        ),
    ),
) -> None:
    """
    Wire up GitHub Actions continuous deployment for this project.

    Generates a dedicated ed25519 deploy key, installs the public key on
    the deploy server's authorized_keys, pushes the private key + host +
    user to GitHub Actions secrets, and scaffolds .github/workflows/deploy.yml.

    Requires the GitHub CLI (gh) authenticated via 'gh auth login', and an
    .aegis/deploy.yml from a prior 'aegis deploy-init'.

    Examples:\\n
        - aegis deploy-cd-setup\\n
        - aegis deploy-cd-setup --on-tag\\n
        - aegis deploy-cd-setup --force  # rotate existing key\\n
    """
    import os
    import shutil
    import tempfile

    project_root = _get_project_root(project_path)

    # Preflight: gh CLI
    if not dry_run:
        _check_gh_cli()

    # Preflight: deploy config
    config = _load_deploy_config(project_path)
    if not config:
        typer.secho(t("deploy.no_config"), fg="red", err=True)
        raise typer.Exit(1)
    host = config["server"]["host"]
    user = config["server"]["user"]

    # Preflight: repo
    repo_slug = repo or _detect_github_repo(project_root)
    if not repo_slug:
        typer.secho(t("deploy.cd_repo_not_detected"), fg="red", err=True)
        raise typer.Exit(1)

    workflow_path = project_root / ".github" / "workflows" / "deploy.yml"
    marker = f"github-actions-deploy@{repo_slug}"

    # Preflight: collisions
    existing_ci = (
        config.get("ci", {}).get("github") if isinstance(config, dict) else None
    )
    if existing_ci and not force:
        typer.secho(
            t(
                "deploy.cd_already_configured",
                fingerprint=existing_ci.get("deploy_key_fingerprint", "unknown"),
            ),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    if not force and not dry_run:
        existing_secrets = _list_gh_secrets(repo_slug)
        clash = existing_secrets & {
            _GH_DEPLOY_KEY_SECRET,
            _GH_DEPLOY_HOST_SECRET,
            _GH_DEPLOY_USER_SECRET,
        }
        if clash:
            typer.secho(
                t("deploy.cd_secret_exists", names=", ".join(sorted(clash))),
                fg="red",
                err=True,
            )
            raise typer.Exit(1)

    if workflow_path.exists() and not force:
        typer.secho(
            t("deploy.cd_workflow_exists", path=str(workflow_path)),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    # Plan
    typer.secho(
        t("deploy.cd_title", repo=repo_slug, target=f"{user}@{host}"),
        fg="blue",
        bold=True,
    )
    typer.echo(t("deploy.cd_plan_header"))
    typer.echo(t("deploy.cd_plan_keygen"))
    typer.echo(t("deploy.cd_plan_install", user=user, host=host))
    typer.echo(t("deploy.cd_plan_secrets", repo=repo_slug))
    typer.echo(
        t("deploy.cd_plan_workflow", path=str(workflow_path.relative_to(project_root)))
    )

    if dry_run:
        typer.secho(t("deploy.cd_dry_run"), fg="yellow")
        return

    # Generate key
    tempdir = Path(tempfile.mkdtemp(prefix="aegis-deploy-"))
    key_path = tempdir / "aegis_deploy_ci"
    typer.echo(t("deploy.cd_generating_key"))
    keygen = subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(key_path),
            "-N",
            "",
            "-C",
            marker,
            "-q",
        ],
        capture_output=True,
        text=True,
    )
    if keygen.returncode != 0:
        shutil.rmtree(tempdir, ignore_errors=True)
        typer.secho(
            t("deploy.cd_keygen_failed", error=keygen.stderr),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    pubkey_body = (key_path.with_suffix(".pub")).read_text().strip()
    fingerprint = _key_fingerprint(key_path.with_suffix(".pub"))

    # If rotating an existing key, remove the previous one first so we don't
    # leave dead keys valid in authorized_keys.
    if force and existing_ci:
        _remove_pubkey_from_server(marker, host, user)

    # Install pubkey on server
    typer.echo(t("deploy.cd_installing_pubkey", user=user, host=host))
    install = _install_pubkey_on_server(pubkey_body, host, user)
    if install.returncode != 0:
        shutil.rmtree(tempdir, ignore_errors=True)
        typer.secho(
            t("deploy.cd_install_failed", error=install.stderr),
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    # Push secrets
    typer.echo(t("deploy.cd_pushing_secrets", repo=repo_slug))
    secret_calls = [
        (
            _GH_DEPLOY_KEY_SECRET,
            lambda: _set_gh_secret_from_file(
                _GH_DEPLOY_KEY_SECRET, key_path, repo_slug
            ),
        ),
        (
            _GH_DEPLOY_HOST_SECRET,
            lambda: _set_gh_secret(_GH_DEPLOY_HOST_SECRET, host, repo_slug),
        ),
        (
            _GH_DEPLOY_USER_SECRET,
            lambda: _set_gh_secret(_GH_DEPLOY_USER_SECRET, user, repo_slug),
        ),
    ]
    for name, call in secret_calls:
        result = call()
        if result.returncode != 0:
            # Rollback: remove the pubkey we just installed
            _remove_pubkey_from_server(marker, host, user)
            shutil.rmtree(tempdir, ignore_errors=True)
            typer.secho(
                t("deploy.cd_secret_failed", name=name, error=result.stderr),
                fg="red",
                err=True,
            )
            raise typer.Exit(1)

    # Scaffold workflow
    typer.echo(
        t(
            "deploy.cd_writing_workflow",
            path=str(workflow_path.relative_to(project_root)),
        )
    )
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(
        _render_deploy_workflow(
            on_tag=on_tag,
            python_version=_project_python_minor(project_root),
        )
    )

    # Update .aegis/deploy.yml with ci.github block (merge, don't clobber)
    config.setdefault("ci", {})["github"] = {
        "repo": repo_slug,
        "deploy_key_fingerprint": fingerprint,
        "workflow_path": str(workflow_path.relative_to(project_root)),
    }
    # _save_deploy_config relies on cwd; pass project_path through directly
    config_path = project_root / DEPLOY_CONFIG_FILE
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

    # Optional: keep a local copy of the private key
    if keep_key:
        dest = Path(keep_key).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(key_path, dest)
        os.chmod(dest, 0o600)
        typer.echo(t("deploy.cd_kept_key", path=str(dest)))

    # Cleanup tempdir (best-effort secure delete: overwrite then unlink)
    for path in (key_path, key_path.with_suffix(".pub")):
        if path.exists():
            try:
                size = path.stat().st_size
                with open(path, "r+b") as f:
                    f.write(b"\x00" * size)
                    f.flush()
                    os.fsync(f.fileno())
            except OSError:
                pass
    shutil.rmtree(tempdir, ignore_errors=True)

    typer.secho(f"\n{t('deploy.cd_complete')}", fg="green", bold=True)
    typer.echo(t("deploy.cd_fingerprint", fingerprint=fingerprint))
    typer.echo(
        t("deploy.cd_next_commit", path=str(workflow_path.relative_to(project_root)))
    )
    typer.echo(t("deploy.cd_next_run"))
    if not keep_key:
        typer.echo("")
        typer.secho(t("deploy.cd_key_discarded"), fg="yellow")
        typer.echo(t("deploy.cd_key_recover_hint"))
