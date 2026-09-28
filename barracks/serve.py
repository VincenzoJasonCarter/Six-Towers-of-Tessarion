# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Serve the Barracks (charasheet, built) at /barracks/, the way the public site does.

Usage, from the repo root:

    uv run barracks/serve.py              # http://127.0.0.1:8768/barracks/
    uv run barracks/serve.py --port 9000 --no-browser

Builds first if charasheet/ changed since the last build (see build.py; that
needs Node), then serves charasheet/dist/ with the same fallback as
vercel.json: a /barracks/ address that isn't a file gets index.html, so a
sheet's own address works on reload. items.json (the item index) is made
fresh from data/items.yaml on every request. It serves what was built, so it starts
at once; to see edits to charasheet's code as you make them, use its Vite
dev server instead (make barracks-dev).
"""
import argparse
import shutil
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from build import BASE, DIST, build, is_stale
from items import items_json

# Explicit, because Windows' registry can map .js to text/plain, which
# browsers refuse for module scripts.
TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json", ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, status, body, content_type, cors=False):
        self.send_response(status)
        if cors:  # the item index is for other sites' charasheets too
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if not path.startswith(BASE):
            self.send_response(302)
            self.send_header("Location", BASE)
            self.end_headers()
            return
        if path == BASE + "items.json":
            try:
                body = items_json().encode("utf-8")
            except Exception as e:  # a YAML slip shouldn't take the server down
                return self._send(500, f"data/items.yaml: {e}".encode("utf-8"), "text/plain; charset=utf-8")
            return self._send(200, body, TYPES[".json"], cors=True)
        file = (DIST / path[len(BASE):]).resolve()
        if not file.is_relative_to(DIST.resolve()) or not file.is_file():
            file = DIST / "index.html"
        self._send(200, file.read_bytes(), TYPES.get(file.suffix, "application/octet-stream"))


def main():
    parser = argparse.ArgumentParser(description="Serve the Barracks (charasheet, built) at /barracks/.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab automatically.")
    args = parser.parse_args()

    if is_stale():
        if shutil.which("npm") or not (DIST / "index.html").exists():
            print("charasheet/ changed since the last build: building it first...")
            build()
        else:
            print("charasheet/ changed since the last build, but there's no `npm` to rebuild it: serving the old build.")

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}{BASE}"
    print(f"The Barracks running at {url}")
    print("Serves the last build of charasheet/ (rebuilt on start if it changed). Press Ctrl+C to stop.")
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
