# The Threadmint on the web

The hub, the library, the bestiary and the Memoria as one static site: the
hub's reception hall at `/`, the library at `/library/`, the bestiary at
`/bestiary/` and the Memoria at `/memoria/`. The Barracks (charasheet) isn't
part of it: the hub loads it in a frame from https://charasheet.rayy.dev/,
where its author hosts it. Only its item index is here, at
`/barracks/items.json`.

## Building it

From the repo root:

```
make web-build                # or: uv run web/build.py
```

That runs `library/build.py`, `bestiary/build.py`, `barracks/build.py` (the
item index) and `memoria/build.py`, gathers their output
into `dist/` (not committed) and copies the hub's page files to its root.
The hub's page is marked `<body data-hosted>` there, so instead of asking
`hub/serve.py` which tools are running it shows every hall as open and loads
them from the folders next to it (the Barracks from its own site). Like them, it is a snapshot: rebuild after
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
`hub/`, `library/`, `bestiary/`, `memoria/`, `lore-book/`, `data/`, `barracks/`). If the build starts reading
another folder, add it there too.

Library images carry a hash of their contents in their names, so vercel.json
tells browsers to cache them for a year.

The site is public: anyone with the link can read the whole lore-book and
the bestiary's DM material (the **DM material** switch only hides it).

## The Barracks (charasheet)

The character sheets are [SonicRay241/charasheet](https://github.com/SonicRay241/charasheet),
used with the author's permission and loaded from https://charasheet.rayy.dev/
(the address is in `hub/app.js`). Nothing of it is built or deployed here;
see `barracks/README.md`.

## Files

```
build.py     runs both exports and assembles dist/ around the hub's page
```
