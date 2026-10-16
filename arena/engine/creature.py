"""Creatures, the effects on them, concentration, and zones on the line.

Effects are named. The names the engine itself checks:

| Effect          | Means                                                        | Added by                 |
|-----------------|--------------------------------------------------------------|--------------------------|
| paralyzed       | incapacitated, auto-fails Str/Dex saves, hits within 5 ft crit | Hold Person/Monster     |
| stunned         | incapacitated, auto-fails Str/Dex saves                      | Soulshot Barrage          |
| restrained      | speed 0, attacks at disadvantage, attacked at advantage, Dex saves at disadvantage; value ("escape", DC) lets it spend its action to break free | Entangle, Iron-Hound's net, Snare |
| blinded         | attacked at advantage, attacks at disadvantage               | (none yet)                |
| frightened      | disadvantage while it can see the source; won't step closer  | Red Pact                  |
| slow            | speed reduced by value                                       | Rootbind, Verdant arrow   |
| speed0          | speed 0                                                      | anchor, Lockstep, Snare, Fortress |
| ac              | AC changed by value                                          | shield, Amber Slug, Recoil Step |
| silenced        | can't cast                                                   | Powder Disruption, Mana-Mite Swarm |
| darkness        | can't be seen without Devil's Sight                          | Hellbound                 |
| white_dust      | darkness doesn't hide it                                     | White Dust arrow          |
| next_atk_disadv | its next attack roll has disadvantage                        | Curseweaver, evolutions   |
| next_atk_pen    | its next attack roll loses 1d(value)                         | Covering Fire             |
| next_save_pen   | its next save loses 1d4                                      | Violet Hex shot           |
| tethered        | attacks anyone but the source at disadvantage                | Shackle Strike            |
| hunger          | its next attack roll has disadvantage                        | Hunger of the Armor       |
| crash           | its attacks and concentration saves at disadvantage          | War Drum's crit           |
| unlocated       | attacks the source at disadvantage                           | Silent Volley             |
| veiled          | ranged weapon attacks from beyond 10 ft at disadvantage      | Verdant Veil              |
| cage            | (on the Warden) a dome: spells from outside must beat value  | Mana Cage                 |
| no_heal         | can't regain HP                                              | Prismatic shot            |
| dot             | takes value=(dice, source) at the end of its turn, once       | Vitriolic Sphere          |
| inspired, spotted, spotted_dmg | see heroes/evolution.py                       | evolutions                |

Subclasses add their own names (booming, hexed, shadow_mark, soul_tether,
mage_armor, stoneheart, null_field, fortress, anchored, crystal_sight, recoil).
"""
from __future__ import annotations

from .dice import mod
from .impact import credit
from .movement import ARENA, move, room_behind

SPEED_ZERO = ("paralyzed", "stunned", "restrained", "speed0")


class Effect:
    """A named condition or modifier on a creature.

    until = ("start" | "end", creature): removed at the start/end of that
    creature's turn, after letting `skip` such moments pass. None = until removed.
    """
    __slots__ = ("name", "source", "until", "skip", "value")

    def __init__(self, name, source=None, until=None, value=None, skip=0):
        self.name, self.source, self.until, self.value, self.skip = name, source, until, value, skip


class Conc:
    """A concentration spell: dropping it ends the effects it holds."""

    def __init__(self, name, held=()):
        self.name = name
        self.held = list(held)  # [(creature, Effect)]


class Zone:
    """An area on the line owned by one creature (anchor, nexus, lockstep field...).
    `follows`: it moves with its owner. `difficult`: enemies pay double to walk in it."""

    def __init__(self, name, owner, center, radius, follows=False, difficult=False):
        self.name, self.owner, self.radius = name, owner, radius
        self.follows, self.difficult = follows, difficult
        self._center = center

    def center(self):
        return self.owner.x if self.follows else self._center

    def covers(self, pos):
        return not self.owner.dead and abs(pos - self.center()) <= self.radius

    def on_enemy_turn_start(self, c):
        """An enemy of the owner starts its turn inside."""

    def on_enemy_turn_end(self, c):
        """An enemy of the owner ends its turn inside."""


class Creature:
    style = "melee"        # melee | ranged | caster: how it moves
    caster = False         # casts spells (anti-magic features care)
    creature_type = "humanoid"
    devils_sight = False   # sees through magical darkness
    can_oa = True          # makes opportunity attacks
    heals = False          # can heal itself (Prismatic Round cares)
    max_range = 5          # farthest it can usefully fight from
    watches_damage = False # gets witness_damage() for every hit in the fight
    immovable = False      # can't be pushed

    def __init__(self, name, level, scores, save_profs, pb, hp, ac, speed=30, reach=5):
        self.name, self.level, self.scores, self.save_profs = name, level, scores, set(save_profs)
        self.pb, self.max_hp, self.hp, self.base_ac = pb, hp, hp, ac
        self.base_speed, self.reach = speed, reach
        self.thp = 0
        self.thp_src = None  # who granted the current temporary HP
        self.effects: list[Effect] = []
        self.conc: Conc | None = None
        self.dead = False
        self.side = 0
        self.x = 0
        self.foe: Creature | None = None   # this turn's target
        self.fight = None
        # reset every turn
        self.reaction = True
        self.bonus_used = False
        self.moved = 0
        self.hit_this_turn = False
        self.acted = False       # attacked or cast at an enemy this turn (Pact Nexus)
        self.last_natural = 0    # the d20 of its last attack roll (misfires)
        # stats the runners read
        self.turns = 0
        self.dealt = 0           # damage dealt, with overkill
        self.taken = 0
        self.dealt_hp = 0        # damage that came off enemies' HP (no overkill): Impact's Damage
        self.protect = 0.0       # Impact's other parts; see impact.py
        self.control = 0.0
        self.enable = 0.0
        self.tank = 0.0
        self.aimed = 0           # enemy attack rolls aimed at it
        self.mitigated = 0.0     # damage its own reactions and resistances kept off itself
        self.kills = 0

    # ----- effects ---------------------------------------------------------------
    def add(self, name, source=None, until=None, value=None, skip=0):
        e = Effect(name, source, until, value, skip)
        self.effects.append(e)
        if name in ("paralyzed", "stunned"):
            self.drop_conc()  # incapacitated creatures lose concentration
        return e

    def has(self, name):
        for e in self.effects:
            if e.name == name:
                return True
        return False

    def get(self, name):
        for e in self.effects:
            if e.name == name:
                return e
        return None

    def remove(self, name=None, effect=None):
        self.effects = [e for e in self.effects
                        if not (e is effect or (name is not None and e.name == name))]

    def take(self, name):
        """Remove and return the first effect called `name` (one-shot effects)."""
        e = self.get(name)
        if e:
            self.remove(effect=e)
        return e

    def total(self, name):
        return sum(e.value or 0 for e in self.effects if e.name == name)

    def end_effect(self, e, holder):
        """End effect `e` early (a save or an escape), and let go of it in
        `holder`'s concentration; with nothing left to hold, the spell ends."""
        self.remove(effect=e)
        if holder.conc and any(x is e for _, x in holder.conc.held):
            holder.conc.held = [(h, x) for h, x in holder.conc.held if x is not e]
            if not holder.conc.held:
                holder.conc = None

    def drop_conc(self):
        if self.conc:
            for holder, eff in self.conc.held:
                holder.remove(effect=eff)
            self.conc = None

    def until_my_next_end(self):
        """Effect timing for "until the end of your next turn"."""
        return dict(until=("end", self), skip=1 if self.my_turn() else 0)

    # ----- who is where ------------------------------------------------------------
    def enemies(self):
        return [c for c in self.fight.all if c.side != self.side and not c.dead]

    def allies(self):
        """Living allies, not counting this creature."""
        return [c for c in self.fight.all if c.side == self.side and not c.dead and c is not self]

    def dist_to(self, other):
        return abs(self.x - other.x)

    def dist(self):
        return self.dist_to(self.foe) if self.foe else 999

    def threatened(self):
        """A hostile that isn't incapacitated stands within 5 feet (ranged attacks suffer)."""
        return any(self.dist_to(e) <= 5 and not e.incapacitated() for e in self.enemies())

    def nearest(self, creatures):
        return min(creatures, key=lambda c: (self.dist_to(c), c.hp), default=None)

    def nearest_enemy(self):
        return self.nearest(self.enemies())

    def melee_threat(self):
        """The nearest enemy that wants to fight in melee."""
        return self.nearest([e for e in self.enemies() if e.style == "melee"])

    def pick_target(self):
        """This turn's target. Default: the nearest enemy, the most hurt on a tie."""
        return self.nearest_enemy()

    def stand_in(self, gone):
        """Who I would attack instead if `gone` weren't there (for Tanking; no dice)."""
        return self.nearest([e for e in self.enemies() if e is not gone])

    def my_turn(self):
        return self.fight.current is self

    # ----- footwork for shooters and casters ------------------------------------
    def keep_distance(self):
        """Kite whatever wants to melee me; close on targets beyond my range.
        Called before and again after the action, with whatever movement is left."""
        sp = self.speed_now() - self.moved
        if sp <= 0:
            return
        threat = self.melee_threat()
        if threat:
            gap = self.dist_to(threat)
            if gap <= threat.reach:
                # Step away (eating the opportunity attack) only if it can't
                # follow and still attack on its turn.
                after = gap + min(sp, room_behind(self, threat))
                if threat.speed_now() < after - threat.reach:
                    move(self, False, sp, ref=threat)
                return
            if self.foe and self.dist() < self.max_range:
                move(self, False, min(sp, self.max_range - self.dist()), ref=threat)
                return
        if self.foe and self.dist() > self.max_range:
            move(self, True, min(sp, self.dist() - self.max_range))

    # ----- area effects -------------------------------------------------------------
    def area_targets(self, center_x, radius):
        """Enemies inside an area, or None if it would catch me or an ally."""
        if any(abs(c.x - center_x) <= radius for c in [self] + self.allies()):
            return None
        return [e for e in self.enemies() if abs(e.x - center_x) <= radius]

    def best_area(self, radius, rng, score=len):
        """(targets, center) for the area spot that best scores its targets. Every
        5-foot point in range is tried, so a blast can sit off-centre to catch an
        enemy while missing the ally fighting it."""
        best = None
        for cx in range(max(ARENA[0], self.x - rng), min(ARENA[1], self.x + rng) + 1, 5):
            hit = self.area_targets(cx, radius)
            if hit and (best is None or score(hit) > score(best[0])):
                best = (hit, cx)
        return best

    # ----- derived stats --------------------------------------------------------------
    def ac_bonus(self):
        """Modifiers on top of base armour: effects plus allies' auras."""
        return self.total("ac") + sum(a.aura_ac(self) for a in self.allies()) if self.fight else self.total("ac")

    def ac(self):
        return self.base_ac + self.ac_bonus()

    def incapacitated(self):
        return self.has("paralyzed") or self.has("stunned")

    def speed_now(self):
        if any(e.name in SPEED_ZERO for e in self.effects):
            return 0
        return max(0, self.base_speed - self.total("slow"))

    def mod(self, abil):
        return mod(self.scores[abil])

    def save_bonus(self, abil):
        return self.mod(abil) + (self.pb if abil in self.save_profs else 0)

    def in_difficult(self, pos):
        return any(z.difficult and z.owner.side != self.side and z.covers(pos) for z in self.fight.zones)

    def can_see(self, other):
        """False when `other` stands in magical darkness this creature can't see through."""
        return not (other.has("darkness") and not self.devils_sight and not other.has("white_dust"))

    def est_dpr(self, target):
        """Rough damage per round against `target`; bots use it to judge threats."""
        return 10

    # ----- shared mechanics -------------------------------------------------------------
    def heal(self, amount, src=None):
        """`src`: who heals me, when it isn't me (for its Impact)."""
        if self.has("no_heal") or amount <= 0:
            return 0
        got = min(amount, self.max_hp - self.hp)
        self.hp += got
        if src is not self:
            credit(src, "protect", got)
        return got

    def gain_thp(self, amount, src=None):
        if amount > self.thp:
            self.thp, self.thp_src = amount, src

    # =================================================================================
    # Hooks. Subclasses override these; the defaults do nothing. "adv" hooks return
    # (advantage, disadvantage) and must not spend anything: bots call them to predict.
    # =================================================================================

    # ----- my turn
    def on_initiative(self): pass
    def take_turn(self): pass
    def on_turn_end(self): pass

    # ----- when I attack
    def my_attack_adv(self, tgt, ctx): return False, False
    def on_hit_roll(self, tgt, ctx): pass                  # a hit, before damage; may set ctx.crit
    def bonus_damage(self, tgt, ctx): return []            # extra [Dice] on a hit
    def on_hit(self, tgt, ctx, crit): pass                 # after the hit's damage
    def on_damage_dealt(self, tgt, amount, ctx): pass      # any damage I deal to an enemy
    def on_kill(self, tgt): pass
    def opportunity_attack(self, tgt): pass
    def on_enemy_moved(self, mover): pass

    # ----- when I'm attacked or damaged
    def hit_reaction(self, att, ctx, total, ac): return 0  # my reaction to a hit: AC it adds (shield)
    def blocks_magic_missile(self): return False          # spends shield if it does
    def shield_ready(self): return False
    def lures(self, c): return False                      # c attacks anyone but me at disadvantage
    def reduce_damage(self, dmg, src, ctx): return dmg     # flat reduction, before resistance
    def resists(self, dtype, ctx, nonmagical): return False
    def damage_reaction(self, dmg, src, ctx): return dmg   # my reaction to damage I take

    # ----- saving throws
    def my_save_adv(self, abil, src, ctx): return False, False
    def target_save_adv(self, tgt, abil, ctx): return False, False   # on saves against me
    def save_reroll(self, abil, dc, src, ctx): return False          # True = the reroll succeeded
    def force_fail(self, tgt, ctx): return False                     # turn tgt's success into a failure
    def on_failed_save(self, tgt, ctx): pass                         # tgt failed a save against me

    # ----- for allies (or myself, where noted)
    def aura_ac(self, ally): return 0
    def aura_save_adv(self, ally, abil, src, ctx): return False, False
    def aura_save_bonus(self, ally, abil): return 0
    def ally_attacked(self, att, ally, ctx): return False                # True = impose disadvantage
    def ally_hit_reaction(self, att, ally, ctx, total, ac): return 0     # AC added for the ally
    def ally_save_reroll(self, ally, abil, dc, src, ctx): return False
    def intercept(self, ally, dmg, src, ctx): return False               # True = take the hit instead
    def ally_damage_reaction(self, ally, dmg, src, ctx): return dmg
    def save_from_death(self, tgt): return False                         # tgt may be me or an ally
    def witness_damage(self, tgt, total, src): pass                      # needs watches_damage
