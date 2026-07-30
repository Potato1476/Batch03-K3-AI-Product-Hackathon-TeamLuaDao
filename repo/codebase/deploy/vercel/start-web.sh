#!/bin/sh
set -eu

python - <<'PY'
import time
import urllib.error
import urllib.request

for _ in range(50):
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8000/healthz", timeout=0.5
        ) as response:
            if response.status == 200:
                break
    except (OSError, urllib.error.URLError):
        time.sleep(0.1)
else:
    print("gateway was not ready after 5 seconds; starting nginx anyway")
PY

exec /usr/sbin/nginx -c /tmp/nginx.conf -g "daemon off;"
