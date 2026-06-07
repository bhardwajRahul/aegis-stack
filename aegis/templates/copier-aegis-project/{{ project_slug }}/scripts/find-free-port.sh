#!/usr/bin/env bash
#
# find-free-port.sh START [MAX]
#
# Print the first free TCP host port at or above START, scanning up to
# MAX candidates (default 20). "Free" means nothing is currently
# accepting connections on 127.0.0.1:PORT, which is the same thing
# `docker compose up` cares about when it publishes a host port.
#
# Exits non-zero (with nothing on stdout) if no free port is found.
#
# A connect-test is used instead of a bind-test so it works for
# privileged ports (e.g. 80) without root.
set -euo pipefail

start="${1:?usage: find-free-port.sh START [MAX]}"
max="${2:-20}"

is_free() {
    python3 - "$1" <<'PY'
import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.3)
try:
    sock.connect(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(0)  # nothing listening -> port is free
else:
    sys.exit(1)  # connection accepted -> port is in use
finally:
    sock.close()
PY
}

port="$start"
limit=$((start + max))
while [ "$port" -lt "$limit" ]; do
    if is_free "$port"; then
        echo "$port"
        exit 0
    fi
    port=$((port + 1))
done

echo "find-free-port: no free port in ${start}..$((limit - 1))" >&2
exit 1
