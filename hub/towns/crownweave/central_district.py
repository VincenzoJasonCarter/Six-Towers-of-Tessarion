"""Central District, seat of Skyloom: the Groundring (lore-book 13).

The Groundring is the city where those without wings walk: wards and winding streets round the Loom Temple, the
Skyward Towers on their square to the west and the Veil Court to the east, the Albrole running through its northern
quarters. The Aerialring floats above it, anchored by the Towers, drawn as an overlay the page can show over the city.

The town draws itself (draw()). Positions are in plan units (1.6 m) from the Loom Temple, x east and y south.
"""
import heapq
import math

import numpy as np
from scipy.spatial import Voronoi
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, polylabel, split, unary_union

from plans import INK, MARK, PAPER, ROAD, WATER, Plan, cartouche, compass, map_town, path_d, poly_d, road_title, scale_bar, smooth, upright, wiggle

TOWN = "Central District"
EPITHET = "Seat of the Weave"
BOOK = "Of Skyloom, the Loom Above"

W, H = 2400, 1560
CX, CY = 1200, 800
SLATE = "#9fb1bc"     # Skyloom's blue-grey roofs
STONE = "#efe6cf"     # paving of the great squares
GLASS = "#d6e8ee"     # cloudglass and translucent stone
GOLD = "#d9a63a"      # the woven light
ROOFS = ("#cdb48f", "#c6ab85", "#d3bd99", "#bfa47f", "#c9b392", "#bba98d")
GARDEN, YARD = "#c5cb9c", "#ebe1c8"


def at(x, y):
    return CX + x, CY + y


def T(g):
    return affinity.translate(g, CX, CY)


def octagon(x, y, r, rot=22.5):
    return Polygon([(x + r * math.cos(math.radians(rot + 45 * k)), y + r * math.sin(math.radians(rot + 45 * k))) for k in range(8)])


def ellipse(x, y, rx, ry):
    return affinity.scale(Point(x, y).buffer(1, 64), rx, ry)


def parts(g):
    return [q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and not q.is_empty]


def longest_line(g):
    lines = [q for q in getattr(g, "geoms", [g]) if q.geom_type == "LineString"]
    return max(lines, key=lambda q: q.length)


def tower(x, y, r, fill=SLATE):
    """A round tower under a cone roof, seen from above."""
    ribs = "".join(f"M{x:.1f} {y:.1f}L{x + r * .92 * math.cos(a):.1f} {y + r * .92 * math.sin(a):.1f}" for a in [k * math.pi / 3 + .3 for k in range(6)])
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{INK}" stroke-width="1.2"/>'
            f'<path d="{ribs}" stroke="{INK}" stroke-width=".6" opacity=".45"/>'
            f'<circle cx="{x - r * .35:.1f}" cy="{y - r * .35:.1f}" r="{r * .3:.1f}" fill="#fff" opacity=".22"/>')


def dome(x, y, r, oculus=0):
    """A ribbed dome; with an oculus, open at its apex."""
    ribs = "".join(f"M{x + oculus * math.cos(a):.1f} {y + oculus * math.sin(a):.1f}L{x + r * math.cos(a):.1f} {y + r * math.sin(a):.1f}" for a in [k * math.pi / 8 for k in range(16)])
    out = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{SLATE}" stroke="{INK}" stroke-width="1.5"/>'
           f'<path d="{ribs}" stroke="{INK}" stroke-width=".6" opacity=".4"/>'
           f'<path d="M{x - r * .75:.1f} {y - r * .2:.1f}A{r * .8:.1f} {r * .8:.1f} 0 0 1 {x + r * .2:.1f} {y - r * .75:.1f}" fill="none" stroke="#fff" stroke-width="{r * .12:.1f}" opacity=".25" stroke-linecap="round"/>')
    if not oculus:
        out += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(3, r * .14):.1f}" fill="#c9d4da" stroke="{INK}" stroke-width=".8"/>'
    return out


def skycraft(x, y, rot, s=1.0):
    """A skycraft: a hull with a wing-sail either side."""
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({rot:.0f}) scale({s})">'
            f'<path d="M-6 -4L-30 -22 -14 -3ZM-6 4L-30 22 -14 3Z" fill="{PAPER}" stroke="{INK}" stroke-width=".9"/>'
            f'<path d="M-28 0q28 -11 56 0q-28 11 -56 0Z" fill="#7b6a58" stroke="{INK}" stroke-width="1"/>'
            f'<circle cx="16" r="2.4" fill="{GLASS}" stroke="{INK}" stroke-width=".6"/></g>')


# ---------------------------------------------------------------- the city's bones
# The city grew the way old cities do: wards of irregular size, smaller towards the middle, with a street
# along every edge between two wards; main streets from each gate to the Loom Temple along those edges;
# and in every ward its houses, lot by lot, each fronting a street, yards and gardens behind.
RX, RY = 770, 520     # the walls' reach from the Loom Temple


def city_shape(rng):
    """The walls: a rough oval, run in straight lengths from tower to tower."""
    ph = rng.uniform(0, 6.3, 2)
    pts = []
    for k in range(26):
        a = 2 * math.pi * k / 26 + rng.uniform(-.05, .05)
        r = 1 + .05 * math.sin(3 * a + ph[0]) + .03 * math.sin(5 * a + ph[1])
        pts.append(at(RX * r * math.cos(a), RY * r * math.sin(a)))
    return Polygon(pts)


def cells_of(seeds, clip):
    far = [(CX + 5000 * math.cos(a), CY + 5000 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    vor = Voronoi(np.vstack([seeds, far]))
    out = []
    for i in range(len(seeds)):
        ps = parts(Polygon(vor.vertices[vor.regions[vor.point_region[i]]]).intersection(clip))
        if ps: out.append(max(ps, key=lambda g: g.area))
    return out


def wards(city, rng, n=74):
    """Voronoi wards over the city, closer together towards its middle, relaxed so none is a sliver."""
    seeds = []
    for i in range(n):
        f = ((i + .5) / n) ** .78 * .97
        a = i * 2.39996 + rng.uniform(-.3, .3)
        seeds.append(at(RX * f * math.cos(a), RY * f * math.sin(a)))
    cells = cells_of(np.array(seeds), city)
    for _ in range(2):  # Lloyd's relaxation
        cells = cells_of(np.array([c.centroid.coords[0] for c in cells]), city)
    return cells


def street_graph(cells):
    """Every ward edge is a street: {node: {node: length}}."""
    G = {}
    for c in cells:
        cs = [(round(x, 1), round(y, 1)) for x, y in c.exterior.coords]
        for a, b in zip(cs, cs[1:]):
            if a != b:
                G.setdefault(a, {})[b] = G.setdefault(b, {})[a] = math.dist(a, b)
    return G


def shortest(G, s, t):
    dist, prev, todo = {s: 0}, {}, [(0, s)]
    while todo:
        d, u = heapq.heappop(todo)
        if u == t: break
        if d > dist[u]: continue
        for v, w in G[u].items():
            if d + w < dist.get(v, 1e18):
                dist[v], prev[v] = d + w, u
                heapq.heappush(todo, (d + w, v))
    path = [t]
    while path[-1] != s:
        path.append(prev[path[-1]])
    return path[::-1]


def bisect(poly, amin, rng, out, depth=0):
    """Lots: a block cut across its longest side, and again, till each piece is a house's size.
    Now and then a cut through a big block is left open as an alley."""
    if poly.area < amin * rng.uniform(1, 2.2) or depth > 22:
        out.append(poly)
        return
    c = list(poly.minimum_rotated_rectangle.exterior.coords)
    a, b = (c[0], c[1]) if math.dist(c[0], c[1]) >= math.dist(c[1], c[2]) else (c[1], c[2])
    t = rng.uniform(.35, .65)
    mx, my = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2 + rng.uniform(-.2, .2)
    line = LineString([(mx - 3000 * math.cos(ang), my - 3000 * math.sin(ang)), (mx + 3000 * math.cos(ang), my + 3000 * math.sin(ang))])
    pieces = parts(split(poly, line))
    if len(pieces) < 2:
        out.append(poly)
        return
    if poly.area > amin * 16 and rng.random() < .35:
        pieces = [q for p_ in pieces for q in parts(p_.difference(line.buffer(2.2)))]
    for q in pieces:
        bisect(q, amin, rng, out, depth + 1)


def lanes(ward, amax, rng):
    """A big ward is cut by lanes into blocks."""
    if ward.area < amax:
        return [ward]
    c = list(ward.minimum_rotated_rectangle.exterior.coords)
    a, b = (c[0], c[1]) if math.dist(c[0], c[1]) >= math.dist(c[1], c[2]) else (c[1], c[2])
    t = rng.uniform(.4, .6)
    mx, my = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2 + rng.uniform(-.25, .25)
    line = LineString([(mx - 3000 * math.cos(ang), my - 3000 * math.sin(ang)), (mx + 3000 * math.cos(ang), my + 3000 * math.sin(ang))])
    pieces = parts(ward.difference(line.buffer(3.2)))
    if len(pieces) < 2:
        return [ward]
    return [q for p_ in pieces for q in lanes(p_, amax, rng)]


def lots_of(block, amin, depth, rng):
    """The houses of one block: it is cut into lots, and every lot that fronts a street is built on
    to the same depth back from it, so the street is lined end to end; behind lie yards."""
    pieces = []
    bisect(block, amin, rng, pieces)
    core = block.buffer(-depth, join_style=2)
    front = block.difference(core) if not core.is_empty else block
    houses = []
    for q in pieces:
        for g in parts(q.intersection(front)):
            for h in parts(g.buffer(-.45, join_style=2)):
                if h.area > 10: houses.append(h)
        if not core.is_empty and rng.random() < .2:  # now and then an outbuilding in the yard
            back = q.intersection(core)
            if back.area > 60:
                for h in parts(back.buffer(-math.sqrt(back.area) * .22, join_style=2)):
                    if h.area > 12: houses.append(h)
    return houses


def grand_hall(p, b, pid=None):
    """A great courtyard building under slate roofs, its court laid out as a garden."""
    core = b.buffer(-20, join_style=2)
    place = f' data-place="{pid}" class="place"' if pid else ""
    p.add("marks", f'<path d="{poly_d(b.difference(core))}" fill="{SLATE}" fill-rule="evenodd" stroke="{INK}" stroke-width="1.4"{place}/>'
                   f'<path d="{poly_d(core)}" fill="{GARDEN}" stroke="{INK}" stroke-width=".9"/>')
    c = polylabel(core, 1)
    r = core.exterior.distance(c) * .5
    p.add("marks", f'<path d="M{c.x - r:.1f} {c.y:.1f}H{c.x + r:.1f}M{c.x:.1f} {c.y - r:.1f}V{c.y + r:.1f}" stroke="{STONE}" stroke-width="5"/>'
                   f'<circle cx="{c.x:.1f}" cy="{c.y:.1f}" r="{max(5, r * .3):.1f}" fill="{WATER}" stroke="{INK}" stroke-width=".8"/>')


def yard(p, b, pid, rng, sheds=3, vats=0):
    """A walled yard with its sheds or stills."""
    p.add("marks", f'<path d="{poly_d(b)}" fill="#e3d6b8" stroke="{INK}" stroke-width="1.3" stroke-dasharray="5 3" data-place="{pid}" class="place"/>')
    pieces = []
    bisect(b.buffer(-10, join_style=2), b.area / (sheds * 2.2), rng, pieces)
    for q in sorted(pieces, key=lambda g: -g.area)[:sheds]:
        for g in parts(q.buffer(-6, join_style=2)):
            p.add("marks", f'<path d="{poly_d(g)}" fill="{MARK}" stroke="{INK}" stroke-width="1.1" data-place="{pid}" class="place"/>')
    c = polylabel(b, 1)
    for k in range(vats):
        x, y = c.x - (vats - 1) * 11 + k * 22, c.y + 6
        if b.buffer(-8).contains(Point(x, y)):
            p.add("marks", f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="#a98a62" stroke="{INK}" stroke-width=".9" data-place="{pid}" class="place"/>')


# ---------------------------------------------------------------- the city
def draw():
    p = Plan("central-district", W, H, seed=1301)
    p.mpu = 1.6
    p.palette, p.corner = ROOFS, .05
    rng = p.rng
    canvas = box(-20, -20, W + 20, H + 20)
    city = city_shape(rng)
    p.add("ground", f'<rect width="{W}" height="{H}" fill="url(#grass)"/>')

    # ---- the Albrole, which comes in from the east and runs through the city's northern quarters
    rline = smooth(LineString([at(*q) for q in ((1350, -250), (900, -300), (520, -245), (120, -305), (-300, -235), (-760, -290), (-1350, -215))]), 4)
    river = rline.buffer(21, cap_style=2)

    # ---- wards, and the streets between them
    cells = wards(city, rng)
    G = street_graph(cells)
    on_wall = [n for n in G if city.exterior.distance(Point(n)) < .6]
    centre = min(G, key=lambda n: math.dist(n, at(0, 0)))
    heading = lambda n: math.degrees(math.atan2(n[1] - CY, n[0] - CX))
    gap = lambda a, b: abs((a - b + 180) % 360 - 180)
    exits = [(road_title(name), group, hd) for name, group, hd in map_town(TOWN)["roads"]] + [(None, "tracks", 180), (None, "tracks", 92)]
    gates, mains = [], []
    for name, group, hd in exits:
        g = min(on_wall, key=lambda n: gap(heading(n), hd))
        gates.append((g, name, group, hd))
        mains.append(LineString(shortest(G, g, centre)))
    main_streets = unary_union([m.buffer(8) for m in mains])

    # ---- what each ward is for
    def take(near, radius, least=1):
        free = [c for c in cells if c not in used]
        pick = [c for c in free if c.centroid.distance(Point(at(*near))) < radius]
        pick = pick or sorted(free, key=lambda c: c.centroid.distance(Point(at(*near))))[:least]
        used.update(pick)
        return pick
    used = set()
    temple_sq = unary_union(take((0, 0), 120))
    towers_sq = unary_union(take((-470, 15), 115))
    veil_sq = unary_union(take((470, 0), 105))
    docks = take((-250, -430), 0)[0]
    beside = [c for c in cells if c not in used and c.distance(towers_sq) < 1 and c.distance(river) > 30]
    wardens = max(beside, key=lambda c: c.area)
    used.add(wardens)
    stores = take((330, 380), 0)[0]
    cloudwine = take((-320, 390), 0)[0]
    edge_cells = sorted((c for c in cells if c not in used and c.exterior.distance(city.exterior) < 1), key=lambda c: heading(c.centroid.coords[0]))
    orchards = set(edge_cells[k] for k in range(int(rng.integers(len(edge_cells))) % 5, len(edge_cells), len(edge_cells) // 4)[:4])
    squares = [temple_sq, towers_sq, veil_sq]

    # ---- the ground: the city's floor is street; the river runs over it; the blocks stand on it
    p.add("ground", f'<path d="{poly_d(city)}" fill="{ROAD}"/>')
    p.add("water", f'<path d="{poly_d(river.intersection(canvas))}" fill="{WATER}" stroke="{INK}" stroke-width="1.6"/>')
    p.block(river)
    p.block(city.buffer(12))
    for sq in squares:
        p.add("streets", f'<path d="{poly_d(sq.buffer(-3.5, join_style=2))}" fill="{STONE}" stroke="{INK}" stroke-width=".8" stroke-opacity=".5"/>')
    keep_off = unary_union([main_streets, river.buffer(6), city.exterior.buffer(14)])
    houses, gardens, yards_, trees_ = [], [], [], []
    for c in cells:
        if c in used: continue
        for b in [q for w in parts(c.buffer(-3.6, join_style=2).difference(keep_off)) for q in lanes(w, 9000, rng)]:
            if b.area < 60: continue
            r = Point(b.centroid).distance(Point(at(0, 0))) / RX
            if c in orchards:  # orchards and gardens within the walls, a house or two among them
                gardens.append(poly_d(b))
                x0, y0, x1, y1 = b.bounds
                for _ in range(int(b.area / 260)):
                    x, y, rr = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(5, 8)
                    if b.buffer(-2).contains(Point(x, y).buffer(rr)): trees_.append((x, y, rr))
                houses += lots_of(b, 300, 14, rng)[:int(rng.integers(2, 6))]
                continue
            (gardens if r > .6 and rng.random() < .3 else yards_).append(poly_d(b))
            houses += lots_of(b, 90 + 110 * r, 28 - 13 * r + rng.uniform(-2, 2), rng)
    big = [h for h in houses if h.area > 380]
    seal = max([h for h in houses if h.distance(towers_sq) < 10], key=lambda h: h.area)
    slate = set(id(h) for h in big if rng.random() < .25)
    roofs = {col: [] for col in ROOFS + (SLATE,)}
    for h in houses:
        if h is not seal:
            roofs[SLATE if id(h) in slate else ROOFS[int(rng.integers(len(ROOFS)))]].append(poly_d(h))
    p.add("houses", f'<path d="{" ".join(yards_)}" fill="{YARD}"/>')
    p.add("houses", f'<path d="{" ".join(gardens)}" fill="{GARDEN}" stroke="{INK}" stroke-width=".5" stroke-opacity=".4"/>')
    for col, ds in roofs.items():
        if ds: p.add("houses", f'<path d="{" ".join(ds)}" fill="{col}" stroke="{INK}" stroke-width=".8" stroke-linejoin="round"/>')
    p.add("trees", "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#a9b886" stroke="{INK}" stroke-width=".6"/>' for x, y, r in trees_))
    p.add("marks", f'<path d="{poly_d(seal)}" fill="{MARK}" stroke="{INK}" stroke-width="1.3" data-place="lift-seal-office" class="place"/>')

    # bridges, where the main streets cross the river
    for m in mains:
        for seg in getattr(m.intersection(river.buffer(7)), "geoms", [m.intersection(river.buffer(7))]):
            if seg.geom_type == "LineString" and seg.length > 10:
                p.add("piers", f'<path d="{poly_d(seg.buffer(8, cap_style=2))}" fill="#d9c9a6" stroke="{INK}" stroke-width="1.4"/>')

    # ---- the roads out of the gates, the way the map's leave town, and a straggle of houses along them
    roads = []
    for g, name, group, hd in gates:
        a = math.radians(hd)
        end = (g[0] + math.cos(a) * 1600, g[1] + math.sin(a) * 1600)
        if group == "tracks":
            end = (g[0] + math.cos(a) * 260, g[1] + math.sin(a) * 260)
        line = wiggle(smooth(LineString([g, ((g[0] + end[0]) / 2 + 20, (g[1] + end[1]) / 2 - 15), end]), 3), 5, 1.4, rng, 14).intersection(canvas)
        width = {"roads": 15, "trails": 10}.get(group, 8)
        p.street(line, width)
        roads.append((name, line, width))
    outside = canvas.difference(city.buffer(50)).difference(river.buffer(14))
    for name, line, width in roads:
        if width < 9: continue
        ribbon = outside.intersection(line.buffer(48)).intersection(Point(CX, CY).buffer(1150))
        p.houses_along(line, ribbon, depth=(10, 16), width=(8, 14), gap=(1, 9), street_w=width)
    tints = ("#e3d6b0", "#dccd9f", "#e6dbb8", "#d5c79a", "#e0d2a6", "#d9d0a2")
    taken = unary_union([ln.buffer(w / 2 + 14) for _, ln, w in roads] + [city.buffer(110)])
    for _ in range(70):
        fx, fy = rng.uniform(0, W), rng.uniform(0, H)
        ang = rng.uniform(-25, 25) + rng.choice([0, 90])
        nx_, ny_ = int(rng.integers(2, 5)), int(rng.integers(1, 3))
        sw_, sh_ = rng.uniform(28, 42), rng.uniform(70, 120)
        strips = [affinity.rotate(box(fx + (i - nx_ / 2) * sw_, fy + (j - ny_ / 2) * sh_, fx + (i - nx_ / 2) * sw_ + sw_ - 3, fy + (j - ny_ / 2) * sh_ + sh_ - 3), ang, origin=(fx, fy))
                  for i in range(nx_) for j in range(ny_)]
        farm = unary_union(strips)
        if farm.intersects(taken) or not outside.contains(farm.centroid): continue
        taken = taken.union(farm.buffer(8))
        for s in strips:
            g = s.intersection(outside)
            if g.area > 200:
                p.add("ground", f'<path d="{poly_d(g)}" fill="{tints[int(rng.integers(len(tints)))]}" stroke="#a89068" stroke-width=".7" opacity=".9"/>')
    p.trees(outside.difference(taken.difference(city.buffer(110))), 280, r=(5, 10))

    # ---- the great squares and what stands on them
    # the Loom Temple, at the city's heart: a domed rotunda open to the sky, the ring of woven light within
    x, y = at(0, 0)
    tr = min(84, temple_sq.exterior.distance(Point(x, y)) * .55)
    k = tr / 80
    for j in range(4):
        wing = affinity.rotate(box(x, y - 16 * k, x + 112 * k, y + 16 * k), 45 + 90 * j, origin=(x, y))
        p.add("marks", f'<path d="{poly_d(wing)}" fill="{SLATE}" stroke="{INK}" stroke-width="1.2" data-place="loom-temple" class="place"/>')
    p.add("marks", "".join(f'<g data-place="loom-temple" class="place">{dome(x + 108 * k * math.cos(math.radians(45 + 90 * j)), y + 108 * k * math.sin(math.radians(45 + 90 * j)), 27 * k)}</g>' for j in range(4)))
    p.add("marks", f'<g data-place="loom-temple" class="place">{dome(x, y, tr, oculus=30 * k)}'
                   f'<circle cx="{x}" cy="{y}" r="{30 * k:.1f}" fill="#f3e6b8" stroke="{INK}" stroke-width="1.2"/>'
                   f'<circle cx="{x}" cy="{y}" r="{21 * k:.1f}" fill="none" stroke="{GOLD}" stroke-width="5"/>'
                   f'<circle cx="{x}" cy="{y}" r="{21 * k:.1f}" fill="none" stroke="#fff3c4" stroke-width="1.6" stroke-dasharray="4 3"/></g>')
    temple_lab = (0, tr * 1.75 + 22)

    # the Skyward Towers: three spires round the anchor-runes, in the Tower Plazas
    tc = polylabel(towers_sq, 1)
    rr = min(62, towers_sq.exterior.distance(tc) * .5)
    p.add("streets", f'<path d="{poly_d(towers_sq.buffer(-3.5, join_style=2))}" fill="transparent" data-place="lift-plaza" class="place"/>'
                     f'<circle cx="{tc.x:.1f}" cy="{tc.y:.1f}" r="{rr:.1f}" fill="none" stroke="{GOLD}" stroke-width="2" stroke-dasharray="7 5"/>')
    p.add("marks", "".join(f'<g data-place="skyward-towers" class="place">{tower(tc.x + rr * math.cos(math.radians(a)), tc.y + rr * math.sin(math.radians(a)), rr * .48, "#8799a5")}</g>' for a in (-90, 30, 150)))

    # the Veil Court: a broad reflective square, inlaid
    vc = polylabel(veil_sq, 1)
    vr = min(92, veil_sq.exterior.distance(vc) * .85)
    x, y = vc.x, vc.y
    sq = vr * .76
    star = unary_union([box(x - sq, y - sq, x + sq, y + sq), affinity.rotate(box(x - sq, y - sq, x + sq, y + sq), 45)])
    p.add("streets", f'<path d="{poly_d(veil_sq.buffer(-3.5, join_style=2))}" fill="#e7eeee" stroke="{INK}" stroke-width="1.2" data-place="veil-court" class="place"/>')
    p.add("marks", f'<g fill="none" stroke="{INK}" stroke-width=".8" opacity=".55" style="pointer-events:none"><circle cx="{x:.1f}" cy="{y:.1f}" r="{vr:.1f}"/>'
                   f'<path d="{poly_d(star)}"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{vr * .37:.1f}"/></g>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{vr * .37:.1f}" fill="{GLASS}" opacity=".6" style="pointer-events:none"/>')
    lift = nearest_points(veil_sq.buffer(-8).exterior, Point(x + 200, y - 260))[0]
    lx, ly = lift.x, lift.y
    arch = f"M{lx - 14:.1f} {ly + 9:.1f}V{ly - 4:.1f}A14 14 0 0 1 {lx + 14:.1f} {ly - 4:.1f}V{ly + 9:.1f}"
    p.add("marks", f'<g data-place="windspire-lift" class="place"><path d="{arch}" fill="none" stroke="{INK}" stroke-width="7"/><path d="{arch}" fill="none" stroke="#cfdde2" stroke-width="4"/></g>')

    # the Warden's Court, the yards, and the Skyward Gate Docks against the north wall
    grand_hall(p, wardens.buffer(-3.6, join_style=2).difference(keep_off), "wardens-court")
    yard(p, stores.buffer(-3.6, join_style=2).difference(keep_off), "candle-yards", rng, 3)
    yard(p, cloudwine.buffer(-3.6, join_style=2).difference(keep_off), "cloudwine", rng, 2, vats=5)
    d = max(parts(docks.buffer(-3.6, join_style=2).difference(keep_off)), key=lambda g: g.area)
    p.add("marks", f'<path d="{poly_d(d)}" fill="#e3d6b8" stroke="{INK}" stroke-width="1.4" stroke-dasharray="6 3" data-place="skyward-gate-docks" class="place"/>')
    dc = polylabel(d, 1)
    for j in range(-2, 3):
        mx, my = dc.x + j * 40, dc.y - 22
        if not d.buffer(-12).contains(Point(mx, my + 30)): continue
        p.add("marks", f'<g data-place="skyward-gate-docks" class="place"><circle cx="{mx:.1f}" cy="{my:.1f}" r="8" fill="{GLASS}" stroke="{INK}" stroke-width="1.5"/>'
                       f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="3.5" fill="none" stroke="#8fb8c6" stroke-width="2"/></g>')
        p.add("boats", skycraft(mx, my + 34, 90 + rng.uniform(-8, 8), .8))

    # ---- the walls: straight lengths between towers, a gatehouse on every road, water-gates for the Albrole
    gate_pts = [Point(g) for g, *_ in gates]
    band = city.exterior.buffer(7).difference(unary_union([g.buffer(14) for g in gate_pts] + [river]))
    p.add("marks", f'<path d="{poly_d(band)}" fill="#8f7b5c" stroke="{INK}" stroke-width="1.3" data-place="walls" class="place"/>')
    ext = city.exterior
    corners = [Point(c) for c in list(ext.coords)[:-1]]
    p.add("marks", "".join(tower(q.x, q.y, 12) for q in corners if min(q.distance(g) for g in gate_pts) > 34 and river.distance(q) > 14))
    for q in parts(ext.buffer(7).intersection(river.buffer(16)).difference(river)):  # a tower on either bank at the water-gates
        p.add("marks", tower(q.centroid.x, q.centroid.y, 14))
    for g in gate_pts:
        s = ext.project(g)
        a, b = ext.interpolate(s - 1), ext.interpolate(s + 1)
        ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
        for side in (-1, 1):
            tx, ty = g.x + side * 22 * math.cos(math.radians(ang)), g.y + side * 22 * math.sin(math.radians(ang))
            p.add("marks", f'<rect x="-10" y="-10" width="20" height="20" fill="#6d5a40" stroke="{INK}" stroke-width="1.2" transform="translate({tx:.1f} {ty:.1f}) rotate({ang:.0f})"/>')
    se = nearest_points(ext, Point(at(950, 140)))[0]  # Stormwatch Edge, a terrace out beyond the east wall
    terrace = Point(se.x, se.y).buffer(55).difference(city)
    rail = longest_line(Point(se.x, se.y).buffer(47).exterior.difference(city.buffer(4)))
    p.add("marks", f'<path d="{poly_d(terrace)}" fill="{STONE}" stroke="{INK}" stroke-width="1.6" data-place="stormwatch-edge" class="place"/>'
                   f'<path d="{path_d(rail.coords)}" fill="none" stroke="{INK}" stroke-width="1" stroke-dasharray="2 3"/>')

    # ---- words
    L = lambda pt, text, size=15, cls="tp-lbl", **kw: p.label(pt[0], pt[1], text, size, cls, **kw)
    L(at(*temple_lab), "The Loom Temple", 20, pid="loom-temple")
    L((tc.x, tc.y + rr + 34), "the Skyward Towers", 17, pid="skyward-towers")
    L((seal.centroid.x, seal.centroid.y - 14), "Lift-Seal Office", 12, pid="lift-seal-office")
    L((vc.x, vc.y + 6), "The Veil Court", 18, pid="veil-court")
    L((lx + 20, ly - 4), "Windspire Lift", 12, anchor="start", pid="windspire-lift")
    w = polylabel(wardens, 1)
    L((w.x, w.y + 4), "The Warden's Court", 12, pid="wardens-court")
    L((dc.x, d.bounds[3] + 16), "Skyward Gate Docks", 14, pid="skyward-gate-docks")
    L((polylabel(stores, 1).x, stores.bounds[3] + 14), "the Loom Stores", 13, pid="candle-yards")
    L((polylabel(cloudwine, 1).x, cloudwine.bounds[3] + 14), "Cloudwine Distilleries", 13, pid="cloudwine")
    L((se.x + 64, se.y + 5), "Stormwatch Edge", 14, anchor="start", pid="stormwatch-edge")
    L(at(-560, -120), "THE LUMINOUS WARD", 24, "tp-area", rotate=-8, spacing=5, pid="luminous-ward")
    L(at(-170, 330), "THE LUMINOUS WARD", 22, "tp-area", rotate=4, spacing=5, pid="luminous-ward")
    for name, line, width in roads:
        if not name: continue
        q = line.interpolate(min(line.length - 80, 300))
        q2 = line.interpolate(line.project(q) + 10)
        p.label(q.x, q.y - 13, name.upper(), 13, "tp-road", rotate=upright(math.degrees(math.atan2(q2.y - q.y, q2.x - q.x))), spacing=3,
                pid={"the Loom Road": "loom-road", "the Sapphire Road": "sapphire-road"}.get(name))
    q = rline.interpolate(.1, normalized=True)
    q2 = rline.interpolate(rline.project(q) + 10)
    p.label(q.x, q.y + 36, "the Albrole", 17, "tp-sub", rotate=upright(math.degrees(math.atan2(q2.y - q.y, q2.x - q.x))))

    cartouche(p, W - 250, H - 80, TOWN, "Seat of Skyloom · the Groundring", w=420)
    compass(p, W - 80, 120)
    scale_bar(p, 60, H - 50, 500)
    for pl in PLACES:
        p.place(pl["id"], pl["name"], pl["epithet"], pl["text"], BOOK)
    p.overlays.append({"id": "aerialring", "name": "Aerialring", "epithet": "Floating above the Groundring, for the winged and the very trusted",
                       "svg": aerialring((lx, ly)), "places": [dict(pl, source=BOOK) for pl in AERIAL_PLACES]})
    print(f"{'':30} {len(houses):5} houses in {len(cells)} wards")
    return p


# ---------------------------------------------------------------- the Aerialring, above it
def aerialring(lift):
    """The higher, thinner loop of galleries floating over the city, with its shadow cast on the streets below."""
    out = ['<defs><filter id="aerial-blur" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="8"/></filter></defs>',
           f'<rect width="{W}" height="{H}" fill="#edf1ee" opacity=".5" style="pointer-events:none"/>']
    light = "#8fb8c6"
    deck = "#f1ecdf"

    # the shapes of everything aloft, for the shadow
    ring = T(ellipse(0, 0, 640, 345)).difference(T(ellipse(0, 0, 588, 300)))
    overlook = T(octagon(0, 0, 100))
    walk_lines = (((0, -96), (0, -302)), ((0, 96), (0, 302)), ((96, 0), (590, 0)), ((-96, 0), (-590, 0)))
    walks = [T(LineString(pts)).buffer(7, cap_style=2) for pts in walk_lines]
    pads = [T(Point(x, y).buffer(24)) for x, y in ((0, -322), (0, 322), (614, 0), (-614, 0))]
    market = T(box(-150, -458, 150, -342).buffer(10, join_style=1))
    aeries = {}
    for side in (-1, 1):
        cx = side * 735
        aeries[side] = unary_union([T(Point(cx, 0).buffer(62)), T(LineString([(side * 630, 0), (cx, 0)]).buffer(16, cap_style=2))]
                                   + [T(Point(cx + side * 70 * math.cos(math.radians(a)), 72 * math.sin(math.radians(a))).buffer(30)) for a in (-80, 0, 80)])
    ring_x = CX + 640 * math.sqrt(max(0, 1 - ((lift[1] - CY) / 345) ** 2)) - 6  # where the ring passes the lift
    liftdeck = unary_union([Point(*lift).buffer(26), LineString([(ring_x, lift[1]), lift]).buffer(9, cap_style=2)])
    dropdeck = T(box(-30, 340, 30, 520))
    aloft = unary_union([ring, overlook, market, liftdeck, dropdeck, *aeries.values()] + walks + pads)
    out.append(f'<path d="{poly_d(affinity.translate(aloft, 34, 52))}" fill="#1f2a33" opacity=".24" filter="url(#aerial-blur)" style="pointer-events:none"/>')

    # the Sky Lanes: a loop round the ring and lanes away over the country, lit by dim rune-lamps
    lanes = [list(T(ellipse(0, 0, 820, 480)).exterior.coords)]
    for pts in (((-760, -260), (-960, -440), (-1240, -600)), ((-780, 250), (-980, 420), (-1240, 600)), ((260, -460), (330, -620), (380, -820)),
                ((815, -60), (1000, -110), (1240, -130)), ((560, 380), (760, 560), (900, 800))):
        lanes.append(list(smooth(LineString([at(*q) for q in pts]), 3).coords))
    for k, pts in enumerate(lanes):
        dd = path_d(pts, closed=k == 0)
        out.append(f'<path d="{dd}" fill="none" stroke="{light}" stroke-width="10" opacity=".22" stroke-linecap="round"/>'
                   f'<path d="{dd}" fill="none" stroke="{light}" stroke-width="2.6" stroke-dasharray="3 11" stroke-linecap="round"/>'
                   f'<path d="{dd}" fill="none" stroke="transparent" stroke-width="20" data-place="sky-lanes" class="place"/>')
        line = LineString(pts)
        out.append("".join(f'<circle cx="{q.x:.1f}" cy="{q.y:.1f}" r="3.4" fill="#f2d98a" stroke="{INK}" stroke-width=".6"/>'
                           for q in (line.interpolate(s) for s in range(40, int(line.length), 90))))
    loop = LineString(lanes[0])
    for t in (.04, .17, .31, .45, .58, .72, .86):  # winged patrols
        q, q2 = loop.interpolate(t, normalized=True), loop.interpolate(t + .003, normalized=True)
        ang = math.degrees(math.atan2(q2.y - q.y, q2.x - q.x))
        out.append(f'<path d="M-12 -6L0 2 12 -6" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" '
                   f'transform="translate({q.x:.1f} {q.y - 16:.1f}) rotate({ang - 90:.0f})"/>')

    # the ring of open galleries, with a balustrade along either edge
    out.append(f'<path d="{poly_d(ring)}" fill="{deck}" fill-rule="evenodd" stroke="{INK}" stroke-width="1.8" data-place="aerialring" class="place"/>')
    spokes = "".join(f"M{CX + 592 * math.cos(a):.1f} {CY + 304 * math.sin(a):.1f}L{CX + 636 * math.cos(a):.1f} {CY + 341 * math.sin(a):.1f}"
                     for a in [2 * math.pi * k / 120 for k in range(120)])
    out.append(f'<path d="{spokes}" stroke="{INK}" stroke-width=".7" opacity=".35" style="pointer-events:none"/>')
    for e in (T(ellipse(0, 0, 632, 337)), T(ellipse(0, 0, 596, 308))):
        out.append(f'<path d="{path_d(e.exterior.coords, True)}" fill="none" stroke="{INK}" stroke-width="2.4" stroke-dasharray=".1 9" stroke-linecap="round" opacity=".7" style="pointer-events:none"/>')

    # the arcane walkways in to the Halo Overlook, and the rune pads where they meet the ring
    for w in walks:
        out.append(f'<path d="{poly_d(w)}" fill="{deck}" stroke="{INK}" stroke-width="1.3"/>')
    for pts in walk_lines:
        line = T(LineString(pts))
        out.append("".join(f'<circle cx="{q.x:.1f}" cy="{q.y:.1f}" r="2.6" fill="#f2d98a" stroke="{INK}" stroke-width=".5"/>'
                           for q in (line.interpolate(s) for s in range(20, int(line.length), 36))))
    for pd in pads:
        c = pd.centroid
        out.append(f'<circle cx="{c.x:.1f}" cy="{c.y:.1f}" r="24" fill="{GLASS}" stroke="{INK}" stroke-width="1.4"/>'
                   f'<circle cx="{c.x:.1f}" cy="{c.y:.1f}" r="15" fill="none" stroke="{GOLD}" stroke-width="1.6" stroke-dasharray="4 3"/>'
                   f'<circle cx="{c.x:.1f}" cy="{c.y:.1f}" r="5" fill="{light}"/>')
    x, y = at(0, 0)
    facets = "".join(f"M{x:.1f} {y:.1f}L{x + 100 * math.cos(math.radians(22.5 + 45 * k)):.1f} {y + 100 * math.sin(math.radians(22.5 + 45 * k)):.1f}" for k in range(8))
    out.append(f'<g data-place="halo-overlook" class="place"><path d="{poly_d(overlook)}" fill="{GLASS}" fill-opacity=".85" stroke="{INK}" stroke-width="2.2"/>'
               f'<path d="{facets}" stroke="#fff" stroke-width="1.2" opacity=".6"/>'
               f'<path d="{poly_d(T(octagon(0, 0, 76)))}" fill="none" stroke="{light}" stroke-width="1.6"/>'
               f'<circle cx="{x}" cy="{y}" r="34" fill="#f3e6b8" opacity=".55"/>'
               f'<circle cx="{x}" cy="{y}" r="21" fill="none" stroke="{GOLD}" stroke-width="4" opacity=".85"/></g>')
    for ox in (-46, 46):  # the heads of the guarded stairways up from the Loom Temple
        sx, sy = at(ox, 48)
        out.append(f'<g data-place="temple-stairs" class="place"><rect x="{sx - 9:.1f}" y="{sy - 9:.1f}" width="18" height="18" fill="#c9b48e" stroke="{INK}" stroke-width="1.3"/>'
                   f'<path d="M{sx - 6:.1f} {sy + 5:.1f}h4v-4h4v-4h4" fill="none" stroke="{INK}" stroke-width="1.2"/></g>')

    # the Loft Market, on a deck out from the northern section
    out.append(f'<path d="{poly_d(market)}" fill="{deck}" stroke="{INK}" stroke-width="1.7" data-place="loft-market" class="place"/>')
    awnings = ("#c98f6a", "#a7b48a", "#c9b06a", "#9fb5c0", "#b98a9a")
    mx, my = at(0, -400)
    for i in range(9):
        for row in (-1, 1):
            sx, sy = mx - 136 + i * 31, my + row * 30 - 9
            out.append(f'<rect x="{sx:.0f}" y="{sy:.0f}" width="24" height="18" fill="{awnings[(i * 2 + row) % len(awnings)]}" stroke="{INK}" stroke-width=".8" style="pointer-events:none"/>'
                       f'<path d="M{sx + 6:.0f} {sy}v18M{sx + 12:.0f} {sy}v18M{sx + 18:.0f} {sy}v18" stroke="#fff" stroke-width="1.6" opacity=".45" style="pointer-events:none"/>')

    # the High Aeries, on the western and eastern flanks: round platforms, each with its nest-towers
    for side, shape in aeries.items():
        out.append(f'<path d="{poly_d(shape)}" fill="{deck}" stroke="{INK}" stroke-width="1.7" data-place="high-aeries" class="place"/>')
        cx = side * 735
        nests = [(cx, 0, 26)] + [(cx + side * 70 * math.cos(math.radians(a)), 72 * math.sin(math.radians(a)), 17) for a in (-80, 0, 80)]
        nests += [(cx + 38 * math.cos(math.radians(a)), 38 * math.sin(math.radians(a)), 10) for a in (60, 180, 300)]
        out.append("".join(f'<g style="pointer-events:none">{tower(*at(nx, ny), r, "#c9b48e")}</g>' for nx, ny, r in nests))

    # the Windspire Lift comes up here from the Veil Court's edge
    lx, ly = lift
    out.append(f'<g data-place="windspire-lift" class="place"><path d="{poly_d(liftdeck)}" fill="{deck}" stroke="{INK}" stroke-width="1.4"/>'
               f'<circle cx="{lx}" cy="{ly}" r="17" fill="{GLASS}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="4 3"/>'
               f'<path d="M{lx} {ly + 10}V{ly - 10}M{lx - 6} {ly - 4}L{lx} {ly - 10} {lx + 6} {ly - 4}" fill="none" stroke="{INK}" stroke-width="1.8"/></g>')

    # the Dropway: a launching-deck south off the ring, and the shaft of clear air beyond the south wall
    out.append(f'<path d="{poly_d(dropdeck)}" fill="{deck}" stroke="{INK}" stroke-width="1.5" data-place="dropway" class="place"/>')
    sx, sy = at(0, 600)
    out.append(f'<g data-place="dropway" class="place"><circle cx="{sx}" cy="{sy}" r="72" fill="#c4d1d3" fill-opacity=".55" stroke="{INK}" stroke-width="1.6" stroke-dasharray="9 6"/>'
               + "".join(f'<path d="M{sx - 14} {sy + o - 7}L{sx} {sy + o + 5} {sx + 14} {sy + o - 7}" fill="none" stroke="{INK}" stroke-width="1.7" opacity=".7"/>' for o in (-26, 0, 26))
               + "</g>")

    # words
    def lab(x, y, text, pid, size=17, cls="tp-lbl", extra=""):
        X, Y = at(x, y)
        out.append(f'<text x="{X:.1f}" y="{Y:.1f}" class="{cls} place" font-size="{size}" text-anchor="middle" data-place="{pid}"{extra}>{text}</text>')
    lab(0, -240, "THE AERIALRING", "aerialring", 26, "tp-area", ' letter-spacing="8"')
    lab(0, -394, "Loft Market", "loft-market")
    lab(0, 130, "Halo Overlook", "halo-overlook", 18)
    lab(-735, 125, "High Aeries", "high-aeries")
    lab(735, 125, "High Aeries", "high-aeries")
    lab(lift[0] - CX + 2, lift[1] - CY - 36, "Windspire Lift", "windspire-lift", 14)
    lab(0, 697, "the Dropway", "dropway")
    X, Y = at(-560, -430)
    lab(-560, -430, "SKY LANES", "sky-lanes", 14, "tp-road", f' letter-spacing="3" transform="rotate(-22 {X:.1f} {Y:.1f})"')
    return "\n".join(out)


PLACES = [
    {"id": "loom-temple", "name": "The Loom Temple", "epithet": "The great ring of woven light",
     "text": "At the city's heart, open to the sky at its apex, stands the temple that houses the great ring of woven light from which the Weave takes its name. Loomwardens pace its circumference, adjusting sigils and murmuring complex formulae. From here winds are redirected over Emberweave's dust, storms are delayed to spare the northern harvest, and the weather over Caer Veyn's harbor is kept, barely, within limits the harbormasters can tolerate. Guarded stairways climb from it to the Aerialring."},
    {"id": "skyward-towers", "name": "The Skyward Towers", "epithet": "Three tall spires rooted firmly in stone",
     "text": "The anchors of Skyloom: they house the anchor-runes, lift-wards and harassed clerks whose task is to make sure the sky-bound part of Skyloom stays attached to the rest. From The Crown, one reaches the Aerialring by way of them."},
    {"id": "lift-plaza", "name": "The Tower Plazas", "epithet": "", "text": "The plazas round the roots of the Skyward Towers, at the city's west end."},
    {"id": "lift-seal-office", "name": "The Lift-Seal Office", "epithet": "No seal, no lift",
     "text": "Where lift-seals are issued: the permits without which nobody rides the Skyward Towers up to the Aerialring."},
    {"id": "wardens-court", "name": "The Warden's Court", "epithet": "Where the Weave Warden holds court",
     "text": "The seat of the Weave Warden of Skyloom, elected from among the senior Loomwardens, at the edge of the tower plazas."},
    {"id": "veil-court", "name": "The Veil Court", "epithet": "Open to the sky above and The Crown beyond",
     "text": "A broad, reflective plaza at the city's eastern end. Here treaties concerning sky-lanes over the Union, the extension of weather wards over the other Weaves, and the limits of certain magical experiments are read aloud and bound."},
    {"id": "windspire-lift", "name": "The Windspire Lift", "epithet": "A discreet arch at the Court's edge",
     "text": "An invisible column of rising air that carries those with the proper seals up to the Aerialring."},
    {"id": "skyward-gate-docks", "name": "The Skyward Gate Docks", "epithet": "Where skycraft sidle in along glowing mooring-rings",
     "text": "Against the northern wall. Couriers from Northreach, diplomatic cutters out of Caer Veyn, and merchant vessels that prefer thin air to crowded roads all put in here. Heavier craft put down instead at Farwatch Landing on the coast."},
    {"id": "luminous-ward", "name": "The Luminous Ward", "epithet": "Light treated more as a guest than a resource",
     "text": "A district of pale houses and glass-roofed courtyards spreading west and south. Mirrors, thin stone and cleverly angled panels (most of them fired in Midhurstnes) pull dawn and dusk deep into interior rooms. Wind-chimes and wire-songs hum between balconies, giving the whole ward a faint, constant music."},
    {"id": "stormwatch-edge", "name": "Stormwatch Edge", "epithet": "Many oaths are taken here; a few are not survived",
     "text": "A simple stone terrace with a simple stone rail out from the eastern wall, looking toward The Crown's western wall and, beyond it, the slow, silent churning of the Everstorm that rings the heart of the Union."},
    {"id": "walls", "name": "The Walls", "epithet": "Low walls and open terraces", "text": "The city's edges are ringed by low walls, towers under slate cones, and open terraces."},
    {"id": "candle-yards", "name": "The Loom Stores", "epithet": "Cheese, liquor, and a great many candles",
     "text": "Where the Aerialring's needs are gathered before being sent up: cheese, liquor, and a great many candles."},
    {"id": "cloudwine", "name": "The Cloudwine Distilleries", "epithet": "Drunk mostly by people who have just come down",
     "text": "Distilleries that make cloudwine, a clear, cold spirit."},
    {"id": "loom-road", "name": "The Loom Road", "epithet": "", "text": "East through the Loomward stormgate to The Crown."},
    {"id": "sapphire-road", "name": "The Sapphire Road", "epithet": "", "text": "West through Midhurstnes, Castfield and Clitford toward Cloudmoor Harbor."},
]

AERIAL_PLACES = [
    {"id": "aerialring", "name": "The Aerialring", "epithet": "It belongs to whatever has learned to trust the sky",
     "text": "The higher, thinner loop over the Groundring: open galleries, high aeries and Sky Lanes, reserved mostly for the winged and the very trusted. It is reached by the Windspire Lift or through guarded stairways in the Loom Temple. Wing-guards enforce three simple rules: no reckless flight near docks, edges, or the Sky Lane beacons; no tampering with lift, gravity, or wind without proper sigils; and no duels over open Everstorm."},
    {"id": "halo-overlook", "name": "The Halo Overlook", "epithet": "For vows expected to outlive everyone present",
     "text": "A circular platform of translucent stone at the Aerialring's exact centre, suspended directly above the Loom Temple's inner ring. From here one can look down through crystal at the Loom itself, and beyond that to the fields of the Shadowline, a faint pattern of roads and threads barely visible through spell-glass. It is used sparingly: for flight-rites, public auguries, and vows whose consequences are expected to outlive everyone present."},
    {"id": "temple-stairs", "name": "The Temple Stairways", "epithet": "Guarded",
     "text": "The guarded stairways that climb from the Loom Temple below: with the Windspire Lift, the way up to the Aerialring."},
    {"id": "high-aeries", "name": "The High Aeries", "epithet": "On the western and eastern flanks",
     "text": "Home to elves of the upper air, aarakocra scouts, harpies who have traded shriek for discipline, and certain tieflings and Sangrith bearing rune-bound wings."},
    {"id": "loft-market", "name": "The Loft Market", "epithet": "A compact cluster of stalls",
     "text": "In the northern section: feathersteel harness and flight-cloaks (Castfield leather, Waringley wool), instruments that measure altitude, pressure, and cloud-depth, and small vials of carefully stored, highly unstable weather."},
    {"id": "windspire-lift", "name": "The Windspire Lift", "epithet": "No seal, no lift",
     "text": "The invisible column of rising air from the arch at the Veil Court's edge comes up here, carrying those with the proper seals."},
    {"id": "dropway", "name": "The Dropway", "epithet": "When falling becomes flight, and when it does not",
     "text": "To the south a clear shaft of air opens toward the hills below. Young fliers are taught here, under supervision, precisely when falling becomes flight and when it does not. Those who learn the lesson incorrectly are buried at Buneymouth."},
    {"id": "sky-lanes", "name": "The Sky Lanes", "epithet": "Paths in the air marked by dim rune-light",
     "text": "The lanes along which winged patrols fly. The lamps that mark them over the countryside below are tended from the ground, by the candle-makers of Aillenestre and Fercelle."},
]
