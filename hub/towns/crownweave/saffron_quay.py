"""Saffron Quay, the Spice-Port: Emberweave's door to the eastern sea (lore-book 15)."""
TOWN = "Saffron Quay"
EPITHET = "The Spice-Port"
BOOK = "Of Emberweave, the Burning Gate of the South"

SPEC = {
    "id": "saffron-quay", "seed": 1517, "style": "tiefling", "density": 1.0,
    "centre": (720, 560), "extent": (380, 300),
    "sea": {"dir": "E", "shore": 320, "bay": 70, "bay_width": 240, "name": "the eastern sea", "piers": 6, "ships": 6},
    "river": {"at": (0, 30), "width": 30, "lab_at": .15},
    "plaza": {"r": 48, "shape": "square", "angle": 4, "id": "saffron-plaza", "at": (40, 140)},
    "from_map": True, "names": [{"dir": -154, "id": "saffron-road"}],
    "spokes": 7,
    "landmarks": [
        {"id": "temple", "at": (-120, 180), "size": (64, 64), "kind": "round"},
        {"id": "sea-shrine", "at": (290, -120), "size": (22, 22), "kind": "round", "fill": "#4f7488", "lab": (-10, 28)},
        {"id": "spice-warehouses", "at": (210, 210), "size": (70, 140), "angle": 6, "kind": "yard", "sheds": 3},
        {"id": "dye-house", "at": (-200, -80), "size": (70, 40), "angle": -10, "fill": "#6d4a7a"},
        {"id": "emberfall-factory", "at": (170, -100), "size": (50, 36), "angle": 10, "fill": "#8c2f23"},
    ],
    "districts": [{"id": "pepper-lanes", "text": "the Pepper Lanes", "at": (-60, -120), "rotate": 6}],
    "places": [
        {"id": "saffron-plaza", "name": "The Saffron Plaza", "epithet": "The Weave's door to the eastern sea",
         "text": "A plaza-port square where spice, dye, resin and saffron come ashore and are first sold.", "source": BOOK},
        {"id": "temple", "name": "The Temple of Two Altars", "epithet": "A Dustveil altar and a sea-shrine",
         "text": "The only temple on the coast with a Dustveil altar for those who go inland and a sea-shrine for those who go out, and it keeps both busy.", "source": BOOK},
        {"id": "sea-shrine", "name": "The Harbour Shrine", "epithet": "", "text": "The temple's sea-shrine keeps a lamp at the end of the quays as well, lit for every ship still out.", "source": BOOK},
        {"id": "spice-warehouses", "name": "The Spice Warehouses", "epithet": "Most of the spice stalls in the city quarter are stocked from here",
         "text": "Long warehouses along the quay, cool and dark and overwhelming, where the spice waits for the caravans up the Saffron Road.", "source": BOOK},
        {"id": "dye-house", "name": "The Dye-House", "epithet": "", "text": "Where dyes landed from the east are tested and mixed before going upriver to Dyewater's vats."},
        {"id": "emberfall-factory", "name": "The Emberfall Factory", "epithet": "Emberfall's trade",
         "text": "The house of the Emberfall trading houses' factors, where contracts with the tiefling ports are written in very small ink.", "source": BOOK},
        {"id": "pepper-lanes", "name": "The Pepper Lanes", "epithet": "", "text": "The streets north of the river, where spice is ground, bagged and argued over."},
        {"id": "saffron-road", "name": "The Saffron Road", "epithet": "", "text": "West through Tuskhold and Slagbarrow, past the foot of Emberpeak, to Fjerfi.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Emberweave · the Spice-Port", "cartouche": (230, 1020), "compass": (80, 120), "scale": (170, 60),
}
