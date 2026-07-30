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

if [ -z "${CHAN_DATABASE_URL:-}" ]; then
  echo "CHAN_DATABASE_URL is required. Connect a managed PostgreSQL database in Vercel." >&2
  exit 1
fi

python /app/deploy/vercel/migrate.py
envsubst '${PORT}' \
  < /app/deploy/vercel/nginx.conf.template \
  > /tmp/nginx.conf

exec /usr/bin/supervisord \
  --nodaemon \
  --configuration /app/deploy/vercel/supervisord.conf
