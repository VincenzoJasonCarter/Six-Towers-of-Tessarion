from pathlib import Path

import yaml

from .models import Item

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_material_costs(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, float | None]:
    with open(data_dir / "materials.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_items(data_dir: Path = DEFAULT_DATA_DIR) -> list[Item]:
    with open(data_dir / "items.yaml", encoding="utf-8") as f:
        raw_items = yaml.safe_load(f)

    items = []
    for raw in raw_items:
        materials = [(name, float(qty)) for name, qty in raw["materials"]]
        items.append(Item(
            name=raw["name"],
            emoji=raw["emoji"],
            category=raw["category"],
            stat=raw["stat"],
            power=raw["power"],
            materials=materials,
            tools=raw["tools"],
            craft_time_hrs=raw["craft_time_hrs"],
            market_value=raw.get("market_value"),
            upgrade_from=raw.get("upgrade_from"),
            upgrade_gap=raw.get("upgrade_gap", False),
        ))
    return items
