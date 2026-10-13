# The Threadmint Market

Everything in `../data/items.yaml` as the Merchant's Guild would sell it.
The home page is a market hall with an aisle for each kind of goods: 1 Arms,
2 Armour & Shields, 3 Provisions, 4 Raw Stock and 5 the Workshop (tools and
forge hire). A beam runs across the hall with a numbered sign hung from it
for each aisle, banded in the aisle's colour and saying what's down it; click
one to walk that aisle (the page remembers the last one), and at the far end
of an aisle the next one is a click away. A search looks down every aisle at
once: each sign says how many matches are down it, and a click on it jumps to
them. An aisle is a run of wooden shelving, its number and its name on a
brass plaque on the head board. Down it, each tier has a shelf of its own, named on a plate in its
metal (bronze for Tier I, steel for Tier II, blued Crucible steel for
Tier III, plain paper for untiered supplies) and parted from the next by a heavier fixed board. Every item
stands on a plank as a paper tag edged in its tier's colour, showing its
picture, its stat line (up to three lines; the slip has the rest) and its
price in Crownsblood (CB). Click a tag to open
the item's slip: its rules, its upgrade path, its recipe priced material by
material, and what the materials cost against buying it made. A material's
slip lists the recipes that use it, and a tool's slip the recipes it works.

## Running it

From the repo root:

```
make market                   # or: uv run market/serve.py
```

The Market starts on http://127.0.0.1:8770/ and opens in your browser. It
rereads `items.yaml` on every load, and an open page reloads itself when you
save `items.yaml`, Ch.10 of the lore-book, an icon, or the page files
(`template.html`, `style.css`, `app.js`). If the YAML has an error, the page
shows it in a banner until you fix it.
Options: `--port 9000`, `--no-browser` (via `make market ARGS="..."`).

To get a single file you can open without the server, or send to someone:

```
make market-build             # or: uv run market/build.py
```

That writes `market.html`, a snapshot (about 340 KB, icons included).
Run the command again after editing `items.yaml`. `web/build.py` puts it at
`/market/` on the public site.

## The quartermaster

Talvender Prolyman, the stall's quartermaster (a retired adventurer: twenty-two
years on the road, eleven behind this counter), stands behind his own counter
beside the intro, scales and abacus in front of him. Click him and he talks:
who he is and why he stopped, what to buy for each calling (Aegisbound, Archer,
Gunman, crystal mage, or just starting out), how Guild and local prices work,
market gossip, stories from the road, and what might be coming in. Each line
comes with replies to pick from, as with Hessa at the hub's front desk.

He also has a word for every item: it sits at the top of the item's slip. At
the top of the tally he gives his opinion of the purchase, the most pressing
thing first: a bow with no arrows, a gun with nothing to load, a two-handed
weapon bought with a shield, a month of rations, a local market's markup, a
foreign coin, or just the size of the bill. Adding things from the shelves
gets a word now and then, and when the total passes 20 and 50 CB. His eyes
follow the pointer, he mutters if left alone, and he'd rather you didn't touch
his scales.

Everything he says is written out in `keeper.js` (the comment at the top
explains the format, the same as the hub's `clerk.js`). An item with no line
of its own gets a line for its kind, so new items in `items.yaml` don't need
one, but deserve one. He uses no AI model and needs no network.

## The tally

The **+** on a tag (or **Add to the tally** on its slip) puts the item on
the tally, the button at the top right. The tally adds up the purchase at
the Official Value and prices it the way Ch.9 (Economy of Tessarion) says:

- **Guild market**: the Official Value, to the nearest CB, halves up, at
  least 1 CB.
- **Local market**: the Official Value times the markup for its kind of
  market (Loft Market × 2, street stall × 3, frontier trader × 4, Underweave
  outlet × 5), times 2 more if **Scarce here** is ticked (goods the region
  brings in from elsewhere, like wood in Northreach), always rounded up. The
  **Markup** box takes a haggled or insulted figure (never below × 1);
  picking a kind of market again resets it.

**Paying in** converts the total into another nation's coin at the official
Trade Unit rate (also Ch.9), before the Guild changers' 2–3% fee. **Copy as
text** copies the list and the total, for pasting into a chat. The tally,
the market, the markup and the coin are remembered in the browser.

## Where the data comes from

- **Items, rules, recipes, prices**: `data/items.yaml`, the same file the
  Barracks' `items.json` is made from (see `barracks/README.md`). Entries
  marked `hidden: true` stay out of the Market too. An item with
  `market_value: null` shows as "Not stocked" and can't go on the tally.
- **Pictures**: `icons/<id>.svg`, one per item, named after its `id` in
  `items.yaml` (a `.png`, `.webp` or `.jpg` works too). They are cartoon
  vectors drawn on a 96 × 96 grid: chunky shapes with a 4px dark outline
  (`#2b1d12`), cel shading (a hard darker band along each shape's lower
  right, with the light from the top left), white glints, and a soft shadow
  underneath. Tier 1 metal is dull, notched and rust-spotted; Tier 2 is clean
  steel with brass fittings and a sparkle. An item without one shows its
  `emoji` instead. The live page picks up a new or changed icon by itself.

Ch.10 of the lore-book (Official Tessarion Market Value) is checked against
`items.yaml`, matching names while ignoring anything in brackets ("Impure
Ingot (150 g)" is the Impure Ingot). A price that differs, an item
Ch.10 sells that `items.yaml` lacks, or a recipe that calls for a material
`items.yaml` doesn't list is printed by `build.py` as a warning, and listed
under **Data notes** at the bottom of the page on the live server (never in
the export).

## Files

```
serve.py        live server (stdlib http.server)
build.py        static export: market.html
core.py         shared: reads items.yaml, the icons and Ch.10, checks Ch.10 against items.yaml
icons/          one cartoon SVG per item, named after its id
template.html   page markup; core.py fills in the data
style.css       page styles
app.js          the aisles, the item slips and the tally
keeper.js       Talvender, the quartermaster: everything he says, and when
market.html     the static export
```
