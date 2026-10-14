"""Marlmond, the Perfumers' City: where foreign cargo is made respectable (lore-book 16)."""
TOWN = "Marlmond"
EPITHET = "The Perfumers' City"
BOOK = "Of Stormwake, the Open Harbor of the East"

SPEC = {
    "id": "marlmond", "seed": 1612, "style": "human", "density": 1.05,
    "centre": (820, 560), "extent": (420, 320),
    "plaza": {"r": 44, "id": "blending-square"},
    "from_map": True, "names": [{"dir": -179, "id": "newbomyard-trail"}],
    "spokes": 8, "fields": True, "farms": 30,
    "landmarks": [
        {"id": "distilleries", "at": (-200, -90), "size": (140, 64), "angle": -10, "kind": "yard", "sheds": 3},
        {"id": "bottling-houses", "at": (180, -110), "size": (120, 54), "angle": 8, "kind": "yard", "sheds": 3},
        {"id": "glasshouse", "at": (-150, 150), "size": (64, 40), "angle": 14},
        {"id": "customs", "at": (90, 60), "size": (60, 40), "angle": -6, "fill": "#7d4a2c"},
        {"id": "label-house", "at": (-60, -110), "size": (36, 26), "angle": 4},
    ],
    "districts": [{"id": "still-lanes", "text": "the Still Lanes", "at": (-230, 20), "rotate": -8}],
    "places": [
        {"id": "distilleries", "name": "The Distilleries", "epithet": "Where foreign cargo is made respectable",
         "text": "Resins, spices, oils and aromatics landed in Caer Veyn come up here to be distilled and blended into the perfumes Marlmond is famous for.", "source": BOOK},
        {"id": "bottling-houses", "name": "The Bottling-Houses", "epithet": "The reason the customs law runs to eleven pages",
         "text": "Where foreign goods are rebottled in Marlmond glass and relabelled as Crownweave goods. Anything that smells of Stormwake in The Crown's markets probably passed through here on the way.", "source": BOOK},
        {"id": "glasshouse", "name": "The Marlmond Glasshouse", "epithet": "Marlmond glass",
         "text": "The furnaces that blow the town's own bottles: thin, faintly violet, and stamped on the base with a mark that customs clerks have learned to trust a little too much."},
        {"id": "customs", "name": "The Customs House", "epithet": "Eleven pages",
         "text": "Where the Union tries to keep track of what goes into Marlmond's vats as foreign and comes out as domestic. The clerks are thorough; the bottlers are more so.", "source": BOOK},
        {"id": "label-house", "name": "The Label House", "epithet": "",
         "text": "Printers and calligraphers who make the labels, in the right ink, the right hand and the right language for whichever market a bottle is going to."},
        {"id": "blending-square", "name": "Blending Square", "epithet": "", "text": "The market square, which smells of everything at once."},
        {"id": "still-lanes", "name": "The Still Lanes", "epithet": "", "text": "Streets of small family stills, each with a recipe it will not share and a neighbour it suspects of stealing it."},
        {"id": "newbomyard-trail", "name": "The Newbomyard Trail", "epithet": "", "text": "North-west to Northreach.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Stormwake Weave · the Perfumers' City",
}
