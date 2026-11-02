"""Two computers, one account: tests for encrypted sync.  python -m unittest -v"""

import json
import os
import tempfile
import time
import unittest

from cloud import Cloud, SessionExpired
from sync import Syncer, VaultMismatch
from test_cloud import FakeSupabase
from vault import TamperError, Vault, WrongPassword, merge_vaults

EMAIL, MASTER = "me@x.com", "master password 1"


class Computer:
    """One computer: its own folder (vault file + protected storage)."""

    def __init__(self, server):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = self.tmp.name
        self.cloud = Cloud("https://demo.supabase.co", "k", opener=server)
        self.syncer = Syncer(self.cloud, EMAIL, self.folder)
        self.vault = None

    def sign_in_with_code(self):
        self.cloud.send_code(EMAIL)
        return self.cloud.verify_code(EMAIL, "123456")

    def sync(self):
        row = self.syncer.fetch()
        plan = self.syncer.reconcile(self.vault, row)
        self.syncer.upload(plan)
        return plan


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeSupabase()
        self.a = Computer(self.server)
        self.b = Computer(self.server)
        # computer A: make a vault and turn on sync
        self.a.vault = Vault(EMAIL, self.a.folder)
        self.a.vault.create(MASTER)
        self.riot = self.a.vault.add("Riot Games", "summoner99", "riot-pw", "riotgames")
        self.a.syncer.remember_session(self.a.sign_in_with_code())
        self.a.sync()

    def tearDown(self):
        self.a.tmp.cleanup()
        self.b.tmp.cleanup()

    def new_computer_b(self, master=MASTER):
        session = self.b.sign_in_with_code()
        data = self.b.syncer.download_for_new_computer(session)
        v = Vault.save_cloud_copy(EMAIL, self.b.folder, data)
        v.unlock(master)
        self.b.vault = v
        return v

    def test_server_never_sees_logins(self):
        stored = self.server.vaults["uid-" + EMAIL]["data"]
        for secret in ("Riot", "summoner99", "riot-pw", MASTER):
            self.assertNotIn(secret, stored)

    def test_sign_in_on_new_computer_gets_everything(self):
        v = self.new_computer_b()
        self.assertEqual(v.reveal(self.riot), ("summoner99", "riot-pw"))
        self.assertEqual(v.list_entries()[0]["icon"], "riotgames")

    def test_new_computer_wrong_password(self):
        session = self.b.sign_in_with_code()
        data = self.b.syncer.download_for_new_computer(session)
        v = Vault.save_cloud_copy(EMAIL, self.b.folder, data)
        with self.assertRaises(WrongPassword):
            v.unlock("not my password")

    def test_changes_flow_both_ways(self):
        self.new_computer_b()
        steam = self.b.vault.add("Steam", "erick_s", "steam-pw")
        self.b.sync()
        netflix = self.a.vault.add("Netflix", "e@x.com", "nflx-pw")
        self.a.sync()
        self.b.sync()
        for v in (self.a.vault, self.b.vault):
            self.assertEqual(sorted(e["title"] for e in v.list_entries()), ["Netflix", "Riot Games", "Steam"])
        self.assertEqual(self.a.vault.reveal(steam), ("erick_s", "steam-pw"))
        self.assertEqual(self.b.vault.reveal(netflix), ("e@x.com", "nflx-pw"))

    def test_newest_edit_wins(self):
        self.new_computer_b()
        time.sleep(1.1)  # timestamps are per second
        self.b.vault.update(self.riot, "Riot Games", "summoner99", "NEW-riot-pw", "riotgames")
        self.b.sync()
        self.a.sync()
        self.assertEqual(self.a.vault.reveal(self.riot)[1], "NEW-riot-pw")

    def test_deletion_syncs_and_stays_deleted(self):
        self.new_computer_b()
        self.b.vault.delete(self.riot)
        self.b.sync()
        self.a.sync()
        self.assertEqual(self.a.vault.list_entries(), [])
        self.a.sync()
        self.b.sync()
        self.assertEqual(self.b.vault.list_entries(), [])  # didn't come back

    def test_master_password_change_follows(self):
        self.new_computer_b()
        time.sleep(1.1)
        self.a.vault.change_master(MASTER, "brand new master", "brand new master")
        self.a.sync()
        self.b.sync()
        self.b.vault.lock()
        with self.assertRaises(WrongPassword):
            Vault(EMAIL, self.b.folder).unlock(MASTER)
        Vault(EMAIL, self.b.folder).unlock("brand new master")

    def test_remembered_devices_stay_local(self):
        self.a.vault.enable_auto_signin()
        self.a.vault.remember_device()
        self.a.sync()
        stored = json.loads(self.server.vaults["uid-" + EMAIL]["data"])
        self.assertNotIn("auto_signin", stored)
        self.assertNotIn("devices", stored)

    def test_tampered_server_copy_refused(self):
        self.new_computer_b()
        row = self.server.vaults["uid-" + EMAIL]
        data = json.loads(row["data"])
        data["entries"] = []          # the server tries to delete everything
        row["data"] = json.dumps(data)
        with self.assertRaises(TamperError):
            self.b.sync()
        self.assertEqual(len(self.b.vault.list_entries()), 1)

    def test_nothing_to_upload_when_up_to_date(self):
        self.assertIsNone(self.a.sync())

    def test_refresh_token_keeps_working_without_codes(self):
        self.a.syncer._session = None            # app restarted
        self.a.vault.add("Discord", "erick", "disc-pw")
        self.a.sync()                            # uses the saved refresh token
        self.assertTrue(self.a.syncer.enabled)
        self.a.syncer._session = None
        self.a.sync()                            # tokens rotate; the new one is saved

    def test_expired_sign_in_pauses_sync(self):
        self.server.refresh_tokens.clear()
        self.a.syncer._session = None
        with self.assertRaises(SessionExpired):
            self.a.sync()
        self.assertFalse(self.a.syncer.enabled)

    def test_two_separate_vaults_can_be_combined(self):
        # computer B made its own vault before sync existed
        b = Vault(EMAIL, self.b.folder)
        b.create("b master password")
        b.add("Steam", "erick_s", "steam-pw")
        self.b.vault = b
        self.b.syncer.remember_session(self.b.sign_in_with_code())
        with self.assertRaises(VaultMismatch) as ctx:
            self.b.sync()
        cloud_vault = Vault.open_cloud_copy(ctx.exception.cloud_data, MASTER)
        copied = b.adopt(cloud_vault)
        self.assertEqual(copied, 1)
        self.b.sync()
        self.a.sync()
        self.assertEqual(sorted(e["title"] for e in self.a.vault.list_entries()), ["Riot Games", "Steam"])
        b.lock()
        Vault(EMAIL, self.b.folder).unlock(MASTER)  # B now uses the shared vault's password

    def test_merge_is_pure(self):
        local = {"entries": [{"id": "1", "updated": "2026-01-01T00:00:00+00:00"}], "deleted": {},
                 "devices": {"x": 1}, "seal": "s"}
        cloud = {"entries": [{"id": "2", "updated": "2026-01-02T00:00:00+00:00"}],
                 "deleted": {"1": "2026-01-03T00:00:00+00:00"}}
        merged = merge_vaults(local, cloud)
        self.assertEqual([e["id"] for e in merged["entries"]], ["2"])
        self.assertNotIn("devices", merged)
        self.assertNotIn("seal", merged)


if __name__ == "__main__":
    unittest.main()
