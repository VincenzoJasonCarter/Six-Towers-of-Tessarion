"""Craftry: the Shipwrights' Tools, a small town with a large charter (lore-book 16)."""
TOWN = "Craftry"
EPITHET = "The Shipwrights' Tools"
BOOK = "Of Stormwake, the Open Harbor of the East"

SPEC = {
    "id": "craftry", "seed": 1631, "style": "human", "density": 1.1, "mpu": .6,
    "centre": (800, 560), "extent": (300, 230),
    "plaza": {"r": 40, "shape": "square", "id": "charter-square"},
    "from_map": True, "names": [{"dir": -63, "id": "dunscaston-trail"}],
    "spokes": 6, "fields": True, "farms": 22,
    "landmarks": [
        {"id": "charter-hall", "at": (0, -80), "size": (90, 50), "angle": 2, "lsize": 15},
        {"id": "toolsmiths", "at": (-170, 30), "size": (110, 54), "angle": 14, "kind": "yard", "sheds": 3, "fill": "#7d6a4e"},
        {"id": "edge-mill", "at": (-60, -195), "size": (40, 26), "angle": 4, "fill": "#7d6a4e"},
        {"id": "gale-tools", "at": (110, 90), "size": (26, 26), "kind": "round", "fill": "#8a7a5a"},
    ],
    "places": [
        {"id": "charter-hall", "name": "The Charter Hall", "epithet": "A charter out of all proportion to its size",
         "text": "A town hall fit for a city, in a town of under three thousand. Craftry's charter was granted in gratitude for the tools that rebuilt Caer Veyn's harbour after the Western Gale, and the town has built up to it ever since.", "source": BOOK},
        {"id": "toolsmiths", "name": "The Tool-Forges", "epithet": "Every shipyard in the Union",
         "text": "Where the adzes, augers, caulking irons and rope-hooks of every shipyard in the Union are forged, hardened and stamped with the Craftry mark.", "source": BOOK},
        {"id": "edge-mill", "name": "The Edge-Mill", "epithet": "", "text": "A water-mill on the brook that grinds and hones the forges' blades."},
        {"id": "gale-tools", "name": "The Gale Anvil", "epithet": "", "text": "The anvil on which the first of the tools for the rebuilding of Caer Veyn was struck, set up in the square on a plinth, with the date.", "source": BOOK},
        {"id": "charter-square", "name": "Charter Square", "epithet": "", "text": "The square in front of the Charter Hall, larger than the town strictly needs."},
        {"id": "dunscaston-trail", "name": "The Dunscastonese Trail", "epithet": "", "text": "One of the trails linking the Harbor Shore's towns, north-east toward Dunscaston and Caer Veyn.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Stormwake · the Shipwrights' Tools", "scale_m": 100,
}
