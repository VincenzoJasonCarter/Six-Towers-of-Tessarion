"""A fight: two sides on the line, initiative, and the turn loop."""
from __future__ import annotations

from .combat import deal, saving_throw
from .context import Ctx
from .dice import R, d20, roll_damage
from .impact import causes, deny
from .movement import ARENA

START = (30, 90)                       # one-on-one
FORMATION = ((30, 10), (90, 110))      # parties: (front rank, back rank) for side 0 and side 1
MAX_ROUNDS = 20


class Fight:
    """Two sides, each a creature or a list of creatures."""

    def __init__(self, a, b):
        sides = [list(a) if isinstance(a, (list, tuple)) else [a],
                 list(b) if isinstance(b, (list, tuple)) else [b]]
        self.sides = sides
        self.all = sides[0] + sides[1]
        self.zones = []
        self.watchers = [c for c in self.all if c.watches_damage]
        self.round = 0
        self.current = None
        for i, side in enumerate(sides):
            for c in side:
                c.side, c.fight, c.foe = i, self, None
        if len(sides[0]) == 1 and len(sides[1]) == 1:
            sides[0][0].x, sides[1][0].x = START
        else:
            for i, side in enumerate(sides):
                self.line_up(side, *FORMATION[i])

    @staticmethod
    def line_up(side, front, back):
        """Melee creatures in the front rank, the rest in the back, each rank
        staggered 5 feet apart around its spot: 0, +5, -5, +10, -10, ..."""
        placed = {}   # rank -> how many already stand in it
        for c in side:
            home = front if c.style == "melee" else back
            k = placed[home] = placed.get(home, -1) + 1
            off = 5 * ((k + 1) // 2) * (1 if k % 2 else -1)
            c.x = max(ARENA[0], min(ARENA[1], home + off))

    def run(self, max_rounds=MAX_ROUNDS):
        """Returns (winning side 0/1 or None for a draw, rounds)."""
        order = sorted(self.all, key=lambda c: (d20() + c.mod("dex"), R.random()), reverse=True)
        for c in order:
            c.on_initiative()
        for self.round in range(1, max_rounds + 1):
            for c in order:
                if self.over():
                    break
                if not c.dead:
                    self.turn(c)
            if self.over():
                break
        return self.winner(), self.round

    def down(self, i):
        return all(c.dead for c in self.sides[i])

    def over(self):
        return self.down(0) or self.down(1)

    def winner(self):
        if self.down(1) and not self.down(0):
            return 0
        if self.down(0) and not self.down(1):
            return 1
        return None

    def turn(self, c):
        self.current = c
        expire(self, "start", c)
        for z in list(self.zones):
            if z.owner.side != c.side and z.covers(c.x):
                z.on_enemy_turn_start(c)
        c.reaction = True
        c.bonus_used = False
        c.moved = 0
        c.turns += 1
        c.hit_this_turn = False
        c.acted = False
        c.foe = c.pick_target()
        if c.foe and not c.dead and c.incapacitated():
            deny(c, causes(c, ("paralyzed", "stunned")))
        if c.foe and not c.incapacitated() and not c.dead:
            c.take_turn()
        if not self.over():
            for z in list(self.zones):
                if z.owner.side != c.side and z.covers(c.x):
                    z.on_enemy_turn_end(c)
        if not self.over():
            end_of_turn(c)
        if not self.over() and not c.dead:
            c.on_turn_end()
        expire(self, "end", c)
        self.current = None


def expire(fight, phase, who):
    """Remove the effects that last until the start/end of `who`'s turn."""
    for c in fight.all:
        keep = []
        for e in c.effects:
            if e.until and e.until[0] == phase and e.until[1] is who:
                if not e.skip:
                    continue
                e.skip -= 1
            keep.append(e)
        c.effects = keep


def end_of_turn(c):
    """Repeated saves and delayed damage that resolve at the end of a creature's turn."""
    for e in list(c.effects):
        if c.dead:
            return
        if e.name == "paralyzed" and e.value:      # Hold: save again to break free
            abil, dc, caster = e.value
            if saving_throw(c, abil, dc, caster, Ctx(spell=True, level=2, control=True)):
                c.end_effect(e, caster)
        elif e.name == "dot":                      # Vitriolic Sphere's acid
            parts, src = e.value
            c.remove(effect=e)
            deal(c, roll_damage(parts), src, Ctx(spell=True))
