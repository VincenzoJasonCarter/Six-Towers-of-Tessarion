# The Barracks

The character sheets: [charasheet](https://github.com/SonicRay241/charasheet)
by SonicRay241, hosted by its author at https://charasheet.rayy.dev/. Walking
into the Barracks in the hub goes on to that address in the same tab (it is
`TOOLS.barracks.url` in `hub/app.js`), both locally and on the public site,
so there is no copy of charasheet here and nothing to build or serve for it.
Our changes to it live in
[VincenzoJasonCarter/charasheet](https://github.com/VincenzoJasonCarter/charasheet).

It isn't loaded in a frame like the other halls: framed by another site,
charasheet gets storage apart from its own site's and its Google Drive
sign-in fails ("Google authorization window was closed."). See "The
Barracks" in `hub/README.md`.

## The item index

`/barracks/items.json` on the public site lists the items of Tessarion for
charasheet to offer in its Weapons and Equipment panels. It's made from
`data/items.yaml`: edit that, not the JSON. Entries marked `hidden: true`
stay out.

```
make barracks-build    # or: uv run barracks/build.py  -> barracks/dist/items.json
```

`web/build.py` runs it and puts the result at `/barracks/` on the public site.

Its format is at the top of `items.py`. Two things other code relies on:
ids never change once published, and damage dice carry no modifier (the
wielder adds their `ability` modifier and the item's `bonus`). The file is
served with `Access-Control-Allow-Origin: *` (vercel.json), so charasheet,
hosted elsewhere, can read it.

## Files

```
build.py     writes items.json into barracks/dist/
items.py     data/items.yaml as items.json (the format is described at the top)
```
