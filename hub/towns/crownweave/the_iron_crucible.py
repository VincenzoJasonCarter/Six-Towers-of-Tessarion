"""The Iron Crucible, seat of Northreach: a town that grew up around a fortress, then into it (lore-book 14)."""
TOWN = "The Iron Crucible"
EPITHET = "Seat of the Weave"
BOOK = "Of Northreach Weave, the Iron Threshold"

SPEC = {
    "id": "the-iron-crucible", "seed": 1401, "style": "dwarf", "density": 1.25,
    "centre": (800, 580), "extent": (430, 360),
    # the highest ground in the Union: the fortress at the summit, the town in terraces below it
    "hill": {"at": (0, -170), "radii": (120, 210, 300, 400, 500)},
    "plaza": {"r": 46, "id": "chapel-close", "at": (0, 40)},
    "from_map": True, "names": [{"dir": 20, "id": "penilworth-trail"}, {"dir": 151, "name": "the Forge Run road", "id": "forge-run"}],
    "rings": (.36, .56, .76, .95), "spokes": 6,
    "landmarks": [
        {"id": "resonance-crucible", "at": (0, -200), "size": (170, 120), "angle": 4, "kind": "tower", "fill": "#5f5246", "lab": (0, -78), "lsize": 17},
        {"id": "chapel", "at": (0, 40), "size": (44, 44), "kind": "round", "lab": (0, 40)},
        {"id": "scriptoriums", "at": (-150, -150), "size": (80, 44), "angle": -14},
        {"id": "containment-yards", "at": (175, -110), "size": (130, 80), "angle": 12, "kind": "yard", "fill": "#7d6a4e"},
        {"id": "deepdelve-head", "at": (-250, 170), "size": (54, 40), "kind": "rift", "lab": (0, 38)},
        {"id": "waste-heat-works", "at": (190, 170), "size": (120, 60), "angle": -8, "kind": "yard", "sheds": 3},
    ],
    "districts": [{"id": "terraces", "text": "the Upper Terraces", "at": (-10, -95), "size": 16},
                  {"id": "conclaves", "text": "the Conclaves", "at": (-120, 220), "rotate": -6}],
    "places": [
        {"id": "resonance-crucible", "name": "The Resonance Crucible", "epithet": "A laboratory that learned to defend itself",
         "text": "The fortress-complex at the summit: lead-lined halls, reinforced glass vats and sealed scriptoriums, where research is organised round the three sanctioned pillars of Mana Conversion, Corruption Containment and Glass Circuitry. From without it resembles a keep. The town took its name from it long before anyone gave it a charter.", "source": BOOK},
        {"id": "chapel", "name": "The Chapel of Tolerances", "epithet": "Congregants listen for their own family names",
         "text": "The Weave's only temple of note, at the Crucible's heart. It holds no idol; its walls are lined floor to ceiling with bronze plates, each stamped with the date, place and margin of a structural failure, and its priests read from them on feast-days.", "source": BOOK},
        {"id": "chapel-close", "name": "The Chapel Close", "epithet": "",
         "text": "The slate-paved square round the Chapel, warm underfoot in all weathers: its seams are cut with grooves that bleed the Vessels' excess heat into the ground so that it never ices.", "source": BOOK},
        {"id": "scriptoriums", "name": "The Sealed Scriptoriums", "epithet": "Reviewed, stamped, and quietly classified",
         "text": "The highest terrace below the fortress, where laboratories, archives and fortified offices review the Crucible's results and decide which of them anyone else will ever read.", "source": BOOK},
        {"id": "containment-yards", "name": "The Containment Yards", "epithet": "Sub-levels whose purpose has been lost to reinforcement",
         "text": "Testing halls and containment yards on the terrace beneath the laboratories, where sinks are proved before they go to the Orcholis Aperture, and where some of the older sub-levels are no longer entered at all.", "source": BOOK},
        {"id": "deepdelve-head", "name": "The Deepdelve Shaft-head", "epithet": "Light is indirect. Warmth is routed. Silence is engineered.",
         "text": "Where the shafts, ramps and pressure-rated stairwells of the town's lower conclaves go down into the Deepdelve Faces under the Crucible. Entire clan lines live closer to bedrock than sky; most of the Weave's candles end up down there.", "source": BOOK},
        {"id": "waste-heat-works", "name": "The Waste-Heat Works", "epithet": "Nothing warm is wasted in Northreach",
         "text": "The potteries, distilleries and preserving-houses that the Crucible runs on heat bled from the Vessels, because its cold hills will not feed it otherwise.", "source": BOOK},
        {"id": "terraces", "name": "The Upper Terraces", "epithet": "",
         "text": "The stone terraces that step down from the fortress: laboratories and archives highest, testing halls beneath them, and beneath those, the people.", "source": BOOK},
        {"id": "conclaves", "name": "The Conclaves", "epithet": "Each begins as shelter and ends as infrastructure",
         "text": "The dwarven residential quarters, which are not streets or blocks but irregular stone masses accreted, reinforced and re-hollowed over generations. Hearths sit where heat already sheds; walls thicken where the resonance hums strongest.", "source": BOOK},
        {"id": "penilworth-trail", "name": "The Penilworth Trail", "epithet": "",
         "text": "The main highland road east from the Crucible through Bybdetos to the Penilworth fort.", "source": BOOK},
        {"id": "forge-run", "name": "The Forge Run road", "epithet": "",
         "text": "South down the river valley where the Infusion Forges burn, past Naurias and Pekion.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Seat of Northreach Weave", "scale_m": 200,
}
