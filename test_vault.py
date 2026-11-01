"""Tests for vault.py.  Run with:  python -m unittest -v"""

import json
import os
import tempfile
import unittest

from vault import (TamperError, Vault, VaultError, WrongPassword,
                   generate_password, looks_like_email, new_recovery_secret,
                   password_strength)

EMAIL = "Erick@Example.com"
MASTER = "correct horse battery"


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.secret = new_recovery_secret()

    def tearDown(self):
        self.tmp.cleanup()

    def new_vault(self, recovery=True):
        v = Vault(EMAIL, self.dir)
        v.create(MASTER, self.secret if recovery else None)
        return v

    def fresh(self, email=EMAIL):
        return Vault(email, self.dir)

    def load(self, v):
        with open(v.path, encoding="utf-8") as f:
            return json.load(f)

    def dump(self, v, data):
        with open(v.path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    # ---- basics ----

    def test_create_and_unlock(self):
        v = self.new_vault()
        v.add("Riot account 1", "summoner99", "hunter2!")
        v.lock()
        v2 = self.fresh("  erick@example.COM ")  # email is case/space-insensitive
        v2.unlock(MASTER)
        (eid, title), = v2.list_titles()
        self.assertEqual(title, "Riot account 1")
        self.assertEqual(v2.reveal(eid), ("summoner99", "hunter2!"))

    def test_wrong_password(self):
        self.new_vault()
        with self.assertRaises(WrongPassword):
            self.fresh().unlock("not the password")

    def test_other_email_has_no_vault(self):
        self.new_vault()
        with self.assertRaises(VaultError):
            self.fresh("someone@else.com").unlock(MASTER)

    def test_two_emails_two_vaults(self):
        self.new_vault()
        other = Vault("friend@example.com", self.dir)
        other.create("another password")
        self.assertNotEqual(other.path, self.fresh().path)

    def test_nothing_readable_on_disk(self):
        v = self.new_vault()
        v.add("Riot account 1", "summoner99", "hunter2!")
        with open(v.path, encoding="utf-8") as f:
            raw = f.read()
        for secret in ("Riot", "summoner99", "hunter2", MASTER, "erick"):
            self.assertNotIn(secret.lower(), raw.lower())
        self.assertNotIn("erick", os.path.basename(v.path))

    def test_update_delete(self):
        v = self.new_vault()
        eid = v.add("A", "u", "p")
        v.update(eid, "B", "u2", "p2")
        self.assertEqual(v.get(eid)["title"], "B")
        self.assertEqual(v.reveal(eid), ("u2", "p2"))
        v.delete(eid)
        self.assertEqual(v.list_titles(), [])

    def test_change_master_keeps_recovery_working(self):
        v = self.new_vault()
        eid = v.add("Riot", "u", "p")
        v.change_master(MASTER, "a brand new master", "a brand new master")
        v.lock()
        with self.assertRaises(WrongPassword):
            self.fresh().unlock(MASTER)
        reset = self.fresh().start_recovery(self.secret)
        reset.complete("third password!", "third password!")
        v2 = self.fresh()
        v2.unlock("third password!")
        self.assertEqual(v2.reveal(eid), ("u", "p"))

    def test_bad_new_master(self):
        with self.assertRaises(VaultError):
            Vault(EMAIL, self.dir).create("short")
        v = self.new_vault()
        with self.assertRaises(VaultError):
            v.change_master(MASTER, "longenough1", "longenough2")

    def test_locked_vault_refuses(self):
        v = self.new_vault()
        v.lock()
        with self.assertRaises(VaultError):
            v.list_titles()

    # ---- recovery ----

    def test_recovery_resets_master_and_keeps_entries(self):
        v = self.new_vault()
        eid = v.add("Riot account 1", "summoner99", "hunter2!")
        v.lock()
        reset = self.fresh().start_recovery(self.secret)
        reset.complete("my new master pw", "my new master pw")
        with self.assertRaises(WrongPassword):
            self.fresh().unlock(MASTER)
        v2 = self.fresh()
        v2.unlock("my new master pw")
        self.assertEqual(v2.reveal(eid), ("summoner99", "hunter2!"))

    def test_nothing_changes_until_reset_clicked(self):
        v = self.new_vault()
        v.add("Keep", "a", "b")
        v.lock()
        with open(v.path, "rb") as f:
            before = f.read()
        reset = self.fresh().start_recovery(self.secret)
        with self.assertRaises(VaultError):
            reset.complete("mismatch one", "mismatch two")  # typo in retype
        reset.cancel()
        with open(v.path, "rb") as f:
            self.assertEqual(before, f.read())
        self.fresh().unlock(MASTER)  # old password still works
        with self.assertRaises(VaultError):
            reset.complete("new password 1", "new password 1")  # cancelled = dead

    def test_wrong_recovery_secret_rejected(self):
        self.new_vault()
        with self.assertRaises(VaultError):
            self.fresh().start_recovery(new_recovery_secret())

    def test_no_recovery_vault(self):
        v = self.new_vault(recovery=False)
        self.assertFalse(v.has_recovery)
        with self.assertRaises(VaultError):
            self.fresh().start_recovery(self.secret)

    # ---- tampering ----

    def test_edited_entry_detected(self):
        v = self.new_vault()
        v.add("Site", "me", "pw")
        data = self.load(v)
        tok = data["entries"][0]["password"]
        data["entries"][0]["password"] = tok[:-6] + ("A" if tok[-6] != "A" else "B") + tok[-5:]
        self.dump(v, data)
        with self.assertRaises(TamperError):
            self.fresh().unlock(MASTER)

    def test_deleted_entry_detected(self):
        v = self.new_vault()
        v.add("Keep", "a", "b")
        v.add("Remove me", "c", "d")
        data = self.load(v)
        data["entries"].pop()
        self.dump(v, data)
        with self.assertRaises(TamperError):
            self.fresh().unlock(MASTER)

    def test_weakened_settings_detected(self):
        v = self.new_vault()
        data = self.load(v)
        data["kdf"]["iterations"] = 1
        self.dump(v, data)
        with self.assertRaises(VaultError):
            self.fresh().unlock(MASTER)

    def test_removed_recovery_detected(self):
        v = self.new_vault()
        data = self.load(v)
        data["recovery"] = None
        self.dump(v, data)
        with self.assertRaises(TamperError):
            self.fresh().unlock(MASTER)

    def test_backup_kept(self):
        v = self.new_vault()
        v.add("First", "a", "b")
        self.assertTrue(os.path.isfile(v.backup_path))

    # ---- logos + remember device ----

    def test_logo_saved_encrypted(self):
        v = self.new_vault()
        eid = v.add("Riot main", "u", "p", icon="riotgames")
        self.assertEqual(v.list_entries()[0]["icon"], "riotgames")
        with open(v.path, encoding="utf-8") as f:
            self.assertNotIn("riotgames", f.read())
        v.update(eid, "Riot main", "u", "p", icon="")
        self.assertEqual(v.get(eid)["icon"], "")

    def test_remember_device(self):
        v = self.new_vault()
        self.assertFalse(v.is_device_remembered())
        v.remember_device()
        v.lock()
        v2 = self.fresh()
        v2.unlock(MASTER)
        self.assertTrue(v2.is_device_remembered())
        v2.forget_device()
        self.assertFalse(v2.is_device_remembered())

    def test_remembered_device_expires(self):
        v = self.new_vault()
        v.remember_device(days=-1)
        self.assertFalse(v.is_device_remembered())

    def test_copied_vault_on_other_computer_not_remembered(self):
        import vault as vmod
        v = self.new_vault()
        v.remember_device()
        real = vmod.device_id
        vmod.device_id = lambda: "some-other-computer"
        try:
            self.assertFalse(v.is_device_remembered())
        finally:
            vmod.device_id = real

    def test_faked_remember_flag_detected(self):
        v = self.new_vault()
        data = self.load(v)
        from vault import device_id
        data["devices"] = {device_id(): 9999999999}  # attacker edits the file
        self.dump(v, data)
        with self.assertRaises(TamperError):
            self.fresh().unlock(MASTER)

    # ---- helpers ----

    def test_generate_password(self):
        pw = generate_password(18)
        self.assertEqual(len(pw), 18)
        self.assertNotEqual(pw, generate_password(18))
        self.assertTrue(any(not c.isalnum() for c in pw))

    def test_strength(self):
        self.assertEqual(password_strength("")[0], 0)
        self.assertLessEqual(password_strength("abc")[0], 1)
        self.assertEqual(password_strength(generate_password(18))[0], 4)

    def test_email_check(self):
        self.assertTrue(looks_like_email("a@b.co"))
        for bad in ("", "abc", "a@b", "a b@c.com", "@b.com", "a@@b.com"):
            self.assertFalse(looks_like_email(bad), bad)


if __name__ == "__main__":
    unittest.main()
