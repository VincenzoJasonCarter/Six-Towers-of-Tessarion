# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "markdown-it-py>=3.0"]
# ///
"""Serve the Threadmint Library live from lore-book/.

Usage, from the repo root:

    uv run library/serve.py              # http://127.0.0.1:8767/
    uv run library/serve.py --port 9000 --no-browser

Every page load rereads the chapters, and an open page reloads itself when a
chapter, catalogue.yaml or template.html changes. A catalogue error shows up
as a banner on the page instead of stopping the server.
"""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import yaml

from core import image, load, render, version

# Chapter 23 alone is ~4 MB of base64 images, so parse once per version
# instead of on every image request.
_cache = {"version": None}


def library():
    v = version()
    if _cache["version"] != v:
        _cache["payload"], _cache["pool"] = load()
        _cache["version"] = v
    return _cache["payload"], _cache["pool"]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, status, body, content_type, cache="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            try:
                payload, _ = library()
                payload = {**payload, "images": {}}
            except (yaml.YAMLError, OSError, KeyError, TypeError) as e:
                payload = {"books": [], "shelves": [], "images": {}, "version": version(),
                           "error": f"Could not read the lore-book or library/catalogue.yaml:\n{e}"}
            self._send(200, render(payload, live=True).encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/version":
            self._send(200, json.dumps({"version": version()}).encode("utf-8"), "application/json")
        elif path.startswith("/images/"):
            try:
                found = image(library()[1], path[len("/images/"):])
            except (yaml.YAMLError, OSError, KeyError, TypeError):
                found = None
            if found:
                self._send(200, found[0], found[1], cache="max-age=60")
            else:
                self._send(404, b"Not found", "text/plain; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")


def main():
    parser = argparse.ArgumentParser(description="Serve the Threadmint Library live from lore-book/.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab automatically.")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Threadmint Library running at {url}")
    print("Edit a chapter in lore-book/ and the page reloads itself. Press Ctrl+C to stop.")
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
