"""
sync.py - keep your vault the same on every computer you sign in to.

Zero-knowledge, the way Bitwarden and 1Password do it:
  - Only the ENCRYPTED vault is uploaded to your HushKey account (Supabase).
  - Your master password never leaves your computer, so nobody (not even
    whoever runs the server) can read a single login.
  - Every downloaded copy must pass the vault's tamper seal, so the server
    can't secretly change anything either.

Signing in for sync uses the 8-digit email code. After that, a refresh token
(kept in Windows' protected storage / the Mac Keychain) lets HushKey keep
syncing without asking for a code every time.

The app runs the slow parts (network) in the background and the merge on the
main thread, so a login you're saving can never be overwritten by a sync.
"""

import time

import device_lock
from cloud import Cloud, CloudError, Session, SessionExpired

KIND = "sync"


class VaultMismatch(Exception):
    """The account already has a DIFFERENT vault (made on another computer
    before syncing was on). The user must choose to combine them."""

    def __init__(self, cloud_data):
        super().__init__("Your account has a different HushKey vault from another computer.")
        self.cloud_data = cloud_data


class Syncer:
    def __init__(self, cloud: Cloud, email: str, key_folder: str):
        self.cloud = cloud
        self.email = email
        self.key_folder = key_folder
        self._session: Session | None = None
        self.last_synced = 0.0
        self.state = "off"   # off | syncing | ok | paused | offline | error

    # ---- the sign-in that sync uses ----------------------------------------

    @property
    def enabled(self) -> bool:
        return self.cloud.configured and device_lock.load(self.email, self.key_folder, KIND) is not None

    def remember_session(self, session: Session) -> None:
        """Call after a correct 8-digit code: keeps sync signed in."""
        self._session = session
        if session.refresh_token:
            device_lock.save(self.email, session.refresh_token.encode("utf-8"), self.key_folder, KIND)

    def forget(self) -> None:
        self._session = None
        device_lock.delete(self.email, self.key_folder, KIND)
        self.state = "off"

    def _live_session(self) -> Session:
        if self._session is not None and self._session.expires_at > time.time():
            return self._session
        saved = device_lock.load(self.email, self.key_folder, KIND)
        if saved is None:
            raise SessionExpired("Sync needs you to confirm your email again.")
        try:
            session = self.cloud.refresh(saved.decode("utf-8"))
        except SessionExpired:
            device_lock.delete(self.email, self.key_folder, KIND)
            raise
        self.remember_session(session)
        return session

    # ---- the three steps of a sync --------------------------------------------

    def fetch(self):
        """Background: download the account's encrypted vault (or None)."""
        return self.cloud.get_vault(self._live_session())

    def reconcile(self, vault, row):
        """Main thread: merge the downloaded copy into the vault on this
        computer. Returns what to upload, or None if the cloud is up to date."""
        if row is None:
            return {"vault_id": vault.vault_id, "data": vault.cloud_payload(), "rev": 1}
        if not vault.same_vault(row["data"]):
            raise VaultMismatch(row["data"])
        _changed_here, needs_upload = vault.apply_cloud(row["data"])
        if not needs_upload:
            return None
        return {"vault_id": vault.vault_id, "data": vault.cloud_payload(), "rev": row["rev"] + 1}

    def upload(self, plan) -> None:
        """Background: save the merged, encrypted vault to the account."""
        if plan is not None:
            self.cloud.put_vault(self._live_session(), plan["vault_id"], plan["data"], plan["rev"])
        self.last_synced = time.time()

    def sign_out_others(self) -> None:
        """Background: end sync sign-ins on all other computers."""
        self.cloud.sign_out_others(self._live_session())

    # ---- new computer --------------------------------------------------------

    def download_for_new_computer(self, session: Session):
        """After the 8-digit code on a computer with no vault yet."""
        self.remember_session(session)
        row = self.cloud.get_vault(session)
        if row is None:
            raise CloudError("There's no synced HushKey vault for this email yet. Sign in on the "
                             "computer where you made your vault first, so it can sync.")
        return row["data"]

    def status_text(self) -> str:
        if self.state == "syncing":
            return "Syncing…"
        if self.state == "ok":
            return "Synced ✓"
        if self.state == "offline":
            return "Offline: will sync later"
        if self.state == "paused":
            return "Sync paused"
        if self.state == "error":
            return "Sync problem"
        return ""
