"""Fjerfi, seat of Emberweave: a walled river-port on the Newleighin (lore-book 15)."""
TOWN = "Fjerfi"
EPITHET = "Seat of the Weave"
BOOK = "Of Emberweave, the Burning Gate of the South"

SPEC = {
    "id": "fjerfi", "seed": 1502, "style": "human",
    "centre": (760, 520), "extent": (420, 330),
    # the Newleighin comes down from the north-east and runs away south-west toward the sea
    "river": {"at": (-260, -40), "width": 40, "lab_at": .85},
    "walls": [{"rx": 330, "ry": 255, "towers": 22, "thick": 10, "id": "walls"}],
    "plaza": {"r": 70, "shape": "square", "angle": 8, "id": "great-plaza"},
    "from_map": True, "names": [{"dir": -54, "id": "ember-road"}],
    "spokes": 7, "fields": True, "density": 1.1,
    "landmarks": [
        {"id": "wardens-court", "at": (-30, -125), "size": (70, 46), "angle": 6},
        {"id": "charter-house", "at": (115, -95), "size": (48, 34), "angle": 12},
        {"id": "temple", "at": (-150, 40), "size": (60, 60), "kind": "round"},
        {"id": "citadel", "at": (200, 120), "size": (90, 70), "angle": -10, "kind": "tower", "fill": "#7d6a4e"},
        {"id": "tusk-halls", "at": (-120, 175), "size": (110, 46), "angle": 20, "kind": "yard"},
        {"id": "lighter-quays", "at": (-255, -100), "size": (130, 22), "angle": -58, "kind": "dock", "lab": (75, 10)},
        {"id": "caravan-yards", "at": (40, 330), "size": (150, 80), "angle": -6, "kind": "yard"},
    ],
    "districts": [{"id": "lighter-quarter", "text": "Lightermen's Quarter", "at": (-120, -190), "rotate": -35},
                  {"id": "hookah-lanes", "text": "the Awning Lanes", "at": (170, 75), "rotate": 8}],
    "places": [
        {"id": "great-plaza", "name": "The Great Plaza", "epithet": "A smaller, hotter twin of the Ashward",
         "text": "Fjerfi's great square, where caravans for the south are assembled in uncertain lines, as they are on the Ashward Plaza in the city quarter, only hotter and with fewer people watching.", "source": BOOK},
        {"id": "wardens-court", "name": "The Warden's Court", "epithet": "Where the Weave Warden holds court",
         "text": "The hall on the plaza's north side where the Weave Warden of Emberweave sits: usually a veteran of the road, sun-scarred, pragmatic, and more interested in keeping blades sheathed than in filing neat reports.", "source": BOOK},
        {"id": "charter-house", "name": "The Charter House", "epithet": "Where caravan charters for the south are sealed",
         "text": "Scribes in triplicate, a long queue and a longer ledger. Anything that leaves the Crown for the south passes through Fjerfi and is counted here.", "source": BOOK},
        {"id": "temple", "name": "The Temple and its Dustveil Altar", "epithet": "Every journey is another line in the pattern",
         "text": "Fjerfi's temple keeps a Dustveil altar of its own, a twin of the way-altar in the city quarter, where caravan hands tie a length of coloured thread to belt or wagon before they roll out.", "source": BOOK},
        {"id": "citadel", "name": "The Citadel", "epithet": "The Warden's last argument",
         "text": "A squat keep in the wall's southern arc, garrisoned by the Weave's watch. Its yard holds the town's water-cisterns, which in a dry year are guarded more closely than its treasury."},
        {"id": "tusk-halls", "name": "The Iron-Tusk Country Halls", "epithet": "Where the clans' contracts actually get signed",
         "text": "The country halls of the Iron-Tusk lodges of the city quarter: long timber halls banded in iron, hung with clan banners, where caravan masters and clan envoys argue over the price of protection.", "source": BOOK},
        {"id": "lighter-quays", "name": "The Lighter Quays", "epithet": "By Emberweave standards, almost orderly",
         "text": "Sea-going ships cannot reach Fjerfi; the flat-bottomed lighters of the Fjerfian Route can, and bring cargo up from the coast to these quays. The lightermen's guild sets the price of everything that arrives by water.", "source": BOOK},
        {"id": "caravan-yards", "name": "The Caravan Yards", "epithet": "Water, measured more carefully than gold",
         "text": "Pens, sheds and water-troughs outside the south gate, where the caravans that will take the Brand Road to the coast are watered, loaded and argued over before dawn."},
        {"id": "walls", "name": "The Walls of Fjerfi", "epithet": "Dark brick, warm to the touch at midnight",
         "text": "A ring of dark brick round the river-port, with a gate on every road. The river runs through the wall under a pair of water-gates that are closed at sunset and opened, for a fee, at any hour."},
        {"id": "lighter-quarter", "name": "The Lightermen's Quarter", "epithet": "",
         "text": "The riverside streets where the lightermen live, mend their boats and drink, and from which the guild runs the river."},
        {"id": "hookah-lanes", "name": "The Awning Lanes", "epithet": "",
         "text": "Narrow streets east of the plaza, shaded by canvas awnings in sun-faded reds and oranges: spice stalls, hookah dens, and the smell of hot iron."},
        {"id": "ember-road", "name": "The Ember Road", "epithet": "A day's ride to the Emberward stormgate",
         "text": "The road north to The Crown, the one the caravans of the city quarter actually take.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Seat of Emberweave",
}
