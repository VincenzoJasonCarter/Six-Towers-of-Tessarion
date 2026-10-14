"""Phais: the Glass Citadel and the Margin, Northreach's gate toward The Crown (lore-book 14)."""
TOWN = "Phais"
EPITHET = "The Glass Citadel and the Margin"
BOOK = "Of Northreach Weave, the Iron Threshold"

SPEC = {
    "id": "phais", "seed": 1404, "style": "dwarf", "density": 1.15,
    "centre": (760, 520), "extent": (360, 300),
    "hill": {"at": (-40, -60), "radii": (140, 240, 340, 450)},
    "walls": [{"rx": 320, "ry": 262, "towers": 20, "thick": 11, "id": "walls"}],
    "plaza": {"r": 42, "id": "glass-market", "at": (0, 20)},
    "from_map": True, "names": [{"dir": 84, "id": "iron-road"}],
    "spokes": 7,
    "landmarks": [
        {"id": "glass-citadel", "at": (-60, -150), "size": (110, 84), "angle": -6, "kind": "tower", "fill": "#6a7f86", "lab": (0, -58), "lsize": 16},
        {"id": "temple", "at": (130, -60), "size": (70, 70), "kind": "round"},
        {"id": "glassworks", "at": (-190, 80), "size": (130, 70), "angle": 15, "kind": "yard", "sheds": 3, "fill": "#a5532f"},
        {"id": "twice-gate", "at": (205, 140), "size": (52, 34), "angle": 40, "fill": "#7d6a4e", "lab": (36, 34)},
        {"id": "circuit-house", "at": (40, 150), "size": (60, 34), "angle": -8},
    ],
    "shanty": {"at": (460, 210), "r": (190, 120)},
    "districts": [{"id": "margin", "text": "the Margin", "at": (480, 330), "rotate": -10}],
    "fields": True, "farms": 18,
    "places": [
        {"id": "glass-citadel", "name": "The Glass Citadel", "epithet": "Fortified, and full of very careful people",
         "text": "Phais's fortress on the town's high ground, walled and garrisoned: the Weave's gate toward The Crown, and the keep that watches everything leaving Northreach for the capital.", "source": BOOK},
        {"id": "temple", "name": "The Temple of Phais", "epithet": "Questions whose answers would need to be recorded",
         "text": "A large temple within the walls. Its priests feed and house the people of the Margin outside them, and ask no questions whose answers would need to be recorded.", "source": BOOK},
        {"id": "glassworks", "name": "The Glassworks", "epithet": "The Union's greatest",
         "text": "Furnace-halls where the circuits of Glass Circuitry, designed in the Crucible, are blown, along with most of the Vessels' glass linings and a surprising quantity of fine jewellery and southern-bound wine.", "source": BOOK},
        {"id": "circuit-house", "name": "The Circuit House", "epithet": "Carefully isolated",
         "text": "Where finished circuits are tested before they go north, in rooms kept apart from one another for reasons described as technical and discussed as superstitious.", "source": BOOK},
        {"id": "twice-gate", "name": "The Twice-Gate", "epithet": "Everything leaving Northreach is inspected twice",
         "text": "The south-east gate, on the Iron Road to The Crown. Everything bound for the capital passes through it and is inspected, and then, at the inner yard, inspected again.", "source": BOOK},
        {"id": "margin", "name": "The Margin", "epithet": "Patched stone and salvaged plating",
         "text": "The shanty-quarter sprawling outside the walls, where artificers rotated out of the Crucible go when they have nowhere else to go, and where 'reassigned' bonding subjects tend, eventually, to surface.", "source": BOOK},
        {"id": "walls", "name": "The Walls of Phais", "epithet": "", "text": "Walled and fortified, as befits the Weave's gate toward The Crown.", "source": BOOK},
        {"id": "glass-market", "name": "The Glass Market", "epithet": "", "text": "The square inside the walls where jewellers and wine-glass merchants sell what the glassworks make for people who are not the Crucible."},
        {"id": "iron-road", "name": "The Iron Road", "epithet": "", "text": "South from Phais round the western foot of the Everstorm's mountain and through the Ironward stormgate to The Crown.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Northreach Weave · the gate toward The Crown",
}
