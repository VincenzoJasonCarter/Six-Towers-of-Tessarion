# ---------------------------------------------------------------
# Tower run: chains floors together into a full 10-floor climb
# ---------------------------------------------------------------
#
# A single CombatEngine/simulate_combat call is one floor's fight
# against one random monster - this module is the layer above that:
# a fixed-length sequence of floors, most of them a fight against a
# random monster (see monster.py's roster), a healing floor with no
# monster where the character gets a full rest instead right before
# each of the two boss floors, and the bosses themselves (see
# BOSS_TEMPLATES) on floors 5 and 10.
#
# The character dict (see character.py) is loaded once and threaded
# through every floor unchanged except for its mutable state (hp,
# attacks[].uses_remaining, soul_tether.uses_remaining) - that's what
# makes it a run instead of ten unrelated one-off fights: damage and
# spent resources carry forward, and only a healing floor resets them.

import argparse
import random

from .character import load_character
from .combat import simulate_combat
from .monster import MONSTERS_DIR

FLOOR_COUNT = 10

# Fixed, not randomized like the rest of the plan - healing sits right
# before each boss so the climb always gives the party a chance to
# rest up before the fight that's actually meant to test them, rather
# than risking a boss landing right after a random string of regular
# fights has already worn the party down.
HEALING_FLOORS = {4, 9}
BOSS_FLOORS = {5, 10}

# Which boss template (see monster.py's generate_monster_group()
# template_path) a boss floor forces, instead of a difficulty-weighted
# roll from the regular roster - keyed by floor number. Kept in
# monsters/bosses/ specifically so list_monster_templates() (a plain,
# non-recursive glob of monsters/*.yaml) never picks one for a regular
# floor by chance.
BOSS_TEMPLATES = {
    5: MONSTERS_DIR / "bosses" / "chronophage.yaml",
    10: MONSTERS_DIR / "bosses" / "revenant_of_yesterday.yaml",
}


def generate_floor_plan(floor_count=FLOOR_COUNT):
    """Decide which floors are a regular fight, a boss fight, or a
    healing chamber - see HEALING_FLOORS/BOSS_FLOORS above; everything
    else is a regular combat floor.

    Returns a list of {"number", "type"} dicts, 1-indexed, "type" is
    "combat", "boss", or "healing".
    """

    return [
        {
            "number": n,
            "type": "healing" if n in HEALING_FLOORS else "boss" if n in BOSS_FLOORS else "combat",
        }
        for n in range(1, floor_count + 1)
    ]


def apply_healing(character, log=None):
    """A healing floor's effect: full HP, and every limited-use attack
    and class feature (Soul Tether) restored - the sim's stand-in for
    a long rest, since there's no other rest mechanic."""

    character["hp"] = character["max_hp"]
    for attack in character["attacks"]:
        if attack.get("uses") is not None:
            attack["uses_remaining"] = attack["uses"]
    soul_tether = character.get("soul_tether")
    if soul_tether and soul_tether.get("uses") is not None:
        soul_tether["uses_remaining"] = soul_tether["uses"]

    if log is not None:
        log.append(f"{character['name']} rests here. HP and spent abilities are fully restored.")


def simulate_run(character_path=None, seed=42, max_rounds_per_floor=20, verbose=True):
    """Headless version of a full tower climb - runs simulate_combat
    floor by floor against the same persistent character dict, until
    either all floors are cleared or the character falls.
    """

    rng = random.Random(seed)
    character = load_character(character_path)
    plan = generate_floor_plan()

    log = []
    floor_results = []
    victory = False
    floors_cleared = 0

    for floor in plan:
        log.append(f"=== Floor {floor['number']}/{len(plan)} ({floor['type']}) ===")

        if floor["type"] == "healing":
            apply_healing(character, log)
            floor_results.append({"floor": floor["number"], "type": "healing"})
            floors_cleared = floor["number"]
            continue

        floor_seed = rng.randint(0, 2**31 - 1)
        # 0.0 on floor 1, 1.0 on the last floor - biases which monster
        # template shows up (see monster.py's DIFFICULTY_ORDER) without
        # ever fully excluding the hardest one early or the easiest late.
        # A boss floor's template is forced regardless (see
        # BOSS_TEMPLATES), but difficulty still scales its stats.
        difficulty = (floor["number"] - 1) / (FLOOR_COUNT - 1)
        boss_template = BOSS_TEMPLATES.get(floor["number"]) if floor["type"] == "boss" else None
        result = simulate_combat(
            character=character, seed=floor_seed, floor_seed=floor_seed,
            max_rounds=max_rounds_per_floor, verbose=False, monster_difficulty=difficulty,
            monster_template_path=boss_template,
        )
        log.extend(result["log"])
        floor_results.append({
            "floor": floor["number"], "type": floor["type"],
            "monsters": [m["name"] for m in result["monsters"]], "winner": result["winner"],
        })

        if result["winner"] != character["name"]:
            log.append(f"=== {character['name']} falls on floor {floor['number']}. The climb ends here. ===")
            break

        floors_cleared = floor["number"]
    else:
        victory = True
        log.append(f"=== {character['name']} clears all {len(plan)} floors of Thal'Vireth! ===")

    if verbose:
        for line in log:
            print(line)

    return {
        "character": character,
        "plan": plan,
        "floors": floor_results,
        "log": log,
        "victory": victory,
        "floors_cleared": floors_cleared,
    }


def main():
    parser = argparse.ArgumentParser(description="Simulate a full 10-floor Thal'Vireth tower climb.")
    parser.add_argument("--character", default=None, help="Path to a character YAML config (defaults to Pijo).")
    parser.add_argument("--seed", type=int, default=42, help="Seed for the floor plan, monsters, and combat rolls.")
    parser.add_argument("--max-rounds", type=int, default=20, help="Round limit per combat floor.")
    parser.add_argument("--quiet", action="store_true", help="Suppress the round-by-round log.")

    args = parser.parse_args()

    result = simulate_run(
        character_path=args.character, seed=args.seed,
        max_rounds_per_floor=args.max_rounds, verbose=not args.quiet,
    )

    if args.quiet:
        outcome = "Victory!" if result["victory"] else "Defeat."
        print(f"{outcome} Floors cleared: {result['floors_cleared']}/{FLOOR_COUNT}")


if __name__ == "__main__":
    main()
