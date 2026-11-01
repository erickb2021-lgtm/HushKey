"""Tests for cloud.py against a fake Supabase server (no internet needed)."""

import io
import json
import unittest
import urllib.error

from cloud import Cloud, CloudError, Session


class FakeSupabase:
    """Pretends to be Supabase: emails codes, checks them, stores secrets."""

    def __init__(self):
        self.sent = []          # emails a code was sent to
        self.rows = {}          # (user_id, vault_id) -> secret
        self.requests = []

    def __call__(self, req):
        self.requests.append(req)
        path = req.full_url.split(".co", 1)[1]
        body = json.loads(req.data) if req.data else None
        token = req.get_header("Authorization")
        if path == "/auth/v1/otp":
            self.sent.append(body["email"])
            return self._ok({})
        if path == "/auth/v1/verify":
            if body["token"] != "123456":
                return self._err(403, {"msg": "Token has expired or is invalid"})
            return self._ok({"access_token": "tok-" + body["email"], "user": {"id": "uid-" + body["email"]}})
        if path.startswith("/rest/v1/recovery_keys"):
            if not token:
                return self._err(401, {"message": "no auth"})
            uid = "uid-" + token.split("tok-", 1)[1]
            if req.get_method() == "POST":
                assert body["user_id"] == uid  # RLS would block anything else
                self.rows[(uid, body["vault_id"])] = body["secret"]
                return self._ok(None)
            vault_id = path.split("vault_id=eq.", 1)[1].split("&", 1)[0]
            secret = self.rows.get((uid, vault_id))
            return self._ok([{"secret": secret}] if secret else [])
        return self._err(404, {})

    @staticmethod
    def _ok(payload):
        return io.BytesIO(b"" if payload is None else json.dumps(payload).encode())

    @staticmethod
    def _err(code, payload):
        raise urllib.error.HTTPError("x", code, "err", {}, io.BytesIO(json.dumps(payload).encode()))


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeSupabase()
        self.cloud = Cloud("https://demo.supabase.co", "sb_publishable_test", opener=self.server)

    def test_not_configured(self):
        c = Cloud("", "")
        self.assertFalse(c.configured)
        with self.assertRaises(CloudError):
            c.send_code("a@b.com")

    def test_full_round_trip(self):
        self.cloud.send_code("a@b.com")
        self.assertEqual(self.server.sent, ["a@b.com"])
        s = self.cloud.verify_code("a@b.com", " 123 456 ")
        self.assertIsInstance(s, Session)
        self.cloud.store_secret(s, "vault1", b"\x01" * 32)
        self.assertEqual(self.cloud.fetch_secret(s, "vault1"), b"\x01" * 32)
        self.assertEqual(self.server.requests[0].get_header("Apikey"), "sb_publishable_test")

    def test_wrong_code(self):
        with self.assertRaises(CloudError) as ctx:
            self.cloud.verify_code("a@b.com", "999999")
        self.assertIn("wrong or has expired", str(ctx.exception))

    def test_short_code_rejected_locally(self):
        with self.assertRaises(CloudError):
            self.cloud.verify_code("a@b.com", "12")
        self.assertEqual(self.server.requests, [])

    def test_other_users_secret_not_visible(self):
        s1 = self.cloud.verify_code("a@b.com", "123456")
        s2 = self.cloud.verify_code("evil@b.com", "123456")
        self.cloud.store_secret(s1, "vault1", b"\x02" * 32)
        with self.assertRaises(CloudError):
            self.cloud.fetch_secret(s2, "vault1")

    def test_offline(self):
        def boom(req):
            raise urllib.error.URLError("no network")
        c = Cloud("https://demo.supabase.co", "k", opener=boom)
        with self.assertRaises(CloudError) as ctx:
            c.send_code("a@b.com")
        self.assertIn("internet", str(ctx.exception))

    def test_rate_limit_message(self):
        def limited(req):
            FakeSupabase._err(429, {"msg": "email rate limit exceeded"})
        c = Cloud("https://demo.supabase.co", "k", opener=limited)
        with self.assertRaises(CloudError) as ctx:
            c.send_code("a@b.com")
        self.assertIn("Too many", str(ctx.exception))


class EndToEndRecoveryTest(unittest.TestCase):
    """Create a vault with email recovery, forget the password, reset it."""

    def test_forgot_password_flow(self):
        import tempfile
        from vault import Vault, new_recovery_secret, new_vault_id

        server = FakeSupabase()
        cloud = Cloud("https://demo.supabase.co", "k", opener=server)
        with tempfile.TemporaryDirectory() as folder:
            # sign up: verify email, store secret online, then create the vault
            cloud.send_code("me@x.com")
            s = cloud.verify_code("me@x.com", "123456")
            secret, vid = new_recovery_secret(), new_vault_id()
            cloud.store_secret(s, vid, secret)
            v = Vault("me@x.com", folder)
            v.create("original master", secret, vid)
            eid = v.add("Riot account 1", "summoner99", "pw!")
            v.lock()

            # forgot password: new code, fetch secret, reset
            v = Vault("me@x.com", folder)
            s2 = cloud.verify_code("me@x.com", "123456")
            reset = v.start_recovery(cloud.fetch_secret(s2, v.vault_id))
            reset.complete("brand new master", "brand new master")

            v = Vault("me@x.com", folder)
            v.unlock("brand new master")
            self.assertEqual(v.reveal(eid), ("summoner99", "pw!"))


if __name__ == "__main__":
    unittest.main()
