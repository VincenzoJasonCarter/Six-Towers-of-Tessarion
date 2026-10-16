"""What an attack, save or damage packet is about, for the features that care.

Every rule function takes one of these and every hook receives it. Fields left
at their defaults simply don't apply.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

__all__ = ["Ctx", "replace"]


@dataclass(slots=True)
class Ctx:
    # ----- what kind of thing it is
    kind: str | None = None      # "melee" | "ranged" for an attack roll
    spell: bool = False          # a spell (Null Field, Mana Cage and Aether's resistance care)
    level: int = 0               # the spell's level (Null Field only stops 3rd or lower)
    magical: bool = False        # gets through Anchored Stance's resistance
    weapon: str | None = None    # name of the weapon making the attack, if any
    name: str | None = None      # the spell or feature, for features keyed on one
    attack: bool = False         # damage from an attack roll (set by attack() on its damage)
    oa: bool = False             # an opportunity attack

    # ----- how much it matters (bots and Legendary Resistance)
    control: bool = False        # a save against being taken out of the fight (Hold, nets, fear...)
    big: bool = False            # a damaging spell worth a Legendary Resistance
    damage: bool = False         # a damaging spell (Crimson Presence, Overlord)
    single: bool = False         # targets one creature (Intercepting Guard, Null Field's reroll)
    fear: bool = False           # a fear effect (Memory of the Grove)
    group: list | None = None    # every target of the spell (Flux Manipulation picks one save for all)
    predict: bool = False        # a bot estimating, not a real roll: hooks mustn't spend anything
    stake: float = 0.0           # damage a failed save costs over a success (credited to helpers)

    # ----- filled in while an attack resolves
    crit: bool = False
    bonus: int = 0               # the attack's to-hit bonus (Null Field rerolls the attack)
    intercepted: bool = False    # Intercepting Guard already stepped in

    # ----- subclass riders
    special: str | None = None   # the special arrow or shot loaded (Range)
    attack_action: bool = False  # part of the Attack action (Silent Volley)
    powder: bool = False         # a firearm shot from 7th level: concentration saves at disadvantage
    barrage: bool = False        # Soulshot Barrage
    pact: int = 0                # Red Pact dice spent on this hit (Sanguine Aegis)
