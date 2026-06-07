"""Tests for `make serve` host-port auto-discovery (issue #702).

Generated projects ship two helper scripts that let `make serve` /
`make serve-bg` pick a free host port when the default is already taken
(another `make serve` running, an unrelated service on 8000, etc.)
instead of dying with `bind: address already in use`:

  - scripts/find-free-port.sh   -> prints the first free TCP port >= START
  - scripts/resolve-ports.sh    -> emits `export VAR=port` lines for compose

Both are plain bash (no Jinja), so they are exercised directly here.
"""

from __future__ import annotations

import socket
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

TEMPLATE_SCRIPTS = (
    Path(__file__).parent.parent
    / "aegis"
    / "templates"
    / "copier-aegis-project"
    / "{{ project_slug }}"
    / "scripts"
)

FIND_FREE_PORT = TEMPLATE_SCRIPTS / "find-free-port.sh"
RESOLVE_PORTS = TEMPLATE_SCRIPTS / "resolve-ports.sh"


@contextmanager
def occupy_port() -> Iterator[int]:
    """Bind and listen on an ephemeral port for the duration of the block."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    try:
        yield sock.getsockname()[1]
    finally:
        sock.close()


def _run(
    script: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        env=env,
    )


# --------------------------------------------------------------------------- #
# Both scripts must exist                                                      #
# --------------------------------------------------------------------------- #


def test_helper_scripts_exist() -> None:
    assert FIND_FREE_PORT.exists(), f"missing {FIND_FREE_PORT}"
    assert RESOLVE_PORTS.exists(), f"missing {RESOLVE_PORTS}"


# --------------------------------------------------------------------------- #
# find-free-port.sh                                                           #
# --------------------------------------------------------------------------- #


def _is_bindable(port: int) -> bool:
    """True if nothing else holds the port (i.e. it is genuinely free)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def test_find_free_port_returns_a_free_port_at_or_above_start() -> None:
    """Given a free start port, the result is >= start and actually free.

    Asserting `>= start` (rather than exact equality) keeps the test
    deterministic on busy hosts where `start` may get grabbed between the
    probe and the bind. The "increments past a taken port" guarantee is
    covered by test_find_free_port_skips_taken_port.
    """
    with occupy_port() as taken:
        start = taken + 1
    result = _run(FIND_FREE_PORT, str(start))
    assert result.returncode == 0, result.stderr
    chosen = int(result.stdout.strip())
    assert chosen >= start
    assert _is_bindable(chosen), f"returned port {chosen} is not actually free"


def test_find_free_port_skips_taken_port() -> None:
    """When the start port is in use, the next free port is returned."""
    with occupy_port() as taken:
        result = _run(FIND_FREE_PORT, str(taken))
    assert result.returncode == 0, result.stderr
    chosen = int(result.stdout.strip())
    assert chosen > taken, f"expected a port above {taken}, got {chosen}"


def test_find_free_port_fails_when_range_exhausted() -> None:
    """With max=1 and the only candidate taken, the script reports failure."""
    with occupy_port() as taken:
        result = _run(FIND_FREE_PORT, str(taken), "1")
    assert result.returncode != 0
    assert result.stdout.strip() == ""


# --------------------------------------------------------------------------- #
# resolve-ports.sh                                                            #
# --------------------------------------------------------------------------- #


def test_resolve_ports_emits_webserver_export() -> None:
    """Default run emits an evalable WEBSERVER_HOST_PORT export plus a banner."""
    result = _run(RESOLVE_PORTS)
    assert result.returncode == 0, result.stderr
    assert "export WEBSERVER_HOST_PORT=" in result.stdout
    # Human banner goes to stderr so stdout stays eval-safe.
    assert "127.0.0.1" in result.stderr


def test_resolve_ports_shifts_when_base_taken() -> None:
    """When the configured base port is busy, the exported port differs."""
    with occupy_port() as taken:
        env = {"WEBSERVER_PORT_BASE": str(taken), "PATH": _path()}
        result = _run(RESOLVE_PORTS, env=env)
    assert result.returncode == 0, result.stderr
    line = next(
        ln
        for ln in result.stdout.splitlines()
        if ln.startswith("export WEBSERVER_HOST_PORT=")
    )
    chosen = int(line.split("=", 1)[1])
    assert chosen != taken
    assert "in use" in result.stderr


def test_resolve_ports_ingress_emits_traefik_ports() -> None:
    """--ingress adds the traefik HTTP + dashboard exports."""
    result = _run(RESOLVE_PORTS, "--ingress")
    assert result.returncode == 0, result.stderr
    assert "export WEBSERVER_HOST_PORT=" in result.stdout
    assert "export INGRESS_HTTP_PORT=" in result.stdout
    assert "export INGRESS_DASHBOARD_PORT=" in result.stdout


# --------------------------------------------------------------------------- #
# resolve-ports.sh: backing-service host ports                                #
#                                                                             #
# Only the HOST publish is shifted (developer convenience). Containers keep   #
# their fixed internal ports, so in-network clients (which use the service    #
# name) are unaffected.                                                        #
# --------------------------------------------------------------------------- #


def _exported(stdout: str, var: str) -> int:
    line = next(ln for ln in stdout.splitlines() if ln.startswith(f"export {var}="))
    return int(line.split("=", 1)[1])


def test_resolve_ports_backing_services_off_by_default() -> None:
    """No backing-service exports unless the stack opts in via flags."""
    result = _run(RESOLVE_PORTS)
    assert result.returncode == 0, result.stderr
    assert "export POSTGRES_HOST_PORT=" not in result.stdout
    assert "export REDIS_HOST_PORT=" not in result.stdout
    assert "export OLLAMA_HOST_PORT=" not in result.stdout


def test_resolve_ports_postgres_emits_export() -> None:
    """--postgres adds a POSTGRES_HOST_PORT export."""
    result = _run(RESOLVE_PORTS, "--postgres")
    assert result.returncode == 0, result.stderr
    assert "export POSTGRES_HOST_PORT=" in result.stdout


def test_resolve_ports_postgres_shifts_when_base_taken() -> None:
    """A busy 5432 (modeled via base override) yields a different host port."""
    with occupy_port() as taken:
        env = {"POSTGRES_PORT_BASE": str(taken), "PATH": _path()}
        result = _run(RESOLVE_PORTS, "--postgres", env=env)
    assert result.returncode == 0, result.stderr
    assert _exported(result.stdout, "POSTGRES_HOST_PORT") != taken
    assert "in use" in result.stderr


def test_resolve_ports_redis_and_ollama_emit_exports() -> None:
    """--redis / --ollama add their respective host-port exports."""
    result = _run(RESOLVE_PORTS, "--redis", "--ollama")
    assert result.returncode == 0, result.stderr
    assert "export REDIS_HOST_PORT=" in result.stdout
    assert "export OLLAMA_HOST_PORT=" in result.stdout


def test_resolve_ports_backing_services_use_plain_host_banner() -> None:
    """Backing services print a plain host:port, not a misleading http:// URL."""
    result = _run(RESOLVE_PORTS, "--postgres")
    assert result.returncode == 0, result.stderr
    assert (
        "postgres: 127.0.0.1:" in result.stderr
        or "postgres on 127.0.0.1:" in result.stderr
    )
    assert "http://127.0.0.1" not in result.stderr.split("postgres", 1)[1]


def test_resolve_ports_rejects_unknown_flag() -> None:
    """A typo'd flag fails fast instead of silently emitting nothing."""
    result = _run(RESOLVE_PORTS, "--postgress")
    assert result.returncode == 2
    assert "unknown flag" in result.stderr
    assert result.stdout.strip() == ""


def _path() -> str:
    import os

    return os.environ.get("PATH", "")
