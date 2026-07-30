"""Small loopback proxy that absorbs Gateway cold-start time.

Vercel requires the public container port to open within 15 seconds. Nginx can
do that immediately, while the Gateway may still be connecting to PostgreSQL.
This proxy accepts the internal request, waits for Gateway health, then forwards
the request exactly once.
"""

from __future__ import annotations

import http.client
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = int(os.getenv("CHAN_WAIT_PROXY_PORT", "7999"))
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = int(os.getenv("CHAN_GATEWAY_PORT", "8000"))
READY_TIMEOUT_SECONDS = float(os.getenv("CHAN_GATEWAY_READY_TIMEOUT_SECONDS", "20"))

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def gateway_ready() -> bool:
    try:
        connection = http.client.HTTPConnection(GATEWAY_HOST, GATEWAY_PORT, timeout=0.5)
        connection.request("GET", "/healthz")
        response = connection.getresponse()
        response.read()
        connection.close()
        return response.status == 200
    except OSError:
        return False


class WaitProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _respond_json(self, status: int, payload: dict[str, str]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _proxy(self) -> None:
        if self.path == "/__wait_proxy_healthz":
            self._respond_json(200, {"status": "ok"})
            return

        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if gateway_ready():
                break
            time.sleep(0.1)
        else:
            self._respond_json(503, {"detail": "gateway_starting"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else None
        forwarded_headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
            and key.lower() not in {"content-length", "host"}
        }
        if body is not None:
            forwarded_headers["Content-Length"] = str(len(body))

        try:
            connection = http.client.HTTPConnection(
                GATEWAY_HOST,
                GATEWAY_PORT,
                timeout=60,
            )
            connection.request(
                self.command,
                self.path,
                body=body,
                headers=forwarded_headers,
            )
            response = connection.getresponse()
            response_body = response.read()
        except OSError:
            self._respond_json(502, {"detail": "gateway_unavailable"})
            return

        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() not in {
                "content-length",
                "date",
                "server",
            }:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response_body)
        connection.close()

    do_DELETE = _proxy
    do_GET = _proxy
    do_HEAD = _proxy
    do_OPTIONS = _proxy
    do_PATCH = _proxy
    do_POST = _proxy
    do_PUT = _proxy

    def log_message(self, format: str, *args: object) -> None:
        # Do not risk logging user-controlled URLs or payload-derived values.
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), WaitProxyHandler)
    server.serve_forever()
