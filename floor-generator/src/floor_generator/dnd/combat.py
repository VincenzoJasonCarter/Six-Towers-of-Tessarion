# ---------------------------------------------------------------
# Combat simulation
# ---------------------------------------------------------------
#
# Runs a 5e-style fight between a loaded character and a generated
# monster on a temporal floor from the core generator.
#
# Initiative follows the design doc's "Normal Battle Effect" rule
# (ACC doubles it, DEC halves it) but, like standard 5e, is rolled
# once at the top of the encounter from each combatant's starting
# zone - the resulting turn order holds for the whole fight, it is
# not re-rolled every round.
#
# Movement speed itself is never modified by zones, per design
# principle #5 - but every move now costs a d20 Athletics check
# (STR modifier, DC 10) to represent Thal'Vireth's temporally
# unstable footing. A failed check wastes the move: the mover stays
# put. This is a simple first pass, not tied to zone type yet.

import math
import random

from .. import generate_temporal_floor
from ..pathfinding import find_path
from ..progression import entrance_spawn_point, exit_spawn_point
from ..zones import DEFAULT_ZONE_TYPES
from .character import load_character
from .dice import roll_d20, roll_dice_string
from .monster import generate_encounter, generate_monster_group

ATHLETICS_DC = 10

# Obstacle density for a combat floor - modest on purpose. Generation
# already guarantees entrance<->exit reachability (see obstacles.py),
# but a fight only has 20x20 m and up to 10 temporal zones (3-5 m
# each) to work with already, so piling on CLI-level wall/block
# counts here would leave little open ground to maneuver in.
COMBAT_N_WALLS = 6
COMBAT_WALL_LENGTH_RANGE = (1, 3)
COMBAT_N_BLOCKS = 2

# A monster group (see monster.py's generate_monster_group() - most
# templates are a single monster, a "swarm" template spawns several)
# is placed clustered around one anchor point instead of stacked on a
# single tile - these are grid-cell offsets from that anchor, used
# round-robin, enough for the largest swarm template. Mirrors
# engine.py's GROUP_SPAWN_OFFSETS (same reasoning, separate copy - see
# that module's docstring on why the interactive and headless paths
# don't share turn-loop-adjacent code).
GROUP_SPAWN_OFFSETS = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


def zone_at(x, y, zones):
    for zone in zones:
        if zone["x"] <= x < zone["x"] + zone["w"] and zone["y"] <= y < zone["y"] + zone["h"]:
            return zone
    return None


def initiative_multiplier(pos, zones, zone_types):
    zone = zone_at(pos[0], pos[1], zones)
    if zone is None:
        return 1.0
    return zone_types[zone["type"]].get("multiplier") or 1.0


def distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def step_toward(pos, target, max_step):
    dx, dy = target[0] - pos[0], target[1] - pos[1]
    d = (dx ** 2 + dy ** 2) ** 0.5
    if d <= max_step or d == 0:
        return target
    return (pos[0] + dx / d * max_step, pos[1] + dy / d * max_step)


def snap_to_grid(pos, size=20):
    """Snap a world position to the center of the 1 m grid cell it
    falls in, clamped to the floor's bounds.

    Movement is still computed continuously (step_toward, Flicker
    Step) - this is the single place that continuous math gets
    rounded back onto the battle grid, so a combatant's position is
    always a clean cell center (n + 0.5), never an arbitrary float
    partway along a movement vector.
    """

    def snap(v):
        cell = max(0, min(size - 1, math.floor(v)))
        return cell + 0.5

    return (snap(pos[0]), snap(pos[1]))


def average_damage(attack):
    n, sides = attack["damage_dice"].lower().split("d")
    return int(n) * (int(sides) + 1) / 2 + attack.get("damage_bonus", 0)


def usable_attacks(combatant, dist):
    """Attacks within range and not out of uses.

    "uses" is a per-encounter cap set on the attack (e.g. a prepared
    spell like Inflict Wounds); None means at-will, like a cantrip or
    a mundane weapon. "uses_remaining" is initialized alongside it by
    load_character()/generate_monster() and ticks down as the fight
    goes on - there's no rest mechanic in the sim, so a used-up attack
    stays unavailable for the rest of the encounter.

    Excludes "hazard" attacks (e.g. Create Bonfire) - those target a
    point on the ground, not the enemy directly, so they don't have an
    attack_bonus to resolve_attack() against and aren't picked through
    this rotation. See hazard_attacks()/cast_hazard() below.
    """
    return [
        a for a in combatant["attacks"]
        if a["kind"] != "hazard" and dist <= a["range"] + 0.01 and (a.get("uses") is None or a["uses_remaining"] > 0)
    ]


def consume_attack_use(attack):
    """Spend one use of a limited attack - casting a prepared spell
    costs its slot whether it hits or misses. No-op for at-will
    attacks (uses is None)."""
    if attack.get("uses") is not None:
        attack["uses_remaining"] -= 1


def resolve_attack(rng, attack, target):
    """Roll to hit and, on a hit, roll damage.

    Returns {"d20", "crit", "hit", "damage"} - "d20" is the raw
    attack-roll die, exposed so a GUI can animate it; "damage" is
    None on a miss.
    """

    d20 = roll_d20(rng)
    crit = d20 == 20
    hit = crit or (d20 != 1 and d20 + attack["attack_bonus"] >= target["ac"])

    damage = None
    if hit:
        damage = roll_dice_string(rng, attack["damage_dice"]) + attack.get("damage_bonus", 0)
        if crit:
            damage += roll_dice_string(rng, attack["damage_dice"])
        damage = max(0, damage)

    return {"d20": d20, "crit": crit, "hit": hit, "damage": damage}


def hazard_attacks(combatant):
    """Attacks that place a zone on the ground instead of targeting
    the enemy directly (e.g. Create Bonfire) - the counterpart to
    usable_attacks() excluding them. Not range-checked against a
    specific target here since a hazard's "range" is how far from the
    caster it can be placed, not a distance to any particular enemy."""
    return [
        a for a in combatant["attacks"]
        if a["kind"] == "hazard" and (a.get("uses") is None or a["uses_remaining"] > 0)
    ]


def cast_hazard(rng, hazards, owner, spell, target_pos, combatants, log):
    """Place a hazard spell's zone (an area_size x area_size square,
    centered on target_pos's grid cell), replacing any zone the same
    owner is already concentrating on - 5e only allows concentrating
    on one spell at a time, and Create Bonfire requires concentration.
    """

    consume_attack_use(spell)
    cell = snap_to_grid(target_pos)
    cx, cy = int(cell[0]), int(cell[1])
    size = spell.get("area_size", 1)
    half = size // 2

    hazards[:] = [h for h in hazards if h["owner"] != owner]
    hazard = {
        "name": spell["name"],
        "owner": owner,
        "x": cx - half,
        "y": cy - half,
        "w": size,
        "h": size,
        "damage_dice": spell["damage_dice"],
        "damage_type": spell["damage_type"],
        "save_ability": spell["save_ability"],
        "save_dc": combatants[owner].get("spell_save_dc", 10),
        "rounds_left": spell["duration_rounds"],
    }
    hazards.append(hazard)
    log.append(f"{owner} conjures a {size}x{size} m {spell['name']} centered at ({cx + 0.5:.1f}, {cy + 0.5:.1f}).")
    return hazard


def resolve_hazard_tick(rng, hazard, victim):
    """Saving throw against an active hazard zone - full rolled
    damage on a failed save, half (rounded down) on a success. Mirrors
    resolve_attack()'s shape, but for a save instead of an attack
    roll."""

    d20 = roll_d20(rng)
    modifier = victim["modifiers"][hazard["save_ability"]]
    total = d20 + modifier
    success = total >= hazard["save_dc"]
    damage = roll_dice_string(rng, hazard["damage_dice"])
    if success:
        damage //= 2
    return {"d20": d20, "modifier": modifier, "total": total, "success": success, "damage": damage}


def apply_hazard_ticks(rng, hazards, positions, combatants, log, only=None):
    """Resolve a save for every living creature standing anywhere
    inside an active hazard's area.

    The spell's two real triggers - "in the area when you cast it" and
    "ends its turn there" - collapse into this one positional check.
    Pass `only` (a combatant name) right after that creature's turn
    ends; omit it to sweep every combatant at once, used the instant a
    hazard is placed.

    Returns the list of ticks applied (each a resolve_hazard_tick()
    result plus "name"/"hazard_name"), so a GUI can animate the d20s
    the same way it does for attacks and Athletics checks.
    """

    ticks = []
    names = [only] if only else list(positions.keys())
    for name in names:
        victim = combatants[name]
        if victim["hp"] <= 0:
            continue
        cx, cy = math.floor(positions[name][0]), math.floor(positions[name][1])
        for hz in hazards:
            if not (hz["x"] <= cx < hz["x"] + hz["w"] and hz["y"] <= cy < hz["y"] + hz["h"]):
                continue
            result = resolve_hazard_tick(rng, hz, victim)
            victim["hp"] = max(0, victim["hp"] - result["damage"])
            outcome = "succeeds" if result["success"] else "fails"
            log.append(
                f"{name} {outcome} a {hz['save_ability']} save against {hz['name']}: "
                f"{result['d20']}{result['modifier']:+d}={result['total']} vs DC {hz['save_dc']}, "
                f"takes {result['damage']} {hz['damage_type']} damage. {name} HP: {victim['hp']}/{victim['max_hp']}"
            )
            if victim["hp"] <= 0:
                log.append(f"{name} falls!")
            ticks.append({
                "name": name, "hazard_name": hz["name"], "owner": hz["owner"],
                "damage_type": hz["damage_type"], **result,
            })
    return ticks


def make_echo(revenant, echo_name, echo_hp, attack):
    """A Revenant of Yesterday's Echo (see monsters/bosses/
    revenant_of_yesterday.yaml) - a real combatant dict, built from the
    Revenant's own scores/modifiers/ac so it fights like a diminished
    copy of it, holding a single fresh copy of whichever attack it's
    meant to repeat. speed 0 and empty traits mean it never moves and
    can't recurse into spawning its own Echoes or using Flicker Step.
    Module-level (not a simulate_combat-local closure) so engine.py's
    interactive CombatEngine can build one the same way.
    """
    attack_copy = dict(attack)
    attack_copy["uses_remaining"] = attack_copy.get("uses")
    return {
        "name": echo_name, "type": "Echo", "challenge_rating": 0,
        "scores": revenant["scores"], "modifiers": revenant["modifiers"],
        "hp": echo_hp, "max_hp": echo_hp, "ac": revenant["ac"], "speed": 0,
        "proficiency_bonus": revenant["proficiency_bonus"],
        "traits": [], "attacks": [attack_copy], "is_echo": True,
    }


def athletics_check(rng, mover, dc=ATHLETICS_DC):
    """d20 + STR modifier vs dc. Rolled before every walking move."""

    d20 = roll_d20(rng)
    modifier = mover["modifiers"]["STR"]
    total = d20 + modifier
    return {"d20": d20, "modifier": modifier, "total": total, "dc": dc, "success": total >= dc}


def _on_throne_steps(cell, throne_steps):
    """Whether a grid cell's center falls within a boss floor's dais
    (see throne_room.py) - the outermost step's footprint covers every
    step inside it too, since they're nested squares, so checking just
    that one entry is enough to mean "anywhere on the stairs"."""
    if not throne_steps:
        return False
    x0, y0, x1, y1 = throne_steps[0]
    cx, cy = cell[0] + 0.5, cell[1] + 0.5
    return x0 <= cx <= x1 and y0 <= cy <= y1


def attempt_move(rng, mover, mover_name, pos, target, max_step, log, size, obstacles, throne_steps=None):
    """Roll an Athletics check, then advance along an obstacle-aware
    route toward target, spending up to max_step meters of movement.

    Walls and blocks (see obstacles.py) remove edges/cells from the
    pathfinding grid (pathfinding.find_path), so a move routes around
    them instead of cutting straight through - obstacle generation
    guarantees the entrance and exit are always mutually reachable,
    but a monster/player can still end up boxed away from each other
    mid-fight depending on where they're standing when a route is
    needed, in which case the move just fails to make progress, same
    as a failed Athletics check.

    throne_steps (see throne_room.py), if given, is a boss floor's
    dais - stepping onto it costs double the usual distance out of
    max_step, i.e. movement speed is effectively halved while climbing
    it, same as difficult terrain. Unlike walls/blocks this never
    blocks a route, only slows it.

    Returns (new_position, check, waypoints) - new_position is the
    mover's (possibly unchanged) position as a list; check is the raw
    athletics_check() result, exposed so a GUI can animate the d20;
    waypoints is the actual sequence of cell centers stepped through
    to get there (starting with the pre-move position, so it always
    has at least one point) - a GUI can glide a token through each of
    these in turn instead of cutting a straight line from the old
    position to the new one, which would visibly clip through
    whatever obstacle the route just detoured around.
    """

    check = athletics_check(rng, mover)
    log.append(
        f"{mover_name} rolls an Athletics check to move: {check['d20']}{check['modifier']:+d}="
        f"{check['total']} vs DC {check['dc']} -> {'success' if check['success'] else 'fails to find footing'}"
    )

    if not check["success"]:
        return list(pos), check, [list(pos)]

    start_cell = (math.floor(pos[0]), math.floor(pos[1]))
    goal_cell = (math.floor(target[0]), math.floor(target[1]))
    path = find_path(start_cell, goal_cell, size, obstacles)

    if path is None:
        log.append(f"{mover_name} finds no route through - the way is blocked.")
        return list(pos), check, [list(pos)]

    # Cardinal-only pathfinding (see pathfinding.py) means `path` is
    # one cell per meter, even along a straight unobstructed run - so
    # collapse consecutive steps in the same direction into a single
    # waypoint instead of recording every cell crossed. Otherwise a
    # plain 8 m walk in a straight line would hand the animation 8
    # separate segments to ease in and out of individually, one per
    # meter, which reads as a stutter rather than a walk - a new
    # waypoint should only appear where the route actually turns.
    waypoints = [list(pos)]
    new_pos = list(pos)
    remaining = max_step
    prev_cell = start_cell
    direction = None
    climbed_stairs = False
    for cell in path:
        step_target = (cell[0] + 0.5, cell[1] + 0.5)
        step_dist = distance(new_pos, step_target)
        on_stairs = _on_throne_steps(cell, throne_steps)
        cost = step_dist * 2 if on_stairs else step_dist
        if cost > remaining + 0.01:
            break
        new_pos = list(step_target)
        remaining -= cost
        climbed_stairs = climbed_stairs or on_stairs
        step_direction = (cell[0] - prev_cell[0], cell[1] - prev_cell[1])
        if step_direction == direction:
            waypoints[-1] = list(new_pos)
        else:
            waypoints.append(list(new_pos))
            direction = step_direction
        prev_cell = cell

    if new_pos == list(pos):
        log.append(f"{mover_name} can't find a way past the obstacles blocking the route.")
    elif climbed_stairs:
        log.append(f"{mover_name} climbs the throne steps, slowed, to ({new_pos[0]:.1f}, {new_pos[1]:.1f}).")
    else:
        log.append(f"{mover_name} moves to ({new_pos[0]:.1f}, {new_pos[1]:.1f}).")

    return new_pos, check, waypoints


def simulate_combat(
    character_path=None, character=None, seed=42, floor_seed=None, max_rounds=20,
    verbose=True, monster_difficulty=None, monster_template_path=None,
):
    """character, if given, is used as-is instead of loading fresh from
    character_path - a TowerRun (see run.py) passes the same dict into
    every floor's fight so HP and spent uses carry over between them.

    monster_difficulty (0.0-1.0), if given, scales every monster's
    stats (see monster.py's _difficulty_scaling) - see run.py's
    per-floor difficulty curve.

    monster_template_path, if given, forces that specific template
    instead of a mixed-role encounter (see monster.py's
    generate_encounter()) - used for a boss floor (see run.py's
    BOSS_TEMPLATES), which always fights the same named boss rather
    than a rolled-up squad. Without it, the fight is a composed
    encounter: a frontline anchor plus a difficulty-scaled chance of
    backline/swarm support, so most floors aren't a single monster
    alone - the player always targets whichever's nearest."""

    rng = random.Random(seed)

    # A boss floor (monster_template_path forces a specific boss - see
    # run.py's BOSS_TEMPLATES) gets a throne room instead of the usual
    # far-quadrant-from-the-entrance spawn (see __init__.py's
    # generate_temporal_floor(throne_room=...)) - and no extra random
    # wall/block scatter, so the room actually reads as a room instead
    # of getting buried in unrelated obstacles.
    is_boss_floor = monster_template_path is not None
    floor = generate_temporal_floor(
        seed=floor_seed if floor_seed is not None else seed,
        n_zones=10,
        zone_size_range=(3, 5),
        n_wall_segments=0 if is_boss_floor else COMBAT_N_WALLS,
        wall_length_range=COMBAT_WALL_LENGTH_RANGE,
        n_obstacle_blocks=0 if is_boss_floor else COMBAT_N_BLOCKS,
        throne_room=is_boss_floor,
        show=False,
    )
    zones = floor["zones"]
    zone_types = DEFAULT_ZONE_TYPES
    obstacles = floor["obstacles"]

    character = character if character is not None else load_character(character_path)
    if monster_template_path is not None:
        monsters = generate_monster_group(rng, difficulty=monster_difficulty, template_path=monster_template_path)
    else:
        monsters = generate_encounter(rng, difficulty=monster_difficulty)
    monster_names = [m["name"] for m in monsters]

    entrance = floor["entrance_door"]
    exit_ = floor["exit_ladder"]
    ex, ey = entrance_spawn_point(entrance)
    mx, my = exit_spawn_point(exit_)

    positions = {character["name"]: [ex, ey]}
    for i, name in enumerate(monster_names):
        dx, dy = GROUP_SPAWN_OFFSETS[i % len(GROUP_SPAWN_OFFSETS)]
        positions[name] = [
            min(max(mx + dx, 0.5), floor["size"] - 0.5),
            min(max(my + dy, 0.5), floor["size"] - 0.5),
        ]

    combatants = {character["name"]: character}
    combatants.update({m["name"]: m for m in monsters})
    flicker_available = {name: True for name in monster_names}
    hazards = []
    tether = None  # {"target", "rounds_left"} or None - mirrors engine.py's Soul Tether

    # The Chronophage's Time Debt/"You Are Already Late" (see
    # monsters/bosses/chronophage.yaml) - player-only state, since both
    # traits only ever apply to the player ("whenever a PLAYER is hit").
    # skip_move/skip_bonus are consumed the next time it's actually the
    # player's turn (see the "used_skip_*" locals inside the loop below).
    time_debt = 0
    late_mark = None  # {"rounds_left", "expiry_damage_dice"} or None
    skip_move = False
    skip_bonus = False

    # The Revenant of Yesterday's Echo/Reversal (see
    # monsters/bosses/revenant_of_yesterday.yaml). revenant_name is the
    # one monster (never an Echo - see make_echo) carrying the
    # "revenant_echo" tag; None for every other fight, in which case
    # nothing below this point ever fires. Echoes are real combatants
    # (added to combatants/positions/order, so they act, can be hit,
    # and render for free) but deliberately left out of monster_names,
    # so the fight's win condition stays "defeat the Revenant itself",
    # not "and every Echo it ever left behind" - see side_defeated()
    # and the win-check after the round loop.
    revenant_name = next(
        (n for n in monster_names if any(t.get("mechanic") == "revenant_echo" for t in combatants[n]["traits"])),
        None,
    )
    revenant_attack_this_round = None
    echo_order = []  # spawn order, oldest first - see Reversal below
    echo_count = 0
    reversal_used = False

    def nearest_alive_monster(pos):
        alive_names = [n for n in monster_names if combatants[n]["hp"] > 0]
        if not alive_names:
            return None
        return min(alive_names, key=lambda n: distance(pos, positions[n]))

    def side_defeated(other_name):
        """Whichever side other_name belongs to - the player, or the
        whole monster group - has nothing left standing. Ending a
        round early on "my target died" only makes sense once that
        happens on their side; one swarm member falling shouldn't cut
        the round short while its packmates are still up.

        The Revenant of Yesterday overrides this to just its own HP
        (see revenant_name above) - its Echoes don't gate victory."""
        if other_name == character["name"]:
            return not alive(character)
        if revenant_name is not None:
            return not alive(combatants[revenant_name])
        return not any(alive(combatants[n]) for n in monster_names)

    log = []
    round_num = 0

    def alive(c):
        return c["hp"] > 0

    def refresh_tether(attacker_name, victim_name):
        """Mark/refresh victim_name as attacker_name's Soul Tether
        target - called whenever attacker_name deals it damage. A
        no-op for a combatant without the feature (only Pijo has it)."""
        nonlocal tether
        cfg = combatants[attacker_name].get("soul_tether")
        if not cfg or not alive(combatants[victim_name]):
            return
        tether = {"target": victim_name, "rounds_left": cfg["duration_rounds"]}

    def note_hazard_tether_refresh(ticks):
        for t in ticks:
            if t["damage"] > 0:
                refresh_tether(t["owner"], t["name"])

    def try_soul_tether(cname, other_name, skip_bonus=False):
        """Soul Tether's bonus action - independent of cname's main
        action this turn, so it's checked alongside every branch below
        rather than gating on which one was taken. skip_bonus is set
        when the Chronophage's Time Debt Repayment cost cname (always
        the player - see monsters/bosses/chronophage.yaml) this turn's
        bonus action."""
        nonlocal tether
        if skip_bonus:
            return
        cfg = combatants[cname].get("soul_tether")
        if not cfg or tether is None or tether["target"] != other_name:
            return
        if cfg.get("uses") is not None and cfg["uses_remaining"] <= 0:
            return
        c, target = combatants[cname], combatants[other_name]
        if not alive(target):
            return
        dmg = roll_dice_string(rng, cfg["damage_dice"])
        target["hp"] = max(0, target["hp"] - dmg)
        healed = min(dmg, c["max_hp"] - c["hp"])
        c["hp"] += healed
        if cfg.get("uses") is not None:
            cfg["uses_remaining"] -= 1
        log.append(
            f"{cname} feeds on the tether binding {other_name} for {dmg} necrotic damage and regains "
            f"{healed} HP. {other_name} HP: {target['hp']}/{target['max_hp']}, {cname} HP: {c['hp']}/{c['max_hp']}"
        )
        if target["hp"] <= 0:
            log.append(f"{other_name} falls!")
            tether = None

    # Initiative: rolled once, from each combatant's starting zone, then fixed.
    order = []
    for cname, c in combatants.items():
        pos = positions[cname]
        multiplier = initiative_multiplier(pos, zones, zone_types)
        raw = roll_d20(rng) + c["modifiers"]["DEX"]
        initiative = raw * multiplier
        zone = zone_at(pos[0], pos[1], zones)
        note = f" [{zone['type']} zone, x{multiplier:g} initiative]" if zone else ""
        log.append(f"{cname} rolls initiative: {raw:g} -> {initiative:g}{note}")
        order.append((initiative, cname))
    order.sort(key=lambda t: t[0], reverse=True)
    order = [cname for _, cname in order]

    while alive(character) and any(alive(combatants[n]) for n in monster_names) and round_num < max_rounds:
        round_num += 1
        log.append(f"--- Round {round_num} ---")

        for hz in hazards:
            hz["rounds_left"] -= 1
        for hz in hazards:
            if hz["rounds_left"] <= 0:
                log.append(f"{hz['name']} (cast by {hz['owner']}) burns out.")
        hazards[:] = [hz for hz in hazards if hz["rounds_left"] > 0]

        if tether is not None:
            tether["rounds_left"] -= 1
            if tether["rounds_left"] <= 0:
                log.append(f"The tether binding {tether['target']} fades.")
                tether = None

        if late_mark is not None:
            late_mark["rounds_left"] -= 1
            if late_mark["rounds_left"] <= 0:
                dmg = roll_dice_string(rng, late_mark["expiry_damage_dice"])
                character["hp"] = max(0, character["hp"] - dmg)
                log.append(
                    f"{character['name']}'s time runs out - Already Late resolves for {dmg} psychic damage. "
                    f"HP: {character['hp']}/{character['max_hp']}"
                )
                late_mark = None
            else:
                log.append(f"{character['name']} is Already Late ({late_mark['rounds_left']}).")

        for cname in order:
            c = combatants[cname]
            if not alive(c):
                continue

            if cname == character["name"]:
                other_name = nearest_alive_monster(positions[cname])
                if other_name is None:
                    break  # every monster is down - nothing left for the player to do this round
            else:
                other_name = character["name"]
            other = combatants[other_name]
            if not alive(other):
                break

            pos = positions[cname]
            dist = distance(pos, positions[other_name])

            # Time Debt Repayment/marking (see monsters/bosses/chronophage.yaml) -
            # a free effect on the Chronophage's own turn, same slot Flicker Step
            # occupies on a different monster. Repayment fires the instant the
            # threshold is met rather than being left to chance, so a player
            # watching their own Time Debt stack can reliably predict it.
            if cname == character["name"]:
                used_skip_move, used_skip_bonus = skip_move, skip_bonus
                skip_move = skip_bonus = False
            else:
                used_skip_move = used_skip_bonus = False

                time_debt_trait = next((t for t in c["traits"] if t.get("mechanic") == "time_debt"), None)
                if time_debt_trait and time_debt >= time_debt_trait["debt_threshold"]:
                    if rng.choice((True, False)):
                        skip_move = True
                        skip_bonus = True
                        log.append(
                            f"{character['name']}'s Time Debt comes due - they lose their next move and bonus action!"
                        )
                    else:
                        dmg = roll_dice_string(rng, time_debt_trait["repayment_damage_dice"])
                        character["hp"] = max(0, character["hp"] - dmg)
                        log.append(
                            f"{character['name']}'s Time Debt comes due for {dmg} psychic damage. "
                            f"HP: {character['hp']}/{character['max_hp']}"
                        )
                    time_debt = 0
                    if not alive(character):
                        break

                late_mark_trait = next((t for t in c["traits"] if t.get("mechanic") == "late_mark"), None)
                if late_mark_trait and late_mark is None and round_num % late_mark_trait["mark_interval_rounds"] == 0:
                    late_mark = {
                        "rounds_left": late_mark_trait["countdown_start"],
                        "expiry_damage_dice": late_mark_trait["expiry_damage_dice"],
                    }
                    log.append(
                        f"{cname} marks {character['name']}: You Are Already Late! ({late_mark['rounds_left']})"
                    )

            # Flicker Step: only the monster has it, only worth using to close a gap
            # its normal speed can't cover this round. It's a magical displacement,
            # not a physical move, so it skips the Athletics check.
            #
            # It starts pre-charged, and the party spawns far across the
            # room specifically so the fight opens with a gap to close
            # (see place_exit_ladder in progression.py) - without this
            # round-1 gate a flicker-capable monster teleports 9m plus
            # walks another 9m on its very first turn, virtually every
            # time, before the player has done anything.
            if cname != character["name"]:
                # Matched by "mechanic" (a tag, not the display name) so
                # a monster can reflavor this same dash under its own
                # trait name (e.g. the corrupted High Priestess's "Time
                # Skip" - see monsters/bosses/) without the engine
                # needing to know every alias.
                flicker_trait = next((t for t in c["traits"] if t.get("mechanic") == "flicker_step"), None)
                flicker_ready = round_num > 1
                if flicker_trait and flicker_ready and not flicker_available[cname]:
                    if roll_dice_string(rng, "1d6") >= 5:
                        flicker_available[cname] = True
                        log.append(f"{cname}'s {flicker_trait['name']} recharges.")
                if flicker_trait and flicker_ready and flicker_available[cname] and dist > c["speed"] + 0.01:
                    new_pos = snap_to_grid(step_toward(pos, positions[other_name], min(dist, flicker_trait["range"])))
                    positions[cname] = list(new_pos)
                    pos = positions[cname]
                    dist = distance(pos, positions[other_name])
                    flicker_available[cname] = False
                    log.append(f"{cname} flickers through a torn instant, reappearing at ({pos[0]:.1f}, {pos[1]:.1f}).")

            # Hazard spells (e.g. Create Bonfire) target a point on the
            # ground, not the enemy directly, so they sit outside the
            # normal attack rotation usable_attacks() drives. Simple
            # heuristic for this headless auto-battler: drop one on the
            # enemy's current tile the moment it's in range and cname
            # isn't already concentrating on one - spending the whole
            # turn on it, like a real cast would - then fall back to
            # normal attacks for the rest of the fight while it ticks.
            #
            # Checked against "is cname concentrating on this spell at
            # all", not "is it still covering the enemy's current
            # tile" - a mobile enemy (Flicker Step, kiting) drifts out
            # of a 5x5 zone within a turn or two anyway, and re-centering
            # it on their new tile every single turn would burn the
            # whole fight on casting instead of ever landing a weapon
            # or Inflict Wounds hit.
            cast_this_turn = False
            for spell in hazard_attacks(c):
                if dist > spell["range"] + 0.01:
                    continue
                already_concentrating = any(h["owner"] == cname and h["name"] == spell["name"] for h in hazards)
                if already_concentrating:
                    continue
                cast_hazard(rng, hazards, cname, spell, positions[other_name], combatants, log)
                cast_this_turn = True
                break

            if cast_this_turn:
                note_hazard_tether_refresh(apply_hazard_ticks(rng, hazards, positions, combatants, log, only=cname))
                try_soul_tether(cname, other_name, skip_bonus=used_skip_bonus)
                if side_defeated(other_name):
                    break
                continue

            usable = usable_attacks(c, dist)

            if not usable:
                if used_skip_move:
                    log.append(f"{character['name']} is too far behind on their own timeline to move this turn.")
                elif c.get("is_echo"):
                    pass  # an Echo repeats a past moment in place - it never moves (see make_echo)
                else:
                    positions[cname], _, _ = attempt_move(
                        rng, c, cname, pos, positions[other_name], c["speed"], log, floor["size"], obstacles,
                        throne_steps=floor["throne_steps"],
                    )
                    dist = distance(positions[cname], positions[other_name])
                    usable = usable_attacks(c, dist)

            if not usable:
                log.append(f"{cname} can't yet reach {other_name}.")
                note_hazard_tether_refresh(apply_hazard_ticks(rng, hazards, positions, combatants, log, only=cname))
                try_soul_tether(cname, other_name, skip_bonus=used_skip_bonus)
                continue

            attack = max(usable, key=average_damage)
            consume_attack_use(attack)

            # The Revenant of Yesterday's Echo (see the module docstring
            # above and monsters/bosses/revenant_of_yesterday.yaml) -
            # whichever attack it actually swings with this round gets
            # spawned as an Echo at end-of-round, hit or miss.
            if cname == revenant_name:
                revenant_attack_this_round = attack

            result = resolve_attack(rng, attack, other)

            if not result["hit"]:
                log.append(f"{cname} attacks {other_name} with {attack['name']} and misses.")
                note_hazard_tether_refresh(apply_hazard_ticks(rng, hazards, positions, combatants, log, only=cname))
                try_soul_tether(cname, other_name, skip_bonus=used_skip_bonus)
                continue

            damage, crit = result["damage"], result["crit"]
            other["hp"] = max(0, other["hp"] - damage)
            refresh_tether(cname, other_name)
            crit_note = " (critical hit!)" if crit else ""
            log.append(
                f"{cname} hits {other_name} with {attack['name']} for {damage} {attack['damage_type']} "
                f"damage{crit_note}. {other_name} HP: {other['hp']}/{other['max_hp']}"
            )

            # Time Debt/"You Are Already Late" hooks (see
            # monsters/bosses/chronophage.yaml) - only meaningful in
            # the direction the boss's traits actually apply.
            if other_name == character["name"]:
                if any(t.get("mechanic") == "time_debt" for t in c["traits"]):
                    time_debt += 1
                    log.append(f"{character['name']} gains 1 Time Debt ({time_debt}).")
            elif cname == character["name"] and late_mark is not None:
                if any(t.get("mechanic") == "late_mark" for t in other["traits"]):
                    late_mark = None
                    log.append(f"The mark passes back to {other_name} - Already Late clears.")

            # Reversal (see monsters/bosses/revenant_of_yesterday.yaml) -
            # fires "the instant" the Revenant drops to half HP, not on
            # its own next turn, so this checks right where its HP just
            # changed rather than waiting for cname == revenant_name.
            if other_name == revenant_name and not reversal_used and other["hp"] <= other["max_hp"] // 2:
                oldest_echo = next((e for e in echo_order if alive(combatants[e])), None)
                if oldest_echo is not None:
                    positions[revenant_name], positions[oldest_echo] = positions[oldest_echo], positions[revenant_name]
                    reversal_used = True
                    log.append(f"{revenant_name} performs Reversal, trading places with {oldest_echo}!")

            note_hazard_tether_refresh(apply_hazard_ticks(rng, hazards, positions, combatants, log, only=cname))
            try_soul_tether(cname, other_name, skip_bonus=used_skip_bonus)

            if other["hp"] <= 0:
                log.append(f"{other_name} falls!")
                if side_defeated(other_name):
                    break

        # End of round: the Revenant of Yesterday leaves an Echo behind
        # at its current position, carrying whichever attack it swung
        # this round (see the "revenant_attack_this_round" capture
        # above) - nothing happens if it never got an attack in, or
        # isn't this boss, or has already fallen.
        if revenant_name is not None and revenant_attack_this_round is not None and alive(combatants[revenant_name]):
            echo_count += 1
            echo_name = f"{revenant_name} Echo #{echo_count}"
            echo_trait = next(t for t in combatants[revenant_name]["traits"] if t.get("mechanic") == "revenant_echo")
            combatants[echo_name] = make_echo(
                combatants[revenant_name], echo_name, echo_trait["echo_hp"], revenant_attack_this_round,
            )
            positions[echo_name] = list(positions[revenant_name])
            order.append(echo_name)
            echo_order.append(echo_name)
            log.append(f"{echo_name} forms where {revenant_name} last stood, still swinging {revenant_attack_this_round['name']}.")
        revenant_attack_this_round = None

    # The Revenant of Yesterday's win condition is just its own HP (see
    # revenant_name/side_defeated above) - its Echoes don't count here
    # either, same reasoning.
    if revenant_name is not None:
        monsters_alive = [revenant_name] if alive(combatants[revenant_name]) else []
    else:
        monsters_alive = [n for n in monster_names if alive(combatants[n])]

    if alive(character) and not monsters_alive:
        winner = character["name"]
    elif monsters_alive and not alive(character):
        winner = monsters_alive[0]  # any name will do to mark "the monsters won" - see engine.py's _check_over()
    else:
        winner = None

    log.append(f"--- Combat ends after {round_num} round(s). Winner: {winner or 'draw (round limit reached)'} ---")

    if verbose:
        for line in log:
            print(line)

    return {
        "floor": floor,
        "character": character,
        "monsters": monsters,
        "log": log,
        "winner": winner,
        "rounds": round_num,
        "hazards": hazards,
        "tether": tether,
    }
