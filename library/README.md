# The Threadmint Library

The chapters in `../lore-book/` as a website of books. The home page is a
wall of bookcases, one per subject, and every chapter is a book on a shelf,
bound in its subject's colour (Thal'vireth green, Skyloom blue, and so on).
Click a book to open it. Books open to two pages at a time, with page turns,
running heads and page numbers.

## Running it

From the repo root:

```
make library                  # or: uv run library/serve.py
```

The library starts on http://127.0.0.1:8767/ and opens in your browser. It
rereads the lore-book on every load, and an open page reloads itself when
you save a chapter, `catalogue.yaml` or `template.html`.
Options: `--port 9000`, `--no-browser` (via `make library ARGS="..."`).

To get a single file you can open without the server, or send to someone:

```
make library-build            # or: uv run library/build.py
```

That writes `library.html` (about 5 MB, since every image is embedded). It
is a snapshot: run the command again after editing the lore-book.

## Reading

Clicking a book pulls it off the shelf: it slides out, turns from spine to
cover as it comes to the middle of the screen, and opens onto its endpaper
and title page. Going back to the library (← Library, Esc or the browser's
Back) plays it in reverse: the book closes, turns spine-on and slides back
into its gap. Click anywhere to skip either one. Ctrl/Cmd-click opens a book
in a new tab without it, and the **Animate books** switch on the library
page turns both off.

- **← / →**, Page Up / Page Down, the space bar, the side arrows or the
  slider turn pages. On a phone, swipe or tap the edge of the page.
- **Contents** jumps to any heading. **Scroll** switches to one long page
  (better for looking things up at the table). **A− / A+** change the text
  size. The page remembers all three.
- Each book remembers where you stopped reading.
- Esc goes back to the shelves.
- Links: `#thalvireth` opens a book, `#thalvireth/overview` opens it at a
  heading.

On the shelves, the colour key highlights one subject, **In chapter order**
lines every book up 1–23, and search matches the full text of every volume.
Opening a book from the search results highlights the matches, and **Next ↓**
steps through them.

## Shelves and colours

`catalogue.yaml` decides which shelf each chapter sits on, and so its colour.
Chapters are named by filename without the number and `.md`
(`17-thalvireth.md` → `thalvireth`). To add a chapter, drop the file in
`lore-book/` and list its name under a shelf. Until you do, it sits on an
"Uncatalogued" shelf in plain cloth, and nothing breaks.

A shelf with `part_of: crownweave` (the four Weaves) stands in Crownweave's
bookcase and gets a band of Crownweave's colour at the top of each spine.
`spine_titles` gives shorter spine text for long titles.

## What it fixes up from the Google Docs export

- The export put every image definition at the end of chapter 23, so images
  are pooled from all chapters and resolved wherever they are referenced.
- `$...$` equations (chapter 22) are rendered with KaTeX, loaded from a CDN.
  Offline, the raw TeX shows instead.
- A heading repeating the chapter title near the top is dropped, because the
  title page already shows it.
- Table rows with only the first cell filled ("WEAPONS (TIER I)") span the
  whole row, and empty trailing rows are removed.
- `████` is drawn as a redaction bar, as in the bestiary.

## Files

```
serve.py         live server (stdlib http.server)
build.py         static export to library.html
core.py          shared: reads the lore-book and catalogue, renders markdown
catalogue.yaml   shelves, colours, spine titles
template.html    page layout, styles and the book reader
library.html     static export output
```
