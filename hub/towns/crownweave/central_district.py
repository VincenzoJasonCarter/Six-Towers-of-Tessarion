"""Central District, seat of Skyloom: the anchor-town at the roots of the Skyward Towers (lore-book 13)."""
import math

from plans import INK, MARK, PAPER

TOWN = "Central District"
EPITHET = "Seat of the Weave"
BOOK = "Of Skyloom, the Loom Above"


def loom_shadow(p, ctx):
    """Every afternoon the Loom's shadow crosses the town end to end; shopkeepers set their clocks by it."""
    x, y = ctx["at"]((-120, -40))
    p.add("labels", f'<g opacity=".16" style="pointer-events:none"><ellipse cx="{x}" cy="{y}" rx="560" ry="300" fill="#1d2430" transform="rotate(-12 {x} {y})"/></g>')
    p.add("labels", f'<ellipse cx="{x}" cy="{y}" rx="560" ry="300" fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="2 8" opacity=".6" transform="rotate(-12 {x} {y})" style="pointer-events:none"/>')
    p.label(x - 330, y - 230, "the Loom's shadow, at the third hour after noon", 16, "tp-sub", rotate=-12, pid="loom-shadow")


SPEC = {
    "id": "central-district", "seed": 1301, "style": "human", "corner": .1, "density": .95,
    "centre": (820, 560), "extent": (430, 330),
    "river": {"at": (0, -150), "width": 26, "lab_at": .85},
    "plaza": {"r": 36, "id": "lift-plaza", "at": (0, 70)},
    "from_map": True, "names": [{"dir": -30, "id": "loom-road"}, {"dir": 129, "id": "sapphire-road"}],
    "spokes": 8,
    "landmarks": [
        {"id": "skyward-towers", "at": (60, -10), "size": (38, 38), "kind": "round", "fill": "#7e8fa0", "label": "Skyward Tower", "lab": (0, -30)},
        {"id": "skyward-towers", "at": (-60, 40), "size": (38, 38), "kind": "round", "fill": "#7e8fa0", "label": False},
        {"id": "skyward-towers", "at": (70, 130), "size": (38, 38), "kind": "round", "fill": "#7e8fa0", "label": False},
        {"id": "wardens-court", "at": (-170, 110), "size": (70, 44), "angle": 6},
        {"id": "lift-seal-office", "at": (150, 60), "size": (46, 30), "angle": -4},
        {"id": "candle-yards", "at": (-150, 230), "size": (110, 56), "angle": -8, "kind": "yard"},
        {"id": "cloudwine", "at": (200, 220), "size": (90, 50), "angle": 10, "kind": "yard", "sheds": 3},
    ],
    "labels": [{"text": "the three Skyward Towers", "at": (0, 200), "size": 15, "cls": "tp-lbl", "id": "skyward-towers"}],
    "fields": True,
    "places": [
        {"id": "skyward-towers", "name": "The Skyward Towers", "epithet": "Three tall spires rooted firmly in stone",
         "text": "The anchors of the floating Loom: they house the anchor-runes, lift-wards and harassed clerks whose task is to make sure the sky-bound part of Skyloom stays attached to the rest. From The Crown, one reaches the Loom by way of them.", "source": BOOK},
        {"id": "loom-shadow", "name": "The Loom's Shadow", "epithet": "Shopkeepers set their clocks by it",
         "text": "Every afternoon the shadow of the Loom, floating above, crosses the town end to end. Buildings here are low and broad so as not to foul the lift-wards, so nothing stands tall enough to be lit while the rest is dark.", "source": BOOK},
        {"id": "wardens-court", "name": "The Warden's Court", "epithet": "Where the Weave Warden holds court", "text": "The seat of the Weave Warden of Skyloom, at the edge of the tower plazas.", "source": BOOK},
        {"id": "lift-seal-office", "name": "The Lift-Seal Office", "epithet": "No seal, no lift",
         "text": "Where lift-seals are issued: the permits without which nobody rides the Skyward Towers up to the Groundring.", "source": BOOK},
        {"id": "candle-yards", "name": "The Loom Stores", "epithet": "Cheese, liquor, and a great many candles",
         "text": "Where the Loom's own needs are gathered before being sent up: cheese, liquor, and a great many candles.", "source": BOOK},
        {"id": "cloudwine", "name": "The Cloudwine Distilleries", "epithet": "Drunk mostly by people who have just come down",
         "text": "Distilleries that make cloudwine, a clear, cold spirit.", "source": BOOK},
        {"id": "lift-plaza", "name": "The Tower Plazas", "epithet": "", "text": "Central District's plazas cluster round the roots of the Skyward Towers.", "source": BOOK},
        {"id": "loom-road", "name": "The Loom Road", "epithet": "", "text": "East through the Loomward stormgate to The Crown.", "source": BOOK},
        {"id": "sapphire-road", "name": "The Sapphire Road", "epithet": "", "text": "West through Midhurstnes, Castfield and Clitford toward Cloudmoor Harbor.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Seat of Skyloom, beneath the Loom",
    "extra": loom_shadow,
}
