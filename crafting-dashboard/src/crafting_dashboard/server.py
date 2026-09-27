import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .api import ApiError, CraftingApp

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
MAX_BODY_BYTES = 64 * 1024


def make_handler(app: CraftingApp):
    post_routes = {
        "/api/craft": app.craft,
        "/api/buy": app.buy,
        "/api/inventory/add": app.add_material,
        "/api/inventory/cb": app.adjust_cb,
        "/api/resonate": app.resonate,
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _send(self, status: int, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, obj):
            self._send(status, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

        def _send_error(self, e: ApiError):
            self._send_json(e.status, {"error": e.message, **e.detail})

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in STATIC_FILES:
                filename, content_type = STATIC_FILES[url.path]
                self._send(200, (STATIC_DIR / filename).read_bytes(), content_type)
            elif url.path == "/api/state":
                character = parse_qs(url.query).get("character", ["default"])[0]
                try:
                    self._send_json(200, app.state(character))
                except ApiError as e:
                    self._send_error(e)
            else:
                self._send_json(404, {"error": "Not found"})

        def do_POST(self):
            route = post_routes.get(urlparse(self.path).path)
            if route is None:
                return self._send_json(404, {"error": "Not found"})

            # Requiring JSON forces a CORS preflight for cross-origin requests,
            # which this server never answers, so other sites can't post here.
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._send_json(415, {"error": "Content-Type must be application/json"})

            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                return self._send_json(413, {"error": "Request too large"})

            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "Invalid JSON"})
            if not isinstance(payload, dict):
                return self._send_json(400, {"error": "Expected a JSON object"})

            try:
                self._send_json(200, route(payload))
            except ApiError as e:
                self._send_error(e)

    return Handler


def serve(app: CraftingApp, host: str, port: int, open_browser: bool) -> None:
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    url = f"http://{host}:{port}/"
    print(f"Tessarion Crafting Simulator running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.4, webbrowser.open, [url]).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
