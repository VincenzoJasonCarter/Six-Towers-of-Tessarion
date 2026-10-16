"""Rules core for the Proving Grounds.

A fight is two sides on a straight 120-foot line with a wall at each end: one
creature against one other (run.py), or a party against an encounter
(party.py). Only the 5e rules that the subclasses and the benchmark foes
actually touch are modelled; README.md lists what is left out.

    dice.py      Dice, d20 rolls, hit and save chances
    context.py   Ctx: what an attack, save or damage packet is about
    impact.py    crediting creatures with protection, control, enable and tanking
    movement.py  walking the line, opportunity attacks, pushes
    creature.py  Creature, its effects and every hook a feature can use
    combat.py    attack(), saving_throw(), deal()
    fight.py     Fight: formation, initiative, the turn loop
"""
from .combat import attack, attack_adv, cage_over, deal, saving_throw
from .context import Ctx, replace
from .creature import Conc, Creature, Effect, Zone
from .dice import (R, Dice, avg, avg_dice, d, d20, flat, halved, mod, p_fail, p_hit, p_roll, roll_damage,
                   seed)
from .fight import Fight
from .impact import causes, credit, deny
from .movement import ARENA, move, move_to, push, room_behind
