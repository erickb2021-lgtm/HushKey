"""
cloud.py - talks to Supabase for email codes and recovery secrets.

Uses only Python's built-in urllib (plus certifi for up-to-date security
certificates, which matters inside the packaged Mac and Windows apps).

What goes online:     your email, and a random 32-byte recovery secret.
What NEVER goes online: your master password, your vault file, your logins.
"""

import base64
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

try:
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:  # certifi missing: fall back to the system's certificates
    _SSL = ssl.create_default_context()

try:
    import cloud_config as _config
except ImportError:  # pragma: no cover
    _config = None

TIMEOUT = 20  # seconds


class CloudError(Exception):
    """A friendly, show-it-to-the-user error."""


class SessionExpired(CloudError):
    """The saved sign-in for syncing ran out; an email code is needed again."""


@dataclass
class Session:
    access_token: str
    user_id: str
    refresh_token: str = ""   # lets sync keep working without a new code every hour
    expires_at: float = 0.0


class Cloud:
    def __init__(self, url: str | None = None, key: str | None = None, opener=None):
        self.url = (url if url is not None else getattr(_config, "SUPABASE_URL", "")).rstrip("/")
        self.key = key if key is not None else getattr(_config, "SUPABASE_PUBLIC_KEY", "")
        # opener lets the tests swap in a fake server
        self._open = opener or (lambda req: urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL))

    @property
    def configured(self) -> bool:
        return self.url.startswith("https://") and bool(self.key)

    # ---- low level ---------------------------------------------------------

    def _request(self, method: str, path: str, body=None, token: str | None = None,
                 extra_headers: dict | None = None, sync: bool = False):
        if not self.configured:
            raise CloudError("Email recovery isn't set up in this copy of HushKey.")
        headers = {"apikey": self.key, "Content-Type": "application/json",
                   "Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        headers.update(extra_headers or {})
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers)
        try:
            resp = self._open(req)
            raw = resp.read()
            return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            raw = e.read()
            if sync and e.code in (400, 401, 403):
                raise SessionExpired("Sync needs you to confirm your email again.")
            raise CloudError(self._friendly(e.code, raw))
        except (urllib.error.URLError, TimeoutError, OSError):
            raise CloudError("Couldn't reach the recovery service. Check your internet connection.")

    @staticmethod
    def _friendly(status: int, raw: bytes) -> str:
        try:
            info = json.loads(raw or b"{}")
        except ValueError:
            info = {}
        msg = " ".join(str(info.get(k, "")) for k in ("msg", "message", "error_description", "error_code")).lower()
        if status == 429 or "rate" in msg:
            return "Too many emails or tries. Wait a few minutes and try again."
        if "expired" in msg or "invalid" in msg or status in (401, 403):
            return "That code is wrong or has expired. Check it, or send a new one."
        if status >= 500:
            return "The recovery service is having trouble right now. Try again soon."
        return "Something went wrong with the recovery service (error %d)." % status

    # ---- email codes -------------------------------------------------------

    def send_code(self, email: str) -> None:
        """Email a one-time code to this address."""
        self._request("POST", "/auth/v1/otp", {"email": email, "create_user": True})

    def verify_code(self, email: str, code: str) -> Session:
        """Check the code. Returns a short-lived session that proves email ownership."""
        code = "".join(ch for ch in code if ch.isdigit())
        if not 6 <= len(code) <= 10:
            raise CloudError("Enter the code from the email (just the numbers).")
        data = self._request("POST", "/auth/v1/verify", {"type": "email", "email": email, "token": code})
        return self._session(data)

    @staticmethod
    def _session(data) -> Session:
        import time
        try:
            return Session(data["access_token"], data["user"]["id"], data.get("refresh_token", ""),
                           time.time() + float(data.get("expires_in", 3600)) - 60)
        except (TypeError, KeyError, ValueError):
            raise CloudError("The recovery service sent an unexpected reply.")

    def refresh(self, refresh_token: str) -> Session:
        """Swap a saved refresh token for a fresh session (no email code needed).
        Supabase hands back a NEW refresh token each time; save it."""
        if not refresh_token:
            raise SessionExpired("Sync needs you to confirm your email again.")
        data = self._request("POST", "/auth/v1/token?grant_type=refresh_token",
                             {"refresh_token": refresh_token}, sync=True)
        return self._session(data)

    # ---- recovery secrets --------------------------------------------------

    def store_secret(self, session: Session, vault_id: str, secret: bytes) -> None:
        self._request(
            "POST", "/rest/v1/recovery_keys",
            {"user_id": session.user_id, "vault_id": vault_id,
             "secret": base64.b64encode(secret).decode("ascii")},
            token=session.access_token,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    # ---- encrypted vault sync ---------------------------------------------
    # Only the ENCRYPTED vault is uploaded. Supabase can't read a single login:
    # the key is your master password, which never leaves your computer.

    def get_vault(self, session: Session):
        """The encrypted vault saved in this account, or None."""
        rows = self._request("GET", "/rest/v1/vaults?select=vault_id,data,rev&limit=1",
                             token=session.access_token, sync=True)
        if not rows:
            return None
        row = rows[0]
        try:
            return {"vault_id": row["vault_id"], "data": json.loads(row["data"]), "rev": int(row.get("rev") or 0)}
        except (KeyError, ValueError, TypeError):
            raise CloudError("The synced vault in your account is damaged.")

    def put_vault(self, session: Session, vault_id: str, data_json: str, rev: int) -> None:
        self._request(
            "POST", "/rest/v1/vaults",
            {"user_id": session.user_id, "vault_id": vault_id, "data": data_json, "rev": rev},
            token=session.access_token, sync=True,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"})

    def fetch_secret(self, session: Session, vault_id: str) -> bytes:
        query = urllib.parse.urlencode({"vault_id": "eq." + vault_id, "select": "secret"})
        rows = self._request("GET", "/rest/v1/recovery_keys?" + query, token=session.access_token)
        if not rows:
            raise CloudError("No recovery key was found for this email and vault.")
        try:
            return base64.b64decode(rows[0]["secret"])
        except (KeyError, ValueError, TypeError):
            raise CloudError("The stored recovery key is damaged.")
