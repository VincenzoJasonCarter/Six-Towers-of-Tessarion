# ---------------------------------------------------------------
# 5e dice primitives
# ---------------------------------------------------------------

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


def roll(rng, n, sides):
    return sum(rng.randint(1, sides) for _ in range(n))


def roll_dice_string(rng, dice_str):
    """Roll a "NdM" string, e.g. "2d6"."""
    n, sides = dice_str.lower().split("d")
    return roll(rng, int(n), int(sides))


def roll_d20(rng, advantage=False, disadvantage=False):
    a = rng.randint(1, 20)
    if not (advantage or disadvantage):
        return a
    b = rng.randint(1, 20)
    return max(a, b) if advantage else min(a, b)


def roll_ability_score(rng):
    """4d6, drop the lowest die - standard 5e generation method."""
    dice = sorted(rng.randint(1, 6) for _ in range(4))
    return sum(dice[1:])


def ability_modifier(score):
    return (score - 10) // 2


def proficiency_bonus(level):
    return 2 + (level - 1) // 4
