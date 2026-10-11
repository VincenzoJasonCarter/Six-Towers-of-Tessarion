"""Shared by build.py and serve.py: the one-shot modules (modules/*.md) -> the DM's pages."""
import re
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt

HERE = Path(__file__).resolve().parent
MODULES = HERE / "modules"
TEMPLATE = HERE / "template.html"
STYLE = HERE / "style.css"
SCRIPT = HERE / "app.js"
# serve.py serves these next to the page; the static export inlines them.
ASSETS = {"/style.css": (STYLE, "text/css; charset=utf-8"), "/app.js": (SCRIPT, "text/javascript; charset=utf-8")}
STYLE_LINK = '<link rel="stylesheet" href="style.css">'
SCRIPT_TAG = '<script src="app.js"></script>'
MARKS = ("<!--TITLE-->", "<!--HEADING-->", "<!--EYEBROW-->", "<!--TOC-->", "<!--BODY-->", "/*__CLASS__*/", "/*__LIVE__*/false", '/*__VERSION__*/""')

MD = MarkdownIt("commonmark").enable("table")


def modules():
    return sorted(MODULES.glob("*.md"))


def find(slug):
    path = MODULES / f"{slug}.md"
    return path if path.is_file() else None


def _slug(text, taken):
    s = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-") or "bagian"
    base, n = s, 2
    while s in taken:
        s, n = f"{base}-{n}", n + 1
    taken.add(s)
    return s


def parse(path):
    """Title (the first H1), the italic line under it, the rendered body and its section list."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A# (.+)\n", text)
    title = m.group(1).strip() if m else path.stem
    rest = text[m.end():] if m else text
    sub = re.match(r"\s*\*([^*\n]+)\*\s*\n", rest)
    eyebrow = sub.group(1).strip() if sub else "One-shot"
    if sub:
        rest = rest[sub.end():]
    html = MD.render(rest)

    toc, taken = [], set()

    def anchor(match):
        inner = match.group(1)
        sid = _slug(inner, taken)
        toc.append((sid, re.sub(r"<[^>]+>", "", inner)))
        return f'<h2 id="{sid}">{inner}</h2>'

    html = re.sub(r"<h2>(.*?)</h2>", anchor, html)
    html = html.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    html = html.replace('<a href="http', '<a target="_blank" rel="noopener" href="http')
    return {"slug": path.stem, "title": title, "eyebrow": eyebrow, "body": html, "toc": toc}


def version():
    """Changes whenever a module or the page's files change."""
    paths = [TEMPLATE, STYLE, SCRIPT, *modules()]
    return "|".join(f"{p.name}:{p.stat().st_mtime_ns}" for p in paths if p.exists())


def _fill(title, heading, eyebrow, toc_html, body, cls, live):
    html = TEMPLATE.read_text(encoding="utf-8")
    for mark in (*MARKS, STYLE_LINK, SCRIPT_TAG):
        if mark not in html:
            raise SystemExit(f"{TEMPLATE.name} is missing {mark}")
    if not live:
        # The export is one self-contained file (bar the fonts, from Google Fonts).
        script = SCRIPT.read_text(encoding="utf-8")
        if "</script" in script:
            raise SystemExit(f"{SCRIPT.name} can't be inlined: it contains </script")
        html = html.replace(STYLE_LINK, f"<style>\n{STYLE.read_text(encoding='utf-8')}</style>", 1)
        html = html.replace(SCRIPT_TAG, f"<script>\n{script}</script>", 1)
    for mark, value in zip(MARKS, (escape(title), escape(heading), escape(eyebrow), toc_html, body, cls,
                                   "true" if live else "false", f'"{escape(version())}"' if live else '""')):
        html = html.replace(mark, value, 1)
    return html


def render_module(path, live=False):
    m = parse(path)
    toc = "\n".join(f'<li><a href="#{sid}">{escape(label)}</a></li>' for sid, label in m["toc"])
    return _fill(m["title"], m["title"], m["eyebrow"], toc, m["body"], "module", live)


def render_index(href, live=False):
    """The list of modules. href(slug) gives each module's link (a route live, a file in the export)."""
    items = []
    for path in modules():
        m = parse(path)
        items.append(f'<li><a href="{href(m["slug"])}"><b>{escape(m["title"])}</b><span>{escape(m["eyebrow"])}</span></a></li>')
    body = f'<ul class="shelf">{"".join(items)}</ul>' if items else '<p class="empty">Belum ada module. Tambahkan file .md di oneshots/modules/.</p>'
    return _fill("One-shots", "One-shots", "Khusus DM · bukan untuk pemain", "", body, "index", live)
