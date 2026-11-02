"""Tests for automatic updates (with a fake GitHub).  python -m unittest -v"""

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "app"))

import hashlib
import io
import json
import tempfile
import unittest
import urllib.error

import updater
from updater import Updater, UpdateError, is_newer, parse_version

INSTALLER = b"pretend this is HushKey-Windows.exe" * 100


class FakeGitHub:
    def __init__(self, tag="v9.9.9", with_assets=True, tamper=False):
        self.tag, self.with_assets, self.tamper = tag, with_assets, tamper
        self.calls = []

    def __call__(self, req):
        url = req.full_url
        self.calls.append(url)
        if url.endswith("/releases/latest"):
            assets = []
            if self.with_assets:
                for name in ("HushKey-Windows.exe", "HushKey-Windows.exe.sha256.txt",
                             "HushKey-Mac.zip", "HushKey-Mac.zip.sha256.txt"):
                    assets.append({"name": name, "size": 10, "browser_download_url": "https://dl/" + name})
            body = "## What's new\n- **Sync** across computers\n- [Docs](https://x)"
            return io.BytesIO(json.dumps({"tag_name": self.tag, "body": body, "assets": assets}).encode())
        if url.endswith(".sha256.txt"):
            digest = hashlib.sha256(INSTALLER).hexdigest()
            return io.BytesIO(f"{digest}  HushKey-Windows.exe\n".encode())
        if url.endswith("HushKey-Windows.exe"):
            return io.BytesIO(INSTALLER + (b"!" if self.tamper else b""))
        raise urllib.error.URLError("not found")


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.real_version = updater.__version__
        updater.__version__ = "2.0.9"

    def tearDown(self):
        updater.__version__ = self.real_version
        self.tmp.cleanup()

    def make(self, gh):
        return Updater(repo="johndoe/HushKey", opener=gh, download_dir=self.tmp.name)

    def test_versions(self):
        self.assertTrue(is_newer("2.0.10", "2.0.9"))   # 10 > 9, not "1" < "9"
        self.assertFalse(is_newer("2.0.9", "2.0.9"))
        self.assertFalse(is_newer("2.0.8", "2.0.9"))
        self.assertEqual(parse_version("v2.1.0"), (2, 1, 0))

    def test_finds_newer_release(self):
        rel = self.make(FakeGitHub()).check(asset="HushKey-Windows.exe")
        self.assertEqual(rel.version, "9.9.9")
        self.assertIn("• Sync across computers", rel.notes)
        self.assertNotIn("**", rel.notes)

    def test_no_update_when_current(self):
        self.assertIsNone(self.make(FakeGitHub(tag="v2.0.9")).check(asset="HushKey-Windows.exe"))

    def test_waits_until_github_finished_building(self):
        self.assertIsNone(self.make(FakeGitHub(with_assets=False)).check(asset="HushKey-Windows.exe"))

    def test_download_verifies_fingerprint(self):
        u = self.make(FakeGitHub())
        rel = u.check(asset="HushKey-Windows.exe")
        path = u.download(rel, asset="HushKey-Windows.exe")
        with open(path, "rb") as f:
            self.assertEqual(f.read(), INSTALLER)
        self.assertEqual(u.download(rel, asset="HushKey-Windows.exe"), path)  # reused, not re-downloaded

    def test_tampered_download_rejected(self):
        u = self.make(FakeGitHub(tamper=True))
        rel = u.check(asset="HushKey-Windows.exe")
        with self.assertRaises(UpdateError):
            u.download(rel, asset="HushKey-Windows.exe")

    def test_offline_is_a_friendly_error(self):
        def offline(req):
            raise urllib.error.URLError("no network")
        with self.assertRaises(UpdateError):
            self.make(offline).check(asset="HushKey-Windows.exe")

    def test_disabled_when_running_from_source(self):
        self.assertFalse(Updater(repo="johndoe/HushKey").enabled)
        self.assertIsNone(Updater(repo="").check(asset="HushKey-Windows.exe"))


if __name__ == "__main__":
    unittest.main()
