"""Nabireth, the Landing: the harbour at the head of the Quiet Gulf, where the White Road begins."""
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity

from plans import (Plan, INK, PAPER, WATER, SHALLOW, GROWN, MARK, ROAD, WHITE_ROAD,
                   path_d, poly_d, smooth, wiggle, compass, scale_bar, cartouche)

TOWN = "Nabireth"
EPITHET = "the Landing"


def draw():
    """Nabireth, the Landing (lore-book 18): the harbour at the head of the Quiet Gulf,
    where the White Road begins. The sea is east, the Road leaves west. The Counting
    Pier lies on the Road's own line, so the Road begins, quite literally, at the end
    of the pier."""
    W, H = 1800, 1200
    p = Plan("nabireth", W, H, seed=1818)
    rng = p.rng

    # the Road's direction (Ix'kaanil to Nabireth on the map, reversed): west, a little north
    ux, uy = 0.9957, 0.0932
    gate = (350.0, 560.0)
    on_line = lambda x: gate[1] + (x - gate[0]) * uy / ux

    def shore_x(y):
        bay = -115 * math.exp(-((y - 640) / 240) ** 2)
        north = 95 / (1 + math.exp((y - 300) / 55))
        mouth = -38 * math.exp(-((y - 965) / 28) ** 2)
        noise = 9 * math.sin(y / 37) + 6 * math.sin(y / 13 + 1.3) + 4 * math.sin(y / 7.1)
        return 1250 + bay + north + mouth + noise
    ys = np.arange(-20, H + 21, 6)
    land = Polygon([(-20, -20)] + [(shore_x(y), y) for y in ys] + [(-20, H + 20)])
    sea = box(-20, -20, W + 20, H + 20).difference(land)
    shallows = sea.intersection(land.buffer(85)).difference(land)

    # the stream at Ja'eleth, and the ground it runs through
    stream_line = smooth(LineString([(-20, 1135), (200, 1108), (380, 1140), (560, 1092), (760, 1112), (920, 1043), (1060, 992), (1170, 966), (shore_x(965) + 4, 965)]))
    stream = stream_line.buffer(7, cap_style=2).union(LineString(list(stream_line.coords)[-3:]).buffer(13, cap_style=2))
    land_dry = land.difference(stream)

    p.add("ground", f'<path d="{poly_d(land)}" fill="url(#grass)"/>')
    p.add("water", f'<path d="{poly_d(sea)}" fill="{WATER}"/>')
    p.add("water", f'<path d="{poly_d(shallows)}" fill="{SHALLOW}"/>')
    p.add("water", f'<path d="{poly_d(sea.difference(land.buffer(85)))}" fill="url(#ripple)"/>')
    p.add("water", f'<path d="{path_d([(shore_x(y), y) for y in ys])}" fill="none" stroke="{INK}" stroke-width="2.2"/>')
    p.add("water", f'<path d="{poly_d(stream)}" fill="{WATER}" stroke="{INK}" stroke-width="1"/>')
    p.block(sea.buffer(-2)); p.block(stream.buffer(3))

    # the rise the town climbs to the gate-tower: a few hand-drawn contours
    for k, rad in enumerate((110, 190, 280, 380)):
        pts = []
        for a in np.linspace(0, 2 * math.pi, 90):
            rr = rad * (1 + .08 * math.sin(3 * a + k) + .05 * math.sin(7 * a))
            pts.append((gate[0] - 20 + rr * 1.25 * math.cos(a), gate[1] + 10 + rr * .9 * math.sin(a)))
        ring = Polygon(pts).exterior.intersection(land_dry)
        for g in getattr(ring, "geoms", [ring]):
            if g.length > 20:
                p.add("contours", f'<path d="{path_d(g.coords)}" fill="none" stroke="#9a7b52" stroke-width="1" stroke-dasharray="7 5" opacity=".7"/>')

    # ---- the roads: the White Road and the Landing Way are one line; the Quays follow the shore
    white_road = LineString([(-20, on_line(-20)), gate])
    landing_way = LineString([gate, (shore_x(on_line(1130)) - 6, on_line(1130))])
    pier_end_x = shore_x(on_line(1130)) + 330
    counting_pier = LineString([(shore_x(on_line(1130)) - 6, on_line(1130)), (pier_end_x, on_line(pier_end_x))])
    quays = LineString([(shore_x(y) - 30, y) for y in np.arange(240, 945, 15)])
    granary = wiggle(LineString([(-20, 1062), (95, 940), (170, 765), (212, 625), (240, on_line(240))]), 6, 2.2, rng)
    jaeleth_lane = wiggle(LineString([(shore_x(930) - 30, 930), (shore_x(970) - 60, 975), (1150, 1035), (1120, 1150)]), 5, 3, rng)

    # landmarks first, so the streets and houses keep clear of them
    def rect(cx, cy, w, h, ang=math.degrees(math.atan2(uy, ux))):
        return affinity.translate(affinity.rotate(box(-w / 2, -h / 2, w / 2, h / 2), ang, origin=(0, 0)), cx, cy)
    hall_x = shore_x(on_line(1130)) - 48
    counting_hall = rect(hall_x, on_line(hall_x), 62, 44)
    customs = rect(hall_x - 10, on_line(hall_x) - 70, 64, 40)
    yard = rect(hall_x - 2, on_line(hall_x) - 128, 78, 56)
    shed = rect(hall_x + 22, on_line(hall_x) - 140, 22, 16)
    lt_y = on_line(hall_x) + 78
    long_tide = rect(shore_x(lt_y) - 58, lt_y, 30, 24, 0)
    tower = rect(gate[0], gate[1], 30, 30)
    balam_yard = rect(gate[0] - 46, gate[1] + 2, 44, 52)
    bearers = rect(gate[0] + 120, on_line(gate[0] + 120) + 52, 48, 30)
    warehouses = [rect(shore_x(y) - 62, y, 40, 26, 90 - 4) for y in (338, 382, 426, 470)]
    boatyard = rect(shore_x(1015) - 20, 1015, 46, 30, -20)
    water_stair = rect(shore_x(990) - 6, 990, 14, 26, 0)
    marks = [counting_hall, customs, yard, shed, long_tide, tower, balam_yard, bearers, *warehouses, boatyard, water_stair]
    keep_clear = unary_union([m.buffer(7) for m in marks])

    # The town climbs from the harbour to the gate: streets that follow the rise's contours,
    # streets that climb it from the quays, and alleys between. Nothing in it is straight
    # except the Landing Way, which is the Road.
    rise = (gate[0] - 40, gate[1] + 10)
    def arc(radius, a0, a1):
        pts = [(rise[0] + radius * 1.12 * math.cos(math.radians(a)), rise[1] + radius * .92 * math.sin(math.radians(a))) for a in np.linspace(a0, a1, 60)]
        return wiggle(LineString(pts), rng.uniform(8, 16), rng.uniform(1.2, 2.4), rng)
    contours = [arc(r, -62, 58) for r in (300, 410, 520, 630, 735)]
    climbs = []
    for y0, bend in ((330, -60), (418, 40), (515, -30), (745, 35), (828, -45), (905, 30)):
        start = (shore_x(y0) - 32, y0)
        ang = math.atan2(start[1] - rise[1], start[0] - rise[0])
        end = (rise[0] + 255 * math.cos(ang), rise[1] + 255 * math.sin(ang))
        mid = ((start[0] + end[0]) / 2 - bend * math.sin(ang), (start[1] + end[1]) / 2 + bend * math.cos(ang))
        climbs.append(wiggle(LineString([start, mid, end]), rng.uniform(6, 12), rng.uniform(2, 3.5), rng))
    alleys = []
    for inner, outer in zip(contours, contours[1:]):
        s = rng.uniform(20, 90)
        while s < inner.length:
            a = inner.interpolate(s)
            b = outer.interpolate(outer.project(a) + rng.uniform(-25, 25))
            if rng.random() < .7 and a.distance(b) < 170:
                alleys.append(wiggle(LineString([(a.x, a.y), (b.x, b.y)]), rng.uniform(3, 7), 3, rng))
            s += rng.uniform(80, 150)

    region = land_dry.intersection(box(gate[0] - 20, 255, W, 955))
    lanes, alley_ids = [], set()
    for k, ln in enumerate(contours + climbs + alleys):
        g = ln.intersection(region.buffer(-12)).difference(keep_clear)
        for part in getattr(g, "geoms", [g]):
            if part.geom_type == "LineString" and part.length > 30:
                if k >= len(contours) + len(climbs): alley_ids.add(len(lanes))
                lanes.append(part)
    town = land_dry.intersection(unary_union([ln.buffer(48) for ln in lanes + [landing_way, quays]])).intersection(region)

    for m in marks:
        p.block(m.buffer(4))
    p.street(white_road, 20, WHITE_ROAD)
    p.street(landing_way, 16, WHITE_ROAD)
    p.street(granary, 10)
    p.street(quays, 11)
    p.street(jaeleth_lane, 7)
    for k, ln in enumerate(lanes):
        p.street(ln, 6.5 if k in alley_ids else 8, ROAD)

    # piers: the Counting Pier on the Road's line, the others square to the shore
    p.add("piers", f'<path d="{path_d(counting_pier.coords)}" stroke="{INK}" stroke-width="19" stroke-linecap="square" fill="none"/>'
                   f'<path d="{path_d(counting_pier.coords)}" stroke="#b49064" stroke-width="15" stroke-linecap="square" fill="none" data-place="counting-pier" class="place"/>')
    for y, length in ((300, 150), (470, 190), (540, 175), (735, 205), (812, 165), (880, 120)):
        x0 = shore_x(y) - 4
        p.add("piers", f'<path d="M{x0:.1f} {y}H{x0 + length:.1f}" stroke="{INK}" stroke-width="11" fill="none"/><path d="M{x0:.1f} {y}H{x0 + length:.1f}" stroke="#bf9d70" stroke-width="7.5" fill="none"/>')
        p.block(LineString([(x0, y), (x0 + length, y)]).buffer(8))
        for k in range(int(length / 50)):  # boats tied up along it
            bx = x0 + 30 + k * 48 + rng.uniform(-6, 6); by = y + (13 if k % 2 else -13)
            p.add("boats", f'<path d="M{bx - 14:.1f} {by}q14 -7 28 0q-14 7 -28 0Z" fill="#8a6a46" stroke="{INK}" stroke-width=".8"/>')
    p.block(counting_pier.buffer(12))
    # ships at anchor in the Gulf (the Long Tide, in the wayeb)
    for k, (sx, sy) in enumerate([(1585, 430), (1655, 520), (1600, 805), (1700, 700), (1560, 935), (1690, 300)]):
        rot = rng.uniform(-30, 30)
        p.add("boats", f'<g transform="translate({sx} {sy}) rotate({rot:.0f})"><path d="M-30 0q30 -14 60 0q-30 14 -60 0Z" fill="#7b5b3a" stroke="{INK}" stroke-width="1"/>'
                       f'<path d="M-4 -3V-34L16 -6Z" fill="{PAPER}" stroke="{INK}" stroke-width=".9"/><path d="M-6 -4V-28L-22 -6Z" fill="{PAPER}" stroke="{INK}" stroke-width=".9"/></g>')

    # landmarks
    p.landmark("counting-hall", counting_hall, extra=' stroke-dasharray="5 3"')
    p.landmark("customs-hall", customs)
    p.add("marks", f'<path d="{poly_d(yard)}" fill="#e6d6b4" stroke="{INK}" stroke-width="1.4" stroke-dasharray="3 3" data-place="keepers-shed" class="place"/>')
    p.landmark("keepers-shed", shed, fill="#6e3b26")
    p.landmark("long-tide", long_tide)
    p.landmark("gate-tower", tower, fill="#7d4a2c")
    p.add("marks", f'<path d="{poly_d(balam_yard)}" fill="#e6d6b4" stroke="{INK}" stroke-width="1.4" stroke-dasharray="3 3"/>')
    p.landmark("bearers-yard", bearers)
    for w in warehouses: p.landmark("warehouse-row", w, fill=GROWN)
    p.landmark("boatyard", boatyard, fill=GROWN)
    p.landmark("water-stair", water_stair, fill="#8a7a5a")

    # houses: grown-wood halls along the Landing Way, the waterfront on piles over the
    # shallows, then every street, then the backs of the blocks, thickest by the harbour
    piles = shallows.buffer(-6).intersection(box(0, 250, W, 930)).difference(keep_clear)
    p.houses_along(landing_way, town, depth=(14, 22), width=(12, 20), fill=GROWN, street_w=16)
    p.houses_along(quays, town.union(piles), depth=(11, 18), width=(9, 16), water_ok=piles, street_w=11)
    for ln in sorted(lanes, key=lambda ln: -ln.centroid.x):
        p.houses_along(ln, town)
    harbour = lambda x, y: .25 + .75 * min(1, max(0, (x - gate[0]) / (shore_x(y) - gate[0])))
    p.infill(town, 900, lanes + [landing_way, quays], harbour)
    jaeleth = land_dry.intersection(Point(1110, 1070).buffer(130))
    p.houses_along(jaeleth_lane, jaeleth, depth=(9, 14), width=(8, 13), gap=(3, 10), street_w=7)
    p.infill(jaeleth.intersection(jaeleth_lane.buffer(60)), 35, [jaeleth_lane], size=(7, 11))
    upper = land_dry.intersection(Point(gate[0] - 120, gate[1]).buffer(200))
    p.houses_along(white_road, upper, depth=(10, 15), width=(8, 13), gap=(8, 22), street_w=20)

    # the forest's edge to the north-west; savanna trees and the odd garden tree elsewhere
    edge = Polygon([(-20, -20), (980, -20), (700, 150), (430, 250), (160, 400), (-20, 470)])
    p.forest(land_dry.intersection(edge).difference(town.buffer(25)), 520)
    p.trees(land_dry.difference(town.buffer(35)).difference(edge), 300, r=(5, 10))
    p.trees(town, 70, r=(4, 7), colour="#a9b886")

    # ---- labels
    p.label(1580, 610, "The Quiet Gulf", 38, "tp-sea", spacing=5)
    p.label(1580, 645, "the Anchorage", 20, "tp-sea", pid="anchorage")
    p.label(pier_end_x - 150, on_line(pier_end_x - 150) - 16, "THE COUNTING PIER", 15, "tp-lbl", rotate=math.degrees(math.atan2(uy, ux)), pid="counting-pier", spacing=2)
    p.label(hall_x - 4, on_line(hall_x) + 40, "Counting Hall", 15, pid="counting-hall", anchor="end")
    p.label(hall_x - 48, on_line(hall_x) - 66, "Customs-Hall", 15, pid="customs-hall", anchor="end")
    p.label(hall_x + 40, on_line(hall_x) - 170, "the Keepers' Shed", 14, pid="keepers-shed")
    p.label(shore_x(lt_y) - 76, lt_y + 6, "The Long Tide", 15, pid="long-tide", anchor="end")
    p.label(gate[0], gate[1] - 30, "Gate-Tower", 16, pid="gate-tower")
    p.label(gate[0] + 120, on_line(gate[0] + 120) + 92, "Bearers' Yard", 15, pid="bearers-yard")
    p.label(shore_x(404) - 90, 404, "WAREHOUSE ROW", 14, "tp-area", anchor="end", pid="warehouse-row", spacing=3)
    p.label(shore_x(1015) - 52, 1062, "Ja'eleth Boatyard", 14, pid="boatyard")
    p.label(shore_x(990) - 30, 952, "Water-Stair", 13, pid="water-stair", anchor="end")
    p.label(1080, 1120, "JA'ELETH", 22, "tp-area", spacing=5, pid="jaeleth")
    p.label(980, 790, "FOREIGN LANES", 18, "tp-area", spacing=4, pid="foreign-lanes")
    p.label(890, 490, "CHANDLERS' ROW", 16, "tp-area", spacing=3, rotate=5, pid="chandlers-row")
    p.label(520, 500, "THE RISE", 18, "tp-area", spacing=5, pid="the-rise")
    p.label(shore_x(860) - 52, 860, "THE QUAYS", 16, "tp-area", rotate=78, spacing=4, pid="quays")
    mid = landing_way.interpolate(.5, normalized=True)
    p.label(mid.x, mid.y + 5, "THE LANDING WAY", 13, "tp-road", rotate=math.degrees(math.atan2(uy, ux)), spacing=3, pid="landing-way")
    p.label(150, on_line(150) + 5, "THE WHITE ROAD", 15, "tp-road", rotate=math.degrees(math.atan2(uy, ux)), spacing=4, pid="white-road")
    p.label(150, on_line(150) + 30, "to Koneleth · ten days to the Canopy Court", 13, "tp-sub", rotate=math.degrees(math.atan2(uy, ux)))
    p.label(120, 905, "the Granary Road", 15, "tp-sub", rotate=-58, pid="granary-road")
    p.label(420, 1162, "Ja'eleth's stream", 14, "tp-sub", rotate=-4)
    p.label(300, 120, "the forest's edge", 18, "tp-sub")

    cartouche(p, 1560, 1110, "Nabireth", "the Landing · Sakbeleth, Thal'vireth")
    compass(p, 1720, 140)
    scale_bar(p, 70, 1150)

    # ---- the key: what each place is (lore-book 18, and what the plan adds)
    book = "Of The White Road"
    p.place("counting-pier", "The Counting Pier", "Where a foreigner's years begin to be counted",
            "A long jetty of jade-wood at the centre of the quays, laid on the White Road's own line, so that the Road begins, quite literally, at the end of the pier. Every ship that docks at Nabireth ties up here first, and every passenger walks its length before setting foot on the Road.", book)
    p.place("counting-hall", "The Counting Hall", "Where Ledgers are opened",
            "A low, open hall at the pier's landward end, under a carved frieze of the Ten Stones. The Daykeepers of the Landing sit at a row of tables here and open a Ledger of Hours for every foreigner who lands, and close it again, and keep it, when they leave.", book)
    p.place("customs-hall", "The Customs-Hall", "Thorough, slow, and honest about almost everything",
            "Where the Daykeepers of the Landing open, weigh, count and enter every cargo that comes ashore. Its yard runs back from the quay behind it, and on a busy morning the queue of carts reaches the Landing Way.", book)
    p.place("keepers-shed", "The Keepers' Shed", "The one door customs does not open",
            "A locked shed at the far end of the customs yard. Cargo consigned by name to an Ah K'in passes customs unopened, as a courtesy to the Keepers of the Count, and waits here until its consignee's people come down the Road to collect it. The Daykeepers keep the key, keep a list of what goes in, and are not paid to wonder why.")
    p.place("long-tide", "The Long Tide", "Drink your days slowly. You only get the one kind here.",
            "A two-storey inn of grown wood three doors down from the Counting Pier, with a ship's figurehead over its door: where Crownweave sailors drink, factors meet their contacts, and anyone who wants to know what is happening on the Road goes first. Its innkeeper, Hester Crane, came ashore for one night twenty-six years ago and missed the tide.", book)
    p.place("gate-tower", "The Gate-Tower", "Where the White Road begins",
            "A square tower of the Road's pale stone at the top of the rise, and the town's one gate. The Balam detachment of the Landing keeps it, and the yard behind it, and from its roof a watch on both the Road and the Gulf. Past it the White Road runs west, dead straight, ten days to the Canopy Steps.", book)
    p.place("bearers-yard", "The Bearers' Yard", "Where the slow procession is hired",
            "A walled yard and hall just below the gate, where litters and bearers are hired for the dying who come to be carried up the Road to the Waiting Wards. The bearers' guild sets its own prices and walks at its own pace, and nobody in the yard asks who is in the litters.")
    p.place("warehouse-row", "Warehouse Row", "The realm's harvest, waiting for a ship",
            "Long grown-wood warehouses on the northern quays, where grain, beans and cacao from the Green Cradle and instruments from the Quickening Wards wait to be loaded, and Crownweave iron, salt and wool wait to be carted up the Road.")
    p.place("chandlers-row", "Chandlers' Row", "Rope, tar, salt pork and gossip",
            "The lane behind the northern quays where ships are victualled and refitted: chandlers, ropewalks, sailmakers and the Landing's few money-lenders. Foreign coin is not changed for jade-tally anywhere in Nabireth, only at Koneleth, so the Row's shops keep a slate for every ship's crew and settle it in Crownsblood when they sail.")
    p.place("foreign-lanes", "The Foreign Lanes", "Crownweave, a long way from home",
            "The streets south of the Landing Way where Nabireth's humans live: factors, sailors who missed their ship, and a few families who came three generations ago and never quite left. The houses are built of grown wood like everyone else's, but the doors have Crownweave knockers and the windows have Crownweave glass.")
    p.place("the-rise", "The Rise", "Where the Road-elves live",
            "The upper town, climbing to the gate-tower: the houses of the elves who work the Landing, and who have chosen to live their whole lives at true time. Their Count-bead cords are long and almost entirely white, and they will tell you, at length, that this is sensible.", book)
    p.place("quays", "The Quays", "Inns, warehouses and chandlers that would not look out of place in Stormwake",
            "The waterfront street that runs the length of the harbour, with houses on piles over the shallows on its seaward side. Everything that enters or leaves Thal'vireth crosses it.", book)
    p.place("landing-way", "The Landing Way", "The Road, before it is the Road",
            "The town's main street, running dead straight from the Counting Hall up the rise to the gate-tower, on the same line as the White Road and the Counting Pier. It is paved in the Road's own pale stone and held at true time by the same wards.")
    p.place("white-road", "The White Road", "Ten days, dead straight, to the Canopy Court",
            "A raised causeway of pale, close-fitted stone, broad enough for two carts to pass, running west from the gate-tower to the steps of the Canopy Court. The first of the Ten Stones stands a day's walk out.", book)
    p.place("granary-road", "The Granary Road", "The Green Cradle's harvest, coming down to the sea",
            "The road from the Threshing Mounds at Chaakvael, which joins the White Road just below the gate for its last stretch into Nabireth. In harvest season its carts queue back past the bend.", book)
    p.place("anchorage", "The Anchorage", "The Long Tide",
            "Where ships ride at anchor off Nabireth when the quays are full, and through the five wayeb days, when the Road is closed while its wards are renewed and nothing moves on it. Sailors call those five days the Long Tide, after the inn where they spend them.", book)
    p.place("jaeleth", "Ja'eleth", "The Water-Road",
            "A village on the shore just south of Nabireth, beside the stream that gives the harbour its fresh water. Its people fill and sell ships' water by the barrel and ferry passengers out to vessels at anchor during the wayeb.", book)
    p.place("boatyard", "Ja'eleth Boatyard", "The only yard in the realm that will mend a foreign hull",
            "A slipway and sheds on the shore at Ja'eleth. Elvish shipwrights grow their hulls; this yard has learned to nail them, and charges accordingly.", book)
    p.place("water-stair", "The Water-Stair", "Ships' water, by the barrel",
            "Stone steps down to the stream's mouth where Ja'eleth's water-sellers fill barrels for the ships, and where the ferries leave for the Anchorage.")
    return p
