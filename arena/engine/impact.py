"""Impact: crediting each creature, in hit points, with what it did for its side.

Besides its own damage (Creature.dealt_hp), a creature earns:

- protect: damage it kept off allies (auras, wards, interceptions, temp HP, heals)
- control: enemy damage it denied (lost turns, lost attacks, attacks at disadvantage)
- enable:  extra damage it let allies deal (advantage, lowered AC, worse saves)
- tank:    damage kept off the party by drawing attacks it takes better than
           the ally the attacker would have picked instead

Rolls are credited by expectation (the change in hit or save chance times the
damage at stake), and lost turns at the enemy's expected damage per round, so
crediting never rolls a die and never changes a fight. A creature gets nothing
for helping itself, apart from tanking.

The rules in combat.py call in here at the points where something happens.
"""
from __future__ import annotations

from .dice import avg, avg_dice, p_hit, p_roll

BPS = ("bludgeoning", "piercing", "slashing")


def credit(src, kind, amount):
    """Add `amount` HP to src's `kind` ("protect" | "control" | "enable" | "tank")."""
    if src is not None and amount > 0:
        setattr(src, kind, getattr(src, kind) + amount)


def causes(c, names):
    """The enemies of c behind its effects called `names`."""
    out = []
    for e in c.effects:
        if e.name in names and e.source is not None and e.source.side != c.side and e.source not in out:
            out.append(e.source)
    return out


def deny(c, sources, amount=None):
    """c loses its attacks this turn: its expected damage, split among the causes."""
    if sources and c.foe:
        amount = c.est_dpr(c.foe) if amount is None else amount
        for s in sources:
            credit(s, "control", amount / len(sources))


def is_nonmagical(ctx, dtype):
    """A plain weapon's bludgeoning, piercing or slashing (Anchored Stance resists it)."""
    weaponlike = bool(not ctx.spell and ctx.weapon and not ctx.magical)
    return weaponlike and dtype in BPS


# ----- attack rolls ------------------------------------------------------------

def split_credit(why, kind, gain):
    """Share `gain` among the credited sources of `kind` ("adv" or "dis"). If any
    source of it isn't credited (the creature's own, or the situation), the
    others changed nothing and get nothing."""
    srcs = [(s, cat) for k, s, cat in why if k == kind]
    if srcs and all(s is not None for s, _ in srcs):
        for s, cat in srcs:
            credit(s, cat, gain / len(srcs))


def attack_roll(att, tgt, bonus, parts, adv, dis, why, pen):
    """Credit everyone whose doing moved this attack's chance to hit: the sources
    of its advantage and disadvantage, allies' AC auras on the target, and
    whoever lowered the target's AC. Returns the damage at stake."""
    stake = avg(parts)
    ac = tgt.ac()
    p = p_hit(bonus, ac + pen, adv, dis)
    if adv:
        split_credit(why, "adv", (p - p_hit(bonus, ac + pen, False, dis)) * stake)
    if dis:
        split_credit(why, "dis", (p_hit(bonus, ac + pen, adv, False) - p) * stake)
    for g in tgt.allies():
        v = g.aura_ac(tgt)
        if v:
            credit(g, "protect", (p_hit(bonus, ac + pen - v, adv, dis) - p) * stake)
    for e in tgt.effects:
        if e.name == "ac" and (e.value or 0) < 0 and e.source not in (None, att) and e.source.side == att.side:
            credit(e.source, "enable", (p - p_hit(bonus, ac + pen - e.value, adv, dis)) * stake)
    return stake


def expected_damage(att, tgt, bonus, parts, ctx, adv, dis, pen):
    """An attack's expected damage against tgt, after its armour and resistances."""
    stake = 0.0
    for part in parts:
        x = avg([part])
        if tgt.resists(part.type, ctx, is_nonmagical(ctx, part.type)):
            x /= 2
        stake += x
    return p_hit(bonus, tgt.ac() + pen, adv, dis) * stake


def tanking(att, tgt, other, other_adv, bonus, parts, ctx, adv, dis, pen):
    """What att would have expected to deal to `other` (the one it would attack
    if tgt weren't there) minus what it expects to deal to tgt."""
    a, b = other_adv
    gain = (expected_damage(att, other, bonus, parts, ctx, a, b, pen)
            - expected_damage(att, tgt, bonus, parts, ctx, adv, dis, pen))
    credit(tgt, "tank", gain)


def penalty_die(att, tgt, pen, bonus, adv, dis, stake):
    """A penalty die on the roll (Covering Fire): what it took off the chance to hit."""
    if pen and pen.source is not None and pen.source.side != att.side:
        pen_avg = ((pen.value or 4) + 1) / 2
        p = p_hit(bonus, tgt.ac() + pen_avg, adv, dis)
        credit(pen.source, "control", (p_hit(bonus, tgt.ac(), adv, dis) - p) * stake)


def auto_crit(att, held, parts):
    """A hit on a held creature within 5 feet crits: the extra dice go to whoever held it."""
    if held.source is not att and held.source is not None and held.source.side == att.side:
        credit(held.source, "enable", avg_dice(parts))


# ----- saving throws -----------------------------------------------------------

def save_auto_fail(tgt, abil, dc, src, stake):
    """An incapacitated creature fails Strength and Dexterity saves: credit whoever
    incapacitated it with the chance it would otherwise have made it."""
    if not stake:
        return
    who = [e.source for e in tgt.effects if e.name in ("paralyzed", "stunned") and _helps(e.source, src)]
    for s in who:
        credit(s, "enable", p_roll(dc - tgt.save_bonus(abil)) * stake / len(who))


def save_roll(tgt, src, dc, bonus, stake, *, adv, dis, own_adv, own_dis, boosters, lift, lifter, hold, pen):
    """Credit everyone who moved a save's chance: allies granting advantage
    (boosters) or a bonus (lifter), and the attacker's allies whose restraint
    (hold) or penalty die (pen) made it worse."""
    if not stake:
        return
    ps = lambda adv, dis, lift, pen: p_roll(dc - bonus - lift + (2.5 if pen else 0), adv, dis)
    if boosters and not own_adv:
        for g in boosters:
            credit(g, "protect", (ps(True, dis, lift, pen) - ps(False, dis, lift, pen)) * stake / len(boosters))
    credit(lifter, "protect", (ps(adv, dis, lift, pen) - ps(adv, dis, 0, pen)) * stake)
    if hold and not own_dis and _helps(hold.source, src):
        credit(hold.source, "enable", (ps(adv, False, lift, pen) - ps(adv, True, lift, pen)) * stake)
    if pen and _helps(pen.source, src):
        credit(pen.source, "enable", (ps(adv, dis, lift, False) - ps(adv, dis, lift, True)) * stake)


def _helps(s, src):
    """s is on src's side, and isn't src itself."""
    return s is not None and s is not src and src is not None and s.side == src.side
