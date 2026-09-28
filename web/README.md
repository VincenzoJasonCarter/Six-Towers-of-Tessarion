# The Threadmint on the web

The hub, the library and the bestiary as one static site: the hub's reception
hall at `/`, the library at `/library/` and the bestiary at `/bestiary/`.

## Building it

From the repo root:

```
make web-build                # or: uv run web/build.py
```

That runs `library/build.py` and `bestiary/build.py`, gathers their output
into `dist/` (not committed) and copies the hub's page files to its root.
The hub's page is marked `<body data-hosted>` there, so instead of asking
`hub/serve.py` which tools are running it shows both halls as open and loads
them from `library/` and `bestiary/`. Like those two, it is a snapshot: rebuild after
editing the lore-book or `enemies.yaml`. It also rewrites
`bestiary/bestiary.html`, the same as `make bestiary-build`.

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

`.vercelignore` limits the upload to what the build reads (`web/`,
`hub/`, `library/`, `bestiary/`, `lore-book/`, `data/`). If the build starts reading
another folder, add it there too.

Library images carry a hash of their contents in their names, so vercel.json
tells browsers to cache them for a year.

The site is public: anyone with the link can read the whole lore-book and
the bestiary's DM material (the **DM material** switch only hides it).

## Files

```
build.py     runs both exports and assembles dist/ around the hub's page
```
