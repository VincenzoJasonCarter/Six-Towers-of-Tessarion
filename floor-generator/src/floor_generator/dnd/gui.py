# ---------------------------------------------------------------
# Interactive GUI
# ---------------------------------------------------------------
#
# A Pygame front end over CombatEngine: click inside the highlighted
# circle to move, click an attack button to strike, click End Turn to
# hand control to the monster's AI. A separate dice-roller panel lets
# you roll any standard die at any time, using the same dice.py
# helpers the combat engine rolls with.

import argparse
import ctypes
import random
import sys

import pygame

# Windows renders a non-DPI-aware window through its own bitmap
# scaling on any display with scaling above 100% - the window comes
# out blurry and noticeably bigger/"zoomed" than the pixel size it
# was actually created at. Declaring the process DPI-aware up front
# (before pygame opens a window) makes Windows hand pixels over 1:1
# instead. No-op on any other OS, and safe to skip if it's ever
# unavailable (older Windows, sandboxed environments, etc).
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

from .character import load_character
from .combat import distance, snap_to_grid
from .dice import roll
from .engine import CombatEngine
from .run import BOSS_TEMPLATES, FLOOR_COUNT, apply_healing, generate_floor_plan
from ..progression import door_world_rect, ladder_world_rect
from ..zones import DEFAULT_ZONE_TYPES

GRID_ORIGIN = (24, 24)
PX_PER_M = 27
SIDEBAR_X = GRID_ORIGIN[0] + 20 * PX_PER_M + 24
WINDOW_W = SIDEBAR_X + 320
LOG_HEIGHT = 176
WINDOW_H = GRID_ORIGIN[1] + 20 * PX_PER_M + LOG_HEIGHT + 29

BG = (22, 22, 28)
GRID_LINE = (48, 48, 58)
FLOOR_COLOR = (60, 56, 50)
TEXT = (230, 230, 235)
MUTED = (150, 150, 160)
PLAYER_COLOR = (86, 156, 255)
MONSTER_COLOR = (230, 80, 80)
ECHO_COLOR = (150, 90, 130)  # a faded, ghostly variant of MONSTER_COLOR - see the Revenant of Yesterday's Echo
BTN_BG = (46, 46, 58)
BTN_BG_DISABLED = (34, 34, 40)
BTN_BORDER = (90, 90, 105)
BTN_HOVER = (64, 64, 82)
MOVE_RANGE_COLOR = (86, 156, 255)
DOOR_COLOR = (139, 90, 43)
LADDER_COLOR = (201, 166, 107)
WALL_COLOR = (217, 165, 33)  # yellowish/amber - matches obstacles.DEFAULT_WALL_COLOR, contrasts against the floor/zones
BLOCK_COLOR = (74, 74, 74)
THRONE_STEP_COLOR = (232, 196, 104)  # gold - matches throne_room.STEP_COLOR, purely decorative (not an obstacle)

DICE_TYPES = [4, 6, 8, 10, 12, 20, 100]

ROLL_CYCLE_MS = 60       # how often the animated face changes while "rolling"
ROLL_SPIN_MS = 550       # how long it spins before settling on the real result
ROLL_HOLD_MS = 550       # how long it holds on the result before the next roll starts
ROLL_BOX_COLOR = (36, 36, 46)
ROLL_BOX_BORDER = (110, 110, 130)
ROLL_BOX_BORDER_SETTLED = (240, 200, 90)
ROLL_TEXT_COLOR = (240, 240, 245)

ATTACK_ANIM_MS = 380     # total time an attack's lunge/projectile + impact plays out
ATTACK_LUNGE_FRACTION = 0.35   # how far a melee attacker steps toward its target, as a fraction of the gap
ATTACK_TRAVEL_END = 0.7        # fraction of the animation a ranged bolt takes to arrive
ATTACK_IMPACT_START = 0.6      # fraction of the animation where the impact flash begins
HIT_FLASH_COLOR = (255, 120, 60)
CRIT_FLASH_COLOR = (255, 220, 60)
MISS_PUFF_COLOR = (180, 180, 190)
BOLT_COLOR = (255, 220, 120)

CAST_RANGE_COLOR = (255, 140, 40)
HAZARD_COLOR = (255, 140, 40)
HAZARD_CORE_COLOR = (255, 210, 90)

TETHER_COLOR = (190, 110, 230)  # Soul Tether - a violet life-drain, distinct from fire/necrotic-attack colors

RESULT_PAUSE_MS = 1400  # how long a floor's "X wins!" status holds before a tower run auto-advances

MOVE_ANIM_MS = 320             # fixed duration for a teleport's blink-out/blink-in glide
MOVE_ANIM_MS_PER_METER = 90    # a walk's glide instead scales with the route's real length...
MOVE_ANIM_MIN_MS = 220         # ...down to this floor, so even a 1-cell hop is visible, not instant
TELEPORT_BLINK_OUT = 0.15   # teleporting token vanishes before this fraction of the animation
TELEPORT_BLINK_IN = 0.85    # ...and reappears after this fraction

# Combat log: each line is color/weight-coded by what kind of event it
# is (see CombatGUI._classify_log_line), so the feed reads at a glance
# instead of as a wall of uniform text.
LOG_LINE_H = 16
LOG_TOP_PAD = 8
LOG_BULLET_R = 3
LOG_HEADER_COLOR = ROLL_BOX_BORDER_SETTLED
LOG_DEATH_COLOR = (235, 70, 70)
LOG_FLAVOR_COLOR = (100, 100, 112)
LOG_DEFAULT_BULLET = (110, 110, 120)

# Floating combat popups (damage numbers, MISS, save outcomes) that
# rise and fade over a token instead of only being readable in the
# text log below the grid.
POPUP_ANIM_MS = 900
POPUP_RISE_PX = 34
POPUP_SAVE_COLOR = (140, 220, 150)


def world_to_screen(x, y):
    return GRID_ORIGIN[0] + x * PX_PER_M, GRID_ORIGIN[1] + y * PX_PER_M


def screen_to_world(px, py):
    return (px - GRID_ORIGIN[0]) / PX_PER_M, (py - GRID_ORIGIN[1]) / PX_PER_M


class Button:

    def __init__(self, rect, label, on_click, enabled=lambda: True, sublabel=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.sublabel = sublabel
        self.on_click = on_click
        self.enabled = enabled

    def draw(self, screen, font, small_font):
        active = self.enabled()
        hover = active and self.rect.collidepoint(pygame.mouse.get_pos())
        color = BTN_HOVER if hover else (BTN_BG if active else BTN_BG_DISABLED)
        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, BTN_BORDER, self.rect, width=1, border_radius=6)

        text_color = TEXT if active else MUTED
        label_surf = font.render(self.label, True, text_color)
        screen.blit(label_surf, (self.rect.x + 10, self.rect.y + 6))

        if self.sublabel:
            sub_surf = small_font.render(self.sublabel, True, MUTED)
            screen.blit(sub_surf, (self.rect.x + 10, self.rect.y + 26))

    def handle_click(self, pos):
        if self.enabled() and self.rect.collidepoint(pos):
            self.on_click()
            return True
        return False


class DiceAnimation:
    """Spins through random faces, then settles on the real (already-
    rolled) result - so a roll is always visibly happening, not just
    silently applied to game state."""

    def __init__(self, label, sides, result):
        self.label = label
        self.sides = sides
        self.result = result
        self.start = pygame.time.get_ticks()
        self._last_cycle = self.start
        self.display_value = random.randint(1, sides)

    def settled(self):
        return pygame.time.get_ticks() - self.start >= ROLL_SPIN_MS

    def finished(self):
        return pygame.time.get_ticks() - self.start >= ROLL_SPIN_MS + ROLL_HOLD_MS

    def update(self):
        if self.settled():
            self.display_value = self.result
            return
        now = pygame.time.get_ticks()
        if now - self._last_cycle >= ROLL_CYCLE_MS:
            self.display_value = random.randint(1, self.sides)
            self._last_cycle = now


class AttackAnimation:
    """Plays an already-resolved attack out on the grid: a melee
    attacker lunges toward its target and back, a ranged attacker
    sends a traveling bolt, and the target flashes red on a hit (gold
    and labeled on a crit) or puffs gray with a "miss" label otherwise.

    Positions are captured at the moment of the swing (see
    CombatEngine.last_attacks) so the animation plays correctly even
    if a combatant moves again right after."""

    def __init__(self, attacker_name, attacker_pos, defender_pos, ranged, hit, crit):
        self.attacker_name = attacker_name
        self.attacker_pos = attacker_pos
        self.defender_pos = defender_pos
        self.ranged = ranged
        self.hit = hit
        self.crit = crit
        self.start = pygame.time.get_ticks()

    def _progress(self):
        return min(1.0, (pygame.time.get_ticks() - self.start) / ATTACK_ANIM_MS)

    def finished(self):
        return self._progress() >= 1.0

    def attacker_draw_pos(self):
        """Where the attacker's own token should be drawn this frame -
        lunging toward the defender and back for melee, motionless for
        ranged (only its bolt travels)."""
        if self.ranged:
            return self.attacker_pos
        p = self._progress()
        t = (p * 2) if p < 0.5 else (2 - p * 2)  # 0 -> 1 -> 0
        t *= ATTACK_LUNGE_FRACTION
        ax, ay = self.attacker_pos
        dx, dy = self.defender_pos
        return (ax + (dx - ax) * t, ay + (dy - ay) * t)

    def draw_effect(self, screen):
        p = self._progress()
        ax, ay = self.attacker_pos
        dx, dy = self.defender_pos

        if self.ranged:
            travel = min(1.0, p / ATTACK_TRAVEL_END)
            bx, by = ax + (dx - ax) * travel, ay + (dy - ay) * travel
            sx, sy = world_to_screen(bx, by)
            pygame.draw.circle(screen, BOLT_COLOR, (sx, sy), 5)

        if p < ATTACK_IMPACT_START:
            return

        impact = (p - ATTACK_IMPACT_START) / (1 - ATTACK_IMPACT_START)
        sx, sy = world_to_screen(dx, dy)

        if self.hit:
            color = CRIT_FLASH_COLOR if self.crit else HIT_FLASH_COLOR
            radius = max(1, int(10 + impact * (28 if self.crit else 18)))
            alpha = max(0, 255 - int(impact * 255))
            flash = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash, (*color, alpha), (radius, radius), radius, width=3)
            screen.blit(flash, (sx - radius, sy - radius))
        else:
            radius = max(1, int(8 + impact * 10))
            alpha = max(0, 180 - int(impact * 180))
            puff = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff, (*MISS_PUFF_COLOR, alpha), (radius, radius), radius, width=2)
            screen.blit(puff, (sx - radius, sy - radius))
        # The actual "-12 necrotic" / "MISS" text is a FloatingText
        # popup instead (see CombatGUI._make_popup) - it appears once
        # this whole action's animations settle, so the number lingers
        # long enough to actually read instead of vanishing with the
        # flash.


class MoveAnimation:
    """Glides a token along the actual route it walked - see
    attempt_move()'s waypoints in combat.py - instead of cutting a
    straight line from where it started to where it ended up. That
    distinction only shows up once a walk detours around an obstacle
    (see obstacles.py/pathfinding.py): a straight from->to glide would
    visibly clip through whatever the route just went around, which
    reads as a teleport rather than a walk.

    A plain walk moves along that multi-point path at a speed roughly
    proportional to the route's real length (see MOVE_ANIM_MS_PER_METER)
    so a long detour doesn't flash past in the same time as a short
    hop, and eases each individual segment rather than the path as a
    whole - the token visibly slows into every waypoint and
    accelerates back out toward the next one, so a turn around an
    obstacle reads as an actual turn instead of blending into one
    smooth, nearly-straight glide. A teleport (Flicker Step) isn't a
    real walked route - its path is just [from, to] - so it instead
    blinks the token out near the start and back in near the end over
    a fixed duration, matching "vanishes and reappears" rather than
    sliding through the space between.
    """

    def __init__(self, name, path, teleport=False):
        self.name = name
        self.path = [tuple(p) for p in path] if len(path) > 1 else [tuple(path[0]), tuple(path[0])]
        self.teleport = teleport
        self.start = pygame.time.get_ticks()

        self._seg_lengths = [distance(a, b) for a, b in zip(self.path, self.path[1:])]
        self._total_length = sum(self._seg_lengths)
        self.duration_ms = MOVE_ANIM_MS if teleport else max(
            MOVE_ANIM_MIN_MS, self._total_length * MOVE_ANIM_MS_PER_METER,
        )

    def _progress(self):
        return min(1.0, (pygame.time.get_ticks() - self.start) / self.duration_ms)

    def finished(self):
        return self._progress() >= 1.0

    def draw_pos(self):
        if self._total_length == 0:
            return self.path[-1]

        # Each segment gets a time budget proportional to its own
        # length (so overall pacing still matches duration_ms), but is
        # eased INDEPENDENTLY rather than smoothstepping the whole
        # multi-point path as one curve. One global ease only really
        # decelerates at the very first and very last waypoint - every
        # waypoint in between gets crossed at roughly constant speed,
        # which blends corners together until a route around an
        # obstacle reads as barely different from a straight line.
        # Easing per segment instead means the token visibly slows
        # into every waypoint and accelerates back out of the next
        # one, so a turn reads as a turn.
        target_dist = self._progress() * self._total_length
        traveled = 0.0
        for (ax, ay), (bx, by), seg_len in zip(self.path, self.path[1:], self._seg_lengths):
            if seg_len == 0:
                continue
            if target_dist <= traveled + seg_len:
                local_p = (target_dist - traveled) / seg_len
                eased = local_p * local_p * (3 - 2 * local_p)  # smoothstep, per segment
                return (ax + (bx - ax) * eased, ay + (by - ay) * eased)
            traveled += seg_len
        return self.path[-1]

    def visible(self):
        if not self.teleport:
            return True
        p = self._progress()
        return p < TELEPORT_BLINK_OUT or p > TELEPORT_BLINK_IN


class FloatingText:
    """A bit of combat feedback - a damage number, "MISS", a hazard
    save result - that rises and fades over the spot it happened at,
    instead of only being readable as a line in the text log below."""

    def __init__(self, pos, text, color):
        self.pos = pos
        self.text = text
        self.color = color
        self.start = pygame.time.get_ticks()

    def _progress(self):
        return min(1.0, (pygame.time.get_ticks() - self.start) / POPUP_ANIM_MS)

    def finished(self):
        return self._progress() >= 1.0

    def draw(self, screen, font):
        p = self._progress()
        sx, sy = world_to_screen(*self.pos)
        sy -= int(p * POPUP_RISE_PX)
        alpha = max(0, 255 - int(p * 255))
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        screen.blit(surf, (sx - surf.get_width() // 2, sy - 22))


class CombatGUI:

    def __init__(
        self, character_path=None, character=None, seed=42, floor_seed=None, monster_difficulty=None,
        monster_template_path=None, is_boss=False,
        floor_number=None, floor_count=None, screen=None,
    ):
        # floor_number/floor_count are display-only (TowerGUI passes
        # them in so the sidebar and window title can show "Floor N/10"
        # during the fight, not just on the transition screens between
        # floors) - a standalone single-floor fight just leaves them
        # unset and shows neither.
        self.floor_number = floor_number
        self.floor_count = floor_count

        # screen, if given, is an already-open display surface a
        # TowerGUI is reusing across every floor - re-opening a window
        # (pygame.display.set_mode()) on every floor transition is what
        # caused the visible flash/jump between floors, on top of each
        # one re-running Windows' DPI/window-placement negotiation.
        # Standalone single-floor usage still opens its own window here.
        caption = "Thal'Vireth - Combat Simulator"
        if floor_number is not None and floor_count is not None:
            caption = f"Thal'Vireth - Floor {floor_number}/{floor_count}"

        if screen is not None:
            self.screen = screen
            pygame.display.set_caption(caption)
        else:
            pygame.init()
            pygame.display.set_caption(caption)
            self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("consolas", 16)
        self.small_font = pygame.font.SysFont("consolas", 13)
        self.small_font_bold = pygame.font.SysFont("consolas", 13, bold=True)
        self.big_font = pygame.font.SysFont("consolas", 22, bold=True)
        self.roll_font = pygame.font.SysFont("consolas", 48, bold=True)

        self.engine = CombatEngine(
            character_path=character_path, character=character, seed=seed,
            floor_seed=floor_seed, monster_difficulty=monster_difficulty,
            monster_template_path=monster_template_path, is_boss=is_boss,
        )
        # Set by run(quit_on_game_over=True) once the fight ends - "won",
        # "lost", or "quit" (the window was closed mid-fight) - so a
        # TowerRun (see run.py/TowerGUI) knows whether to advance to the
        # next floor, end the run in defeat, or close the whole app.
        self.result = None
        self._game_over_since = None

        self.move_mode = False
        self.cast_mode = False
        self.casting_spell = None
        self.dice_history = []

        # Toggled by the "?" button (boss fights only - see
        # _build_static_buttons) - an overlay explaining the boss's own
        # traits (Time Debt, Echo, ...) in its own words, pulled
        # straight from the template's "description" text rather than
        # hardcoded here, so a new boss's info panel is a data change,
        # not a code change. See _draw_boss_info_overlay().
        self.show_boss_info = False

        self.roll_queue = []
        self.active_roll = None
        self.roll_queue.extend(self.engine.initiative_rolls)

        self.attack_queue = []
        self.active_attack = None

        self.move_queue = []
        self.active_move = None

        # Popups don't gate _animating() - they're decorative feedback,
        # not a step in the turn's action economy, so several can float
        # at once without blocking buttons or grid clicks. They're held
        # in pending_popups until the roll/move/attack pipeline for
        # their action finishes, then released together in _update_popups.
        self.popups = []
        self.pending_popups = []

        self.buttons = []
        self.attack_buttons = []
        self.soul_tether_buttons = []
        self._build_static_buttons()

    def _animating(self):
        return (
            self.active_roll is not None or bool(self.roll_queue)
            or self.active_move is not None or bool(self.move_queue)
            or self.active_attack is not None or bool(self.attack_queue)
        )

    def _display_pos(self, name):
        """Where to actually draw name's token this frame, accounting
        for a move that's resolved in the engine but hasn't animated
        yet.

        The engine updates positions[name] the instant a move resolves
        (see engine.py's player_move/_run_monster_turn), but its
        animation is only queued, and often has to wait behind a dice
        roll (or other queued moves/attacks) before it actually plays
        (see _update_moves). Drawing straight from engine.positions in
        the meantime would show the token already standing at its new
        spot mid-roll, then have it jump backward the instant the walk
        animation activates and starts playing from the old position -
        a visible double-move. So: while a move for this name is still
        active or waiting in queue, keep drawing wherever that move's
        animation says to (its current glide position if active,
        otherwise its pre-move start) instead of the live engine
        position.
        """
        if self.active_move is not None and self.active_move.name == name:
            return self.active_move.draw_pos()
        for mv in self.move_queue:
            if mv["name"] == name:
                return mv["path"][0]
        return self.engine.positions[name]

    def _queue_last_rolls(self):
        # Queue the raw engine dicts, not already-built animation
        # objects - a move/attack often waits behind other animations
        # before it actually plays (see _update_moves/_update_attacks),
        # and an animation's clock starts at construction. Building it
        # now would stamp that clock long before it's actually shown,
        # so by the time it activates its whole duration has already
        # silently elapsed off-screen and it never visibly plays -
        # exactly how DiceAnimation already avoids this (roll_queue
        # holds plain dicts too, built into a DiceAnimation only once
        # popped in _update_rolls).
        self.roll_queue.extend(self.engine.last_rolls)
        self.pending_popups.extend(self.engine.last_popups)
        self.move_queue.extend(self.engine.last_moves)
        self.attack_queue.extend(self.engine.last_attacks)

    # -- setup -------------------------------------------------------

    def _build_static_buttons(self):
        x = SIDEBAR_X
        n_attacks = len(self.engine.character["attacks"])
        self.has_soul_tether = "soul_tether" in self.engine.character

        # Layout flows top to bottom based on how many attack buttons this
        # character needs (plus a Soul Tether row, if it has that feature),
        # so nothing downstream (End Turn, dice roller, dice history) can
        # collide with it.
        self.y_move = 182
        self.y_attacks = self.y_move + 40
        attacks_bottom = self.y_attacks + n_attacks * 42
        if self.has_soul_tether:
            self.y_soul_tether = attacks_bottom + 8
            self.y_end_turn = self.y_soul_tether + 42
        else:
            self.y_end_turn = attacks_bottom + 10
        self.y_dice_title = self.y_end_turn + 40
        self.y_dice_buttons = self.y_dice_title + 22
        self.y_history = self.y_dice_buttons + 2 * 38 + 12

        self.move_button = Button(
            (x, self.y_move, 150, 32), "Move", self._toggle_move_mode,
            enabled=lambda: self.engine.is_player_turn() and not self.engine.moved_this_turn and not self._animating(),
        )
        self.end_turn_button = Button(
            (x, self.y_end_turn, 150, 32), "End Turn", self._end_turn,
            enabled=lambda: self.engine.is_player_turn() and not self._animating(),
        )
        self.buttons = [self.move_button, self.end_turn_button]

        # Boss fights only (see run()'s BOSS_TEMPLATES/is_boss) - not
        # gated on turn state or _animating() like the action buttons
        # above, since looking up a rule shouldn't require it being
        # your turn. Sits at the top-right of the grid's otherwise-
        # empty strip, next to where _draw_floor_indicator's "BOSS" tag
        # renders on the left.
        if self.engine.is_boss:
            grid_right = GRID_ORIGIN[0] + 20 * PX_PER_M
            self.boss_info_button = Button(
                (grid_right - 26, 1, 26, 22), "?", self._toggle_boss_info,
            )
            self.buttons.append(self.boss_info_button)

        self.dice_buttons = []
        for i, sides in enumerate(DICE_TYPES):
            bx = x + (i % 4) * 78
            by = self.y_dice_buttons + (i // 4) * 38
            self.dice_buttons.append(
                Button((bx, by, 70, 30), f"d{sides}", (lambda s=sides: self._roll_die(s)))
            )

    def _toggle_boss_info(self):
        self.show_boss_info = not self.show_boss_info

    def _rebuild_attack_buttons(self):
        x = SIDEBAR_X
        self.attack_buttons = []
        for i, attack in enumerate(self.engine.character["attacks"]):
            uses_left = attack.get("uses") is None or attack["uses_remaining"] > 0

            if attack["kind"] == "hazard":
                # A hazard spell doesn't target the monster directly -
                # clicking it arms cast_mode, then the next grid click
                # (within its range circle) is where the zone lands.
                def enabled(a=attack, uses_left=uses_left):
                    return (
                        self.engine.is_player_turn()
                        and not self.engine.acted_this_turn
                        and uses_left
                        and not self._animating()
                    )

                dc = self.engine.character.get("spell_save_dc", 10)
                sub = f"{attack['damage_dice']} {attack['damage_type']} zone, DC{dc} {attack['save_ability']}, range {attack['range']:g}m"
                if attack.get("uses") is not None:
                    sub += f" - {attack['uses_remaining']}/{attack['uses']} left"
                label = attack["name"] + (" (targeting...)" if self.casting_spell is attack else "")
                self.attack_buttons.append(
                    Button(
                        (x, self.y_attacks + i * 42, 290, 38),
                        label,
                        (lambda a=attack: self._toggle_cast_mode(a)),
                        enabled=enabled,
                        sublabel=sub,
                    )
                )
                continue

            in_range = attack in self.engine.available_attacks()

            def enabled(a=attack, in_range=in_range):
                return (
                    self.engine.is_player_turn()
                    and not self.engine.acted_this_turn
                    and in_range
                    and not self._animating()
                )

            sub = f"{attack['damage_dice']} {attack['damage_type']}, range {attack['range']:g}m"
            if attack.get("uses") is not None:
                sub += f" - {attack['uses_remaining']}/{attack['uses']} left"
            self.attack_buttons.append(
                Button(
                    (x, self.y_attacks + i * 42, 290, 38),
                    attack["name"],
                    (lambda name=attack["name"]: self._do_attack(name)),
                    enabled=enabled,
                    sublabel=sub,
                )
            )

    def _rebuild_soul_tether_button(self):
        self.soul_tether_buttons = []
        if not self.has_soul_tether:
            return

        cfg = self.engine.character["soul_tether"]

        sub = f"{cfg['damage_dice']} necrotic, heal self - bonus action"
        if cfg.get("uses") is not None:
            sub += f" - {cfg['uses_remaining']}/{cfg['uses']} left"
        if self.engine.tether is None:
            sub += " (needs a hit on something first)"
        else:
            sub += f" - bound: {self.engine.tether['target']}"

        self.soul_tether_buttons.append(Button(
            (SIDEBAR_X, self.y_soul_tether, 290, 38), "Soul Tether: Feed",
            self._use_soul_tether,
            enabled=lambda: self.engine.can_use_soul_tether() and not self._animating(),
            sublabel=sub,
        ))

    # -- actions -------------------------------------------------------

    def _toggle_move_mode(self):
        self.move_mode = not self.move_mode
        self.cast_mode = False
        self.casting_spell = None

    def _toggle_cast_mode(self, spell):
        if self.cast_mode and self.casting_spell is spell:
            self.cast_mode = False
            self.casting_spell = None
        else:
            self.cast_mode = True
            self.casting_spell = spell
            self.move_mode = False

    def _do_attack(self, name):
        self.engine.player_attack(name)
        self._queue_last_rolls()
        self.move_mode = False
        self.cast_mode = False
        self.casting_spell = None

    def _use_soul_tether(self):
        # A bonus action, not the main action - doesn't touch
        # move_mode/cast_mode, since the player can still move or
        # attack/cast the same turn.
        self.engine.player_use_soul_tether()
        self._queue_last_rolls()

    def _end_turn(self):
        self.engine.end_player_turn()
        self._queue_last_rolls()
        self.move_mode = False
        self.cast_mode = False
        self.casting_spell = None

    def _roll_die(self, sides):
        rng = self.engine.rng
        result = roll(rng, 1, sides)
        self.dice_history.insert(0, f"d{sides}: {result}")
        self.dice_history = self.dice_history[:4]
        self.roll_queue.append({"label": f"Manual d{sides}", "sides": sides, "result": result})

    def _handle_grid_click(self, pos):
        if not self.engine.is_player_turn() or self._animating():
            return
        wx, wy = screen_to_world(*pos)
        if not (0 <= wx <= 20 and 0 <= wy <= 20):
            return

        if not (self.move_mode or self.cast_mode):
            # Not placing a move/spell right now - a click near a
            # monster's token instead picks it as the attack/cast
            # target (see engine.py's set_target()/current_target),
            # which only matters once there's more than one on the
            # field (a swarm).
            for name in self.engine.alive_monster_names():
                if distance((wx, wy), self.engine.positions[name]) <= 0.5:
                    self.engine.set_target(name)
                    break
            return

        target = snap_to_grid((wx, wy))

        if self.move_mode:
            if self.engine.can_move_to(target):
                self.engine.player_move(target)
                self._queue_last_rolls()
                self.move_mode = False
            return

        if self.cast_mode and self.casting_spell is not None:
            if self.engine.can_cast_at(self.casting_spell["name"], target):
                self.engine.player_cast(self.casting_spell["name"], target)
                self._queue_last_rolls()
                self.cast_mode = False
                self.casting_spell = None

    # -- drawing -------------------------------------------------------

    def _draw_floor_indicator(self):
        """"Floor N/10" in the otherwise-empty strip above the grid -
        only shown when a TowerGUI run set floor_number/floor_count;
        a standalone single-floor fight has neither. A boss fight (see
        run.py's BOSS_TEMPLATES) gets a "BOSS" tag in the same danger
        color as a death-line in the log regardless - shown alongside
        "Floor N/10" during a tower climb, or on its own for a
        standalone fight (e.g. dnd-gui --boss chronophage) - so the
        one fight per climb that's meant to feel different actually
        reads as different before the first roll even happens."""
        has_floor_number = self.floor_number is not None and self.floor_count is not None
        if not has_floor_number and not self.engine.is_boss:
            return
        x = GRID_ORIGIN[0]
        if has_floor_number:
            label = self.font.render(f"Floor {self.floor_number}/{self.floor_count}", True, ROLL_BOX_BORDER_SETTLED)
            self.screen.blit(label, (x, 4))
            x += label.get_width()
        if self.engine.is_boss:
            tag = self.font.render(" - BOSS" if has_floor_number else "BOSS", True, LOG_DEATH_COLOR)
            self.screen.blit(tag, (x, 4))

    def _draw_grid(self):
        grid_size = 20 * PX_PER_M
        grid_rect = pygame.Rect(*GRID_ORIGIN, grid_size, grid_size)
        pygame.draw.rect(self.screen, FLOOR_COLOR, grid_rect)

        for zone in self.engine.zones:
            cfg = DEFAULT_ZONE_TYPES[zone["type"]]
            color = pygame.Color(cfg["color"])
            color.a = 140
            sx, sy = world_to_screen(zone["x"], zone["y"])
            w, h = zone["w"] * PX_PER_M, zone["h"] * PX_PER_M
            zone_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            zone_surf.fill(color)
            self.screen.blit(zone_surf, (sx, sy))
            label = self.small_font.render(f"{zone['type']} x{cfg['multiplier']:g}", True, TEXT)
            self.screen.blit(label, (sx + 4, sy + 4))

        for i in range(21):
            x = GRID_ORIGIN[0] + i * PX_PER_M
            y = GRID_ORIGIN[1] + i * PX_PER_M
            pygame.draw.line(self.screen, GRID_LINE, (x, GRID_ORIGIN[1]), (x, GRID_ORIGIN[1] + grid_size))
            pygame.draw.line(self.screen, GRID_LINE, (GRID_ORIGIN[0], y), (GRID_ORIGIN[0] + grid_size, y))

        pygame.draw.rect(self.screen, TEXT, grid_rect, width=2)

        for wall in self.engine.obstacles["walls"]:
            sx1, sy1 = world_to_screen(wall["x1"], wall["y1"])
            sx2, sy2 = world_to_screen(wall["x2"], wall["y2"])
            pygame.draw.line(self.screen, WALL_COLOR, (sx1, sy1), (sx2, sy2), width=5)

        for block in self.engine.obstacles["blocks"]:
            sx, sy = world_to_screen(block["x"], block["y"])
            block_rect = (sx, sy, block["w"] * PX_PER_M, block["h"] * PX_PER_M)
            pygame.draw.rect(self.screen, BLOCK_COLOR, block_rect)
            pygame.draw.rect(self.screen, TEXT, block_rect, width=1)

        # A boss floor's decorative dais (see throne_room.py) - purely
        # visual, not an obstacle, so it's a thin outline rather than
        # the thick lines walls/blocks get above.
        for x0, y0, x1, y1 in self.engine.floor.get("throne_steps", []):
            sx, sy = world_to_screen(x0, y0)
            step_rect = (sx, sy, (x1 - x0) * PX_PER_M, (y1 - y0) * PX_PER_M)
            pygame.draw.rect(self.screen, THRONE_STEP_COLOR, step_rect, width=2)

        door = self.engine.floor["entrance_door"]
        dx, dy, dw, dh = door_world_rect(door, self.engine.floor["size"])
        sx, sy = world_to_screen(dx, dy)
        pygame.draw.rect(self.screen, DOOR_COLOR, (sx, sy, max(dw * PX_PER_M, 4), max(dh * PX_PER_M, 4)))

        ladder = self.engine.floor["exit_ladder"]
        lx, ly, lw, lh = ladder_world_rect(ladder)
        sx, sy = world_to_screen(lx, ly)
        pygame.draw.rect(self.screen, LADDER_COLOR, (sx, sy, lw * PX_PER_M, lh * PX_PER_M))

        if self.move_mode and self.engine.is_player_turn():
            px, py = world_to_screen(*self.engine.positions[self.engine.player_name])
            radius = self.engine.move_speed(self.engine.player_name) * PX_PER_M
            highlight = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(highlight, (*MOVE_RANGE_COLOR, 60), (radius, radius), radius)
            pygame.draw.circle(highlight, (*MOVE_RANGE_COLOR, 160), (radius, radius), radius, width=2)
            self.screen.blit(highlight, (px - radius, py - radius))

        if self.cast_mode and self.casting_spell is not None and self.engine.is_player_turn():
            px, py = world_to_screen(*self.engine.positions[self.engine.player_name])
            radius = self.casting_spell["range"] * PX_PER_M
            highlight = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(highlight, (*CAST_RANGE_COLOR, 30), (radius, radius), radius)
            pygame.draw.circle(highlight, (*CAST_RANGE_COLOR, 160), (radius, radius), radius, width=2)
            self.screen.blit(highlight, (px - radius, py - radius))

            # Live footprint preview under the cursor, since the spell
            # is a 5x5 area now, not a single tile - the player should
            # see exactly what it'll cover before clicking.
            mx, my = screen_to_world(*pygame.mouse.get_pos())
            if 0 <= mx <= 20 and 0 <= my <= 20:
                preview_target = snap_to_grid((mx, my))
                in_range = self.engine.can_cast_at(self.casting_spell["name"], preview_target)
                size = self.casting_spell.get("area_size", 1)
                half = size // 2
                cx, cy = int(preview_target[0]), int(preview_target[1])
                psx, psy = world_to_screen(cx - half, cy - half)
                pw = ph = size * PX_PER_M
                preview_color = CAST_RANGE_COLOR if in_range else MISS_PUFF_COLOR
                preview_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
                preview_surf.fill((*preview_color, 60))
                self.screen.blit(preview_surf, (psx, psy))
                pygame.draw.rect(self.screen, preview_color, (psx, psy, pw, ph), width=2)

        for hz in self.engine.hazards:
            sx, sy = world_to_screen(hz["x"], hz["y"])
            w, h = hz["w"] * PX_PER_M, hz["h"] * PX_PER_M
            hazard_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            hazard_surf.fill((*HAZARD_COLOR, 90))
            self.screen.blit(hazard_surf, (sx, sy))
            pygame.draw.rect(self.screen, HAZARD_CORE_COLOR, (sx, sy, w, h), width=2)
            label = self.small_font.render(f"{hz['name']} ({hz['rounds_left']})", True, TEXT)
            self.screen.blit(label, (sx + 4, sy + 4))

        player_name = self.engine.player_name
        anim = self.active_attack
        move = self.active_move

        player_draw_pos, player_visible = self._display_pos(player_name), True
        if move is not None and move.name == player_name:
            player_visible = move.visible()
        elif anim is not None and anim.attacker_name == player_name:
            player_draw_pos = anim.attacker_draw_pos()
        if player_visible:
            self._draw_token(player_draw_pos, PLAYER_COLOR, "P")

        # A swarm template puts several monsters on the field at once
        # (see monster.py's generate_monster_group()) - draw every
        # living one, numbering them only once there's more than one
        # to tell apart, and ring whichever the player's attacks/casts
        # are currently aimed at (see engine.py's current_target). The
        # Revenant of Yesterday's Echoes are real entries in
        # alive_monster_names() too (see engine.py's
        # _spawn_echo_from_last_round), labeled/colored distinctly (E1,
        # E2, ...) so they read as remnants, not additional real
        # monsters, even though they're fully real, targetable combatants.
        alive_monsters = self.engine.alive_monster_names()
        echo_i = 0
        monster_i = 0
        for name in alive_monsters:
            draw_pos, visible = self._display_pos(name), True
            if move is not None and move.name == name:
                visible = move.visible()
            elif anim is not None and anim.attacker_name == name:
                draw_pos = anim.attacker_draw_pos()
            if not visible:
                continue
            if self.engine.combatants[name].get("is_echo"):
                echo_i += 1
                letter, color = f"E{echo_i}", ECHO_COLOR
            else:
                monster_i += 1
                letter = f"M{monster_i}" if len(alive_monsters) > 1 else "M"
                color = MONSTER_COLOR
            self._draw_token(draw_pos, color, letter, highlighted=(name == self.engine.current_target))

        if anim is not None:
            anim.draw_effect(self.screen)

        for p in self.popups:
            p.draw(self.screen, self.font)

    def _draw_token(self, pos, color, letter, highlighted=False):
        sx, sy = world_to_screen(*pos)
        if highlighted:
            pygame.draw.circle(self.screen, ROLL_BOX_BORDER_SETTLED, (sx, sy), 15, width=2)
        pygame.draw.circle(self.screen, color, (sx, sy), 11)
        pygame.draw.circle(self.screen, TEXT, (sx, sy), 11, width=1)
        letter_surf = self.small_font.render(letter, True, (10, 10, 12))
        offset = 7 if len(letter) > 1 else 4
        self.screen.blit(letter_surf, (sx - offset, sy - 7))

    def _draw_hp_bar(self, x, y, width, current, maximum, color, suffix=""):
        pygame.draw.rect(self.screen, BTN_BG_DISABLED, (x, y, width, 14), border_radius=4)
        frac = max(0.0, current / maximum) if maximum else 0
        pygame.draw.rect(self.screen, color, (x, y, int(width * frac), 14), border_radius=4)
        pygame.draw.rect(self.screen, BTN_BORDER, (x, y, width, 14), width=1, border_radius=4)
        label = self.small_font.render(f"{current}/{maximum} HP{suffix}", True, TEXT)
        self.screen.blit(label, (x + width + 8, y - 1))

    def _draw_sidebar(self):
        x = SIDEBAR_X
        e = self.engine

        # Turn order was only ever announced once, at the top of the
        # log, and scrolled away a few lines later - a gold outline
        # around whoever's acting plus each one's rolled initiative
        # keeps that visible for the whole fight.
        player_turn = e.is_player_turn()
        monster_turn = not e.game_over and e.order and e.current_actor() != e.player_name

        if player_turn:
            pygame.draw.rect(self.screen, ROLL_BOX_BORDER_SETTLED, (x - 10, 14, 300, 60), width=2, border_radius=8)
        title = self.big_font.render(e.player_name, True, PLAYER_COLOR)
        self.screen.blit(title, (x, 20))
        init_p = e.initiative_values.get(e.player_name)
        suffix_p = f"   Init {init_p:g}" if init_p is not None else ""
        self._draw_hp_bar(x, 50, 130, e.character["hp"], e.character["max_hp"], (90, 200, 120), suffix=suffix_p)

        # A swarm puts several monsters on the field (see
        # monster.py's generate_monster_group()) - the sidebar shows
        # whichever one is currently targeted (see engine.py's
        # current_target/set_target(), click a token to change it),
        # plus a "+N more" count so the rest aren't invisible. Uses the
        # smaller font here, not big_font like Pijo's name - a swarm
        # member's name (with its "#N" suffix) plus the count can run
        # long enough to crowd the sidebar otherwise.
        if monster_turn:
            pygame.draw.rect(self.screen, ROLL_BOX_BORDER_SETTLED, (x - 10, 84, 300, 60), width=2, border_radius=8)
        target_name = e.current_target
        alive_count = len(e.alive_monster_names())
        if target_name is not None:
            label = target_name + (f"  (+{alive_count - 1} more)" if alive_count > 1 else "")
            mtitle = self.font.render(label, True, MONSTER_COLOR)
            self.screen.blit(mtitle, (x, 92))
            target = e.combatants[target_name]
            init_m = e.initiative_values.get(target_name)
            suffix_m = f"   Init {init_m:g}" if init_m is not None else ""
            if e.tether is not None and e.tether["target"] == target_name:
                suffix_m += f"   [Tethered, {e.tether['rounds_left']}]"
            self._draw_hp_bar(x, 120, 130, target["hp"], target["max_hp"], (220, 90, 90), suffix=suffix_m)
        else:
            mtitle = self.font.render("No enemies remaining", True, MUTED)
            self.screen.blit(mtitle, (x, 92))

        if e.game_over:
            status = f"{e.winner} wins!"
        elif e.is_player_turn():
            status = f"Round {e.round_num} - your turn"
        else:
            status = f"Round {e.round_num} - {e.current_actor()} acting..."
        status_surf = self.font.render(status, True, TEXT)
        self.screen.blit(status_surf, (x, 165))

        if self.move_mode:
            hint = self.small_font.render("Click inside the circle to move.", True, MUTED)
            self.screen.blit(hint, (x, 190))
        elif self.cast_mode:
            hint = self.small_font.render("Click a tile to place it.", True, MUTED)
            self.screen.blit(hint, (x, 190))

        for btn in self.buttons:
            btn.draw(self.screen, self.font, self.small_font)
        for btn in self.attack_buttons:
            btn.draw(self.screen, self.font, self.small_font)
        for btn in self.soul_tether_buttons:
            btn.draw(self.screen, self.font, self.small_font)

        dice_title = self.font.render("Dice roller", True, TEXT)
        self.screen.blit(dice_title, (x, self.y_dice_title))
        for btn in self.dice_buttons:
            btn.draw(self.screen, self.font, self.small_font)

        history_y = self.y_history
        for line in self.dice_history:
            surf = self.small_font.render(line, True, MUTED)
            self.screen.blit(surf, (x, history_y))
            history_y += 18

    def _update_rolls(self):
        if self.active_roll is not None:
            self.active_roll.update()
            if self.active_roll.finished():
                self.active_roll = None
        if self.active_roll is None and self.roll_queue:
            entry = self.roll_queue.pop(0)
            self.active_roll = DiceAnimation(entry["label"], entry["sides"], entry["result"])

    def _update_moves(self):
        # Moves play out only once every roll for that action has
        # settled (e.g. the Athletics check), and before any attack
        # animation, so the sequence reads roll -> glide -> strike
        # instead of everything happening at once.
        if self.active_move is not None and self.active_move.finished():
            self.active_move = None
        if self.active_move is None and self.move_queue and self.active_roll is None and not self.roll_queue:
            mv = self.move_queue.pop(0)
            self.active_move = MoveAnimation(mv["name"], mv["path"], mv["teleport"])

    def _update_attacks(self):
        # Attacks play out only once every roll and move for that
        # action have settled, so the player sees "roll to hit"
        # resolve (and any repositioning finish) before the strike
        # itself animates on the grid.
        if self.active_attack is not None and self.active_attack.finished():
            self.active_attack = None
        if (
            self.active_attack is None and self.attack_queue
            and self.active_roll is None and not self.roll_queue
            and self.active_move is None and not self.move_queue
        ):
            atk = self.attack_queue.pop(0)
            self.active_attack = AttackAnimation(
                atk["attacker_name"], atk["attacker_pos"], atk["defender_pos"],
                atk["ranged"], atk["hit"], atk["crit"],
            )

    def _make_popup(self, entry):
        kind, pos = entry["kind"], entry["pos"]
        if kind == "miss":
            return FloatingText(pos, "MISS", MISS_PUFF_COLOR)
        if kind == "crit":
            return FloatingText(pos, f"-{entry['amount']} {entry['damage_type']}!", CRIT_FLASH_COLOR)
        if kind == "hit":
            return FloatingText(pos, f"-{entry['amount']} {entry['damage_type']}", HIT_FLASH_COLOR)
        if kind == "hazard_hit":
            return FloatingText(pos, f"-{entry['amount']} {entry['damage_type']}", HAZARD_COLOR)
        if kind == "hazard_save":
            text = f"-{entry['amount']} {entry['damage_type']} (saved)" if entry["amount"] else "SAVED"
            return FloatingText(pos, text, POPUP_SAVE_COLOR)
        return FloatingText(pos, "?", TEXT)

    def _update_popups(self):
        self.popups = [p for p in self.popups if not p.finished()]
        # Held back until the roll/move/attack pipeline for their
        # action has fully played out, so a damage number doesn't pop
        # up before the dice roll (or the strike animation) that
        # explains it has even finished.
        if self.pending_popups and not self._animating():
            self.popups.extend(self._make_popup(entry) for entry in self.pending_popups)
            self.pending_popups = []

    def _draw_roll_animation(self):
        if self.active_roll is None:
            return

        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 240, 130
        cx = GRID_ORIGIN[0] + (20 * PX_PER_M) // 2
        cy = GRID_ORIGIN[1] + (20 * PX_PER_M) // 2
        rect = pygame.Rect(cx - box_w // 2, cy - box_h // 2, box_w, box_h)

        border = ROLL_BOX_BORDER_SETTLED if self.active_roll.settled() else ROLL_BOX_BORDER
        pygame.draw.rect(self.screen, ROLL_BOX_COLOR, rect, border_radius=10)
        pygame.draw.rect(self.screen, border, rect, width=3, border_radius=10)

        label_text = f"{self.active_roll.label} (d{self.active_roll.sides})"
        label_surf = self.small_font.render(label_text, True, ROLL_TEXT_COLOR)
        self.screen.blit(label_surf, (rect.centerx - label_surf.get_width() // 2, rect.y + 14))

        value_surf = self.roll_font.render(str(self.active_roll.display_value), True, ROLL_TEXT_COLOR)
        self.screen.blit(value_surf, (rect.centerx - value_surf.get_width() // 2, rect.centery - 8))

        hint = "rolling..." if not self.active_roll.settled() else "rolled!"
        hint_surf = self.small_font.render(hint, True, MUTED)
        self.screen.blit(hint_surf, (rect.centerx - hint_surf.get_width() // 2, rect.bottom - 24))

    def _classify_log_line(self, line):
        """(bullet_color_or_None, text_color, font, extra_gap_before)
        for a combat-log line, inferred from the wording combat.py /
        engine.py already log with - so hits, crits, deaths, hazards
        and round breaks each get their own look instead of one flat
        color for everything.
        """

        if line.startswith("---"):
            return None, LOG_HEADER_COLOR, self.small_font_bold, True
        if "falls!" in line:
            return LOG_DEATH_COLOR, LOG_DEATH_COLOR, self.small_font_bold, False
        if "critical hit" in line:
            return CRIT_FLASH_COLOR, CRIT_FLASH_COLOR, self.small_font, False
        if "save against" in line or "conjures" in line or "burns out" in line:
            return HAZARD_COLOR, TEXT, self.small_font, False
        if "feeds on the tether" in line:
            return TETHER_COLOR, TETHER_COLOR, self.small_font, False

        flavor_markers = (
            "misses", "can't yet reach", "fails to find footing",
            "rolls an Athletics check", "rolls initiative", "moves to",
            "flickers through", "recharges", "tether binding",
        )
        if any(marker in line for marker in flavor_markers):
            return LOG_FLAVOR_COLOR, MUTED, self.small_font, False

        if line.startswith(self.engine.player_name) and "hits" in line:
            return PLAYER_COLOR, TEXT, self.small_font, False
        if "hits" in line and any(line.startswith(name) for name in self.engine.monster_names):
            return MONSTER_COLOR, TEXT, self.small_font, False

        return LOG_DEFAULT_BULLET, TEXT, self.small_font, False

    def _wrap_text(self, text, font, max_width):
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if not current or font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    def _boss_combatant(self):
        """The boss's own combatant dict for a boss fight (see
        run()'s BOSS_TEMPLATES/is_boss) - None otherwise. Excludes a
        Revenant of Yesterday's Echoes (see engine.py's
        _spawn_echo_from_last_round) - they're real, separately-named
        entries in monster_names, but an Echo has no traits of its own
        to explain (see monster.py's make_echo), so it'd never be the
        right thing for _draw_boss_info_overlay to describe."""
        if not self.engine.is_boss:
            return None
        name = next(
            (n for n in self.engine.monster_names if not self.engine.combatants[n].get("is_echo")), None,
        )
        return self.engine.combatants[name] if name else None

    def _draw_boss_info_overlay(self):
        """The "?" button's panel (see _build_static_buttons) - every
        one of the boss's own traits, name and description exactly as
        written in its template YAML (see monsters/bosses/), so a new
        boss's info panel is a content change there, not a code change
        here. Dismissed by a click anywhere (see run())."""
        if not self.show_boss_info:
            return
        boss = self._boss_combatant()
        if boss is None:
            return

        dim = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 190))
        self.screen.blit(dim, (0, 0))

        panel = pygame.Rect(50, 40, WINDOW_W - 100, WINDOW_H - 80)
        pygame.draw.rect(self.screen, BTN_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, ROLL_BOX_BORDER_SETTLED, panel, width=2, border_radius=10)

        title = self.big_font.render(boss["name"], True, MONSTER_COLOR)
        self.screen.blit(title, (panel.x + 20, panel.y + 16))
        subtitle = self.small_font.render(boss.get("type", ""), True, MUTED)
        self.screen.blit(subtitle, (panel.x + 20, panel.y + 46))

        y = panel.y + 76
        max_w = panel.width - 40
        for trait in boss["traits"]:
            name_surf = self.font.render(trait["name"], True, TEXT)
            self.screen.blit(name_surf, (panel.x + 20, y))
            y += 22
            description = " ".join(trait.get("description", "").split())
            for line in self._wrap_text(description, self.small_font, max_w):
                line_surf = self.small_font.render(line, True, MUTED)
                self.screen.blit(line_surf, (panel.x + 20, y))
                y += 18
            y += 12

        hint = self.small_font.render("Click anywhere to close.", True, MUTED)
        self.screen.blit(hint, (panel.x + 20, panel.bottom - 26))

    def _draw_log(self):
        log_rect = pygame.Rect(GRID_ORIGIN[0], GRID_ORIGIN[1] + 20 * PX_PER_M + 12, WINDOW_W - 48, LOG_HEIGHT)
        pygame.draw.rect(self.screen, BTN_BG_DISABLED, log_rect, border_radius=6)
        pygame.draw.rect(self.screen, BTN_BORDER, log_rect, width=1, border_radius=6)

        text_x = log_rect.x + 22
        max_text_w = log_rect.right - 10 - text_x
        max_rows = max(1, (log_rect.height - 2 * LOG_TOP_PAD) // LOG_LINE_H)

        # Wrap from the most recent log entry backward until the box
        # would overflow, so a long message wraps onto its own line
        # instead of running past the edge or getting silently cut
        # short at a fixed entry count.
        entries = []
        total_rows = 0
        for line in reversed(self.engine.log):
            bullet, color, font, header = self._classify_log_line(line)
            wrapped = self._wrap_text(line, font, max_text_w)
            if entries and total_rows + len(wrapped) > max_rows:
                break
            entries.append((wrapped, bullet, color, font, header))
            total_rows += len(wrapped)
            if total_rows >= max_rows:
                break
        entries.reverse()

        y = log_rect.y + LOG_TOP_PAD
        for wrapped, bullet, color, font, header in entries:
            if header and y > log_rect.y + LOG_TOP_PAD:
                y += 4  # a little breathing room before a new round's header
            for i, sub in enumerate(wrapped):
                if bullet and i == 0:
                    pygame.draw.circle(self.screen, bullet, (log_rect.x + 14, y + 7), LOG_BULLET_R)
                surf = font.render(sub, True, color)
                self.screen.blit(surf, (text_x, y))
                y += LOG_LINE_H

    # -- main loop -------------------------------------------------------

    def run(self, quit_on_game_over=False):
        """quit_on_game_over=True is TowerGUI's mode: once the fight
        ends (and every roll/move/attack/popup has finished playing),
        pause briefly on the result, then return instead of calling
        pygame.quit() - the caller decides what happens next (advance
        to the next floor, end the run) and owns the pygame session,
        possibly across several more floors."""

        running = True
        while running:
            self._rebuild_attack_buttons()
            self._rebuild_soul_tether_button()
            self._update_rolls()
            self._update_moves()
            self._update_attacks()
            self._update_popups()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.result = "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.show_boss_info:
                        # The panel eats this click closing itself,
                        # rather than letting it fall through to a
                        # button or grid tile it happens to land on.
                        self.show_boss_info = False
                        continue
                    handled = False
                    for btn in self.buttons + self.attack_buttons + self.soul_tether_buttons + self.dice_buttons:
                        if btn.handle_click(event.pos):
                            handled = True
                            break
                    if not handled:
                        self._handle_grid_click(event.pos)

            self.screen.fill(BG)
            self._draw_floor_indicator()
            self._draw_grid()
            self._draw_sidebar()
            self._draw_log()
            self._draw_roll_animation()
            self._draw_boss_info_overlay()
            pygame.display.flip()
            self.clock.tick(60)

            if quit_on_game_over and self.engine.game_over and not self._animating() and not self.popups:
                if self._game_over_since is None:
                    self._game_over_since = pygame.time.get_ticks()
                elif pygame.time.get_ticks() - self._game_over_since >= RESULT_PAUSE_MS:
                    running = False
                    self.result = "won" if self.engine.winner == self.engine.player_name else "lost"

        if not quit_on_game_over:
            pygame.quit()


class TowerGUI:
    """Drives a full FLOOR_COUNT-floor climb through one pygame window:
    a CombatGUI per combat floor (fresh battlefield and a random,
    difficulty-weighted monster - see run.py), and a simple full-rest
    screen for each healing floor. The character dict is loaded once
    and carried through every floor, so HP and spent uses persist
    except right after a healing floor resets them."""

    def __init__(self, character_path=None, seed=42):
        self.rng = random.Random(seed)
        self.character = load_character(character_path)
        self.plan = generate_floor_plan()
        self.floor_index = 0

        pygame.init()
        pygame.display.set_caption("Thal'Vireth - Tower Climb")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("consolas", 28, bold=True)
        self.font = pygame.font.SysFont("consolas", 16)
        self.small_font = pygame.font.SysFont("consolas", 13)

    def run(self):
        for self.floor_index in range(len(self.plan)):
            floor = self.plan[self.floor_index]

            if floor["type"] == "healing":
                cleared = self._show_message_screen(
                    f"Floor {floor['number']}/{len(self.plan)} - Healing Chamber",
                    "HP and every spent ability are fully restored.",
                    (140, 220, 150),
                )
                if not cleared:
                    pygame.quit()
                    return
                apply_healing(self.character)
                continue

            difficulty = (floor["number"] - 1) / (FLOOR_COUNT - 1)
            floor_seed = self.rng.randint(0, 2**31 - 1)
            is_boss = floor["type"] == "boss"
            combat = CombatGUI(
                character=self.character, seed=floor_seed, floor_seed=floor_seed,
                monster_difficulty=difficulty,
                monster_template_path=BOSS_TEMPLATES.get(floor["number"]) if is_boss else None,
                is_boss=is_boss,
                floor_number=floor["number"], floor_count=len(self.plan),
                screen=self.screen,
            )
            combat.run(quit_on_game_over=True)

            if combat.result == "quit":
                pygame.quit()
                return
            if combat.result == "lost":
                self._show_message_screen(
                    "You have fallen.",
                    f"Floors cleared: {floor['number'] - 1}/{len(self.plan)}.",
                    (235, 90, 90),
                )
                pygame.quit()
                return
            # "won" - loop continues to the next floor

        self._show_message_screen(
            "The climb is complete!",
            f"Pijo clears all {len(self.plan)} floors of Thal'Vireth.",
            (255, 215, 90),
        )
        pygame.quit()

    def _show_message_screen(self, title, subtitle, color):
        """A plain full-window transition screen. Blocks until a click
        or keypress; returns False instead if the window was closed."""

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    waiting = False

            self.screen.fill(BG)
            title_surf = self.title_font.render(title, True, color)
            self.screen.blit(title_surf, title_surf.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 - 40)))
            sub_surf = self.font.render(subtitle, True, TEXT)
            self.screen.blit(sub_surf, sub_surf.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2)))
            hint_surf = self.small_font.render("Click or press any key to continue.", True, MUTED)
            self.screen.blit(hint_surf, hint_surf.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 + 40)))
            pygame.display.flip()
            self.clock.tick(30)

        return True


def _resolve_boss(spec):
    """--boss accepts either a boss floor number (5, 10) or a name
    matching a boss template's filename stem (chronophage,
    revenant_of_yesterday, or just revenant - substring match).
    Returns (template_path, floor_number), or (None, None) if spec is
    None. Exits with a usage error for anything else, listing the
    valid choices, rather than failing deeper inside CombatEngine."""

    if spec is None:
        return None, None

    try:
        floor_num = int(spec)
    except ValueError:
        matches = [n for n, path in BOSS_TEMPLATES.items() if spec.lower() in path.stem.lower()]
        if len(matches) != 1:
            choices = ", ".join(f"{n} ({path.stem})" for n, path in sorted(BOSS_TEMPLATES.items()))
            raise SystemExit(f"--boss '{spec}' doesn't match exactly one boss. Choices: {choices}")
        floor_num = matches[0]

    if floor_num not in BOSS_TEMPLATES:
        choices = ", ".join(str(n) for n in sorted(BOSS_TEMPLATES))
        raise SystemExit(f"--boss {floor_num}: no boss on that floor. Boss floors: {choices}")

    return BOSS_TEMPLATES[floor_num], floor_num


def main():
    parser = argparse.ArgumentParser(description="Interactive Thal'Vireth combat GUI.")
    parser.add_argument("--character", default=None, help="Path to a character YAML config (defaults to Pijo).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--floor-seed", type=int, default=None, help="Only used with --single-floor/--boss.")
    parser.add_argument(
        "--single-floor", action="store_true",
        help="Run one standalone fight instead of the full 10-floor tower climb.",
    )
    parser.add_argument(
        "--boss", default=None,
        help="Fight a specific boss directly instead of a random/difficulty-weighted monster - "
             "by floor number (5 or 10) or name (e.g. chronophage, revenant). Implies --single-floor "
             "and uses that floor's usual difficulty scaling.",
    )

    args = parser.parse_args()
    boss_template, boss_floor = _resolve_boss(args.boss)

    if args.single_floor or boss_template is not None:
        difficulty = (boss_floor - 1) / (FLOOR_COUNT - 1) if boss_floor is not None else None
        gui = CombatGUI(
            character_path=args.character, seed=args.seed, floor_seed=args.floor_seed,
            monster_difficulty=difficulty, monster_template_path=boss_template, is_boss=boss_template is not None,
        )
        gui.run()
    else:
        tower = TowerGUI(character_path=args.character, seed=args.seed)
        tower.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
