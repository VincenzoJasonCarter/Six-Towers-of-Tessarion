# One-shots

The DM's one-shot modules, one Markdown file each in `modules/`. A module is a
whole session: the truth behind it, its structure, pre-gens, NPCs, every act
with its read-aloud text, stat blocks and handouts.

**DM only.** These pages are full of spoilers, so they are not on the hub and
the public site build (`web/build.py`) never copies them. Keep in mind that
the Markdown sources are still in the repo.

## Running it

From the repo root:

```
make oneshots                 # or: uv run oneshots/serve.py
```

The list of modules opens on http://127.0.0.1:8768/. Each page rereads its
module on every load, and an open page reloads itself (at the same scroll
position) when you save the module or the page's files (`template.html`,
`style.css`, `app.js`).
Options: `--port 9000`, `--no-browser` (via `make oneshots ARGS="..."`).

For files you can open without the server, or bring to the table offline:

```
make oneshots-build           # or: uv run oneshots/build.py
```

That writes `dist/<module>.html` for every module, plus `dist/index.html`.
`dist/` is git-ignored. Run it again after editing a module.

## Writing a module

Add `modules/<name>.md`. The page takes:

- the first line, `# Title`, as the page title;
- an italic line right under it (`*One-shot outro arc Crownweave...*`) as the
  small red line above the title;
- every `## Heading` as a section, listed in the contents rail;
- `> quotes` as read-aloud boxes. Tables scroll sideways on narrow screens.

Name new NPCs the campaign's way: cross-blend two related words of three or
more syllables into a first and last name (Remedy × Rosary → Remary Rosedy).

## Files

```
serve.py        live server (stdlib http.server; rereads the modules on every load)
build.py        static export: dist/<module>.html and dist/index.html
core.py         shared: reads a module and fills in the page
template.html   page markup
style.css       page styles
app.js          contents-rail highlight, live reload
modules/        the modules, one .md each
```
