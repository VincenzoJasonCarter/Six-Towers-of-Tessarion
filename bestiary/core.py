"""Shared by build.py and serve.py: enemies.yaml -> bestiary page."""
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "data" / "enemies.yaml"
TEMPLATE = HERE / "template.html"
STYLE = HERE / "style.css"
SCRIPT = HERE / "app.js"
# serve.py serves these next to the page; the static export inlines them.
ASSETS = {"/style.css": (STYLE, "text/css; charset=utf-8"), "/app.js": (SCRIPT, "text/javascript; charset=utf-8")}
STYLE_LINK = '<link rel="stylesheet" href="style.css">'
SCRIPT_TAG = '<script src="app.js"></script>'
IMAGES = HERE / "images"
IMAGE_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
}
DATA_MARK = "/*__BESTIARY_DATA__*/null"
LIVE_MARK = "/*__BESTIARY_LIVE__*/false"

SECTIONS = [
    ("enemies", "creature"),
    ("enemy_concepts", "rumour"),
    ("unstatted_opposition", "figure"),
]


def images():
    """Map entry id -> image filename for every picture in images/."""
    if not IMAGES.is_dir():
        return {}
    return {p.stem: p.name for p in sorted(IMAGES.iterdir())
            if p.is_file() and p.suffix.lower() in IMAGE_TYPES}


def load_entries():
    """Return (entries shown in the bestiary, ids left out because they have no lore)."""
    doc = yaml.safe_load(SOURCE.read_text(encoding="utf-8")) or {}
    pictures = images()
    entries, skipped = [], []
    for key, kind in SECTIONS:
        for raw in doc.get(key) or []:
            if "lore" not in raw:
                # Concepts that only point at a full entry land here too.
                skipped.append(raw.get("id") or raw.get("name"))
                continue
            entry = {"kind": kind, **raw}
            if raw.get("id") in pictures:
                entry["image"] = f"images/{pictures[raw['id']]}"
            entries.append(entry)
    return entries, skipped


def version():
    """Changes whenever enemies.yaml, the page's files, or any image changes."""
    paths = [SOURCE, TEMPLATE, STYLE, SCRIPT]
    if IMAGES.is_dir():
        paths += sorted(IMAGES.iterdir())
    return "|".join(f"{p.name}:{p.stat().st_mtime_ns}" for p in paths if p.exists())


def render(payload, live=False):
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    for mark in (DATA_MARK, LIVE_MARK, STYLE_LINK, SCRIPT_TAG):
        if mark not in html:
            raise SystemExit(f"{TEMPLATE.name} is missing {mark}")
    if not live:
        # The export is one self-contained file, so its stylesheet and script go inline.
        html = html.replace(STYLE_LINK, f"<style>\n{STYLE.read_text(encoding='utf-8')}</style>", 1)
        html = html.replace(SCRIPT_TAG, f"<script>\n{SCRIPT.read_text(encoding='utf-8')}</script>", 1)
    return html.replace(DATA_MARK, data, 1).replace(LIVE_MARK, "true" if live else "false", 1)
