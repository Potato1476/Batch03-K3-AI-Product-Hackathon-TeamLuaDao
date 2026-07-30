#!/bin/sh
set -eu

python - <<'PY'
import socket
import time

for _ in range(20):
    try:
        with socket.create_connection(("127.0.0.1", 7999), timeout=0.1):
            break
    except OSError:
        time.sleep(0.05)
else:
    print("wait proxy was not ready after 1 second; starting nginx anyway")
PY

exec /usr/sbin/nginx -c /tmp/nginx.conf -g "daemon off;"
