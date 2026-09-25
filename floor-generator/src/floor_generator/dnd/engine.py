# ---------------------------------------------------------------
# Turn-by-turn combat engine
# ---------------------------------------------------------------
#
# Same rules as combat.simulate_combat (same dice, zone, and attack
# helpers - nothing about how a roll or a zone multiplier works is
# duplicated here), but exposed as a stateful step-by-step engine so
# a GUI can drive the player's turn interactively while the monster(s)
# still act on their own. simulate_combat stays as the headless/CLI
# path; this is the interactive one.
#
# It's the player against one or more monsters - most fights are
# still 1-on-1, but a "swarm" template (see monster.py's
# generate_monster_group()) spawns several independent monsters at
# once. The player picks which one their attacks/casts target (see
# set_target()); everything that isn't targeted (movement, an AoE
# like Create Bonfire, Soul Tether) already works against however many
# monsters are on the field, since it iterates positions/combatants
# generically rather than assuming exactly one name.
#
# Initiative is rolled once at the start of the fight (from each
# combatant's starting zone) and then fixed for its duration, same as
# combat.py. Every walking move costs an Athletics check - see
# attempt_move() in combat.py.

import random

from .. import generate_temporal_floor
from ..progression import entrance_spawn_point, exit_spawn_point
from ..zones import DEFAULT_ZONE_TYPES
from .character import load_character
from .combat import (
    COMBAT_N_BLOCKS,
    COMBAT_N_WALLS,
    COMBAT_WALL_LENGTH_RANGE,
    apply_hazard_ticks,
    attempt_move,
    average_damage,
    cast_hazard,
    consume_attack_use,
    distance,
    hazard_attacks,
    initiative_multiplier,
    make_echo,
    resolve_attack,
    snap_to_grid,
    step_toward,
    usable_attacks,
    zone_at,
)
from .dice import roll_d20, roll_dice_string
from .monster import generate_encounter, generate_monster_group

# A monster group spawns clustered around one anchor point instead of
# stacked on a single tile - these are grid-cell offsets from that
# anchor, used round-robin, enough for the largest swarm template.
GROUP_SPAWN_OFFSETS = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


class CombatEngine:

    def __init__(
        self, character_path=None, character=None, seed=42, floor_seed=None, max_rounds=50,
        monster_difficulty=None, monster_template_path=None, is_boss=False,
    ):
        """character, if given, is used as-is instead of loading fresh
        from character_path - a TowerRun (see run.py) passes the same
        dict into every floor's fight so HP and spent uses carry over
        between them. monster_difficulty (0.0-1.0) scales every
        monster's stats - see run.py's per-floor difficulty curve.

        monster_template_path, if given, forces that specific template
        instead of a mixed-role encounter (see monster.py's
        generate_encounter()) - used for a boss floor (see run.py's
        BOSS_TEMPLATES); otherwise the fight is a composed encounter
        (frontline anchor plus difficulty-scaled backline/swarm
        support). is_boss is display-only (see gui.py's floor
        indicator)."""

        self.rng = random.Random(seed)
        self.max_rounds = max_rounds
        self.is_boss = is_boss

        # A boss floor (monster_template_path forces a specific boss -
        # see run.py's BOSS_TEMPLATES) gets a throne room instead of
        # the usual far-quadrant-from-the-entrance spawn (see
        # __init__.py's generate_temporal_floor(throne_room=...)) -
        # and no extra random wall/block scatter, so the room actually
        # reads as a room instead of getting buried in unrelated
        # obstacles. Keyed off monster_template_path, not is_boss - the
        # latter is caller-supplied and display-only (see gui.py's
        # floor indicator), this needs to always match reality.
        is_boss_floor = monster_template_path is not None
        self.floor = generate_temporal_floor(
            seed=floor_seed if floor_seed is not None else seed,
            n_zones=10,
            zone_size_range=(3, 5),
            n_wall_segments=0 if is_boss_floor else COMBAT_N_WALLS,
            wall_length_range=COMBAT_WALL_LENGTH_RANGE,
            n_obstacle_blocks=0 if is_boss_floor else COMBAT_N_BLOCKS,
            throne_room=is_boss_floor,
            show=False,
        )
        self.zones = self.floor["zones"]
        self.zone_types = DEFAULT_ZONE_TYPES
        self.obstacles = self.floor["obstacles"]

        self.character = character if character is not None else load_character(character_path)
        if monster_template_path is not None:
            self.monsters = generate_monster_group(
                self.rng, difficulty=monster_difficulty, template_path=monster_template_path,
            )
        else:
            self.monsters = generate_encounter(self.rng, difficulty=monster_difficulty)
        self.monster_names = [m["name"] for m in self.monsters]

        entrance = self.floor["entrance_door"]
        exit_ = self.floor["exit_ladder"]
        ex, ey = entrance_spawn_point(entrance)
        mx, my = exit_spawn_point(exit_)
        self.positions = {self.character["name"]: [ex, ey]}
        for i, name in enumerate(self.monster_names):
            dx, dy = GROUP_SPAWN_OFFSETS[i % len(GROUP_SPAWN_OFFSETS)]
            size = self.floor["size"]
            self.positions[name] = [
                min(max(mx + dx, 0.5), size - 0.5),
                min(max(my + dy, 0.5), size - 0.5),
            ]

        self.combatants = {self.character["name"]: self.character}
        self.combatants.update({m["name"]: m for m in self.monsters})
        self.flicker_available = {name: True for name in self.monster_names}
        self.hazards = []

        # The Chronophage's Time Debt/"You Are Already Late" (see
        # monsters/bosses/chronophage.yaml) - player-only state, mirrors
        # combat.py's simulate_combat locals of the same name.
        self.time_debt = 0
        self.late_mark = None  # {"rounds_left", "expiry_damage_dice"} or None
        self.skip_move = False
        self.skip_bonus = False

        # The Revenant of Yesterday's Echo/Reversal (see
        # monsters/bosses/revenant_of_yesterday.yaml) - mirrors
        # combat.py's simulate_combat locals of the same name. Unlike
        # the headless sim, Echoes ARE added to self.monster_names (see
        # _begin_round) so the player can click one as a target - see
        # module docstring and _boss_defeated() for how the win
        # condition still stays "defeat the Revenant itself" despite that.
        self.revenant_name = next(
            (n for n in self.monster_names if any(t.get("mechanic") == "revenant_echo" for t in self.combatants[n]["traits"])),
            None,
        )
        self.revenant_attack_this_round = None
        self.echo_order = []  # spawn order, oldest first - see Reversal
        self.echo_count = 0
        self.reversal_used = False

        # Which monster the player's attacks/casts-at-a-creature
        # target - set explicitly via set_target() (a GUI click on a
        # token), or left None to just target whichever's first alive
        # in self.monster_names (fine for the common 1-monster case).
        self.target_name = None

        # Soul Tether (see character.py/pijo.yaml) - {"target", "rounds_left"}
        # or None. Refreshed whenever the player damages the tethered
        # target; consumed via the bonus action in player_use_soul_tether().
        self.tether = None
        self.tether_used_this_turn = False

        self.round_num = 0
        self.turn_index = 0
        self.log = []
        self.winner = None
        self.game_over = False
        self.moved_this_turn = False
        self.acted_this_turn = False

        # Every d20/d6 rolled during the most recent player-triggered call
        # (player_move, player_attack, end_player_turn - which may also run
        # the monster's turn), as {"label", "sides", "result"} dicts, so a
        # GUI can animate each roll instead of just seeing the log update.
        self.last_rolls = []
        self.initiative_rolls = []

        # Every attack resolved during the most recent player-triggered
        # call, as {"attacker_pos", "defender_pos", "ranged", "hit",
        # "crit"} snapshots - positions are captured at the moment of the
        # swing so a GUI can play a lunge/projectile animation between
        # them even if a combatant later moves.
        self.last_attacks = []

        # Every walk or Flicker Step taken during the most recent
        # player-triggered call, as {"name", "from_pos", "to_pos",
        # "teleport", "path"} dicts, so a GUI can glide a token along
        # "path" (the actual cell-by-cell route a walk took - see
        # attempt_move()'s waypoints in combat.py; just [from, to] for
        # a teleport) instead of snapping it straight to its new
        # position, or cutting a straight line through whatever
        # obstacle a walk detoured around.
        self.last_moves = []

        # Every damage-dealing event resolved during the most recent
        # player-triggered call, as {"pos", "kind", "amount",
        # "damage_type"} dicts - "kind" is one of "hit"/"crit"/"miss"/
        # "hazard_hit"/"hazard_save", "amount" is the damage dealt (or
        # None for a miss). Meant for a GUI to show as a floating
        # number/label instead of making the player read it off the
        # text log.
        self.last_popups = []

        self.order = self._roll_initiative()
        self._begin_round()

    @property
    def player_name(self):
        return self.character["name"]

    def alive(self, name):
        return self.combatants[name]["hp"] > 0

    def alive_monster_names(self):
        return [name for name in self.monster_names if self.alive(name)]

    def set_target(self, name):
        """Picks which monster the player's next attack/cast-at-a-
        creature goes to - a GUI calls this when the player clicks a
        monster's token."""
        if name in self.monster_names and self.alive(name):
            self.target_name = name

    @property
    def current_target(self):
        """The monster actually being targeted right now - the chosen
        target_name if it's still alive, otherwise whichever monster
        is first alive (so a 1-monster fight never needs set_target()
        called at all, and a swarm just re-targets sensibly once its
        current target dies)."""
        if self.target_name is not None and self.alive(self.target_name):
            return self.target_name
        alive = self.alive_monster_names()
        return alive[0] if alive else None

    # -- round / turn bookkeeping -------------------------------------------------

    def _roll_initiative(self):
        """Rolled once, from each combatant's starting zone, then fixed for the fight."""

        order = []
        self.initiative_values = {}
        for name, c in self.combatants.items():
            pos = self.positions[name]
            multiplier = initiative_multiplier(pos, self.zones, self.zone_types)
            d20 = roll_d20(self.rng)
            raw = d20 + c["modifiers"]["DEX"]
            init = raw * multiplier
            zone = zone_at(pos[0], pos[1], self.zones)
            note = f" [{zone['type']} zone, x{multiplier:g} initiative]" if zone else ""
            self.log.append(f"{name} rolls initiative: {raw:g} -> {init:g}{note}")
            self.initiative_rolls.append({"label": f"{name} initiative", "sides": 20, "result": d20})
            self.initiative_values[name] = init
            order.append((init, name))
        order.sort(key=lambda t: t[0], reverse=True)
        return [name for _, name in order]

    def _begin_round(self):
        if self.round_num >= self.max_rounds:
            self.game_over = True
            self.log.append(f"--- Combat ends after {self.round_num} round(s): round limit reached. ---")
            return

        self._spawn_echo_from_last_round()
        self._tick_late_mark()
        self._check_over()
        if self.game_over:
            return

        self.round_num += 1
        self.log.append(f"--- Round {self.round_num} ---")
        self.turn_index = 0
        self._tick_hazard_durations()
        self._tick_tether_duration()
        self._prepare_turn()

    def _spawn_echo_from_last_round(self):
        """The Revenant of Yesterday's Echo (see monsters/bosses/
        revenant_of_yesterday.yaml) - called right before the round
        that follows the one revenant_attack_this_round was captured
        in (see _run_monster_turn), mirroring combat.py's end-of-round
        spawn. A no-op on the very first call (round 1 has no previous
        round to echo), for every non-Revenant fight, and whenever the
        Revenant didn't land an attack in or has since fallen."""

        if self.revenant_name is None or self.revenant_attack_this_round is None or not self.alive(self.revenant_name):
            self.revenant_attack_this_round = None
            return

        self.echo_count += 1
        echo_name = f"{self.revenant_name} Echo #{self.echo_count}"
        echo_trait = next(
            t for t in self.combatants[self.revenant_name]["traits"] if t.get("mechanic") == "revenant_echo"
        )
        self.combatants[echo_name] = make_echo(
            self.combatants[self.revenant_name], echo_name, echo_trait["echo_hp"], self.revenant_attack_this_round,
        )
        self.positions[echo_name] = list(self.positions[self.revenant_name])
        self.order.append(echo_name)
        self.monster_names.append(echo_name)
        self.echo_order.append(echo_name)
        self.flicker_available[echo_name] = True
        self.log.append(
            f"{echo_name} forms where {self.revenant_name} last stood, "
            f"still swinging {self.revenant_attack_this_round['name']}."
        )
        self.revenant_attack_this_round = None

    def _tick_late_mark(self):
        """The Chronophage's "You Are Already Late" (see monsters/bosses/
        chronophage.yaml) - ticks at the same round boundary as hazards/
        Soul Tether, mirroring combat.py's simulate_combat."""

        if self.late_mark is None:
            return
        self.late_mark["rounds_left"] -= 1
        if self.late_mark["rounds_left"] <= 0:
            dmg = roll_dice_string(self.rng, self.late_mark["expiry_damage_dice"])
            self.character["hp"] = max(0, self.character["hp"] - dmg)
            self.log.append(
                f"{self.character['name']}'s time runs out - Already Late resolves for {dmg} psychic damage. "
                f"HP: {self.character['hp']}/{self.character['max_hp']}"
            )
            self.late_mark = None
        else:
            self.log.append(f"{self.character['name']} is Already Late ({self.late_mark['rounds_left']}).")

    def _tick_hazard_durations(self):
        for hz in self.hazards:
            hz["rounds_left"] -= 1
        for hz in self.hazards:
            if hz["rounds_left"] <= 0:
                self.log.append(f"{hz['name']} (cast by {hz['owner']}) burns out.")
        self.hazards = [hz for hz in self.hazards if hz["rounds_left"] > 0]

    def _tick_tether_duration(self):
        if self.tether is None:
            return
        self.tether["rounds_left"] -= 1
        if self.tether["rounds_left"] <= 0:
            self.log.append(f"The tether binding {self.tether['target']} fades.")
            self.tether = None

    def _refresh_tether(self, target_name):
        """Mark/refresh target_name as Soul Tether's target - called
        whenever the player deals it damage. Only one target can be
        Tethered at a time, so a fresh hit just resets the timer."""
        cfg = self.character.get("soul_tether")
        if not cfg or not self.alive(target_name):
            return
        self.tether = {"target": target_name, "rounds_left": cfg["duration_rounds"]}

    def _tick_hazards(self, only=None):
        """Runs apply_hazard_ticks() and mirrors each save it makes
        into last_rolls/last_popups, the same way player_attack()/
        _run_monster_turn() do for attack rolls, so a GUI can animate
        the d20 and show the damage as a floating popup."""
        ticks = apply_hazard_ticks(self.rng, self.hazards, self.positions, self.combatants, self.log, only=only)
        for t in ticks:
            if t["owner"] == self.player_name and t["name"] in self.monster_names and t["damage"] > 0:
                self._refresh_tether(t["name"])
            self.last_rolls.append({"label": f"{t['name']} {t['hazard_name']} save", "sides": 20, "result": t["d20"]})
            self.last_popups.append({
                "pos": tuple(self.positions[t["name"]]),
                "kind": "hazard_save" if t["success"] else "hazard_hit",
                "amount": t["damage"],
                "damage_type": t["damage_type"],
            })

    def _prepare_turn(self):
        if self.game_over:
            return

        while self.turn_index < len(self.order) and not self.alive(self.order[self.turn_index]):
            self.turn_index += 1

        if self.turn_index >= len(self.order):
            self._begin_round()
            return

        self.moved_this_turn = False
        self.acted_this_turn = False
        self.tether_used_this_turn = False

        actor = self.current_actor()
        if actor != self.player_name:
            self._run_monster_turn(actor)

    def current_actor(self):
        return self.order[self.turn_index]

    def is_player_turn(self):
        return not self.game_over and self.order and self.current_actor() == self.player_name

    def _boss_defeated(self):
        """Whether the monster side has lost. The Revenant of Yesterday
        overrides this to just its own HP (see revenant_name) - its
        Echoes are added to self.monster_names so the player can target
        them (see _spawn_echo_from_last_round), but they don't gate
        victory, same as combat.py's simulate_combat."""
        if self.revenant_name is not None:
            return not self.alive(self.revenant_name)
        return not self.alive_monster_names()

    def _check_reversal(self):
        """Reversal (see monsters/bosses/revenant_of_yesterday.yaml) -
        fires "the instant" the Revenant drops to half HP, so this is
        called from _check_over(), which already runs after every
        HP-changing event, rather than only on the Revenant's own turn."""
        if self.revenant_name is None or self.reversal_used:
            return
        revenant = self.combatants[self.revenant_name]
        if revenant["hp"] <= 0 or revenant["hp"] > revenant["max_hp"] // 2:
            return
        oldest_echo = next((e for e in self.echo_order if self.alive(e)), None)
        if oldest_echo is None:
            return
        self.positions[self.revenant_name], self.positions[oldest_echo] = (
            self.positions[oldest_echo], self.positions[self.revenant_name]
        )
        self.reversal_used = True
        self.log.append(f"{self.revenant_name} performs Reversal, trading places with {oldest_echo}!")

    def _check_over(self):
        self._check_reversal()
        if not self.alive(self.player_name):
            self.game_over = True
            # _check_over() can run mid-player-turn too (a hazard tick
            # from the player's own turn can kill them) - current_actor()
            # isn't reliable there, so pick whichever monster is still
            # standing to credit as the winner (any will do; there's no
            # single meaningful "who landed the last blow" with a swarm).
            alive = self.alive_monster_names()
            self.winner = alive[0] if alive else self.monster_names[0]
            self.log.append(f"--- Combat ends after {self.round_num} round(s). Winner: {self.winner} ---")
        elif self._boss_defeated():
            self.game_over, self.winner = True, self.player_name
            self.log.append(f"--- Combat ends after {self.round_num} round(s). Winner: {self.winner} ---")
            self.tether = None

    # -- player actions -------------------------------------------------------

    def move_speed(self, name):
        return self.combatants[name]["speed"]

    def can_move_to(self, target_pos):
        if not self.is_player_turn() or self.moved_this_turn or self.skip_move:
            return False
        pos = self.positions[self.player_name]
        return distance(pos, target_pos) <= self.move_speed(self.player_name) + 0.01

    def player_move(self, target_pos):
        if not self.can_move_to(target_pos):
            return False
        self.last_rolls = []
        self.last_moves = []
        self.last_attacks = []
        self.last_popups = []
        pos = self.positions[self.player_name]
        old_pos = tuple(pos)
        new_pos, check, waypoints = attempt_move(
            self.rng, self.character, self.player_name, pos, target_pos,
            self.move_speed(self.player_name), self.log, self.floor["size"], self.obstacles,
            throne_steps=self.floor["throne_steps"],
        )
        if tuple(new_pos) != old_pos:
            self.last_moves.append({
                "name": self.player_name, "from_pos": old_pos, "to_pos": tuple(new_pos), "teleport": False,
                "path": [tuple(p) for p in waypoints],
            })
        self.positions[self.player_name] = new_pos
        self.last_rolls.append({"label": f"{self.player_name} Athletics", "sides": 20, "result": check["d20"]})
        self.moved_this_turn = True
        return True

    def available_attacks(self):
        if not self.is_player_turn() or self.current_target is None:
            return []
        c = self.combatants[self.player_name]
        dist = distance(self.positions[self.player_name], self.positions[self.current_target])
        return usable_attacks(c, dist)

    def player_attack(self, attack_name):
        if not self.is_player_turn() or self.acted_this_turn:
            return None

        target_name = self.current_target
        if target_name is None:
            return None

        attack = next((a for a in self.available_attacks() if a["name"] == attack_name), None)
        if attack is None:
            return None

        self.last_rolls = []
        self.last_attacks = []
        self.last_moves = []
        self.last_popups = []
        consume_attack_use(attack)
        target = self.combatants[target_name]
        result = resolve_attack(self.rng, attack, target)
        self.last_rolls.append({"label": f"{self.player_name}: {attack['name']}", "sides": 20, "result": result["d20"]})
        self.last_attacks.append({
            "attacker_name": self.player_name,
            "attacker_pos": tuple(self.positions[self.player_name]),
            "defender_pos": tuple(self.positions[target_name]),
            "ranged": "ranged" in attack["kind"],
            "hit": result["hit"],
            "crit": result["crit"],
        })
        self.acted_this_turn = True

        if not result["hit"]:
            self.log.append(f"{self.player_name} attacks {target_name} with {attack['name']} and misses.")
            self.last_popups.append({"pos": tuple(self.positions[target_name]), "kind": "miss"})
        else:
            damage, crit = result["damage"], result["crit"]
            target["hp"] = max(0, target["hp"] - damage)
            self._refresh_tether(target_name)
            crit_note = " (critical hit!)" if crit else ""
            self.log.append(
                f"{self.player_name} hits {target_name} with {attack['name']} for {damage} "
                f"{attack['damage_type']} damage{crit_note}. {target_name} HP: {target['hp']}/{target['max_hp']}"
            )
            self.last_popups.append({
                "pos": tuple(self.positions[target_name]), "kind": "crit" if crit else "hit",
                "amount": damage, "damage_type": attack["damage_type"],
            })
            if target["hp"] <= 0:
                self.log.append(f"{target_name} falls!")

            # "You Are Already Late" clears if the player lands a hit
            # on the Chronophage while marked (see monsters/bosses/
            # chronophage.yaml) - the debt passes back to it instead.
            if self.late_mark is not None and any(t.get("mechanic") == "late_mark" for t in target["traits"]):
                self.late_mark = None
                self.log.append(f"The mark passes back to {target_name} - Already Late clears.")

            self._check_over()

        return result

    def can_cast_at(self, spell_name, target_pos):
        if not self.is_player_turn() or self.acted_this_turn:
            return False
        spell = next(
            (a for a in self.character["attacks"] if a["name"] == spell_name and a["kind"] == "hazard"), None,
        )
        if spell is None:
            return False
        if spell.get("uses") is not None and spell["uses_remaining"] <= 0:
            return False
        pos = self.positions[self.player_name]
        return distance(pos, target_pos) <= spell["range"] + 0.01

    def player_cast(self, spell_name, target_pos):
        if not self.can_cast_at(spell_name, target_pos):
            return None

        spell = next(a for a in self.character["attacks"] if a["name"] == spell_name and a["kind"] == "hazard")
        self.last_rolls = []
        self.last_attacks = []
        self.last_moves = []
        self.last_popups = []
        cast_hazard(self.rng, self.hazards, self.player_name, spell, target_pos, self.combatants, self.log)
        self.acted_this_turn = True
        # "Any creature in the fire's area when you cast the spell" -
        # sweep everyone now, not just the player, in case the bonfire
        # landed on one or more monsters (a swarm's whole point).
        self._tick_hazards()
        self._check_over()
        return True

    def can_use_soul_tether(self):
        cfg = self.character.get("soul_tether")
        if not cfg or not self.is_player_turn() or self.tether_used_this_turn or self.skip_bonus:
            return False
        if cfg.get("uses") is not None and cfg["uses_remaining"] <= 0:
            return False
        return self.tether is not None and self.alive(self.tether["target"])

    def player_use_soul_tether(self):
        """A bonus action, not the player's main action - it doesn't
        touch acted_this_turn, so it can be used alongside a normal
        attack/cast the same turn (or on its own)."""
        if not self.can_use_soul_tether():
            return None

        cfg = self.character["soul_tether"]
        target_name = self.tether["target"]
        self.last_rolls = []
        self.last_attacks = []
        self.last_moves = []
        self.last_popups = []

        target = self.combatants[target_name]
        damage = roll_dice_string(self.rng, cfg["damage_dice"])
        target["hp"] = max(0, target["hp"] - damage)
        healed = min(damage, self.character["max_hp"] - self.character["hp"])
        self.character["hp"] += healed
        if cfg.get("uses") is not None:
            cfg["uses_remaining"] -= 1
        self.tether_used_this_turn = True

        self.log.append(
            f"{self.player_name} feeds on the tether binding {target_name} for {damage} necrotic damage "
            f"and regains {healed} HP. {target_name} HP: {target['hp']}/{target['max_hp']}, "
            f"{self.player_name} HP: {self.character['hp']}/{self.character['max_hp']}"
        )
        self.last_popups.append({
            "pos": tuple(self.positions[target_name]), "kind": "hit",
            "amount": damage, "damage_type": "necrotic",
        })

        if target["hp"] <= 0:
            self.log.append(f"{target_name} falls!")
            self.tether = None
        self._check_over()
        return {"damage": damage, "healed": healed}

    def end_player_turn(self):
        if not self.is_player_turn():
            return
        self.last_rolls = []
        self.last_attacks = []
        self.last_moves = []
        self.last_popups = []
        # Time Debt Repayment (see monsters/bosses/chronophage.yaml)
        # costs exactly the player's next move + bonus action - once
        # this turn (whether it used them or not) is over, that's spent.
        self.skip_move = False
        self.skip_bonus = False
        self._tick_hazards(only=self.player_name)
        self._check_over()
        if self.game_over:
            return
        self.turn_index += 1
        self._prepare_turn()

    # -- monster AI -------------------------------------------------------

    def _run_monster_turn(self, name):
        c = self.combatants[name]
        other_name = self.player_name
        other = self.combatants[other_name]
        pos = self.positions[name]
        dist = distance(pos, self.positions[other_name])

        # Time Debt Repayment/marking (see monsters/bosses/chronophage.yaml) -
        # a free effect on the Chronophage's own turn, mirroring
        # combat.py's simulate_combat. Fires the instant the threshold
        # is met rather than being left to chance.
        time_debt_trait = next((t for t in c["traits"] if t.get("mechanic") == "time_debt"), None)
        if time_debt_trait and self.time_debt >= time_debt_trait["debt_threshold"]:
            if self.rng.choice((True, False)):
                self.skip_move = True
                self.skip_bonus = True
                self.log.append(
                    f"{self.player_name}'s Time Debt comes due - they lose their next move and bonus action!"
                )
            else:
                dmg = roll_dice_string(self.rng, time_debt_trait["repayment_damage_dice"])
                self.character["hp"] = max(0, self.character["hp"] - dmg)
                self.log.append(
                    f"{self.player_name}'s Time Debt comes due for {dmg} psychic damage. "
                    f"HP: {self.character['hp']}/{self.character['max_hp']}"
                )
                self.last_popups.append({
                    "pos": tuple(self.positions[self.player_name]), "kind": "hit",
                    "amount": dmg, "damage_type": "psychic",
                })
            self.time_debt = 0
            self._check_over()
            if self.game_over:
                return

        late_mark_trait = next((t for t in c["traits"] if t.get("mechanic") == "late_mark"), None)
        if late_mark_trait and self.late_mark is None and self.round_num % late_mark_trait["mark_interval_rounds"] == 0:
            self.late_mark = {
                "rounds_left": late_mark_trait["countdown_start"],
                "expiry_damage_dice": late_mark_trait["expiry_damage_dice"],
            }
            self.log.append(f"{name} marks {self.player_name}: You Are Already Late! ({self.late_mark['rounds_left']})")

        # Matched by "mechanic" (a tag, not the display name) so a
        # monster can reflavor this same dash under its own trait name
        # (e.g. the corrupted High Priestess's "Time Skip" - see
        # monsters/bosses/) without the engine needing to know every
        # alias.
        flicker_trait = next((t for t in c["traits"] if t.get("mechanic") == "flicker_step"), None)
        # Flicker Step starts pre-charged, and the party is spawned far
        # across the room specifically so the fight opens with a gap to
        # close (see place_exit_ladder in progression.py) - without this
        # gate a flicker-capable monster teleports 9m plus walks another
        # 9m on turn 1, virtually every time, before the player has done
        # anything. Holding it back until round 2 guarantees at least one
        # real turn of breathing room first.
        flicker_ready = self.round_num > 1

        if flicker_trait and flicker_ready and not self.flicker_available[name]:
            recharge_roll = roll_dice_string(self.rng, "1d6")
            self.last_rolls.append({"label": f"{name} {flicker_trait['name']} recharge", "sides": 6, "result": recharge_roll})
            if recharge_roll >= 5:
                self.flicker_available[name] = True
                self.log.append(f"{name}'s {flicker_trait['name']} recharges.")

        if flicker_trait and flicker_ready and self.flicker_available[name] and dist > c["speed"] + 0.01:
            new_pos = snap_to_grid(step_toward(pos, self.positions[other_name], min(dist, flicker_trait["range"])))
            self.last_moves.append({
                "name": name, "from_pos": tuple(pos), "to_pos": tuple(new_pos), "teleport": True,
                "path": [tuple(pos), tuple(new_pos)],
            })
            self.positions[name] = list(new_pos)
            pos = self.positions[name]
            dist = distance(pos, self.positions[other_name])
            self.flicker_available[name] = False
            self.log.append(f"{name} flickers through a torn instant, reappearing at ({pos[0]:.1f}, {pos[1]:.1f}).")

        # A hazard-kind attack (e.g. a boss's zone ability - see
        # monster.py) places a zone on the ground instead of targeting
        # the enemy directly, same as the player's Create Bonfire (see
        # player_cast()) - checked before movement/attacks, same order
        # combat.py's headless sim uses, so a monster only casts one if
        # already in range at the start of its turn (no move-then-cast
        # combo). Concentration means only one such zone per owner at a
        # time - already_concentrating skips re-casting over itself.
        for spell in hazard_attacks(c):
            if dist > spell["range"] + 0.01:
                continue
            already_concentrating = any(h["owner"] == name and h["name"] == spell["name"] for h in self.hazards)
            if already_concentrating:
                continue
            cast_hazard(self.rng, self.hazards, name, spell, self.positions[other_name], self.combatants, self.log)
            self._tick_hazards(only=name)
            self._check_over()
            if not self.game_over:
                self.turn_index += 1
                self._prepare_turn()
            return

        usable = usable_attacks(c, dist)

        if not usable and c.get("is_echo"):
            pass  # an Echo repeats a past moment in place - it never moves (see make_echo)
        elif not usable:
            old_pos = tuple(pos)
            new_pos, check, waypoints = attempt_move(
                self.rng, c, name, pos, self.positions[other_name], c["speed"], self.log,
                self.floor["size"], self.obstacles, throne_steps=self.floor["throne_steps"],
            )
            if tuple(new_pos) != old_pos:
                self.last_moves.append({
                    "name": name, "from_pos": old_pos, "to_pos": tuple(new_pos), "teleport": False,
                    "path": [tuple(p) for p in waypoints],
                })
            self.positions[name] = new_pos
            pos = self.positions[name]
            self.last_rolls.append({"label": f"{name} Athletics", "sides": 20, "result": check["d20"]})
            dist = distance(self.positions[name], self.positions[other_name])
            usable = usable_attacks(c, dist)

        if not usable:
            self.log.append(f"{name} can't yet reach {other_name}.")
        else:
            attack = max(usable, key=average_damage)
            consume_attack_use(attack)

            # The Revenant of Yesterday's Echo (see monsters/bosses/
            # revenant_of_yesterday.yaml) - whichever attack it swings
            # with this round gets spawned as an Echo next round (see
            # _spawn_echo_from_last_round), hit or miss.
            if name == self.revenant_name:
                self.revenant_attack_this_round = attack

            result = resolve_attack(self.rng, attack, other)
            self.last_rolls.append({"label": f"{name}: {attack['name']}", "sides": 20, "result": result["d20"]})
            self.last_attacks.append({
                "attacker_name": name,
                "attacker_pos": tuple(self.positions[name]),
                "defender_pos": tuple(self.positions[other_name]),
                "ranged": "ranged" in attack["kind"],
                "hit": result["hit"],
                "crit": result["crit"],
            })
            if not result["hit"]:
                self.log.append(f"{name} attacks {other_name} with {attack['name']} and misses.")
                self.last_popups.append({"pos": tuple(self.positions[other_name]), "kind": "miss"})
            else:
                damage, crit = result["damage"], result["crit"]
                other["hp"] = max(0, other["hp"] - damage)
                crit_note = " (critical hit!)" if crit else ""
                self.log.append(
                    f"{name} hits {other_name} with {attack['name']} for {damage} {attack['damage_type']} "
                    f"damage{crit_note}. {other_name} HP: {other['hp']}/{other['max_hp']}"
                )
                self.last_popups.append({
                    "pos": tuple(self.positions[other_name]), "kind": "crit" if crit else "hit",
                    "amount": damage, "damage_type": attack["damage_type"],
                })
                if other["hp"] <= 0:
                    self.log.append(f"{other_name} falls!")

                # Time Debt (see monsters/bosses/chronophage.yaml) -
                # only the Chronophage's own hits load the player up.
                if any(t.get("mechanic") == "time_debt" for t in c["traits"]):
                    self.time_debt += 1
                    self.log.append(f"{self.player_name} gains 1 Time Debt ({self.time_debt}).")

        self._tick_hazards(only=name)
        self._check_over()
        if not self.game_over:
            self.turn_index += 1
            self._prepare_turn()
