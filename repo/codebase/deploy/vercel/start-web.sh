#!/bin/sh
set -eu

python - <<'PY'
import time
import urllib.error
import urllib.request

for attempt in range(150):
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8000/healthz", timeout=1
        ) as response:
            if response.status == 200:
                break
    except (OSError, urllib.error.URLError):
        pass
    time.sleep(0.1)
else:
    raise SystemExit("gateway_failed_to_start")
PY

exec /usr/sbin/nginx -c /tmp/nginx.conf -g "daemon off;"
