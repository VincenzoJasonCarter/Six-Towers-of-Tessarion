# The Barracks

The character sheets: [charasheet](https://github.com/SonicRay241/charasheet)
by SonicRay241 (in `charasheet/`, see `web/README.md` for how it's kept and
what we changed), built for `/barracks/` and served like the other halls.

## Running it

From the repo root:

```
make barracks          # or: uv run barracks/serve.py
```

It opens at http://127.0.0.1:8768/barracks/ and serves the last build of
charasheet, so it starts at once. If anything in charasheet/ changed since
that build, it builds first (a few seconds; longer the first time, when
`npm ci` installs its packages). Building needs Node; without it, an
existing build is served as it is.

Options: `--port 9000`, `--no-browser`.

To work on charasheet's own code, use Vite's dev server instead, which
reloads the page as you edit:

```
make barracks-dev      # http://127.0.0.1:5173/
```

## Building it

```
make barracks-build    # or: uv run barracks/build.py [--force]
```

writes `charasheet/dist/` for `/barracks/`, without Google Drive sync, and
does nothing if it is already up to date. `web/build.py` runs it and copies
the result to `/barracks/` on the public site.

## Files

```
build.py     builds charasheet/ into charasheet/dist/ when it changed
serve.py     serves that build at /barracks/, building first if needed (stdlib only)
```
