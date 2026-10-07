"""Subclass Evolution (draft): the Ascendant and Corrupted branches a subclass
chooses between at 6th level.

- Ascendant (pre-assimilation): the mana stays outside the body and flows out
  to allies. A support upgrade to the kit, always on, no cost.
- Corrupted (full assimilation): at the start of a fight the character may
  open the seal: for that fight the subclass's kit turns to raw damage, and
  Assimilation goes up by 1 (the 0-6 track; a long rest takes 1 off). A
  Corrupted hero here is one who opened the seal for this fight.

Branches are compared per adventuring day (evolve.py --open-share): over a day
of two hard fights, a Corrupted character opens the seal for one, so a
Corrupted kit should be worth about twice its Ascendant in the fight it opens.

Each branch is a what-if variant of a subclass in heroes.py, the way
SanguineMageNoSwap is. `uses` counts how often a branch feature fired, as a
sanity check.
"""
from engine import Zone, d20, deal, roll_damage, saving_throw
from heroes import (AetherMage, BulwarkAegis, CrystalArcher, Gunman, HellboundMage, SanguineAegis,
                    SanguineMage, StonewardenMage, VerdantMage, WarboundMage, WardenAegis)

UNLOCK = 6


class Branch:
    branch = None

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.evolved = level >= UNLOCK
        self.uses = 0


class Ascendant(Branch):
    branch = "ascendant"


class Corrupted(Branch):
    """The seal is open: this fight, the kit deals raw damage, nothing else."""
    branch = "corrupted"

    def enemy_source(self, src):
        return src is not None and src.side != self.side and not src.dead


def most_hurt(creatures):
    return min(creatures, key=lambda c: c.hp / c.max_hp)


# =========================================================================
# Crystal Mages
# =========================================================================

class VerdantAscendant(Ascendant, VerdantMage):
    """Grovekeeper: Memory of the Grove rerolls any failed save that matters
    (control, fear, or a damaging spell), with one more use, and allies within
    30 feet of you gain a bonus to saving throws equal to your Resonance Rank.

    (Round 3 had no save bonus: +1.5 points. Round 4, +1: +1.9. Round 5, a flat +2.)"""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        if self.evolved:
            self.grove += 1

    def aura_save_bonus(self, ally, abil):
        return self.rk if self.evolved and self.dist_to(ally) <= 30 else 0

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




class WarboundAscendant(Ascendant, WarboundMage):
    """Drumwarden: as a bonus action, beat the war-drum for your allies: each
    ally within 30 feet gains temporary HP equal to your Intelligence modifier
    and advantage on its next attack roll. Uses: half your proficiency bonus, rounded up.

    (Round 1 fired this off War Drum's critical hit instead: 0.1 times a fight,
    +0.2 points. Round 2 also gave temporary HP equal to your Intelligence
    modifier: +3.4. Round 4 dropped the temporary HP: +0.9. Round 5, both
    with proficiency bonus - 1 uses: +3.0.)"""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.drums = (self.pb + 1) // 2 if self.evolved else 0

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




class SanguineAscendant(Ascendant, SanguineMage):
    """Penitent: Soul Tether drains d8s instead of d6s, and heals a creature of
    your choice within 30 feet instead of you, for the damage plus your
    Intelligence modifier.

    (Round 3 drained 1d6: +1.6 points. Round 4 drained 1d10, healed + Intelligence: +1.7.
    Ranked, d10s healing + Intelligence + proficiency: +4.6.)"""

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
                got = deal(e, roll_damage([(self.rk, 8, 0, "necrotic")]), self, {"spell": True})
                who = most_hurt([self] + [a for a in self.allies() if self.dist_to(a) <= 30])
                who.heal(got + max(0, self.mod("int")))
                return




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




class BulwarkAscendant(Ascendant, BulwarkAegis):
    """Shieldbearer: Living Wall reaches allies within 10 feet, and the ally you
    shield gains temporary HP equal to twice your proficiency bonus + your
    Constitution modifier.

    (Round 1 gave proficiency bonus only: +0.6 points. Round 2 gave
    proficiency bonus + Constitution: +1.6.)"""

    def guard_attack(self, att, ally, ctx):
        if not self.evolved:
            return super().guard_attack(att, ally, ctx)
        if self.reaction and not self.incapacitated() and self.dist_to(ally) <= 10 and att is not self:
            self.reaction = False
            self.uses += 1
            ally.gain_thp(2 * self.pb + self.mod("con"))
            return True
        return False




class WardenAscendant(Ascendant, WardenAegis):
    """Peacekeeper: a creature you Shackle Strike also has disadvantage on its next attack roll."""

    def after_hit(self, tgt, ctx, crit):
        before = self.shackles
        super().after_hit(tgt, ctx, crit)
        if self.evolved and self.shackles < before and not tgt.dead:
            self.uses += 1
            tgt.add("next_atk_disadv", self, until=("start", self))




# =========================================================================
# Range
# =========================================================================

class ArcherAscendant(Ascendant, CrystalArcher):
    """Spotter's Mark: until the start of your next turn, your allies have
    advantage on attack rolls against a creature you hit with a special arrow.
    From Resonance Rank 3, the first ally hit on it also deals 1d6 per Rank.

    (Round 1 gave only the next ally's attack advantage: +0.2 points.)"""

    def after_hit(self, tgt, ctx, crit):
        super().after_hit(tgt, ctx, crit)
        if self.evolved and ctx.get("special") and not tgt.dead:
            self.uses += 1
            tgt.add("spotted", self, until=("start", self), value="all")
            if self.rk >= 3 and not tgt.has("spotted_dmg"):
                tgt.add("spotted_dmg", self, until=("start", self), value=(self.rk, 6, 0, "piercing"))




class GunmanAscendant(Ascendant, Gunman):
    """Covering Fire: when an enemy within your firearm's normal range attacks an
    ally, you can use your reaction to fire a warning shot: that attack roll
    takes a penalty die: d4, d6, d8, d10 at Resonance Rank 1-4. Uses: half your
    proficiency bonus + 1.

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
            att.add("next_atk_pen", self, value=2 + 2 * self.rk)   # taken by this very attack roll
        return False


# =========================================================================
# Corrupted kits (the seal open for this fight)
# =========================================================================

class ThornZone(Zone):
    """Thornblood: whatever the Verdant's spells hold bleeds at the start of its turn."""

    def on_enemy_turn_start(self, c):
        o = self.owner
        e = c.get("restrained")
        if e and e.source is o:
            o.uses += 1
            deal(c, roll_damage([(o.rk + 1, 10, o.mod("int"), "piercing")]), o, {"spell": True})


class VerdantCorrupted(Corrupted, VerdantMage):
    """Thornblood: rootbind also deals 1d8 piercing per Resonance Rank on a
    failed save, and a creature restrained by one of your spells takes piercing
    at the start of each of its turns: 1d10 per Rank + 1d10 + your
    Intelligence modifier.

    (Kit round 1 thorns were 1d8 + Intelligence: +1.7 points in an open fight.)"""

    def on_initiative(self):
        super().on_initiative()
        if self.evolved:
            self.fight.zones.append(ThornZone("thorns", self, self.x, 999, follows=True))

    def on_failed_save(self, tgt, ctx):
        super().on_failed_save(tgt, ctx)
        if self.evolved and ctx.get("name") == "rootbind" and not tgt.dead:
            self.uses += 1
            deal(tgt, roll_damage([(self.rk, 8, 0, "piercing")]), self, {"spell": True})

    def extra_options(self, opts):
        super().extra_options(opts)
        foe = self.foe
        if self.evolved and self.dist() <= 30 and self.can_see(foe):
            pf = self.p_save_fail(foe, "str", {"name": "rootbind"})
            opts.append((pf * 4.5 * self.rk, "thorned rootbind", lambda f=foe: self.rootbind(f)))


class WarboundCorrupted(Corrupted, WarboundMage):
    """Ironblood: every Beat you hold adds 1d8 fire to your attack hits, and
    Blood for Power adds three times the hit points you lose.

    (Kit round 1: d4s and twice: +2.3 points in an open fight.)"""

    def hit_extra(self, tgt, ctx):
        out = super().hit_extra(tgt, ctx)
        if self.evolved and self.beats:
            self.uses += 1
            out = out + [(self.beats, 8, 0, "fire")]
        return out

    def spell_bonus_parts(self, ctx):
        bfp = self.bfp
        out = super().spell_bonus_parts(ctx)
        if self.evolved and bfp and not self.bfp:      # Blood for Power just went into this spell
            out = out + [(0, 0, 2 * bfp, "fire")]
        return out


class StonewardenCorrupted(Corrupted, StonewardenMage):
    """Splinterskin: damage your Runic Bulwark prevents is stored as shards and
    added as force to your next damaging spell.

    (Kit round 1 also gave melee attackers force equal to your Intelligence
    modifier: +5.6 points in an open fight.)"""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.shards = 0

    def runic_bulwark(self, tgt, dmg):
        out = super().runic_bulwark(tgt, dmg)
        if self.evolved and out is not dmg:
            self.uses += 1
            self.shards += sum(dmg.values()) - sum(out.values())
        return out

    def spell_bonus_parts(self, ctx):
        out = super().spell_bonus_parts(ctx)
        if self.shards:
            out = out + [(0, 0, self.shards, "force")]
            self.shards = 0
        return out


class HellboundCorrupted(Corrupted, HellboundMage):
    """Debtcaller: your Shadow Mark lasts until it is collected. Each time the
    marked creature takes damage from anyone, its debt grows by 1d10. You can
    collect the whole debt as necrotic when the creature fails a save against
    your spell, or call it in as a bonus action. A failed save no longer ends
    the mark unless you collect.

    (Kit round 1: d8s, collected only on a failed save: +0.7 points in an open
    fight. Round 2 added the bonus-action call, but the bot marked the healthiest
    enemy rather than the one it was casting at: +0.6. Round 3 marked the
    spell's target, but every failed save still ended the mark before any debt
    built up: +0.5. Round 4 kept the mark, with debt growing only from your own
    spells (d10s): +1.7, and it was never collected; the marked creature died first.)"""
    watches_damage = True

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.debt = {}

    def mine(self, tgt):
        m = tgt.get("shadow_mark")
        return m is not None and m.source is self

    def bonus_before(self, plan):
        # Collecting comes first: a debt left standing dies with its debtor.
        for e in list(self.debt):
            if self.evolved and not e.dead and self.mine(e) and self.worth_collecting(e):
                self.bonus_used = True
                self.collect(e)
                return
        if (self.evolved and plan and self.marks and self.foe and not self.foe.dead
                and not any(self.mine(e) for e in self.enemies())):
            self.marks -= 1
            self.bonus_used = True
            self.foe.add("shadow_mark", self)      # mark what this turn's spell is aimed at
            return
        super().bonus_before(plan)
        if not self.evolved:
            return
        for e in self.enemies():
            m = e.get("shadow_mark")
            if m and m.source is self:
                m.until = None                      # the debt doesn't lapse
        if not self.bonus_used and self.marks and not any(self.mine(e) for e in self.enemies()):
            cands = [e for e in self.enemies() if self.dist_to(e) <= 60 and self.can_see(e)]
            if cands:
                self.marks -= 1
                self.bonus_used = True
                max(cands, key=lambda e: e.hp).add("shadow_mark", self)

    def collect(self, tgt):
        owed = self.debt.pop(tgt, 0)
        m = tgt.get("shadow_mark")
        if m and m.source is self:
            tgt.remove(effect=m)
        if owed and not tgt.dead:
            self.uses += 1
            deal(tgt, roll_damage([(owed, 10, 0, "necrotic")]), self, {"spell": True})

    def accrue(self, tgt):
        if self.evolved and not tgt.dead and self.mine(tgt):
            self.debt[tgt] = self.debt.get(tgt, 0) + 1

    def witness_damage(self, tgt, total, src):
        if total > 0 and src is not None and src.side == self.side:
            self.accrue(tgt)

    def worth_collecting(self, tgt):
        owed = self.debt.get(tgt, 0)
        return owed >= 4 or (owed and tgt.hp <= 5.5 * owed)

    def on_failed_save(self, tgt, ctx):
        marked = self.mine(tgt) and ctx.get("spell")
        collect = marked and self.worth_collecting(tgt)
        super().on_failed_save(tgt, ctx)          # the mark's own damage; the base rule ends the mark
        if not marked or tgt.dead:
            return
        if collect:
            self.collect(tgt)
        else:
            tgt.add("shadow_mark", self)          # no collection: the mark and its debt stay


class SanguineCorrupted(Corrupted, SanguineMage):
    """Prism-Burst: Soul Tether drains an extra 1d6 per Resonance Rank in
    necrotic (the extra doesn't heal you) and has no use limit while the seal
    is open. When the tethered creature drops
    to 0 hit points, the tether leaps to the nearest enemy within 30 feet of
    it, which takes the drain at once.

    (Kit round 1: 2d6 with the usual uses: +1.2 points in an open fight.
    Ranked, the drain replaced the base drain and lost its healing: +1.8, and
    -2.0 at 15th level, where the lost healing was largest.)"""

    def bonus_after(self, plan):
        if not self.evolved:
            return super().bonus_after(plan)
        if self.bonus_used:
            return
        for e in self.enemies():
            m = e.get("tethered")
            if m and m.source is self:
                self.bonus_used = True
                self.uses += 1
                self.heal(deal(e, roll_damage([(self.rk, 6, 0, "necrotic")]), self, {"spell": True}))
                if not e.dead:
                    deal(e, roll_damage([(self.rk, 6, 0, "necrotic")]), self, {"spell": True})
                return

    def on_kill(self, tgt):
        super().on_kill(tgt)
        m = tgt.get("tethered")
        if self.evolved and m and m.source is self:
            tgt.remove(effect=m)
            near = [e for e in self.enemies() if e.dist_to(tgt) <= 30]
            if near:
                nxt = min(near, key=lambda e: e.dist_to(tgt))
                self.uses += 1
                nxt.add("tethered", self, until=("start", self), skip=2)
                deal(nxt, roll_damage([(2 * self.rk, 6, 0, "necrotic")]), self, {"spell": True})


class AetherCorrupted(Corrupted, AetherMage):
    """Hollow Mirror: Stabilizing Pulse turns inside out. As a bonus action, a
    creature within 30 feet makes a Constitution save: 1d8 + 1d8 per Resonance
    Rank + your Intelligence modifier in force on a failure, half on a success,
    with twice the dice against a spellcaster. Uses: Intelligence modifier. And when you or an ally
    within 30 feet takes damage from a spell, your reaction throws half-level
    d6s of force back at the caster.

    (Kit round 1 pulsed 2d8: +4.2 points in an open fight.)"""

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.pulses = max(1, self.mod("int")) if self.evolved else 0

    def bonus_after(self, plan):
        super().bonus_after(plan)
        if self.pulses and not self.bonus_used:
            cands = [e for e in self.enemies() if self.dist_to(e) <= 30 and self.can_see(e)]
            if cands:
                e = max(cands, key=lambda e: (e.caster, -e.hp))
                self.pulses -= 1
                self.bonus_used = True
                self.uses += 1
                n = (self.rk + 1) * (2 if e.caster else 1)
                dmg = roll_damage([(n, 8, max(1, self.mod("int")), "force")])
                ok = saving_throw(e, "con", self.dc, self, {"spell": True, "damage": True})
                deal(e, {k: v // 2 for k, v in dmg.items()} if ok else dmg, self, {"spell": True})

    def mirror(self, tgt, dmg, src, ctx):
        if (self.evolved and self.reaction and not self.incapacitated() and ctx.get("spell")
                and self.enemy_source(src) and self.dist_to(tgt) <= 30):
            self.reaction = False
            self.uses += 1
            deal(src, roll_damage([(self.level // 2, 6, 0, "force")]), self, {"spell": True})
        return dmg

    def react_to_damage(self, dmg, src, ctx):
        return self.mirror(self, dmg, src, ctx)

    def ward(self, tgt, dmg, src, ctx):
        return self.mirror(tgt, dmg, src, ctx)


class SanguineAegisCorrupted(Corrupted, SanguineAegis):
    """Bloodfused: your first melee hit each turn deals extra necrotic equal to
    twice your proficiency bonus (the blood Leeching Strikes takes), and Red
    Pact's dice are d8s instead of d6s.

    (Kit round 1: proficiency bonus once: +3.3 points in an open fight.)"""

    def hit_extra(self, tgt, ctx):
        pact = self.pact
        out = super().hit_extra(tgt, ctx)
        if self.evolved and ctx["kind"] == "melee" and ctx.get("weapon") and self.my_turn():
            if self.leeched_turn != self.turns:
                self.uses += 1
                out = out + [(0, 0, 2 * self.pb, "necrotic")]
            if pact and not self.pact:
                out = out + [(0, 0, pact, "necrotic")]   # d8s instead of d6s: +1 a die on average
        return out


class BulwarkCorrupted(Corrupted, BulwarkAegis):
    """Spiteplate: while your Anchored Stance holds, a creature that hits you or
    an ally within 5 feet of you with a melee attack takes 2d6 + your
    Constitution modifier + your proficiency bonus in thunder.

    (Kit round 1: Constitution + proficiency only: +2.0 points in an open fight.)"""

    def spite(self, tgt, dmg, src, ctx):
        if (self.evolved and self.has("anchored") and ctx.get("attack") and ctx.get("kind") == "melee"
                and self.enemy_source(src) and self.dist_to(tgt) <= 5):
            self.uses += 1
            deal(src, roll_damage([(2, 6, self.mod("con") + self.pb, "thunder")]), self, {"magical": True})
        return dmg

    def react_to_damage(self, dmg, src, ctx):
        return self.spite(self, super().react_to_damage(dmg, src, ctx), src, ctx)

    def ward(self, tgt, dmg, src, ctx):
        return self.spite(tgt, super().ward(tgt, dmg, src, ctx), src, ctx)


class WardenCorrupted(Corrupted, WardenAegis):
    """Gravewell: a creature that fails its save against your Gravitic Anchor
    also takes 1d6 force per Resonance Rank, and a Shackle Strike hit deals an
    extra 1d4 force per Rank.

    (Kit round 1: 2d10 on the anchor: +5.6 points in an open fight.)"""

    def on_failed_save(self, tgt, ctx):
        super().on_failed_save(tgt, ctx)
        if self.evolved and ctx.get("name") == "anchor" and not tgt.dead:
            self.uses += 1
            deal(tgt, roll_damage([(self.rk, 6, 0, "force")]), self, {"magical": True})

    def after_hit(self, tgt, ctx, crit):
        before = self.shackles
        super().after_hit(tgt, ctx, crit)
        if self.evolved and self.shackles < before and not tgt.dead:
            self.uses += 1
            deal(tgt, roll_damage([(self.rk, 4, 0, "force")]), self, {"magical": True})


class ArcherCorrupted(Corrupted, CrystalArcher):
    """Shardblood: a special arrow deals an extra 1d6 force per Resonance Rank
    and bursts: each other enemy within 5 feet of the target takes 1d4 force per Rank.

    (Kit round 1: +1d8 on the target: +2.8 points in an open fight. Round 2,
    +2d8: +6.3.)"""

    def hit_extra(self, tgt, ctx):
        out = super().hit_extra(tgt, ctx)
        if self.evolved and ctx.get("special"):
            out = out + [(self.rk, 6, 0, "force")]
        return out

    def after_hit(self, tgt, ctx, crit):
        super().after_hit(tgt, ctx, crit)
        if self.evolved and ctx.get("special"):
            self.uses += 1
            for e in [e for e in self.enemies() if e is not tgt and e.dist_to(tgt) <= 5]:
                deal(e, roll_damage([(self.rk, 4, 0, "force")]), self, {"magical": True})


class GunmanCorrupted(Corrupted, Gunman):
    """Powderveins: a special shot deals an extra 1d6 force per Resonance Rank,
    and a creature that fails its save against Powder Disruption takes 1d6
    thunder per Rank.

    (Kit round 1: +1d10: +3.5 points in an open fight.)"""

    def hit_extra(self, tgt, ctx):
        out = super().hit_extra(tgt, ctx)
        if self.evolved and ctx.get("special"):
            self.uses += 1
            out = out + [(self.rk, 6, 0, "force")]
        return out

    def on_failed_save(self, tgt, ctx):
        super().on_failed_save(tgt, ctx)
        if self.evolved and ctx == {"control": True} and self.level >= 7 and not tgt.dead and self.my_turn():
            deal(tgt, roll_damage([(self.rk, 6, 0, "thunder")]), self, {"magical": True})


EVOLVED = {}
for _cls in (VerdantAscendant, VerdantCorrupted, WarboundAscendant, WarboundCorrupted,
             StonewardenAscendant, StonewardenCorrupted, HellboundAscendant, HellboundCorrupted,
             SanguineAscendant, SanguineCorrupted, AetherAscendant, AetherCorrupted,
             SanguineAegisAscendant, SanguineAegisCorrupted, BulwarkAscendant, BulwarkCorrupted,
             WardenAscendant, WardenCorrupted, ArcherAscendant, ArcherCorrupted,
             GunmanAscendant, GunmanCorrupted):
    EVOLVED[(_cls.key, _cls.branch)] = _cls
