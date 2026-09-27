# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Export the Threadmint Bestiary as one static file, bestiary.html.

Usage, from the repo root:

    uv run bestiary/build.py

For editing, prefer the live server (serve.py), which rereads enemies.yaml
on every change. This export is a snapshot: rebuild it after each edit.
"""
from core import HERE, load_entries, render, version

OUTPUT = HERE / "bestiary.html"


def main():
    entries, skipped = load_entries()
    if skipped:
        print("left out (no lore):", ", ".join(skipped))
    OUTPUT.write_text(render({"entries": entries, "version": version()}), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(HERE.parent)} ({len(entries)} entries)")


if __name__ == "__main__":
    main()
