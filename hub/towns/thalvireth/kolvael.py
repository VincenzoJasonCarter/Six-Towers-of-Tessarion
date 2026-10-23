"""Kolvael, the Hundred Terraces: the Green Cradle's largest town, a bowl of hillside cut into steps (lore-book 26)."""
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity

from plans import (Plan, PALETTES, INK, GROWN, MARK, ROAD, path_d, poly_d, smooth, wiggle,
                   compass, scale_bar, cartouche, map_town, upright)

TOWN = "Kolvael"
EPITHET = "the Hundred Terraces"
BOOK = "Of The Green Cradle"

TERRACES = 162                # "There are, in fact, a hundred and sixty-two of them"
CROPS = ("#b7c98c", "#a3ba78", "#cbd59a", "#e3d08b", "#d9bc6a", "#cdb38c")  # sown, in leaf, young, turning, gold, bare


def draw():
    """Kolvael (lore-book 26): about nine thousand people living on the terraces themselves,
    each line's house at the head of its own stair, three days up the Root-Road from Weneleth.
    The Root-Road comes down from the north-west and runs on south, the way it does on the
    map. East of it the hillside rises in a great bowl cut into 162 terraces from the valley
    floor to the crest, an amphitheatre facing the Keeper's Stair at its foot. The moot meets
    on the uppermost terrace. South of the Stair a surface root of Ix'kaanil comes out of the
    hill and runs off down the valley toward K'anvael, and the ground on either side of it
    is the Planting Field."""
    W, H = 1800, 1300
    p = Plan("kolvael", W, H, seed=2026)
    rng = p.rng
    canvas = box(-20, -20, W + 20, H + 20)
    S = np.array([540.0, 610.0])                       # the Keeper's Stair: the bowl's focus

    # ---- the Root-Road, as the map has it: down from the north-west, on to the south
    heads = [h for _, _, h in map_town(TOWN)["roads"]]
    gap = lambda a, b: abs((a - b + 180) % 360 - 180)
    north = min(heads, key=lambda h: gap(h, -126))      # toward Wayebiel
    south = min(heads, key=lambda h: gap(h, 82))        # toward K'anvael
    R0 = S + (-34, 6)                                  # the road runs just west of the Stair
    def arm(deg, n=14, amp=10):
        u = np.array([math.cos(math.radians(deg)), math.sin(math.radians(deg))])
        return [tuple(R0 + u * t + np.array([-u[1], u[0]]) * amp * math.sin(t / 260)) for t in np.linspace(0, 1500, n)]
    road = smooth(LineString(arm(north)[::-1] + arm(south)[1:]), 2)

    # ---- the bowl: terraces as the hill's contours round the Stair, east of the road
    ph = rng.uniform(0, 6.3, 4)
    def radius(r, th):  # one shared ripple, so the terraces run parallel like contours, spurs and all
        return r * (1 + .045 * (math.sin(3 * th + ph[0]) + .5 * math.sin(7 * th + ph[1]) + .25 * math.sin(13 * th + ph[2])))
    r0, step = 150.0, 5.8
    rs = [r0 + i * step for i in range(TERRACES + 1)]
    lo = lambda i: math.radians(-86 + 7 * math.sin(i / 9 + ph[3]))       # where each terrace ends, north
    hi = lambda i: math.radians(56 + 6 * math.sin(i / 7 + ph[2]))        # and south, above the valley floor
    def at(r, th): return (S[0] + radius(r, th) * math.cos(th), S[1] + radius(r, th) * math.sin(th))
    def band(i, inner_pad=0.0, outer_pad=1.4):
        t = np.linspace(lo(i), hi(i), 160)
        out = [at(rs[i + 1] - outer_pad, a) for a in t]
        inn = [at(rs[i] + inner_pad, a) for a in t[::-1]]
        return Polygon(out + inn).buffer(0)
    bowl = unary_union([band(i, 0, 0) for i in range(TERRACES)]).buffer(.6)
    crest_r = rs[-1]

    p.add("ground", f'<path d="{poly_d(canvas)}" fill="url(#grass)"/>')

    # every terrace planted, each at its own stage: green, then gold, then green again
    state = int(rng.integers(len(CROPS)))
    for i in range(TERRACES):
        if rng.random() < .55: state = (state + int(rng.integers(1, 3))) % len(CROPS)
        g = band(i).intersection(canvas)
        if not g.is_empty:
            p.add("ground", f'<path d="{poly_d(g)}" fill="{CROPS[state]}"/>')
    # the retaining walls, every name on them; the oldest, at the foot, cut deepest
    for i in range(1, TERRACES + 1):
        t = np.linspace(lo(min(i, TERRACES - 1)), hi(min(i, TERRACES - 1)), 160)
        wall = LineString([at(rs[i], a) for a in t]).intersection(canvas)
        for part in getattr(wall, "geoms", [wall]):
            if part.geom_type != "LineString": continue
            old = i <= 14
            p.add("contours", f'<path d="{path_d(part.coords)}" fill="none" stroke="{MARK if old else INK}" stroke-width="{1.5 if old else .55}" opacity="{.85 if old else .45}"'
                              + (' data-place="old-walls" class="place"' if old else "") + "/>")

    # ---- stairs up the bowl, through every terrace; the Great Stair climbs to the moot
    stair_angles = [-74, -56, -38, -10, 8, 26, 44]
    great = -10
    stairs = {}
    for a in stair_angles:
        th = math.radians(a)
        pts = [at(r, th + .012 * math.sin(r / 47)) for r in np.arange(r0 - 30, crest_r + 2, 8)]
        stairs[a] = LineString(pts).intersection(canvas)

    # ---- the valley floor: the Stair, the Daykeepers' House, the Planting Field and the root
    keeper = affinity.translate(affinity.rotate(box(-14, -11, 14, 11), great, origin=(0, 0)), *S)
    platform = affinity.translate(affinity.rotate(box(14, -9, 30, 9), great, origin=(0, 0)), *S)
    dayhouse = affinity.translate(affinity.rotate(box(-26, -13, 26, 13), south - 90, origin=(0, 0)), *(R0 + (-58, -40)))
    moot_t = np.linspace(math.radians(great - 7), math.radians(great + 7), 40)
    moot = Polygon([at(crest_r, a) for a in moot_t] + [at(crest_r + 40, a) for a in moot_t[::-1]])
    # the great root comes up out of the hill below the lowest terrace and runs off south down the valley
    rt = np.linspace(0, 1, 40)
    root_line = smooth(LineString([(S[0] + 40 + 150 * s + 22 * math.sin(s * 9 + ph[1]), S[1] + 70 + 760 * s) for s in rt]), 2)
    root = root_line.buffer(8, cap_style=1)
    rootlets = []
    for s0 in np.linspace(.08, .95, 11):
        q = root_line.interpolate(s0, normalized=True)
        side = rng.choice([-1, 1])
        rootlets.append(LineString([(q.x, q.y), (q.x + side * rng.uniform(40, 90), q.y + rng.uniform(-30, 40))]))
    field = (root_line.buffer(150).union(unary_union([r_.buffer(26) for r_ in rootlets]))
             .difference(road.buffer(18)).difference(bowl.buffer(4)).intersection(canvas)
             .difference(Point(*S).buffer(60)))
    field = max(getattr(field, "geoms", [field]), key=lambda g: g.area)

    for g in (keeper, platform, dayhouse, moot, root):
        p.block(g.buffer(3))
    p.block(road.buffer(9))

    # the soil of the Field, and the marigolds on it
    p.add("ground", f'<path d="{poly_d(field)}" fill="#d8c398" stroke="{INK}" stroke-width=".8" stroke-dasharray="5 4" data-place="planting-field" class="place"/>')
    minx, miny, maxx, maxy = field.bounds
    for _ in range(700):
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if field.contains(Point(x, y)) and not root.buffer(3).contains(Point(x, y)):
            p.add("ground", f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(1.2, 2.6):.1f}" fill="{rng.choice(["#e8902a", "#f0a830", "#d9771f"])}" opacity=".85"/>')
    for r_ in rootlets:
        p.add("marks", f'<path d="{path_d(r_.coords)}" fill="none" stroke="{INK}" stroke-width="5.5" stroke-linecap="round"/>'
                       f'<path d="{path_d(r_.coords)}" fill="none" stroke="#8a6a4a" stroke-width="3.6" stroke-linecap="round"/>')
    p.landmark("great-root", root, fill="#8a6a4a")
    p.add("marks", f'<path d="{path_d(root_line.coords)}" fill="none" stroke="#b08a62" stroke-width="3" opacity=".7" style="pointer-events:none"/>')

    # ---- the roads and stairs
    p.street(road, 13, ROAD)
    for a, ln in stairs.items():
        for part in getattr(ln, "geoms", [ln]):
            if part.geom_type == "LineString" and part.length > 20:
                p.street(part, 8 if a == great else 4.5, ROAD)

    # ---- landmarks
    p.landmark("keepers-stair", keeper, fill="#f7f3e6")
    for k in range(1, 9):  # nine steps up from the road
        a_ = affinity.translate(affinity.rotate(LineString([(-14 + 28 * k / 9, -11), (-14 + 28 * k / 9, 11)]), great, origin=(0, 0)), *S)
        p.add("marks", f'<path d="{path_d(a_.coords)}" stroke="{INK}" stroke-width=".7" opacity=".6" style="pointer-events:none"/>')
    p.landmark("keepers-stair", platform, fill=GROWN)
    queue_dir = np.array([math.cos(math.radians(north)), math.sin(math.radians(north))])
    for k in range(18):  # children holding their households' places in the queue
        q = R0 + queue_dir * (24 + 7 * k) + np.array([-queue_dir[1], queue_dir[0]]) * (11 + 1.5 * math.sin(k))
        p.add("marks", f'<circle cx="{q[0]:.1f}" cy="{q[1]:.1f}" r="1.9" fill="{MARK}" stroke="{INK}" stroke-width=".5" data-place="keepers-stair" class="place"/>')
    p.landmark("daykeepers-house", dayhouse)
    p.landmark("moot-terrace", moot, fill="#e6d6b4")

    # ---- houses: each line's house at the head of its stair, the households crowded round it
    p.palette = PALETTES["elf"]
    for i in range(TERRACES):
        rm = (rs[i] + rs[i + 1]) / 2
        for a in stair_angles:
            if rng.random() > .62: continue
            for side in (-1, 1):
                if side == 1 and rng.random() < .5: continue
                w = rng.uniform(7, 12)
                th = math.radians(a) + side * (w / 2 + 6) / rm
                x, y = at(rm, th)
                if not (math.radians(-90) < th < hi(i) and th > lo(i)): continue
                p.house(x, y, w, 4.3, math.degrees(th) + 90)
    # the valley floor: inns and halls along the Root-Road, either side of the Stair
    floor = Point(*R0).buffer(260).difference(bowl).difference(field.buffer(14))
    p.houses_along(road, floor, depth=(10, 16), width=(9, 15), gap=(2, 9), street_w=13)
    p.infill(floor.difference(Point(*S).buffer(70)), 140, [road], size=(7, 11))

    # ---- glyph-lamps for the long nights, strung up the Great Stair and along every ninth terrace
    for r in np.arange(r0, crest_r, 11):
        for side in (-1, 1):
            x, y = at(r, math.radians(great) + side * 7 / r)
            p.add("marks", f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.5" fill="#f2c14e" stroke="{INK}" stroke-width=".4" data-place="lamp-strings" class="place"/>')
    for i in range(4, TERRACES, 9):
        rm = (rs[i] + rs[i + 1]) / 2
        for a in np.arange(lo(i) + .02, hi(i), 26 / rm):
            x, y = at(rm, a)
            if 0 < x < W and 0 < y < H:
                p.add("marks", f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.1" fill="#f2c14e" opacity=".9" style="pointer-events:none"/>')
    # cisterns under the terraces, and the bead-cords hung on the oldest walls
    for _ in range(90):
        i = int(rng.integers(3, TERRACES - 2))
        a = rng.uniform(lo(i) + .03, hi(i) - .03)
        x, y = at((rs[i] + rs[i + 1]) / 2, a)
        c = Point(x, y).buffer(2.6)
        if 0 < x < W and 0 < y < H and p.free(c):
            p.block(c)
            p.add("marks", f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="#7d8f96" stroke="{INK}" stroke-width=".8" data-place="chultuns" class="place"/>')
    for i in range(1, 15):
        for a in stair_angles:
            for side in (-1, 1):
                x, y = at(rs[i] - .8, math.radians(a) + side * (5 + 3 * rng.random()) / rs[i])
                p.add("marks", f'<circle cx="{x:.1f}" cy="{y:.1f}" r=".9" fill="#4f8a4a" style="pointer-events:none"/>')

    # ---- the forest round it all: toward the Tower in the west, and over the crest
    wood = canvas.difference(bowl.buffer(10)).difference(field.buffer(12)).difference(road.buffer(26)).difference(floor.buffer(6)).difference(moot.buffer(10))
    p.forest(wood, 2300, r=(12, 22))

    # ---- labels
    def lab(r, deg, text, size=15, cls="tp-lbl", pid=None, along=True, **kw):
        x, y = at(r, math.radians(deg))
        p.label(x, y, text, size, cls, rotate=upright(deg + 90) if along else 0, pid=pid, **kw)
    lab(560, -24, "THE HUNDRED TERRACES", 26, "tp-area", "hundred-terraces", spacing=8)
    lab(600, 17, "a hundred and sixty-two of them", 14, "tp-sub", "hundred-terraces")
    lab(crest_r + 24, great, "THE MOOT TERRACE", 13, "tp-area", "moot-terrace", spacing=2)
    lab(r0 + 46, 48, "the Old Walls", 13, "tp-sub", "old-walls")
    gx, gy = at(380, math.radians(great + 2.6))
    p.label(gx, gy, "the Great Stair", 13, "tp-sub", rotate=great, pid="great-stair")
    lx, ly = at(250, math.radians(-42))
    p.label(lx, ly, "glyph-lamps on every ninth terrace", 11, "tp-sub", rotate=upright(-42 + 90), pid="lamp-strings")
    cx_, cy_ = at(520, math.radians(30))
    p.label(cx_, cy_, "chultun", 11, "tp-sub", pid="chultuns")
    p.label(S[0] + 10, S[1] + 36, "the Keeper's Stair", 14, "tp-lbl", pid="keepers-stair")
    dx_, dy_ = dayhouse.centroid.x, dayhouse.centroid.y
    p.label(dx_, dy_ - 22, "the Daykeepers' House", 13, "tp-sub", pid="daykeepers-house")
    fq = root_line.interpolate(.62, normalized=True)
    p.label(fq.x + 78, fq.y, "THE PLANTING FIELD", 17, "tp-area", rotate=78, pid="planting-field", spacing=4)
    rq0, rq1 = root_line.interpolate(.36, normalized=True), root_line.interpolate(.40, normalized=True)
    p.label(rq0.x + 26, rq0.y, "the Great Root", 13, "tp-sub", rotate=upright(math.degrees(math.atan2(rq1.y - rq0.y, rq1.x - rq0.x))), pid="great-root")
    un = np.array([math.cos(math.radians(north)), math.sin(math.radians(north))])
    nq = R0 + un * 380 + np.array([un[1], -un[0]]) * 24   # beside the road, on the forest side
    p.label(nq[0], nq[1], "THE ROOT-ROAD · to Wayebiel and the Deep Count, a day", 13, "tp-road", rotate=upright(north), pid="root-road", spacing=1)
    us = np.array([math.cos(math.radians(south)), math.sin(math.radians(south))])
    sq = R0 + us * 430 + np.array([-us[1], us[0]]) * 42   # on the forest side
    p.label(sq[0], sq[1], "THE ROOT-ROAD · to K'anvael, a day · Weneleth, three", 13, "tp-road", rotate=upright(south), pid="root-road", spacing=1)
    p.label(150, 980, "the forest · toward the Tower", 18, "tp-sub")
    p.label(1700, 120, "over the crest", 15, "tp-sub")

    p.mpu = 1.0
    cartouche(p, 1560, 1218, "Kolvael", "the Hundred Terraces · Iximvael, Thal'vireth", w=400)
    compass(p, 330, 110)
    scale_bar(p, 70, 1262)

    # ---- the key (lore-book 26, and what the plan adds)
    p.place("hundred-terraces", "The Hundred Terraces", "Where the Cradle writes its names",
            "A great bowl of hillside north of the White Road, cut from the valley floor to the crest into steps: the largest and oldest field-works in the realm. There are in fact a hundred and sixty-two of them; the name was given when there were a hundred, before the Compact. Each terrace is held by one family line, and each line's house stands at the head of its own stair, so the town of nine thousand lives on the terraces themselves. Seen from the Root-Road, the fields move: green, then gold, then bare and sown, terrace by terrace, in the course of a few weeks.", BOOK)
    p.place("old-walls", "The Old Walls", "A hand's span below the last name",
            "The retaining walls of the lowest terraces, the first cut. On each wall, at the head of the stair that climbs past it, the line cuts the name of each new head of the household, row on row. The oldest walls are cut so deep that the stone has been replaced twice, the old stones built into the base of the new. When a farmer has worked their full sixty lived years and been planted, their cord of green Count-beads is hung on a peg beside their name until it rots and the beads fall into the terrace.", BOOK)
    p.place("keepers-stair", "The Keeper's Stair", "Where the Cradle stops, for an hour, to be heard",
            "Nine steps of pale stone at the foot of the Hundred Terraces, warded like the White Road, climbing to an open platform under a roof of grown wood: the only ground in the Cradle that keeps true time. The Ah K'in of the Cradle hears petitions here one sun in each season. A petitioner on the Stair is heard at true time; the queue at its foot waits at the Cradle's pace, so households send a child of ten or so to hold their place, and the child is often old enough to speak for the household by the time it is called.", BOOK)
    p.place("great-stair", "The Great Stair", "From the Keeper to the moot",
            "The broadest of the stairs that climb the bowl, straight up from the Keeper's Stair to the uppermost terrace. Every terrace it passes has its oldest name-cuttings beside it, and on the long nights it is the first stair to be lit.")
    p.place("moot-terrace", "The Moot Terrace", "Very hard to stop",
            "The uppermost terrace, widened at the head of the Great Stair into the town's square. The moot of the Hundred Terraces meets here, every line's head together, every sun: it settles boundaries, water-rights, cistern-shares and marriages, talks for most of the sun, and sends up to the Keeper only what it cannot settle. It is where the Full Measure is argued loudest.", BOOK)
    p.place("lamp-strings", "The Lamp-Strings", "The festival that never ends",
            "The sun crosses the Cradle once in six of its own days, so half of every sun is three sleeps of dark, and the Cradle works it by lamplight. The terraces are strung with the Quickening Wards' glyph-lamps from the valley floor to the crest, so that from the Road the hillside seems to be holding a festival that never ends.", BOOK)
    p.place("chultuns", "The Chultun", "Wealth reckoned in terraces, then in cisterns",
            "Bottle-shaped cisterns cut into the rock beneath the terraces, filled through the Long Wet and drawn down a jar at a time through the Long Dry, each of which lasts three of the Cradle's years. A family that has lost its cistern has lost its terraces too, about two years later.", BOOK)
    p.place("planting-field", "The Planting Field", "Where the Cradle feeds the tree",
            "The open soil either side of the great root, the Cradle's root-bed and the busiest in the realm. The dead are laid here without a stone or a name and left for the tree to take, nearly every sleep. Plantings are short and cheerful: the mourners come in their best clothes with marigolds and stay to eat. The first ear cut from every terrace at every harvest is planted here too, so that the tree eats first. The Field is very green, and orange with marigolds.", BOOK)
    p.place("great-root", "The Great Root", "As thick as a house is tall",
            "A surface root of Ix'kaanil that comes up out of the hillside below the Hundred Terraces and runs south along the valley floor for the better part of a day's walk, going down again at last beside K'anvael. Children play on it all through the long day, and are not stopped.", BOOK)
    p.place("daykeepers-house", "The Daykeepers' House", "Ledgers, harvests and names",
            "The hall by the Root-Road where the Daykeepers of the Hundred Terraces keep their Ledgers, witness marriages and plantings, and give the town's children their day-names at dawn: every child born in the same sun gets the same one, named all together.")
    p.place("root-road", "The Root-Road", "Round the Tower, district to district",
            "The road that circles the Tower and links the districts through Count-gates. Here it comes down from Wayebiel and the Deep Count, a day north, past the foot of the Hundred Terraces, and runs on south past the Planting Field to K'anvael and, three days off, Weneleth on the White Road. The Cradle's tithe-carts go up it.", BOOK)
    return p
