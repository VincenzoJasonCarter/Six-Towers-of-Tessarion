"""Rules core for the Proving Grounds: dice, creatures, effects, attacks, saves,
damage, movement and the turn loop.

A fight is two sides on a straight 120-foot line with a wall at each end:
one creature against one other (run.py), or a party of four against an
encounter (party.py). Creatures can pass each other on the line, as they
could step around each other on a real map, but leaving an enemy's reach
provokes an opportunity attack. Only the 5e rules that the eleven
subclasses and the benchmark foes actually touch are modelled; README.md
lists what is left out.
"""
from __future__ import annotations

import random

R = random.Random()
ARENA = (0, 120)
START = (30, 90)                 # one-on-one
FORMATION = ((30, 10), (90, 110))  # parties: (front rank, back rank) for side 0 and side 1
MAX_ROUNDS = 20
BPS = ("bludgeoning", "piercing", "slashing")
SPEED_ZERO = ("paralyzed", "stunned", "restrained", "speed0")


def seed(n):
    R.seed(n)


def d(n, die):
    return sum(R.randint(1, die) for _ in range(n))


def d20(adv=False, dis=False):
    a = R.randint(1, 20)
    if adv == dis:
        return a
    b = R.randint(1, 20)
    return max(a, b) if adv else min(a, b)


def mod(score):
    return (score - 10) // 2


def p_roll(need, adv=False, dis=False):
    """Chance that a d20 (with advantage/disadvantage) shows `need` or more."""
    p = min(1.0, max(0.0, (21 - need) / 20))
    if adv and not dis:
        return 1 - (1 - p) ** 2
    if dis and not adv:
        return p * p
    return p


def p_hit(bonus, ac, adv=False, dis=False):
    p = min(0.95, max(0.05, (21 - (ac - bonus)) / 20))
    if adv and not dis:
        return 1 - (1 - p) ** 2
    if dis and not adv:
        return p * p
    return p


def p_fail(save_bonus, dc, adv=False, dis=False):
    return 1 - p_roll(dc - save_bonus, adv, dis)


def roll_damage(parts, crit=False):
    """parts: [(dice, die, flat, type)] -> {type: total}. A crit doubles the dice."""
    out = {}
    for n, die, flat, dtype in parts:
        out[dtype] = out.get(dtype, 0) + d(2 * n if crit else n, die) + flat
    return out


def avg(parts):
    return sum(n * (die + 1) / 2 + flat for n, die, flat, _ in parts)


class Effect:
    """A named condition or modifier on a creature.

    until = ("start" | "end", creature): removed at the start/end of that
    creature's turn, after skipping `skip` such boundaries. None = until removed.
    """
    __slots__ = ("name", "source", "until", "skip", "value")

    def __init__(self, name, source=None, until=None, value=None, skip=0):
        self.name, self.source, self.until, self.value, self.skip = name, source, until, value, skip


class Conc:
    """A concentration spell: dropping it removes the effects it holds."""

    def __init__(self, name, held=()):
        self.name = name
        self.held = list(held)  # [(creature, Effect)]


class Zone:
    """An area on the line (anchor, nexus, lockstep field) owned by one creature."""

    def __init__(self, name, owner, center, radius, follows=False):
        self.name, self.owner, self.radius, self.follows = name, owner, radius, follows
        self._center = center

    def center(self):
        return self.owner.x if self.follows else self._center

    def covers(self, pos):
        return not self.owner.dead and abs(pos - self.center()) <= self.radius

    def on_enemy_turn_start(self, c):
        pass


class Creature:
    style = "melee"        # melee | ranged | caster: how it moves
    caster = False         # casts spells (anti-magic features care)
    creature_type = "humanoid"
    devils_sight = False   # sees through magical darkness
    can_oa = True          # makes opportunity attacks
    heals = False          # can heal itself (Prismatic Round cares)
    max_range = 5          # farthest it can usefully fight from

    def __init__(self, name, level, scores, save_profs, pb, hp, ac, speed=30, reach=5):
        self.name, self.level, self.scores, self.save_profs = name, level, scores, set(save_profs)
        self.pb, self.max_hp, self.hp, self.base_ac = pb, hp, hp, ac
        self.base_speed, self.reach = speed, reach
        self.thp = 0
        self.effects: list[Effect] = []
        self.conc: Conc | None = None
        self.reaction = True
        self.bonus_used = False
        self.dead = False
        self.side = 0
        self.x = 0
        self.foe: Creature | None = None   # this turn's target
        self.fight: Fight | None = None
        self.moved = 0
        self.turns = 0
        self.dealt = 0
        self.taken = 0
        self.hit_this_turn = False
        self.acted = False   # attacked or cast at an enemy this turn (Pact Nexus)

    # ----- effects -------------------------------------------------------
    def add(self, name, source=None, until=None, value=None, skip=0):
        e = Effect(name, source, until, value, skip)
        self.effects.append(e)
        if name in ("paralyzed", "stunned"):
            self.drop_conc()  # incapacitated creatures lose concentration
        return e

    def has(self, name):
        return any(e.name == name for e in self.effects)

    def get(self, name):
        return next((e for e in self.effects if e.name == name), None)

    def remove(self, name=None, effect=None):
        self.effects = [e for e in self.effects
                        if not (e is effect or (name is not None and e.name == name))]

    def take(self, name):
        """Remove and return the first effect called `name` (one-shot effects)."""
        e = self.get(name)
        if e:
            self.remove(effect=e)
        return e

    def total(self, name):
        return sum(e.value or 0 for e in self.effects if e.name == name)

    # ----- who is where --------------------------------------------------
    def enemies(self):
        return [c for c in self.fight.all if c.side != self.side and not c.dead]

    def allies(self):
        """Living allies, not counting this creature."""
        return [c for c in self.fight.all if c.side == self.side and not c.dead and c is not self]

    def dist_to(self, other):
        return abs(self.x - other.x)

    def dist(self):
        return self.dist_to(self.foe) if self.foe else 999

    def threatened(self):
        """A hostile that isn't incapacitated stands within 5 feet (ranged attacks suffer)."""
        return any(self.dist_to(e) <= 5 and not e.incapacitated() for e in self.enemies())

    def engaged(self):
        return self.threatened()

    def nearest(self, creatures):
        return min(creatures, key=lambda c: (self.dist_to(c), c.hp), default=None)

    def nearest_enemy(self):
        return self.nearest(self.enemies())

    def pick_target(self):
        """This turn's target. Default: the nearest enemy, the most hurt on a tie."""
        return self.nearest_enemy()

    def melee_threat(self):
        """The nearest enemy that wants to fight in melee."""
        return self.nearest([e for e in self.enemies() if e.style == "melee"])

    # ----- footwork for shooters and casters ---------------------------
    def keep_distance(self):
        """Kite whatever wants to melee me; close on targets beyond my range.
        Called before and again after the action, with whatever movement is left."""
        sp = self.speed_now() - self.moved
        if sp <= 0:
            return
        threat = self.melee_threat()
        if threat:
            gap = self.dist_to(threat)
            if gap <= threat.reach:
                # Step away (eating the opportunity attack) only if it can't
                # follow and still attack on its turn.
                after = gap + min(sp, room_behind(self, threat))
                if threat.speed_now() < after - threat.reach:
                    move(self, False, sp, ref=threat)
                return
            if self.foe and self.dist() < self.max_range:
                move(self, False, min(sp, self.max_range - self.dist()), ref=threat)
                return
        if self.foe and self.dist() > self.max_range:
            move(self, True, min(sp, self.dist() - self.max_range))

    # ----- area effects -------------------------------------------------
    def area_targets(self, center_x, radius):
        """Enemies inside an area, or None if it would catch me or an ally."""
        if any(abs(c.x - center_x) <= radius for c in [self] + self.allies()):
            return None
        return [e for e in self.enemies() if abs(e.x - center_x) <= radius]

    def best_area(self, radius, rng, score=len):
        """(targets, center) for the area spot that best scores its targets."""
        best = None
        for e in self.enemies():
            if self.dist_to(e) > rng:
                continue
            hit = self.area_targets(e.x, radius)
            if hit and (best is None or score(hit) > score(best[0])):
                best = (hit, e.x)
        return best

    # ----- derived stats -------------------------------------------------
    def ac_bonus(self):
        """Modifiers on top of base armour: effects plus allies' auras."""
        return self.total("ac") + sum(a.aura_ac(self) for a in self.allies()) if self.fight else self.total("ac")

    def ac(self):
        return self.base_ac + self.ac_bonus()

    def incapacitated(self):
        return self.has("paralyzed") or self.has("stunned")

    def speed_now(self):
        if any(self.has(n) for n in SPEED_ZERO):
            return 0
        return max(0, self.base_speed - self.total("slow"))

    def mod(self, abil):
        return mod(self.scores[abil])

    def save_bonus(self, abil):
        return self.mod(abil) + (self.pb if abil in self.save_profs else 0)

    def in_difficult(self, pos):
        return any(z.covers(pos) for z in self.fight.zones
                   if z.owner.side != self.side and z.name in ("anchor", "lockstep", "nexus"))

    def can_see(self, other):
        """False when `other` stands in magical darkness this creature can't see through."""
        return not (other.has("darkness") and not self.devils_sight and not other.has("white_dust"))

    def can_see_foe(self):
        return self.foe is None or self.can_see(self.foe)

    def est_dpr(self, target):
        """Rough damage per round against `target`; policies use it to judge threats."""
        return 10

    # ----- hooks for subclasses ------------------------------------------
    def on_initiative(self): pass
    def take_turn(self): pass
    def end_turn_hook(self): pass
    def attack_mods(self, tgt, ctx): return False, False   # pure: also used to predict
    def defend_mods(self, att, ctx): return False, False   # pure: also used to predict
    def save_mods(self, abil, src, ctx): return False, False
    def impose_save_mods(self, tgt, abil, ctx): return False, False
    def after_hit_roll(self, tgt, ctx): pass               # may set ctx["crit"]
    def hit_extra(self, tgt, ctx): return []
    def after_hit(self, tgt, ctx, crit): pass
    def after_damage_dealt(self, tgt, amount, ctx): pass
    def react_to_attack(self, att, ctx, total, ac): return 0   # AC raised by its own reaction
    def block_missiles(self): return False
    def resists(self, dtype, ctx): return False
    def react_to_damage(self, dmg, src, ctx): return dmg
    def save_reroll(self, abil, dc, src, ctx): return False    # True = the reroll succeeded
    def flip_success(self, tgt, ctx): return False
    def on_failed_save(self, tgt, ctx): pass
    def on_kill(self, tgt): pass
    def opportunity_attack(self, tgt): pass
    def on_creature_moved(self, mover): pass
    def can_shield_cheap(self): return False                  # a Shield reaction is ready
    # what this creature does for an ally (or itself where noted)
    def aura_ac(self, ally): return 0
    def aura_save_mods(self, ally, abil, src, ctx): return False, False
    def aura_save_bonus(self, ally, abil): return 0
    def guard_attack(self, att, ally, ctx): return False       # True = impose disadvantage
    def guard_attack_hit(self, att, ally, ctx, total, ac): return 0   # AC raised for the ally
    def ally_save_reroll(self, ally, abil, dc, src, ctx): return False
    def intercept(self, ally, dmg, src, ctx): return False     # True = take the hit instead
    def ward(self, tgt, dmg, src, ctx): return dmg              # tgt may be self or an ally
    def save_from_death(self, tgt): return False                # tgt may be self or an ally

    # ----- shared mechanics ----------------------------------------------
    def heal(self, amount):
        if self.has("no_heal") or amount <= 0:
            return 0
        got = min(amount, self.max_hp - self.hp)
        self.hp += got
        return got

    def gain_thp(self, amount):
        self.thp = max(self.thp, amount)

    def drop_conc(self):
        if self.conc:
            for holder, eff in self.conc.held:
                holder.remove(effect=eff)
            self.conc = None

    def my_turn(self):
        return self.fight.current is self


class Fight:
    """Two sides, each a creature or a list of creatures."""

    def __init__(self, a, b):
        sides = [list(a) if isinstance(a, (list, tuple)) else [a],
                 list(b) if isinstance(b, (list, tuple)) else [b]]
        self.sides = sides
        self.all = sides[0] + sides[1]
        self.zones: list[Zone] = []
        self.round = 0
        self.current = None
        for i, side in enumerate(sides):
            for c in side:
                c.side, c.fight, c.foe = i, self, None
        if len(sides[0]) == 1 and len(sides[1]) == 1:
            sides[0][0].x, sides[1][0].x = START
        else:
            for i, side in enumerate(sides):
                front, back = FORMATION[i]
                for c in side:
                    c.x = front if c.style == "melee" else back

    def run(self, max_rounds=MAX_ROUNDS):
        """Returns (winning side 0/1 or None for a draw, rounds)."""
        order = sorted(self.all, key=lambda c: (d20() + c.mod("dex"), R.random()), reverse=True)
        for c in order:
            c.on_initiative()
        for self.round in range(1, max_rounds + 1):
            for c in order:
                if self.over():
                    break
                if not c.dead:
                    self.turn(c)
            if self.over():
                break
        return self.winner(), self.round

    def down(self, i):
        return all(c.dead for c in self.sides[i])

    def over(self):
        return self.down(0) or self.down(1)

    def winner(self):
        if self.down(1) and not self.down(0):
            return 0
        if self.down(0) and not self.down(1):
            return 1
        return None

    def turn(self, c):
        self.current = c
        expire(self, "start", c)
        for z in list(self.zones):
            if z.owner.side != c.side and z.covers(c.x):
                z.on_enemy_turn_start(c)
        c.reaction = True
        c.bonus_used = False
        c.moved = 0
        c.turns += 1
        c.hit_this_turn = False
        c.acted = False
        c.foe = c.pick_target()
        if c.foe and not c.incapacitated() and not c.dead:
            c.take_turn()
        if not self.over():
            nexus_check(c)
        if not self.over():
            end_of_turn(c)
        if not self.over() and not c.dead:
            c.end_turn_hook()
        expire(self, "end", c)
        self.current = None


def expire(fight, phase, who):
    for c in fight.all:
        keep = []
        for e in c.effects:
            if e.until and e.until[0] == phase and e.until[1] is who:
                if not e.skip:
                    continue
                e.skip -= 1
            keep.append(e)
        c.effects = keep


def end_of_turn(c):
    """Repeated saves and delayed damage that resolve at the end of a creature's turn."""
    for e in list(c.effects):
        if c.dead:
            return
        if e.name == "paralyzed" and e.value:
            abil, dc, caster = e.value
            if saving_throw(c, abil, dc, caster, {"spell": True, "level": 2, "control": True}):
                c.remove(effect=e)
                if caster.conc and any(eff is e for _, eff in caster.conc.held):
                    caster.conc.held = [(h, x) for h, x in caster.conc.held if x is not e]
                    if not caster.conc.held:
                        caster.conc = None
        elif e.name == "dot":
            parts, src = e.value
            c.remove(effect=e)
            deal(c, roll_damage(parts), src, {"spell": True})


def nexus_check(c):
    """Pact Nexus: a hostile in the zone that attacked or cast this turn saves or takes necrotic."""
    for z in c.fight.zones:
        if z.name == "nexus" and z.owner.side != c.side and c.acted and z.covers(c.x):
            o = z.owner
            if not saving_throw(c, "wis", o.dc, o, {"spell": True, "level": 9}):
                deal(c, {"necrotic": max(1, o.mod("int"))}, o, {"spell": True})


def cage_over(c):
    """The Mana Cage effect whose dome covers c (raised by c or an ally), if any."""
    for w in [c] + c.allies():
        e = w.get("cage")
        if e and abs(w.x - c.x) <= 15:
            return w, e
    return None, None


# ----- attacks, saves, damage ---------------------------------------------

def attack_adv(att, tgt, ctx):
    """Advantage/disadvantage on an attack, without using anything up."""
    a1, d1 = att.attack_mods(tgt, ctx)
    a2, d2 = tgt.defend_mods(att, ctx)
    adv, dis = a1 or a2, d1 or d2
    if tgt.incapacitated() or tgt.has("restrained") or tgt.has("blinded"):
        adv = True
    if any(att.has(n) for n in ("restrained", "blinded", "crash", "next_atk_disadv", "hunger")):
        dis = True
    fear = att.get("frightened")
    if fear and fear.source and not fear.source.dead and att.can_see(fear.source):
        dis = True
    lost = att.get("unlocated")
    if lost and lost.source is tgt:
        dis = True   # Silent Volley: it can't pin down the archer
    if ctx["kind"] == "ranged" and att.threatened():
        dis = True
    if not att.can_see(tgt):
        dis = True
    if att.has("darkness") and not att.has("white_dust") and not tgt.devils_sight:
        adv = True   # the attacker is unseen
    veil = tgt.get("veiled")
    if veil and ctx["kind"] == "ranged" and not ctx.get("spell") and att.dist_to(tgt) > 10:
        dis = True   # Verdant Veil
    if ctx.get("spell") and ctx["kind"] == "ranged" and cage_over(tgt)[0]:
        dis = True   # Mana Cage
    return adv, dis


def attack(att, tgt, *, bonus, parts, kind, spell=False, level=0, magical=False,
           weapon=None, adv=False, dis=False, ctx=None):
    """One attack roll. kind: "melee" | "ranged". Returns (hit, crit)."""
    if att.dead or tgt.dead:
        return False, False
    att.acted = True
    ctx = dict(ctx or {}, kind=kind, spell=spell, level=level, magical=magical or spell, weapon=weapon)
    a, b = attack_adv(att, tgt, ctx)
    adv, dis = adv or a, dis or b
    if not dis:
        for g in tgt.allies():
            if g.guard_attack(att, tgt, ctx):   # Living Wall
                dis = True
                break
    att.take("next_atk_disadv")
    att.take("hunger")
    pen = att.take("next_atk_pen")
    roll = d20(adv, dis)
    total = roll + bonus - (d(1, 4) if pen else 0)
    crit = roll == 20
    ac = tgt.ac()
    hit = crit or (roll != 1 and total >= ac)
    if hit and not crit:
        ctx["bonus"] = bonus
        raised = 0
        if tgt.reaction and not tgt.incapacitated():
            raised = tgt.react_to_attack(att, ctx, total, ac)
        if not raised or total >= ac + raised:
            for g in tgt.allies():
                raised = g.guard_attack_hit(att, tgt, ctx, total, ac)
                if raised:
                    break
        if raised and total < ac + raised:
            hit = False
    if not hit:
        return False, False
    if tgt.has("paralyzed") and att.dist_to(tgt) <= 5:
        crit = True
    ctx["crit"] = crit
    att.after_hit_roll(tgt, ctx)
    crit = ctx["crit"]
    att.hit_this_turn = True
    extra = att.hit_extra(tgt, ctx)
    deal(tgt, roll_damage(list(parts) + extra, crit), att, dict(ctx, attack=True))
    att.after_hit(tgt, ctx, crit)
    return True, crit


def saving_throw(tgt, abil, dc, src, ctx):
    """True if the save succeeds."""
    if abil in ("str", "dex") and tgt.incapacitated():
        ok = False
    else:
        a1, d1 = tgt.save_mods(abil, src, ctx)
        a2, d2 = src.impose_save_mods(tgt, abil, ctx) if src else (False, False)
        adv, dis = a1 or a2, d1 or d2
        bonus = tgt.save_bonus(abil)
        lift = 0
        for g in tgt.allies():
            a3, d3 = g.aura_save_mods(tgt, abil, src, ctx)
            adv, dis = adv or a3, dis or d3
            lift = max(lift, g.aura_save_bonus(tgt, abil))
        if abil == "dex" and tgt.has("restrained"):
            dis = True
        pen = tgt.take("next_save_pen")
        ok = d20(adv, dis) + bonus + lift - (d(1, 4) if pen else 0) >= dc
        if not ok:
            ok = tgt.save_reroll(abil, dc, src, ctx)
        if not ok:
            for g in tgt.allies():
                if g.ally_save_reroll(tgt, abil, dc, src, ctx):
                    ok = True
                    break
    if ok and src and not src.dead and src.flip_success(tgt, ctx):
        ok = False
    if not ok and src:
        src.on_failed_save(tgt, ctx)
    return ok


def deal(tgt, dmg, src, ctx):
    """Apply a {type: amount} packet: interception, resistances, reactions, temp HP,
    concentration, and going down."""
    if tgt.dead:
        return 0
    if src and src.side != tgt.side and not ctx.get("intercepted"):
        for g in tgt.allies():
            if g.intercept(tgt, dmg, src, ctx):     # Intercepting Guard
                tgt, ctx = g, dict(ctx, intercepted=True)
                break
    weaponlike = bool(not ctx.get("spell") and ctx.get("weapon") and not ctx.get("magical"))
    out = {}
    for dtype, n in dmg.items():
        n = max(0, n)
        if ctx.get("intercepted") or tgt.resists(dtype, dict(ctx, nonmagical=weaponlike and dtype in BPS)):
            n //= 2
        out[dtype] = n
    out = tgt.react_to_damage(out, src, ctx)
    for g in tgt.allies():
        out = g.ward(tgt, out, src, ctx)            # Runic Bulwark on an ally
    total = sum(out.values())
    if total <= 0:
        return 0
    soak = min(tgt.thp, total)
    tgt.thp -= soak
    tgt.hp -= total - soak
    tgt.taken += total
    if src and src.side != tgt.side:
        src.dealt += total
        src.after_damage_dealt(tgt, total, ctx)
    if tgt.hp <= 0:
        if any(g.save_from_death(tgt) for g in [tgt] + tgt.allies()):
            tgt.hp = 1
            return total
        tgt.hp = 0
        tgt.dead = True
        tgt.drop_conc()
        if src and src.side != tgt.side:
            src.on_kill(tgt)
        return total
    if tgt.conc:
        dis = tgt.has("crash") or ctx.get("powder", False)
        if d20(False, dis) + tgt.save_bonus("con") < max(10, total // 2):
            tgt.drop_conc()
    return total


# ----- movement -----------------------------------------------------------

def move_to(c, goal, budget, provoke=True, stop_short=0):
    """Walk up to `budget` feet toward the point `goal` in 5-foot steps, stopping
    `stop_short` feet from it. Entering difficult terrain costs double, leaving
    an enemy's reach provokes an opportunity attack, and a frightened creature
    won't step closer to what frightens it. Returns feet moved."""
    if c.dead or budget <= 0:
        return 0
    step = 5 if goal > c.x else -5
    fear = c.get("frightened")
    spent = moved = 0
    while not c.dead:
        if abs(goal - c.x) <= stop_short:
            break
        new = c.x + step
        if not (ARENA[0] <= new <= ARENA[1]):
            break
        if fear and fear.source and not fear.source.dead and abs(new - fear.source.x) < abs(c.x - fear.source.x):
            break
        cost = 10 if c.in_difficult(new) else 5
        if spent + cost > budget:
            break
        if provoke:
            for e in c.enemies():
                if (abs(c.x - e.x) <= e.reach < abs(new - e.x) and e.reaction and e.can_oa
                        and not e.incapacitated()):
                    e.reaction = False
                    e.opportunity_attack(c)
                    if c.dead or c.speed_now() == 0:
                        break
            if c.dead or c.speed_now() == 0:
                break
        c.x = new
        spent += cost
        moved += 5
    c.moved += moved
    if moved:
        for e in c.enemies():
            e.on_creature_moved(c)
    return moved


def move(c, toward, budget, provoke=True, ref=None):
    """Walk toward `ref` (default: the target) until adjacent, or straight away from it."""
    ref = ref or c.foe or c.nearest_enemy()
    if ref is None:
        return 0
    if toward:
        return move_to(c, ref.x, budget, provoke, stop_short=5)
    wall = ARENA[0] if ref.x > c.x or (ref.x == c.x and c.side == 0) else ARENA[1]
    return move_to(c, wall, budget, provoke)


def room_behind(c, ref=None):
    """Feet c could still back away from `ref` before hitting the wall."""
    ref = ref or c.foe or c.nearest_enemy()
    if ref is None:
        return 0
    return (c.x - ARENA[0]) if ref.x > c.x or (ref.x == c.x and c.side == 0) else (ARENA[1] - c.x)


def push(c, src, feet):
    """Shove c straight away from src."""
    step = feet if c.x > src.x or (c.x == src.x and src.side == 0) else -feet
    c.x = max(ARENA[0], min(ARENA[1], c.x + step))
