"""Windperch, the Aerie Town: the largest settlement of winged folk outside the Aerialring (lore-book 13)."""
TOWN = "Windperch"
EPITHET = "The Aerie Town"
BOOK = "Of Skyloom, the Loom Above"

SPEC = {
    "id": "windperch", "seed": 1310, "style": "human", "corner": .18, "density": .9,
    "centre": (860, 600), "extent": (360, 290),
    "sea": {"dir": "NW", "shore": 520, "name": "the western sea"},
    "hill": {"at": (-20, -40), "radii": (110, 200, 290, 380, 470)},
    "plaza": {"r": 38, "id": "landing-square"},
    "from_map": True, "names": [{"dir": -147, "id": "old-trail"}],
    "spokes": 8,
    "landmarks": [
        {"id": "aeries", "at": (-110, -100), "size": (34, 34), "kind": "tower", "fill": "#6d5a40", "label": "the Aeries", "lab": (0, -28)},
        {"id": "aeries", "at": (40, -150), "size": (30, 30), "kind": "tower", "fill": "#6d5a40", "label": False},
        {"id": "aeries", "at": (150, -40), "size": (30, 30), "kind": "tower", "fill": "#6d5a40", "label": False},
        {"id": "training-field", "at": (-300, 120), "size": (200, 120), "angle": -20, "kind": "field", "lab": (0, 80)},
        {"id": "weather-station", "at": (120, 140), "size": (36, 36), "kind": "round", "fill": "#7e8fa0"},
        {"id": "distillery", "at": (-80, 160), "size": (60, 36), "angle": 10},
    ],
    "places": [
        {"id": "aeries", "name": "The Aeries", "epithet": "Doors halfway up the wall",
         "text": "Tall houses with landing-ledges in place of front doors, where Windperch's winged folk live. The town is the largest settlement of them outside the Aerialring.", "source": BOOK},
        {"id": "training-field", "name": "The Open-Air Field", "epithet": "Before they ever approach the Dropway",
         "text": "The slope where young fliers are trained in open air before they are ever allowed near the Dropway above.", "source": BOOK},
        {"id": "weather-station", "name": "The Weather-Station", "epithet": "The Weave's ground stations",
         "text": "The chief of the ground weather-stations Windperch keeps for the Weave: vanes, gauges, and a reader on watch at every hour.", "source": BOOK},
        {"id": "distillery", "name": "The Hard-Landing Distillery", "epithet": "Considered medicinal after a hard landing",
         "text": "Where Windperch distils its strong liquor, which is prescribed, poured and not argued with after a bad fall.", "source": BOOK},
        {"id": "landing-square", "name": "Landing Square", "epithet": "", "text": "The town square, kept clear of awnings and washing-lines so that anyone can come down into it."},
        {"id": "old-trail", "name": "The Old Trail", "epithet": "", "text": "South from Windperch past Gimorand along the foot of the western heights.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Skyloom · the Aerie Town",
}
