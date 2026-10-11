# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown-it-py>=3.0"]
# ///
"""Export the one-shot modules as static files in oneshots/dist/.

Usage, from the repo root:

    uv run oneshots/build.py

Writes one self-contained page per module (dist/<name>.html) and an index.
dist/ is git-ignored, and the public site build (web/build.py) never copies it:
these pages are for the DM only. For editing, prefer the live server (serve.py).
"""
from core import HERE, modules, render_index, render_module

DIST = HERE / "dist"


def main():
    DIST.mkdir(exist_ok=True)
    for path in modules():
        (DIST / f"{path.stem}.html").write_text(render_module(path), encoding="utf-8")
    (DIST / "index.html").write_text(render_index(lambda slug: f"{slug}.html"), encoding="utf-8")
    print(f"wrote {len(modules())} module(s) and an index to {DIST.relative_to(HERE.parent)}/")


if __name__ == "__main__":
    main()
