"""The backgrounds (Settings > Appearance) are all bundled and open as pictures."""
import os
import unittest

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(HERE, "..", "assets", "backgrounds")
NAMES = ["cherry_blossom", "princess_castle", "ocean_dusk", "fairy_forest", "aurora_peaks", "ramen_shop",
         "samurai_sunset", "knights_keep", "neon_city", "space_voyage", "dragon_mountain", "soccer_stadium",
         "sunny_beach", "race_track", "sky_ruins"]


class BackgroundTests(unittest.TestCase):
    def test_all_fifteen_open(self):
        for name in NAMES:
            with Image.open(os.path.join(FOLDER, name + ".jpg")) as im:
                self.assertGreaterEqual(im.width, 400, name)
                self.assertAlmostEqual(im.width / im.height, 16 / 9, delta=0.05, msg=name)

    def test_app_list_matches_the_files(self):
        with open(os.path.join(HERE, "..", "app", "app.py"), encoding="utf-8") as f:
            source = f.read()
        for name in NAMES:
            self.assertIn(f'("{name}", ', source, name)


class FontTests(unittest.TestCase):
    def test_style_fonts_are_bundled(self):
        fonts = os.path.join(HERE, "..", "assets", "fonts")
        for stem in ("Poppins", "DMSans", "Nunito", "PixelifySans"):
            for weight in ("Regular", "Bold"):
                self.assertTrue(os.path.isfile(os.path.join(fonts, f"{stem}-{weight}.ttf")), stem + weight)
        with open(os.path.join(fonts, "OFL.txt"), encoding="utf-8") as f:
            license_text = f.read()
        for name in ("DM Sans", "Nunito", "Pixelify Sans"):
            self.assertIn(name, license_text)


if __name__ == "__main__":
    unittest.main()
