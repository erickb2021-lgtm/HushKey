"""
brand.py - draws the HushKey logo (a calm face going "shh" with a key) in code.

The app draws its own logo when it starts, so it can never go missing the
way a separate image file can. packaging/make_icons.py uses the same drawing
to make the .ico (Windows) and .icns (Mac) app icons.

v2.0.12 logo: the "Peaceful" face (closed eyes with a soft lid line) and a
short, thin key with two rounded teeth and a ring handle, so its details stay
visible even when the logo is small.
"""

import math

from PIL import Image, ImageDraw

GREEN = (61, 220, 151, 255)
GOLD = (242, 193, 78, 255)
INK = (8, 40, 26, 255)
GREEN_ON_LIGHT = (22, 146, 90, 255)   # deeper shade so the logo pops on off-white
CLEAR = (0, 0, 0, 0)


def _quad(p0, p1, p2, steps=10):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / steps for i in range(1, steps + 1))]


def _semi(cx, cy, r, a0, a1, steps=12):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]


# The key's blade, in a 200x200 drawing (v2.0.12 "soft & rounded", shorter and thinner so it
# stays clear at small sizes): rounded tip, two rounded teeth on the right.
_BLADE = (_semi(100, 105, 5, 180, 360) + [(105, 107)] + _semi(113, 110.5, 3.5, -90, 90)
          + [(105, 114), (105, 119)] + _semi(110, 122.5, 3.5, -90, 90) + [(105, 126), (105, 143), (95, 143)])


def draw_logo(size: int = 256, tile: bool = True, light: bool = False) -> Image.Image:
    """The logo on a rounded green tile (tile=True: app icon, dark lines),
    or on a see-through background in one green (tile=False: inside the app).
    light=True uses a deeper green for light mode."""
    big = max(size, 256) * 4  # draw large, shrink at the end for smooth edges
    s = big / 200.0
    img = Image.new("RGBA", (big, big), CLEAR)
    d = ImageDraw.Draw(img)
    ink = INK if tile else (GREEN_ON_LIGHT if light else GREEN)
    gap = GREEN if tile else CLEAR   # drawing CLEAR on a see-through image cuts a gap

    def pt(x, y):
        return (x * s, y * s)

    def circle(cx, cy, r, fill=None, outline=None, width=0):
        d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s],
                  fill=fill, outline=outline, width=int(round(width * s)))

    def stroke_arc(cx, cy, rx, ry, a0, a1, w, color):
        """An arc with round ends, centered on its path like an SVG stroke."""
        pts = [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))
               for a in [a0 + (a1 - a0) * i / 40 for i in range(41)]]
        d.line([pt(*p) for p in pts], fill=color, width=int(round(w * s)), joint="curve")
        for p in (pts[0], pts[-1]):
            circle(p[0], p[1], w / 2, fill=color)

    def rounded(x0, y0, x1, y1, r, fill):
        d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=r * s, fill=fill)

    if tile:
        d.rounded_rectangle([0, 0, big - 1, big - 1], radius=int(44 * s), fill=GREEN)

    # face + Peaceful eyes (closed, with a soft lid line underneath)
    circle(100, 88, 48.5, outline=ink, width=11)
    for cx in (81, 119):
        stroke_arc(cx, 74, 11, 9, 30, 150, 6, ink)
        stroke_arc(cx, 74, 11, 13, 40, 140, 3, ink)

    # key: a thin gap around each part keeps it apart from the face
    blade = [pt(*p) for p in _BLADE]
    d.polygon(blade, fill=gap, outline=gap, width=int(round(5 * s)))
    for p in blade:
        d.ellipse([p[0] - 2.5 * s, p[1] - 2.5 * s, p[0] + 2.5 * s, p[1] + 2.5 * s], fill=gap)
    d.polygon(blade, fill=ink)
    circle(100, 157, 16, fill=gap)                                                     # ring
    circle(100, 157, 14.25, fill=ink)
    circle(100, 157, 6.75, fill=gap)
    return img.resize((size, size), Image.LANCZOS)
