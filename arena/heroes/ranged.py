"""The two Range subclasses (lore-book/05-subclasses-skill.md): Dexterity,
studded leather, Archery fighting style.

Special ammunition is crafted at a rest, before the party knows the fight, so
each carries a fixed LOADOUT and fires whichever kind it carries is worth most
on the shot. Each kind's effect lasts until the start of the shooter's turn
after next (AMMO_SKIP).

With gear=True (party.py --gear) they carry Tessarion's own weapons from
data/items.yaml instead of the 5e ones: Tier 1 below 5th level, Tier 2 from
5th. Everyone keeps the arena's +1/+2 magic weapon on top; a Tier 2 item's own
+1 is damage only.
  - Gunman: Matchlock Musket and Crude Handgun, then Black-Powder Rifle and
    Heavy Handgun. A natural 1 fouls the barrel (Misfire): clearing a Tier 1
    gun takes an action, a Tier 2 gun a bonus action. With the long gun fouled
    the bot fires its handgun rather than spend a turn clearing, and clears
    only once both are fouled.
  - Crystal Archer: Crude Crossbow (a natural 1 slips the latch: an action to
    re-span), then Composite Bow (Heavy Draw: speed halved on a turn it fires;
    no disadvantage at long range).
"""
from engine import Ctx, Dice, d, deal, flat, halved, mod, move, p_fail, p_hit, push, roll_damage, saving_throw

from .fighter import Fighter, Weapon

AMMO_SKIP = 1        # special ammunition's effects outlast the shooter's next turn start once
MARKSMANS_FOCUS = 2

# The special ammunition carried, by proficiency bonus: the kinds the bot chose
# when it could pick any at the moment it fired, over all four party
# encounters, shared out in proportion.
LOADOUT = {
    "archer": {2: ("amber", "prismatic"), 3: ("amber", "red", "prismatic"),
               4: ("amber", "prismatic", "red", "verdant"),
               5: ("red", "red", "prismatic", "amber", "verdant")},
    "gunman": {2: ("red", "snare"), 3: ("snare", "red", "amber"),
               4: ("red", "red", "snare", "snare"),
               5: ("snare", "snare", "snare", "red", "red")},
}

LONGBOW = Weapon("longbow", 1, 8, "ranged", 150, 600)
MUSKET = Weapon("musket", 1, 12, "ranged", 40, 120)
PISTOL = Weapon("pistol", 1, 10, "ranged", 30, 90)
GEAR = {
    "matchlock musket": Weapon("matchlock musket", 1, 12, "ranged", 40, 120, misfire="action"),
    "crude handgun": Weapon("crude handgun", 1, 10, "ranged", 30, 90, misfire="action"),
    "black-powder rifle": Weapon("black-powder rifle", 1, 12, "ranged", 80, 200, bonus=1, misfire="bonus"),
    "heavy handgun": Weapon("heavy handgun", 1, 10, "ranged", 30, 90, bonus=1, misfire="bonus"),
    "crude crossbow": Weapon("crude crossbow", 1, 8, "ranged", 80, 320, misfire="action"),
    "composite bow": Weapon("composite bow", 1, 8, "ranged", 150, 600, bonus=1, heavy_draw=True, no_long_dis=True),
}
BOWS = {"longbow", "crude crossbow", "composite bow"}   # Marksman's Focus and Crystal Sight


def loadout(key, pb):
    """{kind: count} a Range subclass carries into a fight."""
    out = {}
    for kind in LOADOUT[key][pb]:
        out[kind] = out.get(kind, 0) + 1
    return out


class Range(Fighter):
    ranged = True
    style = "ranged"
    can_oa = False
    resonant_from = 3   # the level Resonant Shot comes in

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.resonant_turn = -1
        self.special_turn = -1   # one special shot a turn

    def armor(self, level, sc):
        return 12 + mod(sc["dex"])   # studded leather

    def resonant(self):
        """Resonant Shot: once on each of my turns, a weapon hit deals an extra
        1d4 force per Resonance Rank."""
        if self.level >= self.resonant_from and self.my_turn() and self.resonant_turn != self.turns:
            self.resonant_turn = self.turns
            return [Dice(self.rank, 4, "force")]
        return []

    def ammo_left(self):
        return sum(self.quiver.values())

    def best_ammo(self, ev):
        """The kind worth most among those still in the quiver, or None (ties: the first)."""
        ev = {k: v for k, v in ev.items() if self.quiver.get(k)}
        return max(ev, key=ev.get) if ev else None

    def spend_ammo(self, kind):
        self.quiver[kind] -= 1
        self.special_turn = self.turns

    def closest_to(self, foe):
        """The member of my party nearest `foe`: whoever it will go for."""
        return min([self] + self.allies(), key=lambda c: c.dist_to(foe))


# =================================================================================
# Crystal Archer: Marksman's Focus, special arrows, Crystal Sight, Silent Volley,
# Rain of Shards
# =================================================================================

class CrystalArcher(Range):
    key, label = "archer", "Crystal Archer"
    max_range = 120
    resonant_from = 7

    def __init__(self, level, gear=False):
        self.weapon = LONGBOW
        if gear:
            self.weapon = GEAR["crude crossbow" if level < 5 else "composite bow"]
            self.max_range = min(self.max_range, self.weapon.normal)
        super().__init__(level, gear)
        self.drawing = False
        self.quiver = loadout("archer", self.pb)
        self.sights = self.pb if level >= 7 else 0
        self.sight_turn = -1
        self.volley_turn = -1
        self.rain_ready = level >= 15
        self.dc = 8 + self.pb + self.mod("dex")

    def ignores_long_range(self):
        return self.level >= 10 or super().ignores_long_range()

    def speed_now(self):
        # Heavy Draw (Composite Bow): half speed on a turn it fires.
        sp = super().speed_now()
        return sp // 10 * 5 if self.drawing else sp

    def take_turn(self):
        self.drawing = self.weapon.heavy_draw and any(
            self.dist_to(e) <= self.weapon.long for e in self.enemies())
        super().take_turn()
        self.drawing = False

    def pre_bonus(self):
        if self.sights and not self.has("crystal_sight"):
            self.sights -= 1
            self.bonus_used = True
            self.add("crystal_sight", self)

    # ----- special arrows ---------------------------------------------------------
    def pick_arrow(self):
        """The special arrow worth most on this shot, or None."""
        if not self.ammo_left() or self.special_turn == self.turns:
            return None
        foe = self.foe
        rk = self.rank
        closest = self.closest_to(foe)
        ev = {"red": 2.5 * rk}
        sp = foe.speed_now()
        if foe.style == "melee" and sp >= foe.dist_to(closest) - 5 > sp - 10:
            ev["verdant"] = foe.est_dpr(closest)          # it can't reach anyone this round
        ev["prismatic"] = 2.5 * rk + (2.5 * rk if self.hp < self.max_hp else 0)
        if self.amber_ally(foe):
            ev["amber"] = 2.5 * rk + self.pb
        ev["violet"] = 0.125 * foe.est_dpr(closest) / max(1, getattr(foe, "multi", 1))
        if foe.has("darkness"):
            p, pd = p_hit(self.atk_bonus, foe.ac()), p_hit(self.atk_bonus, foe.ac(), dis=True)
            ev["white"] = (p - pd) * (4.5 + self.dmg_bonus + MARKSMANS_FOCUS)
        return self.best_ammo(ev)

    def amber_ally(self, tgt):
        """Who would take Amber Dust's temporary HP: the most hurt friend near the target."""
        near = [c for c in [self] + self.allies() if c.dist_to(tgt) <= 10]
        return min(near, key=lambda c: c.hp / c.max_hp) if near else None

    def one_attack(self):
        arrow = self.pick_arrow()
        if arrow:
            self.spend_ammo(arrow)
        self.weapon_attack(self.foe, Ctx(special=arrow, attack_action=True))

    def bonus_damage(self, tgt, ctx):
        out = self.resonant()
        if ctx.weapon in BOWS:
            out.append(flat(MARKSMANS_FOCUS, "piercing"))
            if self.has("crystal_sight") and self.sight_turn != self.turns and self.my_turn():
                self.sight_turn = self.turns
                out.append(Dice(self.rank, 6, "piercing"))
        if ctx.special == "red":
            out.append(Dice(self.rank, 4, "thunder"))
        elif ctx.special == "prismatic":
            out.append(Dice(self.rank, 4, "necrotic"))
        return out

    def on_damage_dealt(self, tgt, amount, ctx):
        if ctx.special == "prismatic":
            self.heal(d(self.rank, 4))   # about the necrotic part of the hit

    def on_hit(self, tgt, ctx, crit):
        if tgt.dead:
            return
        self.arrow_effect(tgt, ctx.special)
        if self.level >= 10 and ctx.attack_action and self.volley_turn != self.turns:
            # Silent Volley: it attacks me at disadvantage until my next turn.
            self.volley_turn = self.turns
            if not saving_throw(tgt, "wis", self.dc, self, Ctx()):
                tgt.add("unlocated", self, until=("start", self))

    def arrow_effect(self, tgt, kind):
        if kind == "verdant":
            tgt.add("slow", self, until=("start", self), skip=AMMO_SKIP, value=10)
        elif kind == "red":
            if not tgt.immovable and not saving_throw(tgt, "str", self.dc, self, Ctx()):
                push(tgt, self, 5)
        elif kind == "amber":
            who = self.amber_ally(tgt)
            if who:
                who.gain_thp(d(self.rank, 4) + self.pb, self)
        elif kind == "white":
            tgt.add("white_dust", self, until=("start", self), skip=AMMO_SKIP)

    # ----- the action ---------------------------------------------------------------
    def main_action(self):
        if self.weapon.name in self.fouled:
            self.fouled.discard(self.weapon.name)   # Slipping Latch: the action goes on re-spanning
            return
        if self.rain_ready and self.try_rain_of_shards():
            return
        super().main_action()

    def try_rain_of_shards(self):
        """Rain of Shards (6d8 piercing + 3d8 force, Dex save for half in 20 feet),
        when it beats a shot and the area catches no allies."""
        dice = (6, 3)
        frac = lambda hit: sum(p_fail(e.save_bonus("dex"), self.dc) / 2 + 0.5 for e in hit)
        area = self.best_area(20, self.weapon.long, score=frac)
        if not area:
            return False
        rain = 4.5 * sum(dice) * frac(area[0])
        volley = p_hit(self.atk_bonus, self.foe.ac()) * (4.5 + self.dmg_bonus + MARKSMANS_FOCUS)
        if rain <= volley:
            return False
        self.rain_ready = False
        hit = area[0]
        arrow = None
        if self.quiver.get("verdant") and any(e.style == "melee" for e in hit):
            arrow = "verdant"
            self.spend_ammo(arrow)
        dmg = roll_damage([Dice(dice[0], 8, "piercing"), Dice(dice[1], 8, "force")])
        stake = sum(dmg.values()) - sum(v // 2 for v in dmg.values())
        for e in hit:
            ok = saving_throw(e, "dex", self.dc, self, Ctx(big=True, stake=stake))
            deal(e, halved(dmg) if ok else dict(dmg), self, Ctx(weapon="longbow", magical=True))
            if not ok and arrow and not e.dead:
                self.arrow_effect(e, arrow)
        return True


# =================================================================================
# Gunman: a musket and a backup pistol, special shots, Powder Disruption,
# Recoil Step, Soulshot Barrage
# =================================================================================

class Gunman(Range):
    key, label = "gunman", "Gunman"
    max_range = 40

    def __init__(self, level, gear=False):
        self.weapon, self.backup = MUSKET, PISTOL
        if gear:
            tier2 = level >= 5
            self.weapon = GEAR["black-powder rifle" if tier2 else "matchlock musket"]
            self.backup = GEAR["heavy handgun" if tier2 else "crude handgun"]
            self.max_range = self.weapon.normal   # it keeps its distance by the long gun's range
        self.main = self.weapon
        super().__init__(level, gear)
        self.quiver = loadout("gunman", self.pb)
        self.barrage_ready = level >= 15
        self.dc = 8 + self.pb + self.mod("dex")

    def pick_target(self):
        # From 7th level, a spellcaster in range is the Gunman's first job.
        if self.level >= 7:
            casters = [e for e in self.enemies() if e.caster and self.dist_to(e) <= self.weapon.long
                       and not e.has("silenced")]
            if casters:
                return min(casters, key=lambda e: e.hp)
        return super().pick_target()

    # ----- special shots ------------------------------------------------------------
    def pick_shot(self):
        """The special round worth most on this shot, or None."""
        if not self.ammo_left() or self.special_turn == self.turns:
            return None
        foe = self.foe
        w = self.weapon
        avg_hit = w.n * (w.die + 1) / 2 + self.dmg_bonus
        closest = self.closest_to(foe)
        threat = foe.est_dpr(closest)
        # Powder Disruption rides on any special shot from 7th level: silence a caster.
        pd = 0.0
        if self.level >= 7 and foe.caster and not foe.has("silenced"):
            pd = p_fail(foe.save_bonus("con"), self.dc) * threat
        rk = self.rank
        ev = {"red": 2.5 * rk + pd}
        if self.level >= 7 and foe.caster:
            ev["violet"] = (p_fail(foe.save_bonus("con") - 2.5, self.dc)) * threat
        ev["prismatic"] = 2.5 * rk + pd + (3 if foe.heals else 0)
        allies = self.allies()
        if allies:
            # -2 AC helps every weapon attack my allies make until my next turn.
            swings = sum(1 for a in allies if isinstance(a, Fighter))
            ev["amber"] = pd + swings * 0.1 * avg_hit
        if foe.style == "melee" and (self.dist() <= 5 or foe.speed_now() >= foe.dist_to(closest) - 5):
            ev["snare"] = pd + p_fail(foe.save_bonus("str"), self.dc) * threat
        if foe.has("mage_armor") or foe.has("darkness"):
            ev["white"] = pd + 3 * 0.15 * avg_hit
        return self.best_ammo(ev)

    def one_attack(self):
        if (self.main.name in self.fouled or self.weapon is not self.main) and not self.ready_gun():
            return
        shot = self.pick_shot()
        if shot:
            self.spend_ammo(shot)
        self.weapon_attack(self.foe, Ctx(special=shot, powder=self.level >= 7))
        # Recoil Step: slide 10 feet back after the shot, no opportunity attack.
        threat = self.melee_threat()
        if self.level >= 10 and threat and self.dist_to(threat) <= 5 and not self.dead:
            if move(self, False, 10, provoke=False, ref=threat) and not self.has("recoil"):
                self.add("ac", self, until=("start", self), value=2)
                self.add("recoil", self, until=("start", self))

    def bonus_damage(self, tgt, ctx):
        out = self.resonant()
        if ctx.special == "red":
            return out + [Dice(self.rank, 4, "force")]
        if ctx.special == "prismatic":
            return out + [Dice(self.rank, 4, "necrotic")]
        if ctx.barrage:
            return out + [Dice(2, 8, "force")]
        return out

    def on_hit(self, tgt, ctx, crit):
        if tgt.dead:
            return
        sp = ctx.special
        if sp == "snare":
            if not saving_throw(tgt, "str", self.dc, self, Ctx()):
                tgt.add("speed0", self, until=("start", self), skip=AMMO_SKIP)
        elif sp == "amber":
            tgt.add("ac", self, until=("start", self), skip=AMMO_SKIP, value=-2)
        elif sp == "violet":
            tgt.add("next_save_pen", self, until=("start", self), skip=AMMO_SKIP)
        elif sp == "prismatic":
            tgt.add("no_heal", self, until=("start", self), skip=AMMO_SKIP)
        elif sp == "white":
            if tgt.has("darkness"):
                tgt.drop_conc()
            elif tgt.has("mage_armor"):
                tgt.remove("mage_armor")
        if sp and self.level >= 7 and not tgt.dead and self.my_turn():
            # Powder Disruption: no verbal or somatic spells until my next turn.
            if not saving_throw(tgt, "con", self.dc, self, Ctx(control=True, name="powder disruption")):
                tgt.add("silenced", self, until=("start", self), skip=AMMO_SKIP)

    # ----- misfires (gear) -------------------------------------------------------------
    def pre_bonus(self):
        # A Tier 2 lock fouled last turn: clear it with the bonus action first.
        m = self.main
        if m.name in self.fouled and m.misfire == "bonus" and not self.bonus_used:
            self.clear(m, "bonus")

    def clear(self, w, how):
        """Spend a bonus action or an action clearing a fouled barrel."""
        if how == "bonus":
            self.bonus_used = True
        self.fouled.discard(w.name)

    def ready_gun(self):
        """Pick the gun for this shot, clearing a fouled one if it's cheap.
        False: no shot this time (both fouled, and the action went on clearing)."""
        for w in (self.main, self.backup):
            if w.name not in self.fouled:
                break
            if w.misfire == "bonus" and not self.bonus_used:
                self.clear(w, "bonus")
                break
        else:
            self.clear(self.main, "action")
            return False
        if self.weapon is not w:
            self.weapon = w
            self.max_range = w.normal
        return True

    # ----- Soulshot Barrage ---------------------------------------------------------------
    def main_action(self):
        if self.barrage_ready and self.dist() <= self.weapon.normal:
            self.soulshot_barrage()
            return
        super().main_action()

    def soulshot_barrage(self):
        """Three shots, then a Wisdom save or stunned for each creature hit. The musket is spent."""
        self.barrage_ready = False
        struck = []
        for _ in range(3):
            if not self.retarget():
                break
            hit, _ = self.weapon_attack(self.foe, Ctx(barrage=True, powder=True))
            if hit and self.foe not in struck:
                struck.append(self.foe)
        self.weapon = self.main = self.backup   # the backup pistol comes out
        self.max_range = 30
        for t in struck:
            if not t.dead and not saving_throw(t, "wis", self.dc, self, Ctx(control=True, name="soulshot barrage")):
                t.add("stunned", self, until=("start", self))
