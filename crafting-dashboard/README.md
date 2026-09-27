# Tessarion Crafting Simulator

A browser GUI for the crafting chapters of the lore book:

- **Workshop** (`07-crafting-book.md`): every craftable item, its recipe,
  and whether the current character can make it. Click **Craft** to use up
  the materials and add the item to their inventory.
- **Market** (`09-economy-of-tessarion.md`, `10-official-tessarion-market-value.md`):
  buy raw materials with CB, priced at OTMV with Guild or Street rounding.
- **Resonance Forge** (`08-on-resonant-crafting.md`): set up a resonance
  attempt (Power Rating, Posture, soulstone, modifiers), roll the pool, or
  simulate 10,000 attempts to see the odds of each Outcome Band.

## Running it

From this folder:

```
uv sync
uv run crafting-dashboard
```

From the repo root:

```
uv run --project crafting-dashboard crafting-dashboard
```

The app starts on http://127.0.0.1:8765/ and opens it in your browser.
Stop it with Ctrl+C. Options: `--port 9000`, `--no-browser`.

## Where state lives

Each character has one file, `data/inventory/<character>.yaml`, holding
their CB, materials on hand, crafted items, and craft log. Pick or create a
character from the top bar. The file is created on that character's first
change. These files are tracked in git, so party progress is saved with
the campaign.

Item recipes are in `data/items.yaml`, and raw material prices are in
`data/materials.yaml`. After editing either one, restart the app.

A material with `null` cost, or an item with `market_value: null`, has no
price in the source chapter. The market won't sell those materials; add
them as loot from the inventory panel instead.

## Not enforced

The simulator tracks materials, CB, and items only. Tool proficiency and
craft time are still handled at the table. Resonance Forge rolls are
what-ifs: they don't use up the base item or any soulstone.

## Layout

```
data/
  items.yaml               item and recipe data
  materials.yaml           raw material OTMV
  inventory/<char>.yaml    per-character state
src/crafting_dashboard/
  models.py                Item / Inventory dataclasses
  loader.py                YAML -> Item objects
  pricing.py               material cost and margin
  crafting.py              craft_item(): checks and uses up materials
  market.py                buying with Ch.9 rounding
  resonance.py             Ch.8 Resonance Pool and Outcome Bands
  inventory.py             inventory load/save
  api.py                   GUI actions: validates input, applies rules, saves
  server.py                local HTTP server (stdlib only, localhost)
  cli.py                   entry point
  static/                  index.html, app.js, style.css
```
