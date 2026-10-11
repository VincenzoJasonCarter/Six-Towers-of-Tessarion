# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown-it-py>=3.0"]
# ///
"""Serve the one-shot modules live from oneshots/modules/*.md.

Usage, from the repo root:

    uv run oneshots/serve.py              # http://127.0.0.1:8768/
    uv run oneshots/serve.py --port 9000 --no-browser

Every page load rereads the module, and an open page reloads itself (at the
same scroll position) when a module or the page's files (template.html,
style.css, app.js) change.
"""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from core import ASSETS, find, render_index, render_module, version


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            self._send(200, render_index(lambda slug: f"/{slug}", live=True).encode("utf-8"), "text/html; charset=utf-8")
        elif path in ASSETS:
            file, content_type = ASSETS[path]
            self._send(200, file.read_bytes(), content_type)
        elif path == "/version":
            self._send(200, json.dumps({"version": version()}).encode("utf-8"), "application/json")
        elif (module := find(path.strip("/").removesuffix(".html"))) is not None:
            self._send(200, render_module(module, live=True).encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")


def main():
    parser = argparse.ArgumentParser(description="Serve the one-shot modules live from oneshots/modules/.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab automatically.")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"One-shots running at {url}")
    print("Edit a file in oneshots/modules/ and the page reloads itself. Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.4, webbrowser.open, [url]).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
