# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "scipy>=1.11", "pillow>=10"]
# ///
"""Draw the countries of Tessarion for the map on the hub's easel.

Usage, from the repo root:

    uv run hub/atlas.py                 # newest map/*.map
    uv run hub/atlas.py --map "map/Tessarion 2026-10-13.map"

Reads the Azgaar save and the lore-book, and writes hub/atlas/, one map per
country in COUNTRIES (the page has a selector for them):

    index.json       the countries, in order, with their names
    <id>.webp        the country's land and sea, shaded, as one picture
    <id>.json        everything drawn over it: borders, rivers, roads,
                     towns (with their gazetteer entries) and labels

Rebuild after editing the map or a country's gazetteer in the lore-book
(12-16 for Crownweave, 17, 18 and 25 for Thal'vireth).
"""
import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from scipy.spatial import Delaunay, Voronoi, cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "atlas"
SCALE = 8           # picture pixels per map unit, at most
MAX_SIDE = 3200     # and no picture side longer than this (a big country gets fewer pixels per unit)
PAD = 14            # map units of sea around the country in the opening view
SEA = 45            # and how far the picture of the sea runs on past that, for dragging about
UNSURVEYED = "The Compendium has not surveyed it yet; what is drawn here is the Guild's chart, and the names are the chart's."
COUNTRIES = [
    {
        "id": "crownweave", "state": 5, "name": "Crownweave", "title": "The Union of Crownweave",
        "intro": "One island in the middle sea. The Crown stands at its heart, ringed by the Crownlands and the Everstorm; "
                 "Skyloom lies west, Northreach north, Stormwake east and Emberweave south. Choose any town for what the Compendium says of it.",
        "terms": {"seat": "Seat of a Weave", "border": "Prefecture border", "fort": "Fort or stormgate", "whole": "The whole Union", "beyond": "Beyond the Union"},
        "names": {"Central City": "The Crownlands"},  # what the lore calls a prefecture, where the save differs
        "under": "Underweave",  # what lies beneath the whole island: uncharted, so the page blacks it out
        "special": {"The Crown": "Heart of the Union"},
        "lore": {  # chapter file -> where the library shelves it
            "12-crownweave.md": "Crownweave",
            "13-of-skyloom-the-loom-above.md": "Of Skyloom, the Loom Above",
            "14-of-northreach-weave-the-iron-threshold.md": "Of Northreach Weave, the Iron Threshold",
            "15-of-emberweave-the-burning-gate-of-the-south.md": "Of Emberweave, the Burning Gate of the South",
            "16-of-stormwake-the-open-harbor-of-the-east.md": "Of Stormwake, the Open Harbor of the East",
        },
    },
    {
        "id": "thalvireth", "state": 6, "name": "Thal'vireth", "title": "Thal'vireth, the Grove That Remembers",
        "intro": "The western realm, wrapped round the Verdant Tower. Six districts ring the Tower, each keeping its own pace of time; "
                 "the White Road runs east from it to Nabireth, the only harbour. Beyond the forest lie the Sound and the Hushwood, "
                 "the Elderwood west of them under the Antlers, and south across the Gulf the Desertborn's Sunward Reach. Choose any place for what the Compendium says of it.",
        "terms": {"seat": "Seat of a district", "border": "District border", "fort": "Fort or drum-tower", "whole": "The whole realm", "beyond": "Beyond Thal'vireth"},
        "special": {"Ix'kaanil": "The Tower, and seat of the High Priestess"},
        # a district's own book first, then the realm's gazetteer (only that section: the rest names towns in passing)
        "lore": {"18-of-the-white-road.md": "Of The White Road", "25-of-the-elderwood.md": "Of The Elderwood", "17-thalvireth.md": "Thal’Vireth"},
        "section": {"18-of-the-white-road.md": "From the Sea to the Steps", "25-of-the-elderwood.md": "Along the Edge", "17-thalvireth.md": "Gazetteer of the Western Reach"},
    },
    {
        "id": "obsidian", "state": 1, "name": "Obsidian Crown", "title": "The Obsidian Crown",
        "intro": "To the north, high above them all, where clouds scrape exposed stone and even dragons grow wary: the sixth and highest Tower, "
                 "and the Sangrith who dwell beneath it, few in number and vast in influence. " + UNSURVEYED,
    },
    {
        "id": "khazrund", "state": 4, "name": "Khazrund", "title": "Khazrund",
        "intro": "The jagged north-east, beneath mountains that never thaw, where the dwarves tunnelled under the Deep Tower and stacked "
                 "their cities downward instead of upward. " + UNSURVEYED,
    },
    {
        "id": "emberfall", "state": 2, "name": "Emberfall", "title": "Emberfall",
        "intro": "The far east, where the land is cracked and kissed by ember-winds, and the tieflings built tiered cities round the Ashen Tower. "
                 "Deals are struck there in whispers and ink. " + UNSURVEYED,
    },
    {
        "id": "ironhordes", "state": 3, "name": "Iron Hordes", "title": "The Iron Hordes",
        "intro": "The harsh, ragged south, where the orcs raised war-camps in the shadow of the Red Tower and carve their history into scars and steel. "
                 + UNSURVEYED,
    },
]
GENERIC_TERMS = {"seat": "Capital", "border": "Province border", "fort": "Fort", "whole": "The whole country", "beyond": "Beyond its borders"}
BIOME_TINT = {  # muted, parchment-friendly versions of Azgaar's biomes, by name
    "Hot desert": (216, 196, 146), "Cold desert": (200, 192, 162), "Savanna": (205, 196, 140),
    "Grassland": (190, 195, 138), "Tropical seasonal forest": (170, 184, 122), "Temperate deciduous forest": (160, 181, 124),
    "Tropical rainforest": (137, 168, 110), "Temperate rainforest": (143, 169, 122), "Taiga": (139, 159, 128),
    "Tundra": (186, 185, 165), "Glacier": (238, 240, 240), "Wetland": (143, 165, 146),
}


# ---------------------------------------------------------------- the save
def load(path):
    with open(path, encoding="utf-8", newline="") as f:  # the save's parts are split by CRLF, its SVG by LF
        L = f.read().split("\r\n")
    ints = lambda k: np.array(L[k].split(","), dtype=int)
    return {
        "grid": json.loads(L[6]), "gh": ints(7), "gt": ints(10), "gf": ints(9),
        "biomes": json.loads(L[3]), "states": json.loads(L[14]), "burgs": json.loads(L[15]),
        "biome": ints(16), "burg": ints(17), "river": ints(22), "state": ints(25), "prov": ints(27),
        "provinces": json.loads(L[30]), "rivers": json.loads(L[32]), "routes": json.loads(L[37]),
        "labels": json.loads(L[47]) if L[47] else [],
        "notes": {n["id"]: n for n in json.loads(L[4])} if L[4] else {},  # a village's says what its name means
        "size": tuple(int(v) for v in L[0].split("|")[4:6]),  # the map's width and height
    }


def pack_points(d):
    """The packed graph's points, as Pack.generate() rebuilds them on load."""
    g = d["grid"]
    pts, bnd = np.array(g["points"], float), np.array(g["boundary"], float)
    n = len(pts)
    tri = Delaunay(np.vstack([pts, bnd]))
    ptr, idx = tri.vertex_neighbor_vertices
    nbrs = [idx[ptr[i]:ptr[i + 1]] for i in range(n)]
    h, t, f = d["gh"], d["gt"], d["gf"]
    P, G = [], []
    for i in range(n):
        if h[i] < 20 and t[i] not in (-1, -2): continue
        if t[i] == -2 and (i % 4 == 0 or g["features"][f[i]]["type"] == "lake"): continue
        x, y = pts[i]
        P.append((x, y)); G.append(i)
        if t[i] in (1, -1) and not any(e >= n for e in nbrs[i]):
            for e in sorted(e for e in nbrs[i] if e < n):
                if i > e or t[e] != t[i]: continue
                ex, ey = pts[e]
                if (y - ey) ** 2 + (x - ex) ** 2 < g["spacing"] ** 2: continue
                P.append((round((x + ex) / 2, 1), round((y + ey) / 2, 1))); G.append(i)
    return np.array(P), np.array(G), bnd


# ---------------------------------------------------------------- the gazetteers
def clean(s):
    return re.sub(r"\*+", "", s).replace("\\", "").strip()


def first_sentences(text, limit=340):
    text = clean(" ".join(text.split()))
    out = ""
    for s in re.split(r"(?<=[.!?])\s+", text):
        if out and len(out) + len(s) > limit: break
        out = f"{out} {s}".strip()
    return out


def gazetteer(names, chapters, sections=None):
    """name -> {epithet, text, chapter} from a country's gazetteers (and Crownweave's stormgate list).
    chapters: file -> library title; sections: file -> the heading to read under, if not the whole chapter."""
    norm = lambda s: clean(s).replace("’", "'")
    known = {norm(n): n for n in names}
    found = {}
    def names_in(text):  # every known town named in bold in a stretch of text, lists split up
        out = []
        for seg in re.findall(r"\*\*(.+?)\*\*", text):
            for n in re.split(r",\s*(?:and\s+)?|\s+and\s+", seg.split(":", 1)[-1]):
                if norm(n) in known and known[norm(n)] not in out: out.append(known[norm(n)])
        return out
    def put(hits, epithet, body, chapter):
        for name in hits:
            found.setdefault(name, {"epithet": epithet, "text": first_sentences(body), "chapter": chapter})
    def split_epithet(body):  # "*The Harbor Guns.*" then the entry
        m = re.match(r"^\*([^*]+)\*\s*\n?(.*)$", body.strip(), re.S)
        return (m[1].strip().rstrip(".,"), m[2]) if m else ("", body)
    for file, chapter in chapters.items():
        text = (ROOT / "lore-book" / file).read_text(encoding="utf-8")
        if sections and file in sections:  # from that heading to the next one of its rank
            m = re.search(r"^(#+)[^\n]*" + re.escape(sections[file]) + r"[^\n]*\n", text, re.M)
            end = re.compile(r"^" + m[1] + r" ", re.M).search(text, m.end()) if m else None
            text = text[m.end():end.start() if end else None] if m else ""
        # "●        **Ix'kaanil** — *The Tower and the Tree.* ..." reads like "**Name** — ..."
        paras = [re.sub(r"^[●•]\s*", "", p.strip()) for p in re.split(r"\n\s*\n", text)]
        for k, p in enumerate(paras):
            if p.startswith("#"):  # a section given to one town: "### **V. Caer Veyn, the Harbor City**"
                hits = names_in(p) or [known[n] for n in known if n in norm(p.lstrip("# "))]
                if hits and k + 2 < len(paras) and re.fullmatch(r"\*[^*]+\*", paras[k + 1]):
                    put(hits[:1], paras[k + 1].strip("*").strip().rstrip("."), paras[k + 2], chapter)
                continue
            for line in p.splitlines():  # "* **Loomward Gate**, on the **Loom Road** ..."
                bullet = re.match(r"^\*\s+\*\*(.+?)\*\*,\s*(.+)$", line.strip())
                if bullet and norm(bullet[1]) in known:
                    put([known[norm(bullet[1])]], "Stormgate of the Crownlands", "A Crown Guard post " + bullet[2].rstrip(";.") + ".", chapter)
            if not p.startswith("**"): continue
            head, sep, rest = p.partition(" — ")
            if not sep:  # "**The Mint Line: Myros, Naupia, ...**" with the text on the next line
                head, _, rest = p.partition("\n")
            hits = names_in(head)
            if not hits:  # "**The Assay Line** — **Buclester**, **Skipseade**, ... See Of Foreign Coin."
                first = re.split(r"(?<=\.)\s", rest, maxsplit=1)[0]
                hits, rest = names_in(first), f"{clean(head)}: {rest}"
            if hits:
                put(hits, *split_epithet(rest), chapter)
    if "The Crown" in names and "12-crownweave.md" in chapters:
        crown = (ROOT / "lore-book" / "12-crownweave.md").read_text(encoding="utf-8")
        sub = re.search(r"^\*([^*\n]+)\*\s*$", crown, re.M)
        found["The Crown"] = {
            "epithet": sub[1].strip() if sub else "",
            "text": "The city itself: The Crown and its walled Weaves, on a broad hill above the Quatford, where every road in the Union knots together above the Meridian Spire.",
            "chapter": "Crownweave",
        }
    return found


def plan_id(name):
    """A town's plan, if hub/plans.py has drawn one: atlas/plans/<id>.svg"""
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "").replace("’", "")).strip("-")


# ---------------------------------------------------------------- drawing
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", help="the .map file (default: the newest in map/)")
    args = ap.parse_args()
    src = Path(args.map) if args.map else max((ROOT / "map").glob("*.map"), key=lambda p: p.stat().st_mtime)
    d = load(src)
    P, G, bnd = pack_points(d)
    if len(P) != len(d["burg"]):
        raise SystemExit(f"rebuilt {len(P)} cells but the save has {len(d['burg'])}; is this an Azgaar save of another version?")
    vor = Voronoi(np.vstack([P, bnd]))
    OUT.mkdir(exist_ok=True)
    index = []
    for country in COUNTRIES:
        draw(d, P, G, bnd, vor, src, country)
        index.append({"id": country["id"], "name": country["name"], "title": country["title"]})
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    keep = {f"{c['id']}.{ext}" for c in COUNTRIES for ext in ("json", "webp")} | {"index.json"}
    for old in OUT.iterdir():  # a country taken off the list, or the old single-map files
        if old.is_file() and old.name not in keep: old.unlink()


def draw(d, P, G, bnd, vor, src, country):
    """One country's picture and vector layers."""
    STATE, cid = country["state"], country["id"]
    NAMES = country.get("names", {})
    h = d["gh"][G]
    land = h >= 20
    island = d["gf"][G]  # the country's own landmass, not the odd stray cell the save files under it elsewhere
    ours = land & (d["state"] == STATE)
    mine = ours & (island == np.bincount(island[ours]).argmax())
    mw, mh = d["size"]  # nothing is drawn past the map's own edge (a country at the edge runs off it)
    x0, y0 = np.maximum(P[mine].min(0) - PAD, 0)
    x1, y1 = np.minimum(P[mine].max(0) + PAD, (mw, mh))
    vb = [round(float(x0), 1), round(float(y0), 1), round(float(x1 - x0), 1), round(float(y1 - y0), 1)]
    tx0, ty0, tx1, ty1 = max(x0 - SEA, 0), max(y0 - SEA, 0), min(x1 + SEA, mw), min(y1 + SEA, mh)
    tb = [round(float(tx0), 1), round(float(ty0), 1), round(float(tx1 - tx0), 1), round(float(ty1 - ty0), 1)]

    N = len(P)
    polys = [vor.vertices[vor.regions[vor.point_region[i]]] for i in range(N)]
    near = lambda pts: ((pts[:, 0] > tx0 - 20) & (pts[:, 0] < tx1 + 20) & (pts[:, 1] > ty0 - 20) & (pts[:, 1] < ty1 + 20)).any()
    visible = [i for i in range(N) if near(polys[i])]

    # -------- terrain picture: biome colours and heights smoothed between cells, hill-shaded,
    # with a crisp coastline and a paper grain
    SC = min(SCALE, MAX_SIDE / max(tx1 - tx0, ty1 - ty0))  # pixels per map unit for this country
    W, H = round((tx1 - tx0) * SC), round((ty1 - ty0) * SC)
    LO = 2  # pixels per map unit for the smooth fields
    biome_names = [b["name"] for b in d["biomes"]]
    def colour(i):
        if h[i] < 20:
            q = h[i] / 19
            return [a + (b - a) * q for a, b in zip((84, 116, 140), (120, 154, 170))]
        base = np.array(BIOME_TINT.get(biome_names[d["biome"][i]], (170, 180, 130)), float)
        if d["state"][i] != STATE:  # lands beyond the country, faded
            base = base * .35 + base.mean() * .65
        return list(base)
    def field(scale, value, cells, mode="F", bg=0):  # bg: what lies where no cell does (a corner of the map)
        im = Image.new(mode, (round((tx1 - tx0) * scale), round((ty1 - ty0) * scale)), bg)
        dr = ImageDraw.Draw(im)
        for i in cells:
            dr.polygon([((x - tx0) * scale, (y - ty0) * scale) for x, y in polys[i]], fill=value(i), outline=value(i))
        return np.asarray(im, float)
    def smooth(arr, weight, sigma):  # blur within one side of the coast only
        num = gaussian_filter(arr * weight, sigma)
        den = gaussian_filter(weight, sigma)
        return num / np.maximum(den, 1e-6)
    up = lambda a: np.asarray(Image.fromarray(a.astype("float32")).resize((W, H), Image.BICUBIC), float)

    land_lo = field(LO, lambda i: 1.0 if land[i] else 0.0, visible)
    sea_lo = 1 - land_lo
    rgb_land, rgb_sea = [], []
    for ch in range(3):
        c = field(LO, lambda i, ch=ch: colour(i)[ch], visible, bg=(84, 116, 140)[ch])
        rgb_land.append(up(smooth(c, land_lo, LO * 2.2)))
        rgb_sea.append(up(smooth(c, sea_lo, LO * 4)))
    rgb_land, rgb_sea = np.dstack(rgb_land), np.dstack(rgb_sea)

    z = up(gaussian_filter(field(LO, lambda i: float(max(h[i], 18)), visible, bg=18), LO * 3.2))
    gy, gx = np.gradient(z * SC * .55)  # height per pixel, exaggerated so hills read
    gx, gy = gx / SC, gy / SC
    az, alt = math.radians(315), math.radians(45)
    lx, ly, lz = math.cos(alt) * math.cos(az), math.cos(alt) * math.sin(az), math.sin(alt)
    shade = (-gx * lx - gy * ly + lz) / np.sqrt(gx * gx + gy * gy + 1)
    relief = np.clip(1 + (shade - lz) * 1.6, .6, 1.3)
    hill_tint = np.clip((z - 40) / 24, 0, 1)[..., None]  # high ground warms towards tan, then umber
    rgb_land = rgb_land * (1 - hill_tint * .75) + np.array([182, 152, 108]) * hill_tint * .75
    peak = np.clip((z - 66) / 14, 0, 1)[..., None]
    rgb_land = rgb_land * (1 - peak * .6) + np.array([138, 112, 90]) * peak * .6

    SS = 3  # the coastline itself, antialiased
    hi = field(SC * SS / 2, lambda i: 1.0 if land[i] else 0.0, visible)  # rounded off, as Azgaar draws coasts
    hi = gaussian_filter(hi, SC * SS / 2 * .9)
    hi = np.clip((hi - .5) * 6 + .5, 0, 1)
    lm = np.asarray(Image.fromarray((hi * 255).astype("uint8")).resize((W, H), Image.LANCZOS), float)[..., None] / 255
    ink = np.clip(1 - np.abs(lm[..., 0] - .5) * 2.4, 0, 1)[..., None]  # a thin inked line along the shore
    halo = gaussian_filter(lm[..., 0], SC * 2)[..., None]
    sea = rgb_sea + halo * np.array([62, 56, 28]) * (1 - lm)   # the shallows glow along the coast
    rgb = rgb_land * relief[..., None] * lm + sea * (1 - lm)
    rgb = rgb * (1 - ink * .85) + np.array([58, 50, 38]) * ink * .85
    rng = np.random.default_rng(7)
    grain = gaussian_filter(rng.random((H, W)), 1.6)
    rgb *= (1 + (grain - grain.mean()) * .22)[..., None]
    Image.fromarray(np.clip(rgb, 0, 255).astype("uint8")).save(OUT / f"{cid}.webp", quality=82, method=6)

    # -------- vector layers
    r1 = lambda v: round(float(v), 1)
    def edge_lines(test):
        """cell edges where test(a, b) holds, joined end to end into lines (drawn smoothed by the page)"""
        key = lambda v: (r1(v[0]), r1(v[1]))
        ends = {}
        for (a, b), verts in zip(vor.ridge_points, vor.ridge_vertices):
            if a >= N or b >= N or -1 in verts or not test(a, b): continue
            p, q = (key(vor.vertices[v]) for v in verts)
            if not (x0 - 5 < p[0] < x1 + 5 and y0 - 5 < p[1] < y1 + 5): continue
            ends.setdefault(p, []).append(q); ends.setdefault(q, []).append(p)
        lines, used = [], set()
        def walk(start, nxt):
            line, prev, cur = [start], start, nxt
            while True:
                used.add(frozenset((prev, cur))); line.append(cur)
                more = [n for n in ends[cur] if frozenset((cur, n)) not in used]
                if len(ends[cur]) != 2 or not more: return line
                prev, cur = cur, more[0]
        for start in sorted(ends, key=lambda v: len(ends[v]) == 2):  # loose ends and junctions first, loops last
            for n in ends[start]:
                if frozenset((start, n)) not in used: lines.append([list(v) for v in walk(start, n)])
        return lines
    prov_border = edge_lines(lambda a, b: land[a] and land[b] and d["state"][a] == d["state"][b] == STATE and d["prov"][a] != d["prov"][b])
    state_border = edge_lines(lambda a, b: land[a] and land[b] and d["state"][a] != d["state"][b] and STATE in (d["state"][a], d["state"][b]))
    inside = lambda x, y: x0 - 10 < x < x1 + 10 and y0 - 10 < y < y1 + 10
    under = None
    if country.get("under"):  # the country's coast, as one closed line round its own landmass
        coast = max(edge_lines(lambda a, b: mine[a] != mine[b]), key=len)
        under = {"name": country["under"], "outline": coast, "at": [r1(v) for v in P[mine].mean(0)]}

    rivers = []
    for r in d["rivers"]:
        cells = [c for c in r.get("cells", []) if 0 <= c < N]
        pts = [[r1(P[c][0]), r1(P[c][1])] for c in cells]
        if len(pts) > 1 and any(inside(*p) for p in pts):
            rivers.append({"name": r.get("name", ""), "w": round(min(1.4, .25 + r.get("discharge", 0) / 700), 2), "pts": pts})
    routes = [{"group": r["group"], "name": r.get("name") or "", "pts": [[r1(p[0]), r1(p[1])] for p in r["points"]]}
              for r in d["routes"] if any(inside(p[0], p[1]) for p in r["points"])]

    provs = {p["i"]: p for p in d["provinces"] if p and not p.get("removed")}
    seats = {p["burg"] for p in provs.values()}
    alive = [b for b in d["burgs"] if b and b.get("i") and not b.get("removed") and inside(b["x"], b["y"])]
    home = [b for b in alive if b.get("state") == STATE]
    lore = gazetteer([b["name"] for b in home], country.get("lore", {}), country.get("section"))
    for b in home:  # no gazetteer entry: the save's own note on the place, if it has one
        note = d["notes"].get(f"burg{b['i']}", {}).get("legend", "")
        if b["name"] not in lore and note.strip():
            lore[b["name"]] = {"epithet": "", "text": re.sub(r"<[^>]+>", "", note).strip()}
    towns = []
    for b in alive:
        p = provs.get(int(d["prov"][b["cell"]]))
        towns.append({
            "name": b["name"], "x": r1(b["x"]), "y": r1(b["y"]), "group": b.get("group", "town"),
            "prov": p["name"] if p else (d["states"][b["state"]]["name"] if b.get("state") else ""),
            "pop": int(round(b.get("population", 0) * 1000, -1)), "seat": b["i"] in seats,
            "home": b.get("state") == STATE,
            **({"plan": plan_id(b["name"])} if b.get("state") == STATE and (OUT / "plans" / f"{plan_id(b['name'])}.json").is_file() else {}),
            "has": [k for k in ("walls", "citadel", "temple", "plaza", "shanty") if b.get(k)] + (["port"] if b.get("port") else []),
            **({"lore": lore[b["name"]]} if b["name"] in lore and b.get("state") == STATE else {}),
        })
    labels = []
    named = [t for t in towns if t["seat"] or t["group"] in ("city", "capital")]
    obstacles = [(t["x"] - 2, t["x"] + 2 + (len(t["name"]) * 2.4 if t in named else 0), t["y"]) for t in towns] + \
        [(l["x"] - len(l["label"]["text"]) * 1.5, l["x"] + len(l["label"]["text"]) * 1.5, l["y"]) for l in d["labels"] if inside(l["x"], l["y"])]
    cells_at = cKDTree(P)
    for pid, p in provs.items():
        if p.get("state") != STATE: continue
        cells = np.where((d["prov"] == pid) & land)[0]
        text = NAMES.get(p["name"], p["name"])
        # Somewhere central where the name covers nothing else that is named at the opening zoom.
        # There, a prefecture's name runs about 4.4 map units a letter, a town's 2.4 (to the right
        # of its marker) and a landmark's 3; only the seats' and cities' names show.
        cx, cy = P[cells].mean(0)
        half = len(text) * 2.2
        def clearance(c):
            x, y = P[c]
            gap = min(max(ox0 - (x + half), (x - half) - ox1, 0) ** 2 + ((oy - y) * 1.3) ** 2 for ox0, ox1, oy in obstacles) ** .5
            on_land = land[cells_at.query([(x + half * k / 3, y) for k in range(-3, 4)])[1]].mean()  # not out over the sea
            return min(gap, 12) - .1 * math.dist((x, y), (cx, cy)) - 40 * (1 - on_land)
        c = max(cells, key=clearance)
        labels.append({"kind": "prov", "text": text, "x": r1(P[c][0]), "y": r1(P[c][1]), **({"small": True} if len(cells) < 60 else {})})
        if len(cells) >= 60: obstacles += [(P[c][0] - half - 8, P[c][0] + half + 8, P[c][1] + dy) for dy in (-5, 0, 5)]  # the next name keeps clear of this one
    for l in d["labels"]:
        if inside(l["x"], l["y"]) and l.get("label", {}).get("text"):
            labels.append({"kind": "land", "text": l["label"]["text"], "x": r1(l["x"]), "y": r1(l["y"]), "size": 4})
    data = {
        "id": cid, "name": country["name"], "title": country["title"], "intro": country["intro"],
        "terms": {**GENERIC_TERMS, **country.get("terms", {})}, "special": country.get("special", {}),
        "source": src.name, "viewBox": vb, "terrain": f"atlas/{cid}.webp", "terrainBox": tb,
        "provinceBorders": prov_border, "stateBorders": state_border,
        "rivers": rivers, "routes": routes, "towns": towns, "labels": labels,
        **({"under": under} if under else {}),
    }
    (OUT / f"{cid}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    mine_towns = [t for t in towns if t["home"]]
    with_lore = sum(1 for t in mine_towns if "lore" in t)
    print(f"{country['name']}: {W}x{H} terrain, {len(mine_towns)} towns ({with_lore} described), {len(routes)} routes, {len(rivers)} rivers")
    missing = [t["name"] for t in mine_towns if "lore" not in t]
    if country.get("lore") and missing: print("  no gazetteer entry:", ", ".join(missing))


if __name__ == "__main__":
    main()
