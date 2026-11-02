"""
leakcheck.py - has a password shown up in a known data leak?

Uses Have I Been Pwned's free "range" check, the same way Firefox,
1Password and Bitwarden do it, so your passwords stay private:

  1. HushKey turns the password into a SHA-1 hash ON YOUR COMPUTER.
  2. Only the first 5 characters of that hash are sent.
     (Hundreds of different leaked passwords share those 5 characters.)
  3. The site sends back every leaked hash that starts with them, and
     HushKey checks for a match on your computer.

Nobody, not even Have I Been Pwned, learns your password or its full hash.
"""

import urllib.request

try:
    from cloud import _SSL
except Exception:  # pragma: no cover
    import ssl
    _SSL = ssl.create_default_context()

RANGE_URL = "https://api.pwnedpasswords.com/range/"
TIMEOUT = 15


def _default_fetch(prefix: str) -> str:
    req = urllib.request.Request(RANGE_URL + prefix, headers={
        "User-Agent": "HushKey-password-manager",
        "Add-Padding": "true",   # the reply is padded so its size gives nothing away either
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL) as r:
        return r.read().decode("utf-8", "replace")


def leaked_ids(hashes: dict, fetch=_default_fetch) -> set:
    """hashes: {login id: uppercase SHA-1 hex}. Returns the ids whose
    password is in a known leak. Each 5-character prefix is asked once."""
    by_prefix = {}
    for entry_id, h in hashes.items():
        by_prefix.setdefault(h[:5], []).append((entry_id, h[5:]))
    found = set()
    for prefix, items in by_prefix.items():
        counts = {}
        for line in fetch(prefix).splitlines():
            suffix, _, n = line.strip().partition(":")
            if suffix and n.strip() not in ("", "0"):   # padding lines have a count of 0
                counts[suffix.upper()] = n
        for entry_id, rest in items:
            if rest in counts:
                found.add(entry_id)
    return found
