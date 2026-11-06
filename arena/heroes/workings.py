"""Common Workings (lore-book chapter 27): the Aether Hall's general spells,
as something any Crystal Mage can learn. `with_workings(cls, env)` gives a mage
class every working below on top of its own kit; workings.py (the runner) fights
parties with and without it.

Most workings need something in the room: a rug to pull, a puddle to boil,
something hanging to make heavier. The arena has none of that, so `env` says
what is there:

- "bare":      floor, walls and ceiling only (stone or earth underfoot).
- "furnished": also loose objects, liquid, cloth on the floor and something
               hanging overhead (one rug and one hanging thing per fight).

Modelled, and how they read on the line:

| Working | Needs | Read as |
|---|---|---|
| Throw the Book | furnished | ranged spell attack, 1d10 per tier bludgeoning, 60 ft |
| Flash Boil | furnished | Con save, 1d8 per tier fire, 5 ft around a puddle anywhere in 60 ft |
| Rug Pull | furnished | once: Dex save or prone, a 15-ft cloth under the enemies |
| Slip & Grip | bare | a 5-ft square of difficult terrain (two from 5th), placed in a charger's way |
| Mind the Floor | bare | conc.: 20-ft square, difficult; Dex save or prone on entering or starting a turn there |
| Assessed Weight | furnished | once: the thing overhead falls, 4d10 Dex half |
| Banked Fire | bare | conc.: a 10-ft patch of heated floor, 1d6 fire to whoever starts a turn on it |
| Fault Line | bare | trench from the caster's feet: Dex save or 1d6 and prone |
| Thread Bridge (net) | bare | conc.: 10-ft square, difficult; Dex save or restrained (escape vs DC) on appearing or entering |
| Red Tape | bare | conc.: Str save or restrained (escape vs DC); +1 target per slot level above 2nd |
| Matter Conversion | bare | conc.: the floor ahead turns to a 30-ft pool of difficult terrain (touch, so from the caster) |
| Which Way Is Down | bare | conc.: 20-ft cube, gravity up: Dex save or fall 2d6 onto the ceiling, prone; a melee creature up there spends its next turn getting down (another 2d6). On a success it climbs at half speed |
| Not My Department | bare | reaction before an attack roll: Wis save or the attacker picks another target in reach |
| Overtime | bare | the house rule's short rest: the mage and allies within 30 ft back to full HP, once a fight |

Zones and restraints catch enemies only, as the arena's other zones do: on a
real map a party steps around its own slick floor. Not modelled (no fight value
on the line, or nothing for them to work on): Harvest Minute, Not Yet,
Peephole, Pocket Echo, Teacup Everstorm, Put It Back (cover isn't modelled),
Hawker's Shell, Harvest Hours, Payment Deferred (nobody falls), Window Tax,
Tide Clerk (no water), Wrong Door, Local Forecast (it takes a minute to
arrive), Glow Test, Receipt, Look Up.
"""
from collections import Counter

from engine import Conc, Ctx, Dice, Effect, Zone, avg, deal, p_hit, roll_damage, saving_throw

from .base import legendary_left

ENVIRONMENTS = ("bare", "furnished")


class SpellZone(Zone):
    """A zone that lasts as long as its owner's concentration on `spell` (or the fight, if None)."""

    def __init__(self, name, owner, center, radius, difficult=False, spell=None):
        super().__init__(name, owner, center, radius, difficult=difficult)
        self.spell = spell
        self.active = True

    def covers(self, pos):
        return (self.active and super().covers(pos)
                and (self.spell is None or self.owner.conc is self.spell))


class Slick(SpellZone):
    """Mind the Floor: Dex save or prone on entering or starting a turn inside."""

    def __init__(self, owner, center, radius, level, spell):
        super().__init__("mind the floor", owner, center, radius, difficult=True, spell=spell)
        self.level = level

    def trip(self, c):
        if not c.has("prone") and not c.has("aloft"):
            if not saving_throw(c, "dex", self.owner.dc, self.owner,
                                Ctx(spell=True, level=self.level, name="mind the floor")):
                c.add("prone", self.owner)

    def on_enemy_turn_start(self, c):
        self.trip(c)

    def on_enemy_enter(self, c):
        self.trip(c)


class Net(SpellZone):
    """Thread Bridge's net: Dex save or restrained on entering."""

    def __init__(self, owner, center, spell):
        super().__init__("thread net", owner, center, 5, difficult=True, spell=spell)

    def on_enemy_enter(self, c):
        self.owner.restrain(c, "dex", 2, "thread net", self.spell)


class Heat(SpellZone):
    """Banked Fire's receiver: 1d6 fire to whoever starts a turn on it."""

    def __init__(self, owner, center, spell):
        super().__init__("banked fire", owner, center, 5, spell=spell)

    def on_enemy_turn_start(self, c):
        deal(c, roll_damage([Dice(1, 6, "fire")]), self.owner, Ctx(spell=True, level=1, name="banked fire"))


class Squares(SpellZone):
    """Slip & Grip: one or two 5-foot squares of difficult terrain."""

    def __init__(self, owner, squares):
        super().__init__("slip & grip", owner, squares[0], 0, difficult=True)
        self.squares = set(squares)

    def covers(self, pos):
        return self.active and not self.owner.dead and pos in self.squares


class Gravity(SpellZone):
    """Which Way Is Down, pulling toward the ceiling of a 20-foot cube."""

    def __init__(self, owner, center, spell):
        super().__init__("which way is down", owner, center, 10, spell=spell)
        self.aloft = []

    def pull(self, c):
        if c.has("aloft") or c.dead:
            return
        if saving_throw(c, "dex", self.owner.dc, self.owner,
                        Ctx(spell=True, level=3, control=True, name="which way is down")):
            c.add("slow", self.owner, until=("end", c), value=c.base_speed // 2)   # climbing
            return
        self.fall(c)
        if not c.dead:
            c.add("aloft", self.owner, value=self)
            c.add("prone", self.owner)
            self.aloft.append(c)
            if c.my_turn():
                c.add("speed0", self.owner, until=("end", c))   # it stops where it fell

    def fall(self, c):
        deal(c, roll_damage([Dice(2, 6, "bludgeoning")]), self.owner,
             Ctx(spell=True, level=3, name="which way is down"))

    def on_enemy_enter(self, c):
        self.pull(c)

    def on_enemy_turn_start(self, c):
        if not c.has("aloft"):
            c.add("slow", self.owner, until=("end", c), value=c.base_speed // 2)
        elif c.style == "melee":
            self.climb_down(c)

    def climb_down(self, c):
        """A melee creature on the ceiling walks off the cube's edge toward the
        party, falls, and lands prone: its turn goes on getting down."""
        c.remove("aloft")
        if c in self.aloft:
            self.aloft.remove(c)
        near = c.nearest_enemy()
        side = 1 if near is None or near.x >= self.center() else -1
        c.x = max(0, min(120, self.center() + side * (self.radius + 5)))
        self.fall(c)
        if not c.dead:
            c.add("prone", self.owner)
            c.add("stunned", self.owner, until=("end", c))

    def release(self):
        """The spell ends: everyone still up there falls."""
        for c in list(self.aloft):
            if not c.dead and c.has("aloft"):
                c.remove("aloft")
                self.fall(c)
                if not c.dead:
                    c.add("prone", self.owner)
        self.aloft = []
        self.active = False


class Workings:
    """Mixin: put it before a Wizard subclass. `workings_env` is set by with_workings()."""
    workings_env = "bare"
    workings_without = frozenset()   # workings left out (workings.py --without)

    def knows(self, name):
        return name not in self.workings_without

    def __init__(self, level, gear=False):
        super().__init__(level, gear)
        furnished = self.workings_env == "furnished"
        self.loose = self.liquid = furnished
        self.rugs = self.hanging = 1 if furnished else 0
        self.slip = None
        self.gravity = None
        self.cast_log = Counter()

    # ----- helpers ------------------------------------------------------------------
    def slot_for(self, lo):
        """The lowest slot from `lo` up, keeping one 1st-level slot back for shield."""
        for lv in self.avail(lo):
            if lv == 1 and self.slots[1] <= 1 and not self.free.get("shield"):
                continue
            return lv
        return None

    def cast(self, name, level):
        self.spend(level)
        self.acted = True
        self.cast_log[name] += 1

    def hold_on(self, name, held=()):
        """Concentrate on `name`. The placeholder keeps the spell up when every
        creature it holds has broken free (it still covers its ground)."""
        self.drop_conc()
        self.conc = Conc(name, list(held) + [(self, Effect("holding", self))])
        return self.conc

    def drop_conc(self):
        if self.gravity is not None and self.conc is self.gravity.spell:
            g, self.gravity = self.gravity, None
            g.release()
        super().drop_conc()

    def workings_save(self, t, abil, ctx):
        """A save against a working, through Flux Manipulation like any other spell."""
        return saving_throw(t, self.save_ability(t, abil, ctx, commit=True), self.dc, self, ctx)

    def restrain(self, t, abil, level, name, spell):
        if t.dead or t.has("restrained") or t.incapacitated():
            return
        if not self.workings_save(t, abil, Ctx(spell=True, level=level, control=True, name=name)):
            e = t.add("restrained", self, value=("escape", self.dc))
            if spell is not None and self.conc is spell:
                spell.held.insert(0, (t, e))

    def p_save(self, t, abil, control=False):
        return self.p_save_fail(t, abil, Ctx(control=control))

    @staticmethod
    def weight(e, melee, other):
        return melee if e.style == "melee" else other

    def threat_gap(self, e):
        """Feet a melee enemy still has to cover to reach the nearest of us."""
        near = e.nearest_enemy()
        return (e.dist_to(near) - e.reach) if near else 999

    def prone_value(self, e):
        """Rough worth, in HP, of knocking e down: our melee swings at it get
        advantage until its turn, our ranged ones disadvantage, and standing up
        costs it half its speed, which can keep a charger from reaching anyone."""
        melee = sum(1 for a in self.allies() if a.style == "melee" and a.dist_to(e) <= 35)
        ranged = sum(1 for a in self.allies() + [self] if a.style != "melee")
        v = 2.5 * melee - 1.0 * ranged
        gap = self.threat_gap(e)
        if e.style == "melee" and e.base_speed / 2 < gap <= e.base_speed:
            v += 0.8 * e.est_dpr(self)
        return max(0.0, v)

    def spot_clear(self, center, radius):
        return not any(abs(c.x - center) <= radius for c in [self] + self.allies())

    # ----- control: competes with Hold (wizard.control_option) -------------------------
    def extra_controls(self):
        out = list(super().extra_controls())
        if self.conc:
            return out
        out += [self.mind_the_floor_option(), self.thread_net_option(), self.red_tape_option(),
                self.gravity_option(), self.matter_option()]
        return [o for o in out if o]

    def mind_the_floor_option(self):
        if not self.knows("mind the floor"):
            return None
        lv = self.slot_for(1)
        if lv is None:
            return None
        def score(hit):
            return sum(self.p_save(e, "dex") * self.weight(e, 0.5, 0.2) for e in hit if not e.has("prone"))
        area = self.best_area(10, 60, score=score)
        if not area or score(area[0]) <= 0:
            return None
        hit, cx = area
        def do():
            self.cast("mind the floor", lv)
            spell = self.hold_on("mind the floor")
            self.fight.zones.append(Slick(self, cx, 10, lv, spell))   # they save on entering or starting a turn there
        return (score(hit), "mind the floor", do)

    def thread_net_option(self):
        if not self.knows("thread bridge (net)"):
            return None
        lv = self.slot_for(2)
        if lv is None:
            return None
        def score(hit):
            return sum(self.p_save(e, "dex", True) * self.weight(e, 0.8, 0.35)
                       for e in hit if not e.has("restrained"))
        area = self.best_area(5, 60, score=score)
        if not area or score(area[0]) <= 0:
            return None
        hit, cx = area
        def do():
            self.cast("thread bridge (net)", lv)
            self.control_tries += 1
            lr = legendary_left(hit)
            spell = self.hold_on("thread net")
            self.fight.zones.append(Net(self, cx, spell))
            for e in hit:
                self.restrain(e, "dex", lv, "thread net", spell)
            self.refund_if_resisted(lr, hit)
        return (score(hit), "thread bridge (net)", do)

    def red_tape_option(self):
        if not self.knows("red tape"):
            return None
        if not self.avail(2):
            return None
        cands = sorted(((self.p_save(e, "str", True) * self.weight(e, 0.8, 0.35), e)
                        for e in self.in_range(60)
                        if not (e.has("restrained") or e.incapacitated()) and e.hp >= 0.3 * e.max_hp),
                       key=lambda x: -x[0])
        if not cands:
            return None
        best = None
        for lv in self.avail(2):
            k = 1 + (lv - 2)
            sc = sum(v for v, _ in cands[:k]) - 0.1 * (lv - 2)
            if best is None or sc > best[0]:
                best = (sc, lv, [e for _, e in cands[:k]])
        sc, lv, tgts = best
        def do():
            self.cast("red tape", lv)
            self.control_tries += 1
            lr = legendary_left(tgts)
            spell = self.hold_on("red tape")
            for e in tgts:
                self.restrain(e, "str", lv, "red tape", spell)
            self.refund_if_resisted(lr, tgts)
        return (sc, "red tape", do)

    def gravity_option(self):
        if not self.knows("which way is down"):
            return None
        lv = self.slot_for(3)
        if lv is None:
            return None
        def score(hit):
            return sum(self.p_save(e, "dex", True) * self.weight(e, 0.9, 0.3) for e in hit if not e.has("aloft"))
        area = self.best_area(10, 60, score=score)
        if not area or score(area[0]) <= 0:
            return None
        hit, cx = area
        def do():
            self.cast("which way is down", lv)
            self.control_tries += 1
            lr = legendary_left(hit)
            spell = self.hold_on("which way is down")
            z = Gravity(self, cx, spell)
            self.gravity = z
            self.fight.zones.append(z)
            for e in hit:
                z.pull(e)
            self.refund_if_resisted(lr, hit)
        return (score(hit), "which way is down", do)

    def matter_option(self):
        if not self.knows("matter conversion"):
            return None
        lv = self.slot_for(3)
        foes = [e for e in self.enemies() if e.style == "melee"]
        if lv is None or not foes:
            return None
        side = 1 if self.nearest(foes).x > self.x else -1
        cx = self.x + side * 20   # touched at my feet: the pool runs 5 to 35 feet ahead
        if not self.spot_clear(cx, 15):
            return None
        crossing = [e for e in foes if (e.x - cx) * side > 15]
        sc = 0.25 * len(crossing)
        if not sc:
            return None
        def do():
            self.cast("matter conversion", lv)
            spell = self.hold_on("matter conversion")
            self.fight.zones.append(SpellZone("matter conversion", self, cx, 15, difficult=True, spell=spell))
        return (sc, "matter conversion", do)

    # ----- damage and the rest: the highest expected value (wizard.options) -----------
    def extra_options(self, opts):
        super().extra_options(opts)
        if self.has("silenced") or self.foe is None:
            return
        foe, t = self.foe, self.tier
        sight = self.can_see(foe)
        if self.loose and self.dist() <= 60 and self.knows("throw the book"):
            p = self.p_attack(foe)
            opts.append((p * 5.5 * t * self.cage_factor(foe), "throw the book", lambda: self.throw_book(foe)))
        if self.liquid and self.knows("flash boil"):
            sc = lambda hit: sum(self.p_save_fail(e, "con") for e in hit)
            area = self.best_area(5, 60, score=sc)
            if area:
                opts.append((4.5 * t * sc(area[0]), "flash boil", lambda hit=area[0]: self.flash_boil(hit)))
        if self.rugs and self.knows("rug pull"):
            sc = lambda hit: sum(self.p_save_fail(e, "dex") * self.prone_value(e) for e in hit if not e.has("prone"))
            area = self.best_area(5, 60, score=sc)
            if area and sc(area[0]) > 0:
                opts.append((sc(area[0]), "rug pull", lambda hit=area[0]: self.rug_pull(hit)))
        if self.hanging and self.knows("assessed weight") and sight and self.dist() <= 60 and not self.conc:
            lv = self.slot_for(1)
            if lv is not None:
                opts.append((22 * self.p_half(foe, "dex", Ctx(damage=True, big=True)) * self.cage_factor(foe),
                             "assessed weight", lambda lv=lv: self.assessed_weight(foe, lv)))
        self.fault_line_option(opts)
        self.banked_fire_option(opts)
        self.slip_option(opts)
        self.overtime_option(opts)

    def throw_book(self, foe):
        self.cast_log["throw the book"] += 1
        self.spell_attack("throw the book", 0, 1, [Dice(self.tier, 10, "bludgeoning")], rng=60)

    def flash_boil(self, hit):
        self.cast_log["flash boil"] += 1
        self.save_spell("flash boil", 0, "con", [Dice(self.tier, 8, "fire")], half=False, targets=hit,
                        targeted=False)

    def rug_pull(self, hit):
        self.cast("rug pull", 0)
        self.rugs -= 1
        for e in hit:
            if not saving_throw(e, "dex", self.dc, self, Ctx(spell=True, name="rug pull")):
                e.add("prone", self)

    def assessed_weight(self, foe, lv):
        self.cast_log["assessed weight"] += 1
        self.hanging -= 1
        self.drop_conc()
        self.save_spell("assessed weight", lv, "dex", [Dice(4, 10, "bludgeoning")])

    def fault_line_option(self, opts):
        if not self.knows("fault line"):
            return None
        lv = self.slot_for(2)
        if lv is None:
            return
        best = None
        for side in (1, -1):
            squares = (self.x + 5 * side, self.x + 10 * side)
            if any(a.x in squares for a in self.allies()):
                continue
            hit = [e for e in self.enemies() if e.x in squares]
            v = sum(self.p_save_fail(e, "dex") * (3.5 + self.prone_value(e)) for e in hit)
            if hit and (best is None or v > best[0]):
                best = (v, hit)
        if best:
            opts.append((best[0], "fault line", lambda hit=best[1]: self.fault_line(hit, lv)))

    def fault_line(self, hit, lv):
        self.cast("fault line", lv)
        for e in hit:
            if not saving_throw(e, "dex", self.dc, self, Ctx(spell=True, level=lv, name="fault line")):
                deal(e, roll_damage([Dice(1, 6, "bludgeoning")]), self, Ctx(spell=True, level=lv, name="fault line"))
                if not e.dead:
                    e.add("prone", self)
                    e.add("slow", self, value=10, **e.until_my_next_end())   # climbing out of the trench

    def banked_fire_option(self, opts):
        if not self.knows("banked fire"):
            return None
        if self.conc:
            return
        lv = self.slot_for(1)
        if lv is None:
            return
        area = self.best_area(5, 30)
        if area:
            opts.append((3.5 * len(area[0]) * 2, "banked fire", lambda a=area: self.banked_fire(a[1], lv)))

    def banked_fire(self, cx, lv):
        self.cast("banked fire", lv)
        spell = self.hold_on("banked fire")
        self.fight.zones.append(Heat(self, cx, spell))

    def slip_option(self, opts):
        """Only worth it when the extra cost keeps a charger from reaching us this round."""
        if not self.knows("slip & grip"):
            return
        n = 2 if self.level >= 5 else 1
        for e in self.enemies():
            if e.style != "melee" or e.incapacitated():
                continue
            gap, sp = self.threat_gap(e), e.speed_now()
            if 0 < gap <= sp < gap + 5 * n:
                near = e.nearest_enemy()
                step = 5 if near.x > e.x else -5
                squares = [e.x + step * (i + 1) for i in range(n)]
                if any(a.x in squares for a in [self] + self.allies()) or self.dist_to(e) > 60:
                    continue
                opts.append((0.7 * e.est_dpr(near), "slip & grip", lambda sq=squares: self.slip_grip(sq)))
                return

    def slip_grip(self, squares):
        self.cast("slip & grip", 0)
        if self.slip:
            self.slip.active = False   # casting it again ends the last one
        self.slip = Squares(self, squares)
        self.fight.zones.append(self.slip)

    def overtime_option(self, opts):
        if not self.knows("overtime"):
            return None
        lv = self.slot_for(3)
        if lv is None:
            return
        group = [c for c in [self] + self.allies() if self.dist_to(c) <= 30 and not getattr(c, "overtimed", False)]
        missing = sum(c.max_hp - c.hp for c in group)
        if missing > 0:
            opts.append((0.9 * missing, "overtime", lambda g=group: self.overtime(g, lv)))

    def overtime(self, group, lv):
        self.cast("overtime", lv)
        for c in group:
            c.overtimed = True
            c.heal(c.max_hp - c.hp, self)

    # ----- Not My Department --------------------------------------------------------
    def redirect_attack(self, att, ctx, bonus, parts):
        if self.has("silenced") or not hasattr(att, "attacks") or not self.knows("not my department"):
            return None
        lv = self.slot_for(1)
        if lv is None:
            return None
        if ctx.kind == "melee":
            reach = att.reach
        else:
            reach = max((a.long for a in att.attacks if a.kind == "ranged"), default=0)
        others = [h for h in self.allies() if att.dist_to(h) <= reach]
        if not others:
            return None
        pf = self.p_save_fail(att, "wis")
        stake = p_hit(bonus, self.ac()) * avg(parts)
        if pf < 0.35 or (pf * stake < 5 and stake < self.hp):   # not worth a slot, unless it could drop me
            return None
        self.cast("not my department", lv)
        self.reaction = False
        if saving_throw(att, "wis", self.dc, self, Ctx(spell=True, level=lv, name="not my department")):
            return None
        pick = att.stand_in(self)
        return pick if pick in others else min(others, key=att.dist_to)


WORKINGS = ("throw the book", "flash boil", "rug pull", "slip & grip", "mind the floor", "assessed weight",
            "banked fire", "fault line", "thread bridge (net)", "red tape", "matter conversion", "which way is down",
            "not my department", "overtime")
_MADE = {}


def with_workings(cls, env, without=frozenset()):
    """`cls` (a Crystal Mage) that also knows the Common Workings, in environment
    `env`, except those named in `without`."""
    key = (cls, env, frozenset(without))
    if key not in _MADE:
        _MADE[key] = type(cls.__name__ + "Workings", (Workings, cls),
                          {"workings_env": env, "workings_without": frozenset(without),
                           "key": cls.key, "label": cls.label})
    return _MADE[key]
