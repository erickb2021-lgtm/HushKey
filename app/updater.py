"""
updater.py - automatic updates from your GitHub releases.

How it works:
  1. When HushKey opens, it asks GitHub for the newest release
     (api.github.com/repos/<you>/<repo>/releases/latest). Nothing about the
     user is sent; it's the same public page anyone can open.
  2. If it's newer than this copy, HushKey downloads the right file
     (HushKey-Windows.exe or HushKey-Mac.zip) in the background and checks
     its SHA-256 fingerprint against the .sha256.txt published with it.
  3. "Update now" installs it right away and reopens HushKey.
     "Later" installs it automatically when you close HushKey, so the next
     time you open it, you're on the newest version.

Windows: runs the normal installer silently (it closes HushKey and keeps your
vault). Mac: swaps the old HushKey.app for the new one after HushKey quits.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass

try:
    from cloud import _SSL
except Exception:  # pragma: no cover
    import ssl
    _SSL = ssl.create_default_context()

from version import __version__

try:
    from version import __repo__
except ImportError:
    __repo__ = ""

IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"
ASSET = "HushKey-Windows.exe" if IS_WIN else ("HushKey-Mac.zip" if IS_MAC else "")
TIMEOUT = 20


class UpdateError(Exception):
    pass


@dataclass
class Release:
    version: str        # "2.0.10"
    notes: str          # the release description, cleaned up
    url: str            # download link for this computer's file
    sha_url: str        # link to its .sha256.txt
    size: int = 0


def parse_version(text: str):
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:4]) or (0,)


def is_newer(candidate: str, current: str = __version__) -> bool:
    return parse_version(candidate) > parse_version(current)


def _clean_notes(body: str) -> str:
    lines = []
    for line in (body or "").splitlines():
        line = re.sub(r"^#+\s*", "", line.strip())
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", line)
        line = re.sub(r"^[-*]\s+", "• ", line)
        lines.append(line)
    text = "\n".join(lines).strip()
    return (text[:700] + "…") if len(text) > 700 else text


class Updater:
    def __init__(self, repo: str = None, opener=None, download_dir: str = None):
        self.repo = (repo if repo is not None else __repo__).strip()
        self._open = opener or (lambda req: urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL))
        self.download_dir = download_dir or os.path.join(tempfile.gettempdir(), "HushKey-update")

    @property
    def enabled(self) -> bool:
        """Updates only work in the installed app built by GitHub."""
        return bool(self.repo and ASSET and getattr(sys, "frozen", False))

    def _get(self, url: str, accept="application/vnd.github+json") -> bytes:
        req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "HushKey-updater"})
        try:
            return self._open(req).read()
        except Exception as exc:
            raise UpdateError(f"Couldn't check for updates ({exc.__class__.__name__}).")

    def check(self, asset: str = ASSET):
        """The newest release if it's newer than this copy AND its download
        for this computer is ready; otherwise None."""
        if not self.repo or not asset:
            return None
        info = json.loads(self._get(f"https://api.github.com/repos/{self.repo}/releases/latest"))
        version = (info.get("tag_name") or "").lstrip("vV")
        if not version or not is_newer(version):
            return None
        files = {a.get("name"): a for a in info.get("assets") or []}
        main, sha = files.get(asset), files.get(asset + ".sha256.txt")
        if not main or not sha:
            return None  # GitHub is still building this release; check again next time
        return Release(version=version, notes=_clean_notes(info.get("body") or "") or
                       "Improvements and fixes.", url=main["browser_download_url"],
                       sha_url=sha["browser_download_url"], size=int(main.get("size") or 0))

    def download(self, release: Release, asset: str = ASSET) -> str:
        """Download and verify. Returns the local file path."""
        folder = os.path.join(self.download_dir, release.version)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, asset)
        expected = self._get(release.sha_url, accept="application/octet-stream").decode(
            "ascii", "ignore").split()[0].lower()
        if os.path.isfile(path) and _sha256(path) == expected:
            return path  # already downloaded
        data = self._get(release.url, accept="application/octet-stream")
        if hashlib.sha256(data).hexdigest() != expected:
            raise UpdateError("The downloaded update didn't match its fingerprint, so it was thrown away.")
        tmp = path + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return path

    # ---- installing -----------------------------------------------------------

    def mac_app_path(self):
        """/Applications/HushKey.app (the bundle this copy is running from)."""
        exe = os.path.abspath(sys.executable)
        parts = exe.split(os.sep)
        for i in range(len(parts) - 1, 0, -1):
            if parts[i].endswith(".app"):
                return os.sep.join(parts[: i + 1])
        return None

    def can_install(self) -> tuple:
        """(True, "") or (False, reason to show the user)."""
        if IS_MAC:
            app = self.mac_app_path()
            if not app or "/AppTranslocation/" in app:
                return False, ("Move HushKey into your Applications folder to turn on automatic "
                               "updates (macOS runs it from a temporary place until you do).")
            if not os.access(os.path.dirname(app), os.W_OK):
                return False, "HushKey can't update itself in this folder. Move it to Applications."
        return True, ""

    def install(self, path: str, relaunch: bool) -> None:
        """Start installing. HushKey must quit right after calling this."""
        if IS_WIN:
            args = [path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"]
            if relaunch:
                args.append("/RELAUNCH=1")
            flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(args, creationflags=flags, close_fds=True)
            return
        if IS_MAC:
            app = self.mac_app_path()
            work = os.path.join(os.path.dirname(path), "unzipped")
            subprocess.run(["rm", "-rf", work], check=False)
            subprocess.run(["ditto", "-x", "-k", path, work], check=True, timeout=120)
            new_app = os.path.join(work, "HushKey.app")
            if not os.path.isdir(new_app):
                raise UpdateError("The Mac update file didn't contain HushKey.app.")
            script = os.path.join(os.path.dirname(path), "install.sh")
            with open(script, "w") as f:
                f.write(MAC_SCRIPT)
            subprocess.Popen(["/bin/bash", script, str(os.getpid()), new_app, app, "1" if relaunch else "0"],
                             start_new_session=True, close_fds=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        raise UpdateError("Automatic updates aren't available on this system.")


MAC_SCRIPT = r"""#!/bin/bash
# Wait for HushKey to quit, swap in the new version, then (maybe) reopen it.
PID="$1"; NEW="$2"; DEST="$3"; RELAUNCH="$4"
for i in $(seq 1 120); do kill -0 "$PID" 2>/dev/null || break; sleep 0.5; done
rm -rf "$DEST.old"
if mv "$DEST" "$DEST.old" && mv "$NEW" "$DEST"; then
  rm -rf "$DEST.old"
else
  [ -d "$DEST.old" ] && [ ! -d "$DEST" ] && mv "$DEST.old" "$DEST"
fi
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null
[ "$RELAUNCH" = "1" ] && open "$DEST"
"""


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
