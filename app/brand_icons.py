"""
brand_icons.py - find and draw app logos (Riot, Discord, Steam...) for logins.

The logos come from Simple Icons (free, CC0), bundled in
assets/brand_icons.json.gz, so nothing is downloaded and no website learns
which apps you use. Each logo is one SVG "path" (a list of drawing commands
like "move here, draw a curve to there"). This file turns that path into a
see-through PNG with Pillow, so it blends into HushKey's dark background.
"""

import base64
import gzip
import io
import json
import math
import os
import re
import sys
import threading

from PIL import Image

_lock = threading.Lock()
_icons = None        # list of [slug, title, hex, path, aliases]
_by_slug = None
_cache = {}

BACKGROUND = (22, 26, 34)  # HushKey card color, used to keep logos readable
CUSTOM_PREFIX = "img:"     # a login's own picture is saved as "img:<base64 PNG>"

# Everyday icons drawn for HushKey (24x24 SVG paths, "evenodd" fill so the
# inner shapes cut holes). They cover anything without a brand logo; e.g.
# typing "xbox" or "minecraft" offers the game controller.
EVERYDAY = [
    ["hk-controller", "Game controller", "3DDC97",
     "M7 6h10c3 0 5 3 5.6 7l.4 3c.3 2-1.9 3.4-3.6 2.2L16 16H8l-3.4 2.2C2.9 19.4.7 18 1 16l.4-3C2 9 4 6 7 6Z"
     "M6 9h2v2h2v2H8v2H6v-2H4v-2h2ZM15 11a1.3 1.3 0 1 0 2.6 0a1.3 1.3 0 1 0-2.6 0Z"
     "M17.5 13.5a1.3 1.3 0 1 0 2.6 0a1.3 1.3 0 1 0-2.6 0Z",
     ["game", "gaming", "games", "console", "xbox", "nintendo", "switch", "minecraft", "blizzard",
      "call of duty", "warzone", "overwatch", "apex", "genshin", "hoyoverse", "rocket league",
      "world of warcraft", "hearthstone", "diablo", "bethesda"]],
    ["hk-bank", "Bank", "F2C14E", "M12 2 2 7v2h20V7ZM4 10h3v8H4ZM10.5 10h3v8h-3ZM17 10h3v8h-3ZM2 19h20v3H2Z",
     ["bank", "banking", "credit union", "savings", "checking", "capital one", "finance"]],
    ["hk-email", "Email", "6CB6FF", "M2 5h20v14H2ZM4 7v.5l8 5.5 8-5.5V7l-8 5.5Z",
     ["email", "mail", "inbox", "outlook", "yahoo", "hotmail", "aol"]],
    ["hk-shopping", "Shopping", "FF9F5A", "M5 7h14l-1 15H6ZM9 7V6a3 3 0 0 1 6 0v1h-2V6a1 1 0 0 0-2 0v1Z",
     ["shopping", "shop", "store", "walmart", "costco", "best buy", "shein", "temu", "home depot",
      "lowes", "sephora", "ulta", "macys", "kohls", "hm", "h&m", "gap", "old navy", "dollar general"]],
    ["hk-chat", "Chat", "B18CFF",
     "M4 3h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z",
     ["chat", "messages", "messaging", "texting", "slack", "teams", "skype"]],
    ["hk-music", "Music", "FF6FA8", "M9 3h11v12.5a3 3 0 1 1-2-2.8V7h-7v10.5a3 3 0 1 1-2-2.8Z",
     ["music", "songs", "audio", "soundcloud", "pandora", "apple music"]],
    ["hk-video", "Video", "FF6B6B",
     "M3 4h18a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2ZM10 8.5v7l6-3.5Z",
     ["video", "movies", "clips", "video editor"]],
    ["hk-cloud", "Cloud", "8FD3FF",
     "M7 19a5 5 0 0 1-.6-10A7 7 0 0 1 19.6 9.5 4.8 4.8 0 0 1 18 19Z",
     ["cloud", "storage", "backup", "onedrive", "box"]],
    ["hk-work", "Work", "C9A27E",
     "M9 3h6a2 2 0 0 1 2 2v1h4a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4V5a2 2 0 0 1 2-2ZM9 5v1h6V5Z",
     ["work", "job", "office", "business", "linkedin", "microsoft", "company"]],
    ["hk-school", "School", "7CC4FF",
     "M12 3 1 9l11 6 9-4.9V16h2V9ZM5 13v4c0 1.7 3.1 3 7 3s7-1.3 7-3v-4l-7 3.8Z",
     ["school", "college", "university", "student", "class", "canvas", "blackboard", "education"]],
    ["hk-money", "Money", "3DDC97",
     "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20Z"
     "M11 6h2v1.1c1.7.3 3 1.4 3 2.9h-2c0-.6-.9-1-2-1s-2 .4-2 1 .9 1 2 1c2.2 0 4 1.1 4 3 0 1.5-1.3 2.6-3 2.9V18h-2v-1.1"
     "c-1.7-.3-3-1.4-3-2.9h2c0 .6.9 1 2 1s2-.4 2-1-.9-1-2-1c-2.2 0-4-1.1-4-3 0-1.5 1.3-2.6 3-2.9Z",
     ["money", "cash", "crypto", "wallet", "payment", "investing", "stocks"]],
    ["hk-food", "Restaurant", "FFA64D",
     "M5 2h1.5v6H8V2h1.5v6H11V2h1.5v7a3 3 0 0 1-2.5 3V22H8V12a3 3 0 0 1-3-3ZM18.5 2C16 3.5 15 6 15 9v4h2v9h2V2Z",
     ["food", "restaurant", "takeout", "take out", "delivery", "dinner", "lunch", "grubhub", "seamless",
      "chipotle", "chickfila", "chick fil a", "popeyes", "subway", "panera", "panera bread", "panda express",
      "olive garden", "applebees", "chilis", "wingstop", "jollibee", "nandos", "arbys", "qdoba", "raising canes"]],
    ["hk-pizza", "Pizza", "FF6B6B",
     "M12 2C7.5 2 3.6 3.9 1.5 6.5L12 22 22.5 6.5C20.4 3.9 16.5 2 12 2ZM9 8.5a1.6 1.6 0 1 0 0 3.2a1.6 1.6 0 0 0 0-3.2Z"
     "M14.8 11a1.6 1.6 0 1 0 0 3.2a1.6 1.6 0 0 0 0-3.2ZM12 4.2c3 0 5.8 1 7.6 2.7l-.9 1.3C17.2 6.8 14.7 6 12 6S6.8 6.8 5.3 8.2l-.9-1.3C6.2 5.2 9 4.2 12 4.2Z",
     ["pizza", "dominos", "domino's", "pizza hut", "pizzahut", "papa johns", "papajohns", "little caesars",
      "marcos pizza", "round table"]],
    ["hk-burger", "Burger", "F2C14E",
     "M3 10.5A9 7 0 0 1 21 10.5ZM2 12.5h20v3H2ZM3 17.5h18a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3Z",
     ["burger", "burgers", "wendys", "wendy's", "five guys", "in n out", "innout", "whataburger", "shake shack",
      "culvers", "sonic", "carls jr", "jack in the box", "white castle", "smashburger"]],
    ["hk-coffee", "Coffee", "C9A27E",
     "M3 8h14v6a6 6 0 0 1-6 6H9a6 6 0 0 1-6-6ZM17 9.5h1.5a3 3 0 0 1 0 6H17v-2h1.5a1 1 0 0 0 0-2H17ZM7 2h2v4H7ZM11 2h2v4h-2Z",
     ["coffee", "cafe", "dunkin", "dunkin donuts", "tim hortons", "dutch bros", "peets", "caribou", "tea"]],
    ["hk-heart", "Heart", "FF6F91", "M12 21 3.5 12.6A5 5 0 0 1 12 6a5 5 0 0 1 8.5 6.6Z",
     ["heart", "love", "dating", "favorite", "health"]],
    ["hk-star", "Star", "F2C14E", "M12 2l3 6.5 7 .8-5.2 4.8 1.4 7L12 17.6 5.8 21.1l1.4-7L2 9.3l7-.8Z",
     ["star", "favorite", "important"]],
    ["hk-key", "Key", "F2C14E",
     "M8 3a5 5 0 1 0 4.6 7H15v2h2v-2h2v3h2V8h-8.4A5 5 0 0 0 8 3ZM8 6a2 2 0 1 1 0 4a2 2 0 0 1 0-4Z",
     ["key", "password", "wifi", "router", "door"]],
    ["hk-lock", "Lock", "3DDC97",
     "M6 10V7a6 6 0 0 1 12 0v3h1a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V11a1 1 0 0 1 1-1ZM8 10h8V7a4 4 0 0 0-8 0Z",
     ["lock", "secure", "security", "vpn", "private"]],
    ["hk-home", "Home", "8FD3FF", "M12 3 2 11h3v10h5v-6h4v6h5V11h3Z",
     ["home", "house", "utilities", "electric", "internet", "rent", "apartment"]],
    ["hk-phone", "Phone", "B18CFF",
     "M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2ZM7 5v13h10V5Z",
     ["phone", "mobile", "carrier", "verizon", "att", "t-mobile", "sim"]],
]
# added in v2.0.18: Amazon (its logo isn't in Simple Icons, so HushKey draws its own) and icons
# for airlines, cars, cards, streaming, groceries, hotels and video games
EVERYDAY += [
    ["hk-amazon", "Amazon", "FF9900",
     "M6 2.5h12v7.5H6ZM10.5 2.5v3h3v-3ZM2.9 12.2Q10.5 18.6 17.3 15L18 16.6Q10.5 20.5 2 13.6ZM16.2 13.6 22 13 19.6 18.6Z",
     []],
    ["hk-plane", "Airline", "6CB6FF",
     "M12 1.5c.9 0 1.5 1 1.5 2.5v5l8 4.5v2l-8-2.5v5l2.5 2V22L12 21l-3.5 1v-2l2.5-2v-5l-8 2.5v-2l8-4.5V4c0-1.5.6-2.5 1.5-2.5Z",
     []],
    ["hk-car", "Car", "FF6B6B",
     "M5 11l1.6-4.6A2 2 0 0 1 8.5 5h7a2 2 0 0 1 1.9 1.4L19 11a2 2 0 0 1 2 2v4h-2v2h-3v-2H8v2H5v-2H3v-4a2 2 0 0 1 2-2ZM7.2 11h9.6l-1.2-3.6a.6.6 0 0 0-.6-.4H9a.6.6 0 0 0-.6.4ZM5 13.6a1.3 1.3 0 1 0 2.6 0a1.3 1.3 0 1 0-2.6 0ZM16.4 13.6a1.3 1.3 0 1 0 2.6 0a1.3 1.3 0 1 0-2.6 0Z",
     []],
    ["hk-card", "Credit card", "8FD3FF",
     "M3 4h18a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2ZM1 8v3h22V8ZM4 14.5h6v2H4Z",
     []],
    ["hk-tv", "Streaming TV", "B18CFF",
     "M3 3h18a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2ZM3.2 5.2v10.6h17.6V5.2ZM10 7.5v6l5-3ZM7 20h10v2H7Z",
     []],
    ["hk-cart", "Groceries", "3DDC97",
     "M1 3h3.6l3 12H19v2H6L3 5H1ZM7 6h15l-2.2 7H8.7ZM6.8 19.6a1.8 1.8 0 1 0 3.6 0a1.8 1.8 0 1 0-3.6 0ZM15.4 19.6a1.8 1.8 0 1 0 3.6 0a1.8 1.8 0 1 0-3.6 0Z",
     []],
    ["hk-hotel", "Hotel", "F2C14E",
     "M2 4h2v8h18v8h-2v-2H4v2H2ZM5.5 9a2.2 2.2 0 1 0 4.4 0a2.2 2.2 0 1 0-4.4 0ZM11 7.5h8a3 3 0 0 1 3 3V11H11Z",
     []],
    ["hk-sword", "Video game", "FF6FA8",
     "M11 1h2l1.2 2.2V14h-4.4V3.2ZM6 14.2h12v2.2H6ZM11 16.6h2v3.8h-2ZM10.4 22a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0-3.2 0Z",
     []],
]
EVERYDAY += [
    ["hk-train", "Train & bus", "8FD3FF",
     "M6 2h12a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3l2 3h-2.5l-2-3h-7l-2 3H4l2-3a3 3 0 0 1-3-3V5a3 3 0 0 1 3-3Z"
     "M5.5 5v5h13V5ZM7 13a1.5 1.5 0 1 0 0 3a1.5 1.5 0 1 0 0-3ZM17 13a1.5 1.5 0 1 0 0 3a1.5 1.5 0 1 0 0-3Z",
     ["train", "bus", "rail", "subway pass", "transit", "metro card", "commute"]],
    ["hk-shield", "Insurance", "3DDC97",
     "M12 2 3 5.5v6c0 5.3 3.8 9.4 9 10.5 5.2-1.1 9-5.2 9-10.5v-6Z"
     "M10.6 15.6 7.2 12.2l1.4-1.4 2 2 4.8-4.8 1.4 1.4Z",
     ["insurance", "health insurance", "car insurance", "home insurance", "life insurance", "doctor",
      "health", "dental", "pharmacy", "medical"]],
]
_EVERYDAY_SLUGS = {e[0] for e in EVERYDAY}
NONZERO = {"hk-amazon"}   # drawn as overlapping pieces, so no holes


_NAMED = {}   # a company drawn with an everyday icon (see brand_named.py) -> that icon's slug
# words left out when matching a company by its short name ("Frontier Airlines" -> "frontier")
_GENERIC_WORDS = {"airlines", "airline", "airways", "air", "aviation", "bank", "credit", "union", "federal",
                  "fcu", "financial", "wireless", "mobile", "insurance", "restaurant", "pizza", "coffee",
                  "burger", "grill", "cafe", "hotels", "lines", "line", "cruise", "market", "markets", "foods",
                  "the", "of", "by", "and", "online", "app", "deli", "steakhouse", "rent", "a", "car", "rental"}


def _named_entries(known_titles):
    """Each company in brand_named.py as its own logo entry, plus the extra names in
    brand_names.py for the everyday icons (e.g. "car payment" -> Car)."""
    from brand_names import MORE_NAMES
    from brand_named import NAMED
    by_base = {e[0]: e for e in EVERYDAY}
    out, covered, slugs = [], set(), set()
    _NAMED.clear()
    for base, text in NAMED.items():
        icon = by_base[base]
        for line in text.strip().splitlines():
            parts = [x.strip() for x in line.split("|")]
            title = parts[0]
            key = _norm(title)
            if not key or key in known_titles or key.replace(" ", "") in known_titles:
                continue   # already has a real logo
            color = parts[1] if len(parts) > 1 and re.fullmatch(r"[0-9A-Fa-f]{6}", parts[1]) else icon[2]
            aliases = [a.strip() for a in parts[2].split(";") if a.strip()] if len(parts) > 2 else []
            short = " ".join(w for w in key.split() if w not in _GENERIC_WORDS)
            if short and short != key and len(short) >= 3:
                aliases.append(short)
            slug = base + "/" + re.sub(r"[^a-z0-9]", "", key)
            if slug in slugs:
                continue
            slugs.add(slug)
            _NAMED[slug] = base
            covered.update(_norm(a) for a in [title] + aliases)
            out.append([slug, title, color, icon[3], aliases])
    for e in EVERYDAY:   # a company with its own entry no longer points at the plain icon
        names = list(dict.fromkeys(e[4] + MORE_NAMES.get(e[0], [])))
        e[4] = [a for a in names if _norm(a) not in covered]
    return out


def is_named(slug) -> bool:
    return slug in _NAMED

# The best-known apps, banks, streaming services, games, stores and
# restaurants, most popular first. This is what the dropdown shows before you
# type ("Top apps & games"), and these are ranked first in search results. (Amazon, Microsoft/Xbox/Outlook, LinkedIn,
# Disney+, Hulu, Minecraft and Nintendo don't allow their logos to be shared,
# so they use an everyday icon or "Use my own picture" instead.)
TOP_50 = ["google", "youtube", "gmail", "apple", "icloud", "instagram", "facebook", "whatsapp",
          "tiktok", "snapchat", "x", "reddit", "discord", "twitch", "netflix", "spotify", "max",
          "paypal", "venmo", "cashapp", "chase", "bankofamerica", "wellsfargo", "americanexpress",
          "coinbase", "uber", "doordash", "airbnb", "ebay", "github", "zoom", "dropbox",
          "pinterest", "telegram", "messenger", "steam", "epicgames", "playstation", "roblox",
          "fortnite", "riotgames", "leagueoflegends", "valorant", "battledotnet", "ea", "ubisoft",
          "activision", "rockstargames", "chessdotcom", "duolingo",
          # added in v2.0.11: food, shopping, streaming, social, money, travel and more
          "mcdonalds", "starbucks", "burgerking", "kfc", "tacobell", "ubereats", "instacart", "postmates",
          "deliveroo", "justeat", "target", "etsy", "shopify", "aliexpress", "nike", "adidas", "ikea", "zara",
          "newbalance", "puma", "wish", "hbomax", "hbo", "crunchyroll", "appletv", "youtubemusic", "applemusic",
          "soundcloud", "pandora", "tidal", "deezer", "audible", "paramountplus", "plex", "vimeo", "threads",
          "bluesky", "tumblr", "quora", "medium", "signal", "wechat", "line", "viber", "bereal", "mastodon",
          "kakaotalk", "visa", "mastercard", "robinhood", "zelle", "discover", "klarna", "afterpay", "wise",
          "revolut", "binance", "stripe", "lyft", "bookingdotcom", "expedia", "delta", "unitedairlines",
          "southwestairlines", "americanairlines", "marriott", "hilton", "notion", "figma", "protonmail",
          "samsung", "wordpress", "claude", "pubg", "counterstrike"]
TOP = TOP_50   # kept under both names

# The logo menu's categories, shown under "Popular" before you type. Each brand
# shows once; any without a logo in this copy are skipped.
CATEGORIES = [
    ("Shopping", ["hk-amazon", "hk-shopping", "ebay", "target", "etsy", "shopify", "aliexpress", "temu", "shein",
                  "ikea", "nike", "adidas", "newbalance", "puma", "underarmour", "zara", "handm", "uniqlo",
                  "macys", "zalando", "stockx", "vinted", "wish", "newegg", "rakuten", "shopee", "taobao",
                  "kaufland", "otto", "groupon", "honey", "dell", "hp", "lenovo", "samsung", "apple"]),
    ("Banks & money", ["hk-bank", "hk-card", "hk-money", "chase", "bankofamerica", "wellsfargo",
                       "americanexpress", "discover", "hsbc", "barclays", "goldmansachs", "deutschebank",
                       "commerzbank", "sparkasse", "revolut", "monzo", "n26", "starlingbank", "bunq", "nubank",
                       "hdfcbank", "icicibank", "paypal", "venmo", "cashapp", "zelle", "applepay", "googlepay",
                       "samsungpay", "visa", "mastercard", "klarna", "afterpay", "wise", "stripe", "robinhood",
                       "coinbase", "binance", "mercadopago", "paytm", "phonepe"]),
    ("Airlines & travel", ["hk-plane", "hk-hotel", "hk-train", "delta", "unitedairlines", "americanairlines",
                           "southwestairlines", "jetblue", "aircanada", "britishairways", "lufthansa", "airfrance",
                           "klm", "emirates", "qatarairways", "etihadairways", "turkishairlines",
                           "singaporeairlines", "qantas", "japanairlines", "ana", "ryanair", "easyjet", "wizzair",
                           "norwegian", "iberia", "aeromexico", "avianca", "copaairlines", "virginatlantic",
                           "airasia", "airindia", "indigo", "airchina", "chinaeasternairlines",
                           "chinasouthernairlines", "airbnb", "bookingdotcom", "expedia", "hotelsdotcom",
                           "tripadvisor", "trivago", "marriott", "hilton", "uber", "lyft", "grab", "waze",
                           "googlemaps", "sncf", "deutschebahn"]),
    ("Food & delivery", ["hk-food", "hk-pizza", "hk-burger", "hk-coffee", "hk-cart", "mcdonalds", "starbucks",
                         "burgerking", "kfc", "tacobell", "doordash", "ubereats", "instacart", "postmates",
                         "deliveroo", "justeat", "glovo", "foodpanda", "zomato", "swiggy", "hellofresh", "yelp",
                         "samsclub", "lidl", "aldinord", "aldisud", "tesco", "iceland"]),
    ("Cars & dealerships", ["hk-car", "toyota", "ford", "chevrolet", "honda", "nissan", "hyundai", "kia",
                            "tesla", "jeep", "ram", "chrysler", "cadillac", "generalmotors", "subaru", "mazda",
                            "volkswagen", "bmw", "audi", "porsche", "volvo", "acura", "infiniti", "mini",
                            "mitsubishi", "suzuki", "fiat", "polestar", "lucid", "peugeot", "renault", "citroen",
                            "opel", "skoda", "seat", "dacia", "ferrari", "lamborghini", "maserati", "bentley",
                            "rollsroyce", "astonmartin", "mclaren", "bugatti", "shell"]),
    ("Streaming & music", ["hk-tv", "hk-music", "netflix", "max", "hbomax", "hbo", "paramountplus", "appletv",
                           "youtube", "youtubetv", "crunchyroll", "tubi", "roku", "starz", "showtime", "mubi",
                           "plex", "dazn", "twitch", "kick", "vimeo", "spotify", "applemusic", "youtubemusic",
                           "tidal", "deezer", "pandora", "soundcloud", "audible", "iheartradio", "shazam",
                           "bandcamp", "audiomack", "napster", "lastdotfm", "applepodcasts", "pocketcasts",
                           "jellyfin", "emby", "kodi"]),
    ("Phone, internet & bills", ["hk-phone", "hk-home", "hk-shield", "verizon", "atandt", "vodafone",
                                 "orange", "spectrum", "boost", "metro", "ring", "vivint", "arlo", "wyze",
                                 "zillow", "starlink"]),
    ("Gaming services", ["hk-controller", "steam", "epicgames", "playstation", "battledotnet", "ea", "origin",
                         "ubisoft", "gogdotcom", "itchdotio", "humblebundle", "riotgames", "rockstargames",
                         "activision", "valve", "roblox", "discord", "nvidia", "amd", "razer", "curseforge",
                         "modrinth", "faceit", "mihoyo", "unity", "unrealengine"]),
    ("Video games", ["hk-sword", "fortnite", "leagueoflegends", "valorant", "counterstrike", "dota2", "pubg",
                     "rust", "fifa", "thefinals", "chessdotcom", "lichess", "osu"]),
]
_TOP_RANK = {slug: i for i, slug in enumerate(TOP_50)}
POPULAR = TOP_50


def _resource(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


def load():
    """Load the logo list once (about 0.2s)."""
    global _icons, _by_slug
    with _lock:
        if _icons is None:
            icons = []
            try:
                # 1st choice: the copy built into the code (always packed into the app)
                import brand_data
                raw = gzip.decompress(base64.b64decode("".join(brand_data.BRAND_ICONS_GZ_B64)
                                                       if isinstance(brand_data.BRAND_ICONS_GZ_B64, (list, tuple))
                                                       else brand_data.BRAND_ICONS_GZ_B64))
                icons = json.loads(raw)["icons"]
            except Exception:
                try:
                    # 2nd choice: the file in assets/ (when running from source)
                    with gzip.open(_resource(os.path.join("assets", "brand_icons.json.gz")), "rt",
                                   encoding="utf-8") as f:
                        icons = json.load(f)["icons"]
                except Exception:
                    # never crash the app over logos: everyday icons still work
                    import traceback
                    traceback.print_exc()
            known = {_norm(i[1]) for i in icons} | {i[0] for i in icons}
            icons = [list(e) for e in EVERYDAY] + _named_entries(known) + icons
            _by_slug = {i[0]: i for i in icons}
            _icons = icons
    return _icons


def sections():
    """What the dropdown shows before you type anything."""
    load()

    def pick(slugs):
        return [(s, _by_slug[s][1]) for s in slugs if s in _by_slug]
    seen = set(TOP_50[:50])
    out = [("Popular", pick(TOP_50[:50]))]
    for title, slugs in CATEGORIES:
        bases = {s for s in slugs if s in _EVERYDAY_SLUGS}
        named = sorted((s for s, b in _NAMED.items() if b in bases), key=lambda s: _by_slug[s][1].lower())
        mine = [s for s in list(dict.fromkeys(slugs + named)) if s not in seen]
        seen.update(mine)
        out.append((title, pick(mine)))
    rest = [s for s in TOP_50 if s not in seen] + [e[0] for e in EVERYDAY if e[0] not in seen]
    out.append(("More apps & icons", pick(rest)))
    return out


# ---- a login's own picture ------------------------------------------------

MAX_PICTURE_BYTES = 15 * 1024 * 1024


def picture_to_icon(path: str) -> str:
    """Turn any image file into a small square icon string to save with a login."""
    if os.path.getsize(path) > MAX_PICTURE_BYTES:
        raise ValueError("That picture is too big (max 15 MB).")
    try:
        with Image.open(path) as im:
            im = im.convert("RGBA")
    except Exception:
        raise ValueError("That file isn't a picture HushKey can read. Try a PNG or JPG.")
    side = min(im.size)
    left, top = (im.width - side) // 2, (im.height - side) // 2
    im = im.crop((left, top, left + side, top + side)).resize((96, 96), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return CUSTOM_PREFIX + base64.b64encode(buf.getvalue()).decode("ascii")


def is_picture(icon: str) -> bool:
    return bool(icon) and icon.startswith(CUSTOM_PREFIX)


def count() -> int:
    return len(load())


def title(slug):
    if is_picture(slug):
        return "Your picture"
    load()
    item = _by_slug.get(slug)
    return item[1] if item else None


def _norm(text):
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


def search(query: str, limit: int = 8):
    """Best matches as [(slug, title)], e.g. 'riot' -> Riot Games first."""
    load()
    q = _norm(query)
    if not q:
        return [(s, _by_slug[s][1]) for s in POPULAR if s in _by_slug][:limit]
    q_tight = q.replace(" ", "")
    scored = []
    for slug, name, _hex, _path, aliases in _icons:
        best = 9
        for i, candidate in enumerate([name] + list(aliases)):
            n = _norm(candidate)
            penalty = 0 if i == 0 else 0.5
            if n == q:
                s = 0
            elif n.startswith(q):
                s = 1
            elif any(w.startswith(q) for w in n.split()):
                s = 2
            elif q in n:
                s = 3
            elif q_tight in slug:
                s = 4
            else:
                continue
            best = min(best, s + penalty)
        if best < 9:
            # big, well-known names first, then HushKey's everyday icons, then the rest
            if slug in _TOP_RANK:
                best -= 0.75
            elif slug in _NAMED:
                best -= 0.3
            elif slug in _EVERYDAY_SLUGS:
                best -= 0.25
            scored.append((best, _TOP_RANK.get(slug, 999), len(name), name.lower(), slug, name))
    scored.sort()
    return [(s[4], s[5]) for s in scored[:limit]]


def suggest(client_name: str):
    """Guess a logo from a client name: 'Riot account 1' -> riotgames."""
    words = _norm(client_name).split()
    if not words or len(words[0]) < 3:
        return None  # too short to guess safely ("my bank" shouldn't match anything)
    first = words[0]
    while words:
        hits = search(" ".join(words), limit=1)
        if hits:
            slug, name = hits[0]
            brand_words = _norm(name).split()
            squashed = _norm(name).replace(" ", "")
            if first in brand_words or squashed == first or (len(first) >= 6 and squashed.startswith(first)):
                return slug
            if slug in _EVERYDAY_SLUGS or slug in _NAMED:   # "Dominos" -> Pizza, "Chipotle" -> Restaurant
                said = " ".join(words)
                for kw in _by_slug[slug][4]:
                    k = _norm(kw)
                    if k == said or k.replace(" ", "") == said.replace(" ", ""):
                        return slug
        words = words[:-1]
    return None


# --------------------------------------------------------------------------
# Drawing an SVG path (the "M13.458.86 0 7.093l3.353..." text) with Pillow
# --------------------------------------------------------------------------

_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


class _Reader:
    def __init__(self, d):
        self.d, self.i = d, 0

    def _skip(self):
        while self.i < len(self.d) and self.d[self.i] in " ,\t\r\n":
            self.i += 1

    def has_number(self):
        self._skip()
        return self.i < len(self.d) and (self.d[self.i].isdigit() or self.d[self.i] in "+-.")

    def number(self):
        self._skip()
        m = _NUM.match(self.d, self.i)
        if not m:
            raise ValueError("bad number at %d" % self.i)
        self.i = m.end()
        return float(m.group())

    def flag(self):  # arc flags may be written squashed together, like "01"
        self._skip()
        ch = self.d[self.i]
        self.i += 1
        return ch == "1"

    def command(self):
        self._skip()
        if self.i >= len(self.d):
            return None
        ch = self.d[self.i]
        if ch.isalpha():
            self.i += 1
            return ch
        return ""  # implicit repeat of the previous command


def _cubic(p0, p1, p2, p3, steps=10):
    pts = []
    for k in range(1, steps + 1):
        t = k / steps
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


def _quad(p0, p1, p2, steps=8):
    pts = []
    for k in range(1, steps + 1):
        t = k / steps
        u = 1 - t
        pts.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return pts


def _arc(p0, rx, ry, phi_deg, large, sweep, p1, steps=12):
    """SVG elliptical arc -> points (math from the SVG spec, appendix F.6)."""
    x1, y1 = p0
    x2, y2 = p1
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [p1]
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(phi_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = x1p * x1p / (rx * rx) + y1p * y1p / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        coef = -coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def angle(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    th1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dth = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dth > 0:
        dth -= 2 * math.pi
    elif sweep and dth < 0:
        dth += 2 * math.pi
    n = max(2, int(abs(dth) / (math.pi / 2) * steps / 2) + 2)
    pts = []
    for k in range(1, n + 1):
        a = th1 + dth * k / n
        pts.append((cx + rx * math.cos(a) * cp - ry * math.sin(a) * sp,
                    cy + rx * math.cos(a) * sp + ry * math.sin(a) * cp))
    return pts


def path_to_polygons(d: str):
    """Turn SVG path text into a list of closed point lists."""
    r = _Reader(d)
    polys, cur = [], []
    x = y = sx = sy = 0.0
    last_ctrl = None
    prev = None
    while True:
        cmd = r.command()
        if cmd is None:
            break
        if cmd == "":
            if prev is None:
                raise ValueError("path must start with a command")
            cmd = {"M": "L", "m": "l"}.get(prev, prev)
        rel = cmd.islower()
        c = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if c == "Z":
            if cur:
                polys.append(cur)
            cur = []
            x, y = sx, sy
            last_ctrl = None
            prev = cmd
            continue
        if c == "M":
            if cur:
                polys.append(cur)
            x, y = r.number() + ox, r.number() + oy
            sx, sy = x, y
            cur = [(x, y)]
            last_ctrl = None
        elif c == "L":
            x, y = r.number() + ox, r.number() + oy
            cur.append((x, y))
            last_ctrl = None
        elif c == "H":
            x = r.number() + ox
            cur.append((x, y))
            last_ctrl = None
        elif c == "V":
            y = r.number() + (y if rel else 0.0)
            cur.append((x, y))
            last_ctrl = None
        elif c == "C":
            p1 = (r.number() + ox, r.number() + oy)
            p2 = (r.number() + ox, r.number() + oy)
            p3 = (r.number() + ox, r.number() + oy)
            cur += _cubic((x, y), p1, p2, p3)
            last_ctrl, (x, y) = ("C", p2), p3
        elif c == "S":
            p1 = (2 * x - last_ctrl[1][0], 2 * y - last_ctrl[1][1]) if last_ctrl and last_ctrl[0] == "C" else (x, y)
            p2 = (r.number() + ox, r.number() + oy)
            p3 = (r.number() + ox, r.number() + oy)
            cur += _cubic((x, y), p1, p2, p3)
            last_ctrl, (x, y) = ("C", p2), p3
        elif c == "Q":
            p1 = (r.number() + ox, r.number() + oy)
            p2 = (r.number() + ox, r.number() + oy)
            cur += _quad((x, y), p1, p2)
            last_ctrl, (x, y) = ("Q", p1), p2
        elif c == "T":
            p1 = (2 * x - last_ctrl[1][0], 2 * y - last_ctrl[1][1]) if last_ctrl and last_ctrl[0] == "Q" else (x, y)
            p2 = (r.number() + ox, r.number() + oy)
            cur += _quad((x, y), p1, p2)
            last_ctrl, (x, y) = ("Q", p1), p2
        elif c == "A":
            rx, ry, rot = r.number(), r.number(), r.number()
            large, sweep = r.flag(), r.flag()
            p = (r.number() + ox, r.number() + oy)
            cur += _arc((x, y), rx, ry, rot, large, sweep, p)
            (x, y), last_ctrl = p, None
        else:
            raise ValueError("unknown command " + cmd)
        prev = cmd
    if cur:
        polys.append(cur)
    return [p for p in polys if len(p) >= 3]


def _fill_nonzero(polys, size, scale, evenodd=False):
    """Fill shapes using the SVG 'nonzero' rule (or 'evenodd'), so holes work."""
    rows = [[] for _ in range(size)]
    for poly in polys:
        n = len(poly)
        for k in range(n):
            x0, y0 = poly[k]
            x1, y1 = poly[(k + 1) % n]
            x0, y0, x1, y1 = x0 * scale, y0 * scale, x1 * scale, y1 * scale
            if y0 == y1:
                continue
            direction = 1 if y1 > y0 else -1
            ylo, yhi = min(y0, y1), max(y0, y1)
            start = max(0, int(math.ceil(ylo - 0.5)))
            end = min(size - 1, int(math.ceil(yhi - 0.5)) - 1)
            inv = (x1 - x0) / (y1 - y0)
            for row in range(start, end + 1):
                yc = row + 0.5
                rows[row].append((x0 + (yc - y0) * inv, direction))
    buf = bytearray(size * size)
    for row, hits in enumerate(rows):
        if not hits:
            continue
        hits.sort()
        wind = 0
        for idx in range(len(hits) - 1):
            wind += 1 if evenodd else hits[idx][1]
            if (wind % 2 != 0) if evenodd else (wind != 0):
                a = max(0, min(size, int(round(hits[idx][0]))))
                b = max(0, min(size, int(round(hits[idx + 1][0]))))
                if b > a:
                    buf[row * size + a: row * size + b] = b"\xff" * (b - a)
    return Image.frombytes("L", (size, size), bytes(buf))


LIGHT_BACKGROUND = (255, 255, 255)  # HushKey card color in light mode


def _readable_color(hex_color, light=False):
    """Brand color, unless it would vanish on HushKey's cards: too dark in
    dark mode (drawn light instead) or too pale in light mode (drawn dark)."""
    rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    bg = LIGHT_BACKGROUND if light else BACKGROUND

    def lum(c):
        ch = [v / 255 for v in c]
        ch = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

    contrast = (max(lum(rgb), lum(bg)) + 0.05) / (min(lum(rgb), lum(bg)) + 0.05)
    if contrast >= 2.4:
        return rgb
    return (27, 31, 36) if light else (238, 241, 246)


def render(slug: str, size: int = 64, light: bool = False):
    """See-through PNG of a brand logo in its own color, or None if unknown.
    light=True makes sure it shows up on light mode's white cards."""
    key = (slug, size, light)
    if key in _cache:
        return _cache[key]
    if is_picture(slug):
        try:
            img = Image.open(io.BytesIO(base64.b64decode(slug[len(CUSTOM_PREFIX):]))).convert("RGBA")
        except Exception:
            return None
        img = img.resize((size, size), Image.LANCZOS)
        _cache[key] = img
        return img
    load()
    item = _by_slug.get(slug)
    if not item:
        return None
    ss = 4  # draw 4x bigger, then shrink, for smooth edges
    big = size * ss
    base = _NAMED.get(slug, slug)
    mask = _fill_nonzero(path_to_polygons(item[3]), big, big / 24.0,
                         evenodd=base in _EVERYDAY_SLUGS and base not in NONZERO)
    mask = mask.resize((size, size), Image.BOX)
    img = Image.new("RGBA", (size, size), _readable_color(item[2], light) + (0,))
    img.putalpha(mask)
    _cache[key] = img
    return img
