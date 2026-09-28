# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build the Threadmint's public website: the library and the bestiary as one static site.

Usage, from the repo root:

    uv run web/build.py      # -> dist/

dist/ is index.html (the landing page, web/index.html), library/ (the output
of library/build.py) and bestiary/ (bestiary.html as its index.html, plus
bestiary/images/ if there is one). It is rebuilt from scratch every time.
Upload it to any static host; vercel.json at the repo root does that on Vercel.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = ROOT / "dist"


def run(script):
    # uv sets UV to its own path for the commands it runs; the outer script's
    # environment would otherwise leak into the inner `uv run`.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    try:
        subprocess.run([os.environ.get("UV", "uv"), "run", script], cwd=ROOT, env=env, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(f"{script} failed (exit {e.returncode})")


def main():
    run("library/build.py")
    run("bestiary/build.py")

    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(ROOT / "library" / "site", DIST / "library")
    (DIST / "bestiary").mkdir()
    shutil.copy(ROOT / "bestiary" / "bestiary.html", DIST / "bestiary" / "index.html")
    if (ROOT / "bestiary" / "images").is_dir():
        shutil.copytree(ROOT / "bestiary" / "images", DIST / "bestiary" / "images")
    shutil.copy(HERE / "index.html", DIST / "index.html")

    size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file())
    print(f"wrote {DIST.relative_to(ROOT)}/ ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
