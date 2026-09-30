"""Small local HTTP service; all records are returned without persistence."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import FEATURES, RELEASE
from .customers import import_customer

MAX_BODY_BYTES = 64 * 1024
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    server_version = "Northstar"

    def _respond(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0:
                raise ValueError
        except ValueError:
            self._respond(400, {"error": "invalid_request"})
            return False, None
        if length > MAX_BODY_BYTES:
            self._respond(413, {"error": "body_too_large"})
            return False, None
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type.lower() != "application/json":
            self._respond(415, {"error": "unsupported_media_type"})
            return False, None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._respond(400, {"error": "invalid_json"})
            return False, None
        return True, payload

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self._respond(200, {"status": "ok"})
        elif path == "/version":
            self._respond(200, {"release": RELEASE, "features": FEATURES})
        elif path in STATIC_FILES:
            filename, mime_type = STATIC_FILES[path]
            try:
                body = (WEB_ROOT / filename).read_bytes()
            except FileNotFoundError:
                self._respond(404, {"error": "not_found"})
            else:
                self._respond(200, body, mime_type)
        else:
            self._respond(404, {"error": "not_found"})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path != "/customers/import":
            self._respond(404, {"error": "not_found"})
            return
        valid, payload = self._json_body()
        if not valid:
            return
        try:
            customer = import_customer(payload)
        except ValueError:
            self._respond(422, {"error": "invalid_customer"})
        else:
            self._respond(201, {"customer": customer, "imported": True})


def serve(host="127.0.0.1", port=8080):
    with ThreadingHTTPServer((host, port), Handler) as server:
        print(f"Northstar {RELEASE} listening on http://{host}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
