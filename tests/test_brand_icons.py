"""Tests for brand_icons.py and brand.py.  Run with:  python -m unittest -v"""

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "app"))

import unittest

import brand_icons
from brand import draw_logo


class BrandIconTests(unittest.TestCase):
    def test_index_loads(self):
        self.assertGreater(brand_icons.count(), 3000)

    def test_logos_load_without_the_assets_file(self):
        """The packed app must work even if assets/ wasn't included."""
        saved = (brand_icons._icons, brand_icons._by_slug, brand_icons._resource)
        try:
            brand_icons._icons = brand_icons._by_slug = None
            brand_icons._resource = lambda rel: "/definitely/not/here/" + rel
            self.assertGreater(brand_icons.count(), 3000)
            self.assertIsNotNone(brand_icons.render("riotgames", 32))
        finally:
            brand_icons._icons, brand_icons._by_slug, brand_icons._resource = saved

    def test_fonts_built_in(self):
        import base64
        import brand_data
        for name in ("Poppins-Regular.ttf", "Poppins-Bold.ttf"):
            data = base64.b64decode("".join(brand_data.FONTS_B64[name]))
            self.assertGreater(len(data), 100_000)
            self.assertEqual(data[:4], b"\x00\x01\x00\x00")  # a real TrueType font

    def test_search_riot(self):
        self.assertEqual(brand_icons.search("riot")[0], ("riotgames", "Riot Games"))

    def test_popular_when_empty(self):
        self.assertEqual(brand_icons.search("")[0][0], "google")

    def test_top_apps_all_available(self):
        sections = brand_icons.sections()
        self.assertEqual(sections[0][0], "Popular")
        self.assertEqual(len(sections[0][1]), 50)
        shown = [slug for _, items in sections for slug, _ in items]
        self.assertEqual(len(shown), len(set(shown)), "each logo shows in one category only")
        for slug in brand_icons.TOP_50:          # the 125 top apps are all still in the menu
            self.assertIn(slug, shown)
        titles = [t for t, _ in sections]
        for t in ("Shopping", "Banks & money", "Airlines & travel", "Food & delivery", "Cars & dealerships",
                  "Streaming & music", "Gaming services", "Video games"):
            self.assertIn(t, titles)
            self.assertGreater(len(dict(sections)[t]), 5, t)

    def test_amazon_and_new_categories(self):
        cases = {"Amazon": "hk-amazon", "Amazon Prime": "hk-amazon", "Capital One": "hk-bank",
                 "Citibank": "hk-bank", "Spirit Airlines": "hk-plane", "Delta": "delta", "Hulu": "hk-tv",
                 "Disney+": "hk-tv", "Netflix": "netflix", "Mercedes": "hk-car", "Carvana": "hk-car",
                 "Toyota": "toyota", "Kroger": "hk-cart", "Xbox": "hk-controller",
                 "Elden Ring": "hk-sword", "Minecraft": "hk-sword", "Hilton": "hilton", "Hyatt": "hk-hotel",
                 "Chase": "chase", "Wendys": "hk-burger"}
        for name, slug in cases.items():
            self.assertEqual(brand_icons.suggest(name), slug, name)

    def test_new_icons_draw_solid(self):
        for slug in ("hk-amazon", "hk-plane", "hk-car", "hk-card", "hk-tv", "hk-cart", "hk-hotel", "hk-sword"):
            img = brand_icons.render(slug, 48)
            self.assertIsNotNone(img, slug)
            self.assertGreater(sum(img.getchannel("A").histogram()[129:]), 300, slug)

    def test_restaurants(self):
        self.assertEqual(brand_icons.suggest("McDonalds"), "mcdonalds")
        self.assertEqual(brand_icons.suggest("Starbucks rewards"), "starbucks")
        self.assertEqual(brand_icons.suggest("Dominos"), "hk-pizza")      # no shared logo: pizza icon
        self.assertEqual(brand_icons.suggest("Chipotle"), "hk-food")
        self.assertEqual(brand_icons.suggest("Wendys"), "hk-burger")
        self.assertEqual(brand_icons.suggest("Dunkin"), "hk-coffee")

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
