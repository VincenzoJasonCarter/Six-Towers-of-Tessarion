"""Hinckburgh, the Wakewatch: a hill-city on Stormwake's southern headland (lore-book 16)."""
TOWN = "Hinckburgh"
EPITHET = "The Wakewatch"
BOOK = "Of Stormwake, the Open Harbor of the East"

SPEC = {
    "id": "hinckburgh", "seed": 1621, "style": "human", "density": 1.0,
    "centre": (680, 560), "extent": (380, 310),
    "sea": {"dir": "ESE", "shore": 290, "bay": -60, "bay_width": 340, "name": "the open sea", "piers": 4, "ships": 3},
    "hill": {"at": (40, -40), "radii": (90, 170, 250, 340, 430)},
    "plaza": {"r": 36, "id": "lantern-square", "at": (-30, 40)},
    "from_map": True, "names": [],
    "spokes": 7,
    "landmarks": [
        {"id": "wakewatch", "at": (60, -70), "size": (46, 46), "kind": "tower", "fill": "#5d4a3a", "lab": (0, -36)},
        {"id": "signal-mast", "at": (150, -150), "size": (20, 20), "kind": "round", "fill": "#7e8fa0", "lab": (0, -20)},
        {"id": "readers-hall", "at": (-40, -140), "size": (60, 36), "angle": 8},
        {"id": "gale-stone", "at": (-140, 60), "size": (18, 18), "kind": "round", "fill": "#8a7a5a"},
        {"id": "pilots-house", "at": (250, 100), "size": (40, 26), "angle": -20},
    ],
    "districts": [{"id": "steps", "text": "the Hundred Steps", "at": (110, 120), "rotate": -30, "size": 15}],
    "places": [
        {"id": "wakewatch", "name": "The Wakewatch", "epithet": "A constant watch on the southern and eastern horizons",
         "text": "The tower on the headland's crown from which Hinckburgh's weather-readers watch the sea, day and night, for anything blowing in.", "source": BOOK},
        {"id": "signal-mast", "name": "The Signal Mast", "epithet": "Cordially, now",
         "text": "Where Hinckburgh exchanges signals with Skyloom's Loomwardens across the island: cordially, now, though Hinckburgh has never entirely forgiven the Western Gale.", "source": BOOK},
        {"id": "readers-hall", "name": "The Readers' Hall", "epithet": "", "text": "Where the weather-readers keep their logs, their barometers and their grudges."},
        {"id": "gale-stone", "name": "The Gale Stone", "epithet": "Never entirely forgiven",
         "text": "A marker stone carved with the names of those the Western Gale took from Hinckburgh, and, at the bottom, in smaller letters, the word Skyloom.", "source": BOOK},
        {"id": "pilots-house", "name": "The Pilots' House", "epithet": "Where the Lane leaves the Wakewater",
         "text": "Home of the pilots who take ships out where the Caer Veynese Lane leaves the Wakewater for the open sea.", "source": BOOK},
        {"id": "lantern-square", "name": "Lantern Square", "epithet": "", "text": "The town's square, where a lantern is hung for every ship the Wakewatch has seen go out and not yet seen come back."},
        {"id": "steps", "name": "The Hundred Steps", "epithet": "", "text": "The stair-streets climbing from the harbour to the hilltop; there are rather more than a hundred."},
    ],
    "title": TOWN, "sub": "Stormwake · the southern headland", "cartouche": (230, 1020), "compass": (80, 120), "scale": (170, 60),
}
