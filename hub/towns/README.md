# Town plans

One file per town, one folder per country. If a town has a file here, it has
a plan in the map room. `hub/plans.py` is the toolkit that draws them, and
`make atlas` builds them all before it draws the maps.

```
uv run hub/plans.py                 # every town
uv run hub/plans.py crownweave      # one country
uv run hub/plans.py fjerfi phais    # some towns (file names, with - for _)
```

## A town file

```python
TOWN = "Fjerfi"                # the town's name on the map: this is what links it to the atlas
EPITHET = "Seat of the Weave"
SPEC = { ... }                 # a description, laid out by plans.build()
```

`SPEC` gives:

- **The town's centre and extent.**
- **The ground:** the sea (which way it lies and how far off), a lake, a river, a hill.
- **Its structure:** walls, a plaza, the roads out of town, and ring roads.
- **Its landmarks:** each placed by an offset from the centre, roughly a metre per unit.
- **District names.**
- **The key:** `places`, each with its entry text and the lore-book chapter it comes from.

`plans.build()`'s docstring lists every key, and `fjerfi.py` is a good one to copy. The code fills in the rest: lanes, houses, fields and trees. It is seeded, so a plan only changes when its file does.

## Roads and river from the map

Set `"from_map": True` in `SPEC` and the town's roads and river come from the Azgaar map (the newest `map/*.map`): every road and trail leaves town in the direction it takes on the map, and the river comes in and goes out the way the map's does. The rest of the town is still generated.

- `"names": [{"dir": "W", "name": ..., "id": ...}]` names or links the map's roads. Each entry matches the road heading closest to `dir`, a compass point or a plan angle in degrees (0 east, 90 south). Roads with a name on the map get it automatically.
- `"river": {"at": (x, y), "width": ..., "bend": ..., "name": ...}` sets where the map's river passes the town centre and how it is drawn. `"river": False` leaves it out.

Every Crownweave town uses this. Places named in a town file should be places in that town: the Weaves are prefectures far across the island, not quarters of The Crown.

## More than SPEC can describe

A town that needs more than `SPEC` can describe can do either of these:

- Add an `"extra"` function to `SPEC`. Central District's shadow of the Loom and Skyfall Reach's rain work this way.
- Define `draw()` and draw the whole plan itself, as `thalvireth/nabireth.py` does.

Place everything where the lore-book says it is, and keep each entry to what the lore says, or to what the plan adds without contradicting it.
