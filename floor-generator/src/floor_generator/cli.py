# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------

import argparse
from pathlib import Path

from . import generate_temporal_floor


def main():

    parser = argparse.ArgumentParser(
        description="Generate a Thal'Vireth temporal floor."
    )

    parser.add_argument("--size", type=int, default=20)
    parser.add_argument("--n-zones", type=int, default=5)
    parser.add_argument("--zone-min", type=int, default=2, help="Min zone width/height (m).")
    parser.add_argument("--zone-max", type=int, default=4, help="Max zone width/height (m).")
    parser.add_argument("--min-gap", type=int, default=1)
    parser.add_argument("--n-walls", type=int, default=10, help="Number of wall obstacles (edge segments, not tiles).")
    parser.add_argument("--wall-min", type=int, default=1, help="Min wall segment length (grid edges).")
    parser.add_argument("--wall-max", type=int, default=3, help="Max wall segment length (grid edges).")
    parser.add_argument("--n-blocks", type=int, default=3, help="Number of full-tile obstacles.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pixels-per-meter", type=int, default=32)
    parser.add_argument("--grid-pixels", type=int, default=100, help="VTT grid square size in px.")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--show", action="store_true", help="Also open an interactive preview window.")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    basename = f"floor_seed{args.seed}"
    render_path = output_dir / f"{basename}.png"
    texture_path = output_dir / f"{basename}_texture.png"
    vtt_path = output_dir / f"{basename}_scene.json"

    generate_temporal_floor(
        size=args.size,
        zone_size_range=(args.zone_min, args.zone_max),
        n_zones=args.n_zones,
        min_zone_gap=args.min_gap,
        n_wall_segments=args.n_walls,
        wall_length_range=(args.wall_min, args.wall_max),
        n_obstacle_blocks=args.n_blocks,
        seed=args.seed,
        show=args.show,
        pixels_per_meter=args.pixels_per_meter,
        grid_pixels=args.grid_pixels,
        export_render=str(render_path),
        export_texture=str(texture_path),
        export_vtt=str(vtt_path),
    )

    print(f"Render:  {render_path}")
    print(f"Texture: {texture_path}")
    print(f"VTT:     {vtt_path}")


if __name__ == "__main__":
    main()
