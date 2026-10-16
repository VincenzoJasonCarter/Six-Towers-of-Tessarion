"""The Wizard chassis the six Crystal Mages are built on: spell slots, the spell
list every mage knows, and the bot that picks a spell each turn.

The bot holds the most dangerous enemy when that's likely to land (control
first), and otherwise casts whatever has the highest expected damage this
turn, so it spends its biggest slots first. Area spells go where they catch
the most enemies and no allies.
"""
from engine import (Conc, Ctx, Dice, attack, attack_adv, avg, cage_over, d20, deal, halved, mod, p_fail, p_hit,
                    replace, roll_damage, saving_throw)

from .base import Hero, legendary_left, scores_at, tier

SLOTS = {
    1: [2], 2: [3], 3: [4, 2], 4: [4, 3], 5: [4, 3, 2], 6: [4, 3, 3], 7: [4, 3, 3, 1],
    8: [4, 3, 3, 2], 9: [4, 3, 3, 3, 1], 10: [4, 3, 3, 3, 2], 11: [4, 3, 3, 3, 2, 1],
    12: [4, 3, 3, 3, 2, 1], 13: [4, 3, 3, 3, 2, 1, 1], 14: [4, 3, 3, 3, 2, 1, 1],
    15: [4, 3, 3, 3, 2, 1, 1, 1],
}
WIZ_BASE = dict(str=8, dex=14, con=14, int=16, wis=12, cha=10)
CONTROL_TRIES = 2   # the bot gives up on Holds after this many (Legendary Resistance refunds one)


class Wizard(Hero):
    chassis = "Wizard"
    style = "caster"
    caster = True
    can_oa = False
    max_range = 60

    def __init__(self, level, gear=False):
        sc = scores_at(WIZ_BASE, "int", level, (4, 8, 12, 16, 19))
        con = mod(sc["con"])
        hp = 6 + con + (level - 1) * (4 + con)
        super().__init__(level, sc, ("int", "wis"), hp, 10 + mod(sc["dex"]))
        self.slots = [0] + SLOTS[level] + [0] * (9 - len(SLOTS[level]))   # slots[n]: nth-level slots left
        self.free = {}             # spell -> casts left that need no slot
        self.spell_atk = self.mod("int") + self.pb + self.item
        self.dc = 8 + self.spell_atk
        self.tier = tier(level)
        self.control_tries = 0
        self.don_mage_armor()

    def don_mage_armor(self):
        self.add("mage_armor", self)
        self.slots[1] -= 1         # cast before the day's fights

    def ac(self):
        return self.base_ac + (3 if self.has("mage_armor") else 0) + self.ac_bonus()

    def est_dpr(self, target):
        return 0.65 * 5.5 * self.tier + 3 * self.level

    # ----- slots -------------------------------------------------------------
    def avail(self, lo):
        """Slot levels from `lo` up that have a slot left."""
        return [lv for lv in range(lo, 10) if self.slots[lv] > 0]

    def spend(self, level, free_name=None):
        if free_name and self.free.get(free_name):
            self.free[free_name] -= 1
        elif level:
            self.slots[level] -= 1

    # ----- shield ------------------------------------------------------------
    def can_shield(self):
        return self.free.get("shield") or self.slots[1] > 0

    def shield_ready(self):
        return self.reaction and bool(self.can_shield())

    def use_shield(self):
        self.spend(1, "shield")
        self.reaction = False
        self.add("ac", self, until=("start", self), value=5)

    def hit_reaction(self, att, ctx, total, ac):
        if total < ac + 5 and self.can_shield():
            self.use_shield()
            return 5
        return 0

    def blocks_magic_missile(self):
        if self.reaction and not self.incapacitated() and self.can_shield():
            self.use_shield()
            return True
        return False

    # ----- predicting ----------------------------------------------------------
    def p_attack(self, tgt, kind="ranged"):
        adv, dis = attack_adv(self, tgt, Ctx(kind=kind, spell=True))
        return p_hit(self.spell_atk, tgt.ac(), adv, dis)

    def save_ability(self, tgt, abil, ctx, commit=False):
        """The ability the target actually saves with (Flux Manipulation changes it)."""
        return abil

    def p_save_fail(self, tgt, abil, ctx=None):
        ctx = replace(ctx or Ctx(), spell=True)
        abil = self.save_ability(tgt, abil, ctx)
        if abil in ("str", "dex") and tgt.incapacitated():
            return 1.0
        a1, d1 = tgt.my_save_adv(abil, self, ctx)
        a2, d2 = self.target_save_adv(tgt, abil, replace(ctx, predict=True))
        adv, dis = a1 or a2, d1 or d2 or (abil == "dex" and tgt.has("restrained"))
        for g in tgt.allies():
            a3, d3 = g.aura_save_adv(tgt, abil, self, ctx)
            adv, dis = adv or a3, dis or d3
        return p_fail(tgt.save_bonus(abil), self.dc, adv, dis)

    def p_half(self, tgt, abil, ctx=None):
        """Expected fraction of a save-for-half spell's damage that lands."""
        pf = self.p_save_fail(tgt, abil, ctx)
        return pf + (1 - pf) / 2

    def cage_factor(self, tgt, targeted=True):
        """Chance a spell at tgt gets through a Mana Cage (1 if there's none)."""
        w, cage = cage_over(tgt) if targeted else (None, None)
        if cage and abs(self.x - w.x) > 15:
            return min(1.0, max(0.0, (21 - (cage.value - self.mod("int"))) / 20))
        return 1.0

    def cage_passes(self, tgt, targeted=True):
        """Roll to get a spell at tgt through a Mana Cage."""
        w, cage = cage_over(tgt) if targeted else (None, None)
        if cage and abs(self.x - w.x) > 15:
            return d20() + self.mod("int") >= cage.value
        return True

    def in_range(self, rng, sight=True):
        return [e for e in self.enemies() if self.dist_to(e) <= rng and (not sight or self.can_see(e))]

    def aim(self, tgt):
        self.foe = tgt

    # ----- casting ---------------------------------------------------------------
    def spell_bonus_damage(self):
        """Extra [Dice] some subclasses add to a spell's damage (may use something up)."""
        return []

    def bonus_damage(self, tgt, ctx):
        return self.spell_bonus_damage() if ctx.spell else []

    def after_spell_damage(self, tgt, ctx):
        pass

    def spell_attack(self, name, level, rays, parts, kind="ranged", free=None, rng=120):
        """Fire bolt, scorching ray, inflict wounds: one attack per ray, moving to
        the most hurt enemy in range when the target drops."""
        self.spend(level, free)
        self.acted = True
        if not self.cage_passes(self.foe):
            return
        for _ in range(rays):
            if self.foe.dead:
                nxt = self.in_range(rng, sight=False)
                if not nxt:
                    break
                self.foe = min(nxt, key=lambda e: e.hp)
            attack(self, self.foe, bonus=self.spell_atk, parts=parts, kind=kind,
                   spell=True, level=level, ctx=Ctx(name=name))

    def save_spell(self, name, level, abil, parts, half=True, targets=None, free=None,
                   on_fail=None, targeted=True):
        """One spell, one damage roll, a save for each creature caught in it.
        `targeted`: aimed at a creature, so a Mana Cage over it gets a say."""
        self.spend(level, free)
        self.acted = True
        targets = [t for t in (targets or [self.foe]) if not t.dead]
        if targeted and targets and not self.cage_passes(targets[0]):
            return
        base = roll_damage(list(parts) + self.spell_bonus_damage())
        # The save's ability is chosen once for the whole spell (Flux Manipulation).
        lead = max(targets, key=lambda t: t.max_hp) if targets else None
        ab = abil
        if lead:
            ab = self.save_ability(lead, abil, Ctx(spell=True, level=level, damage=True,
                                                   big=avg(parts) >= 0.2 * lead.max_hp, group=targets),
                                   commit=True)
        stake = sum(base.values()) - (sum(v // 2 for v in base.values()) if half else 0)
        for t in targets:
            ctx = Ctx(spell=True, level=level, name=name, damage=True, single=len(targets) == 1,
                      big=avg(parts) >= 0.2 * t.max_hp, stake=stake)
            ok = saving_throw(t, ab, self.dc, self, ctx)
            if ok and not half:
                continue
            deal(t, halved(base) if ok else dict(base), self, ctx)
            if not ok and on_fail and not t.dead:
                on_fail(t)
            self.after_spell_damage(t, ctx)

    def magic_missile(self, level):
        self.spend(level)
        self.acted = True
        if not self.cage_passes(self.foe) or self.foe.blocks_magic_missile():
            return
        darts = 2 + level
        ctx = Ctx(spell=True, level=level, name="magic missile")
        deal(self.foe, roll_damage([Dice(darts, 4, "force", darts)] + self.spell_bonus_damage()), self, ctx)
        self.after_spell_damage(self.foe, ctx)

    def hold(self, level, name, free=None):
        """Hold Person or Hold Monster on self.foe."""
        self.spend(level, free)
        self.acted = True
        self.drop_conc()
        self.control_tries += 1
        foe = self.foe
        if not self.cage_passes(foe):
            return
        ctx = Ctx(spell=True, level=level, name=name, control=True, single=True)
        abil = self.save_ability(foe, "wis", ctx, commit=True)
        lr = legendary_left([foe])
        if not saving_throw(foe, abil, self.dc, self, ctx):
            e = foe.add("paralyzed", self, value=(abil, self.dc, self))   # value: the repeat save
            self.conc = Conc(name, [(foe, e)])
        self.refund_if_resisted(lr, [foe])

    def refund_if_resisted(self, before, targets):
        """Legendary Resistance is announced at the table, so a control spell it
        shrugged off doesn't count toward the bot's tries."""
        if legendary_left(targets) < before:
            self.control_tries -= 1

    def toll_the_dead(self):
        die = 12 if self.foe.hp < self.foe.max_hp else 8
        self.save_spell("toll the dead", 0, "wis", [Dice(self.tier, die, "necrotic")], half=False)

    # ----- choosing ---------------------------------------------------------------
    def options(self):
        """Every damaging action worth considering this turn, as (expected damage, label, do)."""
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
                         lambda: self.spell_attack("fire bolt", 0, 1, [Dice(t, 10, "fire")])))
        if dist <= 60 and sight:
            die = 6.5 if foe.hp < foe.max_hp else 4.5
            opts.append((self.p_save_fail(foe, "wis") * die * t * cage_t, "toll the dead", self.toll_the_dead))
        if sight and dist <= 120:
            for lv in self.avail(1):
                if lv == 1 and self.slots[1] <= 1 and not self.free.get("shield"):
                    continue  # keep one first-level slot for shield
                darts = 2 + lv
                blocked = 0.9 if foe.caster and foe.shield_ready() else 0
                opts.append((darts * 3.5 * cage_t * (1 - blocked), f"magic missile {lv}",
                             lambda lv=lv: self.magic_missile(lv)))
        if dist <= 120:
            for lv in self.avail(2):
                rays = 1 + lv
                opts.append((rays * p * 7 * cage_t, f"scorching ray {lv}",
                             lambda lv=lv, r=rays: self.spell_attack("scorching ray", lv, r, [Dice(2, 6, "fire")])))
        self.area_options(opts)
        if sight and dist <= 60:
            pd = self.p_save_fail(foe, "dex", Ctx(damage=True, big=True))
            for lv in self.avail(6):
                n = 10 + 3 * (lv - 6)
                opts.append(((3.5 * n + 40) * pd * cage_t, f"disintegrate {lv}",
                             lambda lv=lv, n=n: self.save_spell(
                                 "disintegrate", lv, "dex", [Dice(n, 6, "force", 40)], half=False)))
            ph = self.p_half(foe, "con", Ctx(damage=True, big=True))
            for lv in self.avail(7):
                opts.append((61.5 * ph * cage_t, f"finger of death {lv}",
                             lambda lv=lv: self.save_spell(
                                 "finger of death", lv, "con", [Dice(7, 8, "necrotic", 30)])))
        self.extra_options(opts)
        return opts

    def area_options(self, opts):
        """Fireball and vitriolic sphere, on the spot that catches the most enemies and no friends."""
        if not self.avail(3):
            return
        area = self.best_area(20, 150, score=lambda hit: sum(self.p_half(e, "dex") for e in hit))
        if not area:
            return
        hit, cx = area
        frac = sum(self.p_half(e, "dex") for e in hit)
        for lv in self.avail(3):
            n = 5 + lv
            opts.append((3.5 * n * frac, f"fireball {lv}",
                         lambda lv=lv, n=n, hit=hit: self.save_spell(
                             "fireball", lv, "dex", [Dice(n, 6, "fire")], targets=hit, targeted=False)))
        for lv in self.avail(4):
            n = 10 + 2 * (lv - 4)
            later = sum(self.p_save_fail(e, "dex") for e in hit) * 12.5
            opts.append((2.5 * n * frac + later, f"vitriolic sphere {lv}",
                         lambda lv=lv, n=n, hit=hit: self.save_spell(
                             "vitriolic sphere", lv, "dex", [Dice(n, 4, "acid")], targets=hit, targeted=False,
                             on_fail=lambda e: e.add("dot", self, value=([Dice(5, 4, "acid")], self)))))

    def extra_options(self, opts):
        """Subclasses add their own damaging options here."""

    def control_option(self):
        """Hold the most dangerous enemy that isn't held yet, if it's likely to land.
        Returns (chance, label, do) or None."""
        if self.conc or self.control_tries >= CONTROL_TRIES or self.has("silenced"):
            return None
        best = None   # (chance, score, label, do)
        for e in self.enemies():
            if (e.incapacitated() or e.has("restrained") or not self.can_see(e)
                    or e.hp < 0.3 * e.max_hp):
                continue
            pf = self.p_save_fail(e, "wis", Ctx(control=True)) * self.cage_factor(e)
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
        """Subclasses' own control spells, as [(chance x impact, label, do)]."""
        return []

    def choose(self):
        """This turn's plan: (value, label, do), or None."""
        ctrl = self.control_option()
        if ctrl:
            return ctrl
        opts = self.options()
        return max(opts, key=lambda o: o[0]) if opts else None

    # ----- the turn -------------------------------------------------------------------
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
        """Bonus action before the plan's action."""

    def bonus_after(self, plan):
        """Bonus action after it."""
