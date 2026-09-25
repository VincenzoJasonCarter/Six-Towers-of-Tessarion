import argparse
from pathlib import Path

from .segment import find_latest_map, segment_map_by_state


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Segment an Azgaar Fantasy Map Generator .map file into per-state mini maps."
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=None,
        help="Path to a .map file. Defaults to the latest .map in --map-dir.",
    )
    parser.add_argument(
        "--map-dir",
        type=Path,
        default=Path(__file__).resolve().parents[4] / "Map",
        help="Directory to search for the latest .map file when --map is omitted.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write mini maps to. Defaults to <map-dir>/segments/<map-stem>/.",
    )
    parser.add_argument("--zoom", type=float, default=4.0, help="Render scale factor (default: 4.0).")
    parser.add_argument(
        "--padding",
        type=float,
        default=0.05,
        help="Fractional padding added around each state's bounding box (default: 0.05).",
    )
    args = parser.parse_args()

    map_path = args.map or find_latest_map(args.map_dir)
    output_dir = args.output_dir or map_path.parent / "segments" / map_path.stem

    written = segment_map_by_state(map_path, output_dir, zoom=args.zoom, padding_ratio=args.padding)

    print(f"Segmented {map_path.name} into {len(written)} mini maps:")
    for path in written:
        print(f"  {path}")


if __name__ == "__main__":
    main()
