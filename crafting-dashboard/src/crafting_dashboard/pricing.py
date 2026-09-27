from .models import Item


def price_item(item: Item, unit_costs: dict[str, float | None]) -> None:
    """Fills in material_cost, cost_gap and margin on `item` in place.

    A material missing from unit_costs (OTMV not listed in Ch.10) sets
    cost_gap=True instead of being guessed at — the resulting material_cost
    is then a partial (lower-bound) figure.
    """
    total = 0.0
    gap = False
    for material, qty in item.materials:
        unit_cost = unit_costs.get(material)
        if unit_cost is None:
            gap = True
        else:
            total += unit_cost * qty

    item.material_cost = round(total, 2)
    item.cost_gap = gap
    item.margin = (
        round(item.market_value - item.material_cost, 2)
        if item.market_value is not None
        else None
    )


def price_all(items: list[Item], unit_costs: dict[str, float | None]) -> None:
    for item in items:
        price_item(item, unit_costs)
