from dataclasses import dataclass, field


@dataclass
class Inventory:
    character: str
    currency_cb: float = 0.0
    materials: dict[str, float] = field(default_factory=dict)
    items: dict[str, int] = field(default_factory=dict)
    crafted_log: list[dict] = field(default_factory=list)


@dataclass
class Item:
    name: str
    emoji: str
    category: str
    stat: str
    power: str
    materials: list[tuple[str, float]]
    tools: str
    craft_time_hrs: float
    market_value: float | None = None
    upgrade_from: str | None = None
    upgrade_gap: bool = False

    # filled in by pricing.price_item()
    material_cost: float = 0.0
    cost_gap: bool = False
    margin: float | None = None
