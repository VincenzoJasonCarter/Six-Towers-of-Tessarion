"""The three Aegisbound subclasses (lore-book/05-subclasses-skill.md): Strength,
longsword and shield, Defense fighting style."""
from engine import Ctx, Dice, Zone, d, d20, saving_throw

from .fighter import Fighter, Weapon

LONGSWORD = Weapon("longsword", 1, 8, "melee", 5, 5, dtype="slashing")


class Aegis(Fighter):
    """Every Aegisbound: a d12 hit die, and from 5th level Reinforced Plating."""
    weapon = LONGSWORD

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.max_hp += 2 + (level - 1)   # d12 instead of d10: +2 at 1st level, +1 a level on average
        self.hp = self.max_hp

    def armor(self, level, sc):
        body = 16 if level < 5 else 18   # chain mail, then plate
        return body + 2 + 1              # shield, Defense

    def reduce_damage(self, dmg, src, ctx):
        """Reinforced Plating: a weapon attack that hits loses the proficiency bonus off its damage."""
        if not (self.level >= 5 and ctx.attack and not ctx.spell):
            return dmg
        cut = self.pb
        for k in sorted(dmg, key=dmg.get, reverse=True):
            take = min(cut, max(0, dmg[k]))
            dmg[k] -= take
            cut -= take
            if not cut:
                break
        return dmg


# =================================================================================
# Sanguine Aegis: Blood Charges, Blood Lure, Red Pact, Leeching Strikes,
# Scent of Blood, Hunger of the Armor, Overdrive
# =================================================================================

class SanguineAegis(Aegis):
    key, label = "sanguine_aegis", "Sanguine Aegis"
    heals = True

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.charges = 0
        self.max_charges = max(1, self.mod("con") + self.pb)
        self.overdrive = False
        self.overdrive_ready = level >= 15
        self.leeched_turn = -1
        self.hit_since = True     # landed a melee hit since the end of its last turn

    def gain(self, n):
        self.charges = min(self.max_charges, self.charges + n)

    def on_initiative(self):
        if self.level >= 7 and self.charges == 0:
            self.gain(self.pb)

    def pre_bonus(self):
        if self.overdrive:
            self.gain(1)
        if self.overdrive_ready:
            self.overdrive_ready = False
            self.overdrive = True
            self.bonus_used = True
            return
        if self.hp < 0.4 * self.max_hp and self.charges:
            self.bonus_used = True
            self.heal(d(self.charges, 6))   # spend every charge: a d6 each
            self.charges = 0

    def lures(self, c):
        """Blood Lure: with a Blood Charge in the armor, enemies within 10 feet are drawn to me."""
        return self.charges > 0 and not self.dead and self.dist_to(c) <= 10

    def my_attack_adv(self, tgt, ctx):
        scent = self.level >= 10 and ctx.kind == "melee" and tgt.hp < tgt.max_hp / 2   # Scent of Blood
        return scent, False

    def bonus_damage(self, tgt, ctx):
        out = []
        if ctx.kind == "melee" and ctx.weapon:
            if self.overdrive:
                out.append(Dice(1, 8, "necrotic"))
            if self.level >= 7 and self.charges:
                pact = min(self.charges, self.level // 2)   # Red Pact, spent as the hit lands
                self.charges -= pact
                out.append(Dice(pact, 6, "necrotic"))
                ctx.pact = pact
        return out

    def on_hit(self, tgt, ctx, crit):
        if ctx.kind != "melee" or not ctx.weapon:
            return
        self.hit_since = True
        self.gain(2 if crit else 1)
        if ctx.pact and not tgt.dead:   # Red Pact frightens
            dc = 8 + self.pb + self.mod("con")
            if not saving_throw(tgt, "con", dc, self, Ctx(fear=True, control=True)):
                tgt.add("frightened", self, **self.until_my_next_end())

    def on_damage_dealt(self, tgt, amount, ctx):
        # Leeching Strikes: heal by the proficiency bonus, once a turn.
        if ctx.kind == "melee" and ctx.weapon and self.leeched_turn != self.turns and self.my_turn():
            self.leeched_turn = self.turns
            self.heal(self.pb)

    def on_turn_end(self):
        # Hunger of the Armor: a turn without a hit, and the armor may turn on its wearer.
        if self.level >= 10 and not self.hit_since:
            if d20() + self.save_bonus("wis") < 13:
                self.add("hunger", self, until=("end", self), skip=1)
        self.hit_since = False


# =================================================================================
# Bulwark Aegis: Living Wall, Anchored Stance, Unmoving Bastion,
# Intercepting Guard, Fortress
# =================================================================================

class BulwarkAegis(Aegis):
    key, label = "bulwark", "Bulwark Aegis"
    guard = True

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.base_ac += 1          # Living Wall
        self.fortress_ready = level >= 15
        self.immovable = level >= 7

    def on_turn_end(self):
        if self.moved <= 10:
            self.add("anchored", self, until=("start", self))   # Anchored Stance

    def resists(self, dtype, ctx, nonmagical):
        return self.has("fortress") or (self.has("anchored") and nonmagical)

    def ally_attacked(self, att, ally, ctx):
        # Living Wall: an attack on someone next to me is made with disadvantage.
        if self.reaction and not self.incapacitated() and self.dist_to(ally) <= 5 and att is not self:
            self.reaction = False
            return True
        return False

    def aura_ac(self, ally):
        bonus = 0
        if self.level >= 7 and self.dist_to(ally) <= 10:
            bonus += 2 if self.level >= 15 else 1   # Unmoving Bastion
        if self.has("fortress") and self.dist_to(ally) <= 10:
            bonus += 2                               # Fortress: half cover
        return bonus

    def aura_save_bonus(self, ally, abil):
        return 2 if self.has("fortress") and abil == "dex" and self.dist_to(ally) <= 10 else 0

    def intercept(self, ally, dmg, src, ctx):
        # Intercepting Guard: step in and take a big hit meant for someone within 10 feet.
        total = sum(dmg.values())
        if (self.level >= 10 and self.reaction and not self.incapacitated() and self.dist_to(ally) <= 10
                and (total >= 10 or total >= ally.hp) and self.hp > 0.3 * self.max_hp
                and (ctx.attack or ctx.single)):
            self.reaction = False
            self.x = ally.x
            return True
        return False

    def main_action(self):
        if (self.fortress_ready and self.dist() <= 5 and self.foe.style == "melee"
                and not self.has("fortress")):
            self.fortress_ready = False
            self.add("fortress", self)
            self.add("speed0", self)
            return
        super().main_action()


# =================================================================================
# Warden Aegis: Gravitic Anchor, Shackle Strike, Lockstep Field, Mana Cage,
# Field Commander
# =================================================================================

class AnchorZone(Zone):
    """Gravitic Anchor: an enemy starting its turn in the area saves or can't move."""

    def __init__(self, owner, center):
        super().__init__("anchor", owner, center, 10, difficult=True)

    def on_enemy_turn_start(self, c):
        if not saving_throw(c, "str", self.owner.dc, self.owner, Ctx(name="anchor")):
            c.add("speed0", self.owner, until=("start", c))


class WardenAegis(Aegis):
    key, label = "warden", "Warden Aegis"
    guard = True

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.shackles = self.pb    # Shackle Strike's old uses, still spent by the evolutions' riders
        self.anchor = None
        self.cage_ready = level >= 10
        self.dc = 8 + self.pb + self.mod("str")

    def on_initiative(self):
        if self.level >= 7:
            self.fight.zones.append(Zone("lockstep", self, self.x, 5, follows=True, difficult=True))

    def take_turn(self):
        # Raise the Mana Cage on turn one against spellcasters, then move up.
        if self.cage_ready and any(e.caster for e in self.enemies()) and not self.has("restrained"):
            self.pre_bonus()
            self.action = False
            self.cage_ready = False
            self.add("cage", self, value=self.dc)
            self.close_in()
            self.post_bonus()
            return
        super().take_turn()

    def post_bonus(self):
        if self.anchor is None and not self.bonus_used:
            # Gravitic Anchor on the enemies nearest us, within 20 feet of where I stand.
            near = self.nearest_enemy()
            if near and self.dist_to(near) <= 30:
                self.bonus_used = True
                self.anchor = AnchorZone(self, max(self.x - 20, min(self.x + 20, near.x)))
                self.fight.zones.append(self.anchor)

    def on_hit(self, tgt, ctx, crit):
        if tgt.dead:
            return
        if ctx.oa and self.level >= 7:
            tgt.add("speed0", self, until=("end", tgt))    # Lockstep Field
        # Shackle Strike: every hit tethers the target to me until my next turn.
        tgt.add("tethered", self, until=("start", self))
        if self.shackles and not ctx.oa:
            self.shackles -= 1

    def aura_save_bonus(self, ally, abil):
        # Field Commander: allies within 10 feet may use my Strength or Constitution.
        if self.level >= 15 and abil in ("str", "con") and self.dist_to(ally) <= 10:
            mine = max(self.mod("str"), self.mod("con"))
            return max(0, mine - ally.mod(abil))
        return 0
