# The Threadmint Bestiary

An in-world encyclopedia of everything in `../data/enemies.yaml`, kept like
the vault under the Threadmint it is: the home page is a stone wall of iron
cells, a block per region under a brass plaque. Click one and it lifts out of the grid and flies to
the middle of the screen, turning over as it goes: its back is the entry, with lore,
habitat and field notes on top and the DM material (stat blocks, tactics,
loot, source contradictions) in a panel underneath. Closing it (← All entries,
Esc, a click outside it, or the browser's Back) turns it face up and flies it
back into its gap.

## Running it

From the repo root:

```
make bestiary                 # or: uv run bestiary/serve.py
```

The bestiary starts on http://127.0.0.1:8766/ and opens it in your browser.
It rereads `enemies.yaml` on every load, and an open page reloads itself
when you save `enemies.yaml`, the page files (`template.html`, `style.css`,
`app.js`) or anything in `images/`. If
the YAML has an error, the page shows it in a banner until you fix it.
Options: `--port 9000`, `--no-browser` (via `make bestiary ARGS="..."`).

To get a single file you can open without the server, or send to someone:

```
make bestiary-build           # or: uv run bestiary/build.py
```

That writes `bestiary.html`, a snapshot. It does not update itself; run the
command again after editing `enemies.yaml`.

## Using it

- Search matches names, places, factions and lore text.
- The tabs split entries into Creatures (`enemies`), Rumoured
  (`enemy_concepts`) and Factions & Figures (`unstatted_opposition`).
- Untick **DM material** to hide stats, tactics and category badges before
  showing the screen to players. The page remembers the setting.
- On an open card, ‹ › (or ← / →) slide to the previous or next entry in
  the grid.
- Untick **Animate cards** to open and close cards without the flight and
  the turn. The page remembers that too.
- Every entry has its own link (`#setanta`); opening one lays its card
  straight on the table.

## Portraits

Until an entry has a picture, it shows a placeholder in its cell. A
creature is a pair of eyes in the dark behind bars, in its region's colour
(each entry's sit and blink in their own place and time); a rumour is the
same seen through drifting fog; a faction or figure is a silhouette against
a height chart. Its designation hangs on a brass tag (see below). The
**Animate cards** switch also stills the blinking, the fog and the cage by
the title. To give it a real one, put an image named after
its `id` in `images/`, e.g. `images/setanta.png`. PNG, JPG, WebP, GIF and
SVG all work, and the live page picks it up without a restart. Square images
look best.

## Designations

Every entry has a containment designation, SCP-fashion: its region's code
(CRW Crownweave, SKL Skyloom, NRH Northreach, EMB Emberweave, STW Stormwake,
THV Thal'vireth) and four digits, with `PoI-` (person of interest) in front
for factions and figures: `NRH-0417`, `PoI-CRW-2281`. A rumour's tag carries
a `?`. It's on the cell's tag and under the entry's name, and the search
finds it.

The digits come from the entry's `id`, so an entry keeps its designation as
others are added or removed (it changes only if the `id` or region does). To
choose one by hand, say because the lore names it, give the entry a
`serial:`, e.g. `serial: NRH-0001`; that's used exactly as written.

## Adding an entry

Give it an `id`, a `name`, a `region` ("Weave · Place"), and a `lore` block:

```yaml
    region: Northreach · Deepdelve Faces
    lore:
      classification: Mutant — Red Mana saturation
      habitat: >-
        Where it is found.
      entry: >-
        First paragraph.

        Second paragraph (a blank line starts a new one).
      field_notes:
        - >-
          “A quote from someone in the world.” — who said it
```

Entries without a `lore` block stay in `enemies.yaml` but are left out of
the bestiary. `████` in any text is drawn as a redaction bar.

## Files

```
serve.py        live server (stdlib http.server)
build.py        static export to bestiary.html
core.py         shared: reads enemies.yaml, finds images, fills the template
template.html   page markup; core.py fills in the data
style.css       page styles
app.js          rendering script
images/         optional portraits, named <id>.<ext>
bestiary.html   static export output (one file: styles and script inlined)
```
