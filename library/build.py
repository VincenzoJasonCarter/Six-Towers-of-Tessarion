# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "markdown-it-py>=3.0", "pillow>=10"]
# ///
"""Export the Threadmint Library as a static site, for hosting.

Usage, from the repo root:

    uv run library/build.py                # -> library/site/
    uv run library/build.py --single-file  # -> library/library.html

library/site/ is index.html (styles and script inline) and an images/ folder.
A reader only downloads a book's pictures when they open that book, and each
image's name carries a hash of its contents, so a host can cache them for as
long as it likes. The folder is rebuilt from scratch every time.

--single-file writes everything, pictures included, into one library.html
instead: handy for sending to someone, but they download every picture up
front.

Either way the pictures are re-encoded as WebP (see compress_images in
core.py), and either way it is a snapshot: rebuild after editing the
lore-book. For editing, prefer the live server (serve.py).
"""
import argparse
import base64
import hashlib
import shutil

from core import HERE, compress_images, load, render

SITE = HERE / "site"
SINGLE = HERE / "library.html"
EXT = {"image/webp": "webp", "image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/svg+xml": "svg"}


def main():
    parser = argparse.ArgumentParser(description="Export the Threadmint Library as a static site.")
    parser.add_argument("--single-file", action="store_true", help=f"Write one self-contained {SINGLE.name} instead of {SITE.name}/.")
    args = parser.parse_args()

    payload, pool = load()
    for w in payload["warnings"]:
        print("warning:", w)
    before = sum(len(uri) * 3 // 4 for uri in pool.values())
    images = compress_images(pool)
    after = sum(len(data) for data, _ in images.values())
    print(f"images: {before / 1e6:.1f} MB as PNG -> {after / 1e6:.1f} MB")

    if args.single_file:
        uris = {ref: f"data:{kind};base64,{base64.b64encode(data).decode()}" for ref, (data, kind) in images.items()}
        SINGLE.write_text(render({**payload, "images": uris}), encoding="utf-8")
        print(f"wrote {SINGLE.relative_to(HERE.parent)} ({len(payload['books'])} books, {SINGLE.stat().st_size / 1e6:.1f} MB)")
        return

    shutil.rmtree(SITE, ignore_errors=True)
    (SITE / "images").mkdir(parents=True)
    urls = {}
    for ref, (data, kind) in images.items():
        name = f"{ref}-{hashlib.sha256(data).hexdigest()[:10]}.{EXT.get(kind, 'bin')}"
        (SITE / "images" / name).write_bytes(data)
        urls[ref] = f"images/{name}"
    page = SITE / "index.html"
    page.write_text(render({**payload, "images": urls}), encoding="utf-8")
    print(f"wrote {SITE.relative_to(HERE.parent)}/ ({len(payload['books'])} books: "
          f"index.html {page.stat().st_size / 1e6:.2f} MB, {len(urls)} images {after / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
