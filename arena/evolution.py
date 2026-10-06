"""Subclass Evolution (draft): the Ascendant and Corrupted branches a subclass
chooses between at 6th level.

- Ascendant (pre-assimilation): the mana stays outside the body and flows out
  to allies. Support-oriented, no cost.
- Corrupted (full assimilation): one Corrupted power, offence shaped by the
  subclass's role. Each use adds 1 Assimilation (the 0-6 track; a long rest
  takes 1 off). Every Corrupted power deals the same budget, d8s equal to half
  your level, so subclasses differ only in how they deliver it.

Each branch is a what-if variant of a subclass in heroes.py, the way
SanguineMageNoSwap is. Fights start fresh, so the Assimilation track itself
(marks at 2, Fracture at 4, Lost at 6) isn't modelled: CORRUPT_USES is how many
Corrupted powers a hero may spend per fight (1 = the rate a long rest pays back).
`uses` counts how often a branch feature actually fired, as a sanity check.
"""
from engine import d20, deal, roll_damage, saving_throw
from heroes import (AetherMage, BulwarkAegis, CrystalArcher, Gunman, HellboundMage, SanguineAegis,
                    SanguineMage, StonewardenMage, VerdantMage, WarboundMage, WardenAegis)

UNLOCK = 6
CORRUPT_USES = 1


class Branch:
    branch = None

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.evolved = level >= UNLOCK
        self.uses = 0


class Ascendant(Branch):
    branch = "ascendant"


class Corrupted(Branch):
    branch = "corrupted"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.corrupt = CORRUPT_USES if self.evolved else 0

    def assimilate(self):
        self.corrupt -= 1
        self.uses += 1

    def burst(self, dtype):
        """The Corrupted damage budget: d8s equal to half your level."""
        return [(self.level // 2, 8, 0, dtype)]

    def enemy_source(self, src):
        return src is not None and src.side != self.side and not src.dead


def most_hurt(creatures):
    return min(creatures, key=lambda c: c.hp / c.max_hp)


# =========================================================================
# Crystal Mages
# =========================================================================

class VerdantAscendant(Ascendant, VerdantMage):
    """Grovekeeper: Memory of the Grove rerolls any failed save that matters
    (control, fear, or a damaging spell), with one more use."""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        if self.evolved:
            self.grove += 1

    def grove_reroll(self, who, abil, dc, ctx):
        if not self.evolved:
            return super().grove_reroll(who, abil, dc, ctx)
        if ((ctx.get("fear") or ctx.get("control") or ctx.get("damage")) and self.grove and self.reaction
                and not self.incapacitated() and self.dist_to(who) <= 30):
            self.grove -= 1
            self.reaction = False
            self.uses += 1
            return d20() + who.save_bonus(abil) >= dc
        return False


class VerdantCorrupted(Corrupted, VerdantMage):
    """Thornblood: when a creature fails its save against your entangle or
    rootbind, roots tear out of your veins: the burst in piercing, and it is
    restrained until the end of its next turn."""

    def on_failed_save(self, tgt, ctx):
        super().on_failed_save(tgt, ctx)
        if self.corrupt and ctx.get("name") in ("entangle", "rootbind") and not tgt.dead and self.my_turn():
            self.assimilate()
            deal(tgt, roll_damage(self.burst("piercing")), self, {"spell": True})
            if not tgt.dead and not tgt.has("restrained"):
                tgt.add("restrained", self, until=("end", tgt))

    def extra_options(self, opts):
        super().extra_options(opts)
        foe = self.foe
        if self.corrupt and self.dist() <= 30 and self.can_see(foe):
            pf = self.p_save_fail(foe, "str", {"name": "rootbind"})
            opts.append((pf * (4.5 * (self.level // 2) + 0.5 * foe.est_dpr(self)), "thornblood",
                         lambda f=foe: self.rootbind(f)))


class WarboundAscendant(Ascendant, WarboundMage):
    """Drumwarden: as a bonus action, beat the war-drum for your allies: each
    ally within 30 feet gains temporary HP equal to your Intelligence modifier
    and advantage on its next attack roll. Uses: proficiency bonus.

    (Round 1 fired this off War Drum's critical hit instead: 0.1 times a fight,
    +0.2 points.)"""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.drums = self.pb if self.evolved else 0

    def bonus_after(self, plan):
        super().bonus_after(plan)
        near = [a for a in self.allies() if self.dist_to(a) <= 30]
        if self.drums and not self.bonus_used and near:
            self.drums -= 1
            self.bonus_used = True
            self.uses += 1
            for a in near:
                a.gain_thp(max(1, self.mod("int")))
                a.add("inspired", self, until=("end", a))


class WarboundCorrupted(Corrupted, WarboundMage):
    """Ironblood: when you use Blood for Power, the spell also deals the burst in fire."""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.iron = False

    def bonus_before(self, plan):
        super().bonus_before(plan)
        if self.corrupt and self.bfp:
            self.assimilate()
            self.iron = True

    def spell_bonus_parts(self, ctx):
        out = super().spell_bonus_parts(ctx)
        if self.iron:
            self.iron = False
            out = out + self.burst("fire")
        return out

    def bonus_after(self, plan):
        super().bonus_after(plan)
        self.iron = False


class StonewardenAscendant(Ascendant, StonewardenMage):
    """Runekeeper: Runic Bulwark reaches 60 feet.

    (Round 1 also gave the warded creature temporary HP equal to your
    Intelligence modifier: +6.3 points, the strongest Ascendant.)"""

    def runic_bulwark(self, tgt, dmg):
        if not self.evolved:
            return super().runic_bulwark(tgt, dmg)
        total = sum(dmg.values())
        if (self.runic and self.reaction and not self.incapacitated() and self.dist_to(tgt) <= 60
                and total >= max(8, 0.15 * tgt.max_hp)):
            self.runic -= 1
            self.reaction = False
            self.uses += 1
            return {k: v // 2 for k, v in dmg.items()}
        return dmg


class StonewardenCorrupted(Corrupted, StonewardenMage):
    """Splinterskin: when you use Runic Bulwark, the ward bursts outward and the
    attacker takes the burst in force."""

    def splinter(self, used, src):
        if used and self.corrupt and self.enemy_source(src):
            self.assimilate()
            deal(src, roll_damage(self.burst("force")), self, {"spell": True})

    def react_to_damage(self, dmg, src, ctx):
        out = super().react_to_damage(dmg, src, ctx)
        self.splinter(out is not dmg, src)
        return out

    def ward(self, tgt, dmg, src, ctx):
        out = super().ward(tgt, dmg, src, ctx)
        self.splinter(out is not dmg, src)
        return out


class HellboundAscendant(Ascendant, HellboundMage):
    """Ashwarden: a creature under your Shadow Mark has disadvantage on its next
    attack roll. You can mark the most dangerous enemy even when you aren't
    casting at it."""

    def bonus_before(self, plan):
        marks = self.marks
        super().bonus_before(plan)
        if not self.evolved:
            return
        if self.marks < marks:
            self.uses += 1
            self.foe.add("next_atk_disadv", self, **self.until_my_next_end())
        elif not self.bonus_used and self.marks:
            cands = [e for e in self.enemies() if self.dist_to(e) <= 60 and self.can_see(e)]
            if cands:
                e = max(cands, key=lambda e: e.est_dpr(self))
                self.marks -= 1
                self.bonus_used = True
                self.uses += 1
                e.add("shadow_mark", self, **self.until_my_next_end())
                e.add("next_atk_disadv", self, **self.until_my_next_end())


class HellboundCorrupted(Corrupted, HellboundMage):
    """Debtcaller: when a creature under your Shadow Mark fails a save against
    your spell, it takes the burst in necrotic and suffers both Curseweaver
    effects, without your reaction."""

    def on_failed_save(self, tgt, ctx):
        m = tgt.get("shadow_mark")
        marked = m is not None and m.source is self
        super().on_failed_save(tgt, ctx)
        if marked and self.corrupt and not tgt.dead and ctx.get("spell"):
            self.assimilate()
            deal(tgt, roll_damage(self.burst("necrotic")), self, {"spell": True})
            if not tgt.dead:
                tgt.add("slow", self, value=10, **self.until_my_next_end())
                tgt.add("next_atk_disadv", self, until=("end", tgt))


class SanguineAscendant(Ascendant, SanguineMage):
    """Penitent: Soul Tether's drain heals a creature of your choice within 30
    feet instead of you, for the damage plus your Intelligence modifier."""

    def bonus_after(self, plan):
        if not self.evolved:
            return super().bonus_after(plan)
        if not self.tethers or self.bonus_used:
            return
        for e in self.enemies():
            m = e.get("tethered")
            if m and m.source is self:
                self.tethers -= 1
                self.bonus_used = True
                self.uses += 1
                got = deal(e, roll_damage([(1, 6, 0, "necrotic")]), self, {"spell": True})
                who = most_hurt([self] + [a for a in self.allies() if self.dist_to(a) <= 30])
                who.heal(got + max(0, self.mod("int")))
                return


class SanguineCorrupted(Corrupted, SanguineMage):
    """Prism-Burst: as a bonus action, detonate your Soul Tether: the burst in
    necrotic, and you regain half the damage."""

    def bonus_after(self, plan):
        if self.corrupt and not self.bonus_used:
            for e in self.enemies():
                m = e.get("tethered")
                if m and m.source is self:
                    self.assimilate()
                    self.bonus_used = True
                    e.remove(effect=m)
                    self.heal(deal(e, roll_damage(self.burst("necrotic")), self, {"spell": True}) // 2)
                    return
        super().bonus_after(plan)


class AetherAscendant(Ascendant, AetherMage):
    """Steadying Pulse: Stabilizing Pulse is a bonus action, and the creature also
    gains temporary HP equal to your wizard level. Uses: Intelligence modifier."""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.pulses = max(1, self.mod("int")) if self.evolved else 0

    def bonus_after(self, plan):
        super().bonus_after(plan)
        if self.pulses and not self.bonus_used:
            cands = [c for c in [self] + self.allies()
                     if self.dist_to(c) <= 30 and c.hp < c.max_hp and c.thp < self.level]
            if cands:
                self.pulses -= 1
                self.bonus_used = True
                self.uses += 1
                most_hurt(cands).gain_thp(self.level)


class AetherCorrupted(Corrupted, AetherMage):
    """Hollow Mirror: when you or an ally within 30 feet takes damage from a
    spell, you can use your reaction to halve it and throw the burst back at
    the caster as force."""

    def mirror(self, tgt, dmg, src, ctx):
        if (self.corrupt and self.reaction and not self.incapacitated() and ctx.get("spell")
                and self.enemy_source(src) and self.dist_to(tgt) <= 30):
            self.assimilate()
            self.reaction = False
            deal(src, roll_damage(self.burst("force")), self, {"spell": True})
            return {k: v // 2 for k, v in dmg.items()}
        return dmg

    def react_to_damage(self, dmg, src, ctx):
        return self.mirror(self, dmg, src, ctx)

    def ward(self, tgt, dmg, src, ctx):
        return self.mirror(tgt, dmg, src, ctx)


# =========================================================================
# Aegisbound
# =========================================================================

class SanguineAegisAscendant(Ascendant, SanguineAegis):
    """Leashed: when Leeching Strikes heals you, the most hurt ally within 30
    feet regains twice your proficiency bonus in hit points.

    (Round 1 spent Blood Charges on an ally instead: -0.6 points, because the
    Aegis gave away its own sustain. Round 2 healed the ally by your
    proficiency bonus: +0.4.)"""

    def after_damage_dealt(self, tgt, amount, ctx):
        leeched = self.leeched_turn
        super().after_damage_dealt(tgt, amount, ctx)
        if self.evolved and self.leeched_turn != leeched:
            hurt = [a for a in self.allies() if self.dist_to(a) <= 30 and a.hp < a.max_hp]
            if hurt:
                self.uses += 1
                most_hurt(hurt).heal(2 * self.pb)


class SanguineAegisCorrupted(Corrupted, SanguineAegis):
    """Bloodfused: when you hit with a melee weapon attack, the armour drinks
    deep: the burst in necrotic, and you gain Blood Charges equal to your
    proficiency bonus."""

    def hit_extra(self, tgt, ctx):
        out = super().hit_extra(tgt, ctx)
        if self.corrupt and ctx["kind"] == "melee" and ctx.get("weapon") and self.my_turn():
            self.assimilate()
            self.gain(self.pb)
            out = out + self.burst("necrotic")
        return out


class BulwarkAscendant(Ascendant, BulwarkAegis):
    """Shieldbearer: Living Wall reaches allies within 10 feet, and the ally you
    shield gains temporary HP equal to your proficiency bonus + Constitution
    modifier.

    (Round 1 gave proficiency bonus only: +0.6 points.)"""

    def guard_attack(self, att, ally, ctx):
        if not self.evolved:
            return super().guard_attack(att, ally, ctx)
        if self.reaction and not self.incapacitated() and self.dist_to(ally) <= 10 and att is not self:
            self.reaction = False
            self.uses += 1
            ally.gain_thp(self.pb + self.mod("con"))
            return True
        return False


class BulwarkCorrupted(Corrupted, BulwarkAegis):
    """Spiteplate: when a melee attack hits you, the plates bite back: you take
    half damage and the attacker takes the burst in thunder."""

    def react_to_damage(self, dmg, src, ctx):
        if (self.corrupt and ctx.get("attack") and ctx.get("kind") == "melee" and self.enemy_source(src)
                and sum(dmg.values()) >= 8):
            self.assimilate()
            deal(src, roll_damage(self.burst("thunder")), self, {"magical": True})
            return {k: v // 2 for k, v in dmg.items()}
        return dmg


class WardenAscendant(Ascendant, WardenAegis):
    """Peacekeeper: a creature you Shackle Strike also has disadvantage on its next attack roll."""

    def after_hit(self, tgt, ctx, crit):
        before = self.shackles
        super().after_hit(tgt, ctx, crit)
        if self.evolved and self.shackles < before and not tgt.dead:
            self.uses += 1
            tgt.add("next_atk_disadv", self, until=("start", self))


class WardenCorrupted(Corrupted, WardenAegis):
    """Gravewell: as a bonus action, collapse your Gravitic Anchor. Each enemy
    within 10 feet of it makes a Strength save: the burst in force and speed 0
    until the start of your next turn on a failure, half damage on a success.
    (The pull toward the anchor isn't modelled on the line.)"""

    def post_bonus(self):
        if self.corrupt and self.anchor is not None and not self.bonus_used:
            c = self.anchor.center()
            caught = [e for e in self.enemies() if abs(e.x - c) <= 10]
            if len(caught) >= 2 or (caught and self.turns >= 3):
                self.assimilate()
                self.bonus_used = True
                self.fight.zones = [z for z in self.fight.zones if z is not self.anchor]
                self.anchor = None
                dmg = roll_damage(self.burst("force"))
                for e in caught:
                    ok = saving_throw(e, "str", self.dc, self, {"damage": True})
                    deal(e, {k: v // 2 for k, v in dmg.items()} if ok else dict(dmg), self, {"magical": True})
                    if not ok and not e.dead:
                        e.add("speed0", self, until=("start", self))
        super().post_bonus()


# =========================================================================
# Range
# =========================================================================

class ArcherAscendant(Ascendant, CrystalArcher):
    """Spotter's Mark: until the start of your next turn, your allies have
    advantage on attack rolls against a creature you hit with a special arrow.

    (Round 1 gave only the next ally's attack advantage: +0.2 points.)"""

    def after_hit(self, tgt, ctx, crit):
        super().after_hit(tgt, ctx, crit)
        if self.evolved and ctx.get("special") and not tgt.dead:
            self.uses += 1
            tgt.add("spotted", self, until=("start", self), value="all")


class ArcherCorrupted(Corrupted, CrystalArcher):
    """Shardblood: when you hit with a bow, the dust in your blood rides the
    arrow: the burst in force."""

    def hit_extra(self, tgt, ctx):
        out = super().hit_extra(tgt, ctx)
        if self.corrupt and ctx.get("weapon") == "longbow" and self.my_turn():
            self.assimilate()
            out = out + self.burst("force")
        return out


class GunmanAscendant(Ascendant, Gunman):
    """Covering Fire: when an enemy within your firearm's normal range attacks an
    ally, you can use your reaction to fire a warning shot: that attack roll
    takes a -1d4 penalty. Uses: half your proficiency bonus + 1.

    (Round 1 imposed disadvantage, proficiency-bonus uses: +5.1 points.
    Round 2 cut the uses: +4.2.)"""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.covers = self.pb // 2 + 1 if self.evolved else 0

    def guard_attack(self, att, ally, ctx):
        if (self.covers and self.reaction and not self.incapacitated() and att.side != self.side
                and self.dist_to(att) <= self.weapon["normal"] and self.can_see(att)):
            self.covers -= 1
            self.reaction = False
            self.uses += 1
            att.add("next_atk_pen", self)   # taken by this very attack roll
        return False


class GunmanCorrupted(Corrupted, Gunman):
    """Powderveins: when you hit with a firearm, the powder in your veins goes
    off with the shot: the burst in force, rolled as d10s.

    (Round 2 rolled d8s like everyone else: +2.9 points against the Archer's +4.9.)"""

    def hit_extra(self, tgt, ctx):
        out = super().hit_extra(tgt, ctx)
        if self.corrupt and ctx.get("firearm") and self.my_turn():
            self.assimilate()
            out = out + [(self.level // 2, 10, 0, "force")]
        return out


EVOLVED = {}
for _cls in (VerdantAscendant, VerdantCorrupted, WarboundAscendant, WarboundCorrupted,
             StonewardenAscendant, StonewardenCorrupted, HellboundAscendant, HellboundCorrupted,
             SanguineAscendant, SanguineCorrupted, AetherAscendant, AetherCorrupted,
             SanguineAegisAscendant, SanguineAegisCorrupted, BulwarkAscendant, BulwarkCorrupted,
             WardenAscendant, WardenCorrupted, ArcherAscendant, ArcherCorrupted,
             GunmanAscendant, GunmanCorrupted):
    EVOLVED[(_cls.key, _cls.branch)] = _cls
