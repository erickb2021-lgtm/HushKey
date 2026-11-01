"""Tests for vault.py.  Run with:  python -m unittest -v"""

import json
import os
import tempfile
import unittest

from vault import Vault, VaultError, WrongPassword, generate_password

MASTER = "correct horse battery"


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "vault.json")

    def tearDown(self):
        self.tmp.cleanup()

    def new_vault(self):
        v = Vault(self.path)
        v.create(MASTER)
        return v

    def test_create_and_unlock(self):
        v = self.new_vault()
        v.add("Riot account 1", "summoner99", "hunter2!")
        v.lock()
        v2 = Vault(self.path)
        v2.unlock(MASTER)
        (entry_id, title), = v2.list_titles()
        self.assertEqual(title, "Riot account 1")
        self.assertEqual(v2.reveal(entry_id), ("summoner99", "hunter2!"))

    def test_wrong_password_rejected(self):
        self.new_vault()
        with self.assertRaises(WrongPassword):
            Vault(self.path).unlock("not the password")

    def test_nothing_readable_on_disk(self):
        v = self.new_vault()
        v.add("Riot account 1", "summoner99", "hunter2!")
        with open(self.path, encoding="utf-8") as f:
            raw = f.read()
        for secret in ("Riot", "summoner99", "hunter2", MASTER):
            self.assertNotIn(secret, raw)

    def _load(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _dump(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_edited_entry_detected(self):
        v = self.new_vault()
        v.add("Site", "me", "pw")
        data = self._load()
        tok = data["entries"][0]["password"]
        data["entries"][0]["password"] = tok[:-6] + ("A" if tok[-6] != "A" else "B") + tok[-5:]
        self._dump(data)
        with self.assertRaises(VaultError) as ctx:
            Vault(self.path).unlock(MASTER)
        self.assertNotIsInstance(ctx.exception, WrongPassword)

    def test_deleted_entry_detected(self):
        v = self.new_vault()
        v.add("Keep", "a", "b")
        v.add("Remove me", "c", "d")
        data = self._load()
        data["entries"].pop()
        self._dump(data)
        with self.assertRaises(VaultError):
            Vault(self.path).unlock(MASTER)

    def test_weakened_settings_detected(self):
        self.new_vault()
        data = self._load()
        data["iterations"] = 1  # attacker tries to make future guesses cheap
        self._dump(data)
        with self.assertRaises(VaultError):
            Vault(self.path).unlock(MASTER)

    def test_backup_kept(self):
        v = self.new_vault()
        v.add("First", "a", "b")
        self.assertTrue(os.path.isfile(v.backup_path))
        backup = Vault(v.backup_path)
        backup.unlock(MASTER)  # the backup is a valid, sealed vault too
        self.assertEqual(backup.list_titles(), [])

    def test_update_delete(self):
        v = self.new_vault()
        eid = v.add("A", "u", "p")
        v.update(eid, "B", "u2", "p2")
        self.assertEqual(v.get(eid)["title"], "B")
        self.assertEqual(v.reveal(eid), ("u2", "p2"))
        v.delete(eid)
        self.assertEqual(v.list_titles(), [])

    def test_change_master(self):
        v = self.new_vault()
        eid = v.add("Riot", "u", "p")
        v.change_master(MASTER, "a brand new master")
        v.lock()
        with self.assertRaises(WrongPassword):
            Vault(self.path).unlock(MASTER)
        v2 = Vault(self.path)
        v2.unlock("a brand new master")
        self.assertEqual(v2.reveal(eid), ("u", "p"))

    def test_short_master_rejected(self):
        with self.assertRaises(VaultError):
            Vault(self.path).create("short")

    def test_same_password_different_salt(self):
        """Two vaults with the same master password hash differently (salt)."""
        other = os.path.join(self.tmp.name, "other.json")
        self.new_vault()
        Vault(other).create(MASTER)
        a = self._load()["verifier"]
        with open(other, encoding="utf-8") as f:
            b = json.load(f)["verifier"]
        self.assertNotEqual(a, b)

    def test_locked_vault_refuses(self):
        v = self.new_vault()
        v.lock()
        with self.assertRaises(VaultError):
            v.list_titles()

    def test_generate_password(self):
        pw = generate_password(24)
        self.assertEqual(len(pw), 24)
        self.assertNotEqual(pw, generate_password(24))


if __name__ == "__main__":
    unittest.main()
