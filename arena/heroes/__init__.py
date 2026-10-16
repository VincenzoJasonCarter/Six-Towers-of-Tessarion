"""The eleven subclasses as fighting creatures, built from
lore-book/05-subclasses-skill.md.

    base.py           what every hero shares (levels, scores, targeting)
    wizard.py         the Wizard chassis: slots, spells, the spell-choosing bot
    crystal_mages.py  Verdant, Warbound, Stonewarden, Hellbound, Sanguine and Aether Mages
    fighter.py        the martial chassis: one attack a turn, weapons, the melee bot
    aegisbound.py     Sanguine, Bulwark and Warden Aegis
    ranged.py         Crystal Archer and Gunman, their ammunition and gear
    evolution.py      the Ascendant and Corrupted branches (draft)

Every hero is built as Class(level), or Class(level, gear=True) to give the
Range subclasses Tessarion's own weapons.
"""
from .aegisbound import BulwarkAegis, SanguineAegis, WardenAegis
from .crystal_mages import AetherMage, HellboundMage, SanguineMage, StonewardenMage, VerdantMage, WarboundMage
from .ranged import CrystalArcher, Gunman

ROSTER = [VerdantMage, WarboundMage, StonewardenMage, HellboundMage, SanguineMage, AetherMage,
          SanguineAegis, BulwarkAegis, WardenAegis, CrystalArcher, Gunman]
BY_KEY = {c.key: c for c in ROSTER}


class SanguineMageNoSwap(SanguineMage):
    """What-if: Flux Manipulation keeps its damage-type swap but loses the save swap."""
    key, label = "sanguine_mage_noswap", "Sanguine Mage without Flux's save swap"

    def save_ability(self, tgt, abil, ctx, commit=False):
        return abil


VARIANTS = [SanguineMageNoSwap]   # what-ifs run.py compares against the subclass as written
BY_KEY.update({c.key: c for c in VARIANTS})
