# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Serve the Threadmint Market live from data/items.yaml.

Usage, from the repo root:

    uv run market/serve.py              # http://127.0.0.1:8770/
    uv run market/serve.py --port 9000 --no-browser

Every page load rereads items.yaml, the icons in icons/ and Ch.10 of the
lore-book (for the price check), and an open page reloads itself when any of
them, or the page's files (template.html, style.css, app.js), change. A YAML error
shows up as a banner on the page instead of stopping the server.
"""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import yaml

from core import ASSETS, load, render, version


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
            try:
                payload = load()
            except (yaml.YAMLError, OSError, KeyError, TypeError, ValueError) as e:
                payload = {"items": [], "warnings": [], "version": version(), "error": f"Could not read data/items.yaml:\n{e}"}
            self._send(200, render(payload, live=True).encode("utf-8"), "text/html; charset=utf-8")
        elif path in ASSETS:
            file, content_type = ASSETS[path]
            self._send(200, file.read_bytes(), content_type)
        elif path == "/version":
            self._send(200, json.dumps({"version": version()}).encode("utf-8"), "application/json")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")


def main():
    parser = argparse.ArgumentParser(description="Serve the Threadmint Market live from data/items.yaml.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab automatically.")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Threadmint Market running at {url}")
    print("Edit data/items.yaml and the page reloads itself. Press Ctrl+C to stop.")
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
