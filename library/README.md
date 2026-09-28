# The Threadmint Library

The chapters in `../lore-book/` as a website of books. The home page is one
tall bookcase against a papered wall, with a bay for each subject (its name on
a brass label on the plank above), and every chapter is a book on a shelf,
bound in its subject's colour (Thal'vireth green, Skyloom blue, and so on).
The free end of each shelf holds an ornament: a globe, crystals, a candle.
Click a book to open it. Books open to two pages at a time, with page turns,
running heads and page numbers.

## Running it

From the repo root:

```
make library                  # or: uv run library/serve.py
```

The library starts on http://127.0.0.1:8767/ and opens in your browser. It
rereads the lore-book on every load, and an open page reloads itself when
you save a chapter, `catalogue.yaml` or the page files (`template.html`,
`style.css`, `app.js`).
Options: `--port 9000`, `--no-browser` (via `make library ARGS="..."`).

To put it on the web:

```
make library-build            # or: uv run library/build.py
```

That writes `library/site/`: an `index.html` (about 145 KB gzipped) and an
`images/` folder. Upload the folder to any static host (GitHub Pages,
Netlify, Cloudflare Pages). A reader downloads a book's pictures only when
they open that book. Each image's file name carries a hash of its contents,
so the host can cache them for as long as it likes. The folder is rebuilt
from scratch each time and isn't committed to git.

For one file you can open without a server, or send to someone:

```
make library-build ARGS="--single-file"
```

That writes `library.html` (about 1.6 MB, or 0.9 MB zipped) with every
picture embedded.

Both are snapshots: run the command again after editing the lore-book. Both
also re-encode the lore-book's PNGs as WebP (about 3.2 MB down to 0.7 MB).
Each picture gets the lowest quality that stays within 40 dB PSNR of the
original, which the eye can't tell apart. Pictures with transparency are
stored losslessly. The PNGs in `lore-book/` are left as they are, and the
live server still shows them. `TARGET_PSNR` in `core.py` sets the bar.

## Reading

Clicking a book pulls it off the shelf: it slides out, turns from spine to
cover as it comes to the middle of the screen, and opens onto its endpaper
and title page. Going back to the library (← Library, Esc or the browser's
Back) plays it in reverse: the book closes, turns spine-on and slides back
into its gap. Click anywhere to skip either one. Ctrl/Cmd-click opens a book
in a new tab without it.

Turning a page lifts it by the outer edge and rolls it over the spine, bending
like paper, with the next page printed on its back. The **Animate books** switch on the library page turns off the pulling
out and the page flips. It is remembered in the browser, and it is on unless
switched off there, whatever the system's reduce-motion setting says.

- **← / →**, Page Up / Page Down, the space bar, the side arrows or the
  slider turn pages (the slider jumps without flipping). On a phone, swipe or
  tap the edge of the page.
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
bay and gets a band of Crownweave's colour at the top of each spine.
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
build.py         static export: library/site/ (or library.html with --single-file)
core.py          shared: reads the lore-book and catalogue, renders markdown
catalogue.yaml   shelves, colours, spine titles
template.html    page markup; core.py fills in the data
style.css        page styles
app.js           the bookcase and the book reader
site/            static export output (index.html + images/), not committed
library.html     --single-file output (styles, script and images inlined)
```
