"""The eleven subclasses as fighting creatures, built from
lore-book/05-subclasses-skill.md on the 5e Wizard and Fighter chassis.

patched=False rebuilds the rules as they stood before Patch 1
(balance-patch.md) for the four subclasses it changed; the other seven
ignore the flag. Everything works one-on-one and in a party; features that
help allies only do something when there are allies.
"""
from engine import (TACTICS, Conc, Creature, Zone, attack, attack_adv, avg, cage_over, d, d20, deal, mod,
                    move, move_to, p_fail, p_hit, push, roll_damage, room_behind, saving_throw)


def prof(level):
    return 2 + (level - 1) // 4


def item(level):
    """+N of the weapon or spell focus everyone carries at this level."""
    return 0 if level < 5 else 1 if level < 15 else 2


def tier(level):
    return 1 + (level >= 5) + (level >= 11) + (level >= 17)


def legendary_left(creatures):
    """Legendary Resistances the creatures still have (heroes have none)."""
    return sum(getattr(c, "legendary", 0) for c in creatures)


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
    guard = False   # holds the line in front of the back rank instead of charging

    def __init__(self, level, patched, scores, save_profs, hp, ac):
        super().__init__(self.label, level, scores, save_profs, prof(level), hp, ac)
        self.patched = patched
        self.item = item(level)

    def until_my_next_end(self):
        """Effect timing for "until the end of your next turn"."""
        return dict(until=("end", self), skip=1 if self.my_turn() else 0)

    # ----- targets ----------------------------------------------------
    def reach_of_attacks(self):
        return self.reach if self.style == "melee" else self.max_range

    def pick_target(self):
        """Melee: the most hurt enemy within reach, else the nearest. Ranged and
        casters: focus fire on the most hurt enemy in range, else the nearest."""
        foes = self.enemies()
        if not foes:
            return None
        if self.guard and self.ward_ally():
            ward = self.ward_ally()
            return min(foes, key=lambda e: (e.dist_to(ward), e.hp))
        rng = self.reach_of_attacks()
        near = [e for e in foes if self.dist_to(e) <= rng]
        if near:
            return min(near, key=lambda e: (e.hp, self.dist_to(e)))
        return self.nearest(foes)

    def ward_ally(self):
        """The back-rank ally a guard stands in front of, if any."""
        backs = [a for a in self.allies() if a.style != "melee"]
        return min(backs, key=lambda a: (a.ac(), a.hp)) if backs else None


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
        return self.base_ac + (3 if self.has("mage_armor") else 0) + self.ac_bonus()

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

    def can_shield_cheap(self):
        return self.reaction and bool(self.can_shield())

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
    def p_attack(self, tgt, kind="ranged"):
        adv, dis = attack_adv(self, tgt, {"kind": kind, "spell": True})
        return p_hit(self.spell_atk, tgt.ac(), adv, dis)

    def save_ability(self, tgt, abil, ctx, commit=False):
        """Hook for Flux Manipulation; returns the ability the target actually saves with."""
        return abil

    def p_save_fail(self, tgt, abil, ctx=None):
        ctx = dict(ctx or {}, spell=True)
        abil = self.save_ability(tgt, abil, ctx)
        if abil in ("str", "dex") and tgt.incapacitated():
            return 1.0
        a1, d1 = tgt.save_mods(abil, self, ctx)
        a2, d2 = self.impose_save_mods(tgt, abil, dict(ctx, predict=True))
        adv, dis = a1 or a2, d1 or d2 or (abil == "dex" and tgt.has("restrained"))
        for g in tgt.allies():
            a3, d3 = g.aura_save_mods(tgt, abil, self, ctx)
            adv, dis = adv or a3, dis or d3
        return p_fail(tgt.save_bonus(abil), self.dc, adv, dis)

    def p_half(self, tgt, abil, ctx=None):
        """Expected fraction of a save-for-half spell's damage that lands."""
        pf = self.p_save_fail(tgt, abil, ctx)
        return pf + (1 - pf) / 2

    def cage_factor(self, tgt, targeted=True):
        w, cage = cage_over(tgt) if targeted else (None, None)
        if cage and abs(self.x - w.x) > 15:
            return min(1.0, max(0.0, (21 - (cage.value - self.mod("int"))) / 20))
        return 1.0

    def cage_passes(self, tgt, targeted=True):
        w, cage = cage_over(tgt) if targeted else (None, None)
        if cage and abs(self.x - w.x) > 15:
            return d20() + self.mod("int") >= cage.value
        return True

    def in_range(self, rng, sight=True):
        return [e for e in self.enemies() if self.dist_to(e) <= rng and (not sight or self.can_see(e))]

    def aim(self, tgt):
        self.foe = tgt

    # ----- spells ----------------------------------------------------
    def spell_bonus_parts(self, ctx):
        """Flat bonuses some subclasses add to a spell's damage roll."""
        return []

    def spell_attack(self, name, level, rays, parts, kind="ranged", free=None, rng=120):
        self.cast = {}
        self.spend(level, free)
        self.acted = True
        if not self.cage_passes(self.foe):
            return
        for _ in range(rays):
            if self.foe.dead:
                nxt = [e for e in self.in_range(rng, sight=False)]
                if not nxt:
                    break
                self.foe = min(nxt, key=lambda e: e.hp)
            attack(self, self.foe, bonus=self.spell_atk, parts=parts, kind=kind,
                   spell=True, level=level, ctx={"name": name})

    def hit_extra(self, tgt, ctx):
        return self.spell_bonus_parts(ctx) if ctx.get("spell") else []

    def save_spell(self, name, level, abil, parts, half=True, targets=None, free=None,
                   on_fail=None, targeted=True):
        """One spell, one damage roll, a save for each creature caught in it."""
        self.cast = {}
        self.spend(level, free)
        self.acted = True
        targets = [t for t in (targets or [self.foe]) if not t.dead]
        if targeted and targets and not self.cage_passes(targets[0]):
            return
        base = roll_damage(list(parts) + self.spell_bonus_parts({"spell": True}))
        # The save's ability is chosen once for the whole spell (Flux Manipulation).
        lead = max(targets, key=lambda t: t.max_hp) if targets else None
        ab = abil
        if lead:
            ab = self.save_ability(lead, abil, {"spell": True, "level": level, "damage": True,
                                                "big": avg(parts) >= 0.2 * lead.max_hp,
                                                "group": targets}, commit=True)
        for t in targets:
            ctx = {"spell": True, "level": level, "name": name, "damage": True,
                   "single": len(targets) == 1, "big": avg(parts) >= 0.2 * t.max_hp}
            ok = saving_throw(t, ab, self.dc, self, ctx)
            if ok and not half:
                continue
            dmg = {k: v // 2 for k, v in base.items()} if ok else dict(base)
            deal(t, dmg, self, ctx)
            if not ok and on_fail and not t.dead:
                on_fail(t)
            self.after_spell_damage(t, ctx)

    def after_spell_damage(self, tgt, ctx):
        pass

    def magic_missile(self, level):
        self.cast = {}
        self.spend(level)
        self.acted = True
        if not self.cage_passes(self.foe) or self.foe.block_missiles():
            return
        darts = 2 + level
        ctx = {"spell": True, "level": level, "name": "magic missile"}
        deal(self.foe, roll_damage([(darts, 4, darts, "force")] + self.spell_bonus_parts(ctx)), self, ctx)
        self.after_spell_damage(self.foe, ctx)

    def hold(self, level, name, free=None):
        self.spend(level, free)
        self.acted = True
        self.drop_conc()
        self.control_tries += 1
        foe = self.foe
        if not self.cage_passes(foe):
            return
        ctx = {"spell": True, "level": level, "name": name, "control": True, "single": True}
        abil = self.save_ability(foe, "wis", ctx, commit=True)
        lr = legendary_left([foe])
        if not saving_throw(foe, abil, self.dc, self, ctx):
            e = foe.add("paralyzed", self, value=(abil, self.dc, self))
            self.conc = Conc(name, [(foe, e)])
        self.refund_if_resisted(lr, [foe])

    def refund_if_resisted(self, before, targets):
        """Legendary Resistance is announced at the table, so a control spell it
        shrugged off doesn't count toward the bot's two tries."""
        if "legendary_refund" in TACTICS and legendary_left(targets) < before:
            self.control_tries -= 1

    def toll_the_dead(self):
        die = 12 if self.foe.hp < self.foe.max_hp else 8
        self.save_spell("toll the dead", 0, "wis", [(self.tier, die, 0, "necrotic")], half=False)

    # ----- choosing ---------------------------------------------------
    def options(self):
        """Every action worth considering this turn as (expected value, label, do)."""
        foe, opts = self.foe, []
        if self.has("silenced") or foe is None:
            return opts
        dist = self.dist()
        sight = self.can_see(foe)
        p = self.p_attack(foe)
        cage_t = self.cage_factor(foe)
        t = self.tier
        if dist <= 120:
            opts.append((p * 5.5 * t * cage_t, "fire bolt",
                         lambda: self.spell_attack("fire bolt", 0, 1, [(t, 10, 0, "fire")])))
        if dist <= 60 and sight:
            die = 6.5 if foe.hp < foe.max_hp else 4.5
            opts.append((self.p_save_fail(foe, "wis") * die * t * cage_t, "toll the dead", self.toll_the_dead))
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
                             lambda lv=lv, r=rays: self.spell_attack("scorching ray", lv, r, [(2, 6, 0, "fire")])))
        # Area spells: the spot that catches the most enemies and no friends.
        if self.avail(3):
            area = self.best_area(20, 150, score=lambda hit: sum(self.p_half(e, "dex") for e in hit))
            if area:
                hit, cx = area
                frac = sum(self.p_half(e, "dex") for e in hit)
                for lv in self.avail(3):
                    n = 5 + lv
                    opts.append((3.5 * n * frac, f"fireball {lv}",
                                 lambda lv=lv, n=n, hit=hit: self.save_spell(
                                     "fireball", lv, "dex", [(n, 6, 0, "fire")], targets=hit, targeted=False)))
                for lv in self.avail(4):
                    n = 10 + 2 * (lv - 4)
                    later = sum(self.p_save_fail(e, "dex") for e in hit) * 12.5
                    opts.append((2.5 * n * frac + later, f"vitriolic sphere {lv}",
                                 lambda lv=lv, n=n, hit=hit: self.save_spell(
                                     "vitriolic sphere", lv, "dex", [(n, 4, 0, "acid")], targets=hit,
                                     targeted=False,
                                     on_fail=lambda e: e.add("dot", self, value=([(5, 4, 0, "acid")], self)))))
        if sight and dist <= 60:
            pd = self.p_save_fail(foe, "dex", {"damage": True, "big": True})
            for lv in self.avail(6):
                n = 10 + 3 * (lv - 6)
                opts.append(((3.5 * n + 40) * pd * cage_t, f"disintegrate {lv}",
                             lambda lv=lv, n=n: self.save_spell(
                                 "disintegrate", lv, "dex", [(n, 6, 40, "force")], half=False)))
            ph = self.p_half(foe, "con", {"damage": True, "big": True})
            for lv in self.avail(7):
                opts.append((61.5 * ph * cage_t, f"finger of death {lv}",
                             lambda lv=lv: self.save_spell(
                                 "finger of death", lv, "con", [(7, 8, 30, "necrotic")])))
        self.extra_options(opts)
        return opts

    def extra_options(self, opts):
        pass

    def control_option(self):
        """Hold the most dangerous enemy that isn't held yet, if it's likely to land.
        Candidates are (chance x impact, label, do); paralysis has impact 1."""
        if self.conc or self.control_tries >= 2 or self.has("silenced"):
            return None
        best = None
        for e in self.enemies():
            if (e.incapacitated() or e.has("restrained") or not self.can_see(e)
                    or e.hp < 0.3 * e.max_hp):
                continue
            pf = self.p_save_fail(e, "wis", {"control": True}) * self.cage_factor(e)
            score = pf * (1 + e.est_dpr(self) / 100)
            if e.creature_type == "humanoid" and self.dist_to(e) <= 60 and self.avail(2):
                cand = (pf, score, "hold person",
                        lambda e=e, lv=self.avail(2)[0]: (self.aim(e), self.hold(lv, "hold person")))
            elif self.dist_to(e) <= 90 and self.avail(5) and e.creature_type != "undead":
                cand = (pf, score, "hold monster",
                        lambda e=e, lv=self.avail(5)[0]: (self.aim(e), self.hold(lv, "hold monster")))
            else:
                continue
            if best is None or cand[1] > best[1]:
                best = cand
        for alt in self.extra_controls():
            if alt and (best is None or alt[0] > best[0]):
                best = (alt[0], alt[0], alt[1], alt[2])
        if best and best[0] >= 0.4:
            return (best[0], best[2], best[3])
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
        if not self.dead and self.enemies():
            if self.foe is None or self.foe.dead:
                self.foe = self.pick_target()
            if self.foe:
                self.bonus_after(plan)
                self.keep_distance()

    def bonus_before(self, plan):
        pass

    def bonus_after(self, plan):
        pass


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

    def entangle(self, hit):
        self.spend(0 if self.free.get("entangle") else self.avail(1)[0], "entangle")
        self.acted = True
        self.drop_conc()
        self.control_tries += 1
        held = []
        lr = legendary_left(hit)
        for t in hit:
            if not saving_throw(t, "str", self.dc, self, {"spell": True, "level": 1, "control": True,
                                                          "name": "entangle"}):
                held.append((t, t.add("restrained", self, value=("escape", self.dc))))
        if held:
            self.conc = Conc("entangle", held)
        self.refund_if_resisted(lr, hit)

    def extra_controls(self):
        if not (self.free.get("entangle") or self.avail(1)):
            return []
        # Restrained stops a melee foe reaching anyone; a shooter or caster barely cares.
        impact = lambda e: 0.8 if e.style == "melee" else 0.35
        score = lambda hit: sum(self.p_save_fail(e, "str", {"control": True, "name": "entangle"}) * impact(e)
                                for e in hit if not e.has("restrained"))
        area = self.best_area(10, 90, score=score)
        if area and score(area[0]) > 0:
            return [(score(area[0]), "entangle", lambda hit=area[0]: self.entangle(hit))]
        return []

    def rootbind(self, tgt):
        self.acted = True
        extra = [e for e in self.enemies() if e is not tgt and e.dist_to(tgt) <= 5]
        for t in [tgt] + extra[:self.tier - 1]:
            if not saving_throw(t, "str", self.dc, self, {"spell": True, "level": 0, "name": "rootbind"}):
                t.add("slow", self, until=("start", self), value=10)

    def extra_options(self, opts):
        foe = self.foe
        if self.dist() <= 30 and foe.style == "melee" and not self.threatened() and self.can_see(foe):
            sp = foe.speed_now()
            if sp >= self.dist() - 5 > sp - 10:  # the slow keeps it out of reach this round
                pf = self.p_save_fail(foe, "str", {"name": "rootbind"})
                opts.append((pf * foe.est_dpr(self), "rootbind", lambda f=foe: self.rootbind(f)))

    def impose_save_mods(self, tgt, abil, ctx):
        # Master of Living Paths: disadvantage on the first save (each casting has one).
        return False, bool(self.first_save_dis and ctx.get("name") in ("entangle", "rootbind"))

    def on_failed_save(self, tgt, ctx):
        # Master of Living Paths: teleport 15 feet when a restrain/slow spell lands.
        if self.level >= 14 and ctx.get("name") in ("entangle", "rootbind") and self.threatened():
            threat = self.melee_threat()
            if threat:
                move(self, False, 15, provoke=False, ref=threat)

    def grove_reroll(self, who, abil, dc, ctx):
        if ctx.get("fear") and self.grove and self.reaction and not self.incapacitated() \
                and self.dist_to(who) <= 30:
            self.grove -= 1
            self.reaction = False
            return d20() + who.save_bonus(abil) >= dc
        return False

    def save_reroll(self, abil, dc, src, ctx):
        return self.grove_reroll(self, abil, dc, ctx)

    def ally_save_reroll(self, ally, abil, dc, src, ctx):
        return self.grove_reroll(ally, abil, dc, ctx)

    def bonus_before(self, plan):
        # Verdant Veil on whoever the enemy archers are most likely to shoot.
        if self.veils and any(e.style == "ranged" for e in self.enemies()):
            cands = [self] + [a for a in self.allies() if self.dist_to(a) <= 30]
            who = min(cands, key=lambda c: (c.ac(), c.hp))
            if not who.has("veiled"):
                self.veils -= 1
                self.bonus_used = True
                who.add("veiled", self, until=("start", self))


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

    def on_creature_moved(self, mover):
        e = mover.get("booming")
        if e and e.source is self:
            mover.remove(effect=e)
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
        if self.dist() <= 5:
            adv, dis = attack_adv(self, foe, {"kind": "melee"})
            p = p_hit(self.wpn_bonus, foe.ac(), adv, dis)
            n, die, _ = self.wpn
            ev = p * (n * (die + 1) / 2 + self.wpn_dmg + (self.tier - 1) * 4.5)
            opts.append((ev, "booming blade", self.booming_blade))
        if self.warstorm_ready and not self.warstorm:
            if self.patched:
                gain = 0.55 * (4.5 + self.wpn_dmg) if self.threatened() else 0
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
        if self.warstorm and self.patched and plan and not self.bonus_used and self.dist() <= 5:
            self.bonus_used = True
            self.opportunity_attack(self.foe)

    def on_kill(self, tgt):
        self.battle_surge()


class StonewardenMage(Wizard):
    key, label = "stonewarden", "Stonewarden Mage"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.runic = max(1, self.mod("int")) if level >= 6 else 0
        self.stoneheart_ready = level >= 14

    def don_mage_armor(self):
        self.add("mage_armor", self)   # the free casting, no slot spent

    def ac(self):
        # Stoneguard: 13 + Dex, +1 more under mage armor.
        return 13 + self.mod("dex") + (1 if self.has("mage_armor") else 0) + self.ac_bonus()

    def runic_bulwark(self, tgt, dmg):
        total = sum(dmg.values())
        if (self.runic and self.reaction and not self.incapacitated() and self.dist_to(tgt) <= 30
                and total >= max(8, 0.15 * tgt.max_hp)):
            self.runic -= 1
            self.reaction = False
            return {k: v // 2 for k, v in dmg.items()}
        return dmg

    def react_to_damage(self, dmg, src, ctx):
        return self.runic_bulwark(self, dmg)

    def ward(self, tgt, dmg, src, ctx):
        return self.runic_bulwark(tgt, dmg)

    # Stoneheart Aegis: +2 AC and advantage on Con saves for allies within 30 feet.
    def aura_ac(self, ally):
        return 2 if self.has("stoneheart") and self.dist_to(ally) <= 30 else 0

    def aura_save_mods(self, ally, abil, src, ctx):
        return bool(self.has("stoneheart") and abil == "con" and self.dist_to(ally) <= 30), False

    def choose(self):
        near = [a for a in self.allies() if self.dist_to(a) <= 30]
        if self.stoneheart_ready and len(near) >= 2 and not self.has("silenced"):
            return (99, "stoneheart aegis", self.raise_stoneheart)
        return super().choose()

    def raise_stoneheart(self):
        self.stoneheart_ready = False
        self.add("stoneheart", self)


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
            ev = sum(max(1, self.mod("int")) * self.p_save_fail(e, "wis") * 3 for e in near)
            opts.append((ev, "pact nexus", self.pact_nexus))

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

    def save_ability(self, tgt, abil, ctx, commit=False):
        """Flux Manipulation: move the save onto the target's weakest ability."""
        if not self.flux or not (ctx.get("control") or ctx.get("big")):
            return abil
        if tgt.incapacitated() and abil in ("str", "dex"):
            return abil
        group = ctx.get("group") or [tgt]
        total = lambda ab: sum(t.save_bonus(ab) for t in group) / len(group)
        best = min(("str", "dex", "con", "int", "wis", "cha"), key=total)
        if total(best) <= total(abil) - 2:
            if commit:
                self.flux -= 1
            return best
        return abil

    def inflict_wounds(self):
        free = self.free.get("inflict wounds")
        lv = 1 if free else self.avail(1)[0]
        self.spell_attack("inflict wounds", 0 if free else lv, 1, [(2 + lv, 10, 0, "necrotic")],
                          kind="melee", free="inflict wounds", rng=5)

    def extra_options(self, opts):
        if self.dist() <= 5 and self.free.get("inflict wounds") and not self.has("silenced"):
            opts.append((self.p_attack(self.foe, "melee") * 16.5, "inflict wounds", self.inflict_wounds))

    def choose(self):
        if (self.overlord_ready and not self.has("silenced")
                and sum(e.hp for e in self.enemies()) > 0.6 * sum(e.max_hp for e in self.enemies())):
            return (99, "sanguine overlord", self.enter_overlord)
        return super().choose()

    def enter_overlord(self):
        self.overlord_ready = False
        self.overlord = True
        self.max_range = 30   # its save-flipping reaches 30 feet

    def flip_success(self, tgt, ctx):
        if (self.overlord and ctx.get("spell") and (ctx.get("control") or ctx.get("big"))
                and tgt.side != self.side and self.dist_to(tgt) <= 30 and self.hp > 25):
            deal(self, {"psychic": d(2, 8)}, None, {})
            return not self.dead
        return False

    def after_damage_dealt(self, tgt, amount, ctx):
        if self.my_turn() and not tgt.dead:
            for e in self.enemies():
                m = e.get("tethered")
                if m and m.source is self:
                    e.remove(effect=m)        # one tether at a time
            tgt.add("tethered", self, until=("start", self), skip=2)

    def after_spell_damage(self, tgt, ctx):
        # Overlord: push a damaged Large-or-smaller creature 10 feet (here: away).
        if self.overlord and not tgt.dead and tgt.style == "melee":
            push(tgt, self, 10)

    def bonus_after(self, plan):
        if not self.tethers or self.bonus_used:
            return
        for e in self.enemies():
            m = e.get("tethered")
            if m and m.source is self:
                self.tethers -= 1
                self.bonus_used = True
                self.heal(deal(e, roll_damage([(1, 6, 0, "necrotic")]), self, {"spell": True}))
                return


class AetherMage(Wizard):
    key, label = "aether", "Aether Mage"

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.fields = self.pb if level >= 10 else 0
        self.anchor_ready = level >= 14

    def bonus_before(self, plan):
        if self.fields and any(e.caster for e in self.enemies()) and not self.has("null_field"):
            self.fields -= 1
            self.bonus_used = True
            self.add("null_field", self)

    def in_field(self, who):
        return self.has("null_field") and self.dist_to(who) <= 10

    def save_mods(self, abil, src, ctx):
        return bool(self.has("null_field") and ctx.get("spell")), False

    def aura_save_mods(self, ally, abil, src, ctx):
        return bool(self.in_field(ally) and ctx.get("spell")), False

    def field_reroll(self, who, abil, dc, ctx):
        if (self.in_field(who) and ctx.get("spell") and ctx.get("level", 0) <= 3 and ctx.get("single", True)
                and self.reaction and not self.incapacitated()):
            self.reaction = False
            return d20() + who.save_bonus(abil) >= dc
        return False

    def save_reroll(self, abil, dc, src, ctx):
        return self.field_reroll(self, abil, dc, ctx)

    def ally_save_reroll(self, ally, abil, dc, src, ctx):
        return self.field_reroll(ally, abil, dc, ctx)

    def react_to_attack(self, att, ctx, total, ac):
        raised = super().react_to_attack(att, ctx, total, ac)
        if raised:
            return raised
        return self.guard_attack_hit(att, self, ctx, total, ac)

    def guard_attack_hit(self, att, ally, ctx, total, ac):
        # Null Field: force a spell attack (3rd level or lower) to be rerolled.
        if (self.in_field(ally) and ctx.get("spell") and ctx.get("level", 0) <= 3
                and self.reaction and not self.incapacitated()):
            self.reaction = False
            if d20() + ctx["bonus"] < ac:
                return 99
        return 0

    def resists(self, dtype, ctx):
        return self.level >= 14 and dtype in ("force", "psychic")

    def save_from_death(self, tgt):
        # Anchor of Tessarion: once, someone within 30 feet drops to 1 HP instead.
        if self.anchor_ready and self.dist_to(tgt) <= 30 and (self.reaction or tgt is self):
            self.anchor_ready = False
            if tgt is not self:
                self.reaction = False
            return True
        return False


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

    def reach_of_attacks(self):
        return self.weapon["normal"] if self.ranged else self.reach

    def weapon_attack(self, tgt, *, ctx=None, extra=(), weapon=None):
        w = weapon or self.weapon
        dis = w["kind"] == "ranged" and self.dist_to(tgt) > w["normal"] and not self.ignores_long_range()
        parts = [(w["n"], w["die"], self.dmg_bonus, w["dtype"])] + list(extra)
        return attack(self, tgt, bonus=self.atk_bonus, parts=parts, kind=w["kind"],
                      magical=self.item > 0, weapon=w["name"], dis=dis, ctx=ctx)

    def ignores_long_range(self):
        return False

    def can_attack(self):
        if self.foe is None or self.foe.dead:
            return False
        w = self.weapon
        if w["kind"] == "melee":
            return self.dist() <= self.reach
        return self.dist() <= w["long"]

    def retarget(self):
        """After a kill: the next enemy this turn's attacks can still reach."""
        if self.foe is not None and not self.foe.dead:
            return True
        self.foe = self.pick_target()
        return self.can_attack()

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
        if self.action and self.can_attack():
            self.action = False
            self.main_action()
        if self.surges and self.retarget() and not self.dead:
            self.surges -= 1
            self.main_action()
        if not self.dead and self.enemies():
            self.retarget()
            if self.foe:
                self.post_bonus()
                if self.ranged:
                    self.keep_distance()   # e.g. step off a foe the shot just rooted

    def try_escape(self):
        e = self.get("restrained")
        if e and e.value and e.value[0] == "escape":
            self.action = False
            if d20() + self.mod("str") + self.pb >= e.value[1]:
                self.remove(effect=e)
                src = e.source
                if src.conc and any(eff is e for _, eff in src.conc.held):
                    src.conc.held = [(h, x) for h, x in src.conc.held if x is not e]
                    if not src.conc.held:
                        src.conc = None

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
        self.attack_action()

    def attack_action(self):
        for i in range(self.attacks):
            if self.dead or not self.retarget():
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
    guard = True

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

    def guard_attack(self, att, ally, ctx):
        # Living Wall: an attack on someone next to me is made with disadvantage.
        if self.reaction and not self.incapacitated() and self.dist_to(ally) <= 5 and att is not self:
            self.reaction = False
            return True
        return False

    def aura_ac(self, ally):
        bonus = 0
        if self.level >= 7 and self.dist_to(ally) <= 10:
            bonus += 1                   # Unmoving Bastion
        if self.has("fortress") and self.dist_to(ally) <= 10:
            bonus += 2                   # Fortress: half cover
        return bonus

    def aura_save_bonus(self, ally, abil):
        return 2 if self.has("fortress") and abil == "dex" and self.dist_to(ally) <= 10 else 0

    def intercept(self, ally, dmg, src, ctx):
        # Intercepting Guard: step in and take a big hit meant for someone within 10 feet.
        total = sum(dmg.values())
        if (self.level >= 10 and self.reaction and not self.incapacitated() and self.dist_to(ally) <= 10
                and (total >= 10 or total >= ally.hp) and self.hp > 0.3 * self.max_hp
                and (ctx.get("attack") or ctx.get("single", False))):
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


class WardenAegis(Aegis):
    key, label = "warden", "Warden Aegis"
    guard = True

    def __init__(self, level, patched=True):
        super().__init__(level, patched)
        self.shackles = self.pb
        self.anchor = None
        self.cage_ready = level >= 10
        self.dc = 8 + self.pb + self.mod("str")

    def on_initiative(self):
        if self.level >= 7:
            self.fight.zones.append(Zone("lockstep", self, self.x, 5, follows=True))

    def take_turn(self):
        # Raise the Mana Cage on turn one against spellcasters, then move up.
        if self.cage_ready and any(e.caster for e in self.enemies()) and not self.has("restrained"):
            self.pre_bonus()
            self.action = False
            self.cage_ready = False
            self.add("cage", self, value=8 + self.pb + self.mod("str"))
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
                center = max(self.x - 20, min(self.x + 20, near.x))
                self.anchor = AnchorZone("anchor", self, center, 10)
                self.fight.zones.append(self.anchor)
        super().post_bonus()

    def after_hit(self, tgt, ctx, crit):
        if ctx.get("oa") and self.level >= 7 and not tgt.dead:
            tgt.add("speed0", self, until=("end", tgt))    # Lockstep Field
        elif (self.shackles and not tgt.dead and not ctx.get("oa")
              and (tgt.style != "melee" or self.allies())):
            self.shackles -= 1
            tgt.add("slow", self, until=("start", self), value=10)

    def aura_save_bonus(self, ally, abil):
        # Field Commander: allies within 10 feet may use my Strength or Constitution.
        if self.level >= 15 and abil in ("str", "con") and self.dist_to(ally) <= 10:
            mine = max(self.mod("str"), self.mod("con"))
            return max(0, mine - ally.mod(abil))
        return 0


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

    def amber_ally(self, tgt):
        """Who would take Amber Dust's temporary HP: the most hurt friend near the target."""
        near = [c for c in [self] + self.allies() if c.dist_to(tgt) <= 10]
        return min(near, key=lambda c: c.hp / c.max_hp) if near else None

    def pick_arrow(self, i):
        """The special arrow worth most on this shot, or None (one per turn)."""
        if not self.arrows or self.special_turn == self.turns:
            return None
        foe = self.foe
        avg_hit = 4.5 + self.dmg_bonus + 2
        left = self.attacks - 1 - i
        dc = 8 + self.pb + self.mod("dex")
        ev = {"red": 2.5}
        if self.dist() <= 5 and foe.style == "melee" and left and not getattr(foe, "immovable", False):
            # the push frees the remaining arrows from point-blank disadvantage
            p, pd = p_hit(self.atk_bonus, foe.ac()), p_hit(self.atk_bonus, foe.ac(), dis=True)
            ev["red"] += p_fail(foe.save_bonus("str"), dc) * left * (p - pd) * avg_hit
        sp = foe.speed_now()
        closest = min([self] + self.allies(), key=lambda c: c.dist_to(foe))
        if foe.style == "melee" and sp >= foe.dist_to(closest) - 5 > sp - 10:
            ev["verdant"] = foe.est_dpr(closest)          # it can't reach anyone this round
        if self.patched:
            ev["prismatic"] = 2.5 + (2.5 if self.hp < self.max_hp else 0)
            if self.amber_ally(foe):
                ev["amber"] = 2.5 + self.pb
            ev["violet"] = 0.125 * foe.est_dpr(closest) / max(1, getattr(foe, "multi", 1))
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
                push(tgt, self, 5)
        elif sp == "amber":
            who = self.amber_ally(tgt)
            if who:
                who.gain_thp(d(1, 4) + self.pb)
        elif sp == "white":
            tgt.add("white_dust", self, until=("start", self))

    def main_action(self):
        if self.rain_ready:
            dc = 8 + self.pb + self.mod("dex")
            dice = (6, 3) if self.patched else (4, 2)
            frac = lambda hit: sum(p_fail(e.save_bonus("dex"), dc) / 2 + 0.5 for e in hit)
            area = self.best_area(20, self.weapon["long"], score=frac)
            if area:
                rain = 4.5 * sum(dice) * frac(area[0])
                p = p_hit(self.atk_bonus, self.foe.ac())
                volley = self.attacks * p * (4.5 + self.dmg_bonus + 2)
                if rain > volley:
                    self.rain_ready = False
                    self.rain_of_shards(dc, dice, area[0])
                    return
        super().main_action()

    def rain_of_shards(self, dc, dice, hit):
        arrow = None
        if self.patched and self.arrows:
            self.arrows -= 1
            arrow = "verdant" if any(e.style == "melee" for e in hit) else None
        dmg = roll_damage([(dice[0], 8, 0, "piercing"), (dice[1], 8, 0, "force")])
        for e in hit:
            ok = saving_throw(e, "dex", dc, self, {"big": True})
            deal(e, {k: v // 2 for k, v in dmg.items()} if ok else dict(dmg), self,
                 {"weapon": "longbow", "magical": True})
            if not ok and arrow and not e.dead:
                self.arrow_effect(e, arrow)


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

    def pick_target(self):
        # From 7th level, a spellcaster in range is the Gunman's first job.
        if self.level >= 7:
            casters = [e for e in self.enemies() if e.caster and self.dist_to(e) <= self.weapon["long"]
                       and not e.has("silenced")]
            if casters:
                return min(casters, key=lambda e: e.hp)
        return super().pick_target()

    def pick_shot(self, i):
        """The special round worth most on this shot, or None (one per turn)."""
        if not self.shots or self.special_turn == self.turns:
            return None
        foe = self.foe
        dc = 8 + self.pb + self.mod("dex")
        w = self.weapon
        avg_hit = w["n"] * (w["die"] + 1) / 2 + self.dmg_bonus
        closest = min([self] + self.allies(), key=lambda c: c.dist_to(foe))
        threat = foe.est_dpr(closest)
        # Powder Disruption rides on any special shot from 7th level: silence a caster.
        pd = 0.0
        if self.level >= 7 and foe.caster and not foe.has("silenced"):
            pd = p_fail(foe.save_bonus("con"), dc) * threat
        ev = {"red": 3.5 + pd}
        if self.level >= 7 and foe.caster:
            ev["violet"] = (p_fail(foe.save_bonus("con") - 2.5, dc)) * threat
        if self.patched:
            ev["prismatic"] = 3.5 + pd + (3 if foe.heals else 0)
            if self.attacks - 1 - i > 0 or self.allies():
                # -2 AC helps my remaining attacks this turn and every ally's until my next turn
                swings = (self.attacks - 1 - i) + sum(getattr(a, "attacks", 0) for a in self.allies())
                ev["amber"] = pd + swings * 0.1 * avg_hit
            reach = foe.style == "melee" and (self.dist() <= 5 or foe.speed_now() >= foe.dist_to(closest) - 5)
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
        self.weapon_attack(self.foe, ctx={"special": shot, "firearm": True, "powder": self.level >= 7})
        # Recoil Step: slide 10 feet back after the shot, no opportunity attack.
        threat = self.melee_threat()
        if self.level >= 10 and threat and self.dist_to(threat) <= 5 and not self.dead:
            if move(self, False, 10, provoke=False, ref=threat) and not self.has("recoil"):
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
            struck = []
            for _ in range(3):
                if not self.retarget():
                    break
                hit, _ = self.weapon_attack(self.foe, ctx={"barrage": True, "firearm": True, "powder": True})
                if hit and self.foe not in struck:
                    struck.append(self.foe)
            self.weapon = dict(self.PISTOL)   # the musket is spent; the backup pistol comes out
            self.max_range = 30
            for t in struck:
                if not t.dead and not saving_throw(t, "wis", dc, self, {"control": True}):
                    t.add("stunned", self, until=("start", self))
            return
        super().main_action()


ROSTER = [VerdantMage, WarboundMage, StonewardenMage, HellboundMage, SanguineMage, AetherMage,
          SanguineAegis, BulwarkAegis, WardenAegis, CrystalArcher, Gunman]
BY_KEY = {c.key: c for c in ROSTER}


class SanguineMageNoSwap(SanguineMage):
    """What-if: Flux Manipulation keeps its damage-type swap but loses the save swap."""
    key, label = "sanguine_mage_noswap", "Sanguine Mage without Flux's save swap"

    def save_ability(self, tgt, abil, ctx, commit=False):
        return abil


VARIANTS = [SanguineMageNoSwap]
BY_KEY.update({c.key: c for c in VARIANTS})
