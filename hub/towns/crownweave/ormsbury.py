"""Ormsbury, the Ore Harbor: the Frost Coast port where the Great Frost Route comes in (lore-book 14)."""
TOWN = "Ormsbury"
EPITHET = "The Ore Harbor"
BOOK = "Of Northreach Weave, the Iron Threshold"

SPEC = {
    "id": "ormsbury", "seed": 1414, "style": "dwarf", "density": 1.0, "mpu": .6,
    "centre": (800, 640), "extent": (280, 210),
    "sea": {"dir": "N", "shore": 230, "bay": 60, "bay_width": 200, "name": "the Frost Coast", "piers": 4, "ships": 3},
    "river": {"at": (-70, 0), "width": 22, "lab_at": .8},
    "plaza": {"r": 34, "id": "chandlery-square", "at": (60, 40)},
    "from_map": True, "names": [{"dir": 122, "id": "maramersban-path"}],
    "rings": (.4, .7, .95), "spokes": 5,
    "landmarks": [
        {"id": "ore-quays", "at": (140, -150), "size": (160, 34), "angle": 4, "kind": "dock", "lab": (0, 36)},
        {"id": "candle-works", "at": (-190, 90), "size": (90, 46), "angle": 12, "kind": "yard"},
        {"id": "ice-house", "at": (190, 30), "size": (50, 34), "angle": -6, "fill": "#7e8fa0"},
        {"id": "factor-house", "at": (-30, -60), "size": (40, 28), "angle": 6},
    ],
    "places": [
        {"id": "ore-quays", "name": "The Ore Quays", "epithet": "Where the Great Frost Route comes in",
         "text": "Where ore, cold-cured timber and the occasional Khazrund cargo are landed from the north and sent inland along the Maramersban Path.", "source": BOOK},
        {"id": "ice-house", "name": "The Dockers' Hall", "epithet": "Good ice from bad, by listening to it",
         "text": "The harbour ices over in deep winter, and Ormsbury's dockers are said to be the only people in the Union who can tell good ice from bad by listening to it. This is where they meet to decide whether to.", "source": BOOK},
        {"id": "candle-works", "name": "The Candle-Works", "epithet": "For the Deepdelve, where open flame is forbidden",
         "text": "Ormsbury is one of the towns that pours wax and tallow for the Deepdelve, where a sealed candle is the only light a family can call its own.", "source": BOOK},
        {"id": "factor-house", "name": "The Khazrund Factor's House", "epithet": "Occasional Khazrund cargoes", "text": "Where Khazrund's factor in the harbour keeps rooms, and an unusually good door.", "source": BOOK},
        {"id": "chandlery-square", "name": "Chandlery Square", "epithet": "", "text": "The town square, ringed by chandlers who sell rope, tar, and stoves for ships that have to winter here."},
        {"id": "maramersban-path", "name": "The Maramersban Path", "epithet": "", "text": "Across the eastern moors from Ormsbury inland.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Northreach · the Frost Coast", "scale_m": 100, "cartouche": (1390, 1020), "compass": (80, 880),
}
