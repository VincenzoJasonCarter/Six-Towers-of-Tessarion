# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build the Threadmint's public website: the hub, the library, the Market, the bestiary, the Barracks and the Memoria as one static site.

Usage, from the repo root:

    uv run web/build.py      # -> dist/

dist/ is the hub's reception page at the root (index.html, style.css, app.js,
clerk.js from hub/, with the page marked data-hosted so it needs no hub
server, balance-patch.md for its notice board, atlas/ for the map on its
easel, as last drawn by hub/atlas.py, and fonts/, which every page uses), library/ (the output of library/build.py), market/
(market.html as its index.html), bestiary/
(bestiary.html as its index.html, plus bestiary/images/ if there is one) and
barracks/ (just items.json, the output of barracks/build.py: the hub loads the
character sheets from where charasheet is hosted) and memoria/ (memoria.html
as its index.html). It is rebuilt from scratch every time. Upload it to any static host; vercel.json
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

# The fonts every page here asks Google for, which hub/fonts/ holds. On the
# website each hall's page is pointed at those instead, the same files the
# hub uses, so a visitor downloads them once and asks no other site for them.
GOOGLE_FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
                '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
                '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700'
                '&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">\n')
OUR_FONTS = '<link rel="stylesheet" href="../fonts/fonts.css">\n'


def share_fonts(page):
    html = page.read_text(encoding="utf-8")
    if GOOGLE_FONTS in html:
        page.write_text(html.replace(GOOGLE_FONTS, OUR_FONTS), encoding="utf-8")
    elif "fonts.googleapis.com" in html:
        print(f"note: {page.relative_to(DIST)} asks Google for other fonts than hub/fonts/ has; left as it is")


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
    run("market/build.py")
    run("bestiary/build.py")
    run("barracks/build.py")
    run("memoria/build.py")

    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(ROOT / "barracks" / "dist", DIST / "barracks")
    shutil.copytree(ROOT / "library" / "site", DIST / "library")
    (DIST / "market").mkdir()
    shutil.copy(ROOT / "market" / "market.html", DIST / "market" / "index.html")
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
    shutil.copytree(HUB / "fonts", DIST / "fonts")
    for hall in ("library", "market", "bestiary", "memoria"):
        share_fonts(DIST / hall / "index.html")
    shutil.copy(ROOT / "balance-patch.md", DIST / "balance-patch.md")  # pinned to the hub's notice board
    if (HUB / "atlas").is_dir():  # the map on the hub's easel (hub/atlas.py)
        shutil.copytree(HUB / "atlas", DIST / "atlas")

    size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file())
    print(f"wrote {DIST.relative_to(ROOT)}/ ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
