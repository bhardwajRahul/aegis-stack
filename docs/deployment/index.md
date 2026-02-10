# Deployment

Deploy your Aegis Stack project to a remote server with a single command. The deployment system handles file syncing, Docker builds, and service orchestration over SSH.

## Prerequisites

- **A VPS or server** with SSH access (Ubuntu, Debian, or Fedora)
- **SSH key authentication** configured for your server
- **rsync** installed locally (included on macOS and most Linux distributions)
- **A domain** (optional, required for TLS/HTTPS)

## Quick Start

```bash
# 1. Initialize deployment config
aegis deploy-init --host 192.168.1.100

# 2. Provision the server (installs Docker, configures firewall)
aegis deploy-setup

# 3. Deploy your application
aegis deploy
```

Your application is now running at `http://your-server-ip`.

## Configuration

Deployment settings are stored in `.aegis/deploy.yml`, created by `deploy-init`:

```yaml
# .aegis/deploy.yml
server:
  host: 192.168.1.100
  user: root
  path: /opt/my-project

docker:
  context: my-project-remote
```

| Field | Description |
|-------|-------------|
| `server.host` | Server IP address or hostname |
| `server.user` | SSH user (default: `root`) |
| `server.path` | Application directory on server (default: `/opt/{project-name}`) |
| `docker.context` | Docker context name (used by generated Makefile `deploy-*` targets) |

!!! tip "Git-ignore deploy config"
    Add `.aegis/` to your `.gitignore` to keep deployment config out of version control. `deploy-init` will remind you if it's missing.

---

## Command Reference

### aegis deploy-init

Initialize deployment configuration for a project.

**Usage:**
```bash
aegis deploy-init [OPTIONS]
```

**Options:**

- `--host, -h TEXT` — Server IP address or hostname (prompted if not provided)
- `--user, -u TEXT` — SSH user for deployment (default: `root`)
- `--path, -p TEXT` — Deployment path on server (default: `/opt/{project-name}`)
- `--project-path TEXT` — Path to the project (default: current directory)

**Examples:**
```bash
# Interactive (prompts for host)
aegis deploy-init

# Specify host directly
aegis deploy-init --host 192.168.1.100

# Custom user and path
aegis deploy-init --host myserver.com --user deploy --path /srv/myapp
```

---

### aegis deploy-setup

Provision a remote server for deployment. Run this **once** on a fresh server before your first deploy.

**Usage:**
```bash
aegis deploy-setup [OPTIONS]
```

**Options:**

- `--project-path TEXT` — Path to the project (default: current directory)

**What it does:**

1. Verifies SSH connectivity (adds host key if needed)
2. Copies `scripts/server-setup.sh` to the server
3. Runs the setup script, which:
    - Installs Docker and Docker Compose plugin
    - Installs `uv` (Python package manager)
    - Installs build tools (`build-essential` / `gcc`)
    - Configures firewall (ports 22, 80, 443)
    - Sets up Docker daemon with log rotation
    - Creates application directory with proper permissions
    - Applies system optimizations (file limits, TCP BBR)

**Examples:**
```bash
aegis deploy-setup
```

!!! note "Requires ingress component"
    The `server-setup.sh` script is generated when the ingress component is included. If you see "Server setup script not found", add ingress first: `aegis add ingress`.

---

### aegis deploy

Deploy (or redeploy) the application to the configured server.

**Usage:**
```bash
aegis deploy [OPTIONS]
```

**Options:**

- `--build / --no-build` — Build Docker images before deploying (default: `--build`)
- `--project-path TEXT` — Path to the project (default: current directory)

**What it does:**

1. **Syncs files** to the server via `rsync`
2. **Copies `.env`** file separately (excluded from rsync for safety)
3. **Stops existing services** with `docker compose down`
4. **Builds and starts services** with production compose overrides
5. **Restarts Traefik** if the ingress component is present (ensures container re-discovery)

**Excluded from sync:**

Files and directories excluded from the rsync transfer:

- `.git` — Git history
- `__pycache__` — Python cache
- `.venv` — Virtual environment
- `*.pyc` — Compiled Python files
- `.pytest_cache` — Test cache
- `.ruff_cache` — Linter cache
- `data/` — Local database files
- `.env` — Environment file (copied separately)
- `.aegis/` — Deploy configuration

**Examples:**
```bash
# Full deploy with build
aegis deploy

# Skip image rebuild (faster, uses cached images)
aegis deploy --no-build
```

---

### aegis deploy-logs

View logs from the deployed application.

**Usage:**
```bash
aegis deploy-logs [OPTIONS]
```

**Options:**

- `--follow / --no-follow, -f` — Follow log output in real-time (default: `--follow`)
- `--service, -s TEXT` — Show logs for a specific service
- `--project-path TEXT` — Path to the project (default: current directory)

**Examples:**
```bash
# Follow all service logs
aegis deploy-logs

# View logs without following
aegis deploy-logs --no-follow

# View logs for a specific service
aegis deploy-logs --service webserver
aegis deploy-logs -s traefik
aegis deploy-logs -s redis
```

---

### aegis deploy-status

Check the status of all deployed services.

**Usage:**
```bash
aegis deploy-status [OPTIONS]
```

**Options:**

- `--project-path TEXT` — Path to the project (default: current directory)

**Examples:**
```bash
aegis deploy-status
```

Shows the output of `docker compose ps` on the remote server, including container status, ports, and health.

---

### aegis deploy-stop

Stop all deployed services.

**Usage:**
```bash
aegis deploy-stop [OPTIONS]
```

**Options:**

- `--project-path TEXT` — Path to the project (default: current directory)

**Examples:**
```bash
aegis deploy-stop
```

Runs `docker compose down` on the remote server.

---

### aegis deploy-restart

Restart all deployed services.

**Usage:**
```bash
aegis deploy-restart [OPTIONS]
```

**Options:**

- `--project-path TEXT` — Path to the project (default: current directory)

**Examples:**
```bash
aegis deploy-restart
```

Runs `docker compose restart` on the remote server.

---

### aegis deploy-shell

Open an interactive shell in a deployed container.

**Usage:**
```bash
aegis deploy-shell [OPTIONS]
```

**Options:**

- `--service, -s TEXT` — Service to connect to (default: `webserver`)
- `--project-path TEXT` — Path to the project (default: current directory)

**Examples:**
```bash
# Shell into the webserver (default)
aegis deploy-shell

# Shell into Redis
aegis deploy-shell --service redis

# Shell into Traefik
aegis deploy-shell -s traefik
```

Opens a `/bin/bash` session inside the container via SSH.

---

## TLS/HTTPS with Let's Encrypt

Enable automatic HTTPS on a deployed project using `aegis ingress-enable`.

### aegis ingress-enable

Configure TLS (HTTPS) with automatic Let's Encrypt certificates.

**Usage:**
```bash
aegis ingress-enable [OPTIONS]
```

**Options:**

- `--domain, -d TEXT` — Domain name for the TLS certificate (e.g., `example.com`)
- `--email, -e TEXT` — Email for Let's Encrypt certificate notifications
- `--project-path, -p TEXT` — Path to the project (default: current directory)
- `--yes, -y` — Skip confirmation prompts

**What it does:**

1. Adds the ingress component if not already present
2. Configures `traefik/traefik.yml` with HTTPS entrypoint and ACME resolver
3. Updates Docker Compose labels for TLS routing
4. Adds `traefik-letsencrypt` Docker volume for certificate storage
5. Configures HTTP → HTTPS redirect

**Examples:**
```bash
# Interactive (prompts for domain and email)
aegis ingress-enable

# Fully specified
aegis ingress-enable --domain example.com --email admin@example.com

# Non-interactive
aegis ingress-enable -d example.com -e admin@example.com -y

# On a different project
aegis ingress-enable -p ../my-project -d example.com
```

### Full TLS Workflow

```bash
# 1. Enable TLS on your project
aegis ingress-enable --domain example.com --email admin@example.com

# 2. Deploy to your server
aegis deploy

# 3. Ensure DNS is configured
#    Point your domain's A record to your server IP

# 4. Certificates auto-provision on first request
#    Traefik handles Let's Encrypt automatically
```

After deployment:

- `http://example.com` redirects to `https://example.com`
- Certificates renew automatically before expiration
- Certificate data persists in the `traefik-letsencrypt` Docker volume

!!! warning "DNS must be configured first"
    Let's Encrypt validates domain ownership via HTTP challenge. Your domain's A record must point to the server IP **before** requesting certificates.

---

## Deployment Workflow

### First Deployment

```bash
# 1. Create project with ingress
aegis init my-app --components ingress
cd my-app

# 2. Configure and test locally
uv sync && cp .env.example .env
make serve  # Verify everything works

# 3. Set up deployment
aegis deploy-init --host your-server-ip
aegis deploy-setup

# 4. Deploy
aegis deploy
```

### Subsequent Deployments

```bash
# Make changes, then redeploy
aegis deploy

# Or skip rebuild for config-only changes
aegis deploy --no-build
```

### Monitoring

```bash
# Check service health
aegis deploy-status

# Follow logs in real-time
aegis deploy-logs

# Check a specific service
aegis deploy-logs --service webserver

# Debug inside a container
aegis deploy-shell
```

---

## Next Steps

- **[Ingress Component](../components/ingress.md)** — Traefik configuration, routing, and admin protection
- **[CLI Reference](../cli-reference.md)** — Complete command reference
- **[Evolving Your Stack](../evolving-your-stack.md)** — Adding components and deploying over time
