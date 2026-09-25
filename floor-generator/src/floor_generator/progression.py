# ---------------------------------------------------------------
# Floor progression: entrance door + exit ladder
# ---------------------------------------------------------------

DOOR_COLOR = "#8B5A2B"
LADDER_COLOR = "#C9A66B"


def point_in_any_zone(x, y, zones):
    return any(
        z["x"] <= x < z["x"] + z["w"] and z["y"] <= y < z["y"] + z["h"]
        for z in zones
    )


def place_entrance_door(size, zones, rng):
    """Pick a boundary-wall cell for the entrance door that doesn't
    fall inside a temporal zone."""

    for _ in range(2000):

        edge = rng.choice(["N", "S", "E", "W"])

        if edge in ("S", "N"):
            x = rng.randint(0, size - 1)
            y = 0 if edge == "S" else size - 1
        else:
            y = rng.randint(0, size - 1)
            x = 0 if edge == "W" else size - 1

        if not point_in_any_zone(x, y, zones):
            return {"x": x, "y": y, "edge": edge}

    raise RuntimeError("Could not place entrance door.")


def place_exit_ladder(size, zones, rng, entrance):
    """Pick a cell for the exit ladder - and therefore the monster's
    combat spawn (see engine.py/combat.py) - on the far side of the
    floor from the entrance door.

    Every valid cell (not inside a zone, not the door itself) is
    ranked by distance from the entrance, and one is picked at random
    from the farthest quarter. That keeps placement seed-varied while
    guaranteeing the monster starts clear across the room instead of
    a step or two from where the player walks in - closing that gap
    is meant to be part of the fight, not skipped.
    """

    candidates = []
    for x in range(size):
        for y in range(size):
            if (x, y) == (entrance["x"], entrance["y"]):
                continue
            if point_in_any_zone(x, y, zones):
                continue
            dist = ((x - entrance["x"]) ** 2 + (y - entrance["y"]) ** 2) ** 0.5
            candidates.append((dist, x, y))

    if not candidates:
        raise RuntimeError("Could not place exit ladder.")

    candidates.sort(key=lambda c: c[0], reverse=True)
    far_pool = candidates[: max(1, len(candidates) // 4)]
    _, x, y = rng.choice(far_pool)
    return {"x": x, "y": y}


def door_world_rect(entrance_door, size, thickness=0.15):
    """World-space (x, y, w, h) footprint of the entrance door, as a
    thin rectangle set into the relevant boundary wall."""

    x, y, edge = entrance_door["x"], entrance_door["y"], entrance_door["edge"]

    if edge == "S":
        return (x, 0, 1, thickness)
    if edge == "N":
        return (x, size - thickness, 1, thickness)
    if edge == "W":
        return (0, y, thickness, 1)
    return (size - thickness, y, thickness, 1)  # E


def ladder_world_rect(exit_ladder, inset=0.15):
    """World-space (x, y, w, h) footprint of the exit ladder marker,
    inset within its floor tile."""

    x, y = exit_ladder["x"], exit_ladder["y"]
    side = 1 - 2 * inset
    return (x + inset, y + inset, side, side)


def entrance_spawn_point(entrance_door):
    """World-space (x, y) where a creature entering through this door
    should stand.

    entrance_door["x"]/["y"] are cell indices (0..size-1), not world
    coordinates - a door on the S/W wall sits at index 0. Spawning a
    token at that raw index put its center exactly on the floor's
    boundary line, so half the token rendered outside the drawn grid.
    Using the cell's center instead keeps every spawn a half-meter
    inside the wall, regardless of which edge the door is on.
    """
    return (entrance_door["x"] + 0.5, entrance_door["y"] + 0.5)


def exit_spawn_point(exit_ladder):
    """World-space (x, y) at the center of the exit ladder's cell (see
    entrance_spawn_point - same reasoning, the ladder's x/y are cell
    indices, not a ready-to-use world position)."""
    return (exit_ladder["x"] + 0.5, exit_ladder["y"] + 0.5)
