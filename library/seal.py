# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "markdown-it-py>=3.0", "cryptography>=42"]
# ///
"""Seal lore-vault/ into library/sealed.json, the library's withdrawn shelf.

Usage, from the repo root:

    uv run library/seal.py

lore-vault/ is kept out of git: its chapters (*.md, named like the
lore-book's) and vault.yaml, which gives the shelf, the serials and the key.
The key is a sequence of words. A reader who clicks those words in the
library's books, in that order, unseals the shelf.

sealed.json holds only the chapters encrypted with AES-GCM under a key
derived from that word sequence (PBKDF2-SHA256), plus the salt, the nonce
and how many words to listen for. Neither the words nor the text are in it
or anywhere else on the site, so it is safe to commit and publish. Run this
again after editing the vault: the live library reloads when sealed.json
changes, and the static export picks it up on its next build.
"""
import base64
import hashlib
import json
import os
import re
import unicodedata

import yaml
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core import HERE, IMAGE_REF, SOURCE, _body, _plain, _render, _text

VAULT = HERE.parent / "lore-vault"
CONFIG = VAULT / "vault.yaml"
SEALED = HERE / "sealed.json"
ITERATIONS = 250_000  # app.js reads this from sealed.json


def word(s):
    """Must match normWord in app.js: NFKC, lower case, letters and digits only."""
    s = unicodedata.normalize("NFKC", s).lower()
    return "".join(c for c in s if unicodedata.category(c)[0] in "LN")


def main():
    if not CONFIG.exists():
        raise SystemExit(f"{CONFIG.relative_to(HERE.parent)} not found; nothing to seal")
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    words = [w for w in map(word, str(cfg.get("key") or "").split()) if w]
    if len(words) < 3:
        raise SystemExit("vault.yaml: key needs at least three words")
    shelf = {"id": "withdrawn", "name": "Withdrawn Materials", "colour": "#241f2b", **(cfg.get("shelf") or {})}
    serials, spines = cfg.get("serials") or {}, cfg.get("spine_titles") or {}

    public = {re.sub(r"^\d+-", "", p.stem) for p in SOURCE.glob("*.md")}
    books = []
    for path in sorted(VAULT.glob("*.md")):
        raw = path.read_text(encoding="utf-8").strip()
        m = re.match(r"(\d+)-(.+)", path.stem)
        num, slug = (int(m.group(1)), m.group(2)) if m else (len(books) + 1, path.stem)
        if slug in public:
            raise SystemExit(f"{path.name}: the lore-book already has a chapter called {slug}")
        if IMAGE_REF.search(raw):
            print(f"warning: {path.name} has images; the sealed shelf does not carry them")
        first, _, rest = raw.partition("\n")
        title, rest = (_plain(first[2:]), rest) if first.startswith("# ") else (slug.replace("-", " ").title(), raw)
        page = _render(_body(title, rest))
        text = _text(page)
        books.append({
            "slug": slug, "num": num, "file": path.name, "title": title,
            "serial": serials.get(slug) or f"WM-{num:02d}", "spine": spines.get(slug, title),
            "shelf": shelf["id"], "sealed": True, "words": len(text.split()), "html": page, "text": text,
        })
    if not books:
        raise SystemExit(f"{VAULT.relative_to(HERE.parent)} has no chapters")

    salt, iv = os.urandom(16), os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", " ".join(words).encode(), salt, ITERATIONS, 32)
    plain = json.dumps({"shelf": shelf, "books": books}, ensure_ascii=False).encode()
    b64 = lambda b: base64.b64encode(b).decode()
    SEALED.write_text(json.dumps({
        "n": len(words), "iterations": ITERATIONS, "salt": b64(salt), "iv": b64(iv),
        "data": b64(AESGCM(key).encrypt(iv, plain, None)),
    }) + "\n", encoding="utf-8")
    print(f"sealed {len(books)} books ({sum(b['words'] for b in books)} words) under a {len(words)}-word key "
          f"-> {SEALED.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
