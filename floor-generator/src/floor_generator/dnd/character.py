# ---------------------------------------------------------------
# Character loading
# ---------------------------------------------------------------
#
# Characters are defined in YAML config, not generated procedurally -
# this simulation runs real campaign characters, starting with Pijo.
# Configs live in characters/ at the project root, outside src/, since
# they're campaign data to be hand-edited, not package code.
#
# characters/pijo.yaml is a raw export from a character-sheet app (the
# one used to actually run the campaign), not a format designed for
# this sim - it has ability scores, HP, AC, weapons and spell names,
# but none of the mechanical crunch the combat engine needs for spells
# (range, save DC/ability, area, duration, limited uses) and nothing
# at all for homebrew class features (Soul Tether). This loader:
#
#   1. Reads the raw export as-is (so it can keep being re-exported
#      whenever the real sheet changes - level up, new gear, etc.).
#   2. Fills in the missing mechanical crunch for spells it recognizes
#      by name, via SPELL_LIBRARY below.
#   3. Adds back class features the export doesn't capture, via
#      CLASS_FEATURES below.
#
# A spell not in SPELL_LIBRARY still loads (as a plain melee spell
# attack, no special mechanics) instead of crashing - see
# _build_spell_attack(). Add it to the library to give it real rules.

import re
from pathlib import Path

import yaml

from .dice import ABILITIES, ability_modifier

# dnd/ -> floor_generator/ -> src/ -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "characters"
DEFAULT_CHARACTER = DATA_DIR / "pijo.yaml"

# The export's "speed" is in feet, like the rest of a 5e sheet - the
# sim's grid uses meters. 0.3 (not the precise 0.3048) matches the
# stylized conversion already used everywhere else in this project
# (30 ft speed -> 9 m, 5 ft reach -> 1.5 m, 60 ft range -> 18 m).
FEET_TO_METERS = 0.3

ABILITY_KEYS = {
    "STR": "strength",
    "DEX": "dexterity",
    "CON": "constitution",
    "INT": "intelligence",
    "WIS": "wisdom",
    "CHA": "charisma",
}

DAMAGE_TYPE_LETTERS = {"B": "bludgeoning", "S": "slashing", "P": "piercing"}

# Mechanical stats for known spells - see the module docstring. Keyed
# by the exact name the character-sheet export uses in spells[].name.
# "kind": "hazard" places a zone (see combat.py's cast_hazard()); any
# other kind resolves as a normal attack roll (resolve_attack()).
# Leaving "uses" out makes the spell at-will (cantrips).
SPELL_LIBRARY = {
    "Create Bonfire": {
        "kind": "hazard",
        "range": 18,      # meters (60 ft) - max distance the zone can be placed from the caster
        "area_size": 5,   # meters - forced-save zone, centered on the target (bigger than the real 5 ft cube, by request)
        "damage_dice": "1d8",
        "damage_type": "fire",
        "save_ability": "DEX",
        "duration_rounds": 10,  # "Concentration, up to 1 minute" simplified to a flat timer
    },
    "Inflict Wounds": {
        "kind": "melee_spell",
        "range": 1.5,     # meters (5 ft, touch)
        "damage_dice": "3d10",
        "damage_type": "necrotic",
        "uses": 2,        # Pijo's one 1st-level slot at level 2, capped per encounter (no rest mechanic in the sim)
    },
}

# Homebrew class features a generic character-sheet export has no
# field for, merged in by className if the export doesn't already
# define them. See engine.py's player_use_soul_tether().
CLASS_FEATURES = {
    "Sanguine Mage": {
        "soul_tether": {
            "damage_dice": "1d4",
            "damage_type": "necrotic",
            "duration_rounds": 3,
            "uses": 2,
        },
    },
}


def _parse_weapon(weapon):
    """"1d4-1/B" -> dice "1d4", bonus -1, type "bludgeoning". The
    export has no reach/range data, so every weapon is treated as a 5
    ft/1.5 m melee weapon - true for Quarterstaff, but would need a
    real fix if a ranged weapon (bow, thrown dagger, ...) shows up."""

    dice_part, _, type_letter = weapon["damage"].partition("/")
    m = re.match(r"(\d+d\d+)([+-]\d+)?", dice_part)
    dice = m.group(1)
    bonus = int(m.group(2)) if m.group(2) else 0

    return {
        "name": weapon["name"],
        "kind": "melee",
        "attack_bonus": int(weapon["attackBonus"]),  # "+1" -> 1, int() handles the leading sign
        "damage_dice": dice,
        "damage_bonus": bonus,
        "damage_type": DAMAGE_TYPE_LETTERS.get(type_letter, type_letter.lower() or "bludgeoning"),
        "range": 1.5,
    }


def _build_spell_attack(spell, spell_attack_bonus):
    name = spell["name"]
    cfg = SPELL_LIBRARY.get(name)
    if cfg is None:
        # Unrecognized spell - load it as a generic melee spell attack
        # rather than skip it or crash. Add it to SPELL_LIBRARY to give
        # it real range/save/area/uses.
        cfg = {"kind": "melee_spell", "range": 1.5, "damage_dice": "1d6", "damage_type": "force"}

    attack = {"name": name, **cfg}
    if attack["kind"] != "hazard":
        attack["attack_bonus"] = spell_attack_bonus
        attack.setdefault("damage_bonus", 0)
    if spell.get("level", 0) > 0:
        attack.setdefault("uses", 2)  # no slot-count data in the export - see SPELL_LIBRARY docstring
    return attack


def _apply_class_features(character):
    for key, cfg in CLASS_FEATURES.get(character.get("class"), {}).items():
        character.setdefault(key, dict(cfg))


def load_character(path=None):
    """Load a character from the character-sheet app's raw YAML
    export.

    Returns a dict in the shape the combat engine expects for both
    characters and monsters: name, hp, max_hp, ac, speed, modifiers,
    attacks (weapons + recognized spells), spell_save_dc, and any
    homebrew class features (see CLASS_FEATURES).
    """

    path = Path(path) if path else DEFAULT_CHARACTER

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    scores = {
        ability: raw["abilities"][ABILITY_KEYS[ability]]["score"] for ability in ABILITIES
    }
    modifiers = {ability: ability_modifier(score) for ability, score in scores.items()}

    proficiency_bonus = raw.get("proficiencyBonus", 2)
    # Sanguine Mage casts off INT, like a Wizard (see the master sheet's
    # SpellcastingAbility field) - not itself in this export, so it's
    # assumed rather than read.
    spell_ability_mod = modifiers["INT"]
    spell_attack_bonus = proficiency_bonus + spell_ability_mod
    spell_save_dc = 8 + proficiency_bonus + spell_ability_mod

    attacks = [_parse_weapon(w) for w in raw.get("weapons", [])]
    attacks += [_build_spell_attack(s, spell_attack_bonus) for s in raw.get("spells", [])]
    for attack in attacks:
        attack["uses_remaining"] = attack.get("uses")

    character = {
        "name": raw["name"],
        "class": raw.get("className"),
        "level": raw.get("level"),
        "scores": scores,
        "modifiers": modifiers,
        "proficiency_bonus": proficiency_bonus,
        "hp": raw["currentHitPoints"],
        "max_hp": raw["hitPointMaximum"],
        "ac": raw["armorClass"],
        "speed": raw["speed"] * FEET_TO_METERS,
        "spell_save_dc": spell_save_dc,
        "attacks": attacks,
    }

    _apply_class_features(character)
    if "soul_tether" in character:
        character["soul_tether"]["uses_remaining"] = character["soul_tether"].get("uses")

    return character
