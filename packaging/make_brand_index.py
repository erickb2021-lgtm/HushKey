"""Packs the Simple Icons brand logos into one small file the app ships with:
assets/brand_icons.json.gz

Simple Icons (https://simpleicons.org) is a free (CC0) collection of 3,000+
brand logos, each a single see-through shape plus the brand's color.
Bundling them means HushKey never has to go online to show a logo, so no
website learns which apps you keep passwords for.

To update the logos:
    git clone --depth 1 https://github.com/simple-icons/simple-icons.git
    python packaging/make_brand_index.py path/to/simple-icons
"""
import gzip
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "brand_icons.json.gz")

_REPLACE = {"+": "plus", ".": "dot", "&": "and", "đ": "d", "ħ": "h", "ı": "i", "ĸ": "k",
            "ŀ": "l", "ł": "l", "ß": "ss", "ŧ": "t", "ø": "o"}


def title_to_slug(title: str) -> str:
    """Same rule Simple Icons uses to name its files."""
    s = title.lower()
    s = "".join(_REPLACE.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFD", s)
    return re.sub(r"[^a-z0-9]", "", s)


def main(repo: str):
    with open(os.path.join(repo, "data", "simple-icons.json"), encoding="utf-8") as f:
        data = json.load(f)
    entries = data["icons"] if isinstance(data, dict) else data
    out, missing = [], 0
    for e in entries:
        slug = e.get("slug") or title_to_slug(e["title"])
        svg_path = os.path.join(repo, "icons", slug + ".svg")
        if not os.path.isfile(svg_path):
            missing += 1
            continue
        with open(svg_path, encoding="utf-8") as f:
            m = re.search(r'<path d="([^"]+)"', f.read())
        if not m:
            missing += 1
            continue
        aliases = e.get("aliases") or {}
        extra = list(aliases.get("aka", []))
        for v in (aliases.get("dup") or []):
            if isinstance(v, dict) and v.get("title"):
                extra.append(v["title"])
        for v in (aliases.get("loc") or {}).values():
            extra.append(v)
        out.append([slug, e["title"], e["hex"], m.group(1), extra])
    payload = {"source": "Simple Icons (CC0) https://simpleicons.org", "icons": out}
    with gzip.open(OUT, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"wrote {len(out)} logos ({missing} skipped) to {os.path.abspath(OUT)} "
          f"({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "simple-icons")
