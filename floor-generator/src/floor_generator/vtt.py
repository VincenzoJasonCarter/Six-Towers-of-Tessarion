# ---------------------------------------------------------------
# Foundry VTT export
# ---------------------------------------------------------------

import json
import random
import string

from .obstacles import DEFAULT_BLOCK_COLOR
from .progression import DOOR_COLOR, LADDER_COLOR, door_world_rect, ladder_world_rect
from .zones import DEFAULT_ZONE_TYPES, zone_label


def _gen_foundry_id(rng):
    alphabet = string.ascii_letters + string.digits
    return "".join(rng.choices(alphabet, k=16))


def export_to_foundry_vtt(
    floor_data,
    path,
    zone_types=None,
    grid_pixels=100,
    scene_name=None,
    texture_image=None,
):
    """
    Write a Foundry VTT scene JSON for a generated floor.

    Import it in Foundry via the Scenes directory's "Import Data"
    option on a scene entry (targets Foundry v11/v12 scene schema).

    Parameters
    ----------
    floor_data : dict
        Output of generate_temporal_floor(). Its "obstacles" key (see
        obstacles.py), if present, is exported as real Foundry walls
        (so they block token movement/sight, not just drawn lines) -
        a wall segment becomes one wall document, a full-tile block
        becomes a filled drawing plus four walls ringing its edges.

    path : str
        File path to write the scene JSON to.

    zone_types : dict or None
        Same registry used to generate the floor, needed to look up
        colors/labels. Defaults to DEFAULT_ZONE_TYPES.

    grid_pixels : int
        Pixel size of one grid square.

    scene_name : str or None
        Scene name. Defaults to a name derived from the seed.

    texture_image : str or None
        Path/filename of a texture PNG (e.g. from export_texture) to
        use as the scene's background image.
    """

    if zone_types is None:
        zone_types = DEFAULT_ZONE_TYPES

    size = floor_data["size"]
    seed = floor_data["seed"]
    rng = random.Random(f"vtt-{seed}")

    scene_name = scene_name or f"Thal'Vireth Floor (Seed {seed})"

    def to_px_x(x):
        return x * grid_pixels

    def to_px_y_top(y, h):
        # Flip: our y=0 is the bottom row, Foundry's y=0 is the top.
        return (size - y - h) * grid_pixels

    drawings = []

    for zone in floor_data["zones"]:

        cfg = zone_types[zone["type"]]
        label = zone_label(zone["type"], cfg)

        drawings.append({
            "_id": _gen_foundry_id(rng),
            "shape": {
                "type": "r",
                "width": zone["w"] * grid_pixels,
                "height": zone["h"] * grid_pixels,
            },
            "x": to_px_x(zone["x"]),
            "y": to_px_y_top(zone["y"], zone["h"]),
            "elevation": 0,
            "sort": 0,
            "rotation": 0,
            "bezierFactor": 0,
            "fillType": 1,
            "fillColor": cfg["color"],
            "fillAlpha": 0.35,
            "strokeWidth": 4,
            "strokeColor": cfg["color"],
            "strokeAlpha": 1,
            "texture": None,
            "text": label,
            "textColor": "#FFFFFF",
            "fontFamily": "Signika",
            "fontSize": 32,
            "textAlpha": 1,
            "hidden": False,
            "locked": False,
            "flags": {},
        })

    def add_marker_drawing(rect, color, text):
        rx, ry, rw, rh = rect
        drawings.append({
            "_id": _gen_foundry_id(rng),
            "shape": {"type": "r", "width": rw * grid_pixels, "height": rh * grid_pixels},
            "x": to_px_x(rx),
            "y": to_px_y_top(ry, rh),
            "elevation": 0,
            "sort": 0,
            "rotation": 0,
            "bezierFactor": 0,
            "fillType": 1,
            "fillColor": color,
            "fillAlpha": 0.9,
            "strokeWidth": 3,
            "strokeColor": color,
            "strokeAlpha": 1,
            "texture": None,
            "text": text,
            "textColor": "#FFFFFF",
            "fontFamily": "Signika",
            "fontSize": 28,
            "textAlpha": 1,
            "hidden": False,
            "locked": False,
            "flags": {},
        })

    entrance_door = floor_data.get("entrance_door")
    exit_ladder = floor_data.get("exit_ladder")

    if entrance_door:
        add_marker_drawing(door_world_rect(entrance_door, size), DOOR_COLOR, "Door")

    if exit_ladder:
        add_marker_drawing(ladder_world_rect(exit_ladder), LADDER_COLOR, "Ladder")

    # -----------------------------------------------------
    # Obstacles: wall segments become real Foundry walls (so they
    # actually block token movement/sight in the scene, not just a
    # drawn line) - a "block" gets both a filled drawing (so it reads
    # visually) and four wall segments ringing its tile, since a
    # drawing alone wouldn't block anything in Foundry.
    # -----------------------------------------------------

    walls = []

    def add_wall(x1, y1, x2, y2):
        walls.append({
            "_id": _gen_foundry_id(rng),
            "c": [to_px_x(x1), to_px_y_top(y1, 0), to_px_x(x2), to_px_y_top(y2, 0)],
            "light": 20,
            "sight": 20,
            "sound": 20,
            "move": 20,
            "dir": 0,
            "door": 0,
            "ds": 0,
            "threshold": {"light": None, "sight": None, "sound": None, "attenuation": False},
            "flags": {},
        })

    obstacles = floor_data.get("obstacles") or {"walls": [], "blocks": []}

    for wall in obstacles["walls"]:
        add_wall(wall["x1"], wall["y1"], wall["x2"], wall["y2"])

    for block in obstacles["blocks"]:
        bx, by, bw, bh = block["x"], block["y"], block["w"], block["h"]
        add_marker_drawing((bx, by, bw, bh), DEFAULT_BLOCK_COLOR, "")
        add_wall(bx, by, bx + bw, by)              # south edge
        add_wall(bx, by + bh, bx + bw, by + bh)     # north edge
        add_wall(bx, by, bx, by + bh)               # west edge
        add_wall(bx + bw, by, bx + bw, by + bh)     # east edge

    scene = {
        "_id": _gen_foundry_id(rng),
        "name": scene_name,
        "active": False,
        "navigation": False,
        "width": size * grid_pixels,
        "height": size * grid_pixels,
        "padding": 0,
        "background": {"src": texture_image},
        "foreground": None,
        "thumb": None,
        "initial": None,
        "backgroundColor": "#999999",
        "grid": {
            "type": 1,
            "size": grid_pixels,
            "color": "#000000",
            "alpha": 0.2,
            "distance": 1,
            "units": "m",
        },
        "tokenVision": False,
        "drawings": drawings,
        "tokens": [],
        "lights": [],
        "notes": [],
        "sounds": [],
        "walls": walls,
        "tiles": [],
        "folder": None,
        "sort": 0,
        "ownership": {"default": 0},
        "flags": {
            "floor-generator": {
                "seed": seed,
                "size": size,
            }
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)

    return scene
