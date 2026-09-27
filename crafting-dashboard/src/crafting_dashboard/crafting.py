from datetime import datetime, timezone

from .models import Inventory, Item


class CraftError(Exception):
    """Raised when an item can't be crafted — carries the shortfall so the
    caller can report exactly what's missing."""

    def __init__(self, shortfall: dict[str, float]):
        self.shortfall = shortfall
        missing = ", ".join(f"{mat} x{qty:g}" for mat, qty in shortfall.items())
        super().__init__(f"Not enough materials - missing {missing}")


def missing_materials(item: Item, inventory: Inventory, qty: int = 1) -> dict[str, float]:
    """Returns {material: shortfall_amount} for whatever the inventory doesn't
    cover. Empty dict means the item is craftable right now."""
    shortfall = {}
    for material, per_unit_qty in item.materials:
        needed = per_unit_qty * qty
        have = inventory.materials.get(material, 0.0)
        if have < needed:
            shortfall[material] = round(needed - have, 4)
    return shortfall


def craft_item(item: Item, inventory: Inventory, qty: int = 1) -> None:
    """Mutates `inventory` in place: deducts materials and appends a crafted
    log entry. Raises CraftError (inventory left untouched) if short."""
    shortfall = missing_materials(item, inventory, qty)
    if shortfall:
        raise CraftError(shortfall)

    for material, per_unit_qty in item.materials:
        needed = per_unit_qty * qty
        remaining = round(inventory.materials.get(material, 0.0) - needed, 4)
        if remaining <= 0:
            inventory.materials.pop(material, None)
        else:
            inventory.materials[material] = remaining

    inventory.items[item.name] = inventory.items.get(item.name, 0) + qty
    inventory.crafted_log.append({
        "item": item.name,
        "qty": qty,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
