"""Saves the HushKey logo (drawn in brand.py) as every icon file the build needs:

  assets/HushKey.ico   Windows app, taskbar + installer icon
  assets/HushKey.icns  Mac app + dock icon
  assets/icon-512.png  README picture

Run from the project folder:  python packaging/make_icons.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from brand import draw_logo  # noqa: E402

OUT = os.path.join(HERE, "..", "assets")


def main():
    os.makedirs(OUT, exist_ok=True)
    big = draw_logo(1024)
    big.save(os.path.join(OUT, "HushKey.ico"),
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big.save(os.path.join(OUT, "HushKey.icns"))
    draw_logo(512).save(os.path.join(OUT, "icon-512.png"))
    print("icons written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
