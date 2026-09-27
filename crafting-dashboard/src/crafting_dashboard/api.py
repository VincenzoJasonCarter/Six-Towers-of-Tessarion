import math
import random
import threading
from pathlib import Path

from .crafting import CraftError, craft_item, missing_materials
from .inventory import is_valid_character, list_characters, load_inventory, save_inventory
from .loader import load_items, load_material_costs
from .market import MARKETS, MarketError, buy
from .models import Inventory, Item
from .pricing import price_all
from .resonance import OUTCOME_INFO, RARITY, RESONANCE_DC, ResonanceBuild, simulate_many, simulate_once

OUTCOME_ORDER = [
    "Resonant Apex", "Full Resonance", "Threshold",
    "Dim Resonance", "Fractured Emergence", "Rejection",
]
MAX_SIM_ROLLS = 100_000


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, **detail):
        super().__init__(message)
        self.message = message
        self.status = status
        self.detail = detail


def _require(payload: dict, key: str):
    if key not in payload:
        raise ApiError(f"Missing field: {key}")
    return payload[key]


def _int_in_range(value, name: str, lo: int, hi: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        raise ApiError(f"{name} must be a whole number.")
    value = int(value)
    if not lo <= value <= hi:
        raise ApiError(f"{name} must be between {lo} and {hi}.")
    return value


def _number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ApiError(f"{name} must be a number.")
    return float(value)


def _choice(value, name: str, options) -> str:
    if value not in options:
        raise ApiError(f"{name} must be one of: {', '.join(options)}.")
    return value


class CraftingApp:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.unit_costs = load_material_costs(data_dir)
        self.items = load_items(data_dir)
        price_all(self.items, self.unit_costs)
        self.items_by_name = {it.name: it for it in self.items}
        self._lock = threading.Lock()
        self._rng = random.Random()

    # --- helpers -----------------------------------------------------------

    def _character(self, payload_or_name) -> str:
        name = payload_or_name if isinstance(payload_or_name, str) else _require(payload_or_name, "character")
        if not isinstance(name, str) or not is_valid_character(name):
            raise ApiError("Character names may only use letters, numbers, - and _ (max 40).")
        return name

    def _item(self, name) -> Item:
        item = self.items_by_name.get(name)
        if item is None:
            raise ApiError(f"Unknown item: {name!r}", status=404)
        return item

    def _item_view(self, item: Item, inventory: Inventory) -> dict:
        shortfall = missing_materials(item, inventory)
        max_craftable = min(
            (math.floor(inventory.materials.get(mat, 0.0) / qty + 1e-9) for mat, qty in item.materials),
            default=0,
        )
        return {
            "name": item.name,
            "emoji": item.emoji,
            "category": item.category,
            "stat": item.stat,
            "power": item.power,
            "tools": item.tools,
            "craft_time_hrs": item.craft_time_hrs,
            "materials": [
                {
                    "name": mat,
                    "qty": qty,
                    "unit_cost": self.unit_costs.get(mat),
                    "have": inventory.materials.get(mat, 0.0),
                }
                for mat, qty in item.materials
            ],
            "material_cost": item.material_cost,
            "cost_gap": item.cost_gap,
            "market_value": item.market_value,
            "margin": item.margin,
            "upgrade_from": item.upgrade_from,
            "upgrade_gap": item.upgrade_gap,
            "craftable": not shortfall,
            "missing": shortfall,
            "max_craftable": max_craftable,
            "owned": inventory.items.get(item.name, 0),
        }

    def _state(self, inventory: Inventory) -> dict:
        characters = list_characters(self.data_dir)
        if inventory.character not in characters:
            characters = sorted(characters + [inventory.character])
        return {
            "character": inventory.character,
            "characters": characters,
            "inventory": {
                "currency_cb": inventory.currency_cb,
                "materials": inventory.materials,
                "items": inventory.items,
                "crafted_log": list(reversed(inventory.crafted_log[-15:])),
            },
            "items": [self._item_view(it, inventory) for it in self.items],
            "materials": [{"name": n, "unit_cost": c} for n, c in self.unit_costs.items()],
            "resonance": {
                "dc": RESONANCE_DC,
                "rarity": RARITY,
                "outcomes": OUTCOME_INFO,
                "order": OUTCOME_ORDER,
            },
        }

    def _mutate(self, character: str, action):
        """Load -> apply action -> save, under a lock so two browser tabs
        can't interleave writes to the same inventory file."""
        with self._lock:
            inventory = load_inventory(character, self.data_dir)
            message = action(inventory)
            save_inventory(inventory, self.data_dir)
            return {"message": message, "state": self._state(inventory)}

    # --- endpoints ---------------------------------------------------------

    def state(self, character: str) -> dict:
        character = self._character(character)
        return self._state(load_inventory(character, self.data_dir))

    def craft(self, payload: dict) -> dict:
        character = self._character(payload)
        item = self._item(_require(payload, "item"))
        qty = _int_in_range(payload.get("qty", 1), "qty", 1, 999)

        def action(inv: Inventory) -> str:
            try:
                craft_item(item, inv, qty=qty)
            except CraftError as e:
                raise ApiError(str(e), shortfall=e.shortfall)
            return f"Crafted {item.name} ×{qty}."

        return self._mutate(character, action)

    def buy(self, payload: dict) -> dict:
        character = self._character(payload)
        material = _require(payload, "material")
        qty = _int_in_range(_require(payload, "qty"), "qty", 1, 999)
        market = _choice(payload.get("market", "guild"), "market", MARKETS)

        def action(inv: Inventory) -> str:
            try:
                charged = buy(inv, material, qty, self.unit_costs, market)
            except MarketError as e:
                raise ApiError(str(e))
            return f"Bought {material} ×{qty} for {charged} CB ({market} market)."

        return self._mutate(character, action)

    def add_material(self, payload: dict) -> dict:
        character = self._character(payload)
        material = _require(payload, "material")
        if material not in self.unit_costs:
            raise ApiError(f"Unknown material: {material!r}")
        qty = _number(_require(payload, "qty"), "qty")

        def action(inv: Inventory) -> str:
            new_qty = round(inv.materials.get(material, 0.0) + qty, 4)
            if new_qty < 0:
                raise ApiError(f"Can't remove more {material} than you have.")
            if new_qty == 0:
                inv.materials.pop(material, None)
            else:
                inv.materials[material] = new_qty
            verb = "Added" if qty >= 0 else "Removed"
            return f"{verb} {material} ×{abs(qty):g}."

        return self._mutate(character, action)

    def adjust_cb(self, payload: dict) -> dict:
        character = self._character(payload)
        amount = _number(_require(payload, "amount"), "amount")

        def action(inv: Inventory) -> str:
            new_total = round(inv.currency_cb + amount, 2)
            if new_total < 0:
                raise ApiError("CB can't go below 0.")
            inv.currency_cb = new_total
            return f"{'+' if amount >= 0 else ''}{amount:g} CB."

        return self._mutate(character, action)

    def resonate(self, payload: dict) -> dict:
        build = ResonanceBuild(
            power_rating=_int_in_range(_require(payload, "pr"), "pr", 1, 6),
            posture_mode=_choice(payload.get("posture", "single"), "posture", ("single", "dual")),
            tool_proficiency=bool(payload.get("tool_prof", False)),
            expert_tools=bool(payload.get("expert_tools", False)),
            location_bonus=_int_in_range(payload.get("location_bonus", 0), "location_bonus", 0, 15),
            prior_crafts=_int_in_range(payload.get("prior_crafts", 0), "prior_crafts", 0, 5),
            soulstone=_choice(payload.get("soulstone", "off-native"), "soulstone", ("native", "off-native", "hostile")),
            mixed_binding=bool(payload.get("mixed_binding", False)),
            currently_fractured=bool(payload.get("fractured", False)),
        )
        rolls = _int_in_range(payload.get("rolls", 0), "rolls", 0, MAX_SIM_ROLLS)

        response = {
            "dc": build.dc(),
            "rarity": RARITY[build.power_rating],
            "dice_count": build.power_rating + 1,
            "breakdown": [{"label": label, "value": value} for label, value in build.modifier_breakdown()],
            "total_modifier": build.total_modifier(),
            "fractured_emergence_start": build.fractured_emergence_start(),
        }

        if rolls == 1:
            r = simulate_once(build, self._rng)
            response["result"] = {
                "dice": r.dice,
                "dice_sum": r.dice_sum,
                "total": r.total,
                "diff": r.diff,
                "outcome": r.outcome,
                "info": OUTCOME_INFO[r.outcome],
            }
        elif rolls > 1:
            counts = simulate_many(build, rolls, self._rng)
            response["distribution"] = {
                band: round(100 * counts.get(band, 0) / rolls, 1) for band in OUTCOME_ORDER
            }
            response["rolls"] = rolls

        return response
