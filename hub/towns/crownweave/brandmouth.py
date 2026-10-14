"""Brandmouth, the Southern Harbor: the Union's nearest port to the Iron Hordes (lore-book 15)."""
TOWN = "Brandmouth"
EPITHET = "The Southern Harbor"
BOOK = "Of Emberweave, the Burning Gate of the South"

SPEC = {
    "id": "brandmouth", "seed": 1511, "style": "human", "density": 1.05,
    "centre": (780, 440), "extent": (380, 300),
    "sea": {"dir": "S", "shore": 300, "bay": 80, "bay_width": 260, "name": "the Burning Coast", "piers": 5, "ships": 5},
    "river": {"at": (-60, -40), "width": 30, "lab_at": .15},
    "walls": [{"rx": 300, "ry": 230, "at": (40, -30), "towers": 18, "thick": 10, "id": "walls"}],
    "plaza": {"r": 52, "shape": "square", "angle": -6, "id": "orc-market", "at": (110, -20)},
    "from_map": True, "names": [{"dir": -150, "id": "brand-road"}],
    "spokes": 7,
    "landmarks": [
        {"id": "watch-house", "at": (200, -110), "size": (46, 46), "kind": "tower", "fill": "#6d5a40", "lab": (0, -36)},
        {"id": "envoys-hall", "at": (-120, -130), "size": (60, 40), "angle": 10},
        {"id": "soulstone-house", "at": (240, 90), "size": (40, 30), "angle": -10, "fill": "#8c2f23"},
        {"id": "mole", "at": (180, 240), "size": (30, 170), "angle": 10, "kind": "dock", "lab": (60, -20)},
        {"id": "mercenary-yard", "at": (-160, 80), "size": (90, 60), "angle": 18, "kind": "yard"},
    ],
    "districts": [{"id": "river-docks", "text": "the River Docks", "at": (-170, 200), "rotate": -60, "size": 15}],
    "places": [
        {"id": "orc-market", "name": "The Plaza Market", "epithet": "A permanent market for orcish goods",
         "text": "Brandmouth's plaza has a permanent market for orcish goods and a permanent watch for orcish trouble, and the two are often the same people on different days.", "source": BOOK},
        {"id": "watch-house", "name": "The Watch-House", "epithet": "A permanent watch for orcish trouble",
         "text": "The tower on the plaza's edge from which the watch keeps an eye on the market, and on the sea beyond it.", "source": BOOK},
        {"id": "envoys-hall", "name": "The Envoys' Hall", "epithet": "The crossing worth daring",
         "text": "Where envoys from the Iron Hordes are received on landing and where the Union's own envoys wait for a ship south.", "source": BOOK},
        {"id": "soulstone-house", "name": "The Soulstone Exchange", "epithet": "",
         "text": "A small, very well-guarded house where the soulstone-traders who make the crossing worth daring meet their buyers.", "source": BOOK},
        {"id": "mole", "name": "The Southern Mole", "epithet": "", "text": "The long breakwater where ships that dare the crossing to the Iron Hordes load and unload.", "source": BOOK},
        {"id": "mercenary-yard", "name": "The Hiring Yard", "epithet": "", "text": "Where mercenaries for the crossing, and for the caravans inland, wait to be hired, and practise on one another while they wait."},
        {"id": "walls", "name": "The Walls of Brandmouth", "epithet": "", "text": "A walled port at the mouth of the Kingham.", "source": BOOK},
        {"id": "river-docks", "name": "The River Docks", "epithet": "", "text": "Quays along the Kingham, where river-boats bring down what the coast villages catch and cure."},
        {"id": "brand-road", "name": "The Brand Road", "epithet": "", "text": "North-west along the shore, round the end of the ridge at Redbank, and up the Newleighin valley to Fjerfi.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Emberweave · the Burning Coast", "cartouche": (230, 1020), "scale": (1330, 60),
}
