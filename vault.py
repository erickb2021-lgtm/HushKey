"""
vault.py - the "engine" of HushKey (no GUI code in here).

Two security ideas live in this file:

1. HASHING (one-way)
   The master password is NEVER saved. Instead we run it through PBKDF2-SHA256
   600,000 times with a random "salt". The result can't be turned back into
   the password - we can only re-run the same math on whatever you type at
   login and check whether the results match.

2. ENCRYPTION (two-way, needs a key)
   Your saved logins have to come back out when you click them, so they can't
   just be hashed (a hash can't be reversed - that's the whole point). Instead
   they're locked with Fernet (AES-128 + an HMAC tamper check). The key for
   that lock is ALSO produced by hashing your master password, and it only
   ever exists in memory while the vault is unlocked.

   So: no master password -> no key -> the file on disk is just scrambled text.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import string
import sys
import tempfile
import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken

APP_NAME = "HushKey"
FILE_VERSION = 2
KDF_ITERATIONS = 600_000  # OWASP's recommended minimum for PBKDF2-SHA256
MIN_MASTER_LENGTH = 8


class VaultError(Exception):
    """Something is wrong with the vault file."""


class WrongPassword(VaultError):
    """The master password didn't match."""


# --------------------------------------------------------------------------
# File handling helpers
# --------------------------------------------------------------------------

def default_data_dir() -> str:
    """Where the vault file lives, following each OS's convention.

    macOS:   ~/Library/Application Support/HushKey
    Windows: %APPDATA%\\HushKey   (e.g. C:\\Users\\you\\AppData\\Roaming\\HushKey)
    Linux:   ~/.local/share/HushKey
    """
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, APP_NAME)


def default_vault_path() -> str:
    return os.path.join(default_data_dir(), "vault.json")


def _atomic_write_json(path: str, data: dict) -> None:
    """Write JSON so a crash can never leave a half-written vault.

    We write to a temp file in the same folder, flush it to disk, then
    os.replace() swaps it in. os.replace is atomic on both macOS and Windows:
    the old file is either fully there or fully replaced - never corrupted.
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
    # Owner-only permissions (works on macOS/Linux; Windows mostly ignores it
    # but files in %APPDATA% are already private to your user account).
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------

def derive_keys(master: str, salt: bytes, iterations: int = KDF_ITERATIONS):
    """Stretch the master password into two separate 32-byte secrets.

    PBKDF2 = hash the password + salt, then hash that result, again and again
    (600k times). It's deliberately slow (~0.3s) so an attacker guessing
    millions of passwords is slowed down millions of times over.

    We ask for 96 bytes and split them three ways:
      - bytes  0-31 -> "login check" (hashed once more and saved in the file)
      - bytes 32-63 -> encryption key for your entries (never saved)
      - bytes 64-95 -> "seal" key that detects tampering with the file (never saved)
    Splitting means the saved check value tells an attacker nothing about
    the other two keys.
    """
    stretched = hashlib.pbkdf2_hmac(
        "sha256", master.encode("utf-8"), salt, iterations, dklen=96
    )
    auth_part, enc_part, seal_key = stretched[:32], stretched[32:64], stretched[64:]
    verifier = hashlib.sha256(auth_part).digest()
    fernet_key = base64.urlsafe_b64encode(enc_part)
    return verifier, fernet_key, seal_key


def compute_seal(data: dict, seal_key: bytes) -> str:
    """HMAC-SHA256 "fingerprint" over the WHOLE vault file.

    Each entry is already tamper-proof on its own, but an attacker could still
    delete entries, swap in an old copy of one, or change the settings at the
    top of the file. The seal covers everything at once: change one character
    anywhere and the fingerprint no longer matches. Only someone with your
    master password can make a valid seal.
    """
    body = {k: v for k, v in data.items() if k != "seal"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _b64e(hmac.new(seal_key, canonical, hashlib.sha256).digest())


def generate_password(length: int = 20, symbols: bool = True) -> str:
    """Random password using the OS's cryptographically secure randomness."""
    alphabet = string.ascii_letters + string.digits
    if symbols:
        alphabet += "!@#$%^&*-_=+?"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        # make sure it has at least a lower, upper, and digit
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw)):
            return pw


# --------------------------------------------------------------------------
# The vault
# --------------------------------------------------------------------------

class Vault:
    """Load, unlock, edit and save the encrypted vault file.

    Everything in self._data["entries"] is encrypted text. Decrypted values
    are produced only on demand (when you click an entry) and never saved.
    """

    def __init__(self, path: str | None = None):
        self.path = path or default_vault_path()
        self._data: dict | None = None
        self._fernet: Fernet | None = None
        self._seal_key: bytes | None = None

    @property
    def backup_path(self) -> str:
        return self.path + ".bak"

    # ---- state -----------------------------------------------------------

    def exists(self) -> bool:
        return os.path.isfile(self.path)

    @property
    def is_unlocked(self) -> bool:
        return self._fernet is not None

    def _require_unlocked(self):
        if not self.is_unlocked:
            raise VaultError("Vault is locked.")

    # ---- create / unlock / lock -----------------------------------------

    def create(self, master: str) -> None:
        if self.exists():
            raise VaultError("A vault already exists at " + self.path)
        if len(master) < MIN_MASTER_LENGTH:
            raise VaultError(f"Master password must be at least {MIN_MASTER_LENGTH} characters.")
        salt = secrets.token_bytes(16)  # random per vault, so identical passwords hash differently
        verifier, key, seal_key = derive_keys(master, salt)
        self._seal_key = seal_key
        self._data = {
            "app": APP_NAME,
            "version": FILE_VERSION,
            "kdf": "pbkdf2-sha256",
            "iterations": KDF_ITERATIONS,
            "salt": _b64e(salt),
            "verifier": _b64e(verifier),
            "entries": [],
        }
        self._fernet = Fernet(key)
        self._save()

    def unlock(self, master: str) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise VaultError("No vault found. Create one first.")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise VaultError("The vault file is damaged or isn't a HushKey file.")

        try:
            salt = _b64d(data["salt"])
            stored = _b64d(data["verifier"])
            iterations = int(data.get("iterations", KDF_ITERATIONS))
        except (KeyError, ValueError):
            raise VaultError("The vault file is missing required fields.")

        verifier, key, seal_key = derive_keys(master, salt, iterations)
        # compare_digest takes the same time whether 1 or 31 bytes match,
        # so timing can't leak how close a guess was.
        if not hmac.compare_digest(verifier, stored):
            raise WrongPassword("Wrong master password.")

        # Right password - now make sure nobody changed the file behind our back.
        expected = compute_seal(data, seal_key)
        if not hmac.compare_digest(expected, str(data.get("seal", ""))):
            raise VaultError(
                "Security warning: the vault file was changed outside HushKey "
                "and failed its tamper check. Your previous copy is at:\n" + self.backup_path
            )

        self._data = data
        self._data.setdefault("entries", [])
        self._fernet = Fernet(key)
        self._seal_key = seal_key

    def lock(self) -> None:
        """Forget the keys and data. (Python can't truly wipe memory, but
        dropping the references lets them be cleaned up.)"""
        self._fernet = None
        self._seal_key = None
        self._data = None

    def change_master(self, old: str, new: str) -> None:
        """Re-encrypt every entry under a key from the new master password."""
        self._require_unlocked()
        if len(new) < MIN_MASTER_LENGTH:
            raise VaultError(f"Master password must be at least {MIN_MASTER_LENGTH} characters.")
        salt = _b64d(self._data["salt"])
        verifier, _, _ = derive_keys(old, salt, int(self._data["iterations"]))
        if not hmac.compare_digest(verifier, _b64d(self._data["verifier"])):
            raise WrongPassword("Current master password is wrong.")

        plain = [self._decrypt_entry(e) for e in self._data["entries"]]
        new_salt = secrets.token_bytes(16)
        new_verifier, new_key, new_seal_key = derive_keys(new, new_salt)
        self._data["salt"] = _b64e(new_salt)
        self._data["verifier"] = _b64e(new_verifier)
        self._data["iterations"] = KDF_ITERATIONS
        self._fernet = Fernet(new_key)
        self._seal_key = new_seal_key
        self._data["entries"] = [
            self._encrypt_entry(p["title"], p["username"], p["password"], p["id"], p["created"])
            for p in plain
        ]
        self._save()

    # ---- encryption helpers ---------------------------------------------

    def _enc(self, text: str) -> str:
        return self._fernet.encrypt(text.encode("utf-8")).decode("ascii")

    def _dec(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken:
            raise VaultError("An entry failed its tamper check - the file may have been edited.")

    def _encrypt_entry(self, title, username, password, entry_id=None, created=None) -> dict:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return {
            "id": entry_id or uuid.uuid4().hex,
            "title": self._enc(title),
            "username": self._enc(username),
            "password": self._enc(password),
            "created": created or now,
            "updated": now,
        }

    def _decrypt_entry(self, e: dict) -> dict:
        return {
            "id": e["id"],
            "title": self._dec(e["title"]),
            "username": self._dec(e["username"]),
            "password": self._dec(e["password"]),
            "created": e.get("created", ""),
        }

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
                pass  # a failed backup shouldn't stop the real save
        _atomic_write_json(self.path, self._data)

    # ---- public entry API -----------------------------------------------

    def list_titles(self) -> list[tuple[str, str]]:
        """(id, title) for every entry, sorted A-Z. Usernames/passwords stay encrypted."""
        self._require_unlocked()
        rows = [(e["id"], self._dec(e["title"])) for e in self._data["entries"]]
        return sorted(rows, key=lambda r: r[1].lower())

    def reveal(self, entry_id: str) -> tuple[str, str]:
        """Decrypt one entry's (username, password) - called when you click it."""
        self._require_unlocked()
        e = self._find(entry_id)
        return self._dec(e["username"]), self._dec(e["password"])

    def get(self, entry_id: str) -> dict:
        self._require_unlocked()
        return self._decrypt_entry(self._find(entry_id))

    def add(self, title: str, username: str, password: str) -> str:
        self._require_unlocked()
        if not title.strip():
            raise VaultError("Client / title can't be empty.")
        entry = self._encrypt_entry(title.strip(), username, password)
        self._data["entries"].append(entry)
        self._save()
        return entry["id"]

    def update(self, entry_id: str, title: str, username: str, password: str) -> None:
        self._require_unlocked()
        if not title.strip():
            raise VaultError("Client / title can't be empty.")
        old = self._find(entry_id)
        new = self._encrypt_entry(title.strip(), username, password, entry_id, old.get("created"))
        idx = self._data["entries"].index(old)
        self._data["entries"][idx] = new
        self._save()

    def delete(self, entry_id: str) -> None:
        self._require_unlocked()
        self._data["entries"].remove(self._find(entry_id))
        self._save()
