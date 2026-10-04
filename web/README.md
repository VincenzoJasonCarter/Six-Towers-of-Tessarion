# The Threadmint on the web

The hub, the library, the bestiary, the Barracks and the Memoria as one
static site: the hub's reception hall at `/`, the library at `/library/`, the
bestiary at `/bestiary/`, the Barracks (charasheet) at `/barracks/` and the
Memoria at `/memoria/`.

## Building it

From the repo root:

```
make web-build                # or: uv run web/build.py
```

That runs `library/build.py`, `bestiary/build.py`, `barracks/build.py` and `memoria/build.py`
(charasheet's build for `/barracks/`, which needs Node, and skips itself when
charasheet/ hasn't changed since the last one), gathers their output
into `dist/` (not committed) and copies the hub's page files to its root.
The hub's page is marked `<body data-hosted>` there, so instead of asking
`hub/serve.py` which tools are running it shows every hall as open and loads
them from the folders next to it. Like them, it is a snapshot: rebuild after
editing the lore-book, `enemies.yaml` or `memoria.yaml`. It also rewrites
`bestiary/bestiary.html` and `memoria/memoria.html`, the same as
`make bestiary-build` and `make memoria-build`.

To look at it before deploying:

```
uv run --no-project python -m http.server 8790 -d dist
```

## Deploying to Vercel

`vercel.json` at the repo root has everything: Vercel installs uv, runs
`web/build.py` and serves `dist/`. Import the repo in Vercel and leave the
project settings (framework, build command, output directory) on their
defaults, since vercel.json overrides them. Every push to `main` then
redeploys.

`.vercelignore` limits the upload to what the build reads (`balance-patch.md`, `web/`,
`hub/`, `library/`, `bestiary/`, `memoria/`, `lore-book/`, `data/`, `charasheet/`, `barracks/`). If the build starts reading
another folder, add it there too.

Library images carry a hash of their contents in their names, so vercel.json
tells browsers to cache them for a year.

The site is public: anyone with the link can read the whole lore-book and
the bestiary's DM material (the **DM material** switch only hides it).

## The Barracks (charasheet)

`charasheet/` is [SonicRay241/charasheet](https://github.com/SonicRay241/charasheet),
used with the author's permission and kept as a git subtree. To take in the
author's later changes:

```
git subtree pull --prefix=charasheet https://github.com/SonicRay241/charasheet.git main --squash
```

Our changes to it are kept small so those pulls merge cleanly: the router
takes its base path from Vite (`src/main.tsx`), the web manifest uses
relative URLs, the privacy and terms pages are our own, and the "Cloud sync
unavailable" note is hidden when sync isn't configured. Its look is the
Threadmint's (the palette, light and dark, and the Garamond type of the other
halls): nearly all of that is in `src/index.css`, plus the list page (its
heading, and the `barracks` / `footlocker` classes that make it a barracks),
panel titles (`terminal-title` in `panel.tsx`), the toasts following
the system theme, and the font link in `index.html`.

The sheet also has an Equipped panel (`src/components/gear/equipped-panel.tsx`):
the character standing in the middle, drawn like the people in the bunks,
wearing what's in its head, chest, hands, legs, feet, main hand and off hand
slots (what can go where is told from the item's name, in
`src/db/equipped.ts`). Each slot holds the id of one of the character's own
weapons or equipment items, in a new `equipped` field on the character, so
upstream's files carry a little of it:
the field and its v9 migration (`src/db/db.ts`), its default
(`characters.ts`), import/export (`transfer.ts`) and sync merge
(`sync-engine.ts`), and the panel's place on the sheet (`sheet.tsx`).

Google Drive sync is off: it only switches on when `VITE_GDRIVE_CLIENT_ID`
is set at build time, and the build strips that from the environment. Its
token relay (`charasheet/api/google-token.ts`) isn't deployed either, since
Vercel only picks up functions from the repo root's `api/`. Turning sync on
means undoing both, setting up a Google OAuth client, and rewriting the
privacy and terms pages.

vercel.json sends every `/barracks/...` address that isn't a file to
`/barracks/index.html`, so a sheet's own address still works on reload.

## Files

```
build.py     runs both exports and assembles dist/ around the hub's page
```
