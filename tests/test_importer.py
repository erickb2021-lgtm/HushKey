"""Tests for importing and exporting passwords.  Run with:  python -m unittest -v"""

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "app"))

import os
import tempfile
import unittest

import importer
from importer import ImportError_, read_csv_file, read_csv_text, secure_delete, write_csv
from vault import Vault, WrongPassword

GOOGLE = """name,url,username,password,note
riotgames.com,https://auth.riotgames.com/login,summoner99,Gx7!pQ2m,
accounts.google.com,https://accounts.google.com/,john@gmail.com,g00gle-pw,
netflix.com,https://www.netflix.com/login,john@gmail.com,nflx-pw,
mybank.example,https://mybank.example/login,john,bank-pw,
nopassword.com,https://nopassword.com,someone,,
"""

BITWARDEN = """folder,favorite,type,name,notes,fields,reminder,login_uri,login_username,login_password,login_totp
,,login,Discord,,,,https://discord.com/login,john#1234,disc-pw,
,,note,My secret note,hello,,,,,,
,,login,Steam,,,,https://store.steampowered.com,john_steam,steam-pw,
"""

FIREFOX = """"url","username","password","httpRealm","formActionOrigin","guid","timeCreated","timeLastUsed","timePasswordChanged"
"https://www.reddit.com","john_r","reddit-pw",,"https://www.reddit.com","{abc}","1","1","1"
"""

LASTPASS = """url,username,password,totp,extra,name,grouping,fav
https://www.paypal.com,john@gmail.com,pp-pw,,,PayPal,Money,0
"""

ONEPASSWORD = """Title,Url,Username,Password,OTPAuth,Favorite,Archived,Tags,Notes
Spotify,https://open.spotify.com,john,spot-pw,,false,false,,
"""

APPLE = """Title,URL,Username,Password,Notes,OTPAuth
Instagram (john),https://www.instagram.com,john.b,insta-pw,,
"""


class ImportTests(unittest.TestCase):
    def test_google_export(self):
        r = read_csv_text(GOOGLE)
        self.assertEqual(r.source, "Google / Chrome")
        self.assertEqual(r.skipped, 1)  # the row without a password
        titles = [i.title for i in r.items]
        self.assertEqual(titles, ["Riot Games", "Google", "Netflix", "Mybank"])
        riot = r.items[0]
        self.assertEqual((riot.username, riot.password, riot.icon), ("summoner99", "Gx7!pQ2m", "riotgames"))
        self.assertTrue(all(i.selected for i in r.items))

    def test_other_managers(self):
        cases = [(BITWARDEN, "Bitwarden", ["Discord", "Steam"]),
                 (FIREFOX, "Firefox", ["Reddit"]),
                 (LASTPASS, "LastPass", ["PayPal"]),
                 (ONEPASSWORD, "1Password", ["Spotify"]),
                 (APPLE, "Apple Passwords", ["Instagram (john)"])]
        for text, source, titles in cases:
            r = read_csv_text(text)
            self.assertEqual(r.source, source, source)
            self.assertEqual([i.title for i in r.items], titles, source)
        self.assertEqual(read_csv_text(BITWARDEN).skipped, 1)  # the secure note

    def test_duplicates_flagged_and_unchecked(self):
        r = read_csv_text(GOOGLE, existing=[("Netflix", "JOHN@gmail.com")])
        netflix = [i for i in r.items if i.title == "Netflix"][0]
        self.assertTrue(netflix.duplicate)
        self.assertFalse(netflix.selected)

    def test_not_a_password_file(self):
        with self.assertRaises(ImportError_):
            read_csv_text("first,last,phone\nJohn,B,555\n")
        with self.assertRaises(ImportError_):
            read_csv_text("")

    def test_secure_delete(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "Google Passwords.csv")
            with open(path, "w") as f:
                f.write(GOOGLE)
            r = read_csv_file(path)
            self.assertEqual(len(r.items), 4)
            self.assertTrue(secure_delete(path))
            self.assertFalse(os.path.exists(path))

    def test_full_import_then_export_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            v = Vault("me@x.com", d)
            v.create("master password 1")
            r = read_csv_text(GOOGLE, v.existing_keys())
            added = v.add_many([i.__dict__ for i in r.items if i.selected])
            self.assertEqual(added, 4)
            riot = [e for e in v.all_entries() if e["title"] == "Riot Games"][0]
            self.assertEqual(riot["url"], "https://auth.riotgames.com/login")
            self.assertEqual(riot["icon"], "riotgames")
            # importing the same file again: everything is a duplicate
            again = read_csv_text(GOOGLE, v.existing_keys())
            self.assertTrue(all(i.duplicate and not i.selected for i in again.items))
            # export to CSV and read it back
            out = os.path.join(d, "export.csv")
            write_csv(out, v.all_entries())
            back = read_csv_file(out)
            self.assertEqual(sorted((i.username, i.password) for i in back.items),
                             sorted((e["username"], e["password"]) for e in v.all_entries()))

    def test_encrypted_backup_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            v = Vault("me@x.com", d)
            v.create("master password 1")
            v.add("Riot Games", "summoner99", "Gx7!pQ2m", "riotgames")
            backup = os.path.join(d, "HushKey backup.hushkey")
            v.export_backup(backup)
            with open(backup, encoding="utf-8") as f:
                self.assertNotIn("summoner99", f.read())  # still encrypted
            with self.assertRaises(WrongPassword):
                Vault.open_backup(backup, "wrong password")
            b = Vault.open_backup(backup, "master password 1")
            self.assertEqual([(e["title"], e["password"]) for e in b.all_entries()],
                             [("Riot Games", "Gx7!pQ2m")])

    def test_check_master(self):
        with tempfile.TemporaryDirectory() as d:
            v = Vault("me@x.com", d)
            v.create("master password 1")
            self.assertTrue(v.check_master("master password 1"))
            self.assertFalse(v.check_master("nope nope nope"))

    def test_nice_titles(self):
        self.assertEqual(importer.nice_title("", "https://www.bbc.co.uk/account"), "Bbc")
        self.assertEqual(importer.nice_title("Work laptop", "https://x.com"), "Work laptop")
        self.assertEqual(importer.nice_title("store.steampowered.com", ""), "Steam")
        self.assertEqual(importer.nice_title("login.live.com", ""), "Microsoft")
        self.assertEqual(importer.nice_title("", "https://www.amazon.com/ap/signin"), "Amazon")


if __name__ == "__main__":
    unittest.main()
