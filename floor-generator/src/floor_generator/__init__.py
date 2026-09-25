import random

from .obstacles import DEFAULT_BLOCK_COLOR, DEFAULT_WALL_COLOR, generate_obstacles
from .progression import (
    DOOR_COLOR,
    LADDER_COLOR,
    door_world_rect,
    ladder_world_rect,
    place_entrance_door,
    place_exit_ladder,
    point_in_any_zone,
)
from .render import render_floor
from .texture import generate_floor_texture, save_texture_png
from .throne_room import DEFAULT_STEP_SIZES, generate_throne_room
from .vtt import export_to_foundry_vtt
from .zones import DEFAULT_ZONE_TYPES, DEFAULT_ZONE_WEIGHTS, generate_zones, zone_label

__all__ = [
    "generate_temporal_floor",
    "generate_zones",
    "generate_obstacles",
    "generate_throne_room",
    "DEFAULT_STEP_SIZES",
    "generate_floor_texture",
    "save_texture_png",
    "render_floor",
    "export_to_foundry_vtt",
    "zone_label",
    "point_in_any_zone",
    "place_entrance_door",
    "place_exit_ladder",
    "door_world_rect",
    "ladder_world_rect",
    "DEFAULT_ZONE_TYPES",
    "DEFAULT_ZONE_WEIGHTS",
    "DOOR_COLOR",
    "LADDER_COLOR",
    "DEFAULT_WALL_COLOR",
    "DEFAULT_BLOCK_COLOR",
]


def generate_temporal_floor(
    size=20,
    zone_size_range=(2, 4),
    n_zones=5,
    min_zone_gap=1,
    zone_types=None,
    zone_weights=None,
    n_wall_segments=0,
    wall_length_range=(1, 3),
    n_obstacle_blocks=0,
    throne_room=False,
    seed=42,
    show=True,
    pixels_per_meter=32,
    export_render=None,
    export_vtt=None,
    export_texture=None,
    grid_pixels=100,
):
    """
    Generate a Thal'Vireth temporal floor.

    Orchestrates zone placement (zones.py), door/ladder placement
    (progression.py), texture synthesis (texture.py), matplotlib
    rendering (render.py) and Foundry VTT export (vtt.py).

    Parameters
    ----------
    size : int
        Floor dimensions in meters. Default: 20x20 m.

    zone_size_range : tuple(int, int)
        (min, max) width/height in meters for each zone. Width and
        height are rolled independently, so zones need not be square.

    n_zones : int
        Number of temporal zones.

    min_zone_gap : int
        Minimum empty space between zones.

    zone_types : dict or None
        Zone type registry. Defaults to DEFAULT_ZONE_TYPES (ACC/DEC).
        Every tile outside a placed zone is implicitly neutral floor.
        Each value needs "color", "multiplier" (fixed initiative
        multiplier, or None) and "texture_alpha" for the per-pixel
        texture tint.

    zone_weights : dict or None
        Relative weight per zone type key. Defaults to
        DEFAULT_ZONE_WEIGHTS when zone_types is left at its default,
        otherwise uniform weights across the provided types.

    n_wall_segments : int
        Number of wall obstacles to place, each a straight run of
        grid edges (not a tile) - see obstacles.py. Defaults to 0
        (no obstacles) so existing callers - the combat sim, whose
        movement doesn't yet path around them - are unaffected; the
        CLI passes a non-zero default for standalone floor exports.

    wall_length_range : tuple(int, int)
        (min, max) length in grid edges for each wall segment.

    n_obstacle_blocks : int
        Number of full-tile obstacles (e.g. a pillar) to place.
        Defaults to 0, same reasoning as n_wall_segments.

    throne_room : bool
        If True, a decorative stepped dais (see throne_room.py) is
        drawn centered on the floor and the floor's exit/spawn point
        is forced to its exact middle, instead of the usual far-
        quadrant-from-the-entrance roll - purely visual, not an
        obstacle, so it never blocks movement/pathfinding the way a
        wall would (a throne reached by stairs shouldn't). Used for a
        boss floor (see run.py's BOSS_TEMPLATES) so the boss stands in
        the middle of its own dais rather than an arbitrary corner of
        open floor.

    seed : int
        Random seed for reproducible layouts.

    show : bool
        Whether to open an interactive preview window.

    pixels_per_meter : int
        Resolution of the procedurally generated floor texture.

    export_render : str or None
        If set, path to save the annotated matplotlib render (texture
        + grid + zone outlines/labels + legend) as an image.

    export_vtt : str or None
        If set, path to write a Foundry VTT scene JSON (importable
        via Scenes > Import Data) describing the generated floor.

    export_texture : str or None
        If set, path to save the procedurally generated floor
        texture as a PNG. If export_vtt is also set, the scene's
        background image is pointed at this file.

    grid_pixels : int
        Pixel size of one grid square when exporting to VTT.

    Returns
    -------
    dict
        Generated floor data.
    """

    rng = random.Random(seed)

    if zone_types is None:
        zone_types = DEFAULT_ZONE_TYPES
        zone_weights = zone_weights or DEFAULT_ZONE_WEIGHTS

    if zone_weights is None:
        zone_weights = {t: 1 for t in zone_types}

    zones = generate_zones(size, zone_size_range, n_zones, min_zone_gap, zone_types, zone_weights, rng)

    entrance_door = place_entrance_door(size, zones, rng)

    throne_steps = []
    if throne_room:
        throne = generate_throne_room(size)
        exit_ladder = throne["spawn_cell"]
        throne_steps = throne["steps"]
    else:
        exit_ladder = place_exit_ladder(size, zones, rng, entrance_door)

    obstacles = generate_obstacles(
        size, zones, entrance_door, exit_ladder, rng,
        n_walls=n_wall_segments, wall_length_range=wall_length_range, n_blocks=n_obstacle_blocks,
    )

    texture = None
    need_render = show or export_render
    need_texture = need_render or export_texture

    if need_texture:
        texture = generate_floor_texture(size, pixels_per_meter, zones, zone_types, seed, throne_steps=throne_steps)

    if need_render:
        render_floor(
            size, seed, zones, zone_types, entrance_door, exit_ladder, texture,
            obstacles=obstacles, throne_steps=throne_steps, export_render=export_render, show=show,
        )

    result = {
        "size": size,
        "zone_size_range": zone_size_range,
        "zones": zones,
        "entrance_door": entrance_door,
        "exit_ladder": exit_ladder,
        "obstacles": obstacles,
        "throne_steps": throne_steps,
        "seed": seed,
    }

    if export_texture:
        save_texture_png(texture, export_texture)

    if export_vtt:
        export_to_foundry_vtt(
            result,
            export_vtt,
            zone_types=zone_types,
            grid_pixels=grid_pixels,
            texture_image=export_texture,
        )

    return result
