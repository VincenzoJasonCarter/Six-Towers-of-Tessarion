import re
from pathlib import Path

import yaml

from .models import Inventory

# Character names become file names, so keep them to a safe character set.
CHARACTER_NAME = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def is_valid_character(name: str) -> bool:
    return bool(CHARACTER_NAME.match(name))


def _inventory_dir(data_dir: Path) -> Path:
    return data_dir / "inventory"


def _inventory_path(character: str, data_dir: Path) -> Path:
    if not is_valid_character(character):
        raise ValueError(f"Invalid character name: {character!r}")
    return _inventory_dir(data_dir) / f"{character}.yaml"


def list_characters(data_dir: Path) -> list[str]:
    inv_dir = _inventory_dir(data_dir)
    if not inv_dir.exists():
        return []
    return sorted(p.stem for p in inv_dir.glob("*.yaml") if is_valid_character(p.stem))


def load_inventory(character: str, data_dir: Path) -> Inventory:
    path = _inventory_path(character, data_dir)
    if not path.exists():
        return Inventory(character=character)

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return Inventory(
        character=character,
        currency_cb=raw.get("currency_cb", 0.0),
        materials=raw.get("materials") or {},
        items=raw.get("items") or {},
        crafted_log=raw.get("crafted_log") or [],
    )


def save_inventory(inventory: Inventory, data_dir: Path) -> Path:
    path = _inventory_path(inventory.character, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "currency_cb": inventory.currency_cb,
        "materials": inventory.materials,
        "items": inventory.items,
        "crafted_log": inventory.crafted_log,
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)

    return path
