# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "shapely>=2.0", "scipy>=1.11", "pillow>=10"]
# ///
"""Draw town plans for the map on the hub's easel.

Usage, from the repo root:

    uv run hub/plans.py                  # every town in hub/towns/
    uv run hub/plans.py crownweave       # one country
    uv run hub/plans.py fjerfi phais     # or some towns

This file is the toolkit: the Plan (an SVG drawn in ink on parchment), the
drawing helpers, and build(), which lays out a whole town from a description.
The towns themselves live one file each in hub/towns/<country>/<town>.py, so
the folder shows at a glance which towns have a plan. A town module sets

    TOWN = "Fjerfi"            # its name on the map, which links it to the atlas
    EPITHET = "Seat of the Weave"

and either SPEC (a description for build(); see its docstring) or draw(), a
function that returns a Plan it has drawn itself (Nabireth does this). With
"from_map": True in SPEC, a town's roads and river are the ones the Azgaar map
has round it (map_town()): each road leaves town the way it does on the map.

Writes hub/atlas/plans/<id>.svg and <id>.json (the places marked on the plan,
each with its entry). hub/atlas.py gives a town the plan's button when a plan
exists under its name, so run this first (`make atlas` runs both).

Each plan is laid out by hand where the lore-book says where things are and
filled in by the code everywhere else: lanes, houses, trees, fields. Layouts
are seeded, so a plan only changes when its description does.
"""
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity

HERE = Path(__file__).resolve().parent
OUT = HERE / "atlas" / "plans"
TOWNS = HERE / "towns"

INK = "#4a3a28"
PAPER = "#efe4c8"
WATER = "#a9c0c4"
SHALLOW = "#c3d3cf"
HOUSE = "#cbb08a"
PALETTES = {
    "elf": ("#c9ad86", "#cfb48d", "#c4a67e", "#d2ba95"),        # grown wood
    "human": ("#c99a78", "#bf8c6c", "#d1a986", "#b98868", "#c7a07e", "#a98f78"),  # tile, thatch and slate
    "dwarf": ("#a89c8a", "#9d917f", "#b3a792", "#958a7a"),      # stone
    "tiefling": ("#c48a6a", "#b77c62", "#cf9e78", "#a8826a"),
}
GROWN = "#b9a079"   # grown-wood halls, a shade darker than houses
MARK = "#a5532f"    # the places on the key
TREE = "#9bab78"
ROAD = "#f4ecd8"
WHITE_ROAD = "#fbf8ef"


def esc(text):
    """Text safe to put in the SVG (a town may well have a tavern called the Keel & Knot)."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def path_d(coords, closed=False):
    pts = list(coords)
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    return d + ("Z" if closed else "")


def poly_d(geom):
    """SVG path data for a (multi)polygon, holes included."""
    geoms = getattr(geom, "geoms", [geom])
    out = []
    for g in geoms:
        if g.is_empty: continue
        out.append(path_d(g.exterior.coords, True))
        out += [path_d(r.coords, True) for r in g.interiors]
    return " ".join(out)


def smooth(line, rounds=4):
    """Chaikin's corner-cutting: a hand-drawn curve through the points."""
    pts = list(line.coords)
    for _ in range(rounds):
        out = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            out += [(.75 * x0 + .25 * x1, .75 * y0 + .25 * y1), (.25 * x0 + .75 * x1, .25 * y0 + .75 * y1)]
        pts = out + [pts[-1]]
    return LineString(pts)


def wiggle(line, amp, freq, rng, step=12):
    """A street drawn by hand: the line, resampled and nudged sideways a little."""
    L = line.length
    n = max(2, int(L / step))
    phase = rng.uniform(0, 6.3)
    pts = []
    for k in range(n + 1):
        p = line.interpolate(L * k / n)
        a = line.interpolate(min(L, L * k / n + 1)); b = line.interpolate(max(0, L * k / n - 1))
        tx, ty = a.x - b.x, a.y - b.y
        tl = math.hypot(tx, ty) or 1
        off = amp * math.sin(freq * L * k / n / 100 + phase) * math.sin(math.pi * k / n)
        pts.append((p.x - ty / tl * off, p.y + tx / tl * off))
    return LineString(pts)


class Plan:
    def __init__(self, pid, width, height, seed):
        self.id, self.W, self.H = pid, width, height
        self.rng = np.random.default_rng(seed)
        self.layers = {k: [] for k in ("ground", "water", "contours", "streets", "piers", "houses", "marks", "trees", "boats", "labels", "key")}
        self.taken = {}      # footprints nothing else may overlap, filed by 50 m square
        self.places = []
        self.palette = PALETTES["elf"]
        self.corner = .22      # how round a house's corners are, as a share of its shorter side
        self.mpu = 1.0         # metres per unit, for the scale bar

    # ---- bookkeeping
    @staticmethod
    def _cells(geom, size=50):
        x0, y0, x1, y1 = geom.bounds
        return [(i, j) for i in range(int(x0 // size), int(x1 // size) + 1) for j in range(int(y0 // size), int(y1 // size) + 1)]

    def block(self, geom):
        if geom.is_empty: return
        for c in self._cells(geom):
            self.taken.setdefault(c, []).append(geom)

    def free(self, geom):
        return not any(t.intersects(geom) for c in self._cells(geom) for t in self.taken.get(c, ()))

    # ---- drawing
    def add(self, layer, svg):
        self.layers[layer].append(svg)

    def street(self, line, width, colour=ROAD, name=None, layer="streets", edge=True):
        d = path_d(line.coords)
        if edge:
            self.add(layer, f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{width + 2.4:.1f}" stroke-linecap="round" stroke-linejoin="round" opacity=".55"/>')
        self.add(layer, f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
        self.block(line.buffer(width / 2 + 2))

    def house(self, cx, cy, w, d, ang, fill=HOUSE, area=None, water_ok=None):
        """One house, w along its street and d deep, if there is room for it. Grown wood
        has no corners, so its corners are rounded."""
        rect = affinity.translate(affinity.rotate(box(-w / 2, -d / 2, w / 2, d / 2), ang, origin=(0, 0)), cx, cy)
        inside = area is None or area.contains(rect) or (water_ok is not None and water_ok.contains(rect))
        if not inside or not self.free(rect):
            return False
        self.block(rect.buffer(1.0))
        shade = fill if fill != HOUSE else self.palette[int(self.rng.integers(len(self.palette)))]
        self.add("houses", f'<rect x="{-w / 2:.1f}" y="{-d / 2:.1f}" width="{w:.1f}" height="{d:.1f}" rx="{min(w, d) * self.corner:.1f}" '
                           f'fill="{shade}" stroke="{INK}" stroke-width=".7" stroke-opacity=".55" transform="translate({cx:.1f} {cy:.1f}) rotate({ang:.1f})"/>')
        return True

    def houses_along(self, line, area, depth=(10, 18), width=(8, 15), gap=(.6, 2.5), setback=(1, 2.5), fill=HOUSE, both=True, water_ok=None, street_w=8):
        """Lots on either side of a street, each house square to it."""
        rng = self.rng
        L, s = line.length, 0.0
        while s < L:
            w = rng.uniform(*width)
            mid = line.interpolate(s + w / 2)
            a, b = line.interpolate(min(L, s + w / 2 + 1)), line.interpolate(max(0, s + w / 2 - 1))
            tx, ty = a.x - b.x, a.y - b.y
            tl = math.hypot(tx, ty) or 1
            tx, ty = tx / tl, ty / tl
            for side in ((1, -1) if both else (1,)):
                dpt, sb = rng.uniform(*depth), rng.uniform(*setback)
                nx, ny = -ty * side, tx * side
                off = street_w / 2 + 2.5 + sb + dpt / 2  # clear of the street itself
                self.house(mid.x + nx * off, mid.y + ny * off, w, dpt, math.degrees(math.atan2(ty, tx)), fill, area, water_ok)
            s += w + rng.uniform(*gap)

    def infill(self, area, count, streets, density=lambda x, y: 1.0, size=(7, 13)):
        """Houses in the backs of the blocks, each turned to face its nearest street."""
        rng = self.rng
        minx, miny, maxx, maxy = area.bounds
        placed = tries = 0
        while placed < count and tries < count * 40:
            tries += 1
            x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
            if rng.random() > density(x, y): continue
            pt = Point(x, y)
            near = min(streets, key=lambda ln: ln.distance(pt))
            t = near.project(pt)
            a, b = near.interpolate(t + 1), near.interpolate(max(0, t - 1))
            ang = math.degrees(math.atan2(a.y - b.y, a.x - b.x))
            if self.house(x, y, rng.uniform(*size), rng.uniform(*size), ang + rng.uniform(-8, 8), area=area):
                placed += 1

    def landmark(self, pid, geom, fill=MARK, layer="marks", extra=""):
        self.block(geom.buffer(3))
        self.add(layer, f'<path d="{poly_d(geom)}" fill="{fill}" stroke="{INK}" stroke-width="1.6" data-place="{pid}" class="place"{extra}/>')

    def trees(self, region, count, r=(5, 11), colour=TREE):
        """Lone trees, or a few together."""
        rng = self.rng
        minx, miny, maxx, maxy = region.bounds
        placed = tries = 0
        while placed < count and tries < count * 30:
            tries += 1
            x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
            for k in range(int(rng.integers(1, 4))):
                rad = rng.uniform(*r)
                cx, cy = x + rng.uniform(-1, 1) * rad * 1.6 * (k > 0), y + rng.uniform(-1, 1) * rad * 1.6 * (k > 0)
                c = Point(cx, cy).buffer(rad, 8)
                if region.contains(c) and self.free(c):
                    self.block(c)
                    self.add("trees", f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{colour}" stroke="{INK}" stroke-width=".8"/>'
                                      f'<circle cx="{cx - rad * .3:.1f}" cy="{cy - rad * .3:.1f}" r="{rad * .45:.1f}" fill="#fff" opacity=".12"/>')
                    placed += 1

    def forest(self, region, count, r=(9, 18)):
        """Close canopy: crowns run together into one mass with a scalloped edge."""
        rng = self.rng
        minx, miny, maxx, maxy = region.bounds
        crowns = []
        while len(crowns) < count:
            x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
            if region.contains(Point(x, y)):
                crowns.append((x, y, rng.uniform(*r)))
        mass = unary_union([Point(x, y).buffer(rr, 10) for x, y, rr in crowns]).intersection(region)
        self.block(mass)
        self.add("trees", f'<path d="{poly_d(mass)}" fill="#869b67" stroke="{INK}" stroke-width="1.2"/>')
        for x, y, rr in crowns:
            self.add("trees", f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr * .62:.1f}" fill="#9aae78" opacity=".55"/>')
        return mass

    def label(self, x, y, text, size=16, cls="tp-lbl", anchor="middle", rotate=0, pid=None, spacing=None):
        extra = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate else ""
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        place = f' data-place="{pid}"' if pid else ""
        self.add("labels", f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}{" place" if pid else ""}" font-size="{size}" text-anchor="{anchor}"{ls}{extra}{place}>{esc(text)}</text>')

    def place(self, pid, name, epithet, text, source=None):
        self.places.append({"id": pid, "name": name, "epithet": epithet, "text": text, **({"source": source} if source else {})})

    def svg(self, title, subtitle):
        W, H = self.W, self.H
        style = f"""<style>
  .tp-lbl {{ font-family: "Cormorant Garamond", "EB Garamond", Georgia, serif; font-weight: 700; fill: {INK}; paint-order: stroke; stroke: {PAPER}; stroke-width: 4px; stroke-linejoin: round; }}
  .tp-area {{ font-family: "Cormorant Garamond", "EB Garamond", Georgia, serif; font-weight: 600; font-style: italic; fill: {INK}; opacity: .75; paint-order: stroke; stroke: {PAPER}; stroke-width: 3px; }}
  .tp-sea {{ font-family: "Cormorant Garamond", "EB Garamond", Georgia, serif; font-style: italic; fill: #3f5a66; opacity: .8; }}
  .tp-road {{ font-family: "Cormorant Garamond", "EB Garamond", Georgia, serif; font-weight: 600; fill: {INK}; opacity: .8; }}
  .tp-title {{ font-family: "Cormorant Garamond", "EB Garamond", Georgia, serif; font-weight: 700; fill: {INK}; }}
  .tp-sub {{ font-family: "EB Garamond", Georgia, serif; font-style: italic; fill: {INK}; }}
  .place {{ cursor: pointer; }}
</style>"""
        defs = f"""<defs>
  <filter id="paper" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="4"/><feColorMatrix values="0 0 0 0 .3  0 0 0 0 .22  0 0 0 0 .1  0 0 0 .09 0"/><feComposite in2="SourceGraphic" operator="in"/></filter>
  <pattern id="ripple" width="26" height="12" patternUnits="userSpaceOnUse"><path d="M2 8q4-4 8 0t8 0" fill="none" stroke="#6d8a94" stroke-width=".9" opacity=".5"/></pattern>
  <pattern id="grass" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="4" cy="6" r=".9" fill="{INK}" opacity=".18"/><circle cx="15" cy="16" r=".9" fill="{INK}" opacity=".18"/><path d="M11 4l1-3 1 3" fill="none" stroke="{INK}" stroke-width=".6" opacity=".2"/></pattern>
</defs>"""
        body = "\n".join("\n".join(self.layers[k]) for k in self.layers)
        frame = f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" fill="none" stroke="{INK}" stroke-width="2.5"/><rect x="13" y="13" width="{W - 26}" height="{H - 26}" fill="none" stroke="{INK}" stroke-width=".8"/>'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" class="townplan" role="img" aria-label="Plan of {esc(title)}">\n'
                f'<title>{esc(title)}, {esc(subtitle)}</title>\n{style}\n{defs}\n<rect width="{W}" height="{H}" fill="{PAPER}"/>\n{body}\n'
                f'<rect width="{W}" height="{H}" filter="url(#paper)"/>\n{frame}\n</svg>\n')


def compass(p, x, y, r=34):
    p.add("key", f'<g transform="translate({x} {y})" opacity=".85"><circle r="{r}" fill="none" stroke="{INK}" stroke-width="1"/>'
                 f'<path d="M0 {-r - 10}L6 0 0 {r * .5}-6 0Z" fill="{INK}"/><path d="M0 {-r - 10}L6 0H-6Z" fill="{MARK}"/>'
                 f'<text y="{-r - 14}" class="tp-title" font-size="16" text-anchor="middle">N</text></g>')


def scale_bar(p, x, y, metres=200):
    u = metres / p.mpu  # its length on the plan
    p.add("key", f'<g transform="translate({x} {y})"><rect width="{u / 2:.1f}" height="7" fill="{INK}"/><rect x="{u / 2:.1f}" width="{u / 2:.1f}" height="7" fill="none" stroke="{INK}"/>'
                 f'<text y="-6" class="tp-sub" font-size="14">0</text><text x="{u / 2:.1f}" y="-6" class="tp-sub" font-size="14" text-anchor="middle">{metres // 2}</text>'
                 f'<text x="{u:.1f}" y="-6" class="tp-sub" font-size="14" text-anchor="middle">{metres} m</text></g>')


def cartouche(p, x, y, title, sub, w=330):
    p.add("key", f'<g transform="translate({x} {y})"><rect x="{-w / 2}" y="-44" width="{w}" height="78" fill="{PAPER}" stroke="{INK}" stroke-width="1.6"/>'
                 f'<rect x="{-w / 2 + 5}" y="-39" width="{w - 10}" height="68" fill="none" stroke="{INK}" stroke-width=".6"/>'
                 f'<text y="-8" class="tp-title" font-size="34" text-anchor="middle">{esc(title)}</text>'
                 f'<text y="20" class="tp-sub" font-size="16" text-anchor="middle">{esc(sub)}</text></g>')




# ---------------------------------------------------------------- a whole town from a description
DIRS = {"N": (0, -1), "NE": (.7071, -.7071), "E": (1, 0), "SE": (.7071, .7071),
        "S": (0, 1), "SW": (-.7071, .7071), "W": (-1, 0), "NW": (-.7071, -.7071),
        "NNE": (.3827, -.9239), "ENE": (.9239, -.3827), "ESE": (.9239, .3827), "SSE": (.3827, .9239),
        "SSW": (-.3827, .9239), "WSW": (-.9239, .3827), "WNW": (-.9239, -.3827), "NNW": (-.3827, -.9239)}


def blob(cx, cy, rx, ry, rng, wobble=.08, n=96):
    """A rough ellipse, the shape a town takes when nobody planned its edge."""
    k1, k2, ph1, ph2 = rng.integers(2, 5), rng.integers(5, 9), rng.uniform(0, 6.3), rng.uniform(0, 6.3)
    pts = []
    for a in np.linspace(0, 2 * math.pi, n, endpoint=False):
        r = 1 + wobble * (math.sin(k1 * a + ph1) + .5 * math.sin(k2 * a + ph2))
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
    return Polygon(pts)


def ray_to_edge(x, y, dx, dy, W, H):
    """Where a ray from (x, y) leaves the canvas (a little beyond it)."""
    ts = []
    if dx > 0: ts.append((W + 20 - x) / dx)
    if dx < 0: ts.append((-20 - x) / dx)
    if dy > 0: ts.append((H + 20 - y) / dy)
    if dy < 0: ts.append((-20 - y) / dy)
    t = min(ts)
    return x + dx * t, y + dy * t


def upright(angle):
    """A text angle turned so the text never reads upside down."""
    angle = (angle + 180) % 360 - 180
    return angle + 180 if angle > 90 else angle - 180 if angle < -90 else angle


def build(spec):
    """A town from a description. Positions are offsets in plan units (about a metre
    each, times mpu) from the town's centre, x east and y south. The keys:

      id, seed, size=(W, H), centre=(x, y), extent=(rx, ry)   the town's own reach
      style: "human" | "dwarf" | "elf" | "tiefling"            its houses
      mpu: metres per unit (default 1)
      density: how closely it is built (default 1)
      sea: {dir, shore, bay=0, bay_width=300, name, piers=0, ships=0, quay=True}
           the sea lies toward dir, its shore `shore` units from the centre
      lake: {at, r=(rx, ry), name}          river: {pts, width, name}
      hill: {at, radii}                      forest: dir or None
      fields: True for farmland round about
      plaza: {r, shape: "round" | "square", id}
      walls: [{rx, ry, at=(0,0), towers=18, thick=9, id}]   rings of wall; roads pass through gates
      roads: [{name, to: dir or degrees, bend=0, width=12, id, from_=(dx, dy)}]
      from_map: True to take the roads and river from the Azgaar map instead (see from_map());
           then names: [{dir, name, id}] names them, and river: {at, width, bend, name} places the river
      rings, spokes: the town's own lanes (fractions of extent; how many radial lanes)
      ring_roads: [{rx, ry, name, id, width=11}]  roads that circle the town (outside its walls, say)
      shanty: {at, r}                         a quarter of huts with no streets
      landmarks: [{id, at, size=(w, h), angle=0, kind, label, lab=(dx, dy), anchor}]
           kind: hall | tower | round | yard | open | grove | field | rift | masts | dock
      districts: [{id, text, at, rotate=0, size=18}]
      labels: [{text, at, size, cls, rotate}]  anything else to write on it
      places: [{id, name, epithet, text, source}]  the key: what each marked place is
      title, sub, cartouche=(x, y), compass=(x, y), scale=(x, y)
    """
    if spec.get("from_map"):  # the roads and river as the map has them
        map_roads, map_river = from_map(spec)
        spec = dict(spec, roads=map_roads + list(spec.get("roads", ())))
        if map_river:
            spec["river"] = map_river
        elif isinstance(spec.get("river"), dict) and "pts" not in spec["river"]:
            spec.pop("river")
    W, H = spec.get("size", (1600, 1100))
    p = Plan(spec["id"], W, H, seed=spec.get("seed", 1))
    rng = p.rng
    p.palette = PALETTES[spec.get("style", "human")]
    p.corner = spec.get("corner", {"elf": .22, "human": .06, "dwarf": .12, "tiefling": .08}[spec.get("style", "human")])
    p.mpu = spec.get("mpu", 1.0)
    cx, cy = spec["centre"]
    rx, ry = spec["extent"]
    at = lambda off: (cx + off[0], cy + off[1])
    canvas = box(-20, -20, W + 20, H + 20)

    # ---- the ground: sea, lake, river
    land = canvas
    sea = spec.get("sea")
    shoreline = None
    if sea:
        sx, sy = DIRS[sea["dir"]]
        px, py = -sy, sx
        bay, bw = sea.get("bay", 0), sea.get("bay_width", 300)
        ph = rng.uniform(0, 6.3, 3)
        pts = []
        for u in np.arange(-2600, 2601, 6):
            t = sea["shore"] - bay * math.exp(-(u / bw) ** 2) + 10 * math.sin(u / 41 + ph[0]) + 6 * math.sin(u / 15 + ph[1]) + 3 * math.sin(u / 6.7 + ph[2])
            pts.append((cx + u * px + t * sx, cy + u * py + t * sy))
        shoreline = LineString(pts)
        far = [(cx + 2600 * px - 3000 * sx, cy + 2600 * py - 3000 * sy), (cx - 2600 * px - 3000 * sx, cy - 2600 * py - 3000 * sy)]
        land = Polygon(pts + far).buffer(0).intersection(canvas)
    lake = spec.get("lake")
    if lake:
        lx, ly = at(lake["at"])
        lake_poly = blob(lx, ly, *lake["r"], rng, .12)
        land = land.difference(lake_poly)
    water = canvas.difference(land)
    river = spec.get("river")
    land_dry = land
    if river:
        rline = smooth(LineString([at(q) for q in river["pts"]]))
        rpoly = rline.buffer(river.get("width", 16) / 2, cap_style=2)
        land_dry = land.difference(rpoly)
        water = water.union(rpoly.intersection(canvas))
    shallows = water.intersection(land.buffer(70)).difference(land)

    p.add("ground", f'<path d="{poly_d(land)}" fill="url(#grass)"/>')
    p.add("water", f'<path d="{poly_d(water)}" fill="{WATER}"/>')
    p.add("water", f'<path d="{poly_d(shallows)}" fill="{SHALLOW}"/>')
    deep = water.difference(land.buffer(70))
    if not deep.is_empty: p.add("water", f'<path d="{poly_d(deep)}" fill="url(#ripple)"/>')
    coast = land_dry.boundary.difference(canvas.exterior.buffer(2))
    for g in getattr(coast, "geoms", [coast]):
        if g.length > 4: p.add("water", f'<path d="{path_d(g.coords)}" fill="none" stroke="{INK}" stroke-width="{2 if g.length > 400 else 1.2}"/>')
    p.block(water.buffer(-1.5))

    # the lie of the land
    hill = spec.get("hill")
    if hill:
        hx, hy = at(hill["at"])
        for k, rad in enumerate(hill["radii"]):
            ring = blob(hx, hy, rad * 1.15, rad * .9, rng, .07).exterior.intersection(land_dry)
            for g in getattr(ring, "geoms", [ring]):
                if g.geom_type == "LineString" and g.length > 20:
                    p.add("contours", f'<path d="{path_d(g.coords)}" fill="none" stroke="#9a7b52" stroke-width="1" stroke-dasharray="7 5" opacity=".7"/>')

    # ---- the town's reach, its plaza, its walls
    area = blob(cx, cy, rx, ry, rng, .1).intersection(land_dry)
    plaza = spec.get("plaza")
    plaza_geom = None
    if plaza:
        r = plaza.get("r", 40)
        pc = at(plaza.get("at", (0, 0)))
        plaza_geom = (affinity.rotate(box(pc[0] - r, pc[1] - r * .8, pc[0] + r, pc[1] + r * .8), plaza.get("angle", 0))
                      if plaza.get("shape") == "square" else blob(*pc, r, r * .85, rng, .06))
    marks = []
    def lm_geom(m):
        mx, my = at(m["at"])
        w, h = m.get("size", (40, 28))
        kind = m.get("kind", "hall")
        if kind in ("round", "grove", "rift"):
            g = blob(mx, my, w / 2, h / 2, rng, .12 if kind != "rift" else .3, 40)
        else:
            g = affinity.rotate(box(mx - w / 2, my - h / 2, mx + w / 2, my + h / 2), m.get("angle", 0))
        return g
    for m in spec.get("landmarks", ()):
        g = lm_geom(m)
        marks.append((m, g))
    keep_clear = unary_union([g.buffer(6) for _, g in marks] + ([plaza_geom.buffer(4)] if plaza_geom else []) + [water.buffer(4)])

    # main roads: from the plaza's edge out across the plan
    roads = []
    for rd in spec.get("roads", ()):
        dx, dy = math.cos(math.radians(heading(rd["to"]))), math.sin(math.radians(heading(rd["to"])))
        start = at(rd["from_"]) if "from_" in rd else (cx + dx * (plaza.get("r", 40) if plaza else 0), cy + dy * (plaza.get("r", 40) if plaza else 0))
        end = ray_to_edge(start[0], start[1], dx, dy, W, H)
        bend = rd.get("bend", 0)
        mid = ((start[0] + end[0]) / 2 - dy * bend, (start[1] + end[1]) / 2 + dx * bend)
        line = wiggle(smooth(LineString([start, mid, end]), 3), 5, 1.4, rng, 14)
        g = line.difference(water.difference(rpoly if river else Polygon()).buffer(2)) if sea or lake else line
        parts = [g] if g.geom_type == "LineString" else sorted(getattr(g, "geoms", []), key=lambda q: q.distance(Point(start)))
        if parts and not parts[0].is_empty:
            roads.append((rd, parts[0]))

    walls = spec.get("walls", ())
    wall_geoms = []
    gates = []
    for wl in walls:
        wx, wy = at(wl.get("at", (0, 0)))
        ring = blob(wx, wy, wl["rx"], wl["ry"], rng, .05).exterior
        band = ring.buffer(wl.get("thick", 9) / 2).intersection(land_dry)
        for rd, line in roads:
            x = ring.intersection(line)
            for pt in getattr(x, "geoms", [x]):
                if pt.geom_type == "Point":
                    gates.append(pt)
                    band = band.difference(pt.buffer(rd.get("width", 12) * .9 + 4))
        wall_geoms.append((wl, ring, band))
    if plaza_geom is not None:
        p.block(plaza_geom)

    # quay along the shore
    quay = None
    if sea and sea.get("quay", True):
        q = shoreline.parallel_offset(30, "left" if True else "right")
        cand = []
        for side in ("left", "right"):
            q = shoreline.parallel_offset(32, side)
            q = getattr(q, "geoms", [q])
            for part in q:
                if part.geom_type == "LineString" and land_dry.contains(part.interpolate(.5, normalized=True)):
                    cand.append(part)
        if cand:
            ql = cand[0].intersection(area.buffer(40))
            parts = [g for g in getattr(ql, "geoms", [ql]) if g.geom_type == "LineString"]
            if parts:
                quay = max(parts, key=lambda g: g.length)

    # the town's own lanes: rings round the centre, spokes out from it, alleys between
    inner = area.buffer(-8)
    lane_lines, alley_ids = [], set()
    ring_lines = []
    for f in spec.get("rings", (.3, .52, .74, .94)):
        ph, a0 = rng.uniform(0, 6.3), rng.uniform(0, 2 * math.pi)
        arcs, a = [], a0
        while a < a0 + 2 * math.pi - .3:  # arcs of a quarter-turn or so, with gaps between
            span = rng.uniform(.9, 2.0)
            arcs.append((a, min(a + span, a0 + 2 * math.pi - .2)))
            a += span + rng.uniform(.25, .6)
        f2 = f * rng.uniform(.93, 1.07)
        for b0, b1 in arcs:
            pts = []
            for a in np.linspace(b0, b1, max(8, int((b1 - b0) * 30))):
                r = f2 * (1 + .07 * math.sin(3 * a + ph) + .03 * math.sin(7 * a))
                pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
            ring_lines.append(wiggle(LineString(pts), rng.uniform(5, 11), rng.uniform(1.4, 2.6), rng))
    road_angles = [math.radians(heading(rd["to"])) for rd, _ in roads]
    spokes = []
    n_sp = spec.get("spokes", 8)
    tries = 0
    while len(spokes) < n_sp and tries < 200:
        tries += 1
        a = rng.uniform(-math.pi, math.pi)
        if any(abs((a - b + math.pi) % (2 * math.pi) - math.pi) < .22 for b in road_angles + [math.atan2(*s[::-1]) for s in spokes]):
            continue
        spokes.append((math.cos(a), math.sin(a)))
    spoke_lines = []
    r0 = (plaza.get("r", 40) + 10) if plaza else 30
    for dxs, dys in spokes:
        s0 = (cx + dxs * r0, cy + dys * r0 * ry / rx)
        s1 = (cx + dxs * rx * 1.05, cy + dys * ry * 1.05)
        mid = ((s0[0] + s1[0]) / 2 + rng.uniform(-40, 40), (s0[1] + s1[1]) / 2 + rng.uniform(-40, 40))
        spoke_lines.append(wiggle(smooth(LineString([s0, mid, s1]), 2), rng.uniform(5, 10), 2.5, rng))
    alleys = []
    for a_line in ring_lines:
        others = [b for b in ring_lines if b is not a_line]
        s = rng.uniform(10, 60)
        while s < a_line.length and others:
            pa = a_line.interpolate(s)
            b_line = min(others, key=lambda b: b.distance(pa) if b.distance(pa) > 25 else 1e9)
            pb = b_line.interpolate(b_line.project(pa) + rng.uniform(-20, 20))
            if 25 < pa.distance(pb) < 150 and rng.random() < .6:
                alleys.append(wiggle(LineString([(pa.x, pa.y), (pb.x, pb.y)]), 3, 3, rng))
            s += rng.uniform(70, 140)
    walls_block = unary_union([band for _, _, band in wall_geoms]) if wall_geoms else Polygon()
    for k, ln in enumerate(ring_lines + spoke_lines + alleys):
        g = ln.intersection(inner).difference(keep_clear).difference(walls_block.buffer(5))
        for part in getattr(g, "geoms", [g]):
            if part.geom_type == "LineString" and part.length > 28:
                if k >= len(ring_lines) + len(spoke_lines): alley_ids.add(len(lane_lines))
                lane_lines.append(part)

    rings_out = []
    for rr in spec.get("ring_roads", ()):
        g = blob(cx, cy, rr["rx"], rr["ry"], rng, .05).exterior
        g = wiggle(LineString(g.coords), 6, 1.2, rng, 16).intersection(land_dry.buffer(-4))
        for part in getattr(g, "geoms", [g]):
            if part.geom_type == "LineString" and part.length > 40:
                rings_out.append((rr, part))

    # ---- draw: fields, walls, streets, piers, landmarks
    if spec.get("fields"):
        fields = land_dry.difference(area.buffer(30)).intersection(Point(cx, cy).buffer(max(W, H)))
        tints = ("#e3d6b0", "#dccd9f", "#e6dbb8", "#d5c79a", "#e0d2a6", "#d9d0a2")
        taken_f = Polygon()
        for k in range(spec.get("farms", 26)):
            fx, fy = rng.uniform(0, W), rng.uniform(0, H)
            ang = rng.uniform(-30, 30) + rng.choice([0, 90])
            nx_, ny_ = int(rng.integers(2, 5)), int(rng.integers(1, 3))
            sw, sh = rng.uniform(26, 40), rng.uniform(60, 110)
            farm = []
            for i in range(nx_):
                for j in range(ny_):
                    x0 = fx + (i - nx_ / 2) * sw; y0 = fy + (j - ny_ / 2) * sh
                    strip = affinity.rotate(box(x0, y0, x0 + sw - 3, y0 + sh - 3), ang, origin=(fx, fy))
                    farm.append(strip)
            whole = unary_union(farm)
            if whole.intersects(taken_f) or not fields.contains(whole.centroid):
                continue
            taken_f = taken_f.union(whole.buffer(8))
            for i, strip in enumerate(farm):
                g = strip.intersection(fields)
                if g.area > 200:
                    p.add("ground", f'<path d="{poly_d(g)}" fill="{tints[int(rng.integers(len(tints)))]}" stroke="#a89068" stroke-width=".7" opacity=".9"/>')
    for (wl, ring, band) in wall_geoms:
        p.block(band.buffer(1))
    for rr, line in rings_out:
        p.street(line, rr.get("width", 11))
    for rd, line in roads:
        p.street(line, rd.get("width", 12), rd.get("colour", ROAD))
    if quay is not None:
        p.street(quay, 10)
    for k, ln in enumerate(lane_lines):
        p.street(ln, 6 if k in alley_ids else 7.5)
    if plaza_geom is not None:
        p.add("streets", f'<path d="{poly_d(plaza_geom)}" fill="{ROAD}" stroke="{INK}" stroke-width="1.4" opacity=".95"' + (f' data-place="{plaza["id"]}" class="place"' if plaza.get("id") else "") + '/>')
    for (wl, ring, band) in wall_geoms:
        attrs = f' data-place="{wl["id"]}" class="place"' if wl.get("id") else ""
        p.add("marks", f'<path d="{poly_d(band)}" fill="#8f7b5c" stroke="{INK}" stroke-width="1.3"{attrs}/>')
        n = wl.get("towers", 18)
        for k in range(n):
            pt = ring.interpolate(k / n, normalized=True)
            if band.buffer(3).contains(pt):
                p.add("marks", f'<circle cx="{pt.x:.1f}" cy="{pt.y:.1f}" r="{wl.get("thick", 9) * .85:.1f}" fill="#7d6a4e" stroke="{INK}" stroke-width="1.2"/>')
    for g in gates:
        p.add("marks", f'<rect x="{g.x - 9:.1f}" y="{g.y - 9:.1f}" width="18" height="18" fill="#6d5a40" stroke="{INK}" stroke-width="1.2" transform="rotate(45 {g.x:.1f} {g.y:.1f})"/>')

    # piers and ships
    if sea and (sea.get("piers") or sea.get("ships")):
        sx, sy = DIRS[sea["dir"]]
        coast_town = shoreline.intersection(area.buffer(60))
        ct = [g for g in getattr(coast_town, "geoms", [coast_town]) if g.geom_type == "LineString"]
        if ct:
            ct = max(ct, key=lambda g: g.length)
            n = sea.get("piers", 0)
            for k in range(n):
                b = ct.interpolate((k + .5) / n, normalized=True)
                L = rng.uniform(90, 190)
                e = (b.x + sx * L, b.y + sy * L)
                s0 = (b.x - sx * 10, b.y - sy * 10)
                p.add("piers", f'<path d="M{s0[0]:.1f} {s0[1]:.1f}L{e[0]:.1f} {e[1]:.1f}" stroke="{INK}" stroke-width="11" fill="none"/>'
                               f'<path d="M{s0[0]:.1f} {s0[1]:.1f}L{e[0]:.1f} {e[1]:.1f}" stroke="#bf9d70" stroke-width="7.5" fill="none"/>')
                p.block(LineString([s0, e]).buffer(8))
                for j in range(int(L / 55)):
                    t = 35 + j * 50
                    side = 1 if j % 2 else -1
                    bx, by = b.x + sx * t - sy * 13 * side, b.y + sy * t + sx * 13 * side
                    ang = math.degrees(math.atan2(sy, sx))
                    p.add("boats", f'<path d="M-14 0q14 -7 28 0q-14 7 -28 0Z" fill="#8a6a46" stroke="{INK}" stroke-width=".8" transform="translate({bx:.1f} {by:.1f}) rotate({ang:.0f})"/>')
            for k in range(sea.get("ships", 0)):
                b = ct.interpolate(rng.uniform(.1, .9), normalized=True)
                d = rng.uniform(260, 420)
                x, y = b.x + sx * d, b.y + sy * d
                if not (0 < x < W and 0 < y < H) or not water.contains(Point(x, y).buffer(30)): continue
                rot = rng.uniform(-30, 30)
                p.add("boats", f'<g transform="translate({x:.0f} {y:.0f}) rotate({rot:.0f})"><path d="M-30 0q30 -14 60 0q-30 14 -60 0Z" fill="#7b5b3a" stroke="{INK}" stroke-width="1"/>'
                               f'<path d="M-4 -3V-34L16 -6Z" fill="{PAPER}" stroke="{INK}" stroke-width=".9"/><path d="M-6 -4V-28L-22 -6Z" fill="{PAPER}" stroke="{INK}" stroke-width=".9"/></g>')

    # landmarks
    for m, g in marks:
        kind = m.get("kind", "hall")
        pid = m["id"]
        if kind in ("hall", "round"):
            p.landmark(pid, g, fill=m.get("fill", MARK))
        elif kind == "tower":
            p.landmark(pid, g, fill=m.get("fill", "#7d4a2c"))
        elif kind == "yard":
            p.block(g.buffer(3))
            p.add("marks", f'<path d="{poly_d(g)}" fill="#e6d6b4" stroke="{INK}" stroke-width="1.4" stroke-dasharray="4 3" data-place="{pid}" class="place"/>')
            w, h = m.get("size", (40, 28))
            mx, my = at(m["at"])
            for k in range(m.get("sheds", 2 if w * h > 2500 else 1)):  # the halls or sheds in the yard
                t = (k + .5) / m.get("sheds", 2 if w * h > 2500 else 1) - .5
                bx = mx + t * w * .75 * math.cos(math.radians(m.get("angle", 0)))
                by = my + t * w * .75 * math.sin(math.radians(m.get("angle", 0)))
                hall = affinity.rotate(box(bx - w * .16, by - h * .3, bx + w * .16, by + h * .3), m.get("angle", 0))
                p.add("marks", f'<path d="{poly_d(hall)}" fill="{m.get("fill", MARK)}" stroke="{INK}" stroke-width="1.2" data-place="{pid}" class="place"/>')
        elif kind == "open":
            p.block(g.buffer(2))
            p.add("streets", f'<path d="{poly_d(g)}" fill="{ROAD}" stroke="{INK}" stroke-width="1.4" data-place="{pid}" class="place"/>')
        elif kind == "field":
            p.block(g.buffer(2))
            p.add("marks", f'<path d="{poly_d(g)}" fill="#dfe0b0" stroke="{INK}" stroke-width="1.3" stroke-dasharray="8 4" data-place="{pid}" class="place"/>')
        elif kind == "grove":
            mass = p.forest(g, int(g.area / 260) + 6, r=(7, 13))
            p.add("marks", f'<path d="{poly_d(g)}" fill="transparent" stroke="none" data-place="{pid}" class="place"/>')
        elif kind == "rift":
            p.block(g.buffer(4))
            p.add("marks", f'<path d="{poly_d(g)}" fill="#3b3346" stroke="{INK}" stroke-width="1.5" data-place="{pid}" class="place"/>'
                           f'<path d="{poly_d(g.buffer(-5))}" fill="#6c5f80" opacity=".6"/>')
        elif kind == "masts":  # tall iron mooring-masts along a quay, each a ring and a cross
            mx, my = at(m["at"])
            w, h = m.get("size", (200, 20))
            ang = math.radians(m.get("angle", 0))
            for k in range(m.get("count", 5)):
                t = (k / max(1, m.get("count", 5) - 1) - .5) * w
                x, y = mx + math.cos(ang) * t, my + math.sin(ang) * t
                p.block(Point(x, y).buffer(9))
                p.add("marks", f'<g data-place="{pid}" class="place"><circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{PAPER}" stroke="{INK}" stroke-width="1.5"/>'
                               f'<path d="M{x - 6:.1f} {y:.1f}h12M{x:.1f} {y - 6:.1f}v12" stroke="{INK}" stroke-width="1.5"/></g>')
        elif kind == "dock":
            p.block(g.buffer(2))
            p.add("piers", f'<path d="{poly_d(g)}" fill="#bf9d70" stroke="{INK}" stroke-width="1.6" data-place="{pid}" class="place"/>')

    # ---- houses
    density = spec.get("density", 1.0)
    walled = unary_union([Polygon(ring.coords) for _, ring, _ in wall_geoms]) if wall_geoms else None
    main_lines = [ln for _, ln in roads]
    for ln in main_lines:
        p.houses_along(ln, area, depth=(12, 20), width=(10, 18), street_w=12)
    if quay is not None:
        p.houses_along(quay, area, depth=(12, 20), width=(10, 18), street_w=10)
    for ln in sorted(lane_lines, key=lambda l: l.centroid.distance(Point(cx, cy))):
        p.houses_along(ln, area, street_w=7.5)
    def dens(x, y):
        r = math.hypot((x - cx) / rx, (y - cy) / ry)
        base = max(.15, 1 - .7 * r)
        if walled is not None and not walled.contains(Point(x, y)): base *= .45
        return base
    p.infill(area, int(area.area / 330 * density), lane_lines + main_lines, dens)
    for rr, line in rings_out:  # houses face the ring roads, thinly
        p.houses_along(line, land_dry, depth=(10, 15), width=(8, 13), gap=(10, 40), street_w=rr.get("width", 11))
    # ribbon houses along the roads out of town
    for ln in main_lines:
        ribbon = land_dry.intersection(ln.buffer(40)).intersection(blob(cx, cy, rx * 1.55, ry * 1.55, rng, .08)).difference(area)
        p.houses_along(ln, ribbon, depth=(10, 15), width=(8, 13), gap=(6, 22), street_w=12)
    shanty = spec.get("shanty")
    if shanty:
        sxp, syp = at(shanty["at"])
        sh = blob(sxp, syp, *shanty["r"], rng, .18).intersection(land_dry)
        k = tries = 0
        while k < int(sh.area / 140) and tries < 6000:
            tries += 1
            x, y = rng.uniform(*sh.bounds[0::2]), rng.uniform(*sh.bounds[1::2])
            if p.house(x, y, rng.uniform(5, 9), rng.uniform(4, 8), rng.uniform(0, 180), fill="#a8937a", area=sh):
                k += 1

    # ---- trees
    forest = spec.get("forest")
    if forest:
        fx, fy = DIRS[forest]
        cxp, cyp = cx + fx * max(W, H) * .62, cy + fy * max(W, H) * .62
        region = land_dry.intersection(Point(cxp, cyp).buffer(max(W, H) * .42)).difference(area.buffer(60))
        if not region.is_empty:
            p.forest(region, int(region.area / 900) + 20)
    p.trees(land_dry.difference(area.buffer(30)), spec.get("trees", 260), r=(5, 10))
    p.trees(area, spec.get("garden_trees", 60), r=(4, 7), colour="#a9b886")

    # ---- words
    for m, g in marks:
        if m.get("label") is False: continue
        text = m.get("label") or next((pl["name"] for pl in spec["places"] if pl["id"] == m["id"]), m["id"])
        c = g.centroid
        dx, dy = m.get("lab", (0, (g.bounds[3] - g.bounds[1]) / 2 + 16))
        p.label(c.x + dx, c.y + dy, text, m.get("lsize", 14), pid=m["id"], anchor=m.get("anchor", "middle"))
    for d in spec.get("districts", ()):
        x, y = at(d["at"])
        p.label(x, y, d["text"].upper(), d.get("size", 18), "tp-area", rotate=d.get("rotate", 0), spacing=4, pid=d.get("id"))
    for rr, line in rings_out:
        if rr.get("name") and line.length > 300:
            q = line.interpolate(.15, normalized=True); q2 = line.interpolate(line.project(q) + 10)
            p.label(q.x, q.y - 12, rr["name"].upper(), 13, "tp-road", rotate=upright(math.degrees(math.atan2(q2.y - q.y, q2.x - q.x))), spacing=3, pid=rr.get("id"))
            rr = dict(rr, name=None)
    for rd, line in roads:
        if not rd.get("name"): continue
        q = line.interpolate(min(line.length - 60, max(80, line.length * rd.get("lab_at", .72))))
        q2 = line.interpolate(min(line.length, line.project(q) + 10))
        ang = upright(math.degrees(math.atan2(q2.y - q.y, q2.x - q.x)))
        p.label(q.x, q.y - 12, rd["name"].upper(), 13, "tp-road", rotate=ang, spacing=3, pid=rd.get("id"))
    if sea and sea.get("name"):
        sx, sy = DIRS[sea["dir"]]
        x, y = sea.get("label_at") and at(sea["label_at"]) or (cx + sx * (sea["shore"] + 260), cy + sy * (sea["shore"] + 260))
        p.label(min(max(x, 160), W - 160), min(max(y, 60), H - 60), sea["name"], 34, "tp-sea", spacing=4)
    if lake and lake.get("name"):
        lx, ly = at(lake["at"])
        p.label(lx, ly, lake["name"], 28, "tp-sea", spacing=3)
    if river and river.get("name"):
        q = rline.interpolate(river.get("lab_at", .2), normalized=True)
        q2 = rline.interpolate(rline.project(q) + 10)
        p.label(q.x, q.y + 26, river["name"], 16, "tp-sub", rotate=upright(math.degrees(math.atan2(q2.y - q.y, q2.x - q.x))))
    for lb in spec.get("labels", ()):
        x, y = at(lb["at"])
        p.label(x, y, lb["text"], lb.get("size", 16), lb.get("cls", "tp-sub"), rotate=lb.get("rotate", 0), pid=lb.get("id"))

    cartouche(p, *spec.get("cartouche", (W - 210, H - 80)), spec["title"], spec["sub"], w=max(330, 16 * len(spec["sub"]) * .55 + 60))
    compass(p, *spec.get("compass", (W - 80, 120)))
    scale_bar(p, *spec.get("scale", (60, H - 50)), spec.get("scale_m", 200))
    for pl in spec["places"]:
        p.place(pl["id"], pl["name"], pl.get("epithet", ""), pl["text"], pl.get("source"))
    if "extra" in spec:
        spec["extra"](p, {"at": at, "land": land_dry, "water": water, "area": area, "roads": roads})
    return p


# ---------------------------------------------------------------- the town's roads and river, from the map
_MAP = None
RANK = {"roads": 0, "trails": 1}


def map_town(name):
    """Where a town's roads go and its river runs on the Azgaar map (the newest map/*.map):
    {"roads": [(map name, group, heading)], "river": (name, upstream heading, downstream heading) | None}.
    Headings are plan angles in degrees: 0 east, 90 south. Sea lanes are left out."""
    global _MAP
    if _MAP is None:
        import atlas  # hub/atlas.py reads the save
        src = max((HERE.parent / "map").glob("*.map"), key=lambda q: q.stat().st_mtime)
        d = atlas.load(src)
        P, _, _ = atlas.pack_points(d)
        _MAP = (d, P)
    d, P = _MAP
    b = next((b for b in d["burgs"] if isinstance(b, dict) and b.get("name") == name and not b.get("removed")), None)
    if b is None:
        raise SystemExit(f"{name} is not on the map")
    x, y = b["x"], b["y"]
    heads = []
    for r in d["routes"]:
        if r["group"] not in RANK: continue
        pts = r["points"]
        for k, q in enumerate(pts):
            if math.hypot(q[0] - x, q[1] - y) > 1.0: continue
            for step in (-1, 1):  # follow it out of town both ways, about 8 km
                j, far = k, None
                while 0 <= j + step < len(pts):
                    j += step
                    if math.hypot(pts[j][0] - x, pts[j][1] - y) > 2.6:
                        far = pts[j]; break
                if far is None and j != k and math.hypot(pts[j][0] - x, pts[j][1] - y) > .5:
                    far = pts[j]
                if far is not None:
                    heads.append((r.get("name"), r["group"], math.degrees(math.atan2(far[1] - y, far[0] - x))))
    roads = []
    for h in sorted(heads, key=lambda h: (RANK[h[1]], h[0] is None)):
        if all(abs((h[2] - o[2] + 180) % 360 - 180) > 18 for o in roads):
            roads.append(h)
    river = None
    rid = int(d["river"][b["cell"]])
    rv = next((r for r in d["rivers"] if isinstance(r, dict) and r.get("i") == rid), None)
    if rv and b["cell"] in rv.get("cells", []):
        cells = rv["cells"]
        k = cells.index(b["cell"])
        up, dn = P[cells[max(0, k - 2)]], P[cells[min(len(cells) - 1, k + 2)]]
        hd = lambda q: math.degrees(math.atan2(q[1] - y, q[0] - x))
        river = (rv.get("name", ""), hd(up), hd(dn))
    return {"roads": roads, "river": river}


def road_title(name):
    """The map's 'Loom road' as the page writes it: 'the Loom Road'."""
    if not name or name.startswith("Unnamed"):
        return None
    words = name.split()
    words[-1] = words[-1].capitalize()
    if words[0] == "The":
        words[0] = "the"
    else:
        words.insert(0, "the")
    return " ".join(words)


def heading(to):
    """A direction given as a compass point ("NE") or a plan angle in degrees (0 east, 90 south)."""
    if isinstance(to, str):
        return math.degrees(math.atan2(DIRS[to][1], DIRS[to][0]))
    return float(to)


def from_map(spec):
    """build()'s roads and river, as the map has them round the town. spec["names"] names the map's
    roads by the way they head: [{dir, name, id}] (closest first; a map name is used otherwise)."""
    mt = map_town(spec.get("town", spec["title"]))
    roads = [{"name": road_title(n), "to": h, "width": 13 if g == "roads" else 9, "group": g, "map": n} for n, g, h in mt["roads"]]
    gap = lambda a, b: abs((a - b + 180) % 360 - 180)
    pairs = sorted((gap(heading(nm["dir"]), rd["to"]), i, k) for i, rd in enumerate(roads) for k, nm in enumerate(spec.get("names", ())))
    done_r, done_n = set(), set()
    for diff, i, k in pairs:
        if diff < 35 and i not in done_r and k not in done_n:
            nm = spec["names"][k]
            roads[i].update({kk: v for kk, v in nm.items() if kk != "dir"})
            done_r.add(i); done_n.add(k)
    for k, nm in enumerate(spec.get("names", ())):
        if k not in done_n:
            print(f"  ({spec['title']}: no road on the map heads {nm['dir']} for {nm.get('name') or nm.get('id')})")
    river = None
    if mt["river"] and spec.get("river") is not False:
        name, up, dn = mt["river"]
        rs = spec.get("river") or {}
        ox, oy = rs.get("at", (0, 0))  # where it passes the centre
        R = 1600
        u = (R * math.cos(math.radians(up)), R * math.sin(math.radians(up)))
        v = (R * math.cos(math.radians(dn)), R * math.sin(math.radians(dn)))
        bend = rs.get("bend", 60)
        pts = [u, ((u[0] + ox) / 2 + bend, (u[1] + oy) / 2 - bend * .6), (ox, oy), ((v[0] + ox) / 2 - bend * .7, (v[1] + oy) / 2 + bend), v]
        river = {"pts": pts, "width": rs.get("width", 30), "name": rs.get("name", f"the {name}"), "lab_at": rs.get("lab_at", .2)}
    return roads, river


# ---------------------------------------------------------------- running it
def plan_id(name):
    """The id a town's plan is filed under (hub/atlas.py works it out the same way)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "").replace("’", "")).strip("-")


def towns():
    """Every town module in hub/towns/<country>/, as (country, path)."""
    for country in sorted(d for d in TOWNS.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))):
        for f in sorted(country.glob("*.py")):
            if not f.name.startswith("_"):
                yield country.name, f


def load(path):
    spec = importlib.util.spec_from_file_location(f"towns.{path.parent.name}.{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    sys.modules.setdefault("plans", sys.modules[__name__])  # so the town modules share this toolkit
    wanted = {a.lower() for a in sys.argv[1:]}
    OUT.mkdir(parents=True, exist_ok=True)
    done = 0
    for country, path in towns():
        if wanted and country not in wanted and path.stem.replace("_", "-") not in wanted:
            continue
        mod = load(path)
        p = mod.draw() if hasattr(mod, "draw") else build(dict(mod.SPEC, town=mod.TOWN))
        pid = plan_id(mod.TOWN)
        (OUT / f"{pid}.svg").write_text(p.svg(mod.TOWN, mod.EPITHET), encoding="utf-8")
        (OUT / f"{pid}.json").write_text(json.dumps({"id": pid, "town": mod.TOWN, "epithet": mod.EPITHET, "country": country, "places": p.places},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{country:11} {mod.TOWN:18} {len(p.layers['houses']):5} houses {len(p.places):3} places -> {pid}.svg")
        done += 1
    if not done:
        print("no towns matched", " ".join(sys.argv[1:]))


if __name__ == "__main__":
    main()
