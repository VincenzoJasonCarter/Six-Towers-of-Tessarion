import argparse
from pathlib import Path

from .api import CraftingApp
from .loader import DEFAULT_DATA_DIR
from .server import serve


def main():
    parser = argparse.ArgumentParser(
        description="Tessarion Crafting Simulator - opens the crafting GUI in your browser."
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing items.yaml / materials.yaml / inventory/.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab automatically.")
    args = parser.parse_args()

    app = CraftingApp(Path(args.data_dir))
    serve(app, args.host, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
