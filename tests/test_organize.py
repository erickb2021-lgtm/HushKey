"""Tests for v2.0.10: favorites, folders, suggestions, security tips, leak check.
Run with:  python -m unittest -v"""

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "app"))

import hashlib
import tempfile
import time
import unittest

import leakcheck
from test_sync import EMAIL, MASTER, Computer
from test_cloud import FakeSupabase
from vault import Vault, VaultError, health_score


class OrganizeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.v = Vault("john.doe@example.com", self.tmp.name)
        self.v.create("correct horse battery")
        self.discord = self.v.add("Discord", "johndoe", "Summer2024!")
        self.netflix = self.v.add("Netflix", "john@x.com", "Summer2024!")
        self.bank = self.v.add("Bank", "jdoe", "m4R!9vq#Tz2wLp")
        self.steam = self.v.add("Steam", "john_doe", "steam123")

    def tearDown(self):
        self.tmp.cleanup()

    def reopen(self):
        v = Vault("john.doe@example.com", self.tmp.name)
        v.unlock("correct horse battery")
        return v

    def test_favorites_are_saved(self):
        self.v.set_meta(self.bank, fav=True)
        rows = {e["id"]: e for e in self.reopen().list_entries()}
        self.assertTrue(rows[self.bank]["fav"])
        self.assertFalse(rows[self.steam]["fav"])
        self.v.set_meta(self.bank, fav=False)
        self.assertFalse(self.reopen().get(self.bank)["fav"])

    def test_folders_add_move_remove(self):
        g = self.v.add_folder("Gaming", "#8C9EFF")
        with self.assertRaises(VaultError):
            self.v.add_folder("gaming", "#000000")      # no duplicate names
        with self.assertRaises(VaultError):
            self.v.add_folder("   ", "#000000")         # needs a name
        self.v.set_meta(self.steam, folder=g)
        v2 = self.reopen()
        self.assertEqual(v2.folders()[0]["name"], "Gaming")
        self.assertEqual(v2.get(self.steam)["folder"], g)
        self.v.set_meta(self.steam, folder=None)       # take it out again
        self.assertEqual(self.reopen().get(self.steam)["folder"], "")

    def test_rename_and_delete_folder_keeps_logins(self):
        g = self.v.add_folder("Gaming", "#8C9EFF")
        self.v.set_meta(self.steam, folder=g, fav=True)
        self.v.rename_folder(g, "Games")
        self.assertEqual(self.v.folders()[0]["name"], "Games")
        self.v.delete_folder(g)
        v2 = self.reopen()
        self.assertEqual(v2.folders(), [])
        self.assertEqual(v2.get(self.steam)["folder"], "")
        self.assertTrue(v2.get(self.steam)["fav"])           # other choices stay
        self.assertEqual(v2.entry_count, 4)

    def test_folder_names_are_encrypted(self):
        self.v.add_folder("Secret project", "#8C9EFF")
        with open(self.v.path, encoding="utf-8") as f:
            self.assertNotIn("Secret project", f.read())

    def test_security_report(self):
        rows = {r["id"]: r for r in self.v.security_report()}
        self.assertEqual(rows[self.discord]["kind"], "reused")
        self.assertEqual(rows[self.discord]["reused_with"], ["Netflix"])
        self.assertEqual(rows[self.steam]["kind"], "weak")
        self.assertNotIn(self.bank, rows)
        leaked = {hashlib.sha1(b"m4R!9vq#Tz2wLp").hexdigest().upper()}
        rows = {r["id"]: r for r in self.v.security_report(leaked)}
        self.assertEqual(rows[self.bank]["kind"], "leaked")
        self.assertEqual(self.v.security_report(leaked)[0]["id"], self.bank)   # worst first

    def test_changing_password_clears_the_tip(self):
        self.v.set_meta(self.steam, mute=True)
        self.assertTrue(self.v.tip_state(self.steam)["mute"])
        self.v.update(self.steam, "Steam", "john_doe", "steam123")            # same password: kept
        self.assertTrue(self.v.tip_state(self.steam)["mute"])
        self.v.update(self.steam, "Steam", "john_doe", "Lz5@tYc8!rQ0aE-x")   # new password: fresh start
        self.assertFalse(self.v.tip_state(self.steam)["mute"])
        self.assertNotIn(self.steam, {r["id"] for r in self.v.security_report()})

    def test_editing_keeps_folder_and_favorite(self):
        g = self.v.add_folder("Gaming", "#8C9EFF")
        self.v.set_meta(self.steam, folder=g, fav=True)
        self.v.update(self.steam, "Steam (main)", "john_doe", "steam123", "steam")
        e = self.reopen().get(self.steam)
        self.assertEqual((e["title"], e["folder"], e["fav"]), ("Steam (main)", g, True))

    def test_snooze(self):
        until = time.time() + 30 * 86400
        self.v.set_meta(self.netflix, snooze=until)
        self.assertAlmostEqual(self.reopen().tip_state(self.netflix)["snooze"], until, places=0)

    def test_health_score(self):
        self.assertEqual(health_score(0, []), 100)
        report = self.v.security_report()
        score = health_score(self.v.entry_count, report)
        self.assertTrue(0 < score < 100)
        for r in report:                       # "Don't remind me" stops counting
            self.v.set_meta(r["id"], mute=True)
        self.assertEqual(health_score(self.v.entry_count, self.v.security_report()), 100)


class LeakCheckTests(unittest.TestCase):
    def test_only_five_characters_are_sent(self):
        asked = []
        leaked_pw = hashlib.sha1(b"password123").hexdigest().upper()
        safe_pw = hashlib.sha1(b"a very unusual password").hexdigest().upper()

        def fake(prefix):
            asked.append(prefix)
            return f"{leaked_pw[5:]}:42\r\n{'0' * 35}:0\r\n"   # plus a padding line
        found = leakcheck.leaked_ids({"a": leaked_pw, "b": safe_pw}, fetch=fake)
        self.assertEqual(found, {"a"})
        self.assertTrue(all(len(p) == 5 for p in asked))

    def test_padding_lines_never_match(self):
        h = hashlib.sha1(b"x").hexdigest().upper()
        self.assertEqual(leakcheck.leaked_ids({"a": h}, fetch=lambda p: f"{h[5:]}:0\n"), set())


class SyncOrganizeTests(unittest.TestCase):
    def test_folders_and_favorites_sync(self):
        server = FakeSupabase()
        a, b = Computer(server), Computer(server)
        try:
            a.vault = Vault(EMAIL, a.folder)
            a.vault.create(MASTER)
            i = a.vault.add("Steam", "john_doe", "pw-1")
            a.syncer.remember_session(a.sign_in_with_code())
            g = a.vault.add_folder("Gaming", "#8C9EFF")
            a.vault.set_meta(i, folder=g, fav=True)
            a.sync()
            session = b.sign_in_with_code()
            v = Vault.save_cloud_copy(EMAIL, b.folder, b.syncer.download_for_new_computer(session))
            v.unlock(MASTER)
            b.vault = v
            self.assertEqual(v.folders()[0]["name"], "Gaming")
            self.assertTrue(v.get(i)["fav"])
            time.sleep(1.1)
            v.add_folder("School", "#5AB4FF")        # newer folder list on B wins
            b.sync()
            a.sync()
            self.assertEqual([f["name"] for f in a.vault.folders()], ["Gaming", "School"])
        finally:
            a.tmp.cleanup()
            b.tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
