# The Threadmint Bestiary

An in-world encyclopedia of everything in `../data/enemies.yaml`. The home page
is a grid of portrait cards. Click one and it lifts out of the grid and flies to
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
- On an open card, ‹ › (or ← / →) turn to the previous or next entry in
  the grid.
- Untick **Animate cards** to open and close cards without the flight and
  the turn. The page remembers that too.
- Every entry has its own link (`#setanta`); opening one lays its card
  straight on the table.

## Portraits

Until an entry has a picture, it shows a placeholder: its initials on a
background tinted by region. To give it a real one, put an image named after
its `id` in `images/`, e.g. `images/setanta.png`. PNG, JPG, WebP, GIF and
SVG all work, and the live page picks it up without a restart. Square images
look best.

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
