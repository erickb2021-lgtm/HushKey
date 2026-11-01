"""Tests for brand_icons.py and brand.py.  Run with:  python -m unittest -v"""

import unittest

import brand_icons
from brand import draw_logo


class BrandIconTests(unittest.TestCase):
    def test_index_loads(self):
        self.assertGreater(brand_icons.count(), 3000)

    def test_search_riot(self):
        self.assertEqual(brand_icons.search("riot")[0], ("riotgames", "Riot Games"))

    def test_popular_when_empty(self):
        self.assertEqual(brand_icons.search("")[0][0], "google")

    def test_top_50_all_available(self):
        top = brand_icons.sections()[0]
        self.assertEqual(top[0], "Top 50 apps & games")
        self.assertEqual(len(top[1]), 50)

    def test_big_names_ranked_first(self):
        self.assertEqual([t for _, t in brand_icons.search("s", 3)], ["Snapchat", "Spotify", "Steam"])
        self.assertEqual(brand_icons.search("xbox")[0][0], "hk-controller")

    def test_suggest(self):
        self.assertEqual(brand_icons.suggest("Riot account 1"), "riotgames")
        self.assertEqual(brand_icons.suggest("discord main"), "discord")
        self.assertIsNone(brand_icons.suggest("my bank"))
        self.assertEqual(brand_icons.suggest("work email"), "hk-work")

    def test_everyday_icons_draw(self):
        for slug, *_ in brand_icons.EVERYDAY:
            self.assertIsNotNone(brand_icons.render(slug, 32), slug)

    def test_own_picture(self):
        import os
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pic.png")
            Image.new("RGB", (300, 200), (255, 0, 0)).save(path)
            icon = brand_icons.picture_to_icon(path)
            self.assertTrue(brand_icons.is_picture(icon))
            self.assertEqual(brand_icons.title(icon), "Your picture")
            self.assertEqual(brand_icons.render(icon, 40).size, (40, 40))
            bad = os.path.join(d, "notes.txt")
            with open(bad, "w") as f:
                f.write("not a picture")
            with self.assertRaises(ValueError):
                brand_icons.picture_to_icon(bad)

    def test_render_is_see_through(self):
        img = brand_icons.render("riotgames", 64)
        self.assertEqual(img.mode, "RGBA")
        self.assertEqual(img.getpixel((0, 0))[3], 0)        # corner: transparent
        self.assertGreater(img.getchannel("A").getextrema()[1], 200)  # logo: solid
        self.assertGreater(img.getpixel((32, 30))[0], 180)  # Riot red

    def test_dark_logo_made_visible(self):
        img = brand_icons.render("github", 64)  # black brand color
        self.assertGreater(img.getchannel("R").getextrema()[0], 200)  # drawn light instead

    def test_unknown(self):
        self.assertIsNone(brand_icons.render("not-a-real-brand"))

    def test_path_parser_handles_tricky_syntax(self):
        # squashed arc flags ("011"), implicit commands and ".5.5" numbers
        polys = brand_icons.path_to_polygons("M2 2h20v20H2zm5 5a3 3 0 011 1l.5.5.5.5z")
        self.assertEqual(len(polys), 2)

    def test_hushkey_logo(self):
        for tile in (True, False):
            img = draw_logo(64, tile=tile)
            self.assertEqual(img.size, (64, 64))
        self.assertEqual(draw_logo(64, tile=False).getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()
