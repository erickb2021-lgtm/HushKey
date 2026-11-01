"""Draws the HushKey logo (concept A: a face going "shh" with a key) and saves
it as every icon format the apps need:

  assets/logo.png      in-app logo
  assets/HushKey.ico   Windows app + installer icon
  assets/HushKey.icns  Mac app icon

Run:  python packaging/make_icons.py   (needs Pillow: pip install pillow)
"""
import os

from PIL import Image, ImageDraw

GREEN = (61, 220, 151, 255)
INK = (8, 40, 26, 255)
SIZE = 1024
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")


def draw_logo(size=SIZE) -> Image.Image:
    s = size / 200.0  # artwork is drawn on a 200x200 grid, scaled up
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def box(cx, cy, r):
        return [(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s]

    # rounded green tile
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(44 * s), fill=GREEN)
    # head outline
    d.ellipse(box(100, 88, 54), outline=INK, width=int(11 * s))
    # closed eyes
    d.arc([70 * s, 68 * s, 92 * s, 88 * s], 20, 160, fill=INK, width=int(9 * s))
    d.arc([108 * s, 68 * s, 130 * s, 88 * s], 20, 160, fill=INK, width=int(9 * s))
    # key blade held up over the lips (green gap separates it from the face)
    d.rounded_rectangle([90 * s, 96 * s, 110 * s, 168 * s], radius=int(5 * s), fill=INK,
                        outline=GREEN, width=int(5 * s))
    # key teeth
    d.rectangle([108 * s, 102 * s, 121 * s, 111 * s], fill=INK)
    d.rectangle([108 * s, 117 * s, 117 * s, 126 * s], fill=INK)
    # key ring (bow) at the bottom, like a hand holding it
    d.ellipse(box(100, 170, 17), fill=INK, outline=GREEN, width=int(5 * s))
    d.ellipse(box(100, 170, 6), fill=GREEN)
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    big = draw_logo()
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "logo.png"))
    big.save(os.path.join(OUT, "HushKey.ico"),
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big.save(os.path.join(OUT, "HushKey.icns"))
    big.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "icon-512.png"))
    print("icons written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
