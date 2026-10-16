"""Moving along the 120-foot line: 5-foot steps, difficult terrain, opportunity
attacks, fear, and the walls at each end."""
from __future__ import annotations

ARENA = (0, 120)   # the walls


def move_to(c, goal, budget, provoke=True, stop_short=0):
    """Walk up to `budget` feet toward the point `goal` in 5-foot steps, stopping
    `stop_short` feet from it. Entering difficult terrain costs double, leaving
    an enemy's reach provokes an opportunity attack, and a frightened creature
    won't step closer to what frightens it. Returns feet moved."""
    if c.dead or budget <= 0:
        return 0
    step = 5 if goal > c.x else -5
    fear = c.get("frightened")
    spent = moved = 0
    while not c.dead:
        if abs(goal - c.x) <= stop_short:
            break
        new = c.x + step
        if not (ARENA[0] <= new <= ARENA[1]):
            break
        if fear and fear.source and not fear.source.dead and abs(new - fear.source.x) < abs(c.x - fear.source.x):
            break
        cost = 10 if c.in_difficult(new) else 5
        if spent + cost > budget:
            break
        if provoke:
            for e in c.enemies():
                if (abs(c.x - e.x) <= e.reach < abs(new - e.x) and e.reaction and e.can_oa
                        and not e.incapacitated()):
                    e.reaction = False
                    e.opportunity_attack(c)
                    if c.dead or c.speed_now() == 0:
                        break
            if c.dead or c.speed_now() == 0:
                break
        c.x = new
        spent += cost
        moved += 5
    c.moved += moved
    if moved:
        for e in c.enemies():
            e.on_enemy_moved(c)
    return moved


def move(c, toward, budget, provoke=True, ref=None):
    """Walk toward `ref` (default: the target) until adjacent, or straight away from it."""
    ref = ref or c.foe or c.nearest_enemy()
    if ref is None:
        return 0
    if toward:
        return move_to(c, ref.x, budget, provoke, stop_short=5)
    return move_to(c, _wall_behind(c, ref), budget, provoke)


def room_behind(c, ref=None):
    """Feet c could still back away from `ref` before hitting the wall."""
    ref = ref or c.foe or c.nearest_enemy()
    if ref is None:
        return 0
    return abs(c.x - _wall_behind(c, ref))


def _wall_behind(c, ref):
    """The wall on c's side of ref (side 0 starts on the low end)."""
    return ARENA[0] if ref.x > c.x or (ref.x == c.x and c.side == 0) else ARENA[1]


def push(c, src, feet):
    """Shove c straight away from src."""
    step = feet if c.x > src.x or (c.x == src.x and src.side == 0) else -feet
    c.x = max(ARENA[0], min(ARENA[1], c.x + step))
