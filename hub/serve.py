# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""The Threadmint campaign desk: one page for every Tessarion tool.

Usage, from the repo root:

    uv run hub/serve.py              # http://127.0.0.1:8760/
    uv run hub/serve.py --port 9000 --no-browser

Starts the library, bestiary, Barracks and Memoria servers on their usual ports (or
reuses one that is already running there) and shows them side by side in one
tabbed page. Ctrl+C stops everything the hub started.
"""
import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HOST = "127.0.0.1"
MAX_BODY_BYTES = 16 * 1024
PAGE_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/clerk.js": ("clerk.js", "text/javascript; charset=utf-8"),
    "/balance-patch.md": ("../balance-patch.md", "text/markdown; charset=utf-8"),  # the notice board
}

# Same commands as the Makefile targets, minus the browser tab each one opens:
# name -> (port, script, the path its page is at).
APPS = {
    "library": (8767, "library/serve.py", "/"),
    "bestiary": (8766, "bestiary/serve.py", "/"),
    "barracks": (8768, "barracks/serve.py", "/barracks/"),
    "memoria": (8769, "memoria/serve.py", "/"),
}


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, port)) == 0


class Process:
    """A child process whose last lines of output are kept for the page."""

    def __init__(self, args):
        self.log = deque(maxlen=40)
        # The hub's own uv environment would otherwise leak into the child's `uv run`.
        env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        if sys.platform == "win32":
            spawn = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        else:
            spawn = {"start_new_session": True}
        self.proc = subprocess.Popen(
            args, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", **spawn,
        )
        threading.Thread(target=self._drain, daemon=True).start()

    def _drain(self):
        for line in self.proc.stdout:
            self.log.append(line.rstrip())

    def running(self):
        return self.proc.poll() is None

    def stop(self):
        # `uv run` starts the real tool as a grandchild, so stopping uv alone
        # would leave the server running.
        if self.running():
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
            else:
                os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


class Hub:
    def __init__(self, uv):
        self.uv = uv
        self.lock = threading.Lock()
        self.apps = {}  # name -> Process, only for apps the hub started itself

    def start(self, name):
        port, script, _ = APPS[name]
        with self.lock:
            current = self.apps.get(name)
            if current and current.running():
                return
            if port_open(port):
                self.apps.pop(name, None)  # someone else's server already answers there
                return
            self.apps[name] = Process([self.uv, "run", script, "--no-browser", "--port", str(port)])

    def app_status(self, name):
        port, _, path = APPS[name]
        proc = self.apps.get(name)
        if port_open(port):
            state = "ready" if proc else "external"
        elif proc and proc.running():
            state = "starting"
        else:
            state = "stopped"
        info = {"state": state, "url": f"http://{HOST}:{port}{path}", "port": port}
        if state == "stopped" and proc:
            info["log"] = list(proc.log)
        return info

    def status(self):
        return {"apps": {name: self.app_status(name) for name in APPS}}

    def shutdown(self):
        for proc in self.apps.values():
            proc.stop()


def make_handler(hub):
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

        def _json(self, status, obj):
            self._send(status, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            path = unquote(urlparse(self.path).path)
            if path in PAGE_FILES:
                filename, content_type = PAGE_FILES[path]
                self._send(200, (HERE / filename).read_bytes(), content_type)
            elif path == "/api/status":
                self._json(200, hub.status())
            else:
                self._json(404, {"error": "Not found"})

        def do_POST(self):
            # Requiring JSON forces a CORS preflight for cross-origin requests,
            # which this server never answers, so other sites can't post here.
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._json(415, {"error": "Content-Type must be application/json"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                return self._json(413, {"error": "Request too large"})
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "Invalid JSON"})
            if not isinstance(payload, dict):
                return self._json(400, {"error": "Expected a JSON object"})

            path = urlparse(self.path).path
            if path == "/api/start" and payload.get("app") in APPS:
                hub.start(payload["app"])
            else:
                return self._json(404, {"error": "Not found"})
            self._json(200, hub.status())

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Serve the Threadmint campaign desk and the tools behind it.")
    parser.add_argument("--port", type=int, default=8760)
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab automatically.")
    args = parser.parse_args()

    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("The hub needs `uv` on PATH to start the other tools.")

    hub = Hub(uv)
    for name in APPS:
        hub.start(name)

    httpd = ThreadingHTTPServer((HOST, args.port), make_handler(hub))
    url = f"http://{HOST}:{args.port}/"
    print(f"Threadmint campaign desk running at {url}")
    for name, (port, _, path) in APPS.items():
        print(f"  {name:<9} http://{HOST}:{port}{path}")
    print("Press Ctrl+C to stop the hub and everything it started.")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        httpd.server_close()
        hub.shutdown()


if __name__ == "__main__":
    main()
