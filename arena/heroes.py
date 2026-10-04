"""The eleven subclasses as fighting creatures, built from
lore-book/05-subclasses-skill.md on the 5e Wizard and Fighter chassis.

patched=False rebuilds the rules as they stood before Patch 1
(balance-patch.md) for the four subclasses it changed; the other seven
ignore the flag.
"""
from engine import (Conc, Creature, Zone, attack, attack_adv, avg, d, d20, deal, mod, move,
                    p_fail, p_hit, roll_damage, room_behind, saving_throw)


def prof(level):
    return 2 + (level - 1) // 4


def item(level):
    """+N of the weapon or spell focus everyone carries at this level."""
    return 0 if level < 5 else 1 if level < 15 else 2


def tier(level):
    return 1 + (level >= 5) + (level >= 11) + (level >= 17)


def scores_at(base, primary, level, asi_levels):
    s = dict(base)
    for lv in asi_levels:
        if lv <= level:
            if s[primary] < 20:
                s[primary] += 2
            elif s["con"] < 20:
                s["con"] += 2
    return s


SLOTS = {
    1: [2], 2: [3], 3: [4, 2], 4: [4, 3], 5: [4, 3, 2], 6: [4, 3, 3], 7: [4, 3, 3, 1],
    8: [4, 3, 3, 2], 9: [4, 3, 3, 3, 1], 10: [4, 3, 3, 3, 2], 11: [4, 3, 3, 3, 2, 1],
    12: [4, 3, 3, 3, 2, 1], 13: [4, 3, 3, 3, 2, 1, 1], 14: [4, 3, 3, 3, 2, 1, 1],
    15: [4, 3, 3, 3, 2, 1, 1, 1],
}
WIZ_BASE = dict(str=8, dex=14, con=14, int=16, wis=12, cha=10)
AEGIS_BASE = dict(str=16, dex=10, con=14, int=8, wis=12, cha=10)
RANGE_BASE = dict(str=10, dex=16, con=14, int=8, wis=12, cha=10)


class Hero(Creature):
    key = label = chassis = ""
    patch_sensitive = False

    def __init__(self, level, patched, scores, save_profs, hp, ac):
        super().__init__(self.label, level, scores, save_profs, prof(level), hp, ac)
        self.patched = patched
        self.item = item(level)

    def until_my_next_end(self):
        """Effect timing for "until the end of your next turn"."""
        return dict(until=("end", self), skip=1 if self.my_turn() else 0)

    def keep_distance(self):
        """Ranged and caster footwork: kite a foe that wants to close, close on one that doesn't.
        Called before and again after the action, with whatever movement is left."""
        foe, sp = self.foe, self.speed_now() - self.moved
        if sp <= 0:
            return
        if foe.style == "melee":
            if self.engaged():
                # Step away (eating the opportunity attack) only if the foe can't
                # follow and still attack on its turn.
                after = self.dist() + min(sp, room_behind(self))
                if foe.speed_now() < after - foe.reach:
                    move(self, False, sp)
            elif self.dist() < self.max_range:
                move(self, False, min(sp, self.max_range - self.dist()))
        elif self.dist() > self.max_range:
            move(self, True, min(sp, self.dist() - self.max_range))


# =========================================================================
# Wizards
# =========================================================================

class Wizard(Hero):
    chassis = "Wizard"
    style = "caster"
    caster = True
    can_oa = False
    max_range = 60

    def __init__(self, level, patched=True):
        sc = scores_at(WIZ_BASE, "int", level, (4, 8, 12, 16, 19))
        con = mod(sc["con"])
        hp = 6 + con + (level - 1) * (4 + con)
        super().__init__(level, patched, sc, ("int", "wis"), hp, 10 + mod(sc["dex"]))
        self.slots = [0] + SLOTS[level] + [0] * (9 - len(SLOTS[level]))
        self.free = {}             # spell -> free casts left
        self.spell_atk = self.mod("int") + self.pb + self.item
        self.dc = 8 + self.spell_atk
        self.tier = tier(level)
        self.control_tries = 0
        self.cast = {}             # per-casting scratch state
        self.don_mage_armor()

    def don_mage_armor(self):
        self.add("mage_armor", self)
        self.slots[1] -= 1         # cast before the day's fights

    def ac(self):
        return self.base_ac + (3 if self.has("mage_armor") else 0) + self.total("ac")

    def est_dpr(self, target):
        return 0.65 * 5.5 * self.tier + 3 * self.level

    # ----- slots -----------------------------------------------------
    def avail(self, lo):
        return [lv for lv in range(lo, 10) if self.slots[lv] > 0]

    def spend(self, level, free_name=None):
        if free_name and self.free.get(free_name):
            self.free[free_name] -= 1
        elif level:
            self.slots[level] -= 1

    # ----- reactions -------------------------------------------------
    def can_shield(self):
        return self.free.get("shield") or self.slots[1] > 0

    def use_shield(self):
        self.spend(1, "shield")
        self.reaction = False
        self.add("ac", self, until=("start", self), value=5)

    def react_to_attack(self, att, ctx, total, ac):
        if total < ac + 5 and self.can_shield():
            self.use_shield()
            return 5
        return 0

    def block_missiles(self):
        if self.reaction and not self.incapacitated() and self.can_shield():
            self.use_shield()
            return True
        return False

    # ----- prediction helpers -----------------------------------------
    def p_attack(self, kind="ranged"):
        adv, dis = attack_adv(self, self.foe, {"kind": kind, "spell": True})
        return p_hit(self.spell_atk, self.foe.ac(), adv, dis)

    def save_ability(self, abil, ctx, commit=False):
        """Hook for Flux Manipulation; returns the ability the foe actually saves with."""
        return abil

    def p_save_fail(self, abil, ctx=None):
        foe = self.foe
        ctx = dict(ctx or {}, spell=True)
        abil = self.save_ability(abil, ctx)
        if abil in ("str", "dex") and foe.incapacitated():
            return 1.0
        a1, d1 = foe.save_mods(abil, self, ctx)
        a2, d2 = self.impose_save_mods(foe, abil, dict(ctx, predict=True))
        dis = d1 or d2 or (abil == "dex" and foe.has("restrained"))
        p = p_fail(foe.save_bonus(abil), self.dc, a1 or a2, dis)
        return p

    def cage_factor(self, targeted):
        cage = self.foe.get("cage")
        if targeted and cage and self.dist() > 15:
            return min(1.0, max(0.0, (21 - (cage.value - self.mod("int"))) / 20))
        return 1.0

    def cage_passes(self, targeted):
        cage = self.foe.get("cage")
        if targeted and cage and self.dist() > 15:
            return d20() + self.mod("int") >= cage.value
        return True

    # ----- spells ----------------------------------------------------
    def spell_bonus_parts(self, ctx):
        """Flat bonuses some subclasses add to a spell's damage roll."""
        return []

    def spell_attack(self, name, level, rays, parts, kind="ranged", free=None):
        self.cast = {}
        self.spend(level, free)
        self.acted = True
        if not self.cage_passes(True):
            return
        for _ in range(rays):
            if self.foe.dead:
                break
            ctx = {"name": name}
            attack(self, self.foe, bonus=self.spell_atk, parts=parts, kind=kind,
                   spell=True, level=level, ctx=ctx)

    def hit_extra(self, tgt, ctx):
        return self.spell_bonus_parts(ctx) if ctx.get("spell") else []

    def save_spell(self, name, level, abil, parts, half=True, targeted=True, free=None,
                   on_fail=None):
        self.cast = {}
        self.spend(level, free)
        self.acted = True
        foe = self.foe
        if not self.cage_passes(targeted):
            return
        ctx = {"spell": True, "level": level, "name": name, "damage": True,
               "big": avg(parts) >= 0.2 * foe.max_hp}
        abil = self.save_ability(abil, ctx, commit=True)
        ok = saving_throw(foe, abil, self.dc, self, ctx)
        if ok and not half:
            return
        dmg = roll_damage(list(parts) + self.spell_bonus_parts(ctx))
        if ok:
            dmg = {k: v // 2 for k, v in dmg.items()}
        deal(foe, dmg, self, ctx)
        if not ok and on_fail and not foe.dead:
            on_fail()
        self.after_spell_damage(ctx)

    def after_spell_damage(self, ctx):
        pass

    def magic_missile(self, level):
        self.cast = {}
        self.spend(level)
        self.acted = True
        if not self.cage_passes(True) or self.foe.block_missiles():
            return
        darts = 2 + level
        ctx = {"spell": True, "level": level, "name": "magic missile"}
        deal(self.foe, roll_damage([(darts, 4, darts, "force")] + self.spell_bonus_parts(ctx)),
             self, ctx)
        self.after_spell_damage(ctx)

    def hold(self, level, name, free=None):
        self.spend(level, free)
        self.acted = True
        self.drop_conc()
        self.control_tries += 1
        foe = self.foe
        if not self.cage_passes(True):
            return
        ctx = {"spell": True, "level": level, "name": name, "control": True}
        abil = self.save_ability("wis", ctx, commit=True)
        if not saving_throw(foe, abil, self.dc, self, ctx):
            e = foe.add("paralyzed", self, value=(abil, self.dc, self))
            self.conc = Conc(name, [(foe, e)])

    # ----- choosing ---------------------------------------------------
    def options(self):
        """Every action worth considering this turn as (expected value, label, do)."""
        foe, dist, opts = self.foe, self.dist(), []
        if self.has("silenced"):
            return opts
        sight = self.can_see_foe()
        p = self.p_attack()
        cage_t = self.cage_factor(True)
        t = self.tier
        if dist <= 120:
            opts.append((p * 5.5 * t * cage_t, "fire bolt",
                         lambda: self.spell_attack("fire bolt", 0, 1, [(t, 10, 0, "fire")])))
        if dist <= 60 and sight:
            pw = self.p_save_fail("wis")
            die = 6.5 if foe.hp < foe.max_hp else 4.5
            opts.append((pw * die * t * cage_t, "toll the dead", self.toll_the_dead))
        if sight and dist <= 120:
            for lv in self.avail(1):
                if lv == 1 and self.slots[1] <= 1 and not self.free.get("shield"):
                    continue  # keep one first-level slot for shield
                darts = 2 + lv
                blocked = 0.9 if foe.caster and foe.can_shield_cheap() else 0
                opts.append((darts * 3.5 * cage_t * (1 - blocked), f"magic missile {lv}",
                             lambda lv=lv: self.magic_missile(lv)))
        if dist <= 120:
            for lv in self.avail(2):
                rays = 1 + lv
                opts.append((rays * p * 7 * cage_t, f"scorching ray {lv}",
                             lambda lv=lv, r=rays: self.spell_attack(
                                 "scorching ray", lv, r, [(2, 6, 0, "fire")])))
        pd = self.p_save_fail("dex", {"damage": True})
        if 25 <= dist <= 150:
            for lv in self.avail(3):
                n = 5 + lv
                opts.append((3.5 * n * (pd + (1 - pd) / 2), f"fireball {lv}",
                             lambda lv=lv, n=n: self.save_spell(
                                 "fireball", lv, "dex", [(n, 6, 0, "fire")], targeted=False)))
            for lv in self.avail(4):
                n = 10 + 2 * (lv - 4)
                opts.append((2.5 * n * (pd + (1 - pd) / 2) + pd * 12.5, f"vitriolic sphere {lv}",
                             lambda lv=lv, n=n: self.save_spell(
                                 "vitriolic sphere", lv, "dex", [(n, 4, 0, "acid")], targeted=False,
                                 on_fail=lambda: self.foe.add("dot", self, value=([(5, 4, 0, "acid")], self)))))
        if sight and dist <= 60:
            for lv in self.avail(6):
                n = 10 + 3 * (lv - 6)
                opts.append(((3.5 * n + 40) * pd * cage_t, f"disintegrate {lv}",
                             lambda lv=lv, n=n: self.save_spell(
                                 "disintegrate", lv, "dex", [(n, 6, 40, "force")], half=False)))
            pc = self.p_save_fail("con", {"damage": True})
            for lv in self.avail(7):
                opts.append((61.5 * (pc + (1 - pc) / 2) * cage_t, f"finger of death {lv}",
                             lambda lv=lv: self.save_spell(
                                 "finger of death", lv, "con", [(7, 8, 30, "necrotic")])))
        self.extra_options(opts)
        return opts

    def toll_the_dead(self):
        die = 12 if self.foe.hp < self.foe.max_hp else 8
        self.save_spell("toll the dead", 0, "wis", [(self.tier, die, 0, "necrotic")], half=False)

    def extra_options(self, opts):
        pass

    def control_option(self):
        """Hold person / hold monster when nothing is held yet and it's likely to land."""
        foe = self.foe
        if (self.conc or self.control_tries >= 2 or foe.incapacitated() or foe.has("restrained")
                or self.has("silenced") or not self.can_see_foe() or foe.hp < 0.3 * foe.max_hp):
            return None
        best = None
        pf = self.p_save_fail("wis", {"control": True}) * self.cage_factor(True)
        if foe.creature_type == "humanoid" and self.dist() <= 60 and self.avail(2):
            best = (pf, "hold person", lambda lv=self.avail(2)[0]: self.hold(lv, "hold person"))
        elif self.dist() <= 90 and self.avail(5) and foe.creature_type != "undead":
            best = (pf, "hold monster", lambda lv=self.avail(5)[0]: self.hold(lv, "hold monster"))
        for alt in self.extra_controls():
            if alt and (best is None or alt[0] > best[0]):
                best = alt
        if best and best[0] >= 0.4:
            return best
        return None

    def extra_controls(self):
        return []

    def choose(self):
        ctrl = self.control_option()
        if ctrl:
            return ctrl
        opts = self.options()
        return max(opts, key=lambda o: o[0]) if opts else None

    # ----- the turn ---------------------------------------------------
    def take_turn(self):
        self.keep_distance()
        plan = self.choose()
        self.bonus_before(plan)
        if plan and not self.dead:
            plan[2]()
        if not self.foe.dead and not self.dead:
            self.bonus_after(plan)
        if not self.foe.dead and not self.dead:
            self.keep_distance()

    def bonus_before(self, plan):
        pass

    def bonus_after(self, plan):
        pass

    def can_shield_cheap(self):
        return self.reaction and bool(self.can_shield())


class VerdantMage(Wizard):
    key, label = "verdant", "Verdant Mage"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.free["entangle"] = 1
        self.grove = max(1, self.mod("int")) if level >= 6 else 0
        self.veils = self.pb if level >= 10 else 0
        self.first_save_dis = level >= 14

    def ac(self):
        return super().ac() + (1 if self.level >= 10 else 0)

    def entangle(self):
        self.spend(0 if self.free.get("entangle") else self.avail(1)[0], "entangle")
        self.acted = True
        self.drop_conc()
        self.control_tries += 1
        foe = self.foe
        if not self.cage_passes(False):
            return
        if not saving_throw(foe, "str", self.dc, self, {"spell": True, "level": 1, "control": True,
                                                         "name": "entangle"}):
            e = foe.add("restrained", self, value=("escape", self.dc))
            self.conc = Conc("entangle", [(foe, e)])

    def extra_controls(self):
        if self.dist() <= 90 and (self.free.get("entangle") or self.avail(1)):
            pf = self.p_save_fail("str", {"control": True, "name": "entangle"})
            # Restrained stops a melee foe reaching you; a shooter or caster barely cares.
            impact = 0.8 if self.foe.style == "melee" else 0.35
            return [(pf * impact, "entangle", self.entangle)]
        return []

    def rootbind(self):
        self.acted = True
        foe = self.foe
        if not saving_throw(foe, "str", self.dc, self, {"spell": True, "level": 0, "name": "rootbind"}):
            foe.add("slow", self, until=("start", self), value=10)

    def extra_options(self, opts):
        foe = self.foe
        if self.dist() <= 30 and foe.style == "melee" and not self.engaged() and self.can_see_foe():
            sp = foe.speed_now()
            if sp >= self.dist() - 5 > sp - 10:  # the slow keeps it out of reach this round
                pf = self.p_save_fail("str", {"name": "rootbind"})
                opts.append((pf * foe.est_dpr(self), "rootbind", self.rootbind))

    def impose_save_mods(self, tgt, abil, ctx):
        # Master of Living Paths: disadvantage on the first save (each casting has one).
        return False, bool(self.first_save_dis and ctx.get("name") in ("entangle", "rootbind"))

    def on_failed_save(self, tgt, ctx):
        # Master of Living Paths: teleport 15 feet when a restrain/slow spell lands.
        if self.level >= 14 and ctx.get("name") in ("entangle", "rootbind") and self.engaged():
            move(self, False, 15, provoke=False)

    def save_reroll(self, abil, dc, src, ctx):
        if ctx.get("fear") and self.grove and self.reaction:
            self.grove -= 1
            self.reaction = False
            return d20() + self.save_bonus(abil) >= dc
        return False

    def bonus_before(self, plan):
        if self.veils and self.foe.style == "ranged" and not self.has("veiled"):
            self.veils -= 1
            self.add("veiled", self, until=("start", self))

    def defend_mods(self, att, ctx):
        dis = (self.has("veiled") and ctx["kind"] == "ranged" and not ctx.get("spell")
               and self.dist() > 10)
        return False, dis


class WarboundMage(Wizard):
    key, label = "warbound", "Warbound Mage"
    patch_sensitive = True
    can_oa = True

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.free["shield"] = 1
        self.beats = 0
        self.surged_turn = -1
        self.bfp_uses = self.pb if level >= 6 else 0
        self.bfp = 0              # HP burned this turn, waiting for a spell
        self.presence = max(1, self.mod("int")) if level >= 10 else 0
        self.presence_now = False
        self.warstorm = False
        self.warstorm_ready = level >= 14
        # After Patch 1: a martial weapon (rapier); before it, a dagger.
        self.wpn = (1, 8, "piercing") if patched else (1, 4, "piercing")
        self.wpn_bonus = self.mod("dex") + self.pb
        self.wpn_dmg = self.mod("dex")

    # War Drum and Battle Surge ---------------------------------------
    def after_hit_roll(self, tgt, ctx):
        if not self.patched:
            return
        if self.beats >= 3:
            if ctx["crit"]:
                return                    # the drum waits; no crash
            ctx["crit"] = True
            ctx["drum"] = True
            self.beats = 0
            self.add("crash", self, **self.until_my_next_end())
        else:
            self.beats += 1

    def after_hit(self, tgt, ctx, crit):
        if crit:
            self.battle_surge()

    def battle_surge(self):
        if self.surged_turn != self.turns:
            self.surged_turn = self.turns
            self.gain_thp(max(1, self.mod("int") + self.level))

    # Blood for Power, Crimson Presence, Warstorm ------------------------
    def spell_bonus_parts(self, ctx):
        out = []
        if self.bfp:
            if self.patched:
                out.append((0, 0, self.bfp, "fire"))
                self.bfp = 0
            else:
                out.append((0, 0, (self.bfp + 1) // 2, "fire"))   # every roll this turn
        if self.warstorm and not self.patched and not self.cast.get("warstorm"):
            self.cast["warstorm"] = True    # once per spell
            out.append((0, 0, self.mod("int"), "fire"))
        return out

    def impose_save_mods(self, tgt, abil, ctx):
        if ctx.get("damage") and self.presence and (self.presence_now or ctx.get("predict")):
            if not ctx.get("predict"):
                self.presence -= 1
                self.presence_now = False
            return False, True
        return False, False

    def booming_blade(self):
        self.acted = True
        foe, t = self.foe, self.tier
        extra = [(t - 1, 8, 0, "thunder")] if t > 1 else []
        n, die, dtype = self.wpn
        hit, _ = attack(self, foe, bonus=self.wpn_bonus, parts=[(n, die, self.wpn_dmg, dtype)] + extra,
                        kind="melee", weapon="blade", ctx={"cantrip": True})
        if hit and not foe.dead:
            foe.add("booming", self, until=("start", self), value=t)

    def on_foe_moved_away(self, mover):
        e = mover.take("booming")
        if e and e.source is self:
            deal(mover, roll_damage([(e.value, 8, 0, "thunder")]), self, {"spell": True})

    def opportunity_attack(self, tgt):
        n, die, dtype = self.wpn
        attack(self, tgt, bonus=self.wpn_bonus, parts=[(n, die, self.wpn_dmg, dtype)],
               kind="melee", weapon="blade")

    def enter_warstorm(self):
        self.warstorm_ready = False
        self.warstorm = True

    def extra_options(self, opts):
        foe = self.foe
        if self.engaged():
            adv, dis = attack_adv(self, foe, {"kind": "melee"})
            p = p_hit(self.wpn_bonus, foe.ac(), adv, dis)
            n, die, _ = self.wpn
            ev = p * (n * (die + 1) / 2 + self.wpn_dmg + (self.tier - 1) * 4.5)
            opts.append((ev, "booming blade", self.booming_blade))
        if self.warstorm_ready and not self.warstorm:
            if self.patched:
                gain = 0.55 * (4.5 + self.wpn_dmg) if self.engaged() else 0
            else:
                gain = self.mod("int")
            opts.append((gain * 3, "warstorm", self.enter_warstorm))

    def bonus_before(self, plan):
        if not plan:
            return
        label = plan[1]
        leveled = any(label.startswith(s) for s in
                      ("magic missile", "scorching ray", "fireball", "vitriolic", "disintegrate", "finger"))
        if leveled:
            if self.warstorm:
                deal(self, {"psychic": d(1, 6)}, None, {})
            if self.bfp_uses and self.hp - self.level > 0.5 * self.max_hp:
                self.bfp_uses -= 1
                self.bonus_used = True
                self.hp -= self.level
                self.bfp = self.level
            if self.presence and any(label.startswith(s) for s in ("fireball", "vitriolic", "disintegrate", "finger")):
                self.presence_now = True

    def bonus_after(self, plan):
        self.bfp = 0
        self.presence_now = False
        # Warstorm (after Patch 1): a melee weapon attack as a bonus action after casting.
        if self.warstorm and self.patched and plan and not self.bonus_used and self.engaged():
            self.bonus_used = True
            self.opportunity_attack(self.foe)

    def on_kill(self, tgt):
        self.battle_surge()


class StonewardenMage(Wizard):
    key, label = "stonewarden", "Stonewarden Mage"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.runic = max(1, self.mod("int")) if level >= 6 else 0

    def don_mage_armor(self):
        self.add("mage_armor", self)   # the free casting, no slot spent

    def ac(self):
        # Stoneguard: 13 + Dex, +1 more under mage armor.
        return 13 + self.mod("dex") + (1 if self.has("mage_armor") else 0) + self.total("ac")

    def react_to_damage(self, dmg, src, ctx):
        total = sum(dmg.values())
        if self.runic and self.reaction and not self.incapacitated() and total >= max(8, 0.15 * self.max_hp):
            self.runic -= 1
            self.reaction = False
            return {k: v // 2 for k, v in dmg.items()}
        return dmg


class HellboundMage(Wizard):
    key, label = "hellbound", "Hellbound Mage"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.free["hex"] = 1
        self.marks = self.pb
        self.curses = max(1, self.mod("int")) if level >= 6 else 0
        if level >= 10:
            self.devils_sight = True
            self.free["darkness"] = 1
        self.nexus_ready = level >= 14

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
        self.fight.zones.append(Zone("nexus", self, self.x, 20, follows=True))

    def hit_extra(self, tgt, ctx):
        out = super().hit_extra(tgt, ctx)
        e = tgt.get("hexed")
        if e and e.source is self:
            out.append((1, 6, 0, "necrotic"))
        return out

    def on_failed_save(self, tgt, ctx):
        m = tgt.get("shadow_mark")
        if m and m.source is self:
            tgt.remove(effect=m)
            deal(tgt, {"necrotic": max(1, self.mod("int"))}, self, {"spell": True})
        if self.curses and self.reaction and not tgt.dead and ctx.get("spell"):
            self.curses -= 1
            self.reaction = False
            tgt.add("next_atk_disadv", self, until=("end", tgt))

    def choose(self):
        # Hold first; darkness (seen through only by me) when no hold is worth casting.
        ctrl = self.control_option()
        if ctrl:
            return ctrl
        if (not self.conc and not self.has("silenced") and self.free.get("darkness")
                and not self.foe.devils_sight):
            return (99, "darkness", self.darkness)
        return super().choose()

    def extra_options(self, opts):
        if self.nexus_ready:
            pf = self.p_save_fail("wis")
            opts.append((max(1, self.mod("int")) * pf * 3, "pact nexus", self.pact_nexus))

    def bonus_before(self, plan):
        if not plan:
            return
        label = plan[1]
        if (not self.conc and label not in ("darkness", "hold person", "hold monster")
                and (self.free.get("hex") or self.avail(1))
                and any(label.startswith(s) for s in ("fire bolt", "scorching ray"))):
            self.bonus_used = True
            self.hex()
        elif self.marks and any(label.startswith(s) for s in
                                ("fireball", "vitriolic", "disintegrate", "finger", "hold")):
            self.bonus_used = True
            self.marks -= 1
            self.foe.add("shadow_mark", self, **self.until_my_next_end())


class SanguineMage(Wizard):
    key, label = "sanguine_mage", "Sanguine Mage"
    heals = True

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.free["inflict wounds"] = 1
        self.tethers = self.pb
        self.flux = max(1, self.mod("int")) if level >= 6 else 0
        self.overlord_ready = level >= 14
        self.overlord = False

    def save_ability(self, abil, ctx, commit=False):
        """Flux Manipulation: move the save onto the foe's weakest ability."""
        if not self.flux or not (ctx.get("control") or ctx.get("big")):
            return abil
        foe = self.foe
        best = min(("str", "dex", "con", "int", "wis", "cha"), key=foe.save_bonus)
        if foe.incapacitated() and abil in ("str", "dex"):
            return abil
        if foe.save_bonus(best) <= foe.save_bonus(abil) - 2:
            if commit:
                self.flux -= 1
            return best
        return abil

    def inflict_wounds(self):
        free = self.free.get("inflict wounds")
        lv = 1 if free else self.avail(1)[0]
        self.spell_attack("inflict wounds", 0 if free else lv, 1, [(2 + lv, 10, 0, "necrotic")],
                          kind="melee", free="inflict wounds")

    def extra_options(self, opts):
        if self.engaged() and (self.free.get("inflict wounds")) and not self.has("silenced"):
            p = self.p_attack("melee")
            opts.append((p * 16.5, "inflict wounds", self.inflict_wounds))

    def choose(self):
        if self.overlord_ready and self.foe.hp > 0.6 * self.foe.max_hp and not self.has("silenced"):
            return (99, "sanguine overlord", self.enter_overlord)
        return super().choose()

    def enter_overlord(self):
        self.overlord_ready = False
        self.overlord = True
        self.max_range = 30   # its save-flipping reaches 30 feet

    def flip_success(self, tgt, ctx):
        if (self.overlord and ctx.get("spell") and (ctx.get("control") or ctx.get("big"))
                and self.dist() <= 30 and self.hp > 25):
            deal(self, {"psychic": d(2, 8)}, None, {})
            return not self.dead
        return False

    def after_damage_dealt(self, tgt, amount, ctx):
        if self.my_turn() and not tgt.dead:
            tgt.remove("tethered")
            tgt.add("tethered", self, until=("start", self), skip=2)

    def after_spell_damage(self, ctx):
        # Overlord: push a damaged Large-or-smaller creature 10 feet (here: away).
        if self.overlord and not self.foe.dead and self.foe.style == "melee":
            foe = self.foe
            step = 10 if foe.x > self.x else -10
            foe.x = max(0, min(120, foe.x + step))

    def bonus_after(self, plan):
        foe = self.foe
        e = foe.get("tethered")
        if e and e.source is self and self.tethers and not self.bonus_used:
            self.tethers -= 1
            self.bonus_used = True
            dealt = deal(foe, roll_damage([(1, 6, 0, "necrotic")]), self, {"spell": True})
            self.heal(dealt)


class AetherMage(Wizard):
    key, label = "aether", "Aether Mage"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.fields = self.pb if level >= 10 else 0

    def bonus_before(self, plan):
        if self.fields and self.foe.caster and not self.has("null_field"):
            self.fields -= 1
            self.bonus_used = True
            self.add("null_field", self)

    def save_mods(self, abil, src, ctx):
        return bool(self.has("null_field") and ctx.get("spell")), False

    def save_reroll(self, abil, dc, src, ctx):
        if (self.has("null_field") and ctx.get("spell") and ctx.get("level", 0) <= 3
                and self.reaction and not self.incapacitated()):
            self.reaction = False
            return d20() + self.save_bonus(abil) >= dc
        return False

    def react_to_attack(self, att, ctx, total, ac):
        raised = super().react_to_attack(att, ctx, total, ac)
        if raised:
            return raised
        if (self.has("null_field") and ctx.get("spell") and ctx.get("level", 0) <= 3
                and self.reaction):
            self.reaction = False
            if d20() + ctx["bonus"] < ac:
                return 99
        return 0

    def resists(self, dtype, ctx):
        return self.level >= 14 and dtype in ("force", "psychic")


# =========================================================================
# Fighters
# =========================================================================

class Fighter(Hero):
    chassis = "Fighter"
    ranged = False
    weapon = None  # dict(name, n, die, dtype, kind, normal, long)

    def __init__(self, level, patched=True):
        primary = "dex" if self.ranged else "str"
        base = RANGE_BASE if self.ranged else AEGIS_BASE
        sc = scores_at(base, primary, level, (4, 6, 8, 12, 14, 16, 19))
        con = mod(sc["con"])
        hp = 10 + con + (level - 1) * (6 + con)
        super().__init__(level, patched, sc, ("str", "con"), hp, self.armor(level, sc))
        self.attacks = 1 + (level >= 5) + (level >= 11) + (level >= 20)
        self.surges = 1 + (level >= 17)
        self.second_wind = True
        self.indomitable = (level >= 9) + (level >= 13) + (level >= 17)
        self.atk_bonus = self.mod(primary) + self.pb + self.item + (2 if self.ranged else 0)
        self.dmg_bonus = self.mod(primary) + self.item
        self.action = True

    def armor(self, level, sc):
        raise NotImplementedError

    def est_dpr(self, target):
        w = self.weapon
        return self.attacks * p_hit(self.atk_bonus, target.ac()) * (w["n"] * (w["die"] + 1) / 2 + self.dmg_bonus)

    def weapon_attack(self, tgt, *, ctx=None, extra=(), weapon=None):
        w = weapon or self.weapon
        dis = w["kind"] == "ranged" and self.dist() > w["normal"] and not self.ignores_long_range()
        parts = [(w["n"], w["die"], self.dmg_bonus, w["dtype"])] + list(extra)
        return attack(self, tgt, bonus=self.atk_bonus, parts=parts, kind=w["kind"],
                      magical=self.item > 0, weapon=w["name"], dis=dis, ctx=ctx)

    def ignores_long_range(self):
        return False

    def can_attack(self):
        w = self.weapon
        if w["kind"] == "melee":
            return self.dist() <= self.reach
        return self.dist() <= w["long"]

    def opportunity_attack(self, tgt):
        if self.weapon["kind"] == "melee":
            self.weapon_attack(tgt, ctx={"oa": True})

    def save_reroll(self, abil, dc, src, ctx):
        if self.indomitable and (ctx.get("control") or ctx.get("big")):
            self.indomitable -= 1
            return d20() + self.save_bonus(abil) >= dc
        return False

    # ----- the turn ---------------------------------------------------
    def take_turn(self):
        self.action = True
        if self.has("restrained") and not self.ranged:
            self.try_escape()
        self.pre_bonus()
        if self.ranged:
            self.keep_distance()
        else:
            self.close_in()
        if self.action and self.can_attack() and not self.foe.dead:
            self.action = False
            self.main_action()
        if self.surges and self.can_attack() and not self.foe.dead and not self.dead:
            self.surges -= 1
            self.main_action()
        if not self.dead and not self.foe.dead:
            self.post_bonus()
        if self.ranged and not self.dead and not self.foe.dead:
            self.keep_distance()   # e.g. step off a foe the shot just rooted

    def try_escape(self):
        e = self.get("restrained")
        if e and e.value and e.value[0] == "escape":
            self.action = False
            if d20() + self.mod("str") + self.pb >= e.value[1]:
                self.remove(effect=e)
                src = e.source
                if src.conc and any(eff is e for _, eff in src.conc.held):
                    src.conc = None

    def close_in(self):
        sp = self.speed_now()
        if self.engaged() or sp == 0:
            return
        move(self, True, sp)
        if not self.engaged() and self.action and self.speed_now():
            self.action = False   # Dash
            move(self, True, sp)

    def main_action(self):
        self.attack_action()

    def attack_action(self):
        for i in range(self.attacks):
            if self.foe.dead or self.dead:
                break
            self.one_attack(i)

    def one_attack(self, i):
        self.weapon_attack(self.foe)

    def pre_bonus(self):
        pass

    def post_bonus(self):
        if not self.bonus_used and self.second_wind and self.hp < 0.5 * self.max_hp:
            self.second_wind = False
            self.bonus_used = True
            self.heal(d(1, 10) + self.level)


class Aegis(Fighter):
    """Strength, longsword and shield, Defense fighting style."""

    def __init__(self, level, patched=True):
        self.weapon = dict(name="longsword", n=1, die=8, dtype="slashing", kind="melee", normal=5, long=5)
        super().__init__(level, patched)

    def armor(self, level, sc):
        body = 16 if level < 5 else 18   # chain mail, then plate
        return body + 2 + 1


class Range(Fighter):
    """Dexterity, studded leather, Archery fighting style."""
    ranged = True
    style = "ranged"
    can_oa = False

    def armor(self, level, sc):
        return 12 + mod(sc["dex"])


class SanguineAegis(Aegis):
    key, label = "sanguine_aegis", "Sanguine Aegis"
    patch_sensitive = True
    heals = True

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.charges = 0
        self.max_charges = max(1, self.mod("con") + self.pb)
        self.pact = 0
        self.overdrive = False
        self.overdrive_ready = level >= 15
        self.leeched_turn = -1
        self.hit_since = True

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
        if self.hp < 0.4 * self.max_hp:
            if self.second_wind:
                self.second_wind = False
                self.bonus_used = True
                self.heal(d(1, 10) + self.level)
                return
            if self.charges:
                self.bonus_used = True
                self.heal(d(self.charges, 4))
                self.charges = 0
                return
        if self.level >= 7 and self.charges and self.dist() - 5 <= self.speed_now():
            self.pact = min(self.charges, self.level // 2)
            self.charges -= self.pact
            self.bonus_used = True

    def hit_extra(self, tgt, ctx):
        out = []
        if ctx["kind"] == "melee" and ctx.get("weapon"):
            if self.overdrive:
                out.append((1, 8, 0, "necrotic"))
            if self.pact:
                out.append((self.pact, 6, 0, "necrotic") if self.patched else (0, 0, self.pact, "slashing"))
                ctx["pact"] = True
                self.pact = 0
        return out

    def after_hit(self, tgt, ctx, crit):
        if ctx["kind"] != "melee" or not ctx.get("weapon"):
            return
        self.hit_since = True
        if self.patched:
            self.gain(2 if crit else 1)
        if ctx.get("pact") and not tgt.dead:
            dc = 8 + self.pb + self.mod("con")
            if not saving_throw(tgt, "con", dc, self, {"fear": True, "control": True}):
                tgt.add("frightened", self, **self.until_my_next_end())

    def after_damage_dealt(self, tgt, amount, ctx):
        if ctx.get("kind") == "melee" and ctx.get("weapon"):
            if not self.patched:
                self.gain(max(1, amount // 10))
            if self.leeched_turn != self.turns and self.my_turn():
                self.leeched_turn = self.turns
                self.heal(self.pb)

    def end_turn_hook(self):
        if self.level >= 10 and not self.hit_since:
            if d20() + self.save_bonus("wis") < 13:
                self.add("hunger", self, until=("end", self), skip=1)
        self.hit_since = False

    def attack_mods(self, tgt, ctx):
        scent = (self.patched and self.level >= 10 and ctx["kind"] == "melee"
                 and tgt.hp < tgt.max_hp / 2)
        return scent, False

    def post_bonus(self):
        self.pact = 0   # unspent Red Pact charges fade with the turn
        super().post_bonus()


class BulwarkAegis(Aegis):
    key, label = "bulwark", "Bulwark Aegis"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.base_ac += 1          # Living Wall
        self.fortress_ready = level >= 15
        self.immovable = level >= 7

    def end_turn_hook(self):
        if self.moved <= 10:
            self.add("anchored", self, until=("start", self))

    def resists(self, dtype, ctx):
        return self.has("fortress") or (self.has("anchored") and ctx.get("nonmagical"))

    def main_action(self):
        if self.fortress_ready and self.engaged() and self.foe.style == "melee" and not self.has("fortress"):
            self.fortress_ready = False
            self.add("fortress", self)
            self.add("speed0", self)
            return
        super().main_action()


class WardenAegis(Aegis):
    key, label = "warden", "Warden Aegis"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.shackles = self.pb
        self.anchor = None
        self.cage_ready = level >= 10
        self.dc = 8 + self.pb + self.mod("str")

    def on_initiative(self):
        if self.level >= 7:
            self.fight.zones.append(Zone("lockstep", self, self.x, 5, follows=True))

    def main_action(self):
        if self.cage_ready and self.foe.caster:
            self.cage_ready = False
            self.add("cage", self, value=8 + self.pb + self.mod("str"))
            return
        super().main_action()

    def take_turn(self):
        # Raise the Mana Cage before closing in on a caster, then walk.
        if self.cage_ready and self.foe.caster and not self.has("restrained"):
            self.pre_bonus()
            self.action = False
            self.cage_ready = False
            self.add("cage", self, value=8 + self.pb + self.mod("str"))
            move(self, True, self.speed_now())
            self.post_bonus()
            return
        super().take_turn()

    def post_bonus(self):
        if self.anchor is None and not self.bonus_used and self.dist() <= 30:
            self.bonus_used = True
            step = min(20, self.dist())
            center = self.x + (step if self.foe.x > self.x else -step)
            self.anchor = AnchorZone("anchor", self, center, 10)
            self.fight.zones.append(self.anchor)
        super().post_bonus()

    def after_hit(self, tgt, ctx, crit):
        if ctx.get("oa") and self.level >= 7 and not tgt.dead:
            tgt.add("speed0", self, until=("end", tgt))    # Lockstep Field
        elif self.shackles and tgt.style != "melee" and not tgt.dead and not ctx.get("oa"):
            self.shackles -= 1
            tgt.add("slow", self, until=("start", self), value=10)

    def defend_mods(self, att, ctx):
        # Mana Cage: ranged spell attacks at creatures in the dome have disadvantage.
        return False, bool(self.has("cage") and ctx.get("spell") and ctx["kind"] == "ranged")


class AnchorZone(Zone):
    """Gravitic Anchor: an enemy starting its turn in the area saves or can't move."""

    def on_enemy_turn_start(self, c):
        if not saving_throw(c, "str", self.owner.dc, self.owner, {"name": "anchor"}):
            c.add("speed0", self.owner, until=("start", c))


class CrystalArcher(Range):
    key, label = "archer", "Crystal Archer"
    patch_sensitive = True
    max_range = 120

    def __init__(self, level, patched=True):
        self.weapon = dict(name="longbow", n=1, die=8, dtype="piercing", kind="ranged", normal=150, long=600)
        super().__init__(level, patched)
        self.arrows = self.pb
        self.sights = self.pb if (level >= 7 and patched) else 0
        self.sight_turn = -1
        self.special_turn = -1
        self.volley_turn = -1
        self.rain_ready = level >= 15

    def ignores_long_range(self):
        return self.level >= 10

    def pre_bonus(self):
        if self.sights and not self.has("crystal_sight"):
            self.sights -= 1
            self.bonus_used = True
            self.add("crystal_sight", self)

    def pick_arrow(self, i):
        """The special arrow worth most on this shot, or None (one per turn)."""
        if not self.arrows or self.special_turn == self.turns:
            return None
        foe = self.foe
        avg_hit = 4.5 + self.dmg_bonus + 2
        left = self.attacks - 1 - i
        dc = 8 + self.pb + self.mod("dex")
        ev = {"red": 2.5}
        if self.engaged() and foe.style == "melee" and left and not getattr(foe, "immovable", False):
            # the push frees the remaining arrows from point-blank disadvantage
            p, pd = p_hit(self.atk_bonus, foe.ac()), p_hit(self.atk_bonus, foe.ac(), dis=True)
            ev["red"] += p_fail(foe.save_bonus("str"), dc) * left * (p - pd) * avg_hit
        sp = foe.speed_now()
        if not self.engaged() and foe.style == "melee" and sp >= self.dist() - 5 > sp - 10:
            ev["verdant"] = foe.est_dpr(self)          # it can't reach me this round
        if self.patched:
            ev["prismatic"] = 2.5 + (2.5 if self.hp < self.max_hp else 0)
            if self.dist() <= 10:
                ev["amber"] = 2.5 + self.pb          # the temporary HP land on me
            ev["violet"] = 0.125 * foe.est_dpr(self) / max(1, getattr(foe, "multi", 1))
            if foe.has("darkness"):
                p, pd = p_hit(self.atk_bonus, foe.ac()), p_hit(self.atk_bonus, foe.ac(), dis=True)
                ev["white"] = (left + self.attacks) * (p - pd) * avg_hit
        else:
            ev = {k: v for k, v in ev.items() if k in ("red", "verdant")}
        return max(ev, key=ev.get)

    def one_attack(self, i):
        arrow = self.pick_arrow(i)
        if arrow:
            self.arrows -= 1
            self.special_turn = self.turns
        self.weapon_attack(self.foe, ctx={"special": arrow, "attack_action": True})

    def hit_extra(self, tgt, ctx):
        out = []
        if ctx.get("weapon") == "longbow":
            if self.patched or self.moved <= 10:
                out.append((0, 0, 2, "piercing"))          # Marksman's Focus
            if self.has("crystal_sight") and self.sight_turn != self.turns and self.my_turn():
                self.sight_turn = self.turns
                out.append((1, 6, 0, "piercing"))
        sp = ctx.get("special")
        if sp == "red":
            out.append((1, 4, 0, "thunder"))
        elif sp == "prismatic":
            out.append((1, 4, 0, "necrotic"))
        return out

    def after_damage_dealt(self, tgt, amount, ctx):
        if ctx.get("special") == "prismatic":
            self.heal(d(1, 4))   # about the necrotic part of the hit

    def after_hit(self, tgt, ctx, crit):
        if tgt.dead:
            return
        self.arrow_effect(tgt, ctx.get("special"))
        if (self.level >= 10 and ctx.get("attack_action") and self.volley_turn != self.turns):
            self.volley_turn = self.turns
            dc = 8 + self.pb + self.mod("dex")
            if not saving_throw(tgt, "wis", dc, self, {}):
                tgt.add("unlocated", self, until=("start", self))

    def arrow_effect(self, tgt, sp):
        dc = 8 + self.pb + self.mod("dex")
        if sp == "verdant":
            tgt.add("slow", self, until=("start", self), value=10)
        elif sp == "red":
            if not getattr(tgt, "immovable", False) and not saving_throw(tgt, "str", dc, self, {}):
                step = 5 if tgt.x > self.x else -5
                tgt.x = max(0, min(120, tgt.x + step))
        elif sp == "white":
            tgt.add("white_dust", self, until=("start", self))

    def main_action(self):
        if self.rain_ready and self.dist() > 20:
            dc = 8 + self.pb + self.mod("dex")
            pf = p_fail(self.foe.save_bonus("dex"), dc)
            dice = (6, 3) if self.patched else (4, 2)
            rain = 4.5 * sum(dice) * (pf + (1 - pf) / 2)
            p = p_hit(self.atk_bonus, self.foe.ac())
            volley = self.attacks * p * (4.5 + self.dmg_bonus + 2)
            if rain > volley:
                self.rain_ready = False
                self.rain_of_shards(dc, dice)
                return
        super().main_action()

    def rain_of_shards(self, dc, dice):
        foe = self.foe
        arrow = None
        if self.patched and self.arrows:
            self.arrows -= 1
            arrow = "verdant" if foe.style == "melee" else "white" if foe.has("darkness") else None
        ok = saving_throw(foe, "dex", dc, self, {"big": True})
        dmg = roll_damage([(dice[0], 8, 0, "piercing"), (dice[1], 8, 0, "force")])
        if ok:
            dmg = {k: v // 2 for k, v in dmg.items()}
        deal(foe, dmg, self, {"weapon": "longbow", "magical": True})
        if not ok and arrow and not foe.dead:
            self.arrow_effect(foe, arrow)


class Gunman(Range):
    key, label = "gunman", "Gunman"
    patch_sensitive = True
    max_range = 40

    MUSKET = dict(name="musket", n=1, die=12, dtype="piercing", kind="ranged", normal=40, long=120)
    PISTOL = dict(name="pistol", n=1, die=10, dtype="piercing", kind="ranged", normal=30, long=90)

    def __init__(self, level, patched=True):
        self.weapon = dict(self.MUSKET)
        super().__init__(level, patched)
        self.shots = self.pb
        self.special_turn = -1
        self.barrage_ready = level >= 15

    def pick_shot(self, i):
        """The special round worth most on this shot, or None (one per turn)."""
        if not self.shots or self.special_turn == self.turns:
            return None
        foe = self.foe
        dc = 8 + self.pb + self.mod("dex")
        w = self.weapon
        avg_hit = w["n"] * (w["die"] + 1) / 2 + self.dmg_bonus
        p = p_hit(self.atk_bonus, foe.ac())
        threat = foe.est_dpr(self)
        # Powder Disruption rides on any special shot from 7th level: silence a caster.
        pd = 0.0
        if self.level >= 7 and foe.caster and not foe.has("silenced"):
            pd = p_fail(foe.save_bonus("con"), dc) * threat
        ev = {"red": 3.5 + pd}
        if self.level >= 7 and foe.caster:
            ev["violet"] = (p_fail(foe.save_bonus("con") - 2.5, dc)) * threat
        if self.patched:
            ev["prismatic"] = 3.5 + pd + (3 if foe.heals else 0)
            if self.attacks - 1 - i > 0:
                # -2 AC helps only my remaining attacks this turn (allies would gain too)
                ev["amber"] = pd + (self.attacks - 1 - i) * 0.1 * avg_hit
            reach = foe.style == "melee" and (self.engaged() or foe.speed_now() >= self.dist() - 5)
            if reach:
                ev["snare"] = pd + p_fail(foe.save_bonus("str"), dc) * threat
            if foe.has("mage_armor") or foe.has("darkness"):
                ev["white"] = pd + 3 * self.attacks * 0.15 * avg_hit
        return max(ev, key=ev.get)

    def one_attack(self, i):
        shot = self.pick_shot(i)
        if shot:
            self.shots -= 1
            self.special_turn = self.turns
        self.weapon_attack(self.foe, ctx={"special": shot, "firearm": True,
                                          "powder": self.level >= 7})
        # Recoil Step: slide 10 feet back after the shot, no opportunity attack.
        if self.level >= 10 and self.engaged() and not self.dead and self.foe.style == "melee":
            if move(self, False, 10, provoke=False) and not self.has("recoil"):
                self.add("ac", self, until=("start", self), value=2)
                self.add("recoil", self, until=("start", self))

    def hit_extra(self, tgt, ctx):
        sp = ctx.get("special")
        if sp == "red":
            return [(1, 6, 0, "force")]
        if sp == "prismatic":
            return [(1, 6, 0, "necrotic")]
        if ctx.get("barrage"):
            return [(2, 8, 0, "force")]
        return []

    def after_hit(self, tgt, ctx, crit):
        if tgt.dead:
            return
        sp = ctx.get("special")
        dc = 8 + self.pb + self.mod("dex")
        if sp == "snare":
            if not saving_throw(tgt, "str", dc, self, {}):
                tgt.add("speed0", self, until=("start", self))
        elif sp == "amber":
            tgt.add("ac", self, until=("start", self), value=-2)
        elif sp == "violet":
            tgt.add("next_save_pen", self, until=("start", self))
        elif sp == "prismatic":
            tgt.add("no_heal", self, until=("start", self))
        elif sp == "white":
            if tgt.has("darkness"):
                tgt.drop_conc()
            elif tgt.has("mage_armor"):
                tgt.remove("mage_armor")
        if sp and self.level >= 7 and not tgt.dead and self.my_turn():
            # Powder Disruption: no verbal or somatic spells until my next turn.
            if not saving_throw(tgt, "con", dc, self, {"control": True}):
                tgt.add("silenced", self, until=("start", self))

    def main_action(self):
        if self.barrage_ready and self.dist() <= self.weapon["normal"]:
            self.barrage_ready = False
            dc = 8 + self.pb + self.mod("dex")
            hit_any = False
            for _ in range(3):
                if self.foe.dead:
                    break
                hit, _ = self.weapon_attack(self.foe, ctx={"barrage": True, "firearm": True,
                                                           "powder": True})
                hit_any = hit_any or hit
            self.weapon = dict(self.PISTOL)   # the musket is spent; the backup pistol comes out
            self.max_range = 30
            if hit_any and not self.foe.dead:
                if not saving_throw(self.foe, "wis", dc, self, {"control": True}):
                    self.foe.add("stunned", self, until=("start", self))
            return
        super().main_action()


ROSTER = [VerdantMage, WarboundMage, StonewardenMage, HellboundMage, SanguineMage, AetherMage,
          SanguineAegis, BulwarkAegis, WardenAegis, CrystalArcher, Gunman]
BY_KEY = {c.key: c for c in ROSTER}


class SanguineMageNoSwap(SanguineMage):
    """What-if: Flux Manipulation keeps its damage-type swap but loses the save swap."""
    key, label = "sanguine_mage_noswap", "Sanguine Mage without Flux's save swap"

    def save_ability(self, abil, ctx, commit=False):
        return abil


VARIANTS = [SanguineMageNoSwap]
BY_KEY.update({c.key: c for c in VARIANTS})
