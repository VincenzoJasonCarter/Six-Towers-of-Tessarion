# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Export the Threadmint Memoria as one static file, memoria.html.

Usage, from the repo root:

    uv run memoria/build.py

For editing, prefer the live server (serve.py), which rereads memoria.yaml
on every change. This export is a snapshot: rebuild it after each edit.
"""
from core import HERE, DataError, load, render, version

OUTPUT = HERE / "memoria.html"


def main():
    try:
        data = load()
    except DataError as e:
        raise SystemExit(f"data/memoria.yaml:\n{e}")
    OUTPUT.write_text(render({**data, "version": version()}), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(HERE.parent)} ({len(data['items'])} exhibits in {len(data['wings'])} rooms)")


if __name__ == "__main__":
    main()
