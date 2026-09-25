# ---------------------------------------------------------------
# Procedural floor texture
# ---------------------------------------------------------------

import numpy as np
from PIL import Image

from .throne_room import STEP_COLOR


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _resize(lattice, height, width):
    img = Image.fromarray(lattice, mode="F")
    resized = img.resize((width, height), resample=Image.BILINEAR)
    return np.asarray(resized, dtype=np.float32)


def _fractal_noise(height, width, rng, octaves=5, base_res=6, persistence=0.55, lacunarity=2.0):
    """Cheap multi-octave value noise (no external noise lib needed):
    upsample successively finer random lattices with bilinear
    interpolation and sum them, then normalize to [0, 1].
    """

    noise = np.zeros((height, width), dtype=np.float32)
    amplitude = 1.0
    total = 0.0
    res = float(base_res)

    for _ in range(octaves):

        gh = max(2, round(res))
        gw = max(2, round(res * width / height)) if height else gh

        lattice = rng.random((gh, gw)).astype(np.float32)
        layer = _resize(lattice, height, width)

        noise += layer * amplitude
        total += amplitude

        amplitude *= persistence
        res *= lacunarity

    noise /= total

    lo, hi = noise.min(), noise.max()
    if hi > lo:
        noise = (noise - lo) / (hi - lo)

    return noise


def generate_floor_texture(size, pixels_per_meter, zones, zone_types, seed, throne_steps=None):
    """
    Procedurally render the floor as a per-pixel RGB texture: a
    tileable stone-floor pattern (one shaded tile per 1m grid cell,
    plus fine grain and grout lines) with each zone's footprint
    tinted by its type color, and - for a boss floor - each throne
    step (see throne_room.py) tinted a little brighter gold than the
    one before it, so the dais reads as a distinct, gradually-lit
    platform rather than just the thin outline render_floor()/gui.py
    draw on top of it.

    Returns
    -------
    numpy.ndarray
        uint8 array of shape (size*pixels_per_meter, size*pixels_per_meter, 3).
        Row 0 corresponds to y=0 (matches matplotlib's origin="lower").
    """

    rng = np.random.default_rng(seed)
    res = size * pixels_per_meter

    # One base shade per 1m tile, nearest-neighbor upscaled so tile
    # edges stay crisp instead of blurring into fog.
    tile_shade = 0.40 + 0.12 * rng.random((size, size)).astype(np.float32)
    base = np.repeat(np.repeat(tile_shade, pixels_per_meter, axis=0), pixels_per_meter, axis=1)

    # Fine per-pixel grain, high frequency so it reads as stone grain
    # rather than a soft blur.
    grain = _fractal_noise(res, res, rng, octaves=2, base_res=size * 4, persistence=0.5)
    base = base + (grain - 0.5) * 0.05

    gray = np.clip(base, 0, 1)
    rgb = np.stack([gray, gray, gray * 1.02], axis=-1)

    # Grout lines at every tile boundary.
    grout_px = max(1, pixels_per_meter // 14)
    local = np.arange(res) % pixels_per_meter
    on_edge = (local < grout_px) | (local >= pixels_per_meter - grout_px)
    edge_mask = on_edge[:, None] | on_edge[None, :]
    rgb[edge_mask] *= 0.5

    for zone in zones:

        cfg = zone_types[zone["type"]]

        x0 = int(round(zone["x"] * pixels_per_meter))
        x1 = int(round((zone["x"] + zone["w"]) * pixels_per_meter))
        y0 = int(round(zone["y"] * pixels_per_meter))
        y1 = int(round((zone["y"] + zone["h"]) * pixels_per_meter))

        if x1 <= x0 or y1 <= y0:
            continue

        color = np.array(_hex_to_rgb(cfg["color"]), dtype=np.float32) / 255.0
        alpha = cfg.get("texture_alpha", 0.4)

        region = rgb[y0:y1, x0:x1, :]
        rgb[y0:y1, x0:x1, :] = region * (1 - alpha) + color[None, None, :] * alpha

    if throne_steps:
        step_color = np.array(_hex_to_rgb(STEP_COLOR), dtype=np.float32) / 255.0
        n = len(throne_steps)
        for i, (sx0, sy0, sx1, sy1) in enumerate(throne_steps):

            x0 = int(round(sx0 * pixels_per_meter))
            x1 = int(round(sx1 * pixels_per_meter))
            y0 = int(round(sy0 * pixels_per_meter))
            y1 = int(round(sy1 * pixels_per_meter))

            if x1 <= x0 or y1 <= y0:
                continue

            # Steps are nested squares (see throne_room.py) - painting
            # outer to inner, each stronger than the last, is what
            # makes the ring bands show up at all: without this each
            # step would just overwrite the ones before it edge to
            # edge, leaving a single flat-tinted square instead of a
            # visibly tiered dais.
            alpha = 0.12 + 0.18 * (i + 1) / n

            region = rgb[y0:y1, x0:x1, :]
            rgb[y0:y1, x0:x1, :] = region * (1 - alpha) + step_color[None, None, :] * alpha

    rgb = np.clip(rgb, 0, 1)

    return (rgb * 255).astype(np.uint8)


def save_texture_png(texture, path):
    """Save a texture array (row 0 = y=0, bottom-up) as a standard
    top-down PNG."""

    Image.fromarray(np.flipud(texture)).save(path)
