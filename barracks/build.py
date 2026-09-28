# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build the Barracks: charasheet/ for /barracks/, without Google Drive sync.

Usage, from the repo root:

    uv run barracks/build.py            # -> charasheet/dist/, if charasheet/ changed since the last build
    uv run barracks/build.py --force    # rebuild anyway

charasheet is a Vite app, so this needs Node (`npm ci` runs first whenever
package-lock.json is newer than node_modules). The output is what
web/build.py puts at /barracks/ on the public site and what serve.py serves
locally. A build takes a few seconds, so it skips itself when nothing it
reads has changed since the last one.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
APP = ROOT / "charasheet"
DIST = APP / "dist"
BASE = "/barracks/"
# Written after a successful build (Vite empties dist/ first): the base it was built for.
STAMP = DIST / ".built-for"
# What the build reads, besides node_modules.
INPUTS = ["src", "public", "scripts", "index.html", "package.json", "package-lock.json",
          "vite.config.ts", "tsconfig.json", "tsconfig.app.json", "tsconfig.node.json"]


def newest_input():
    newest = 0.0
    for name in INPUTS:
        path = APP / name
        for f in path.rglob("*") if path.is_dir() else [path]:
            # The build rewrites routeTree.gen.ts itself, so it's always newer.
            if f.is_file() and f.name != "routeTree.gen.ts":
                newest = max(newest, f.stat().st_mtime)
    return newest


def is_stale():
    if not STAMP.exists() or STAMP.read_text(encoding="utf-8") != BASE:
        return True
    return STAMP.stat().st_mtime < newest_input()


def build():
    npm = shutil.which("npm")
    if not npm:
        sys.exit("The Barracks (charasheet/) needs Node.js to build: `npm` isn't on PATH")
    installed = APP / "node_modules" / ".package-lock.json"
    lock = APP / "package-lock.json"
    # Drive sync only switches on with a client id; keep a stray one out.
    env = {k: v for k, v in os.environ.items() if not k.startswith("VITE_GDRIVE")}
    steps = [[npm, "run", "build", "--", f"--base={BASE}"]]
    if not installed.exists() or installed.stat().st_mtime < lock.stat().st_mtime:
        steps.insert(0, [npm, "ci", "--no-audit", "--no-fund"])
    for step in steps:
        try:
            subprocess.run(step, cwd=APP, env=env, check=True)
        except subprocess.CalledProcessError as e:
            sys.exit(f"charasheet: `npm {step[1]}` failed (exit {e.returncode})")
    STAMP.write_text(BASE, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build the Barracks (charasheet) for /barracks/.")
    parser.add_argument("--force", action="store_true", help="Rebuild even if nothing changed.")
    args = parser.parse_args()
    if args.force or is_stale():
        build()
        print(f"wrote {DIST.relative_to(ROOT)}/ for {BASE}")
    else:
        print(f"{DIST.relative_to(ROOT)}/ is up to date")


if __name__ == "__main__":
    main()
