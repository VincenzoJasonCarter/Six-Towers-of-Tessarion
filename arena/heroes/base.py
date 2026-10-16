"""What every hero shares: level maths, ability scores, and targeting."""
from engine import Creature

# Resonance Rank: a subclass's dice grow each time it gains a subclass feature.
RANK_LEVELS = {"Wizard": (2, 6, 10, 14), "Fighter": (3, 7, 10, 15)}


def prof(level):
    return 2 + (level - 1) // 4


def item(level):
    """+N of the weapon or spell focus everyone carries at this level."""
    return 0 if level < 5 else 1 if level < 15 else 2


def tier(level):
    """Cantrip damage tier: 1 to 4."""
    return 1 + (level >= 5) + (level >= 11) + (level >= 17)


def resonance_rank(level, chassis):
    return max(1, sum(level >= lv for lv in RANK_LEVELS[chassis]))


def scores_at(base, primary, level, asi_levels):
    """Ability scores at `level`: each increase goes into the main stat, then Constitution."""
    s = dict(base)
    for lv in asi_levels:
        if lv <= level:
            if s[primary] < 20:
                s[primary] += 2
            elif s["con"] < 20:
                s["con"] += 2
    return s


def legendary_left(creatures):
    """Legendary Resistances the creatures still have (heroes have none)."""
    return sum(getattr(c, "legendary", 0) for c in creatures)


def most_hurt(creatures):
    return min(creatures, key=lambda c: c.hp / c.max_hp)


class Hero(Creature):
    key = label = chassis = ""
    guard = False   # holds the line in front of the back rank instead of charging

    def __init__(self, level, scores, save_profs, hp, ac):
        super().__init__(self.label, level, scores, save_profs, prof(level), hp, ac)
        self.item = item(level)
        self.rank = resonance_rank(level, self.chassis)

    def reach_of_attacks(self):
        return self.reach if self.style == "melee" else self.max_range

    def pick_target(self):
        """Guards: whatever is nearest the ally they protect. Otherwise focus fire
        on the most hurt enemy in reach or range, else go for the nearest."""
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
