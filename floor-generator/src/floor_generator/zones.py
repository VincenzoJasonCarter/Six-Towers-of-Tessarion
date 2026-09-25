# ---------------------------------------------------------------
# Zone generation
# ---------------------------------------------------------------
#
# There are only two placed zone types, matching the design doc:
# ACC and DEC. Every tile that isn't inside one of them is implicitly
# "neutral" floor — plain stone texture, no tint, no label — rather
# than a zone type of its own.
#
# Each entry in a zone type registry controls how a zone type is
# rolled, textured and labeled. Pass a custom `zone_types` dict to
# generate_temporal_floor() to add/remove/override types without
# touching the generator logic.
#
# "multiplier" is the fixed initiative multiplier applied to anyone
# standing in the zone when it fires (e.g. ACC doubles initiative,
# DEC halves it). Leave it None for a custom zone type that shouldn't
# affect initiative.

DEFAULT_ZONE_TYPES = {
    "ACC": {
        "color": "#3B82F6",
        "multiplier": 2.0,
        "texture_alpha": 0.4,
    },
    "DEC": {
        "color": "#EF4444",
        "multiplier": 0.5,
        "texture_alpha": 0.4,
    },
}

DEFAULT_ZONE_WEIGHTS = {
    "ACC": 0.5,
    "DEC": 0.5,
}


def zone_label(zone_type, cfg):
    multiplier = cfg.get("multiplier")
    if multiplier is None:
        return zone_type
    return f"{zone_type} ×{multiplier:g}"


def _allocate_zone_types(n_zones, type_names, zone_weights, rng):
    """Decide, up front, which zone type each of the n_zones slots
    will be - as a shuffled list, so placement order doesn't bias
    which type tends to land first.

    When both ACC and DEC are among type_names, their counts are
    forced equal rather than left to independent weighted rolls -
    per the design doc, deceleration and acceleration are the same
    temporal authority pointed in opposite directions, so a floor
    that rolls e.g. 4 ACC zones and 1 DEC zone undersells that
    symmetry. Any other custom zone type (e.g. a future corrupted
    type) still gets its weighted share of the remaining slots
    first; ACC/DEC then split what's left evenly.

    If what's left for ACC/DEC is odd (e.g. the generator's own
    n_zones=5 default), the leftover slot is dropped rather than
    handed to either side - awarding it to one type by RNG would mean
    "equal counts" only held on average across seeds, not on every
    floor. The returned queue is then one shorter than n_zones; the
    caller places exactly len(type_queue) zones.
    """

    if not ("ACC" in type_names and "DEC" in type_names):
        weights = [zone_weights.get(t, 1) for t in type_names]
        return rng.choices(type_names, weights=weights, k=n_zones)

    other_types = [t for t in type_names if t not in ("ACC", "DEC")]
    assigned = []

    if other_types:
        other_weight_total = sum(zone_weights.get(t, 1) for t in other_types)
        acc_dec_weight_total = zone_weights.get("ACC", 1) + zone_weights.get("DEC", 1)
        total_weight = other_weight_total + acc_dec_weight_total
        for t in other_types:
            share = zone_weights.get(t, 1) / total_weight
            assigned.extend([t] * round(share * n_zones))
        assigned = assigned[:n_zones]

    remaining = n_zones - len(assigned)
    half = remaining // 2
    assigned.extend(["ACC"] * half)
    assigned.extend(["DEC"] * half)

    rng.shuffle(assigned)
    return assigned


def generate_zones(size, zone_size_range, n_zones, min_zone_gap, zone_types, zone_weights, rng):
    """Roll non-overlapping ACC/DEC zones onto the floor.

    Parameters
    ----------
    size : int
        Floor dimensions in meters.

    zone_size_range : tuple(int, int)
        (min, max) width/height in meters for each zone. Width and
        height are rolled independently, so zones need not be square.

    n_zones : int
        Target number of zones to place. When ACC and DEC are both
        in zone_types and n_zones is odd, one fewer zone is actually
        placed (see _allocate_zone_types) so the ACC/DEC counts come
        out exactly equal rather than off by one.

    min_zone_gap : int
        Minimum empty space between zones.

    zone_types : dict
        Zone type registry (see DEFAULT_ZONE_TYPES).

    zone_weights : dict
        Relative weight per zone type key. Ignored between ACC and
        DEC specifically when both are present - see
        _allocate_zone_types() - but still honored for any other
        zone type in the registry.

    rng : random.Random
        Seeded RNG to draw from.

    Returns
    -------
    list[dict]
        Zones as {"x", "y", "w", "h", "type"}.
    """

    type_names = list(zone_types.keys())
    type_queue = _allocate_zone_types(n_zones, type_names, zone_weights, rng)

    zones = []
    attempts = 0
    max_attempts = 5000

    while len(zones) < len(type_queue) and attempts < max_attempts:

        attempts += 1

        w = rng.randint(*zone_size_range)
        h = rng.randint(*zone_size_range)

        if w > size or h > size:
            continue

        x = rng.randint(0, size - w)
        y = rng.randint(0, size - h)

        zone_type = type_queue[len(zones)]

        candidate = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "type": zone_type,
        }

        # Check overlap / minimum distance
        valid = True

        for zone in zones:

            zx = zone["x"]
            zy = zone["y"]
            zw = zone["w"]
            zh = zone["h"]

            if (
                x < zx + zw + min_zone_gap
                and
                x + w + min_zone_gap > zx
                and
                y < zy + zh + min_zone_gap
                and
                y + h + min_zone_gap > zy
            ):
                valid = False
                break

        if valid:
            zones.append(candidate)

    # _allocate_zone_types pre-balances ACC/DEC, but a tightly packed
    # floor can still exhaust max_attempts before every pre-allocated
    # slot finds room - if that truncation happens to land on more
    # ACC than DEC placements (or vice versa), drop the extra one(s)
    # from the majority side rather than ship an unequal floor.
    if "ACC" in type_names and "DEC" in type_names:
        acc = [z for z in zones if z["type"] == "ACC"]
        dec = [z for z in zones if z["type"] == "DEC"]
        if len(acc) != len(dec):
            keep = min(len(acc), len(dec))
            drop = set(id(z) for z in (acc[keep:] + dec[keep:]))
            zones = [z for z in zones if id(z) not in drop]

    return zones
