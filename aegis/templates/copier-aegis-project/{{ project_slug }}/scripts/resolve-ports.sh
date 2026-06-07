#!/usr/bin/env bash
#
# resolve-ports.sh [--ingress] [--postgres] [--redis] [--ollama]
#
# Pick free host ports for `make serve` / `make serve-bg` so a busy
# default (another stack running, an unrelated service on 8000, a local
# Postgres on 5432, etc.) doesn't kill the run with "bind: address
# already in use".
#
# STDOUT: `export VAR=port` lines, meant to be eval'd by the Makefile.
# STDERR: a human-readable banner telling the user where things landed.
#
# Only the HOST publish is shifted. Containers keep their fixed internal
# ports, so clients inside the compose network (which reach each service
# by name, e.g. postgres:5432) are unaffected — shifting touches only the
# developer-facing host mapping.
#
# Base ports are overridable via env vars (handy for tests and for
# projects that changed a default):
#   WEBSERVER_PORT_BASE      (default 8000)
#   INGRESS_PORT_BASE        (default 80)
#   INGRESS_DASHBOARD_BASE   (default 8080)
#   POSTGRES_PORT_BASE       (default 5432)
#   REDIS_PORT_BASE          (default 6379)
#   OLLAMA_PORT_BASE         (default 11434)
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
find_port() { bash "$here/find-free-port.sh" "$@"; }

ingress=0
postgres=0
redis=0
ollama=0
for flag in "$@"; do
    case "$flag" in
        --ingress) ingress=1 ;;
        --postgres) postgres=1 ;;
        --redis) redis=1 ;;
        --ollama) ollama=1 ;;
        *) echo "resolve-ports: unknown flag: $flag" >&2; exit 2 ;;
    esac
done

# Resolve a host port, emit its export, and report where it landed.
#   resolve_one VAR BASE LABEL [SCHEME]
# SCHEME defaults to "http://" for browser-facing services; pass "" for
# backing services (postgres/redis/ollama) that aren't reached over HTTP.
resolve_one() {
    local var="$1" base="$2" label="$3" scheme="${4-http://}" port
    port="$(find_port "$base")"
    echo "export ${var}=${port}"
    if [ "$port" = "$base" ]; then
        echo ">> ${label}: ${scheme}127.0.0.1:${port}" >&2
    else
        echo ">> port ${base} in use - ${label} on ${scheme}127.0.0.1:${port}" >&2
    fi
}

resolve_one WEBSERVER_HOST_PORT "${WEBSERVER_PORT_BASE:-8000}" webserver

if [ "$ingress" = "1" ]; then
    resolve_one INGRESS_HTTP_PORT "${INGRESS_PORT_BASE:-80}" ingress
    resolve_one INGRESS_DASHBOARD_PORT "${INGRESS_DASHBOARD_BASE:-8080}" "traefik dashboard"
fi

if [ "$postgres" = "1" ]; then
    resolve_one POSTGRES_HOST_PORT "${POSTGRES_PORT_BASE:-5432}" postgres ""
fi
if [ "$redis" = "1" ]; then
    resolve_one REDIS_HOST_PORT "${REDIS_PORT_BASE:-6379}" redis ""
fi
if [ "$ollama" = "1" ]; then
    resolve_one OLLAMA_HOST_PORT "${OLLAMA_PORT_BASE:-11434}" ollama ""
fi
