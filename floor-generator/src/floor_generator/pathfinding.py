# ---------------------------------------------------------------
# Obstacle-aware grid pathfinding
# ---------------------------------------------------------------
#
# Turns a floor's obstacles (see obstacles.py) into a navigable grid:
# a "block" removes a cell outright (nothing can stand there or pass
# through it); a "wall" removes the edge between the two cells it
# sits between (it's on the line, so it only ever blocks crossing
# that one line - it never removes a cell). Used by both the
# obstacle generator itself (to make sure a wall/block placement
# never seals the entrance off from the exit) and the combat sim's
# movement (attempt_move in dnd/combat.py), so a creature's move
# routes around obstacles instead of clipping through them.
#
# Movement is cardinal-only (N/S/E/W) - no diagonals. A diagonal step
# would need a "don't cut the corner" rule (both flanking cells open,
# neither flanking edge walled) to avoid slicing across a wall corner,
# but the two wall segments that meet at an L-shaped corner (see
# obstacles.py's wall chains) are still visually right there at that
# shared vertex - a diagonal glide passing through it reads as
# clipping the wall even on a technically-legal move. Cardinal-only
# movement sidesteps the whole issue: every step is either fully open
# or fully blocked, with no corner case to get subtly wrong.
#
# Cells are (x, y) integer grid-cell coordinates (0..size-1), not the
# float world positions combatants stand at - dnd/combat.py converts
# at the edges (math.floor(pos) in, cell-center pos out).

from collections import deque

CARDINAL_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def blocked_cells(obstacles):
    """Every grid cell a full-tile obstacle occupies."""
    cells = set()
    for block in obstacles.get("blocks", []):
        for dx in range(block["w"]):
            for dy in range(block["h"]):
                cells.add((block["x"] + dx, block["y"] + dy))
    return cells


def wall_blocks_edge(cell_a, cell_b, walls):
    """True if a wall segment sits on the shared edge between two
    orthogonally adjacent cells. Not meaningful (and always False)
    for a non-adjacent pair."""

    ax, ay = cell_a
    bx, by = cell_b

    if ax == bx and abs(ay - by) == 1:
        # Shared edge is the horizontal grid line at the higher of
        # the two rows, spanning one unit of x starting at ax.
        y = max(ay, by)
        return any(w["y1"] == w["y2"] == y and w["x1"] <= ax < w["x2"] for w in walls)

    if ay == by and abs(ax - bx) == 1:
        # Shared edge is the vertical grid line at the higher of the
        # two columns, spanning one unit of y starting at ay.
        x = max(ax, bx)
        return any(w["x1"] == w["x2"] == x and w["y1"] <= ay < w["y2"] for w in walls)

    return False


def _passable_neighbors(cell, size, blocked, walls):
    x, y = cell
    for dx, dy in CARDINAL_STEPS:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < size and 0 <= ny < size) or (nx, ny) in blocked:
            continue
        if wall_blocks_edge(cell, (nx, ny), walls):
            continue
        yield (nx, ny)


def find_path(start_cell, goal_cell, size, obstacles):
    """Shortest cardinal-only route from start_cell to goal_cell over
    the grid, routing around walls and blocks (plain BFS - every step
    costs the same 1 m, so there's no need for Dijkstra's weighting).

    Returns a list of cells from (but excluding) start_cell to
    (including) goal_cell - so `[]` means start_cell == goal_cell,
    already there - or None if goal_cell isn't reachable at all.
    """

    if start_cell == goal_cell:
        return []

    blocked = blocked_cells(obstacles)
    walls = obstacles.get("walls", [])

    prev = {}
    visited = {start_cell}
    queue = deque([start_cell])

    while queue:
        cell = queue.popleft()
        if cell == goal_cell:
            break
        for ncell in _passable_neighbors(cell, size, blocked, walls):
            if ncell in visited:
                continue
            visited.add(ncell)
            prev[ncell] = cell
            queue.append(ncell)

    if goal_cell not in prev:
        return None

    path = []
    cur = goal_cell
    while cur != start_cell:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def is_connected(start_cell, goal_cell, size, obstacles):
    return find_path(start_cell, goal_cell, size, obstacles) is not None
