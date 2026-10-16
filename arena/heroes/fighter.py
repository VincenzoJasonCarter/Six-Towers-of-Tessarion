"""The martial chassis the Aegisbound and Range are built on.

Tessarion's own progression (the class sheet linked from lore-book Ch.2): one
attack per turn at every level, and none of the 5e Fighter's Action Surge,
Second Wind or Indomitable. Damage grows only through the weapon, Resonance
Rank and subclass features.

The bot: melee heroes close in (dashing when they can't reach) and attack the
most hurt enemy in reach; guards hold the line in front of the back rank;
shooters kite (Creature.keep_distance).
"""
from dataclasses import dataclass

from engine import Ctx, Dice, attack, d20, mod, move, move_to, p_hit

from .base import Hero, scores_at

AEGIS_BASE = dict(str=16, dex=10, con=14, int=8, wis=12, cha=10)
RANGE_BASE = dict(str=10, dex=16, con=14, int=8, wis=12, cha=10)
ASI_LEVELS = (4, 6, 8, 12, 14, 16, 19)


@dataclass(frozen=True)
class Weapon:
    name: str
    n: int                       # damage dice
    die: int
    kind: str                    # "melee" | "ranged"
    normal: int                  # normal range (or reach)
    long: int                    # long range: disadvantage beyond normal
    dtype: str = "piercing"
    bonus: int = 0               # the item's own damage bonus (Tier 2 gear)
    misfire: str | None = None   # a natural 1 fouls it; clearing costs an "action" or a "bonus" action
    heavy_draw: bool = False     # half speed on a turn it fires
    no_long_dis: bool = False    # no disadvantage at long range


class Fighter(Hero):
    chassis = "Fighter"
    ranged = False
    weapon: Weapon = None

    def __init__(self, level, gear=False):
        primary = "dex" if self.ranged else "str"
        sc = scores_at(RANGE_BASE if self.ranged else AEGIS_BASE, primary, level, ASI_LEVELS)
        con = mod(sc["con"])
        hp = 10 + con + (level - 1) * (6 + con)
        super().__init__(level, sc, ("str", "con"), hp, self.armor(level, sc))
        self.atk_bonus = self.mod(primary) + self.pb + self.item + (2 if self.ranged else 0)   # Archery style
        self.dmg_bonus = self.mod(primary) + self.item
        self.action = True
        self.fouled = set()   # names of weapons a misfire has put out of action

    def armor(self, level, sc):
        raise NotImplementedError

    def est_dpr(self, target):
        w = self.weapon
        return p_hit(self.atk_bonus, target.ac()) * (w.n * (w.die + 1) / 2 + self.dmg_bonus + w.bonus)

    def reach_of_attacks(self):
        return self.weapon.normal if self.ranged else self.reach

    # ----- attacking ---------------------------------------------------------------
    def weapon_attack(self, tgt, ctx=None):
        w = self.weapon
        dis = w.kind == "ranged" and self.dist_to(tgt) > w.normal and not self.ignores_long_range()
        parts = [Dice(w.n, w.die, w.dtype, self.dmg_bonus + w.bonus)]
        self.last_natural = 0
        out = attack(self, tgt, bonus=self.atk_bonus, parts=parts, kind=w.kind,
                     magical=self.item > 0, weapon=w.name, dis=dis, ctx=ctx)
        if w.misfire and self.last_natural == 1:
            self.fouled.add(w.name)
        return out

    def ignores_long_range(self):
        return self.weapon.no_long_dis

    def can_attack(self):
        if self.foe is None or self.foe.dead:
            return False
        if self.weapon.kind == "melee":
            return self.dist() <= self.reach
        return self.dist() <= self.weapon.long

    def retarget(self):
        """After a kill: the next enemy this turn's attacks can still reach."""
        if self.foe is not None and not self.foe.dead:
            return True
        self.foe = self.pick_target()
        return self.can_attack()

    def opportunity_attack(self, tgt):
        if self.weapon.kind == "melee":
            self.weapon_attack(tgt, Ctx(oa=True))

    # ----- the turn ----------------------------------------------------------------------
    def take_turn(self):
        self.action = True
        if self.has("restrained") and not self.ranged:
            self.try_escape()
        self.pre_bonus()
        if self.ranged:
            self.keep_distance()
        else:
            self.close_in()
        if self.action and self.can_attack():
            self.action = False
            self.main_action()
        if not self.dead and self.enemies():
            self.retarget()
            if self.foe:
                self.post_bonus()
                if self.ranged:
                    self.keep_distance()   # e.g. step off a foe the shot just rooted

    def try_escape(self):
        """Spend the action breaking out of a restraint that allows it."""
        e = self.get("restrained")
        if e and e.value and e.value[0] == "escape":
            self.action = False
            if d20() + self.mod("str") + self.pb >= e.value[1]:
                self.end_effect(e, e.source)

    def close_in(self):
        sp = self.speed_now()
        if sp == 0 or self.dist() <= self.reach:
            return
        ward = self.ward_ally() if self.guard else None
        if ward:
            # Hold the line: engage what's coming for the back rank, otherwise
            # stand just in front of it.
            if self.dist() - self.reach > sp + 5 and self.foe.dist_to(ward) > 15:
                front = 5 if self.foe.x > ward.x else -5
                move_to(self, ward.x + front, sp)
                return
        move(self, True, sp)
        if self.dist() > self.reach and self.action and self.speed_now():
            self.action = False   # Dash
            move(self, True, sp)

    def main_action(self):
        """The action: one attack, unless a subclass has something better."""
        if not self.dead and self.retarget():
            self.one_attack()

    def one_attack(self):
        self.weapon_attack(self.foe)

    def pre_bonus(self):
        """Bonus action before moving."""

    def post_bonus(self):
        """Bonus action after the action."""
