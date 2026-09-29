# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build the Threadmint's public website: the hub, the library, the bestiary, the Barracks and the Memoria as one static site.

Usage, from the repo root:

    uv run web/build.py      # -> dist/

dist/ is the hub's reception page at the root (index.html, style.css, app.js,
clerk.js from hub/, with the page marked data-hosted so it needs no hub
server), library/ (the output of library/build.py), bestiary/
(bestiary.html as its index.html, plus bestiary/images/ if there is one) and
barracks/ (charasheet/dist, the output of barracks/build.py) and memoria/
(memoria.html as its index.html). It is rebuilt from scratch every time. Upload it to any static host; vercel.json
at the repo root does that on Vercel.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HUB = ROOT / "hub"
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
    run("barracks/build.py")
    run("memoria/build.py")

    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(ROOT / "charasheet" / "dist", DIST / "barracks", ignore=shutil.ignore_patterns(".built-for"))
    shutil.copytree(ROOT / "library" / "site", DIST / "library")
    (DIST / "bestiary").mkdir()
    shutil.copy(ROOT / "bestiary" / "bestiary.html", DIST / "bestiary" / "index.html")
    if (ROOT / "bestiary" / "images").is_dir():
        shutil.copytree(ROOT / "bestiary" / "images", DIST / "bestiary" / "images")
    (DIST / "memoria").mkdir()
    shutil.copy(ROOT / "memoria" / "memoria.html", DIST / "memoria" / "index.html")

    page = (HUB / "index.html").read_text(encoding="utf-8")
    if "<body>" not in page:
        sys.exit("hub/index.html has no plain <body> tag to mark data-hosted")
    (DIST / "index.html").write_text(page.replace("<body>", "<body data-hosted>", 1), encoding="utf-8")
    for name in ("style.css", "app.js", "clerk.js"):
        shutil.copy(HUB / name, DIST / name)

    size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file())
    print(f"wrote {DIST.relative_to(ROOT)}/ ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
