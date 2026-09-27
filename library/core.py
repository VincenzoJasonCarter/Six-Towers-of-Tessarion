"""Shared by build.py and serve.py: lore-book/*.md -> library page."""
import base64
import html
import json
import re
from pathlib import Path

import yaml
from markdown_it import MarkdownIt

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "lore-book"
CATALOGUE = HERE / "catalogue.yaml"
TEMPLATE = HERE / "template.html"
DATA_MARK = "/*__LIBRARY_DATA__*/null"
LIVE_MARK = "/*__LIBRARY_LIVE__*/false"
UNCATALOGUED = {"id": "uncatalogued", "name": "Uncatalogued", "colour": "#7a7166",
                "blurb": "Chapters not yet placed on a shelf in catalogue.yaml."}

# The lore-book is a Google Docs export split into chapters, so every image
# definition ended up at the bottom of the last chapter while the references
# are spread across the others. Definitions from all files go into one pool.
IMAGE_DEF = re.compile(r"^\[(image\d+)\]:\s*<(data:image/[^>]+)>\s*$", re.M)
IMAGE_REF = re.compile(r"!\[([^\]]*)\]\[(image\d+)\]")
# A figure on a line of its own, sometimes bolded or tab-indented (which
# CommonMark would read as a code block).
IMAGE_LINE = re.compile(r"^[ \t]*(?:\*\*)?(!\[[^\]]*\]\[image\d+\])(?:\*\*)?[ \t]*$", re.M)
IMAGE_SRC = re.compile(r'src="#img:(image\d+)"')
MATH = re.compile(r"\$(?=\S)([^$\n]+?)(?<=\S)\$")
MATH_TOKEN = re.compile(r"@@MATH(\d+)@@")
RULE_HEADING = re.compile(r"^#{1,6}\s*(\*\*)?\s*-{3,}\s*(\*\*)?\s*$", re.M)
EMPTY_HEADING = re.compile(r"^#{1,6}\s*(\*\*\s*\*\*)?\s*$", re.M)
EMPTY_ROW = re.compile(r"<tr>\s*(?:<td[^>]*>\s*</td>\s*)+</tr>\n?")
LONE_IMAGE = re.compile(r"<p>(<img [^>]*>)</p>")

md = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])


def _plain(s):
    """Title text without markdown emphasis or leading emoji."""
    s = re.sub(r"[*_`\\]", "", s).strip()
    return re.sub(r"^[^\w'’]+", "", s).strip()


def _key(s):
    return re.sub(r"\W+", "", _plain(s).casefold())


def _body(title, text):
    """Drop the heading that repeats the chapter title near the top."""
    lines = text.split("\n")
    for i, line in enumerate(lines[:15]):
        m = re.match(r"^(?:#{1,6}\s+(.*)|\*\*(.+)\*\*\s*)$", line.strip())
        if m and _key(m.group(1) or m.group(2)) == _key(title):
            del lines[i]
            break
    return "\n".join(lines)


def _render(text):
    """Markdown -> HTML, keeping TeX, images and redactions intact."""
    maths = []

    def keep_math(m):
        maths.append(m.group(1))
        return f"@@MATH{len(maths) - 1}@@"

    text = RULE_HEADING.sub("---", text)
    text = EMPTY_HEADING.sub("", text)
    text = MATH.sub(keep_math, text)
    text = IMAGE_LINE.sub(r"\1", text)
    text = IMAGE_REF.sub(lambda m: f"![{m.group(1)}](#img:{m.group(2)})", text)
    out = md.render(text)
    out = MATH_TOKEN.sub(lambda m: f'<span class="math">{html.escape(maths[int(m.group(1))])}</span>', out)
    out = IMAGE_SRC.sub(r'data-ref="\1"', out)
    out = LONE_IMAGE.sub(r'<p class="figure">\1</p>', out)
    out = EMPTY_ROW.sub("", out)
    return re.sub("█+", lambda m: f'<span class="redact" title="Redacted">{m.group(0)}</span>', out)


def _text(fragment):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def _catalogue():
    doc = yaml.safe_load(CATALOGUE.read_text(encoding="utf-8")) or {}
    shelves = [dict(s) for s in doc.get("shelves") or []]
    return shelves, doc.get("spine_titles") or {}


def load():
    """Return (payload for the page, image pool {ref: data URI})."""
    shelves, spine_titles = _catalogue()
    shelf_of = {slug: s["id"] for s in shelves for slug in s.get("books") or []}
    ids = {s["id"] for s in shelves}
    warnings = [f"catalogue.yaml: shelf {s['id']} is part_of unknown shelf {s['part_of']}"
                for s in shelves if s.get("part_of") and s["part_of"] not in ids]

    pool, books = {}, []
    for path in sorted(SOURCE.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        pool.update(IMAGE_DEF.findall(raw))
        raw = IMAGE_DEF.sub("", raw).strip()
        m = re.match(r"(\d+)-(.+)", path.stem)
        num, slug = (int(m.group(1)), m.group(2)) if m else (len(books) + 1, path.stem)
        first, _, rest = raw.partition("\n")
        if first.startswith("# "):
            title = _plain(first[2:])
        else:
            title, rest = slug.replace("-", " ").title(), raw
        page = _render(_body(title, rest))
        text = _text(page)
        books.append({
            "slug": slug, "num": num, "file": path.name, "title": title,
            "spine": spine_titles.get(slug, title), "shelf": shelf_of.get(slug, UNCATALOGUED["id"]),
            "words": len(text.split()), "html": page, "text": text,
        })

    found = {b["slug"] for b in books}
    warnings += [f"catalogue.yaml lists {slug}, but lore-book/ has no such chapter"
                 for slug in shelf_of if slug not in found]
    if any(b["shelf"] == UNCATALOGUED["id"] for b in books):
        shelves.append(dict(UNCATALOGUED))
    used = {ref for b in books for ref in re.findall(r'data-ref="(image\d+)"', b["html"])}
    warnings += [f"image {ref} is referenced but never defined" for ref in sorted(used - pool.keys(), key=_natural)]

    for s in shelves:
        s.pop("books", None)
    payload = {"books": books, "shelves": shelves, "warnings": warnings, "version": version()}
    return payload, {ref: pool[ref] for ref in used if ref in pool}


def _natural(ref):
    return int(re.sub(r"\D", "", ref) or 0)


def image(pool, ref):
    """Decode one pooled data URI -> (bytes, content type), or None."""
    uri = pool.get(ref)
    if not uri:
        return None
    head, _, data = uri.partition(",")
    return base64.b64decode(data), head[len("data:"):].split(";")[0]


def version():
    """Changes whenever a chapter, the catalogue or the template changes."""
    paths = sorted(SOURCE.glob("*.md")) + [CATALOGUE, TEMPLATE]
    return "|".join(f"{p.name}:{p.stat().st_mtime_ns}" for p in paths if p.exists())


def render(payload, live=False):
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    for mark in (DATA_MARK, LIVE_MARK):
        if mark not in page:
            raise SystemExit(f"{TEMPLATE.name} is missing {mark}")
    return page.replace(DATA_MARK, data).replace(LIVE_MARK, "true" if live else "false")
