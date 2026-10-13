"""Shared by build.py and serve.py: data/items.yaml -> market page.

The items, their stats and recipes come from data/items.yaml (the same file
the Barracks' items.json is made from). Each item's picture is
icons/<id>.svg (or .png, .webp, .jpg), inlined into the page. The market
chapter of the lore-book, Ch.10, is checked against items.yaml: an item it
prices differently, or one it sells that items.yaml lacks, shows up as a
warning.
"""
import base64
import json
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT / "data" / "items.yaml"
LORE = ROOT / "lore-book"
MARKET_CHAPTER = LORE / "10-official-tessarion-market-value.md"
TEMPLATE = HERE / "template.html"
STYLE = HERE / "style.css"
SCRIPT = HERE / "app.js"
KEEPER = HERE / "keeper.js"
ICONS = HERE / "icons"
ICON_TYPES = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
# serve.py serves these next to the page; the static export inlines them.
ASSETS = {"/style.css": (STYLE, "text/css; charset=utf-8"), "/app.js": (SCRIPT, "text/javascript; charset=utf-8"),
          "/keeper.js": (KEEPER, "text/javascript; charset=utf-8")}
STYLE_LINK = '<link rel="stylesheet" href="style.css">'
SCRIPT_TAG = '<script src="app.js"></script>'
KEEPER_TAG = '<script src="keeper.js"></script>'
DATA_MARK = "/*__MARKET_DATA__*/null"
LIVE_MARK = "/*__MARKET_LIVE__*/false"

# The lore-book is a Google Docs export, with images as reference-style
# definitions (see library/core.py); they are dropped before reading the table.
IMAGE_DEF = re.compile(r"^\[(image\d+)\]:\s*<(data:image/[^>]+)>\s*$", re.M)
# One cell of Ch.10's table: ![][image11] **Crude Sword** *blurb* Market Value : 1 CB
CELL = re.compile(r"!\[[^\]]*\]\[(image\d+)\]\s*\*\*(.+?)\*\*(.*?)Market Value\s*:\s*([\d.]+)\s*CB", re.S)


def _key(name):
    """'Impure Ingot (150 g)' and 'Arrow Bundle (10)' match 'Impure Ingot' and 'Arrow Bundle'."""
    name = re.sub(r"\(.*?\)", "", name.replace("\\", ""))
    return re.sub(r"\W+", "", name.casefold())


def _icon_files():
    """{item id: icon file} for every picture in icons/."""
    if not ICONS.is_dir():
        return {}
    return {p.stem: p for p in sorted(ICONS.iterdir()) if p.is_file() and p.suffix.lower() in ICON_TYPES}


def _icon(path):
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{ICON_TYPES[path.suffix.lower()]};base64,{data}"


def _market_listing():
    """Ch.10's table as {name key: (display name, price)}."""
    if not MARKET_CHAPTER.exists():
        return {}
    text = MARKET_CHAPTER.read_text(encoding="utf-8")
    return {_key(name): (name.replace("\\", "").strip(), float(price))
            for _, name, _, price in CELL.findall(IMAGE_DEF.sub("", text))}


def load():
    """Return the page's payload: items, and warnings about the data."""
    raw = yaml.safe_load(SOURCE.read_text(encoding="utf-8")) or []
    listing = _market_listing()
    icons = _icon_files()
    names = {item["name"] for item in raw}
    warnings, items, seen = [], [], set()

    for item in raw:
        if item.get("hidden"):
            continue
        entry = {k: v for k, v in item.items() if k != "hidden"}
        if item["id"] in icons:
            entry["image"] = _icon(icons[item["id"]])
        listed = listing.get(_key(item["name"]))
        if listed:
            seen.add(_key(item["name"]))
            _, price = listed
            if item.get("market_value") is None:
                warnings.append(f"{item['name']}: Ch.10 sells it for {price:g} CB, items.yaml has no market_value")
            elif abs(float(item["market_value"]) - price) > 1e-9:
                warnings.append(f"{item['name']}: items.yaml says {item['market_value']:g} CB, Ch.10 says {price:g} CB")
        for material, _ in item.get("materials") or []:
            if material not in names:
                warnings.append(f"{item['name']}: its recipe calls for {material}, which items.yaml doesn't list")
        if item.get("upgrade_from") and item["upgrade_from"] not in names:
            entry["upgrade_missing"] = True
        items.append(entry)

    for key, (name, price) in listing.items():
        if key not in seen and not any(_key(i["name"]) == key for i in raw):
            warnings.append(f"{name}: Ch.10 sells it for {price:g} CB, but items.yaml has no entry for it")
    return {"items": items, "warnings": warnings, "version": version()}


def version():
    """Changes whenever items.yaml, Ch.10, an icon or the page's files change."""
    paths = [SOURCE, MARKET_CHAPTER, TEMPLATE, STYLE, SCRIPT, KEEPER, *_icon_files().values()]
    return "|".join(f"{p.name}:{p.stat().st_mtime_ns}" for p in paths if p.exists())


def render(payload, live=False):
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    for mark in (DATA_MARK, LIVE_MARK, STYLE_LINK, SCRIPT_TAG, KEEPER_TAG):
        if mark not in html:
            raise SystemExit(f"{TEMPLATE.name} is missing {mark}")
    if not live:
        # The export is one self-contained file, so its stylesheet and scripts go inline.
        html = html.replace(STYLE_LINK, f"<style>\n{STYLE.read_text(encoding='utf-8')}</style>", 1)
        html = html.replace(SCRIPT_TAG, f"<script>\n{SCRIPT.read_text(encoding='utf-8')}</script>", 1)
        html = html.replace(KEEPER_TAG, f"<script>\n{KEEPER.read_text(encoding='utf-8')}</script>", 1)
    return html.replace(DATA_MARK, data, 1).replace(LIVE_MARK, "true" if live else "false", 1)
