# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Serve the Threadmint Memoria live from memoria.yaml.

Usage, from the repo root:

    uv run memoria/serve.py              # http://127.0.0.1:8769/
    uv run memoria/serve.py --port 9000 --no-browser

Every page load rereads memoria.yaml, and an open page reloads itself (in the
same room, facing the same way) when memoria.yaml or the page's files (template.html,
style.css, app.js) change. A mistake in the YAML shows up as a banner on the
page instead of stopping the server.
"""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import yaml

from core import ASSETS, DataError, load, render, version


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
                payload = {**load(), "version": version()}
            except (yaml.YAMLError, OSError, DataError) as e:
                payload = {"wings": [], "items": [], "version": version(), "error": f"Could not read data/memoria.yaml:\n{e}"}
            self._send(200, render(payload, live=True).encode("utf-8"), "text/html; charset=utf-8")
        elif path in ASSETS:
            file, content_type = ASSETS[path]
            self._send(200, file.read_bytes(), content_type)
        elif path == "/version":
            self._send(200, json.dumps({"version": version()}).encode("utf-8"), "application/json")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")


def main():
    parser = argparse.ArgumentParser(description="Serve the Threadmint Memoria live from memoria.yaml.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8769)
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab automatically.")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Threadmint Memoria running at {url}")
    print("Edit data/memoria.yaml and the page reloads itself. Press Ctrl+C to stop.")
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
