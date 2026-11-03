"""
vault.py - the "engine" of HushKey (no window code in here).

THE BIG IDEA: one random "vault key", locked two different ways
----------------------------------------------------------------
Every login you save is encrypted with a random 32-byte VAULT KEY.
That vault key is never saved as-is. Instead, two locked copies are saved:

  1. Locked with your MASTER PASSWORD
     Your master password is HASHED (PBKDF2-SHA256, 600,000 rounds, random
     salt). Part of that hash checks your login; another part unlocks the
     vault key. The master password itself is never stored anywhere.

  2. Locked with a RECOVERY SECRET
     A random secret kept online (Supabase), which you can only download
     after proving you own your email with a 6-digit code.

So to open a vault you need EITHER the master password, OR (this computer's
vault file + your email inbox). The online service never sees the vault file,
and the vault file alone is useless without one of those two.

This is called "key wrapping". It's also why changing or resetting your
master password is instant: only the small locked copy of the vault key
changes, not every entry.

HASHING vs ENCRYPTION, quickly:
  - Hashing is one-way: good for checking a password, can't be reversed.
  - Encryption is two-way with a key: needed for logins you want to read again.
"""

import base64
import getpass
import hashlib
import hmac
import json
import os
import platform
import secrets
import shutil
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken

APP_NAME = "HushKey"
FILE_VERSION = 3
KDF_ITERATIONS = 600_000  # OWASP's recommended minimum for PBKDF2-SHA256
MIN_MASTER_LENGTH = 8


class VaultError(Exception):
    """Something is wrong with the vault or the request."""


class WrongPassword(VaultError):
    """The master password didn't match."""


class TamperError(VaultError):
    """The vault file was changed outside HushKey."""


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _hmac(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def _fernet(raw_key: bytes) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(raw_key))


def normalize_email(email: str) -> str:
    return email.strip().lower()


def looks_like_email(email: str) -> bool:
    e = normalize_email(email)
    if e.count("@") != 1 or " " in e:
        return False
    name, domain = e.split("@")
    return bool(name) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def check_new_master(master: str, confirm: str | None = None) -> None:
    """Raise VaultError with a friendly message if a new master password is unusable."""
    if len(master) < MIN_MASTER_LENGTH:
        raise VaultError(f"Use at least {MIN_MASTER_LENGTH} characters.")
    if confirm is not None and master != confirm:
        raise VaultError("The two passwords don't match.")


# --------------------------------------------------------------------------
# File handling
# --------------------------------------------------------------------------

def default_data_dir() -> str:
    """Where vault files live, following each OS's convention.

    macOS:   ~/Library/Application Support/HushKey
    Windows: %APPDATA%\\HushKey
    Linux:   ~/.local/share/HushKey
    """
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, APP_NAME)


def vault_path_for(email: str, folder: str | None = None) -> str:
    """Each email gets its own vault file. The file name is a hash of the
    email, so someone browsing the folder can't see whose vaults are there."""
    digest = hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()[:24]
    return os.path.join(folder or default_data_dir(), f"vault-{digest}.json")


def _atomic_write_json(path: str, data: dict) -> None:
    """Write JSON so a crash can never leave a half-written vault.

    Write to a temp file in the same folder, flush it to disk, then os.replace()
    swaps it in. os.replace is atomic on macOS and Windows: the old file is
    either fully there or fully replaced, never half-written.
    """
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=folder, prefix=".vault-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    try:
        os.chmod(path, 0o600)  # owner-only on macOS/Linux
    except OSError:
        pass


# --------------------------------------------------------------------------
# Key derivation (the hashing part)
# --------------------------------------------------------------------------

def derive_master_keys(master: str, salt: bytes, iterations: int = KDF_ITERATIONS):
    """Stretch the master password into (verifier, unlock_key).

    PBKDF2 hashes password+salt, then hashes the result again, 600,000 times.
    It's deliberately slow (~0.3s) so someone guessing millions of passwords is
    slowed down millions of times. We ask for 64 bytes and split them:
      first 32 -> hashed once more = the "verifier" saved in the file
      last 32  -> the key that unlocks the vault key (never saved)
    """
    stretched = hashlib.pbkdf2_hmac("sha256", master.encode("utf-8"), salt, iterations, dklen=64)
    verifier = hashlib.sha256(stretched[:32]).digest()
    return verifier, stretched[32:]


def derive_recovery_key(recovery_secret: bytes, salt: bytes) -> bytes:
    """Turn the online recovery secret into the key for the second locked copy.
    The secret is already 32 random bytes, so one HMAC is enough here."""
    return _hmac(recovery_secret, b"hushkey-recovery-v1" + salt)


def _subkeys(vault_key: bytes):
    """Split the vault key into two independent keys: one encrypts entries,
    the other seals the whole file against tampering."""
    return _hmac(vault_key, b"hushkey-entries"), _hmac(vault_key, b"hushkey-seal")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Parts of the vault file that belong to THIS computer only and are never synced.
LOCAL_ONLY = ("devices", "auto_signin", "seal")


def compute_seal(data: dict, seal_key: bytes) -> str:
    """HMAC fingerprint over the WHOLE vault file (everything except the seal).

    Each entry is tamper-proof by itself, but someone could still delete an
    entry, swap in an old copy, or weaken the settings. The seal covers it
    all: change one character anywhere and it no longer matches."""
    body = {k: v for k, v in data.items() if k != "seal"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _b64e(_hmac(seal_key, canonical))


def new_recovery_secret() -> bytes:
    return secrets.token_bytes(32)


def new_vault_id() -> str:
    return uuid.uuid4().hex


REMEMBER_DAYS = 30


def device_id() -> str:
    """A fingerprint of this computer + user account (hashed, so it reveals
    nothing). If the vault file is copied to another computer, the
    fingerprint won't match and HushKey asks for an email code again."""
    raw = f"{uuid.getnode()}|{platform.node()}|{getpass.getuser()}|{sys.platform}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def generate_password(length: int = 18, symbols: bool = True) -> str:
    """Random password from the OS's cryptographically secure randomness.
    Look-alike characters (O/0, l/1/I) are left out so it's easy to read."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    if symbols:
        alphabet += "!@#$%^&*-_=+?"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw)
                and (not symbols or any(not c.isalnum() for c in pw))):
            return pw


def password_strength(pw: str) -> tuple[int, str]:
    """Rough 0-4 score and label for the strength bar."""
    if not pw:
        return 0, "No password yet"
    kinds = sum([any(c.islower() for c in pw), any(c.isupper() for c in pw),
                 any(c.isdigit() for c in pw), any(not c.isalnum() for c in pw)])
    score = 0
    if len(pw) >= 8:
        score += 1
    if len(pw) >= 12:
        score += 1
    if len(pw) >= 16:
        score += 1
    if kinds >= 3:
        score += 1
    if len(pw) < 8:
        score = min(score, 1)
    return score, ["Very weak", "Weak", "Okay", "Strong", "Very strong"][score]


# --------------------------------------------------------------------------
# The vault
# --------------------------------------------------------------------------

class Vault:
    """One person's vault on this computer, found by their email."""

    def __init__(self, email: str, folder: str | None = None):
        self.email = normalize_email(email)
        self.path = vault_path_for(self.email, folder)
        self._data: dict | None = None
        self._entries_fernet: Fernet | None = None
        self._seal_key: bytes | None = None
        self._vault_key: bytes | None = None
        self.on_change = None   # called after every save (the app uses it to sync)

    # ---- state ------------------------------------------------------------

    @property
    def backup_path(self) -> str:
        return self.path + ".bak"

    def exists(self) -> bool:
        return os.path.isfile(self.path)

    @property
    def is_unlocked(self) -> bool:
        return self._vault_key is not None

    def _require_unlocked(self):
        if not self.is_unlocked:
            raise VaultError("Vault is locked.")

    def _read_file(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise VaultError("There's no HushKey vault for this email on this computer.")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise VaultError("The vault file is damaged or isn't a HushKey file.")
        if not isinstance(data, dict) or data.get("version") != FILE_VERSION:
            raise VaultError("This vault file is from a different HushKey version.")
        return data

    @property
    def vault_id(self) -> str:
        """Random id for this vault, used to find its recovery secret online."""
        data = self._data if self._data is not None else self._read_file()
        return data["vault_id"]

    @property
    def has_recovery(self) -> bool:
        data = self._data if self._data is not None else self._read_file()
        return bool(data.get("recovery"))

    def _open_with_key(self, data: dict, vault_key: bytes) -> None:
        entries_key, seal_key = _subkeys(vault_key)
        if not hmac.compare_digest(compute_seal(data, seal_key), str(data.get("seal", ""))):
            raise TamperError(
                "Security warning: this vault file was changed outside HushKey and "
                "failed its tamper check. The previous copy is at:\n" + self.backup_path)
        self._data = data
        self._vault_key = vault_key
        self._entries_fernet = _fernet(entries_key)
        self._seal_key = seal_key

    # ---- create / unlock / lock ------------------------------------------

    def create(self, master: str, recovery_secret: bytes | None = None,
               vault_id: str | None = None) -> None:
        """Make a new vault. Pass recovery_secret (already saved online under
        vault_id) to enable email recovery; leave both out for no recovery."""
        if self.exists():
            raise VaultError("There's already a vault for this email on this computer.")
        check_new_master(master)
        vault_key = secrets.token_bytes(32)
        salt = secrets.token_bytes(16)
        verifier, unlock_key = derive_master_keys(master, salt)
        data = {
            "app": APP_NAME,
            "version": FILE_VERSION,
            "vault_id": vault_id or new_vault_id(),
            "kdf": {"name": "pbkdf2-sha256", "iterations": KDF_ITERATIONS, "salt": _b64e(salt)},
            "verifier": _b64e(verifier),
            "key_by_master": _fernet(unlock_key).encrypt(vault_key).decode("ascii"),
            "master_changed": _now(),
            "recovery": None,
            "entries": [],
            "deleted": {},
        }
        if recovery_secret is not None:
            rsalt = secrets.token_bytes(16)
            rkey = derive_recovery_key(recovery_secret, rsalt)
            data["recovery"] = {
                "salt": _b64e(rsalt),
                "key_by_recovery": _fernet(rkey).encrypt(vault_key).decode("ascii"),
                "changed": _now(),
            }
        entries_key, seal_key = _subkeys(vault_key)
        self._data, self._vault_key = data, vault_key
        self._entries_fernet, self._seal_key = _fernet(entries_key), seal_key
        self._save()

    def unlock(self, master: str) -> None:
        self._unlock_data(self._read_file(), master)

    def _unlock_data(self, data: dict, master: str) -> None:
        try:
            kdf = data["kdf"]
            salt, iterations = _b64d(kdf["salt"]), int(kdf["iterations"])
            stored = _b64d(data["verifier"])
        except (KeyError, ValueError, TypeError):
            raise VaultError("The vault file is missing required fields.")
        verifier, unlock_key = derive_master_keys(master, salt, iterations)
        # compare_digest takes the same time whether 1 or 31 bytes match,
        # so timing can't leak how close a guess was.
        if not hmac.compare_digest(verifier, stored):
            raise WrongPassword("Wrong email or master password.")
        try:
            vault_key = _fernet(unlock_key).decrypt(data["key_by_master"].encode("ascii"))
        except (InvalidToken, KeyError, AttributeError):
            raise TamperError("Security warning: the vault key in this file was changed.")
        self._open_with_key(data, vault_key)

    def lock(self) -> None:
        """Forget every key. (Python can't truly wipe memory, but dropping the
        references lets them be cleaned up.)"""
        self._data = None
        self._vault_key = None
        self._entries_fernet = None
        self._seal_key = None

    def change_master(self, current: str, new: str, confirm: str | None = None) -> None:
        self._require_unlocked()
        check_new_master(new, confirm)
        kdf = self._data["kdf"]
        verifier, _ = derive_master_keys(current, _b64d(kdf["salt"]), int(kdf["iterations"]))
        if not hmac.compare_digest(verifier, _b64d(self._data["verifier"])):
            raise WrongPassword("Your current master password is wrong.")
        self._set_master(new)
        self._save()

    def _set_master(self, master: str) -> None:
        salt = secrets.token_bytes(16)
        verifier, unlock_key = derive_master_keys(master, salt)
        self._data["kdf"] = {"name": "pbkdf2-sha256", "iterations": KDF_ITERATIONS, "salt": _b64e(salt)}
        self._data["verifier"] = _b64e(verifier)
        self._data["key_by_master"] = _fernet(unlock_key).encrypt(self._vault_key).decode("ascii")
        self._data["master_changed"] = _now()

    # ---- recovery ---------------------------------------------------------

    def enable_recovery(self, recovery_secret: bytes) -> None:
        """Turn on email recovery for a vault made without it (e.g. before
        email was set up). The secret must already be saved online under
        this vault's id."""
        self._require_unlocked()
        rsalt = secrets.token_bytes(16)
        rkey = derive_recovery_key(recovery_secret, rsalt)
        self._data["recovery"] = {
            "salt": _b64e(rsalt),
            "key_by_recovery": _fernet(rkey).encrypt(self._vault_key).decode("ascii"),
            "changed": _now(),
        }
        self._save()

    def start_recovery(self, recovery_secret: bytes) -> "RecoveryReset":
        """Use the secret downloaded after the email code to unlock the vault key
        IN MEMORY ONLY. Nothing on disk changes until RecoveryReset.complete()."""
        data = self._read_file()
        rec = data.get("recovery")
        if not rec:
            raise VaultError("Email recovery isn't turned on for this vault.")
        rkey = derive_recovery_key(recovery_secret, _b64d(rec["salt"]))
        try:
            vault_key = _fernet(rkey).decrypt(rec["key_by_recovery"].encode("ascii"))
        except InvalidToken:
            raise VaultError("The recovery key doesn't match this vault.")
        probe = Vault(self.email, os.path.dirname(self.path))
        probe._open_with_key(data, vault_key)  # also runs the tamper check
        return RecoveryReset(self, probe)

    # ---- entries ----------------------------------------------------------

    def _enc(self, text: str) -> str:
        return self._entries_fernet.encrypt(text.encode("utf-8")).decode("ascii")

    def _dec(self, token: str) -> str:
        try:
            return self._entries_fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken:
            raise TamperError("An entry failed its tamper check.")

    def _encrypt_entry(self, title, username, password, icon="", entry_id=None, created=None,
                       url="", meta=None, pw_changed=None) -> dict:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = {
            "id": entry_id or uuid.uuid4().hex,
            "title": self._enc(title),
            "username": self._enc(username),
            "password": self._enc(password),
            "icon": self._enc(icon or ""),  # even the chosen logo is encrypted
            "created": created or now,
            "updated": now,
            "pw_changed": pw_changed or now,
        }
        if url:
            entry["url"] = self._enc(url)   # website address, kept from imports
        if meta:
            entry["meta"] = self._enc(json.dumps(meta, sort_keys=True))  # favorite, folder, tips
        return entry

    def _meta(self, e) -> dict:
        """Favorite, folder and suggestion choices for one login (encrypted too)."""
        if not e.get("meta"):
            return {}
        try:
            m = json.loads(self._dec(e["meta"]))
            return m if isinstance(m, dict) else {}
        except ValueError:
            return {}

    def _url(self, e) -> str:
        return self._dec(e["url"]) if e.get("url") else ""

    def _icon(self, e) -> str:
        return self._dec(e["icon"]) if e.get("icon") else ""

    # ---- remember this device -------------------------------------------

    def is_device_remembered(self) -> bool:
        self._require_unlocked()
        until = self._data.get("devices", {}).get(device_id(), 0)
        return isinstance(until, (int, float)) and until > time.time()

    def remember_device(self, days: int = REMEMBER_DAYS) -> None:
        self._require_unlocked()
        devices = {k: v for k, v in self._data.get("devices", {}).items() if v > time.time()}
        devices[device_id()] = int(time.time() + days * 86400)
        self._data["devices"] = devices
        self._save()

    def forget_device(self) -> None:
        self._require_unlocked()
        changed = self._data.get("devices", {}).pop(device_id(), None) is not None
        changed = self._data.pop("auto_signin", None) is not None or changed
        if changed:
            self._save()

    # ---- stay signed in ("Remember this device for 30 days") ----------------

    def enable_auto_signin(self, days: int = REMEMBER_DAYS) -> bytes:
        """Lock one more copy of the vault key with a random device key and
        return that key, to be kept in Windows' protected storage or the Mac
        Keychain (device_lock.py). Tied to this computer, expires after
        `days`, and the expiry is inside the tamper-proof seal."""
        self._require_unlocked()
        device_key = secrets.token_bytes(32)
        self._data["auto_signin"] = {
            "device": device_id(),
            "until": int(time.time() + days * 86400),
            "key_by_device": _fernet(_hmac(device_key, b"hushkey-auto-signin")).encrypt(
                self._vault_key).decode("ascii"),
        }
        self._save()
        return device_key

    def disable_auto_signin(self) -> None:
        self._require_unlocked()
        if self._data.pop("auto_signin", None) is not None:
            self._save()

    @property
    def auto_signin_until(self) -> int:
        """When stay-signed-in ends (0 = off)."""
        data = self._data if self._data is not None else self._read_file()
        info = data.get("auto_signin") or {}
        return int(info.get("until", 0)) if info.get("device") == device_id() else 0

    def unlock_with_device_key(self, device_key: bytes) -> None:
        """Open the vault without the master password, only on the same
        computer, within the 30 days, and only if the file wasn't tampered with."""
        data = self._read_file()
        info = data.get("auto_signin")
        if not info or info.get("device") != device_id():
            raise VaultError("This computer isn't remembered. Please sign in.")
        if int(info.get("until", 0)) <= time.time():
            raise VaultError("It's been 30 days, so for your safety please sign in again.")
        try:
            vault_key = _fernet(_hmac(device_key, b"hushkey-auto-signin")).decrypt(
                info["key_by_device"].encode("ascii"))
        except (InvalidToken, KeyError, AttributeError):
            raise VaultError("This computer isn't remembered anymore. Please sign in.")
        self._open_with_key(data, vault_key)

    def _find(self, entry_id: str) -> dict:
        for e in self._data["entries"]:
            if e["id"] == entry_id:
                return e
        raise VaultError("Entry not found.")

    def _save(self) -> None:
        """Seal the data, keep one backup of the previous version, then save."""
        self._data["seal"] = compute_seal(self._data, self._seal_key)
        if os.path.isfile(self.path):
            try:
                shutil.copy2(self.path, self.backup_path)
            except OSError:
                pass
        _atomic_write_json(self.path, self._data)
        if self.on_change is not None:
            try:
                self.on_change()
            except Exception:
                pass

    def list_titles(self) -> list[tuple[str, str]]:
        """(id, client name) for every entry, A-Z. Usernames/passwords stay encrypted."""
        return [(e["id"], e["title"]) for e in self.list_entries()]

    def list_entries(self) -> list[dict]:
        """{id, title, icon} for every entry, A-Z. Usernames/passwords stay encrypted."""
        self._require_unlocked()
        rows = []
        for e in self._data["entries"]:
            m = self._meta(e)
            rows.append({"id": e["id"], "title": self._dec(e["title"]), "icon": self._icon(e),
                         "fav": bool(m.get("fav")), "folder": m.get("folder") or "",
                         "changed": e.get("pw_changed") or e.get("created") or ""})
        return sorted(rows, key=lambda r: r["title"].lower())

    def reveal(self, entry_id: str) -> tuple[str, str]:
        """Decrypt one entry's (username, password), only when it's clicked."""
        self._require_unlocked()
        e = self._find(entry_id)
        return self._dec(e["username"]), self._dec(e["password"])

    def get(self, entry_id: str) -> dict:
        self._require_unlocked()
        e = self._find(entry_id)
        m = self._meta(e)
        return {"id": e["id"], "title": self._dec(e["title"]), "icon": self._icon(e),
                "username": self._dec(e["username"]), "password": self._dec(e["password"]),
                "url": self._url(e), "fav": bool(m.get("fav")), "folder": m.get("folder") or "",
                "changed": e.get("pw_changed") or e.get("created") or ""}

    def add(self, title: str, username: str, password: str, icon: str = "") -> str:
        self._require_unlocked()
        if not title.strip():
            raise VaultError("Client name can't be empty.")
        if not password:
            raise VaultError("Password can't be empty.")
        entry = self._encrypt_entry(title.strip(), username.strip(), password, icon)
        self._data["entries"].append(entry)
        self._save()
        return entry["id"]

    def update(self, entry_id: str, title: str, username: str, password: str, icon: str = "") -> None:
        self._require_unlocked()
        if not title.strip():
            raise VaultError("Client name can't be empty.")
        if not password:
            raise VaultError("Password can't be empty.")
        old = self._find(entry_id)
        same_pw = self._dec(old["password"]) == password
        meta = self._meta(old)
        if not same_pw:   # a new password: earlier "Not now" choices start fresh
            meta.pop("snooze", None)
            meta.pop("mute", None)
            meta.pop("leaked", None)   # the old password's leak result doesn't apply to the new one
        new = self._encrypt_entry(title.strip(), username.strip(), password, icon, entry_id,
                                  old.get("created"), url=self._url(old), meta=meta,
                                  pw_changed=old.get("pw_changed") if same_pw else None)
        self._data["entries"][self._data["entries"].index(old)] = new
        self._save()

    def delete(self, entry_id: str) -> None:
        self._require_unlocked()
        self._data["entries"].remove(self._find(entry_id))
        # remember the deletion so syncing doesn't bring it back from another computer
        self._data.setdefault("deleted", {})[entry_id] = _now()
        self._save()

    @property
    def entry_count(self) -> int:
        self._require_unlocked()
        return len(self._data["entries"])

    # ---- favorites, folders, suggestions ---------------------------------

    def set_meta(self, entry_id: str, **changes) -> None:
        """Change a login's favorite / folder / suggestion choices.
        Pass None to clear a value. Syncs like any other edit."""
        self._require_unlocked()
        e = self._find(entry_id)
        m = self._meta(e)
        for k, v in changes.items():
            if v is None or v is False or v == "":
                m.pop(k, None)
            else:
                m[k] = v
        if m:
            e["meta"] = self._enc(json.dumps(m, sort_keys=True))
        else:
            e.pop("meta", None)
        e["updated"] = _now()
        self._save()

    def tip_state(self, entry_id: str) -> dict:
        self._require_unlocked()
        m = self._meta(self._find(entry_id))
        return {"snooze": float(m.get("snooze") or 0), "mute": bool(m.get("mute"))}

    # ---- your computers (Settings > Sync & devices) -------------------------------
    # Each computer that opens this vault adds a small encrypted note: its name, system
    # and when it was last used. Notes sync, so every computer sees the list. Removing
    # one marks it removed; that computer signs itself out the next time it syncs.

    TOUCH_EVERY = 3600   # update "last used" at most once an hour, so it doesn't cause extra syncs

    @staticmethod
    def computer_key() -> str:
        return hashlib.sha256(("hushkey-computer|" + device_id()).encode("utf-8")).hexdigest()[:16]

    def computers(self) -> list:
        """[{key, name, system, first, last, removed, this}], this computer first."""
        self._require_unlocked()
        out = []
        for key, rec in (self._data.get("computers") or {}).items():
            try:
                info = json.loads(self._dec(rec["data"]))
            except (ValueError, KeyError, TypeError):
                continue
            info["key"] = key
            info["this"] = key == self.computer_key()
            info["removed"] = bool(rec.get("removed")) and rec["removed"] > (rec.get("signin") or "")
            out.append(info)
        out.sort(key=lambda c: (not c["this"], -(c.get("last") or 0)))
        return out

    def touch_computer(self, signed_in: bool = False) -> bool:
        """Note that this computer is using the vault. signed_in=True after a full sign-in
        (master password, plus the email code on a new computer) also brings back a
        computer that was removed."""
        self._require_unlocked()
        key = self.computer_key()
        rec = (self._data.get("computers") or {}).get(key)
        cur = next((c for c in self.computers() if c["key"] == key), None)
        now = time.time()
        if cur and cur["removed"] and not signed_in:
            return False
        if cur and not signed_in and now - (cur.get("last") or 0) < self.TOUCH_EVERY:
            return False
        system = {"win32": "Windows", "darwin": "Mac"}.get(sys.platform, platform.system() or "Computer")
        name = (platform.node() or "This computer").split(".")[0][:40]
        info = {"name": name, "system": system, "first": (cur or {}).get("first") or now, "last": now}
        self._data.setdefault("computers", {})[key] = {
            "data": self._enc(json.dumps(info, sort_keys=True)), "updated": _now(),
            "signin": _now() if (signed_in or rec is None) else rec.get("signin", ""),
            "removed": (rec or {}).get("removed")}
        self._save()
        return True

    def remove_computer(self, key: str) -> None:
        self._require_unlocked()
        if key == self.computer_key():
            raise VaultError("To remove this computer, use Sign out instead.")
        rec = (self._data.get("computers") or {}).get(key)
        if rec is None:
            raise VaultError("That computer isn't in your list anymore.")
        rec = dict(rec, removed=_now(), updated=_now())
        self._data["computers"][key] = rec
        self._save()

    def this_computer_removed(self) -> bool:
        if not self.is_unlocked:
            return False
        cur = next((c for c in self.computers() if c["this"]), None)
        return bool(cur and cur["removed"])

    def delete_local_copy(self) -> None:
        """Remove this computer's copy of the vault (after it was removed from the account)."""
        for path in (self.path, self.backup_path):
            try:
                os.remove(path)
            except OSError:
                pass
        self.lock()

    def folders(self) -> list:
        """[{id, name, color}] in the order they were made. Names are encrypted."""
        self._require_unlocked()
        raw = self._data.get("folders")
        if not raw:
            return []
        try:
            items = json.loads(self._dec(raw))
            return [f for f in items if isinstance(f, dict) and f.get("id")]
        except ValueError:
            return []

    def _save_folders(self, items: list) -> None:
        self._data["folders"] = self._enc(json.dumps(items))
        self._data["folders_changed"] = _now()
        self._save()

    def add_folder(self, name: str, color: str) -> str:
        self._require_unlocked()
        name = name.strip()[:40]
        if not name:
            raise VaultError("Give the folder a name.")
        items = self.folders()
        if any(f["name"].lower() == name.lower() for f in items):
            raise VaultError("You already have a folder with that name.")
        fid = uuid.uuid4().hex[:12]
        items.append({"id": fid, "name": name, "color": color})
        self._save_folders(items)
        return fid

    def rename_folder(self, folder_id: str, name: str) -> None:
        self._require_unlocked()
        name = name.strip()[:40]
        if not name:
            raise VaultError("Give the folder a name.")
        items = self.folders()
        for f in items:
            if f["id"] == folder_id:
                f["name"] = name
        self._save_folders(items)

    def delete_folder(self, folder_id: str) -> None:
        """Remove a folder. Its logins stay in your vault, just not in a folder."""
        self._require_unlocked()
        items = [f for f in self.folders() if f["id"] != folder_id]
        for e in self._data["entries"]:
            m = self._meta(e)
            if m.get("folder") == folder_id:
                m.pop("folder")
                if m:
                    e["meta"] = self._enc(json.dumps(m, sort_keys=True))
                else:
                    e.pop("meta", None)
                e["updated"] = _now()
        self._save_folders(items)

    def password_hashes(self) -> dict:
        """{login id: SHA-1 of its password}, in memory only, for the leak check."""
        self._require_unlocked()
        return {e["id"]: hashlib.sha1(self._dec(e["password"]).encode("utf-8")).hexdigest().upper()
                for e in self._data["entries"]}

    def set_leaked(self, leaked_ids) -> bool:
        """Save the leak check's result with each login (encrypted), so the
        Vault health score is right the moment HushKey opens instead of
        jumping when the check finishes. Saves only if something changed."""
        self._require_unlocked()
        leaked_ids, changed = set(leaked_ids), False
        for e in self._data["entries"]:
            m = self._meta(e)
            stamp = e.get("pw_changed") or e.get("created")
            want = stamp if e["id"] in leaked_ids else None
            if m.get("leaked") != want:
                if want is None:
                    m.pop("leaked", None)
                else:
                    m["leaked"] = want
                if m:
                    e["meta"] = self._enc(json.dumps(m, sort_keys=True))
                else:
                    e.pop("meta", None)
                e["updated"] = _now()
                changed = True
        if changed:
            self._save()
        return changed

    def username(self, entry_id: str) -> str:
        """Decrypt just the username (for "Show usernames")."""
        self._require_unlocked()
        return self._dec(self._find(entry_id)["username"])

    def security_report(self, leaked_hashes=()) -> list:
        """One row per login that could be safer: leaked, reused or weak.
        Worst first. Passwords are only compared in memory.
        leaked_hashes: SHA-1s the leak check found (so a changed password
        stops counting as leaked right away)."""
        self._require_unlocked()
        leaked_hashes = set(leaked_hashes)
        rows, by_pw = {}, {}
        for e in self._data["entries"]:
            pw = self._dec(e["password"])
            by_pw.setdefault(pw, []).append(e["id"])
            m = self._meta(e)
            rows[e["id"]] = {"id": e["id"], "title": self._dec(e["title"]), "icon": self._icon(e),
                             "score": password_strength(pw)[0], "reused_with": [],
                             # a saved leak result counts until that password is changed
                             "leaked": (m.get("leaked") is not None
                                        and m.get("leaked") == (e.get("pw_changed") or e.get("created")))
                                       or (bool(leaked_hashes) and hashlib.sha1(
                                           pw.encode("utf-8")).hexdigest().upper() in leaked_hashes),
                             "snooze": float(m.get("snooze") or 0), "mute": bool(m.get("mute"))}
        for ids in by_pw.values():
            if len(ids) > 1:
                for i in ids:
                    rows[i]["reused_with"] = [rows[j]["title"] for j in ids if j != i]
        out = []
        for r in rows.values():
            if r["leaked"]:
                r["kind"], r["level"] = "leaked", 3
            elif r["reused_with"]:
                r["kind"], r["level"] = "reused", 2
            elif r["score"] <= 2:
                r["kind"], r["level"] = "weak", 1 if r["score"] == 2 else 2
            else:
                continue
            out.append(r)
        out.sort(key=lambda r: (-r["level"], r["title"].lower()))
        return out

    # ---- import / export ----------------------------------------------------

    def add_many(self, items) -> int:
        """Add many logins at once (an import) with a single save.
        items: dicts with title, username, password and optional icon, url."""
        self._require_unlocked()
        added = 0
        for it in items:
            title, password = (it.get("title") or "").strip(), it.get("password") or ""
            if not title or not password:
                continue
            self._data["entries"].append(self._encrypt_entry(
                title[:120], (it.get("username") or "").strip(), password,
                it.get("icon") or "", url=(it.get("url") or "")[:500]))
            added += 1
        if added:
            self._save()
        return added

    def existing_keys(self) -> list:
        """(client name, username) of every login, to spot duplicates on import."""
        self._require_unlocked()
        return [(self._dec(e["title"]), self._dec(e["username"])) for e in self._data["entries"]]

    def all_entries(self) -> list:
        """Every login fully decrypted - only used to export."""
        self._require_unlocked()
        return [self.get(e["id"]) for e in self._data["entries"]]

    def check_master(self, master: str) -> bool:
        """Is this the master password? (Asked again before risky actions.)"""
        self._require_unlocked()
        kdf = self._data["kdf"]
        verifier, _ = derive_master_keys(master, _b64d(kdf["salt"]), int(kdf["iterations"]))
        return hmac.compare_digest(verifier, _b64d(self._data["verifier"]))

    def export_backup(self, dest: str) -> None:
        """Save an encrypted copy of the vault (.hushkey). It's the same sealed,
        encrypted file HushKey keeps, so it's only readable with the master
        password that was in use when the backup was made."""
        self._require_unlocked()
        _atomic_write_json(dest, self._data)

    @classmethod
    def open_backup(cls, path: str, master: str) -> "Vault":
        """Unlock a .hushkey backup file to import its logins."""
        v = cls("backup@hushkey.local", os.path.dirname(os.path.abspath(path)))
        v.path = path
        try:
            v.unlock(master)
        except WrongPassword:
            raise WrongPassword("That's not the master password for this backup. Use the master "
                                "password you had when the backup was made.")
        except TamperError:
            raise
        except VaultError:
            raise VaultError("That file isn't a HushKey backup, or it's damaged.")
        return v


# --------------------------------------------------------------------------
# Sync helpers (zero-knowledge: everything uploaded is already encrypted)
# --------------------------------------------------------------------------

def merge_vaults(local: dict, cloud: dict) -> dict:
    """Combine two copies of the SAME vault, without decrypting anything.

    - Logins are matched by id; the most recently edited copy wins.
    - A deletion on either computer wins over an older edit.
    - The master password block (and recovery block) comes from whichever
      copy changed it last.
    Local-only parts (remembered devices, seal) are left out."""
    merged = {k: v for k, v in local.items() if k not in LOCAL_ONLY}
    if (cloud.get("master_changed") or "") > (local.get("master_changed") or ""):
        for k in ("kdf", "verifier", "key_by_master", "master_changed"):
            if k in cloud:
                merged[k] = cloud[k]
    lr, cr = local.get("recovery") or {}, cloud.get("recovery") or {}
    if cr and (not lr or (cr.get("changed") or "") > (lr.get("changed") or "")):
        merged["recovery"] = cr
    if (cloud.get("folders_changed") or "") > (local.get("folders_changed") or ""):
        for k in ("folders", "folders_changed"):
            if k in cloud:
                merged[k] = cloud[k]
    computers = dict(local.get("computers") or {})
    for key, rec in (cloud.get("computers") or {}).items():
        old = computers.get(key)
        if old is None:
            computers[key] = rec
            continue
        win = dict(rec if (rec.get("updated") or "") > (old.get("updated") or "") else old)
        # a removal or a full sign-in is never lost, even if the other copy was edited later
        win["removed"] = max(rec.get("removed") or "", old.get("removed") or "") or None
        win["signin"] = max(rec.get("signin") or "", old.get("signin") or "")
        computers[key] = win
    if computers:
        merged["computers"] = computers
    deleted = dict(local.get("deleted") or {})
    for eid, when in (cloud.get("deleted") or {}).items():
        if when > deleted.get(eid, ""):
            deleted[eid] = when
    by_id, order = {}, []
    for e in list(local.get("entries") or []) + list(cloud.get("entries") or []):
        old = by_id.get(e["id"])
        if old is None:
            order.append(e["id"])
            by_id[e["id"]] = e
        elif (e.get("updated") or "") > (old.get("updated") or ""):
            by_id[e["id"]] = e
    merged["entries"] = [by_id[i] for i in order
                         if deleted.get(i, "") < (by_id[i].get("updated") or "")]
    merged["deleted"] = deleted
    return merged


def _comparable(data: dict) -> str:
    return json.dumps({k: v for k, v in data.items() if k not in LOCAL_ONLY}, sort_keys=True)


def _vault_sync_methods():
    """Added to Vault below (kept here so the sync code reads in one place)."""

    def cloud_payload(self) -> str:
        """The vault as uploaded: encrypted logins, without this computer's
        private bits, sealed so the server can't change anything unnoticed."""
        self._require_unlocked()
        body = {k: v for k, v in self._data.items() if k not in LOCAL_ONLY}
        body["seal"] = compute_seal(body, self._seal_key)
        return json.dumps(body, sort_keys=True, separators=(",", ":"))

    def same_vault(self, cloud_data: dict) -> bool:
        self._require_unlocked()
        return cloud_data.get("vault_id") == self._data.get("vault_id")

    def apply_cloud(self, cloud_data: dict):
        """Merge a downloaded copy into this one. Returns (changed_here,
        needs_upload). Refuses copies that fail the tamper check."""
        self._require_unlocked()
        if not self.same_vault(cloud_data):
            raise VaultError("The synced vault belongs to a different HushKey vault.")
        expected = compute_seal({k: v for k, v in cloud_data.items() if k != "seal"}, self._seal_key)
        if not hmac.compare_digest(expected, str(cloud_data.get("seal", ""))):
            raise TamperError("Security warning: the synced copy failed its tamper check, "
                              "so HushKey ignored it.")
        merged = merge_vaults(self._data, cloud_data)
        changed_here = _comparable(merged) != _comparable(self._data)
        needs_upload = _comparable(merged) != _comparable(cloud_data)
        if changed_here:
            for k in LOCAL_ONLY:
                if k in self._data and k != "seal":
                    merged[k] = self._data[k]
            self._data = merged
            callback, self.on_change = self.on_change, None   # don't trigger another sync
            try:
                self._save()
            finally:
                self.on_change = callback
        return changed_here, needs_upload

    @classmethod
    def save_cloud_copy(cls, email: str, folder, cloud_data: dict) -> "Vault":
        """New computer: store the downloaded (still encrypted) vault here.
        It opens with the master password like any vault."""
        v = cls(email, folder)
        if v.exists():
            raise VaultError("There's already a vault for this email on this computer.")
        if cloud_data.get("app") != APP_NAME or cloud_data.get("version") != FILE_VERSION:
            raise VaultError("The synced vault is from a different HushKey version.")
        _atomic_write_json(v.path, cloud_data)
        return v

    @classmethod
    def open_cloud_copy(cls, cloud_data: dict, master: str) -> "Vault":
        """Unlock a downloaded vault in memory only (to combine two vaults)."""
        v = cls("cloud-copy@hushkey.local", tempfile.gettempdir())
        v.path = None
        v._unlock_data(dict(cloud_data), master)
        return v

    def adopt(self, other: "Vault") -> int:
        """Combine two DIFFERENT vaults (e.g. made separately on two computers):
        copy this vault's logins into `other`, then become `other` here.
        Returns how many logins were copied over."""
        self._require_unlocked()
        existing = {(t.lower(), u.lower()) for t, u in other.existing_keys()}
        items = [e for e in self.all_entries()
                 if (e["title"].lower(), e["username"].lower()) not in existing]
        data = {k: v for k, v in other._data.items() if k not in LOCAL_ONLY}
        entries_key, seal_key = _subkeys(other._vault_key)
        self._data, self._vault_key = data, other._vault_key
        self._entries_fernet, self._seal_key = _fernet(entries_key), seal_key
        for it in items:
            self._data["entries"].append(self._encrypt_entry(
                it["title"], it["username"], it["password"], it.get("icon") or "", url=it.get("url") or ""))
        self._save()
        return len(items)

    return cloud_payload, same_vault, apply_cloud, save_cloud_copy, open_cloud_copy, adopt


(Vault.cloud_payload, Vault.same_vault, Vault.apply_cloud, Vault.save_cloud_copy,
 Vault.open_cloud_copy, Vault.adopt) = _vault_sync_methods()


class RecoveryReset:
    """A password reset in progress. The vault is unlocked in memory only.

    - complete(new, confirm): sets the new master password and saves.
    - cancel(): forgets everything; the old master password keeps working.
    """

    def __init__(self, vault: Vault, unlocked: Vault):
        self._vault = vault
        self._unlocked: Vault | None = unlocked

    def complete(self, new_master: str, confirm: str) -> None:
        if self._unlocked is None:
            raise VaultError("This reset was cancelled. Start again.")
        check_new_master(new_master, confirm)
        self._unlocked._set_master(new_master)
        self._unlocked._data.pop("auto_signin", None)  # after a reset, every device signs in again
        self._unlocked._save()
        self.cancel()

    def cancel(self) -> None:
        if self._unlocked is not None:
            self._unlocked.lock()
        self._unlocked = None


def health_score(entry_count: int, report: list) -> int:
    """0-100 for the Vault health circle. Each login that could be safer
    takes points off; logins you chose "Don't remind me" for don't count."""
    if entry_count <= 0:
        return 100
    weight = {"leaked": 1.0, "reused": 0.6, "weak": 0.5}
    lost = 0.0
    for r in report:
        if r.get("mute"):
            continue
        w = weight[r["kind"]]
        if r["kind"] == "weak" and r["score"] == 2:
            w = 0.25
        lost += w
    return max(0, min(100, round(100 * (1 - lost / max(entry_count, 1)))))
