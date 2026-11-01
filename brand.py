"""
brand.py - draws the HushKey logo (a face going "shh" with a key) in code.

The app draws its own logo when it starts, so it can never go missing the
way a separate image file can. packaging/make_icons.py uses the same drawing
to make the .ico (Windows) and .icns (Mac) app icons.
"""

from PIL import Image, ImageDraw

GREEN = (61, 220, 151, 255)
GOLD = (242, 193, 78, 255)
INK = (8, 40, 26, 255)
GREEN_ON_LIGHT = (22, 146, 90, 255)   # deeper shades so the logo pops on off-white
GOLD_ON_LIGHT = (176, 125, 18, 255)


def draw_logo(size: int = 256, tile: bool = True, light: bool = False) -> Image.Image:
    """The logo on a rounded green tile (tile=True) or just the face on
    a see-through background in green and gold (tile=False). light=True
    uses deeper colors for light mode."""
    big = max(size, 512) * 2  # draw large, shrink at the end for smooth edges
    s = big / 200.0
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    face_green = GREEN_ON_LIGHT if light else GREEN
    key_gold = GOLD_ON_LIGHT if light else GOLD
    fg = INK if tile else face_green
    gap = GREEN if tile else (0, 0, 0, 0)

    def box(cx, cy, r):
        return [(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s]

    if tile:
        d.rounded_rectangle([0, 0, big - 1, big - 1], radius=int(44 * s), fill=GREEN)
    d.ellipse(box(100, 88, 54), outline=fg, width=int(11 * s))                 # head
    d.arc([70 * s, 68 * s, 92 * s, 88 * s], 20, 160, fill=fg, width=int(9 * s))   # closed eye
    d.arc([108 * s, 68 * s, 130 * s, 88 * s], 20, 160, fill=fg, width=int(9 * s))  # closed eye
    if not tile:
        # cut a gap around the key so it stands apart from the face
        d.rounded_rectangle([85 * s, 91 * s, 115 * s, 173 * s], radius=int(8 * s), fill=gap)
    key = fg if tile else key_gold
    d.rounded_rectangle([90 * s, 96 * s, 110 * s, 168 * s], radius=int(5 * s), fill=key,
                        outline=gap if tile else None, width=int(5 * s) if tile else 0)  # blade
    d.rectangle([108 * s, 102 * s, 121 * s, 111 * s], fill=key)                 # teeth
    d.rectangle([108 * s, 117 * s, 117 * s, 126 * s], fill=key)
    if tile:
        d.ellipse(box(100, 170, 17), fill=key, outline=gap, width=int(5 * s))  # ring
        d.ellipse(box(100, 170, 6), fill=gap)
    else:
        d.ellipse(box(100, 170, 17), fill=key)
        d.ellipse(box(100, 170, 6), fill=(0, 0, 0, 0))
    return img.resize((size, size), Image.LANCZOS)
