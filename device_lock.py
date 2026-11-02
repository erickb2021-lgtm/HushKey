"""
device_lock.py - keep a small secret in the computer's own protected storage.

Used by "Remember this device for 30 days" (stay signed in). HushKey never
saves your master password. Instead it saves a random unlock key here:

  Windows: encrypted with Windows' built-in protection (DPAPI), the same
           system Windows uses for saved Wi-Fi passwords. Only YOUR Windows
           account on THIS computer can decrypt it.
  macOS:   stored in your login Keychain, locked to your Mac account.
  Other:   a file only your account can read (for running from source).

Signing out deletes it. The vault itself also records when it expires (30
days), inside its tamper-proof seal.
"""

import base64
import ctypes
import hashlib
import os
import subprocess
import sys

SERVICE = "HushKey"


def _name(email: str) -> str:
    return "autosignin-" + hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:20]


# ---- Windows: DPAPI ---------------------------------------------------------

class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data: bytes, protect: bool) -> bytes:
    from ctypes import wintypes  # noqa: F401  (Windows only)
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _Blob()
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    ok = fn(ctypes.byref(blob_in), None, None, None, None, CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out))
    if not ok:
        raise OSError("Windows protected storage refused the request.")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _file_path(folder: str, name: str) -> str:
    return os.path.join(folder, name + ".key")


# ---- public functions ---------------------------------------------------------

def save(email: str, secret: bytes, folder: str) -> None:
    name = _name(email)
    if sys.platform == "darwin":
        subprocess.run(["security", "add-generic-password", "-U", "-a", name, "-s", SERVICE,
                        "-w", base64.b64encode(secret).decode("ascii")],
                       check=True, capture_output=True, timeout=15)
        return
    data = _dpapi(secret, protect=True) if os.name == "nt" else secret
    os.makedirs(folder, exist_ok=True)
    path = _file_path(folder, name)
    with open(path, "wb") as f:
        f.write(data)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load(email: str, folder: str):
    """The saved secret, or None if there isn't one (or it can't be read)."""
    name = _name(email)
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["security", "find-generic-password", "-a", name, "-s", SERVICE, "-w"],
                                 capture_output=True, timeout=15)
            if out.returncode != 0:
                return None
            return base64.b64decode(out.stdout.strip())
        path = _file_path(folder, name)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            data = f.read()
        return _dpapi(data, protect=False) if os.name == "nt" else data
    except Exception:
        return None


def delete(email: str, folder: str) -> None:
    name = _name(email)
    try:
        if sys.platform == "darwin":
            subprocess.run(["security", "delete-generic-password", "-a", name, "-s", SERVICE],
                           capture_output=True, timeout=15)
        path = _file_path(folder, name)
        if os.path.isfile(path):
            with open(path, "r+b") as f:  # overwrite before deleting
                f.write(b"\0" * os.path.getsize(path))
            os.remove(path)
    except Exception:
        pass
