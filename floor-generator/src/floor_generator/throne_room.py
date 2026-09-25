# ---------------------------------------------------------------
# Throne room: a boss floor's centerpiece
# ---------------------------------------------------------------
#
# A stepped dais centered on the floor, not a walled room - a wall
# blocks movement/pathfinding (see pathfinding.py/obstacles.py), and
# stairs up to a throne shouldn't. So this is purely a visual marker:
# concentric square outlines shrinking toward the center, each one a
# "step" up to where the boss stands. It never touches obstacles,
# zones, or pathfinding at all - see __init__.py's
# generate_temporal_floor(throne_room=...), which only uses this for
# the decorative steps and for fixing the boss's spawn point at the
# exact center (still the far-quadrant-from-the-entrance spawn every
# other floor uses otherwise - see progression.py's place_exit_ladder).

DEFAULT_STEP_SIZES = (8, 6, 4)  # meters, outermost step first, each one a step up toward the center
STEP_COLOR = "#E8C468"  # gold - distinct from a wall's amber (see obstacles.DEFAULT_WALL_COLOR), purely decorative


def generate_throne_room(size, step_sizes=DEFAULT_STEP_SIZES):
    """The boss's throne: a world-space square outline per entry in
    step_sizes, all centered on the floor, plus the boss's spawn cell
    at the exact middle.

    Returns
    -------
    dict
        {"steps": [(x0, y0, x1, y1), ...], "spawn_cell": {"x", "y"}}
        steps are world-space square outlines, outermost (widest)
        first - purely decorative, see the module docstring.
    """

    center = size / 2
    steps = []
    for step_size in step_sizes:
        half = step_size / 2
        steps.append((center - half, center - half, center + half, center + half))

    spawn_cell = int(size) // 2 - 1  # just inside the center vertex, e.g. cell 9 for a 20 m floor
    return {"steps": steps, "spawn_cell": {"x": spawn_cell, "y": spawn_cell}}
