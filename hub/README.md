# Threadmint Campaign Desk

One page for the Tessarion tools:

- **Library**: the lore-book bookcase (`library/`)
- **Bestiary**: the Threadmint Bestiary (`bestiary/`)
- **Memoria**: the museum of Tessarion's history, room by room in lit cases
  (`memoria/`)
- **Barracks**: character sheets, [charasheet](https://github.com/SonicRay241/charasheet)
  by SonicRay241 (`charasheet/`)

## Running it

From the repo root:

```
make hub
```

or

```
uv run hub/serve.py
```

The desk opens at http://127.0.0.1:8760/ on a reception hall: a desk in
front and four corridors behind it, one per tool (the Library's bookshelves,
the Barracks' bunks and the Memoria's marble gallery right behind the clerk,
the Bestiary's dark stone). The lamp on each corridor's plaque shows whether
that tool is running. Click a corridor and you walk into it: the camera
crosses reception, passes through the doorway and goes down the corridor
(redrawn in perspective as it moves) towards the light at the far end, which
opens onto the tool. Go back to Reception (the bar along the top, or the
browser's Back button) and you walk back out the same way.
The bar also jumps straight between tools.

## The clerk

Hessa Vane, Junior Registrar (for eleven years), stands behind the desk.
Click her, or ring the bell, and she talks: each line comes with a few
replies to pick from (who she is, what's behind each door, gossip, bits of
Tessarion lore, and the restricted section, which you can't see). Some of
what she says depends on the moment: the time of day, how often you've been
by, whether a hall is closed, and which hall you've just come back from. Her
eyes follow the doorway you point at, she mutters to herself if you leave
the desk alone for a while, and six rings in quick succession get the bell
confiscated for half a minute. Esc or a click elsewhere ends the
conversation.

Everything she says is written out in `clerk.js`, so adding lines is a
matter of adding to the lists there (the comment at the top explains the
format). She doesn't use an AI model and needs no network.

The **Animate** switch in the bar turns off the walks and the moving lamps
and eyes. Like the library's **Animate books**, it is remembered in the
browser and is on unless switched off there, whatever the system's
reduce-motion setting says.

It starts the tools on their usual ports (library 8767, bestiary 8766,
Barracks 8768, Memoria 8769).
A tool keeps its place while you look at the other. **Open in its own tab**
opens the current tool without the desk around it.

If one of those tools is already running, say from `make library`, the
desk uses that server and doesn't start a second one. Ctrl+C stops the desk
and every tool it started. It doesn't stop a tool that was already
running.

Options: `--port 9000`, `--no-browser`. Requires `uv` on PATH.

## The Barracks

The Barracks is `barracks/serve.py` (port 8768, as `make barracks` runs
it): the last build of charasheet, so it opens as quickly as the other two.
If charasheet/ changed since that build, it builds first, which needs Node
and takes a few seconds, and its lamp stays lit amber meanwhile.

Its sheets are kept in the browser, per site: the desk on 127.0.0.1 and the
public website each have their own.

The public website (`web/`) uses this same page as its front door, without
serve.py: there every hall is always open, and the tools load from
`library/`, `bestiary/`, `barracks/` and `memoria/` next to the page.

## Layout

```
serve.py     starts the tools and serves the desk (stdlib only)
index.html   page markup: the reception hall and tool tabs
style.css    page styles
app.js       corridor drawings (SVG), tool status, views, desk bell
clerk.js     the clerk's conversation: every line, the replies, and when she says what
```
