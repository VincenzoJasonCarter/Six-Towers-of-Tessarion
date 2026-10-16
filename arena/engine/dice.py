"""Dice, d20 rolls, and the hit and save chances the bots and Impact use."""
from __future__ import annotations

import random
from typing import NamedTuple

R = random.Random()   # every roll in a fight comes from here, so a seed replays it exactly


def seed(n):
    R.seed(n)


class Dice(NamedTuple):
    """Damage of one type: Dice(2, 6, "fire", 3) is 2d6 + 3 fire. A crit doubles `n`."""
    n: int
    die: int
    type: str
    plus: int = 0


def flat(amount, dtype):
    """A fixed amount of damage, no dice."""
    return Dice(0, 0, dtype, amount)


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


def roll_damage(parts, crit=False):
    """[Dice] -> {damage type: total}."""
    out = {}
    for p in parts:
        out[p.type] = out.get(p.type, 0) + d(2 * p.n if crit else p.n, p.die) + p.plus
    return out


def halved(dmg):
    """A damage packet after a successful save for half."""
    return {k: v // 2 for k, v in dmg.items()}


def avg(parts):
    """Average damage of [Dice]."""
    return sum(p.n * (p.die + 1) / 2 + p.plus for p in parts)


def avg_dice(parts):
    """Average of the dice alone, without the flat bonuses (what a crit adds)."""
    return sum(p.n * (p.die + 1) / 2 for p in parts)


# ----- chances ---------------------------------------------------------------

def p_roll(need, adv=False, dis=False):
    """Chance that a d20 (with advantage/disadvantage) shows `need` or more."""
    p = min(1.0, max(0.0, (21 - need) / 20))
    return _with_adv(p, adv, dis)


def p_hit(bonus, ac, adv=False, dis=False):
    """Chance an attack with `bonus` hits `ac` (a 1 always misses, a 20 always hits)."""
    p = min(0.95, max(0.05, (21 - (ac - bonus)) / 20))
    return _with_adv(p, adv, dis)


def p_fail(save_bonus, dc, adv=False, dis=False):
    """Chance a save with `save_bonus` fails against `dc`."""
    return 1 - p_roll(dc - save_bonus, adv, dis)


def _with_adv(p, adv, dis):
    if adv and not dis:
        return 1 - (1 - p) ** 2
    if dis and not adv:
        return p * p
    return p
