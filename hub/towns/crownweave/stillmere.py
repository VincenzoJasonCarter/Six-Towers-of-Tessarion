"""Stillmere, the Still Water: a lake-port where the Loomwardens hold the air perfectly still (lore-book 13)."""
TOWN = "Stillmere"
EPITHET = "The Still Water"
BOOK = "Of Skyloom, the Loom Above"

SPEC = {
    "id": "stillmere", "seed": 1313, "style": "human", "corner": .1,
    "centre": (860, 470), "extent": (380, 290),
    "lake": {"at": (-380, 330), "r": (520, 300), "name": "the Mere"},
    "river": {"at": (-170, -20), "width": 22, "lab_at": .15},
    "plaza": {"r": 38, "id": "quiet-square", "at": (40, 40)},
    "from_map": True, "names": [{"dir": -6, "id": "stillmerean-trail"}],
    "spokes": 7,
    "landmarks": [
        {"id": "lens-houses", "at": (140, -110), "size": (90, 44), "angle": 6, "kind": "yard", "sheds": 3},
        {"id": "calibration-hall", "at": (-60, -120), "size": (70, 36), "angle": -8},
        {"id": "ring-foundry", "at": (170, 120), "size": (64, 44), "angle": 12, "fill": "#7d6a4e"},
        {"id": "range", "at": (-250, 150), "size": (260, 40), "angle": 32, "kind": "field", "lab": (40, 50)},
        {"id": "wardens-post", "at": (-160, 10), "size": (30, 30), "kind": "round", "fill": "#7e8fa0"},
    ],
    "labels": [{"text": "no wind reaches the mere", "at": (-420, 420), "size": 18}],
    "fields": True, "farms": 18,
    "places": [
        {"id": "lens-houses", "name": "The Lens-Houses", "epithet": "The most delicate work in the Weave",
         "text": "Where lenses are ground in air so still that not a mote of dust settles crooked.", "source": BOOK},
        {"id": "calibration-hall", "name": "The Calibration Hall", "epithet": "", "text": "Where wind-instruments from all over Skyloom are brought to be set against air that does not move.", "source": BOOK},
        {"id": "ring-foundry", "name": "The Anchor-Ring Foundry", "epithet": "", "text": "Where the bronze anchor-rings that hold the Loom to the Skyward Towers are cast.", "source": BOOK},
        {"id": "range", "name": "The Firing Range", "epithet": "Flight measured without interference",
         "text": "A long cleared strip along the mere's shore, where artillery is test-fired and the fall of every shot measured with no wind to blame.", "source": BOOK},
        {"id": "wardens-post", "name": "The Loomwardens' Post", "epithet": "By long-standing agreement",
         "text": "Where the Loomwardens who hold Stillmere's air perfectly still keep watch. The silence unsettles visitors; the locals no longer hear it.", "source": BOOK},
        {"id": "quiet-square", "name": "Quiet Square", "epithet": "", "text": "The market square, where hawkers do not shout because the still air carries a whisper across it."},
        {"id": "stillmerean-trail", "name": "The Stillmerean Trail", "epithet": "", "text": "One of the trails stitching together Skyloom's southern lake-towns.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Skyloom · the Still Water", "scale": (1320, 1050), "cartouche": (1380, 120), "compass": (1500, 260),
}
