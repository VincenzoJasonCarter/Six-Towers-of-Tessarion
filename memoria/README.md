# The Threadmint Memoria

The museum of Tessarion's history, built from `../data/memoria.yaml` and kept
like the rest of the Threadmint's halls. The page is a gallery wall of plaster
panels, lamplit from above. At the top are the intro and a brass-rimmed plan of
the building: the rotunda over the Meridian Spire, a wing toward each
Tower-nation, and the Hall of Absences beneath. Below that, each room has its
name on a brass plate bolted to a rail in the room's colour, the opening of its
wall text, and a row of display cases. Each case is a walnut-framed vitrine in
the room's colours, with the object under a spotlight, a brass accession tag and
a pinned label. Click one and its placard opens, framed like the case, with the
case beside it.

## Running it

From the repo root:

```
make memoria                  # or: uv run memoria/serve.py
```

The Memoria starts on http://127.0.0.1:8769/ and opens in your browser. It
rereads `memoria.yaml` on every load, and an open page reloads itself (at the
same place) when you save `memoria.yaml` or the page's files (`template.html`,
`style.css`, `app.js`). If the YAML has a mistake, the page shows it in a
banner until you fix it.
Options: `--port 9000`, `--no-browser` (via `make memoria ARGS="..."`).

For a single file you can open without the server, or send to someone:

```
make memoria-build            # or: uv run memoria/build.py
```

That writes `memoria.html`, a snapshot. Run it again after editing `memoria.yaml`.

## Using it

- The room chips, or a room on the plan, show one room. **All rooms**
  shows the lot.
- Search matches names, accession numbers, origins and the placards' text.
- On a placard, **‹ Previous** / **Next ›** (or ← / →) go through the whole
  collection in order, each room's wall text first. Esc or a click outside
  closes it.
- **Read the wall text ›** opens a room's full wall text, with its exhibits
  listed.
- Untick **Animate** to still the pulsing coins, the glows and the placard's
  entrance. The page remembers it.
- Every exhibit has its own link (`#the-empty-case`). A room's wall text is
  `#wall-` plus its id (`#wall-thalvireth`).

## Adding and changing exhibits

Everything is in `data/memoria.yaml`; the comment at its top explains each
field. Exhibits appear in their room in the order the file lists them.
Accession numbers (`TM-W-03`) come from the room's `code` and the exhibit's
place in it, unless you give one. The rotunda's exhibit with
`place: centre` comes first in its row. A wing's `bearing` sets where it is on
the plan.

How an exhibit is drawn in its case is its `model`: a `type`, plus that type's
colours.

| type | shown | options |
| --- | --- | --- |
| `coin` | on a stand | `metal`, `streak`, `rim`, `runes`, `pulse` |
| `crystal` | on a stand | `colour`, `glow`, `ledger`, `prismatic` |
| `pick`, `sickle`, `adze` | on a stand | `stain` (pick), `worn` (sickle) |
| `medallion` | on a stand | `metal`, `stone` |
| `shard`, `amber` | on a stand | `colour`, `scroll` (shard) |
| `thread`, `cord` | on a stand | `colour` |
| `hourglass` | on a stand | `sand` |
| `document` | on a stand, or hung if `framed` | `ink`, `signatures`, `blood` (which ones, from 0) |
| `absence` | on a stand | none |
| `empty` | nothing, under a stronger light | none |
| `banner`, `frame`, `plate`, `tidemarker`, `blade` | hung under a picture light | `left`/`right` (banner), `metal` |
| `mirror`, `chair`, `strikeplate`, `sink`, `armour` | on a dais | their colours |

A new kind of object needs a picture in `art()` in `app.js` (an SVG, 120 by
120) and, if it isn't shown on a stand, an entry in `MOUNT`.

A room's `colours` set its case interiors (`wall`), rail and dais trim
(`trim`) and spotlights (`light`). Its `intro` is its wall text; the first
paragraph is shown on the page. The Hall of Absences' `dates` become its
undescribed cases.

## Files

```
serve.py        live server (stdlib http.server; reads memoria.yaml on every load)
build.py        static export: memoria.html
core.py         shared: reads and checks memoria.yaml, fills in the page
template.html   page markup
style.css       page styles
app.js          the rooms, the cases and their pictures, the plan, the placard
memoria.html    static export output
```
