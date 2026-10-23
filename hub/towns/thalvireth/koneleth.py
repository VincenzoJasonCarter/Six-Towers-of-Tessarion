"""Koneleth, the Exchange Houses: the town at the White Road's midpoint, where coin becomes time (lore-book 18)."""
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity

from plans import (Plan, PALETTES, INK, GROWN, MARK, ROAD, WHITE_ROAD,
                   path_d, poly_d, smooth, wiggle, compass, scale_bar, cartouche, map_near)

TOWN = "Koneleth"
EPITHET = "the Exchange Houses"
BOOK = "Of The White Road"


def draw():
    """Koneleth (lore-book 18): a town of about seven thousand on the fifth day out of
    Nabireth, built round the paved square of the Exchange Houses, with the fifth Stone
    in the middle of it. The White Road runs through the square dead straight, the way
    it runs on the map, and the Strand to Ookeleth peels off it east of town on the
    map's line. Halls stand on three sides of the square; the fourth, the seaward side,
    is open, so a client coming up the Road sees all of them at once."""
    W, H = 1800, 1200
    p = Plan("koneleth", W, H, seed=1805)
    rng = p.rng

    # ---- the map: the White Road's line, and the Strand that leaves it for Ookeleth
    routes = map_near(TOWN, 6)
    road = next(pts for name, _, pts in routes if name == "The White Road")
    ang = math.atan2(road[-1][1] - road[0][1], road[-1][0] - road[0][0])
    if math.cos(ang) < 0: ang += math.pi                 # reckoned eastward, toward the sea
    strand = min((pts for _, g, pts in routes if g == "trails"), key=lambda pts: min(math.hypot(*q) for q in pts))
    k0 = min(range(len(strand)), key=lambda k: math.hypot(*strand[k]))
    q0, q1 = strand[k0], strand[k0 + 1] if k0 + 1 < len(strand) else strand[k0 - 1]
    peel = math.atan2(q1[1] - q0[1], q1[0] - q0[0]) - ang  # its angle off the Road (south side)

    # plan positions are (a, b) from the fifth Stone: a along the Road (east), b across it (south)
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    S = (900.0, 600.0)
    deg = math.degrees(ang)
    pt = lambda a, b: (S[0] + a * ux + b * nx, S[1] + a * uy + b * ny)
    line = lambda pts: LineString([pt(*q) for q in pts])
    poly = lambda pts: Polygon([pt(*q) for q in pts])
    def rect(a, b, w, h, turn=0):
        return affinity.translate(affinity.rotate(box(-w / 2, -h / 2, w / 2, h / 2), deg + turn, origin=(0, 0)), *pt(a, b))
    def oval(a0, rx, ry, wob, n=120):
        ph = rng.uniform(0, 6.3, 2)
        return poly([(a0 + rx * r * math.cos(t), ry * r * math.sin(t)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)
                     for r in [1 + wob * math.sin(3 * t + ph[0]) + wob * .5 * math.sin(7 * t + ph[1])]])

    canvas = box(-20, -20, W + 20, H + 20)
    town = oval(-20, 560, 330, .07)
    clearing = oval(0, 790, 470, .09)
    p.add("ground", f'<path d="{poly_d(canvas)}" fill="url(#grass)"/>')

    # ---- the roads
    white_road = line([(-1200, 0), (1200, 0)])
    sq_a0, sq_a1, sq_b = -114, 122, 80                    # the square: west edge, open east edge, half-width
    road_w, road_e = line([(-1200, 0), (sq_a0, 0)]), line([(sq_a1, 0), (1200, 0)])
    t = np.linspace(0, 1, 30)
    curve = [(470 + 70 * s, 10 + 4 * s * s) for s in t[:10]]  # it leaves the stone gently, then holds its line
    a1, b1 = curve[-1]
    strand_line = smooth(LineString([pt(*q) for q in curve] + [pt(a1 + d * math.cos(peel), b1 + d * math.sin(peel)) for d in (120, 300, 520)]), 2)

    # ---- landmarks first, so the streets and houses keep clear of them
    square = poly([(sq_a0, -sq_b), (sq_a1, -sq_b), (sq_a1, sq_b), (sq_a0, sq_b)])
    halls = [rect(-56, -104, 96, 44), rect(56, -104, 96, 44), rect(-56, 104, 96, 44), rect(56, 104, 96, 44),
             rect(-136, -50, 44, 62), rect(-136, 50, 44, 62)]
    stone = rect(0, 0, 11, 11)
    roll_house = rect(-30, -228, 78, 40)
    tenth_part = rect(176, 50, 36, 26)
    balam_tower, balam_yard = rect(300, -46, 26, 26), rect(300, -92, 58, 46)
    consignment = rect(390, 128, 118, 62)
    carters = rect(-440, -74, 112, 56)
    gate_at = (a1 + 70 * math.cos(peel), b1 + 70 * math.sin(peel))
    marks = [square, *halls, roll_house, tenth_part, balam_tower, balam_yard, consignment, carters]
    keep_clear = unary_union([m.buffer(7) for m in marks])

    # The town's lanes: back streets that run with the Road, a street of halls behind each row
    # of Exchange Houses, cross-lanes between, and alleys. They wander; only the Road is straight.
    backs = []
    for b0 in (-176, -286, 176, 284):
        ph = rng.uniform(0, 6.3)
        backs.append(wiggle(line([(a, b0 + 10 * math.sin(a / 160 + ph)) for a in np.linspace(-680, 680, 40)]), 6, 1.6, rng))
    cross = []
    for a0 in np.arange(-490, 520, 108):
        if -170 < a0 < 150: continue                      # the square and its halls
        a0 += rng.uniform(-22, 22)
        lean = rng.uniform(-40, 40)
        cross.append(wiggle(line([(a0 - lean, -380), (a0 + lean * .3, 0), (a0 + lean, 380)]), rng.uniform(5, 9), 2.2, rng))
    for a0, b0, b1_ in ((-20, -150, -176), (60, 150, 176), (-200, -20, -176), (-200, 20, 176)):
        cross.append(line([(a0, b0), (a0 + rng.uniform(-8, 8), b1_)]))  # from the square's corners and halls to the back streets
    alleys = []
    for inner, outer in ((backs[0], backs[1]), (backs[2], backs[3])):
        s = rng.uniform(20, 80)
        while s < inner.length:
            a_ = inner.interpolate(s)
            b_ = outer.interpolate(outer.project(a_) + rng.uniform(-30, 30))
            if rng.random() < .6:
                alleys.append(wiggle(LineString([(a_.x, a_.y), (b_.x, b_.y)]), 4, 3, rng))
            s += rng.uniform(70, 140)
    lanes, alley_ids = [], set()
    for k, ln in enumerate(backs + cross + alleys):
        g = ln.intersection(town.buffer(-10)).difference(keep_clear).difference(white_road.buffer(16))
        for part in getattr(g, "geoms", [g]):
            if part.geom_type == "LineString" and part.length > 30:
                if k >= len(backs) + len(cross): alley_ids.add(len(lanes))
                lanes.append(part)

    for m in marks:
        p.block(m.buffer(4))
    p.block(strand_line.buffer(5))
    p.block(Point(*pt(*gate_at)).buffer(16))

    # ---- gardens in the clearing, then the forest round it
    gardens = clearing.difference(town.buffer(30)).difference(white_road.buffer(26)).difference(strand_line.buffer(18))
    tints = ("#e3d6b0", "#dccd9f", "#e6dbb8", "#d5c79a", "#e0d2a6", "#d9d0a2")
    taken = Polygon()
    for _ in range(260):
        fx, fy = rng.uniform(0, W), rng.uniform(0, H)
        nx_, ny_ = int(rng.integers(2, 5)), int(rng.integers(1, 3))
        sw, sh = rng.uniform(18, 28), rng.uniform(40, 75)
        strips = [affinity.rotate(box(fx + (i - nx_ / 2) * sw, fy + (j - ny_ / 2) * sh, fx + (i - nx_ / 2 + 1) * sw - 3, fy + (j - ny_ / 2 + 1) * sh - 3),
                                  deg + rng.choice([0, 90]) + rng.uniform(-12, 12), origin=(fx, fy)) for i in range(nx_) for j in range(ny_)]
        whole = unary_union(strips)
        if whole.intersects(taken) or not gardens.contains(whole.centroid):
            continue
        taken = taken.union(whole.buffer(10))
        for s_ in strips:
            g = s_.intersection(gardens)
            if g.area > 150:
                p.add("ground", f'<path d="{poly_d(g)}" fill="{tints[int(rng.integers(len(tints)))]}" stroke="#a89068" stroke-width=".7" opacity=".9"/>')
                p.block(g)

    p.street(road_w, 20, WHITE_ROAD)
    p.street(road_e, 20, WHITE_ROAD)
    p.street(strand_line, 7)
    for k, ln in enumerate(lanes):
        p.street(ln, 6.5 if k in alley_ids else 8, ROAD)
    # the square, paved in the Road's stone, with the Road itself set into it
    p.add("streets", f'<path d="{poly_d(square)}" fill="{ROAD}" stroke="{INK}" stroke-width="1.4" data-place="exchange-square" class="place"/>')
    p.street(line([(sq_a0, 0), (sq_a1, 0)]), 20, WHITE_ROAD, edge=False)

    wood = canvas.difference(clearing).difference(white_road.buffer(16)).difference(strand_line.buffer(10))
    p.forest(wood, 2600, r=(12, 22))

    # ---- landmarks
    for h in halls:
        p.landmark("exchange-houses", h)
    ax, ay = pt(-84, -112)
    p.add("marks", f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="4.5" fill="#6e3b26" stroke="{INK}" stroke-width="1" data-place="candours-table" class="place"/>')
    sx, sy = pt(0, 0)
    p.add("marks", f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="26" fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="4 3" data-place="fifth-stone" class="place"/>')
    p.landmark("fifth-stone", stone, fill="#f7f3e6")
    p.landmark("roll-house", roll_house)
    p.landmark("tenth-part", tenth_part)
    p.add("marks", f'<path d="{poly_d(balam_yard)}" fill="#e6d6b4" stroke="{INK}" stroke-width="1.4" stroke-dasharray="3 3" data-place="balam-post" class="place"/>')
    p.landmark("balam-post", balam_tower, fill="#7d4a2c")
    for m_, sheds in ((consignment, 3), (carters, 2)):
        pid = "consignment-yards" if m_ is consignment else "carters-yards"
        p.add("marks", f'<path d="{poly_d(m_)}" fill="#e6d6b4" stroke="{INK}" stroke-width="1.4" stroke-dasharray="4 3" data-place="{pid}" class="place"/>')
        c = m_.centroid
        for k in range(sheds):
            off = ((k + .5) / sheds - .5) * (118 if m_ is consignment else 112) * .78
            a_, b_ = (390, 128) if m_ is consignment else (-440, -74)
            p.landmark(pid, rect(a_ + off, b_, 26 if m_ is consignment else 34, 36), fill=GROWN if m_ is consignment else MARK)
    # the Count-gate at the Strand's head: an arch of grown wood, and the Daykeeper's post beside it
    gx, gy = gate_at
    for side in (-1, 1):
        p.landmark("strand-gate", rect(gx, gy + side * 8, 5, 5, peel * 180 / math.pi), fill="#6d5a40")
    arch = line([(gx - 3 * math.sin(peel), gy - 10), (gx + 3 * math.sin(peel), gy + 10)])
    p.add("marks", f'<path d="{path_d(arch.coords)}" stroke="{INK}" stroke-width="2.5" fill="none" data-place="strand-gate" class="place"/>')
    p.landmark("strand-gate", rect(gx + 6, gy + 26, 16, 12, peel * 180 / math.pi), fill=MARK)

    # ---- houses: grown-wood halls along the Road, then every lane, then the backs of the blocks.
    # Crownweave factors keep their houses north-east of the square, the tiefling brokers south-west.
    factors = poly([(150, -420), (600, -420), (600, -120), (150, -120)])
    brokers = poly([(-600, 110), (-160, 110), (-160, 420), (-600, 420)])
    def palette_at(x, y):
        q = Point(x, y)
        return PALETTES["human"] if factors.contains(q) else PALETTES["tiefling"] if brokers.contains(q) else PALETTES["elf"]
    for ln in (line([(-700, 0), (sq_a0 - 46, 0)]), line([(sq_a1, 0), (700, 0)])):
        p.houses_along(ln, town, depth=(14, 22), width=(12, 20), fill=GROWN, street_w=20)
    for ln in sorted(lanes, key=lambda ln: ln.centroid.distance(Point(*S))):
        p.palette = palette_at(ln.centroid.x, ln.centroid.y)
        p.houses_along(ln, town)
    near = lambda x, y: max(.2, 1 - .75 * math.hypot(((x - S[0]) * ux + (y - S[1]) * uy) / 560, ((x - S[0]) * nx + (y - S[1]) * ny) / 330))
    everyone = lanes + [white_road]
    for region, pal, n in ((town.intersection(factors), "human", 90), (town.intersection(brokers), "tiefling", 110),
                           (town.difference(factors).difference(brokers), "elf", 520)):
        p.palette = PALETTES[pal]
        p.infill(region, n, everyone, near)
    p.palette = PALETTES["elf"]
    ribbon = clearing.difference(town).intersection(white_road.buffer(45))  # inns along the Road out of town
    for ln in (road_w, road_e):
        p.houses_along(ln, ribbon, depth=(10, 16), width=(9, 14), gap=(8, 26), street_w=20)

    p.trees(gardens, 260, r=(5, 10))
    p.trees(town, 70, r=(4, 7), colour="#a9b886")

    # ---- labels
    def lab(a, b, text, size=15, cls="tp-lbl", pid=None, turn=0, **kw):
        x, y = pt(a, b)
        p.label(x, y, text, size, cls, rotate=deg + turn, pid=pid, **kw)
    lab(10, -32, "THE EXCHANGE SQUARE", 15, "tp-area", "exchange-square", spacing=3)
    lab(0, 36, "the fifth Stone", 14, "tp-sub", "fifth-stone")
    lab(0, -133, "EXCHANGE HOUSES", 13, "tp-lbl", "exchange-houses", spacing=2)
    lab(0, 140, "EXCHANGE HOUSES", 13, "tp-lbl", "exchange-houses", spacing=2)
    lab(-170, 0, "EXCHANGE HOUSES", 12, "tp-lbl", "exchange-houses", turn=-90, spacing=2)
    lab(-84, -62, "Candour's table", 11, "tp-sub", "candours-table")
    lab(-30, -255, "the Roll-House", 15, pid="roll-house")
    lab(176, 80, "The Tenth Part", 14, pid="tenth-part")
    lab(300, -125, "Balam Post", 14, pid="balam-post")
    lab(390, 178, "the Consignment Yards", 14, pid="consignment-yards")
    lab(-440, -112, "Carters' Yards", 14, pid="carters-yards")
    lab(gate_at[0] + 10, gate_at[1] + 52, "the Strand-gate", 13, pid="strand-gate", turn=peel * 180 / math.pi)
    lab(380, -230, "FACTORS' ROW", 17, "tp-area", "factors-row", spacing=4)
    lab(-390, 235, "THE BROKERS' LANES", 17, "tp-area", "brokers-lanes", spacing=4)
    lab(190, 166, "ADVOCATES' WALK", 12, "tp-road", "advocates-walk", spacing=3)
    lab(-330, -236, "THE TALLY LANES", 17, "tp-area", "tally-lanes", spacing=4)
    lab(-720, -16, "THE WHITE ROAD", 15, "tp-road", "white-road", spacing=4)
    lab(-720, 34, "to Chi'eleth · five days to the Canopy Steps", 13, "tp-sub")
    lab(690, -16, "to Kaajeleth · five days to Nabireth", 13, "tp-sub")
    x, y = pt(a1 + 330 * math.cos(peel), b1 + 330 * math.sin(peel) + 20)
    p.label(x, y, "the Strand to Ookeleth", 14, "tp-sub", rotate=deg + peel * 180 / math.pi, pid="ookeleth-strand")
    p.label(200, 130, "the forest", 18, "tp-sub")
    p.label(1500, 1010, "the forest", 18, "tp-sub")

    cartouche(p, 1560, 1110, "Koneleth", "the Exchange Houses · Sakbeleth, Thal'vireth", w=380)
    compass(p, 1720, 140)
    scale_bar(p, 70, 1150)

    # ---- the key (lore-book 18, and what the plan adds)
    p.place("exchange-square", "The Exchange Square", "Where the forest opens",
            "Halfway up the Road, on the fifth day out of Nabireth, the forest opens around a broad square paved in the Road's own pale stone, with the White Road set into the middle of it. The Exchange Houses stand on three sides. The fourth, the seaward side, is open, so a client coming up the Road sees every hall at once, and every hall sees them.", BOOK)
    p.place("fifth-stone", "The Fifth Stone", "Halfway",
            "The fifth of the Ten Stones, a squared pillar of the Road's pale rock twice a tall man's height, standing in the middle of the square: its number on the seaward face, that morning's sunrise hour on the landward. By custom, a contract witnessed at the foot of a Stone cannot later be disputed on the grounds that either party had lost track of the time. Elsewhere on the Road a broker walks a doubtful client out to the nearest Stone to sign. In Koneleth they only have to cross the square, and the paving round the Stone's foot is seldom empty.", BOOK)
    p.place("exchange-houses", "The Exchange Houses", "Where outside coin becomes inside time",
            "Six long halls of grown wood on pale stone footings, each the seat of a trading house licensed by the Curia, open from the first true hour to the last. At the front, brokers change Crownsblood and foreign coin for jade-tally at the Curia's rate, less the tenth. At the back, behind carved screens, the contract-rooms write chronoflow (ageing, keeping and waiting), a Daykeeper at every table. The largest Crownweave houses keep rooms of their own behind the screens, which the Road-elves call, without much affection, the cartel benches.", BOOK)
    p.place("candours-table", "Candour's Table", "What will the Cradle say about it afterwards?",
            "The busiest table in Koneleth, in the same hall for twenty-two outside years. Candour, a tiefling, will tell any client unprompted what each contract will cost them in lived years, in jade-tally, and in what the Cradle will say about it afterwards. Candour keeps no permanent loyalties and many permanent accounts. A good deal of what the cartel benches know came from this table, and so did a good deal of what the Curia knows about the cartel benches.", BOOK)
    p.place("roll-house", "The Roll-House", "Every contract, on file",
            "The Daykeepers' hall behind the northern Exchange Houses. Every chronoflow contract written in Koneleth is copied here and the copy kept, with the Daykeepers of the Exchange who witnessed it. Among the files is the contract, still on file, for keeping an entire wedding cake. The Daykeepers lodge upstairs.")
    p.place("tenth-part", "The Tenth Part", "Named for the fee, and full of people complaining about it",
            "An inn on the open side of the square, where Crownweave factors drink after a day on the benches and complain about the tenth. Its keeper put the name over the door to save them the trouble of saying it.")
    p.place("balam-post", "The Balam Post", "More money than anywhere else on the Road, and a guard to match",
            "A tower of pale stone and a walled yard east of the square, where the Balam detachment that patrols this stretch of the Road keeps its watch. Weapons may be worn openly on the Road but not drawn on the stone, except by the Balam, and in Koneleth the Balam stand where everyone can see them.", BOOK)
    p.place("consignment-yards", "The Consignment Yards", "Cargo waiting to grow old, or not to",
            "Walled yards and sheds south-east of the square, near the head of the Ookeleth Strand. Cargo consigned for chronoflow waits here once its contract is sealed: wine and timber for ageing in the Cradle or the Wards, seed and medicines for keeping in the slow districts. Each crate gets the Roll-House's number chalked on it before the carters take it down a Strand or on up the Road.")
    p.place("carters-yards", "The Carters' Yards", "Paid by the Stone",
            "Ox-pens, cart-sheds and a hiring hall at the town's west end. The Road's carters are paid by the Stone, and the fifth is the halfway mark: most carters change loads here, and a good many change oxen.", BOOK)
    p.place("strand-gate", "The Ookeleth Strand-gate", "A step off the stone is a step into the Cradle's time",
            "A narrow arch of grown wood where the Strand to Ookeleth leaves the Road east of town, with a Daykeeper's post beside it. Every Ledger that goes through it is stamped. Beyond the arch the Strand runs in the Green Cradle's time, where a season passes in weeks.", BOOK)
    p.place("ookeleth-strand", "The Strand to Ookeleth", "Why the Road looks frayed from above",
            "A foot-trail that leaves the White Road at a shallow angle and runs beside it for a while before it bends away south-east to Ookeleth, where the Granary Road and three Strands meet.", BOOK)
    p.place("factors-row", "Factors' Row", "Crownweave, behind the screens and at home",
            "Streets north-east of the square where the permanent factors of the large Crownweave trading houses keep their houses and their clerks. Their houses have Crownweave doors and Crownweave shutters, and their windows face the square.")
    p.place("brokers-lanes", "The Brokers' Lanes", "Very good at it",
            "The lanes south-west of the square where the tiefling brokers and contract-scribes of the Exchange Houses live. They work the halls for the same reason they work Emberweave's: they are very good at it, and the elves would rather not be.", BOOK)
    p.place("advocates-walk", "Advocates' Walk", "Most of the Road's lawyers",
            "The back street behind the southern Exchange Houses, where most of the Road's lawyers keep their offices. Their business is contracts that went wrong, inheritances reckoned in lived years, and the petitions that larger contracts need before they can go up the Road to the Canopy Court for assent.", BOOK)
    p.place("tally-lanes", "The Tally Lanes", "Where the Road-elves live",
            "The older streets north-west of the square, home to the Road-elves who keep Koneleth running: hall-clerks, tally-counters, innkeepers and carters, all living their whole lives at true time, their Count-bead cords long and almost entirely white.", BOOK)
    p.place("white-road", "The White Road", "Five days to the sea, five to the Steps",
            "A raised causeway of pale, close-fitted stone, broad enough for two carts to pass, held at true time by the wards in its stones. Koneleth stands at its midpoint, on the fifth Stone. Chi'eleth and its old strand-gate lie a day west, toward the Canopy Steps.", BOOK)
    return p
