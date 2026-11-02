"""
importer.py - bring passwords in from Google and other password managers,
and write them back out.

Google doesn't let apps read saved passwords directly, so importing works
through the export file every password manager can make:
  Google / Chrome, Microsoft Edge, Firefox, Bitwarden, LastPass, 1Password,
  Apple Passwords, Dashlane... all export a .csv (spreadsheet-style) file.

That file is NOT encrypted - anyone who opens it can read every password -
so after importing, HushKey overwrites it and deletes it (secure_delete).

Nothing here touches the internet. Imported logins go straight into the
encrypted vault on this computer.
"""

import csv
import io
import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import brand_icons

MAX_FILE_BYTES = 20 * 1024 * 1024  # a 20 MB password export would be ~100,000 logins


class ImportError_(Exception):
    """A friendly message about why a file couldn't be imported."""


@dataclass
class Item:
    title: str
    username: str
    password: str
    url: str = ""
    icon: str = ""
    duplicate: bool = False     # already in the vault (or twice in the file)
    selected: bool = True       # checkbox on the review screen


@dataclass
class ImportResult:
    source: str                 # e.g. "Google / Chrome"
    items: list = field(default_factory=list)
    skipped: int = 0            # rows with no password (notes, cards, etc.)


# Column names each password manager uses (all compared in lowercase).
TITLE_COLS = ["name", "title", "account", "item name"]
URL_COLS = ["url", "login_uri", "website", "web site", "origin", "login url", "uri", "hostname"]
USER_COLS = ["username", "login_username", "login", "user", "email", "user name", "login name",
             "username1"]
PASS_COLS = ["password", "login_password", "pass", "passwd"]

SOURCES = [  # (name shown to the user, columns that identify it)
    ("Bitwarden", {"login_uri", "login_username", "login_password"}),
    ("Firefox", {"httprealm", "formactionorigin", "guid"}),
    ("LastPass", {"grouping", "fav", "extra"}),
    ("1Password", {"otpauth", "archived"}),
    ("Apple Passwords", {"otpauth"}),
    ("Dashlane", {"username2", "otpsecret"}),
    ("Google / Chrome", {"name", "url", "username", "password", "note"}),
    ("Microsoft Edge", {"name", "url", "username", "password"}),
]


def _pick(columns, candidates):
    for c in candidates:
        if c in columns:
            return columns[c]
    return None


def _domain(url: str) -> str:
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _looks_like_domain(text: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", text.strip().lower()))


# Web addresses whose name isn't the brand (store.steampowered.com is Steam).
DOMAIN_NAMES = {
    "steampowered": "Steam", "steamcommunity": "Steam", "twitter": "X", "x": "X",
    "live": "Microsoft", "microsoftonline": "Microsoft", "microsoft": "Microsoft",
    "outlook": "Outlook", "hotmail": "Outlook", "xbox": "Xbox", "minecraft": "Minecraft",
    "amazon": "Amazon", "battle": "Battle.net", "blizzard": "Blizzard", "nintendo": "Nintendo",
    "sonyentertainmentnetwork": "PlayStation", "playstation": "PlayStation",
    "appleid": "Apple", "apple": "Apple", "icloud": "iCloud", "bankofamerica": "Bank of America",
    "wellsfargo": "Wells Fargo", "americanexpress": "American Express", "capitalone": "Capital One",
    "cash": "Cash App", "linkedin": "LinkedIn", "riotgames": "Riot Games",
    "leagueoflegends": "League of Legends", "playvalorant": "Valorant", "epicgames": "Epic Games",
    "ea": "EA", "youtube": "YouTube", "github": "GitHub", "doordash": "DoorDash",
    "paypal": "PayPal", "fb": "Facebook", "facebook": "Facebook", "instagram": "Instagram",
    "tiktok": "TikTok", "snapchat": "Snapchat", "whatsapp": "WhatsApp", "chase": "Chase",
    "disneyplus": "Disney+", "hulu": "Hulu", "primevideo": "Prime Video", "hbomax": "Max",
}


def nice_title(raw_title: str, url: str) -> str:
    """Turn 'accounts.riotgames.com' or 'https://www.netflix.com/login' into a
    friendly client name like 'Riot Games' or 'Netflix'."""
    title = (raw_title or "").strip()
    if title and not _looks_like_domain(title) and "://" not in title:
        return title[:80]
    domain = _domain(title if (_looks_like_domain(title) or "://" in title) else url)
    if not domain:
        return title[:80] or "Imported login"
    parts = domain.split(".")
    # keep the main name: accounts.google.com -> google, bbc.co.uk -> bbc
    core = parts[-3] if len(parts) >= 3 and len(parts[-2]) <= 3 and len(parts[-1]) == 2 else (
        parts[-2] if len(parts) >= 2 else parts[0])
    if core in DOMAIN_NAMES:
        return DOMAIN_NAMES[core]
    slug = brand_icons.suggest(core)
    if slug and not slug.startswith("hk-"):
        return brand_icons.title(slug)
    return core.capitalize()


def read_csv_text(text: str, existing=()) -> ImportResult:
    """Read the export file's text. `existing` is a list of (title, username)
    already in the vault, used to flag duplicates."""
    text = text.lstrip("﻿")
    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample.strip() else csv.excel
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    try:
        header = next(reader)
    except StopIteration:
        raise ImportError_("That file is empty.")
    columns = {}
    for i, name in enumerate(header):
        columns.setdefault(name.strip().lower(), i)

    pass_i = _pick(columns, PASS_COLS)
    if pass_i is None:
        raise ImportError_("This doesn't look like a password export: there's no 'password' column. "
                           "Make sure you chose the file you exported from Google (or your other "
                           "password manager).")
    title_i = _pick(columns, TITLE_COLS)
    url_i = _pick(columns, URL_COLS)
    user_i = _pick(columns, USER_COLS)
    type_i = columns.get("type")  # Bitwarden: login / note / card / identity

    names = set(columns)
    source = "Password export"
    for label, needed in SOURCES:
        if needed <= names:
            source = label
            break

    seen = {(t.strip().lower(), (u or "").strip().lower()) for t, u in existing}
    result = ImportResult(source=source)

    def cell(row, i):
        return row[i].strip() if i is not None and i < len(row) else ""

    for row in reader:
        if not any(c.strip() for c in row):
            continue
        if type_i is not None and cell(row, type_i).lower() not in ("", "login"):
            result.skipped += 1
            continue
        password = row[pass_i] if pass_i < len(row) else ""
        if not password:
            result.skipped += 1
            continue
        url = cell(row, url_i)
        title = nice_title(cell(row, title_i), url)
        username = cell(row, user_i)
        icon = brand_icons.suggest(title) or brand_icons.suggest(_domain(url).split(".")[0]) or ""
        key = (title.lower(), username.lower())
        dup = key in seen
        seen.add(key)
        result.items.append(Item(title=title, username=username, password=password, url=url,
                                 icon=icon, duplicate=dup, selected=not dup))
    if not result.items:
        raise ImportError_("No logins with passwords were found in that file.")
    return result


def read_csv_file(path: str, existing=()) -> ImportResult:
    if os.path.getsize(path) > MAX_FILE_BYTES:
        raise ImportError_("That file is too big to be a password export.")
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ImportError_("HushKey couldn't read that file's text.")
    return read_csv_text(text, existing)


def secure_delete(path: str) -> bool:
    """Overwrite the file with zeros, then delete it.

    The overwrite makes the passwords much harder to recover with undelete
    tools. (On SSDs the drive may keep old copies internally, so it's not a
    100% guarantee, but it's far better than a normal delete or the Trash.)
    Returns True if the file is gone."""
    try:
        size = os.path.getsize(path)
        with open(path, "r+b") as f:
            remaining = size
            chunk = b"\0" * 65536
            while remaining > 0:
                n = min(remaining, len(chunk))
                f.write(chunk[:n])
                remaining -= n
            f.flush()
            os.fsync(f.fileno())
        os.remove(path)
    except OSError:
        pass
    return not os.path.exists(path)


def write_csv(path: str, entries) -> None:
    """Write logins as a Google/Chrome-style CSV, which every password manager
    can import. NOT encrypted - only for moving to another app."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "url", "username", "password", "note"])
        for e in entries:
            w.writerow([e["title"], e.get("url", ""), e["username"], e["password"], ""])
