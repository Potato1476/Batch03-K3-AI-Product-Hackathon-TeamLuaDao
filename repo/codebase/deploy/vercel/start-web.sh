#!/bin/sh
set -eu

exec /usr/sbin/nginx -c /tmp/nginx.conf -g "daemon off;"
