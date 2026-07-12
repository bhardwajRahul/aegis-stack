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
import errno
import socket
import sys

port = int(sys.argv[1])


def attempt() -> int:
    """Probe once: 0 = free, 1 = busy, -1 = self-connect collision."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect(("127.0.0.1", port))
    except ConnectionRefusedError:
        return 0  # nothing listening -> port is free
    except OSError as exc:
        # macOS allocates ephemeral SOURCE ports sequentially, so probing
        # a port just above a recent bind makes connect() pick source ==
        # destination and fail with EINVAL (Darwin rejects self-connects).
        # The port is not actually in use; a retry draws a different
        # source port and gives the real answer.
        if exc.errno == errno.EINVAL:
            return -1
        # Timed out / unreachable: we couldn't confirm the port is free,
        # so treat it as unavailable rather than risk handing out a busy
        # port.
        return 1
    else:
        return 1  # connection accepted -> port is in use
    finally:
        sock.close()


for _ in range(3):
    verdict = attempt()
    if verdict >= 0:
        sys.exit(verdict)
sys.exit(1)  # persistent EINVAL: treat as unavailable
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
