"""Rules core for the Proving Grounds: dice, creatures, effects, attacks, saves,
damage, movement and the turn loop.

Every fight is one creature against one other on a straight 120-foot line with
a wall at each end. Only the 5e rules that the eleven subclasses and the
benchmark foes actually touch are modelled; README.md lists what is left out.
"""
from __future__ import annotations

import random

R = random.Random()
ARENA = (0, 120)
START = (30, 90)
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
    """An area on the line (anchor, nexus, dome) owned by one creature."""

    def __init__(self, name, owner, center, radius, follows=False):
        self.name, self.owner, self.radius, self.follows = name, owner, radius, follows
        self._center = center

    def center(self):
        return self.owner.x if self.follows else self._center

    def covers(self, pos):
        return abs(pos - self.center()) <= self.radius

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
        self.x = 0
        self.foe: Creature | None = None
        self.fight: Fight | None = None
        self.moved = 0
        self.turns = 0
        self.dealt = 0
        self.hit_this_turn = False
        self.acted = False   # attacked or cast at the foe this turn (Pact Nexus)

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

    # ----- derived stats -------------------------------------------------
    def ac(self):
        return self.base_ac + self.total("ac")

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

    def dist(self):
        return abs(self.x - self.foe.x)

    def engaged(self):
        return self.dist() <= 5

    def in_difficult(self, pos):
        return any(z.covers(pos) for z in self.fight.zones
                   if z.owner is not self and z.name in ("anchor", "lockstep", "nexus"))

    def can_see_foe(self):
        """False when the foe stands in magical darkness this creature can't see through."""
        f = self.foe
        return not (f.has("darkness") and not self.devils_sight and not f.has("white_dust"))

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
    def react_to_attack(self, att, ctx, total, ac): return 0   # AC raised by a reaction
    def block_missiles(self): return False
    def resists(self, dtype, ctx): return False
    def react_to_damage(self, dmg, src, ctx): return dmg
    def save_reroll(self, abil, dc, src, ctx): return False    # True = the reroll succeeded
    def flip_success(self, tgt, ctx): return False
    def on_failed_save(self, tgt, ctx): pass
    def on_kill(self, tgt): pass
    def opportunity_attack(self, tgt): pass
    def on_foe_moved_away(self, mover): pass
    def can_shield_cheap(self): return False                  # a Shield reaction is ready

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
    def __init__(self, a, b, start=START):
        self.a, self.b = a, b
        self.all = (a, b)
        self.zones: list[Zone] = []
        self.round = 0
        self.current = None
        a.foe, b.foe = b, a
        a.fight = b.fight = self
        a.x, b.x = start

    def run(self, max_rounds=MAX_ROUNDS):
        a, b = self.a, self.b
        ia = (d20() + a.mod("dex"), R.random())
        ib = (d20() + b.mod("dex"), R.random())
        order = [a, b] if ia > ib else [b, a]
        for c in order:
            c.on_initiative()
        for self.round in range(1, max_rounds + 1):
            for c in order:
                if self.over():
                    break
                self.turn(c)
            if self.over():
                break
        winner = a if b.dead and not a.dead else b if a.dead and not b.dead else None
        return winner, self.round

    def over(self):
        return self.a.dead or self.b.dead

    def turn(self, c):
        self.current = c
        expire(self, "start", c)
        for z in list(self.zones):
            if z.owner is not c and z.covers(c.x):
                z.on_enemy_turn_start(c)
        c.reaction = True
        c.bonus_used = False
        c.moved = 0
        c.turns += 1
        c.hit_this_turn = False
        c.acted = False
        if not c.incapacitated():
            c.take_turn()
        if not self.over():
            nexus_check(c)
        if not self.over():
            end_of_turn(c)
        if not self.over():
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
                    caster.conc = None
        elif e.name == "dot":
            parts, src = e.value
            c.remove(effect=e)
            deal(c, roll_damage(parts), src, {"spell": True})


def nexus_check(c):
    """Pact Nexus: a hostile in the zone that attacked or cast this turn saves or takes necrotic."""
    for z in c.fight.zones:
        if z.name == "nexus" and z.owner is not c and c.acted and z.covers(c.x):
            o = z.owner
            if not saving_throw(c, "wis", o.dc, o, {"spell": True, "level": 9}):
                deal(c, {"necrotic": max(1, o.mod("int"))}, o, {"spell": True})


# ----- attacks, saves, damage ---------------------------------------------

def attack_adv(att, tgt, ctx):
    """Advantage/disadvantage on an attack, without using anything up."""
    a1, d1 = att.attack_mods(tgt, ctx)
    a2, d2 = tgt.defend_mods(att, ctx)
    adv, dis = a1 or a2, d1 or d2
    if tgt.incapacitated() or tgt.has("restrained") or tgt.has("blinded"):
        adv = True
    if any(att.has(n) for n in ("restrained", "blinded", "crash", "next_atk_disadv", "hunger", "unlocated")):
        dis = True
    if att.has("frightened") and att.can_see_foe():
        dis = True
    if ctx["kind"] == "ranged" and att.dist() <= 5 and not tgt.incapacitated():
        dis = True
    if not att.can_see_foe():
        dis = True
    if att.has("darkness") and not att.has("white_dust") and not tgt.devils_sight:
        adv = True  # the attacker is unseen
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
    att.take("next_atk_disadv")
    att.take("hunger")
    pen = att.take("next_atk_pen")
    roll = d20(adv, dis)
    total = roll + bonus - (d(1, 4) if pen else 0)
    crit = roll == 20
    ac = tgt.ac()
    hit = crit or (roll != 1 and total >= ac)
    if hit and not crit and tgt.reaction and not tgt.incapacitated():
        ctx["bonus"] = bonus
        raised = tgt.react_to_attack(att, ctx, total, ac)
        if raised and total < ac + raised:
            hit = False
    if not hit:
        return False, False
    if tgt.has("paralyzed") and att.dist() <= 5:
        crit = True
    ctx["crit"] = crit
    att.after_hit_roll(tgt, ctx)
    crit = ctx["crit"]
    att.hit_this_turn = True
    extra = att.hit_extra(tgt, ctx)
    deal(tgt, roll_damage(list(parts) + extra, crit), att, ctx)
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
        if abil == "dex" and tgt.has("restrained"):
            dis = True
        pen = tgt.take("next_save_pen")
        ok = d20(adv, dis) + tgt.save_bonus(abil) - (d(1, 4) if pen else 0) >= dc
        if not ok:
            ok = tgt.save_reroll(abil, dc, src, ctx)
    if ok and src and not src.dead and src.flip_success(tgt, ctx):
        ok = False
    if not ok and src:
        src.on_failed_save(tgt, ctx)
    return ok


def deal(tgt, dmg, src, ctx):
    """Apply a {type: amount} packet: resistances, reactions, temp HP, concentration."""
    if tgt.dead:
        return 0
    weaponlike = bool(not ctx.get("spell") and ctx.get("weapon") and not ctx.get("magical"))
    out = {}
    for dtype, n in dmg.items():
        n = max(0, n)
        if tgt.resists(dtype, dict(ctx, nonmagical=weaponlike and dtype in BPS)):
            n //= 2
        out[dtype] = n
    out = tgt.react_to_damage(out, src, ctx)
    total = sum(out.values())
    if total <= 0:
        return 0
    soak = min(tgt.thp, total)
    tgt.thp -= soak
    tgt.hp -= total - soak
    if src and src is not tgt:
        src.dealt += total
        src.after_damage_dealt(tgt, total, ctx)
    if tgt.hp <= 0:
        tgt.hp = 0
        tgt.dead = True
        tgt.drop_conc()
        if src and src is not tgt:
            src.on_kill(tgt)
        return total
    if tgt.conc:
        dis = tgt.has("crash") or ctx.get("powder", False)
        if d20(False, dis) + tgt.save_bonus("con") < max(10, total // 2):
            tgt.drop_conc()
    return total


# ----- movement -----------------------------------------------------------

def move(c, toward, budget, provoke=True):
    """Walk up to `budget` feet toward (or away from) the foe in 5-foot steps.
    Entering difficult terrain costs double; leaving the foe's reach provokes
    an opportunity attack. Returns feet moved."""
    foe = c.foe
    if toward and c.has("frightened"):
        return 0
    step = (5 if foe.x > c.x else -5) * (1 if toward else -1)
    spent = moved = 0
    while not c.dead and budget > 0:
        new = c.x + step
        if not (ARENA[0] <= new <= ARENA[1]):
            break
        if toward and abs(new - foe.x) < 5:
            break
        cost = 10 if c.in_difficult(new) else 5
        if spent + cost > budget:
            break
        if provoke and abs(c.x - foe.x) <= foe.reach < abs(new - foe.x):
            if foe.reaction and foe.can_oa and not foe.incapacitated() and not foe.dead:
                foe.reaction = False
                foe.opportunity_attack(c)
                if c.dead or c.speed_now() == 0:
                    break
        c.x = new
        spent += cost
        moved += 5
    c.moved += moved
    if moved and not toward:
        foe.on_foe_moved_away(c)
    return moved


def room_behind(c):
    """Feet c could still back away before hitting the wall."""
    return (c.x - ARENA[0]) if c.foe.x > c.x else (ARENA[1] - c.x)
