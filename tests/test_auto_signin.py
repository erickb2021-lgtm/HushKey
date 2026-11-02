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


if __name__ == "__main__":
    unittest.main()
