"""Skyfall Reach: Where the Sky Is Put Down, Skyloom's strangest city (lore-book 13)."""
import math

from plans import INK

TOWN = "Skyfall Reach"
EPITHET = "Where the Sky Is Put Down"
BOOK = "Of Skyloom, the Loom Above"


def weather(p, ctx):
    """Rain hatching across the plan, and the lightning rods on the roofs."""
    rng = p.rng
    for _ in range(140):
        x, y = rng.uniform(0, p.W), rng.uniform(0, p.H)
        p.add("labels", f'<path d="M{x:.0f} {y:.0f}l-8 22" stroke="#5f7380" stroke-width="1" opacity=".35" style="pointer-events:none"/>')
    for _ in range(26):
        x, y = rng.uniform(*ctx["area"].bounds[0::2]), rng.uniform(*ctx["area"].bounds[1::2])
        p.add("labels", f'<path d="M{x:.0f} {y:.0f}l3 -9 -3 2 3 -9" fill="none" stroke="#b87333" stroke-width="1.6" style="pointer-events:none"/>')


SPEC = {
    "id": "skyfall-reach", "seed": 1309, "style": "human", "corner": .42, "density": 1.0,
    "centre": (720, 620), "extent": (360, 290),
    "sea": {"dir": "NE", "shore": 360, "bay": 60, "bay_width": 280, "name": "the northern sea", "piers": 3, "ships": 2},
    "plaza": {"r": 36, "id": "copper-square"},
    "from_map": True, "names": [{"dir": 158, "id": "reach-road"}],
    "spokes": 7,
    "landmarks": [
        {"id": "grove", "at": (-360, -200), "size": (300, 220), "kind": "grove", "lab": (0, 130), "lsize": 16},
        {"id": "reach-tear", "at": (330, 170), "size": (70, 110), "kind": "rift", "lab": (0, 74), "lsize": 15},
        {"id": "loomwardens-house", "at": (-150, -40), "size": (50, 34), "angle": 10},
        {"id": "weaving-sheds", "at": (110, -100), "size": (100, 46), "angle": -10, "kind": "yard", "sheds": 3},
        {"id": "boot-hall", "at": (40, 140), "size": (40, 28), "angle": 6},
    ],
    "places": [
        {"id": "grove", "name": "The Skyfall Grove", "epithet": "Wood that remembers the storms that shaped it",
         "text": "A sacred forest of tall, storm-scarred trees grown under constant weather. Elven Loomwardens tend it as a shrine; wood taken from it, rarely and only with permission, is said to remember the storms that shaped it.", "source": BOOK},
        {"id": "reach-tear", "name": "The Reach Tear", "epithet": "A pressure valve",
         "text": "A standing rift at the edge of the town. The Loomwardens send surplus weather into it. What is on the other side has never been formally described.", "source": BOOK},
        {"id": "loomwardens-house", "name": "The Loomwardens' House", "epithet": "Where the storms are set down",
         "text": "When the Loom Temple turns a storm away from the Union, the weather has to go somewhere; much of it is sent north and set down here, and the Loomwardens in this house decide where.", "source": BOOK},
        {"id": "weaving-sheds", "name": "The Weaving Sheds", "epithet": "", "text": "The Reach weaves cloth, mostly, one suspects, because nothing else wears out quite as fast there.", "source": BOOK},
        {"id": "boot-hall", "name": "The Boot Hall", "epithet": "", "text": "The bootmakers' hall; the Reach goes through boots faster than anywhere in the Union.", "source": BOOK},
        {"id": "copper-square", "name": "Copper Square", "epithet": "Low, rounded, and grounded with copper",
         "text": "The town square, with a copper rod at each corner. Every house in the Reach is built low and rounded, and grounded with copper.", "source": BOOK},
        {"id": "reach-road", "name": "The Skyfall Reach Road", "epithet": "", "text": "Down the Northern Arm to Windperch, with a branch east toward the Iron Crucible.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Skyloom · Where the Sky Is Put Down", "cartouche": (1390, 1020), "compass": (80, 120),
    "extra": weather,
}
