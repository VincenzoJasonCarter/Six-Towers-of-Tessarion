"""Caer Veyn, seat of Stormwake and the Union's capital of record: the harbour city (lore-book 16)."""
TOWN = "Caer Veyn"
EPITHET = "Seat of the Weave, and capital of record of the Union"
BOOK = "Of Stormwake, the Open Harbor of the East"

SPEC = {
    "id": "caer-veyn", "seed": 1605, "style": "human", "density": 1.15,
    "centre": (640, 640), "extent": (470, 360),
    # the Harbor Shore turns south into the Wakewater here: the sea lies north-east
    "sea": {"dir": "NE", "shore": 300, "bay": 120, "bay_width": 260, "name": "the Wakewater", "piers": 7, "ships": 7},
    "plaza": {"r": 44, "id": "customs-square", "at": (-20, 10)},
    "from_map": True, "names": [{"dir": 63, "id": "marlney-path"}],
    "spokes": 8,
    "landmarks": [
        {"id": "tidecall", "at": (150, -150), "size": (150, 80), "angle": -45, "kind": "open", "lab": (-50, 70), "lsize": 15},
        {"id": "saltbond", "at": (-60, -200), "size": (110, 52), "angle": -45, "fill": "#b8ab90", "lab": (-60, -35)},
        {"id": "keel-knot", "at": (60, -60), "size": (26, 20), "angle": -45, "lab": (0, 26)},
        {"id": "mooring-bell", "at": (300, 30), "size": (18, 18), "kind": "round", "lab": (0, 24)},
        {"id": "potteries", "at": (-260, 120), "size": (120, 64), "angle": 10, "kind": "yard", "sheds": 3},
        {"id": "ink-works", "at": (90, 180), "size": (70, 40), "angle": -20, "fill": "#3e3a3a"},
        {"id": "wardens-hall", "at": (-110, 40), "size": (60, 40), "angle": -10},
    ],
    "districts": [{"id": "breakwater-row", "text": "Breakwater Row", "at": (215, -10), "rotate": -45, "size": 15},
                  {"id": "counting-houses", "text": "the Counting-Houses", "at": (-200, -70), "rotate": -20, "size": 15}],
    "places": [
        {"id": "tidecall", "name": "The Tidecall Exchange", "epithet": "Where cargo becomes claim",
         "text": "A broad stone concourse at the heart of the inner harbour, built low and wide and sloping toward the water, with brass tide-markers set into its paving. At high tide it is chaos made orderly; by low tide it empties. Once cargo leaves the Tidecall under seal, its story has officially begun.", "source": BOOK},
        {"id": "saltbond", "name": "The Saltbond Vaults", "epithet": "Stone remembers what water forgets",
         "text": "Bonded warehouses behind thick walls of pale granite, under dwarven charter and Crownweave writ, each door layered with locks, runic wards and lead-plate contracts. Neutral ground: those who break the peace inside find their accounts frozen and their names circulated among the dockmasters.", "source": BOOK},
        {"id": "breakwater-row", "name": "Breakwater Row", "epithet": "The market that shifts with the tide",
         "text": "Less a street than a habit, parallel to the outer quay: stalls put up at dawn and taken down by nightfall, selling foreign potions labelled in three languages and one approximation, wands with carefully vague instructions, and reagents too valuable to discard. No map shows it the same way twice, this one included.", "source": BOOK},
        {"id": "mooring-bell", "name": "The Mooring Bell Shrine", "epithet": "A prayer before the ropes are cast off",
         "text": "A single bronze bell on a weathered timber frame by the easternmost pier: rung once for safe arrival, twice for safe departure, or not at all. Coloured threads are tied to the frame, blue for calm seas, green for profit, red for return.", "source": BOOK},
        {"id": "keel-knot", "name": "The Keel & Knot", "epithet": "Eat well, listen better, leave quietly",
         "text": "A narrow tavern tucked beneath an overhanging warehouse a short walk from the Tidecall, its tables bolted to the floor. Old Sera Vant keeps the house's memory behind the bar, and writes nothing down.", "source": BOOK},
        {"id": "potteries", "name": "The Jar Potteries", "epithet": "Shipping jars and amphorae by the thousand",
         "text": "Kilns and drying-yards on the town's landward side, where the Union's shipping jars are thrown.", "source": BOOK},
        {"id": "ink-works", "name": "The Ink-Works", "epithet": "Veyn black",
         "text": "Where Veyn black is made: the ink of nearly every manifest, bill of lading and customs seal in the Union. Clerks elsewhere will refuse a manifest written in anything else; it is said Caer Veyn's true export is paperwork.", "source": BOOK},
        {"id": "wardens-hall", "name": "The Hall of Record", "epithet": "Where foreign disputes arrive first",
         "text": "The Weave Warden's hall, and by an old quirk of maritime law the seat named on every foreign ship's papers and every treaty sealed at sea. Foreign disputes are heard here, and frequently settled before anyone in the Hall of the Woven Crown has to hear of them.", "source": BOOK},
        {"id": "customs-square", "name": "Customs Square", "epithet": "", "text": "The square where the Marlney Path comes into town, ringed by the offices that will want to see your papers."},
        {"id": "counting-houses", "name": "The Counting-Houses", "epithet": "", "text": "Cargo yards and counting-houses on the inner docks, stacked with goods awaiting inspection.", "source": BOOK},
        {"id": "marlney-path", "name": "The Marlney Path", "epithet": "", "text": "One of the paths that link the Harbor Shore's towns to one another.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Seat of Stormwake · capital of record", "cartouche": (230, 1020), "scale": (1320, 1050),
}
