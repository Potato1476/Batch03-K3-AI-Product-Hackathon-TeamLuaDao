#!/bin/sh
set -eu

random_secret() {
  python -c 'import secrets; print(secrets.token_urlsafe(32))'
}

if [ -z "${CHAN_DETECTION_API_KEY:-}" ]; then
  CHAN_DETECTION_API_KEY="$(random_secret)"
fi
if [ -z "${CHAN_INTEL_API_KEY:-}" ]; then
  CHAN_INTEL_API_KEY="$(random_secret)"
fi
if [ -z "${CHAN_TRAINING_API_KEY:-}" ]; then
  CHAN_TRAINING_API_KEY="$(random_secret)"
fi

export CHAN_DETECTION_API_KEY
export CHAN_INTEL_API_KEY
export CHAN_TRAINING_API_KEY
export CHAN_INTEL_API_KEYS="gateway=${CHAN_INTEL_API_KEY}"
export CHAN_TRAINING_API_KEYS="detection=${CHAN_TRAINING_API_KEY}"

: "${PORT:=80}"
export PORT

if [ -z "${CHAN_DATABASE_URL:-}" ] && [ -n "${DATABASE_URL:-}" ]; then
  CHAN_DATABASE_URL="${DATABASE_URL}"
  export CHAN_DATABASE_URL
fi

if [ -z "${CHAN_DATABASE_URL:-}" ]; then
  echo "CHAN_DATABASE_URL is required. Connect a managed PostgreSQL database in Vercel." >&2
  exit 1
fi

# Vercel gives every invocation a fresh writable /tmp, so directories created
# while building the image are not guaranteed to exist at runtime.
mkdir -p \
  /tmp/nginx/client_body \
  /tmp/nginx/proxy \
  /tmp/nginx/fastcgi \
  /tmp/nginx/uwsgi \
  /tmp/nginx/scgi \
  /tmp/chan/model-registry

envsubst '${PORT}' \
  < /app/deploy/vercel/nginx.conf.template \
  > /tmp/nginx.conf

# Bind the lightweight API wait-proxy before Nginx can receive traffic. Keep it
# in a restart loop; the container runtime terminates all child processes
# together when the invocation ends.
(
  while true; do
    python /app/deploy/vercel/wait_proxy.py
    echo "wait proxy exited; restarting" >&2
    sleep 1
  done
) &

python - <<'PY'
import socket
import time

for _ in range(50):
    try:
        with socket.create_connection(("127.0.0.1", 7999), timeout=0.1):
            break
    except OSError:
        time.sleep(0.1)
else:
    raise SystemExit("wait_proxy_failed_to_bind")
PY

exec /usr/bin/supervisord \
  --nodaemon \
  --configuration /app/deploy/vercel/supervisord.conf
