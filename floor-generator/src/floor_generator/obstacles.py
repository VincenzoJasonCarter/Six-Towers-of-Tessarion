# ---------------------------------------------------------------
# Obstacle generation
# ---------------------------------------------------------------
#
# Two kinds:
#
# - "walls": a thin barrier on the LINE between two tiles, not inside
#   a tile itself - a straight run of 1+ grid edges, horizontal or
#   vertical. This is the common case: cover, chokepoints, partial
#   room dividers, without eating a whole 1x1 m of floor space.
# - "blocks": a full 1x1 m tile an obstacle occupies outright (a
#   pillar, rubble pile, etc.) - the minority case, kept rare on
#   purpose so most of the battlefield still reads as open floor
#   carved up by walls rather than dotted with solid tiles.
#
# Both kinds block movement in the combat sim too (attempt_move in
# dnd/combat.py routes around them via pathfinding.find_path -
# neither the sim nor this generator has real "sufficient safe
# space"/full-map reachability validation yet, matching CLAUDE.md's
# still-open validation-rules list, but generation here does
# guarantee one thing: no wall or block is ever placed if it would
# fully sever the entrance from the exit (see _connects_entrance_exit
# below), so a floor is never physically unsolvable.

from .pathfinding import find_path

DEFAULT_WALL_COLOR = "#D9A521"  # yellowish/amber - reads clearly against the gray stone texture and the blue/red zones
DEFAULT_BLOCK_COLOR = "#4A4A4A"

# How many connected straight runs make up one wall structure (see
# _generate_wall_chain) - 1 is a plain single-segment wall like
# before, 2-3 turns a corner into an L or a dogleg, which is what
# makes a chain read as an actual wall/corridor instead of a lone dash.
WALL_CHAIN_LENGTH_RANGE = (1, 3)


def _wall_touches_cell(x1, y1, x2, y2, cell_x, cell_y):
    """True if the wall segment runs along any edge of the (cell_x,
    cell_y) grid cell - used to keep obstacles off the entrance/exit
    cell, so at least that one tile is never boxed in by the very
    generation pass that placed it."""

    cx0, cy0, cx1, cy1 = cell_x, cell_y, cell_x + 1, cell_y + 1

    if y1 == y2 and y1 in (cy0, cy1):  # horizontal wall on the cell's top/bottom edge
        return not (x2 <= cx0 or x1 >= cx1)
    if x1 == x2 and x1 in (cx0, cx1):  # vertical wall on the cell's left/right edge
        return not (y2 <= cy0 or y1 >= cy1)
    return False


def _generate_wall_chain(rng, size, wall_length_range, chain_length_range=WALL_CHAIN_LENGTH_RANGE):
    """A connected run of straight wall segments, turning 90 degrees
    at the end of each one, so the result reads as an actual wall (or
    a dogleg corridor) instead of a lone floating dash - and, since it
    alternates horizontal/vertical by construction, a multi-segment
    chain always includes both orientations rather than leaving one
    of them up to chance across the whole floor.

    The walk can end early (yielding fewer than chain_length_range
    segments, possibly just one) if it steps off the interior grid or
    a segment would have zero length - that's fine, a shorter wall
    structure is still a valid one.
    """

    horizontal = rng.choice([True, False])

    if horizontal:
        y = rng.randint(1, size - 1)  # interior grid lines only - the floor boundary is already a wall
        x = rng.randint(0, size)
    else:
        x = rng.randint(1, size - 1)
        y = rng.randint(0, size)

    segments = []

    for _ in range(rng.randint(*chain_length_range)):

        length = rng.randint(*wall_length_range)
        direction = rng.choice((1, -1))

        if horizontal:
            if not (1 <= y <= size - 1):
                break
            nx = max(0, min(size, x + direction * length))
            if nx == x:
                break
            x1, x2 = sorted((x, nx))
            segments.append({"x1": x1, "y1": y, "x2": x2, "y2": y})
            x = nx
        else:
            if not (1 <= x <= size - 1):
                break
            ny = max(0, min(size, y + direction * length))
            if ny == y:
                break
            y1, y2 = sorted((y, ny))
            segments.append({"x1": x, "y1": y1, "x2": x, "y2": y2})
            y = ny

        horizontal = not horizontal  # turn the corner for the next segment

    return segments


def generate_obstacles(size, zones, entrance_door, exit_ladder, rng, n_walls=10, wall_length_range=(1, 3), n_blocks=3):
    """Roll wall segments (edge obstacles) and a handful of full-tile
    blocks onto the floor.

    Parameters
    ----------
    size : int
        Floor dimensions in meters.

    zones : list[dict]
        Already-placed temporal zones (see zones.py). Blocks avoid
        overlapping them (a solid obstacle sitting inside a temporal
        field would be an odd double-hazard); walls are allowed to
        run along or through a zone - a wall inside a temporal field
        is a fine detail.

    entrance_door, exit_ladder : dict
        Door/ladder placements (see progression.py). Obstacles avoid
        their cell so neither spawn point is boxed in on the very
        seed that placed it.

    rng : random.Random
        Seeded RNG to draw from.

    n_walls : int
        Number of wall structures to place - each is a connected
        chain of 1-3 straight segments (see _generate_wall_chain), so
        the actual segment count in the returned list runs higher
        than n_walls.

    wall_length_range : tuple(int, int)
        (min, max) length in grid edges for each straight segment
        within a wall structure.

    n_blocks : int
        Number of full-tile obstacles to place.

    Returns
    -------
    dict
        {"walls": [{"x1", "y1", "x2", "y2"}], "blocks": [{"x", "y", "w", "h"}]}
        Wall coordinates are grid-line points (0..size); a horizontal
        wall has y1 == y2, a vertical wall has x1 == x2. Blocks are
        1x1 m cells, same shape as a zone dict minus "type". The
        entrance and exit cells are always mutually reachable through
        whatever's returned here - see the module docstring.
    """

    entrance_cell = (int(entrance_door["x"]), int(entrance_door["y"]))
    exit_cell = (int(exit_ladder["x"]), int(exit_ladder["y"]))

    obstacles = {"walls": [], "blocks": []}
    walls = obstacles["walls"]
    blocks = obstacles["blocks"]

    def _connects_entrance_exit():
        return find_path(entrance_cell, exit_cell, size, obstacles) is not None

    n_chains_placed = 0
    attempts = 0
    max_attempts = 2000

    while n_chains_placed < n_walls and attempts < max_attempts:

        attempts += 1

        chain = _generate_wall_chain(rng, size, wall_length_range)

        if not chain:
            continue
        if any(
            _wall_touches_cell(s["x1"], s["y1"], s["x2"], s["y2"], *entrance_cell)
            or _wall_touches_cell(s["x1"], s["y1"], s["x2"], s["y2"], *exit_cell)
            for s in chain
        ):
            continue

        walls.extend(chain)
        if _connects_entrance_exit():
            n_chains_placed += 1
        else:
            del walls[-len(chain):]

    attempts = 0

    while len(blocks) < n_blocks and attempts < max_attempts:

        attempts += 1

        x = rng.randint(0, size - 1)
        y = rng.randint(0, size - 1)

        if (x, y) in (entrance_cell, exit_cell):
            continue
        if any(z["x"] <= x < z["x"] + z["w"] and z["y"] <= y < z["y"] + z["h"] for z in zones):
            continue
        if any(b["x"] == x and b["y"] == y for b in blocks):
            continue

        blocks.append({"x": x, "y": y, "w": 1, "h": 1})
        if not _connects_entrance_exit():
            blocks.pop()

    return obstacles
