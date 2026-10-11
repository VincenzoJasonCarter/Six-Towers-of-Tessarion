# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Export the Threadmint Market as one static file, market.html.

Usage, from the repo root:

    uv run market/build.py

For editing, prefer the live server (serve.py), which rereads items.yaml on
every change. This export is a snapshot: rebuild it after each edit.
"""
from core import HERE, load, render

OUTPUT = HERE / "market.html"


def main():
    payload = load()
    for w in payload["warnings"]:
        print("warning:", w)
    OUTPUT.write_text(render(payload), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(HERE.parent)} ({len(payload['items'])} items, {OUTPUT.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
