# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Build the Barracks' part of the public site: the item index, items.json.

Usage, from the repo root:

    uv run barracks/build.py    # -> barracks/dist/items.json

The character sheets themselves are charasheet, hosted by its author (the
hub loads it in a frame; see hub/app.js), so there is nothing else to build.
web/build.py puts barracks/dist/ at /barracks/ on the public site.
"""
from pathlib import Path

from items import items_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = HERE / "dist"


def main():
    DIST.mkdir(exist_ok=True)
    (DIST / "items.json").write_text(items_json(), encoding="utf-8")
    print(f"wrote {(DIST / 'items.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
