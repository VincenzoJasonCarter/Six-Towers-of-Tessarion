"""Split the world-map SVG embedded in an Azgaar Fantasy Map Generator
``.map`` save into one cropped PNG per political region (state/nation).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import resvg_py
from PIL import Image

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass
class StateRegion:
    id: int
    name: str
    color: str | None
    bbox: tuple[float, float, float, float]  # minx, miny, maxx, maxy in SVG units


def find_latest_map(map_dir: Path) -> Path:
    candidates = sorted(map_dir.glob("*.map"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No .map files found in {map_dir}")
    return candidates[-1]


def extract_svg(map_text: str) -> str:
    start = map_text.find("<svg")
    end = map_text.find("</svg>")
    if start == -1 or end == -1:
        raise ValueError("No embedded <svg> found in .map file")
    return map_text[start : end + len("</svg>")]


def parse_states(map_text: str) -> list[dict]:
    for line in map_text.splitlines():
        line = line.strip()
        if not (line.startswith("[{") and line.endswith("}]")):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list) and data and isinstance(data[0], dict):
            keys = data[0].keys()
            if {"i", "name", "salesTax", "pollTax"} <= keys:
                return data
    raise ValueError("Could not locate the states array in .map file")


def _path_bbox(d: str) -> tuple[float, float, float, float]:
    numbers = [float(n) for n in _NUMBER_RE.findall(d)]
    xs = numbers[0::2]
    ys = numbers[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def find_state_regions(svg_text: str, states: list[dict]) -> list[StateRegion]:
    names_by_id = {
        s["i"]: s["name"]
        for s in states
        if s.get("i", 0) != 0 and s.get("name") and not s.get("removed")
    }

    body_start = svg_text.find('id="statesBody"')
    body_end = svg_text.find('id="statesHalo"')
    body_segment = svg_text[body_start:body_end]

    regions = []
    for match in re.finditer(
        r'<path\s+d="([^"]*)"\s+fill="(#[0-9a-fA-F]{6})"\s+id="state(\d+)"',
        body_segment,
    ):
        d, color, sid = match.groups()
        sid = int(sid)
        name = names_by_id.get(sid)
        if name is None:
            continue
        regions.append(StateRegion(id=sid, name=name, color=color, bbox=_path_bbox(d)))
    return regions


def render_full_map(svg_text: str, zoom: float) -> Image.Image:
    png_bytes = resvg_py.svg_to_bytes(svg_string=svg_text, zoom=zoom)
    from io import BytesIO

    return Image.open(BytesIO(png_bytes)).convert("RGB")


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-']+", "_", name).strip("_")


def segment_map_by_state(
    map_path: Path,
    output_dir: Path,
    zoom: float = 4.0,
    padding_ratio: float = 0.05,
) -> list[Path]:
    """Render the map embedded in ``map_path`` and crop out one PNG per state.

    Returns the list of written file paths.
    """
    map_text = map_path.read_text(encoding="utf-8")
    svg_text = extract_svg(map_text)
    states = parse_states(map_text)
    regions = find_state_regions(svg_text, states)
    if not regions:
        raise ValueError("No state regions found in map")

    full_image = render_full_map(svg_text, zoom=zoom)
    img_w, img_h = full_image.size

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for region in regions:
        minx, miny, maxx, maxy = region.bbox
        pad_x = (maxx - minx) * padding_ratio
        pad_y = (maxy - miny) * padding_ratio

        left = max(0, int((minx - pad_x) * zoom))
        top = max(0, int((miny - pad_y) * zoom))
        right = min(img_w, int((maxx + pad_x) * zoom))
        bottom = min(img_h, int((maxy + pad_y) * zoom))

        crop = full_image.crop((left, top, right, bottom))
        out_path = output_dir / f"{region.id:02d}_{sanitize_filename(region.name)}.png"
        crop.save(out_path)
        written.append(out_path)

    return written
