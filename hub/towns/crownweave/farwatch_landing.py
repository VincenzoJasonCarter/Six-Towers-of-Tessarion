"""Farwatch Landing, the Ground-Field: a citadel with a landing-field for heavy skycraft (lore-book 13)."""
TOWN = "Farwatch Landing"
EPITHET = "The Ground-Field"
BOOK = "Of Skyloom, the Loom Above"

SPEC = {
    "id": "farwatch-landing", "seed": 1307, "style": "human", "corner": .1, "density": .9, "mpu": .6,
    "centre": (900, 520), "extent": (280, 220),
    "hill": {"at": (-40, -20), "radii": (120, 220, 330, 450)},
    "river": {"at": (300, 0), "width": 20, "lab_at": .8},
    "walls": [{"rx": 170, "ry": 140, "at": (-60, -20), "towers": 10, "thick": 12, "id": "citadel-walls"}],
    "plaza": {"r": 30, "id": "parade", "at": (-60, -20)},
    "from_map": True, "names": [{"dir": 136, "id": "sapphire-road"}],
    "rings": (.4, .7, .95), "spokes": 5,
    "landmarks": [
        {"id": "watch-tower", "at": (-140, -90), "size": (40, 40), "kind": "tower", "fill": "#5d4a3a", "lab": (0, -32)},
        {"id": "landing-field", "at": (-560, 120), "size": (380, 260), "angle": -8, "kind": "field", "lab": (0, 150), "lsize": 16},
        {"id": "hangars", "at": (-330, 260), "size": (110, 50), "angle": -8, "kind": "yard", "sheds": 3},
        {"id": "keep", "at": (20, -50), "size": (54, 40), "angle": 6},
    ],
    "labels": [{"text": "westward: Thal'vireth, perhaps", "at": (-620, -340), "size": 18}],
    "places": [
        {"id": "watch-tower", "name": "The Farwatch", "epithet": "The westernmost manned post in the Union",
         "text": "The citadel's watch-tower. On clear days its keepers claim to see the green line of Thal'vireth. Few believe them.", "source": BOOK},
        {"id": "landing-field", "name": "The Ground-Field", "epithet": "For skycraft too heavy to reach the Loom",
         "text": "A broad, level field on the coastal highland, cleared and rolled, where skycraft too heavy to reach the Loom come down.", "source": BOOK},
        {"id": "hangars", "name": "The Field Sheds", "epithet": "", "text": "Long sheds at the field's edge where skycraft are moored, mended and unloaded."},
        {"id": "keep", "name": "The Keep", "epithet": "", "text": "The citadel's commander's hall and armoury."},
        {"id": "citadel-walls", "name": "The Citadel Walls", "epithet": "", "text": "A citadel on the coastal highlands.", "source": BOOK},
        {"id": "parade", "name": "The Parade", "epithet": "", "text": "The citadel's yard, where the garrison musters."},
        {"id": "sapphire-road", "name": "The Sapphire Road", "epithet": "", "text": "The road along which most of Skyloom's instruments, glass and flight-gear travel.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Skyloom · the Ground-Field", "scale_m": 100,
}
