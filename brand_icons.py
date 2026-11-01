"""
brand_icons.py - find and draw app logos (Riot, Discord, Steam...) for logins.

The logos come from Simple Icons (free, CC0), bundled in
assets/brand_icons.json.gz, so nothing is downloaded and no website learns
which apps you use. Each logo is one SVG "path" (a list of drawing commands
like "move here, draw a curve to there"). This file turns that path into a
see-through PNG with Pillow, so it blends into HushKey's dark background.
"""

import gzip
import json
import math
import os
import re
import sys
import threading

from PIL import Image

_lock = threading.Lock()
_icons = None        # list of [slug, title, hex, path, aliases]
_by_slug = None
_cache = {}

POPULAR = ["riotgames", "leagueoflegends", "valorant", "discord", "steam", "epicgames",
           "playstation", "roblox", "fortnite", "battledotnet", "twitch", "google", "gmail",
           "apple", "instagram", "tiktok", "snapchat", "x", "facebook", "youtube", "netflix",
           "spotify", "paypal", "github", "reddit", "whatsapp"]

BACKGROUND = (22, 26, 34)  # HushKey card color, used to keep logos readable


def _resource(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def load():
    """Load the logo list once (about 0.2s)."""
    global _icons, _by_slug
    with _lock:
        if _icons is None:
            with gzip.open(_resource(os.path.join("assets", "brand_icons.json.gz")), "rt",
                           encoding="utf-8") as f:
                _icons = json.load(f)["icons"]
            _by_slug = {i[0]: i for i in _icons}
    return _icons


def count() -> int:
    return len(load())


def title(slug):
    load()
    item = _by_slug.get(slug)
    return item[1] if item else None


def _norm(text):
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


def search(query: str, limit: int = 8):
    """Best matches as [(slug, title)], e.g. 'riot' -> Riot Games first."""
    load()
    q = _norm(query)
    if not q:
        return [(s, _by_slug[s][1]) for s in POPULAR if s in _by_slug][:limit]
    q_tight = q.replace(" ", "")
    scored = []
    for slug, name, _hex, _path, aliases in _icons:
        best = 9
        for i, candidate in enumerate([name] + list(aliases)):
            n = _norm(candidate)
            penalty = 0 if i == 0 else 0.5
            if n == q:
                s = 0
            elif n.startswith(q):
                s = 1
            elif any(w.startswith(q) for w in n.split()):
                s = 2
            elif q in n:
                s = 3
            elif q_tight in slug:
                s = 4
            else:
                continue
            best = min(best, s + penalty)
        if best < 9:
            scored.append((best, len(name), name.lower(), slug, name))
    scored.sort()
    return [(s[3], s[4]) for s in scored[:limit]]


def suggest(client_name: str):
    """Guess a logo from a client name: 'Riot account 1' -> riotgames."""
    words = _norm(client_name).split()
    if not words or len(words[0]) < 3:
        return None  # too short to guess safely ("my bank" shouldn't match anything)
    first = words[0]
    while words:
        hits = search(" ".join(words), limit=1)
        if hits:
            slug, name = hits[0]
            brand_words = _norm(name).split()
            squashed = _norm(name).replace(" ", "")
            if first in brand_words or squashed == first or (len(first) >= 6 and squashed.startswith(first)):
                return slug
        words = words[:-1]
    return None


# --------------------------------------------------------------------------
# Drawing an SVG path (the "M13.458.86 0 7.093l3.353..." text) with Pillow
# --------------------------------------------------------------------------

_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


class _Reader:
    def __init__(self, d):
        self.d, self.i = d, 0

    def _skip(self):
        while self.i < len(self.d) and self.d[self.i] in " ,\t\r\n":
            self.i += 1

    def has_number(self):
        self._skip()
        return self.i < len(self.d) and (self.d[self.i].isdigit() or self.d[self.i] in "+-.")

    def number(self):
        self._skip()
        m = _NUM.match(self.d, self.i)
        if not m:
            raise ValueError("bad number at %d" % self.i)
        self.i = m.end()
        return float(m.group())

    def flag(self):  # arc flags may be written squashed together, like "01"
        self._skip()
        ch = self.d[self.i]
        self.i += 1
        return ch == "1"

    def command(self):
        self._skip()
        if self.i >= len(self.d):
            return None
        ch = self.d[self.i]
        if ch.isalpha():
            self.i += 1
            return ch
        return ""  # implicit repeat of the previous command


def _cubic(p0, p1, p2, p3, steps=10):
    pts = []
    for k in range(1, steps + 1):
        t = k / steps
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


def _quad(p0, p1, p2, steps=8):
    pts = []
    for k in range(1, steps + 1):
        t = k / steps
        u = 1 - t
        pts.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return pts


def _arc(p0, rx, ry, phi_deg, large, sweep, p1, steps=12):
    """SVG elliptical arc -> points (math from the SVG spec, appendix F.6)."""
    x1, y1 = p0
    x2, y2 = p1
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [p1]
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(phi_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = x1p * x1p / (rx * rx) + y1p * y1p / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        coef = -coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def angle(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    th1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dth = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dth > 0:
        dth -= 2 * math.pi
    elif sweep and dth < 0:
        dth += 2 * math.pi
    n = max(2, int(abs(dth) / (math.pi / 2) * steps / 2) + 2)
    pts = []
    for k in range(1, n + 1):
        a = th1 + dth * k / n
        pts.append((cx + rx * math.cos(a) * cp - ry * math.sin(a) * sp,
                    cy + rx * math.cos(a) * sp + ry * math.sin(a) * cp))
    return pts


def path_to_polygons(d: str):
    """Turn SVG path text into a list of closed point lists."""
    r = _Reader(d)
    polys, cur = [], []
    x = y = sx = sy = 0.0
    last_ctrl = None
    prev = None
    while True:
        cmd = r.command()
        if cmd is None:
            break
        if cmd == "":
            if prev is None:
                raise ValueError("path must start with a command")
            cmd = {"M": "L", "m": "l"}.get(prev, prev)
        rel = cmd.islower()
        c = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if c == "Z":
            if cur:
                polys.append(cur)
            cur = []
            x, y = sx, sy
            last_ctrl = None
            prev = cmd
            continue
        if c == "M":
            if cur:
                polys.append(cur)
            x, y = r.number() + ox, r.number() + oy
            sx, sy = x, y
            cur = [(x, y)]
            last_ctrl = None
        elif c == "L":
            x, y = r.number() + ox, r.number() + oy
            cur.append((x, y))
            last_ctrl = None
        elif c == "H":
            x = r.number() + ox
            cur.append((x, y))
            last_ctrl = None
        elif c == "V":
            y = r.number() + (y if rel else 0.0)
            cur.append((x, y))
            last_ctrl = None
        elif c == "C":
            p1 = (r.number() + ox, r.number() + oy)
            p2 = (r.number() + ox, r.number() + oy)
            p3 = (r.number() + ox, r.number() + oy)
            cur += _cubic((x, y), p1, p2, p3)
            last_ctrl, (x, y) = ("C", p2), p3
        elif c == "S":
            p1 = (2 * x - last_ctrl[1][0], 2 * y - last_ctrl[1][1]) if last_ctrl and last_ctrl[0] == "C" else (x, y)
            p2 = (r.number() + ox, r.number() + oy)
            p3 = (r.number() + ox, r.number() + oy)
            cur += _cubic((x, y), p1, p2, p3)
            last_ctrl, (x, y) = ("C", p2), p3
        elif c == "Q":
            p1 = (r.number() + ox, r.number() + oy)
            p2 = (r.number() + ox, r.number() + oy)
            cur += _quad((x, y), p1, p2)
            last_ctrl, (x, y) = ("Q", p1), p2
        elif c == "T":
            p1 = (2 * x - last_ctrl[1][0], 2 * y - last_ctrl[1][1]) if last_ctrl and last_ctrl[0] == "Q" else (x, y)
            p2 = (r.number() + ox, r.number() + oy)
            cur += _quad((x, y), p1, p2)
            last_ctrl, (x, y) = ("Q", p1), p2
        elif c == "A":
            rx, ry, rot = r.number(), r.number(), r.number()
            large, sweep = r.flag(), r.flag()
            p = (r.number() + ox, r.number() + oy)
            cur += _arc((x, y), rx, ry, rot, large, sweep, p)
            (x, y), last_ctrl = p, None
        else:
            raise ValueError("unknown command " + cmd)
        prev = cmd
    if cur:
        polys.append(cur)
    return [p for p in polys if len(p) >= 3]


def _fill_nonzero(polys, size, scale):
    """Fill shapes using the SVG 'nonzero' rule (holes work properly)."""
    rows = [[] for _ in range(size)]
    for poly in polys:
        n = len(poly)
        for k in range(n):
            x0, y0 = poly[k]
            x1, y1 = poly[(k + 1) % n]
            x0, y0, x1, y1 = x0 * scale, y0 * scale, x1 * scale, y1 * scale
            if y0 == y1:
                continue
            direction = 1 if y1 > y0 else -1
            ylo, yhi = min(y0, y1), max(y0, y1)
            start = max(0, int(math.ceil(ylo - 0.5)))
            end = min(size - 1, int(math.ceil(yhi - 0.5)) - 1)
            inv = (x1 - x0) / (y1 - y0)
            for row in range(start, end + 1):
                yc = row + 0.5
                rows[row].append((x0 + (yc - y0) * inv, direction))
    buf = bytearray(size * size)
    for row, hits in enumerate(rows):
        if not hits:
            continue
        hits.sort()
        wind = 0
        for idx in range(len(hits) - 1):
            wind += hits[idx][1]
            if wind != 0:
                a = max(0, min(size, int(round(hits[idx][0]))))
                b = max(0, min(size, int(round(hits[idx + 1][0]))))
                if b > a:
                    buf[row * size + a: row * size + b] = b"\xff" * (b - a)
    return Image.frombytes("L", (size, size), bytes(buf))


def _readable_color(hex_color):
    """Brand color, unless it's too dark to see on HushKey's dark cards."""
    rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def lum(c):
        ch = [v / 255 for v in c]
        ch = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

    contrast = (max(lum(rgb), lum(BACKGROUND)) + 0.05) / (min(lum(rgb), lum(BACKGROUND)) + 0.05)
    return rgb if contrast >= 2.4 else (238, 241, 246)


def render(slug: str, size: int = 64):
    """See-through PNG of a brand logo in its own color, or None if unknown."""
    key = (slug, size)
    if key in _cache:
        return _cache[key]
    load()
    item = _by_slug.get(slug)
    if not item:
        return None
    ss = 4  # draw 4x bigger, then shrink, for smooth edges
    big = size * ss
    mask = _fill_nonzero(path_to_polygons(item[3]), big, big / 24.0)
    mask = mask.resize((size, size), Image.BOX)
    img = Image.new("RGBA", (size, size), _readable_color(item[2]) + (0,))
    img.putalpha(mask)
    _cache[key] = img
    return img
