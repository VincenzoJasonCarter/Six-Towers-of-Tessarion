"""The Barracks' item index: data/items.yaml as the items.json charasheet reads.

charasheet looks for items.json next to itself (at /barracks/items.json here)
to offer these in its Weapons and Equipment panels. The format, version 1:

    {
      "version": 1,
      "currency": "CB",
      "weapons": [
        {"id", "name", "category", "description", "value",
         "dice", "versatile"?, "bonus", "damageType", "ability", "properties", "emoji"?}
      ],
      "equipment": [
        {"id", "name", "category", "description", "value", "kind", "emoji"?}
      ]
    }

dice and versatile are damage dice without any modifier; the wielder adds
their ability modifier (ability: "str" or "dex") and bonus. value is in
currency and may be null. ids stay the same across releases.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "items.yaml"
VERSION = 1


def describe(item):
    return "\n".join(part for part in (item.get("stat"), item.get("power")) if part)


def build_index():
    weapons, equipment = [], []
    for item in yaml.safe_load(SOURCE.read_text(encoding="utf-8")):
        if item.get("hidden"):
            continue
        entry = {
            "id": item["id"],
            "name": item["name"],
            "category": item.get("category"),
            "description": describe(item),
            "value": item.get("market_value"),
        }
        if item["kind"] == "weapon":
            damage = item["damage"]
            entry["dice"] = damage["dice"]
            if damage.get("versatile"):
                entry["versatile"] = damage["versatile"]
            entry["bonus"] = damage.get("bonus", 0)
            entry["damageType"] = damage["type"]
            entry["ability"] = damage["ability"]
            entry["properties"] = item.get("properties", [])
            target = weapons
        else:
            entry["kind"] = item["kind"]
            target = equipment
        if item.get("emoji"):
            entry["emoji"] = item["emoji"]
        target.append(entry)
    return {"version": VERSION, "currency": "CB", "weapons": weapons, "equipment": equipment}


def items_json():
    return json.dumps(build_index(), ensure_ascii=False, indent=2) + "\n"
