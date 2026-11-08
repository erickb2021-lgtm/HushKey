"""Tests for 'Remember this device for 30 days' (stay signed in)."""

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "app"))

import json
import os
import tempfile
import unittest

import device_lock
import vault as vmod
from vault import TamperError, Vault, VaultError

EMAIL, MASTER = "me@x.com", "master password 1"


class AutoSigninTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        v = Vault(EMAIL, self.dir)
        v.create(MASTER)
        self.eid = v.add("Riot Games", "summoner99", "Gx7!pQ2m")
        self.key = v.enable_auto_signin()
        v.lock()

    def tearDown(self):
        self.tmp.cleanup()

    def test_opens_without_master_password(self):
        v = Vault(EMAIL, self.dir)
        v.unlock_with_device_key(self.key)
        self.assertEqual(v.reveal(self.eid), ("summoner99", "Gx7!pQ2m"))
        self.assertGreater(v.auto_signin_until, 0)

    def test_wrong_key_refused(self):
        with self.assertRaises(VaultError):
            Vault(EMAIL, self.dir).unlock_with_device_key(os.urandom(32))

    def test_expires_after_30_days(self):
        real = vmod.time.time
        vmod.time.time = lambda: real() + 31 * 86400
        try:
            with self.assertRaises(VaultError) as ctx:
                Vault(EMAIL, self.dir).unlock_with_device_key(self.key)
            self.assertIn("30 days", str(ctx.exception))
        finally:
            vmod.time.time = real

    def test_other_computer_refused(self):
        real = vmod.device_id
        vmod.device_id = lambda: "another-computer"
        try:
            with self.assertRaises(VaultError):
                Vault(EMAIL, self.dir).unlock_with_device_key(self.key)
        finally:
            vmod.device_id = real

    def test_cannot_extend_by_editing_the_file(self):
        v = Vault(EMAIL, self.dir)
        with open(v.path, encoding="utf-8") as f:
            data = json.load(f)
        data["auto_signin"]["until"] = 9999999999
        with open(v.path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        with self.assertRaises(TamperError):
            Vault(EMAIL, self.dir).unlock_with_device_key(self.key)

    def test_sign_out_turns_it_off(self):
        v = Vault(EMAIL, self.dir)
        v.unlock(MASTER)
        v.disable_auto_signin()
        v.lock()
        with self.assertRaises(VaultError):
            Vault(EMAIL, self.dir).unlock_with_device_key(self.key)

    def test_password_reset_turns_it_off(self):
        v = Vault(EMAIL, self.dir)
        v.unlock(MASTER)
        secret = vmod.new_recovery_secret()
        v.enable_recovery(secret)
        v.lock()
        Vault(EMAIL, self.dir).start_recovery(secret).complete("new master pw", "new master pw")
        with self.assertRaises(VaultError):
            Vault(EMAIL, self.dir).unlock_with_device_key(self.key)

    def test_device_storage_round_trip(self):
        device_lock.save(EMAIL, self.key, self.dir)
        self.assertEqual(device_lock.load(EMAIL, self.dir), self.key)
        self.assertIsNone(device_lock.load("someone@else.com", self.dir))
        device_lock.delete(EMAIL, self.dir)
        self.assertIsNone(device_lock.load(EMAIL, self.dir))


class SurvivesRestartTests(unittest.TestCase):
    """The computer's fingerprint must stay the same from one launch to the next. It used to
    come from the network card's address, which Python makes up (randomly, every launch)
    on PCs where it can't read it, so 'Remember this device' never remembered anything."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.real_getnode = vmod.uuid.getnode

    def tearDown(self):
        vmod.uuid.getnode = self.real_getnode
        vmod._device_ids.clear()
        self.tmp.cleanup()

    @staticmethod
    def new_launch(made_up_address):
        """Like closing HushKey and opening it again on a PC with no readable network address."""
        vmod._device_ids.clear()
        vmod.uuid.getnode = lambda: made_up_address | (1 << 40)

    def test_stays_signed_in_after_a_restart(self):
        self.new_launch(0x1234)
        v = Vault(EMAIL, self.dir)
        v.create(MASTER)
        v.remember_device()
        key = v.enable_auto_signin()
        v.lock()
        self.new_launch(0x9876)   # a different made-up address this time
        v2 = Vault(EMAIL, self.dir)
        v2.unlock_with_device_key(key)
        self.assertTrue(v2.is_device_remembered(), "no email code needed either")
        self.assertGreater(v2.auto_signin_until, 0)

    def test_remembered_by_an_older_version_still_works(self):
        vmod.uuid.getnode = lambda: 0x00163E5E6C00   # a real address (the old fingerprint used it)
        vmod._device_ids.clear()
        old = vmod.legacy_device_id()
        self.assertIsNotNone(old)
        v = Vault(EMAIL, self.dir)
        v.create(MASTER)
        key = v.enable_auto_signin()
        v._data["auto_signin"]["device"] = old          # what an older HushKey saved
        v._data["devices"] = {old: 9999999999}
        v._save()
        v.lock()
        v2 = Vault(EMAIL, self.dir)
        v2.unlock_with_device_key(key)
        self.assertTrue(v2.is_device_remembered())
        saved = json.load(open(v2.path))
        self.assertEqual(saved["auto_signin"]["device"], vmod.device_id(), "moved to the new fingerprint")
        self.assertIn(vmod.device_id(), saved["devices"])

    def test_made_up_address_is_never_trusted(self):
        vmod.uuid.getnode = lambda: 0x1234 | (1 << 40)
        vmod._device_ids.clear()
        self.assertIsNone(vmod.legacy_device_id())


if __name__ == "__main__":
    unittest.main()
