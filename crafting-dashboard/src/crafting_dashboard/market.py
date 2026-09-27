import math

from .models import Inventory

MARKETS = ("guild", "street")
MINIMUM_CHARGE = 1


class MarketError(Exception):
    pass


def quote(unit_cost: float, qty: float, market: str) -> tuple[float, int]:
    """Returns (raw OTMV total, price actually charged) per Ch.9 §IV rounding."""
    raw = round(unit_cost * qty, 4)
    if market == "guild":
        charged = math.floor(raw + 0.5)
    elif market == "street":
        charged = math.ceil(raw)
    else:
        raise MarketError(f"Unknown market: {market!r}")
    return raw, max(charged, MINIMUM_CHARGE)


def buy(
    inventory: Inventory,
    material: str,
    qty: int,
    unit_costs: dict[str, float | None],
    market: str,
) -> int:
    """Deducts CB and adds the material. Returns the CB charged."""
    if material not in unit_costs:
        raise MarketError(f"Unknown material: {material!r}")
    unit_cost = unit_costs[material]
    if unit_cost is None:
        raise MarketError(f"{material} has no OTMV in Ch.10, so no market sells it.")

    _, charged = quote(unit_cost, qty, market)
    if charged > inventory.currency_cb:
        raise MarketError(f"Not enough CB: {material} x{qty} costs {charged} CB, you have {inventory.currency_cb:g} CB.")

    inventory.currency_cb = round(inventory.currency_cb - charged, 2)
    inventory.materials[material] = round(inventory.materials.get(material, 0.0) + qty, 4)
    return charged
