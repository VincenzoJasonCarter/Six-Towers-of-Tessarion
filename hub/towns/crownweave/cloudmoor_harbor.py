"""Cloudmoor Harbor: Skyloom's great western port, where mast and mooring-ring share a quay (lore-book 13)."""
TOWN = "Cloudmoor Harbor"
EPITHET = "Where Keel Meets Cloud"
BOOK = "Of Skyloom, the Loom Above"

SPEC = {
    "id": "cloudmoor-harbor", "seed": 1303, "style": "human", "corner": .1,
    "centre": (900, 560), "extent": (430, 340),
    "sea": {"dir": "W", "shore": 300, "bay": 90, "bay_width": 280, "name": "the western sea", "piers": 6, "ships": 6},
    "plaza": {"r": 40, "id": "crane-square", "at": (-60, 0)},
    "from_map": True, "names": [{"dir": 6, "id": "sapphire-road"}],
    "spokes": 7,
    "landmarks": [
        {"id": "mooring-masts", "at": (-245, -10), "size": (300, 0), "angle": 90, "kind": "masts", "count": 6, "label": "the Mooring Masts", "lab": (40, -150)},
        {"id": "aurora", "at": (-120, -80), "size": (30, 24), "angle": 4, "lab": (0, 26)},
        {"id": "crane-yard", "at": (-170, 140), "size": (90, 50), "angle": 80, "kind": "yard"},
        {"id": "harbormaster", "at": (-110, 60), "size": (46, 30), "angle": 85},
        {"id": "provision-houses", "at": (120, -150), "size": (110, 50), "angle": 8, "kind": "yard", "sheds": 3},
        {"id": "bootmakers", "at": (130, 130), "size": (40, 28), "angle": -6},
    ],
    "districts": [{"id": "high-quay", "text": "the High Quay", "at": (-205, -170), "rotate": 88, "size": 15},
                  {"id": "cobblers-row", "text": "Cobblers' Row", "at": (170, 60), "rotate": 4, "size": 15}],
    "places": [
        {"id": "mooring-masts", "name": "The Mooring Masts", "epithet": "The only quay in the Union where mast and mooring-ring share a stone",
         "text": "Tall iron masts along the quay, each crowned with a mooring-ring for skycraft. Sea-going ships tie up below; skycraft moor above; cargo is swung between them on cranes.", "source": BOOK},
        {"id": "aurora", "name": "Aurora's Rest", "epithet": "A spilled drink can cost more than a ship",
         "text": "The navigators' inn, with charts spread across every table, where captains of sea and sky compare winds and lie about routes.", "source": BOOK},
        {"id": "crane-yard", "name": "The Crane Yard", "epithet": "Where keel meets cloud",
         "text": "The great cranes that swing cargo from ship to skycraft and back, and the yard where it waits between them.", "source": BOOK},
        {"id": "harbormaster", "name": "The Harbormaster's House", "epithet": "First landfall",
         "text": "Where ships from the western sea make their first landfall in the Union and declare it, including the rare elven vessel out of Thal'vireth.", "source": BOOK},
        {"id": "provision-houses", "name": "The Provision Houses", "epithet": "Preserved, packed and labelled",
         "text": "Salting, drying and packing houses, which make the preserved provisions Cloudmoor is famous for and the Loom eats a great deal of.", "source": BOOK},
        {"id": "bootmakers", "name": "The Bootmakers' Guildhall", "epithet": "Boots and harness for those who fall for a living",
         "text": "Cloudmoor's boots and flying-harnesses are famous; this is the hall of the guild that makes them, and keeps the patterns locked up.", "source": BOOK},
        {"id": "crane-square", "name": "Crane Square", "epithet": "", "text": "The square behind the quays, where the Sapphire Road comes in and the hiring-boards for crane-crews hang."},
        {"id": "high-quay", "name": "The High Quay", "epithet": "", "text": "The long quay under the mooring-masts, with ships below and skycraft above."},
        {"id": "cobblers-row", "name": "Cobblers' Row", "epithet": "", "text": "The bootmakers' and harness-makers' street, loud with hammers from dawn."},
        {"id": "sapphire-road", "name": "The Sapphire Road", "epithet": "Instruments, glass and flight-gear",
         "text": "The road east through Chadon and Burbotford toward Central District, along which most instruments, glass and flight-gear travel.", "source": BOOK},
    ],
    "title": TOWN, "sub": "Skyloom's western port", "compass": (80, 120), "cartouche": (1380, 1020), "scale": (1180, 60),
}
