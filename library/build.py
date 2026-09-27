# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "markdown-it-py>=3.0"]
# ///
"""Export the Threadmint Library as one static file, library.html.

Usage, from the repo root:

    uv run library/build.py

For editing, prefer the live server (serve.py), which rereads the lore-book
on every change. This export is a snapshot with every image embedded:
rebuild it after each edit.
"""
from core import HERE, load, render

OUTPUT = HERE / "library.html"


def main():
    payload, images = load()
    for w in payload["warnings"]:
        print("warning:", w)
    OUTPUT.write_text(render({**payload, "images": images}), encoding="utf-8")
    size = OUTPUT.stat().st_size / 1e6
    print(f"wrote {OUTPUT.relative_to(HERE.parent)} ({len(payload['books'])} books, {len(images)} images, {size:.1f} MB)")


if __name__ == "__main__":
    main()
