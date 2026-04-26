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
