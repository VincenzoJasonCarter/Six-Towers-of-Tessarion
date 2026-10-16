"""The six Crystal Mage subclasses (lore-book/05-subclasses-skill.md) on the Wizard chassis."""
from engine import (Conc, Ctx, Dice, Zone, attack, attack_adv, avg, avg_dice, d, d20, deal, flat, move,
                    p_hit, push, roll_damage, saving_throw)

from .base import legendary_left
from .wizard import Wizard

LEVELED = ("magic missile", "scorching ray", "fireball", "vitriolic", "disintegrate", "finger")
BIG_AREA = ("fireball", "vitriolic", "disintegrate", "finger")


def is_spell(plan, names):
    """The plan's label starts with one of `names`."""
    return any(plan[1].startswith(s) for s in names)


# =================================================================================
# Verdant Mage: entangle, Rootbind, Memory of the Grove, Verdant Veil
# =================================================================================

class VerdantMage(Wizard):
    key, label = "verdant", "Verdant Mage"

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.free["entangle"] = 1
        self.grove = max(1, self.mod("int")) if level >= 6 else 0   # Memory of the Grove rerolls
        self.veils = self.pb if level >= 10 else 0
        self.first_save_dis = level >= 14                           # Master of Living Paths

    def ac(self):
        return super().ac() + (1 if self.level >= 10 else 0)

    # ----- entangle ----------------------------------------------------------
    def extra_controls(self):
        if not (self.free.get("entangle") or self.avail(1)):
            return []
        # Restrained stops a melee foe reaching anyone; a shooter or caster barely cares.
        impact = lambda e: 0.8 if e.style == "melee" else 0.35
        score = lambda hit: sum(self.p_save_fail(e, "str", Ctx(control=True, name="entangle")) * impact(e)
                                for e in hit if not e.has("restrained"))
        area = self.best_area(10, 90, score=score)
        if area and score(area[0]) > 0:
            return [(score(area[0]), "entangle", lambda hit=area[0]: self.entangle(hit))]
        return []

    def entangle(self, hit):
        self.spend(0 if self.free.get("entangle") else self.avail(1)[0], "entangle")
        self.acted = True
        self.drop_conc()
        self.control_tries += 1
        held = []
        lr = legendary_left(hit)
        for t in hit:
            if not saving_throw(t, "str", self.dc, self, Ctx(spell=True, level=1, control=True, name="entangle")):
                held.append((t, t.add("restrained", self, value=("escape", self.dc))))
        if held:
            self.conc = Conc("entangle", held)
        self.refund_if_resisted(lr, hit)

    # ----- Rootbind ----------------------------------------------------------
    def extra_options(self, opts):
        # Only when the slow keeps a charging enemy out of reach this round.
        foe = self.foe
        if self.dist() <= 30 and foe.style == "melee" and not self.threatened() and self.can_see(foe):
            sp = foe.speed_now()
            if sp >= self.dist() - 5 > sp - 10:
                pf = self.p_save_fail(foe, "str", Ctx(name="rootbind"))
                opts.append((pf * foe.est_dpr(self), "rootbind", lambda f=foe: self.rootbind(f)))

    def rootbind(self, tgt):
        self.acted = True
        extra = [e for e in self.enemies() if e is not tgt and e.dist_to(tgt) <= 5]
        for t in [tgt] + extra[:self.tier - 1]:
            if not saving_throw(t, "str", self.dc, self, Ctx(spell=True, level=0, name="rootbind")):
                t.add("slow", self, until=("start", self), value=10)

    # ----- Master of Living Paths --------------------------------------------
    def target_save_adv(self, tgt, abil, ctx):
        return False, bool(self.first_save_dis and ctx.name in ("entangle", "rootbind"))

    def on_failed_save(self, tgt, ctx):
        # Teleport 15 feet away when a restrain or slow lands.
        if self.level >= 14 and ctx.name in ("entangle", "rootbind") and self.threatened():
            threat = self.melee_threat()
            if threat:
                move(self, False, 15, provoke=False, ref=threat)

    # ----- Memory of the Grove -------------------------------------------------
    def grove_reroll(self, who, abil, dc, ctx):
        if ctx.fear and self.grove and self.reaction and not self.incapacitated() and self.dist_to(who) <= 30:
            self.grove -= 1
            self.reaction = False
            return d20() + who.save_bonus(abil) >= dc
        return False

    def save_reroll(self, abil, dc, src, ctx):
        return self.grove_reroll(self, abil, dc, ctx)

    def ally_save_reroll(self, ally, abil, dc, src, ctx):
        return self.grove_reroll(ally, abil, dc, ctx)

    # ----- Verdant Veil ----------------------------------------------------------
    def bonus_before(self, plan):
        # On whoever the enemy archers are most likely to shoot.
        if self.veils and any(e.style == "ranged" for e in self.enemies()):
            cands = [self] + [a for a in self.allies() if self.dist_to(a) <= 30]
            who = min(cands, key=lambda c: (c.ac(), c.hp))
            if not who.has("veiled"):
                self.veils -= 1
                self.bonus_used = True
                who.add("veiled", self, until=("start", self))


# =================================================================================
# Warbound Mage: a greatsword, War Drum, Battle Surge, Blood for Power,
# Crimson Presence, Warstorm
# =================================================================================

class WarboundMage(Wizard):
    key, label = "warbound", "Warbound Mage"
    can_oa = True

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.free["shield"] = 1
        # Crimson Attunement: its one martial weapon, swung with Intelligence.
        self.blade = Dice(2, 6, "slashing", self.mod("int"))
        self.blade_bonus = self.mod("int") + self.pb
        self.beats = d(1, 4) - 1      # War Drum Beats left over from the last fight (they last until a rest)
        self.surged_turn = -1
        self.bfp_uses = self.pb if level >= 6 else 0
        self.bfp = 0                  # HP burned this turn, waiting for a spell
        self.presence = max(1, self.mod("int")) if level >= 10 else 0
        self.presence_now = False
        self.warstorm = False
        self.warstorm_ready = level >= 14

    # ----- War Drum and Battle Surge -------------------------------------------
    def on_hit_roll(self, tgt, ctx):
        if self.beats >= 3:
            if ctx.crit:
                return                    # the drum waits; no crash
            ctx.crit = True
            self.beats = 0
            self.add("crash", self, **self.until_my_next_end())
        else:
            self.beats += 1

    def on_hit(self, tgt, ctx, crit):
        if crit:
            self.battle_surge()

    def on_kill(self, tgt):
        self.battle_surge()

    def battle_surge(self):
        if self.surged_turn != self.turns:
            self.surged_turn = self.turns
            self.gain_thp(max(1, self.mod("int") + self.level))

    # ----- the blade ------------------------------------------------------------
    def booming_blade(self):
        self.acted = True
        foe, t = self.foe, self.tier
        extra = [Dice(t - 1, 8, "thunder")] if t > 1 else []
        hit, _ = attack(self, foe, bonus=self.blade_bonus, parts=[self.blade] + extra, kind="melee", weapon="blade")
        if hit and not foe.dead:
            foe.add("booming", self, until=("start", self), value=t)

    def on_enemy_moved(self, mover):
        e = mover.get("booming")
        if e and e.source is self:
            mover.remove(effect=e)
            deal(mover, roll_damage([Dice(e.value, 8, "thunder")]), self, Ctx(spell=True))

    def opportunity_attack(self, tgt):
        attack(self, tgt, bonus=self.blade_bonus, parts=[self.blade], kind="melee", weapon="blade")

    # ----- choosing -----------------------------------------------------------------
    def extra_options(self, opts):
        foe = self.foe
        if self.dist() <= 5:
            adv, dis = attack_adv(self, foe, Ctx(kind="melee"))
            p = p_hit(self.blade_bonus, foe.ac(), adv, dis)
            opts.append((p * (avg([self.blade]) + (self.tier - 1) * 4.5), "booming blade", self.booming_blade))
        if self.warstorm_ready and not self.warstorm:
            gain = 0.55 * (4.5 + self.blade.plus) if self.threatened() else 0
            opts.append((gain * 3, "warstorm", self.enter_warstorm))

    def options(self):
        opts = super().options()
        if not (self.beats >= 3 and self.foe):
            return opts
        # A ready War Drum crit doubles the dice of the next attack that hits:
        # count that on the attacks that can carry it (one ray of a scorching ray).
        t = self.tier
        dice = {"fire bolt": 5.5 * t, "scorching ray": 7, "booming blade": avg_dice([self.blade]) + (t - 1) * 4.5}
        out = []
        for ev, label, do in opts:
            name = "scorching ray" if label.startswith("scorching ray") else label
            if name in dice:
                kind = "melee" if name == "booming blade" else "ranged"
                bonus = self.blade_bonus if kind == "melee" else self.spell_atk
                adv, dis = attack_adv(self, self.foe, Ctx(kind=kind, spell=kind == "ranged"))
                ev += p_hit(bonus, self.foe.ac(), adv, dis) * dice[name]
            out.append((ev, label, do))
        return out

    def enter_warstorm(self):
        self.warstorm_ready = False
        self.warstorm = True

    # ----- Blood for Power, Crimson Presence, Warstorm ---------------------------
    def bonus_before(self, plan):
        if not plan or not is_spell(plan, LEVELED):
            return
        if self.warstorm:
            deal(self, {"psychic": d(1, 6)}, None, Ctx())       # Warstorm's price per leveled spell
        if self.bfp_uses and self.hp - self.level > 0.5 * self.max_hp:
            self.bfp_uses -= 1
            self.bonus_used = True
            self.hp -= self.level
            self.bfp = self.level
        if self.presence and is_spell(plan, BIG_AREA):
            self.presence_now = True

    def spell_bonus_damage(self):
        if self.bfp:
            bfp, self.bfp = self.bfp, 0
            return [flat(bfp, "fire")]                           # Blood for Power
        return []

    def target_save_adv(self, tgt, abil, ctx):
        # Crimson Presence: disadvantage on the save against a big damaging spell.
        if ctx.damage and self.presence and (self.presence_now or ctx.predict):
            if not ctx.predict:
                self.presence -= 1
                self.presence_now = False
            return False, True
        return False, False

    def bonus_after(self, plan):
        self.bfp = 0
        self.presence_now = False
        # Warstorm: a melee weapon attack as a bonus action after casting.
        if self.warstorm and plan and not self.bonus_used and self.dist() <= 5:
            self.bonus_used = True
            self.opportunity_attack(self.foe)


# =================================================================================
# Stonewarden Mage: Stoneguard, Runic Bulwark, Stoneheart Aegis
# =================================================================================

class StonewardenMage(Wizard):
    key, label = "stonewarden", "Stonewarden Mage"

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.runic = max(1, (self.mod("int") + 1) // 2) if level >= 6 else 0   # half Intelligence, rounded up
        self.stoneheart_ready = level >= 14

    def don_mage_armor(self):
        self.add("mage_armor", self)   # the free casting, no slot spent

    def ac(self):
        # Stoneguard: 13 + Dex, +1 more under mage armor.
        return 13 + self.mod("dex") + (1 if self.has("mage_armor") else 0) + self.ac_bonus()

    # ----- Runic Bulwark: halve a big hit on me or an ally within 30 feet
    def runic_bulwark(self, tgt, dmg):
        total = sum(dmg.values())
        if (self.runic and self.reaction and not self.incapacitated() and self.dist_to(tgt) <= 30
                and total >= max(8, 0.15 * tgt.max_hp)):
            self.runic -= 1
            self.reaction = False
            return {k: v // 2 for k, v in dmg.items()}
        return dmg

    def damage_reaction(self, dmg, src, ctx):
        return self.runic_bulwark(self, dmg)

    def ally_damage_reaction(self, ally, dmg, src, ctx):
        return self.runic_bulwark(ally, dmg)

    # ----- Stoneheart Aegis: +2 AC and advantage on Con saves for allies within 30 feet
    def choose(self):
        near = [a for a in self.allies() if self.dist_to(a) <= 30]
        if self.stoneheart_ready and len(near) >= 2 and not self.has("silenced"):
            return (99, "stoneheart aegis", self.raise_stoneheart)
        return super().choose()

    def raise_stoneheart(self):
        self.stoneheart_ready = False
        self.add("stoneheart", self)

    def aura_ac(self, ally):
        return 2 if self.has("stoneheart") and self.dist_to(ally) <= 30 else 0

    def aura_save_adv(self, ally, abil, src, ctx):
        return bool(self.has("stoneheart") and abil == "con" and self.dist_to(ally) <= 30), False


# =================================================================================
# Hellbound Mage: hex, Shadow Mark, Curseweaver, darkness, Pact Nexus
# =================================================================================

class NexusZone(Zone):
    """Pact Nexus: an enemy that attacked or cast this turn, inside it, saves or takes necrotic."""

    def __init__(self, owner):
        super().__init__("nexus", owner, owner.x, 20, follows=True, difficult=True)

    def on_enemy_turn_end(self, c):
        o = self.owner
        if c.acted and not saving_throw(c, "wis", o.dc, o, Ctx(spell=True, level=9)):
            deal(c, o.nexus_damage(), o, Ctx(spell=True))


class HellboundMage(Wizard):
    key, label = "hellbound", "Hellbound Mage"

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.free["hex"] = 1
        self.marks = self.pb
        self.curses = max(1, self.mod("int")) if level >= 6 else 0
        if level >= 10:
            self.devils_sight = True
            self.free["darkness"] = 1
        self.nexus_ready = level >= 14

    def choose(self):
        # Hold first; darkness (seen through only by me) when no hold is worth casting.
        # With allies around, darkness would blind them too, so it stays solo-only.
        ctrl = self.control_option()
        if ctrl:
            return ctrl
        if (not self.conc and not self.has("silenced") and self.free.get("darkness")
                and not self.allies() and not any(e.devils_sight for e in self.enemies())):
            return (99, "darkness", self.darkness)
        return super().choose()

    def extra_options(self, opts):
        if self.nexus_ready:
            near = [e for e in self.enemies() if self.dist_to(e) <= 20 + 30]
            per = max(1, self.mod("int")) + 3.5 * self.rank
            ev = sum(per * self.p_save_fail(e, "wis") * 3 for e in near)
            opts.append((ev, "pact nexus", self.pact_nexus))

    def bonus_before(self, plan):
        # Hex before an attack spell; Shadow Mark before a save spell.
        if not plan:
            return
        if (not self.conc and plan[1] not in ("darkness", "hold person", "hold monster")
                and (self.free.get("hex") or self.avail(1)) and is_spell(plan, ("fire bolt", "scorching ray"))):
            self.bonus_used = True
            self.hex()
        elif self.marks and is_spell(plan, BIG_AREA + ("hold",)):
            self.bonus_used = True
            self.marks -= 1
            self.foe.add("shadow_mark", self, **self.until_my_next_end())

    def hex(self):
        self.spend(0 if self.free.get("hex") else self.avail(1)[0], "hex")
        self.drop_conc()
        e = self.foe.add("hexed", self)
        self.conc = Conc("hex", [(self.foe, e)])

    def darkness(self):
        self.spend(0, "darkness")
        self.drop_conc()
        e = self.add("darkness", self)
        self.conc = Conc("darkness", [(self, e)])

    def pact_nexus(self):
        self.nexus_ready = False
        self.fight.zones.append(NexusZone(self))

    def nexus_damage(self):
        return roll_damage([Dice(self.rank, 6, "necrotic"), flat(max(1, self.mod("int")), "necrotic")])

    def bonus_damage(self, tgt, ctx):
        out = super().bonus_damage(tgt, ctx)
        e = tgt.get("hexed")
        if e and e.source is self:
            out.append(Dice(1, 6, "necrotic"))
        return out

    def on_failed_save(self, tgt, ctx):
        m = tgt.get("shadow_mark")
        if m and m.source is self:
            tgt.remove(effect=m)
            deal(tgt, roll_damage([Dice(self.rank, 6, "necrotic"), flat(max(1, self.mod("int")), "necrotic")]),
                 self, Ctx(spell=True))
        if self.curses and not tgt.dead and ctx.spell:    # Curseweaver
            self.curses -= 1
            tgt.add("next_atk_disadv", self, until=("end", tgt))


# =================================================================================
# Sanguine Mage: inflict wounds, Soul Tether, Flux Manipulation, Overlord
# =================================================================================

class SanguineMage(Wizard):
    key, label = "sanguine_mage", "Sanguine Mage"
    heals = True

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.free["inflict wounds"] = 1
        self.tethers = self.pb
        self.flux = 1 if level >= 6 else 0    # once per long rest; only the save swap is used here
        self.overlord_ready = level >= 14
        self.overlord = False

    def save_ability(self, tgt, abil, ctx, commit=False):
        """Flux Manipulation: move the save onto the target's weakest ability."""
        if not self.flux or not (ctx.control or ctx.big):
            return abil
        if tgt.incapacitated() and abil in ("str", "dex"):
            return abil
        group = ctx.group or [tgt]
        total = lambda ab: sum(t.save_bonus(ab) for t in group) / len(group)
        best = min(("str", "dex", "con", "int", "wis", "cha"), key=total)
        if total(best) <= total(abil) - 2:
            if commit:
                self.flux -= 1
            return best
        return abil

    def choose(self):
        if (self.overlord_ready and not self.has("silenced")
                and sum(e.hp for e in self.enemies()) > 0.6 * sum(e.max_hp for e in self.enemies())):
            return (99, "sanguine overlord", self.enter_overlord)
        return super().choose()

    def extra_options(self, opts):
        if self.dist() <= 5 and self.free.get("inflict wounds") and not self.has("silenced"):
            opts.append((self.p_attack(self.foe, "melee") * 16.5, "inflict wounds", self.inflict_wounds))

    def inflict_wounds(self):
        free = self.free.get("inflict wounds")
        lv = 1 if free else self.avail(1)[0]
        self.spell_attack("inflict wounds", 0 if free else lv, 1, [Dice(2 + lv, 10, "necrotic")],
                          kind="melee", free="inflict wounds", rng=5)

    # ----- Soul Tether: the last creature I damaged on my turn; drain it as a bonus action
    def on_damage_dealt(self, tgt, amount, ctx):
        if self.my_turn() and not tgt.dead:
            for e in self.enemies():
                m = e.get("soul_tether")
                if m and m.source is self:
                    e.remove(effect=m)        # one tether at a time
            tgt.add("soul_tether", self, until=("start", self), skip=2)

    def bonus_after(self, plan):
        if not self.tethers or self.bonus_used:
            return
        e = self.tethered()
        if e:
            self.tethers -= 1
            self.bonus_used = True
            self.heal(deal(e, roll_damage([Dice(self.rank, 6, "necrotic")]), self, Ctx(spell=True)))

    def tethered(self):
        """The enemy my Soul Tether is on, if any."""
        for e in self.enemies():
            m = e.get("soul_tether")
            if m and m.source is self:
                return e
        return None

    # ----- Overlord ------------------------------------------------------------------
    def enter_overlord(self):
        self.overlord_ready = False
        self.overlord = True
        self.max_range = 30   # its save-flipping reaches 30 feet

    def force_fail(self, tgt, ctx):
        # Flip a success within 30 feet, for 2d8 psychic.
        if (self.overlord and ctx.spell and (ctx.control or ctx.big)
                and tgt.side != self.side and self.dist_to(tgt) <= 30 and self.hp > 25):
            deal(self, {"psychic": d(2, 8)}, None, Ctx())
            return not self.dead
        return False

    def after_spell_damage(self, tgt, ctx):
        # Push a damaged Large-or-smaller creature 10 feet (here: away).
        if self.overlord and not tgt.dead and tgt.style == "melee":
            push(tgt, self, 10)


# =================================================================================
# Aether Mage: Null Field, Anchor of Tessarion
# =================================================================================

class AetherMage(Wizard):
    key, label = "aether", "Aether Mage"

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        self.fields = self.pb if level >= 10 else 0
        self.anchor_ready = level >= 14

    # ----- Null Field: advantage on saves against spells, and a reroll of a spell
    # attack or save (3rd level or lower), for me and allies within 10 feet
    def bonus_before(self, plan):
        if self.fields and any(e.caster for e in self.enemies()) and not self.has("null_field"):
            self.fields -= 1
            self.bonus_used = True
            self.add("null_field", self)

    def in_field(self, who):
        return self.has("null_field") and self.dist_to(who) <= 10

    def my_save_adv(self, abil, src, ctx):
        return bool(self.has("null_field") and ctx.spell), False

    def aura_save_adv(self, ally, abil, src, ctx):
        return bool(self.in_field(ally) and ctx.spell), False

    def field_reroll(self, who, abil, dc, ctx):
        if (self.in_field(who) and ctx.spell and ctx.level <= 3 and ctx.single
                and self.reaction and not self.incapacitated()):
            self.reaction = False
            return d20() + who.save_bonus(abil) >= dc
        return False

    def save_reroll(self, abil, dc, src, ctx):
        return self.field_reroll(self, abil, dc, ctx)

    def ally_save_reroll(self, ally, abil, dc, src, ctx):
        return self.field_reroll(ally, abil, dc, ctx)

    def hit_reaction(self, att, ctx, total, ac):
        raised = super().hit_reaction(att, ctx, total, ac)   # shield first
        if raised:
            return raised
        return self.ally_hit_reaction(att, self, ctx, total, ac)

    def ally_hit_reaction(self, att, ally, ctx, total, ac):
        if (self.in_field(ally) and ctx.spell and ctx.level <= 3
                and self.reaction and not self.incapacitated()):
            self.reaction = False
            if d20() + ctx.bonus < ac:
                return 99    # the reroll missed
        return 0

    # ----- Anchor of Tessarion ---------------------------------------------------------
    def resists(self, dtype, ctx, nonmagical):
        return self.level >= 14 and dtype in ("force", "psychic")

    def save_from_death(self, tgt):
        # Once, someone within 30 feet drops to 1 HP instead.
        if self.anchor_ready and self.dist_to(tgt) <= 30 and (self.reaction or tgt is self):
            self.anchor_ready = False
            if tgt is not self:
                self.reaction = False
            return True
        return False
