import random
from collections import Counter
from dataclasses import dataclass, field

# lore-book/08-on-resonant-crafting.md, Step 4
RESONANCE_DC = {1: 50, 2: 55, 3: 65, 4: 80, 5: 100, 6: 125}
RARITY = {1: "Uncommon", 2: "Uncommon (Refined)", 3: "Rare", 4: "Epic", 5: "Legendary", 6: "Mythic"}

# lore-book/08-on-resonant-crafting.md, Step 5 — "Item Result" column
OUTCOME_INFO = {
    "Resonant Apex": "Item reaches PR ceiling. Gains one Echo Trait.",
    "Full Resonance": "Item reaches PR ceiling. Standard resonant item.",
    "Threshold": "Item reaches PR ceiling, but one Posture modifier is locked (DM's choice).",
    "Dim Resonance": "Item forms one rarity tier below PR ceiling. Posture functions at half modifier values.",
    "Fractured Emergence": "Item forms two rarity tiers below PR ceiling. Fracture Identity is immediately active.",
    "Rejection": "Soulstone refuses entirely. Item reverts to foundational. DC 15 CON save or 1 exhaustion level.",
}


@dataclass
class ResonanceBuild:
    power_rating: int
    posture_mode: str = "single"  # "single" | "dual"
    tool_proficiency: bool = False
    expert_tools: bool = False
    location_bonus: int = 0  # 0, or +5 to +15 at DM's discretion
    prior_crafts: int = 0  # capped at 5 in modifier calc
    soulstone: str = "off-native"  # "native" | "off-native" | "hostile"
    mixed_binding: bool = False
    currently_fractured: bool = False

    def modifier_breakdown(self) -> list[tuple[str, float]]:
        rows: list[tuple[str, float]] = []
        if self.tool_proficiency:
            rows.append(("Relevant tool proficiency", 5))
        if self.expert_tools:
            rows.append(("Expert-grade tools", 3))
        if self.location_bonus:
            rows.append(("Ambient resonance location", self.location_bonus))
        if self.prior_crafts:
            rows.append(("Prior successful crafts (this Posture)", min(self.prior_crafts, 5)))
        if self.soulstone == "native":
            rows.append(("Native soulstone", 5))
        elif self.soulstone == "hostile":
            rows.append(("Hostile soulstone", -10))
        if self.posture_mode == "single":
            rows.append(("Single Posture (exposure cost)", -5))
        if self.mixed_binding:
            rows.append(("Mixed Binding", -10))
        if self.currently_fractured:
            rows.append(("Currently suffering a fracture effect", -5))
        return rows

    def total_modifier(self) -> float:
        return sum(v for _, v in self.modifier_breakdown())

    def dc(self) -> int:
        return RESONANCE_DC[self.power_rating]

    def fractured_emergence_start(self) -> int:
        # lore-book/08-on-resonant-crafting.md — "Stability Threshold"
        return -8 if self.posture_mode == "single" else -12


def roll_pool(power_rating: int, rng: random.Random) -> list[int]:
    return [rng.randint(1, 20) for _ in range(power_rating + 1)]


def classify(diff: float, build: ResonanceBuild) -> str:
    if diff >= 15:
        return "Resonant Apex"
    if diff >= 1:
        return "Full Resonance"
    if diff == 0:
        return "Threshold"
    if diff <= -20:
        return "Rejection"
    if diff <= build.fractured_emergence_start():
        return "Fractured Emergence"
    return "Dim Resonance"


@dataclass
class RollResult:
    dice: list[int]
    dice_sum: int
    modifier: float
    total: int
    dc: int
    diff: float
    outcome: str


def simulate_once(build: ResonanceBuild, rng: random.Random) -> RollResult:
    dice = roll_pool(build.power_rating, rng)
    dice_sum = sum(dice)
    modifier = build.total_modifier()
    total = dice_sum + modifier
    dc = build.dc()
    diff = total - dc
    outcome = classify(diff, build)
    return RollResult(dice=dice, dice_sum=dice_sum, modifier=modifier, total=total, dc=dc, diff=diff, outcome=outcome)


def simulate_many(build: ResonanceBuild, n: int, rng: random.Random) -> Counter:
    counts: Counter = Counter()
    for _ in range(n):
        counts[simulate_once(build, rng).outcome] += 1
    return counts
