"""Shared by build.py and serve.py: memoria.yaml -> the Memoria's page."""
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "data" / "memoria.yaml"
TEMPLATE = HERE / "template.html"
STYLE = HERE / "style.css"
SCRIPT = HERE / "app.js"
# serve.py serves these next to the page; the static export inlines them.
ASSETS = {"/style.css": (STYLE, "text/css; charset=utf-8"), "/app.js": (SCRIPT, "text/javascript; charset=utf-8")}
STYLE_LINK = '<link rel="stylesheet" href="style.css">'
SCRIPT_TAG = '<script src="app.js"></script>'
DATA_MARK = "/*__MEMORIA_DATA__*/null"
LIVE_MARK = "/*__MEMORIA_LIVE__*/false"

KINDS = {"rotunda", "crypt", "wing"}
# Every room holds as many exhibits as it lists.
ROOM_SIZE = {}


class DataError(Exception):
    """memoria.yaml is readable but doesn't describe a museum the page can build."""


def load():
    """Return the page's data: the museum, its wings and its items, with accession numbers."""
    doc = yaml.safe_load(SOURCE.read_text(encoding="utf-8")) or {}
    wings = doc.get("wings") or []
    items = doc.get("items") or []
    problems = []

    by_id = {}
    for w in wings:
        wid = w.get("id")
        if not wid or wid in by_id:
            problems.append(f"wing {wid!r}: every wing needs its own id")
            continue
        w.setdefault("kind", "wing")
        if w["kind"] not in KINDS:
            problems.append(f"wing {wid}: kind must be one of {', '.join(sorted(KINDS))}")
        if w["kind"] == "wing" and not isinstance(w.get("bearing"), (int, float)):
            problems.append(f"wing {wid}: a wing needs a bearing (degrees clockwise from north)")
        w.setdefault("code", wid[:1].upper())
        by_id[wid] = w
    for kind in ("rotunda", "crypt"):
        if sum(w.get("kind") == kind for w in wings) > 1:
            problems.append(f"there can only be one {kind}")

    seen, count = set(), {}
    for item in items:
        iid, wid = item.get("id"), item.get("wing")
        if not iid or iid in seen:
            problems.append(f"item {iid!r}: every item needs its own id")
        seen.add(iid)
        if wid not in by_id:
            problems.append(f"item {iid}: no wing called {wid!r}")
            continue
        if not (item.get("model") or {}).get("type"):
            problems.append(f"item {iid}: model needs a type")
        count[wid] = count.get(wid, 0) + 1
        item.setdefault("accession", f"TM-{by_id[wid]['code']}-{count[wid]:02d}")
    for wid, n in count.items():
        limit = ROOM_SIZE.get(by_id[wid]["kind"])
        if limit and n > limit:
            problems.append(f"{by_id[wid].get('title', wid)} has room for {limit} exhibits, not {n}")

    if problems:
        raise DataError("\n".join(problems))
    return {"memoria": doc.get("memoria") or {}, "wings": wings, "items": items}


def version():
    """Changes whenever memoria.yaml or the page's files change."""
    paths = [SOURCE, TEMPLATE, STYLE, SCRIPT]
    return "|".join(f"{p.name}:{p.stat().st_mtime_ns}" for p in paths if p.exists())


def render(payload, live=False):
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    for mark in (DATA_MARK, LIVE_MARK, STYLE_LINK, SCRIPT_TAG):
        if mark not in html:
            raise SystemExit(f"{TEMPLATE.name} is missing {mark}")
    if not live:
        # The export is one self-contained file (bar the fonts, from Google
        # Fonts), so its stylesheet and script go inline.
        script = SCRIPT.read_text(encoding="utf-8")
        if "</script" in script:
            raise SystemExit(f"{SCRIPT.name} can't be inlined: it contains </script")
        html = html.replace(STYLE_LINK, f"<style>\n{STYLE.read_text(encoding='utf-8')}</style>", 1)
        html = html.replace(SCRIPT_TAG, f"<script>\n{script}</script>", 1)
    return html.replace(DATA_MARK, data, 1).replace(LIVE_MARK, "true" if live else "false", 1)
