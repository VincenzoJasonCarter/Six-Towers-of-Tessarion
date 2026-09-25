# ---------------------------------------------------------------
# Monster generation
# ---------------------------------------------------------------
#
# Base stat blocks are hand-authored YAML in monsters/ at the project
# root (see characters/ for the same pattern on the player side) - not
# hardcoded here, so adding a new monster is a data change, not a code
# change.
#
# monsters/*.yaml (this directory only - list_monster_templates()
# doesn't recurse) is the active common-mob roster for a regular
# floor's encounter (see generate_encounter()): Thal'Vireth's own
# guards, not yet corrupted - a Temporal Gladiator anchoring the
# frontline, with a difficulty-scaled chance of Arcanist/Ranger/
# Chronoswarm support joining it, instead of a single monster alone.
# Each declares a "role" (frontline/backline_magic/backline_physical/
# swarm) - generate_encounter() is the only thing that reads it; a
# template without one is never picked there.
#
# monsters/bosses/ and monsters/corrupted/ are separate, deliberately
# excluded pools (subdirectories aren't picked up by the *.yaml glob):
# bosses are spawned by floor number, never randomly (see run.py's
# BOSS_TEMPLATES); monsters/corrupted/ is the older "Timeline Echo"
# roster (homebrew stat blocks themed around the Verdant Tower's
# corrupted temporal authority, with flavor-level Time Stop/Skip nods -
# not an implementation of the real corrupted-zone mechanic, which is
# still an open design question per CLAUDE.md) - kept, not deleted, as
# the likely roster for a future corrupted-floor pool rather than the
# regular one.
#
# What's still rolled per fight, on top of a template: ability scores
# get a small jitter and HP is rolled fresh from the template's hit
# dice, so two fights against "the same" monster aren't identical.

import random
from pathlib import Path

import yaml

from .dice import ability_modifier, roll

# dnd/ -> floor_generator/ -> src/ -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MONSTERS_DIR = PROJECT_ROOT / "monsters"

JITTER = [-1, 0, 0, 1]


def list_monster_templates():
    """Paths of every monster YAML template in monsters/, sorted for
    reproducibility (so rng.choice() over them is seed-stable)."""
    return sorted(MONSTERS_DIR.glob("*.yaml"))


# Which template shows up (_difficulty_weight, above) only changes the
# odds of drawing a scarier stat block - on its own that still let a
# floor-10 "easy" template roll with the exact same numbers as the
# same template on floor 1. This scales the monster's own numbers on
# top of that, so the climb gets harder even when the same template
# comes up twice. difficulty is 0.0 on floor 1, 1.0 on the tower's
# final floor (see run.py/gui.py), so these are the floor-1 -> floor-10
# bounds, not per-floor increments.
HP_MULT_AT_MAX_DIFFICULTY = 0.6    # +60% HP by the final floor
AC_BONUS_AT_MAX_DIFFICULTY = 2     # +2 AC
ATTACK_BONUS_AT_MAX_DIFFICULTY = 3  # +3 to hit
DAMAGE_BONUS_AT_MAX_DIFFICULTY = 3  # +3 damage per hit


def _difficulty_scaling(difficulty):
    """Stat bonuses for a monster generated at the given difficulty
    (0.0-1.0, see generate_monster). Returns a flat 1.0/0 scaling at
    difficulty=None so an unscaled call (e.g. a one-off monster.py
    caller that never passes difficulty) behaves exactly as before."""
    d = difficulty or 0.0
    return {
        "hp_mult": 1.0 + d * HP_MULT_AT_MAX_DIFFICULTY,
        "ac_bonus": round(d * AC_BONUS_AT_MAX_DIFFICULTY),
        "attack_bonus": round(d * ATTACK_BONUS_AT_MAX_DIFFICULTY),
        "damage_bonus": round(d * DAMAGE_BONUS_AT_MAX_DIFFICULTY),
    }


def generate_monster(rng=None, seed=None, name=None, cr=None, template_path=None, difficulty=None):
    """Roll a monster from one of the stat-block templates in monsters/.

    template_path picks a specific template file directly; otherwise
    one is chosen uniformly at random (via rng) from every template in
    monsters/ - see generate_encounter() for the role-aware composition
    regular floors actually use instead of a single uniform pick.
    difficulty (0.0-1.0), if given, scales the resulting stat block's
    HP/AC/attack bonus/damage upward (see _difficulty_scaling) - see
    run.py's per-floor difficulty curve.

    Ability scores are jittered and HP is rolled fresh, same as before
    this became template-driven.
    """
    if rng is None:
        rng = random.Random(seed)

    if template_path is None:
        templates = list_monster_templates()
        if not templates:
            raise RuntimeError(f"No monster templates found in {MONSTERS_DIR}")
        template_path = rng.choice(templates)

    with open(template_path, "r", encoding="utf-8") as f:
        template = yaml.safe_load(f)

    scores = {ability: max(3, base + rng.choice(JITTER)) for ability, base in template["base_scores"].items()}
    modifiers = {ability: ability_modifier(score) for ability, score in scores.items()}

    hp = sum(max(1, roll(rng, 1, 8) + modifiers["CON"]) for _ in range(template["hit_dice"]))
    ac = template["ac_base"] + max(0, modifiers["DEX"])
    prof = template.get("proficiency_bonus", 2)

    scaling = _difficulty_scaling(difficulty)
    hp = max(1, round(hp * scaling["hp_mult"]))
    ac += scaling["ac_bonus"]

    attacks = []
    for atk in template["attacks"]:
        ability = atk.get("ability", "STR")
        # "uses" (per-encounter cap) mirrors the character-side
        # convention in character.py - absent/None means at-will. None
        # of the current templates limit an attack, but the field is
        # here so one could without touching the combat engine.
        entry = {
            "name": atk["name"],
            "kind": atk["kind"],
            "attack_bonus": prof + modifiers[ability] + scaling["attack_bonus"],
            "damage_dice": atk["damage_dice"],
            "damage_bonus": modifiers[ability] + scaling["damage_bonus"],
            "damage_type": atk["damage_type"],
            "range": atk["range"],
            "uses": atk.get("uses"),
            "uses_remaining": atk.get("uses"),
        }
        if atk["kind"] == "hazard":
            # cast_hazard() (combat.py) indexes these directly, same as
            # a character's hazard spell (see character.py's
            # SPELL_LIBRARY) - area_size falls back the same way
            # cast_hazard() itself does, but save_ability/duration_rounds
            # are required, not optional, for a template to define one.
            entry["area_size"] = atk.get("area_size", 1)
            entry["save_ability"] = atk["save_ability"]
            entry["duration_rounds"] = atk["duration_rounds"]
        attacks.append(entry)

    result = {
        "name": name or template["name"],
        "type": template["type"],
        "challenge_rating": cr if cr is not None else template["challenge_rating"],
        "scores": scores,
        "modifiers": modifiers,
        "hp": hp,
        "max_hp": hp,
        "ac": ac,
        "speed": template["speed"],
        "proficiency_bonus": prof,
        "traits": template.get("traits", []),
        "attacks": attacks,
    }
    if "spell_save_dc" in template:
        # Only needed by a template with a hazard attack - cast_hazard()
        # (combat.py) falls back to a flat DC 10 via .get() when absent,
        # same as it always has for every existing (non-hazard) template.
        result["spell_save_dc"] = template["spell_save_dc"]
    return result


def generate_monster_group(rng=None, seed=None, difficulty=None, template_path=None):
    """Like generate_monster(), but always returns a list of one or
    more monster dicts.

    Most templates are still fought one at a time, so this just wraps
    a single generate_monster() call in a list. A template with a
    "group_size" [lo, hi] field (a swarm - see monsters/chronoswarm.yaml)
    instead rolls a count in that range and generates that many
    independent instances of it (jitter and HP rolled separately for
    each, so they aren't identical copies), each with a unique "#N"
    suffix on its name so they don't collide as combatants/positions
    keys - generate_encounter() reuses this same expansion for a
    "swarm"-role template it selects.

    The template is picked once here (uniformly, unless template_path
    already picks one) and passed down via template_path so every
    instance in a group comes from the same roll of the RNG, not a
    fresh pick per monster.
    """
    if rng is None:
        rng = random.Random(seed)

    if template_path is None:
        templates = list_monster_templates()
        if not templates:
            raise RuntimeError(f"No monster templates found in {MONSTERS_DIR}")
        template_path = rng.choice(templates)

    with open(template_path, "r", encoding="utf-8") as f:
        template = yaml.safe_load(f)

    group_size = template.get("group_size")
    if not group_size:
        return [generate_monster(rng, template_path=template_path, difficulty=difficulty)]

    lo, hi = group_size
    count = rng.randint(lo, hi)
    base_name = template["name"]
    return [
        generate_monster(rng, template_path=template_path, name=f"{base_name} #{i + 1}", difficulty=difficulty)
        for i in range(count)
    ]


# generate_encounter()'s composition rules. A frontline anchor
# (Temporal Gladiator) is always present; each support role then joins
# with probability BASE_CHANCE + difficulty * DIFFICULTY_CHANCE (capped
# at 1.0 by random() never exceeding 1) - so floor 1 is often just the
# Gladiator alone or with a single helper, and floor 10 is likely a
# full mixed squad. EXTRA_FRONTLINE_CHANCE_AT_MAX_DIFFICULTY is the
# chance of a second Gladiator, scaled by difficulty the same way.
ENCOUNTER_ROLE_CHANCES = {
    "backline_magic": (0.35, 0.35),
    "backline_physical": (0.35, 0.35),
    "swarm": (0.25, 0.35),
}
EXTRA_FRONTLINE_CHANCE_AT_MAX_DIFFICULTY = 0.5


def generate_encounter(rng=None, seed=None, difficulty=None):
    """Roll a mixed-role encounter for a regular (non-boss) floor - a
    Temporal Gladiator anchoring the frontline, with a difficulty-
    scaled chance of Temporal Arcanist/Ranger/Chronoswarm support
    joining it (see ENCOUNTER_ROLE_CHANCES), instead of always a
    single monster alone. Only templates that declare a "role" field
    are eligible (see monster.py's module docstring) - monsters/bosses/
    and monsters/corrupted/ aren't in monsters/ at all, so they're
    never in the running regardless.

    Every selected template still goes through generate_monster(), so
    difficulty scales each individual's stats the same way it does
    everywhere else - composition (who shows up) and scaling (how
    tough they are) are independent, stacking dials.

    Returns a list of one or more monster dicts, uniquely named the
    same way generate_monster_group() names a swarm.
    """
    if rng is None:
        rng = random.Random(seed)

    by_role = {}
    for path in list_monster_templates():
        with open(path, "r", encoding="utf-8") as f:
            template = yaml.safe_load(f)
        role = template.get("role")
        if role:
            by_role.setdefault(role, []).append((path, template))

    d = difficulty or 0.0
    monsters = []

    def spawn(template_path, count):
        base_name = None
        for i in range(count):
            m = generate_monster(rng, template_path=template_path, difficulty=difficulty)
            if count > 1:
                base_name = base_name or m["name"]
                m["name"] = f"{base_name} #{i + 1}"
            monsters.append(m)

    frontline = by_role.get("frontline")
    if frontline:
        path, _ = rng.choice(frontline)
        count = 2 if rng.random() < d * EXTRA_FRONTLINE_CHANCE_AT_MAX_DIFFICULTY else 1
        spawn(path, count)

    for role, (base_chance, difficulty_chance) in ENCOUNTER_ROLE_CHANCES.items():
        pool = by_role.get(role)
        if not pool or rng.random() >= base_chance + d * difficulty_chance:
            continue
        path, template = rng.choice(pool)
        group_size = template.get("group_size")
        spawn(path, rng.randint(*group_size) if group_size else 1)

    if not monsters and by_role:
        # Every role happened to roll "no" (or there's no frontline
        # template at all) - never hand back an empty encounter.
        path, _ = rng.choice(next(iter(by_role.values())))
        spawn(path, 1)

    return monsters
