"""Shared by build.py and serve.py: enemies.yaml -> bestiary page."""
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "data" / "enemies.yaml"
TEMPLATE = HERE / "template.html"
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
    """Changes whenever enemies.yaml, the template, or any image changes."""
    paths = [SOURCE, TEMPLATE]
    if IMAGES.is_dir():
        paths += sorted(IMAGES.iterdir())
    return "|".join(f"{p.name}:{p.stat().st_mtime_ns}" for p in paths if p.exists())


def render(payload, live=False):
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    for mark in (DATA_MARK, LIVE_MARK):
        if mark not in html:
            raise SystemExit(f"{TEMPLATE.name} is missing {mark}")
    return html.replace(DATA_MARK, data).replace(LIVE_MARK, "true" if live else "false")
