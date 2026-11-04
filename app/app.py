"""
app.py - HushKey's windows and screens (CustomTkinter, works on Windows and Mac).

All security logic lives in vault.py (encryption, hashing, files) and
cloud.py (email codes). This file only draws screens and calls them.

Run from source:   python app/app.py
Screen check:      python app/app.py --selftest   (opens every screen, then closes)
"""

import os
import queue
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

import brand_icons
import device_lock
import updater as updater_mod
from sync import Syncer, VaultMismatch
import importer
import leakcheck
from brand import draw_logo
from cloud import Cloud, CloudError, SessionExpired
from vault import (MIN_MASTER_LENGTH, REMEMBER_DAYS, TamperError, Vault, VaultError,
                   WrongPassword, check_new_master, generate_password, health_score, health_word,
                   looks_like_email, new_recovery_secret, new_vault_id,
                   normalize_email, password_strength)
from version import __version__

APP_NAME = "HushKey"
DEFAULT_LOCK_SECONDS = 5 * 60   # lock after 5 minutes with no activity (changeable in Settings)
LOCK_CHOICES = [(60, "1 min"), (300, "5 min"), (600, "10 min"), (900, "15 min"), (1800, "30 min"),
                (3600, "1 hour"), (10800, "3 hours"), (0, "Never")]
TIP_SNOOZE_DAYS = 30            # "Not now" hides a suggestion this long
CLIPBOARD_CLEAR_SECONDS = 20    # wipe copied passwords after 20s
REVEAL_SECONDS = 30             # a clicked login hides itself again after 30s

IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"
MONO = "Menlo" if IS_MAC else ("Consolas" if IS_WIN else "DejaVu Sans Mono")

# ---- colors: (light mode, dark mode). Green = safe, gold = key. ----
# CustomTkinter switches between the two automatically when the theme changes.
BG = ("#F7F4EC", "#0E1116")            # off-white / near-black
SURFACE = ("#FFFFFF", "#161A22")
RAISED = ("#EFEADF", "#1D222C")
BORDER = ("#DCD4C2", "#2A303C")
TEXT = ("#1B1F24", "#EEF1F6")
LABEL = ("#3A4250", "#C9CFDA")
MUTED = ("#5B6472", "#A2AAB8")
SUBTLE = ("#6B7280", "#8C95A5")
ACCENT = ("#16925A", "#3DDC97")        # deeper green on light so it stays readable
ACCENT_HOVER = ("#12784A", "#5BE6AA")
ACCENT_INK = ("#FFFFFF", "#08281A")    # text on green buttons
ACCENT_DISABLED_INK = ("#D5F0E2", "#2F5E48")
ACCENT_SOFT = ("#E2F5EA", "#14231D")
ACCENT_SOFT_HOVER = ("#D0EEDD", "#1A3328")
GOLD = ("#B07D12", "#F2C14E")          # deeper gold on light
GOLD_HOVER = ("#946A0F", "#F7D27E")
GOLD_SOFT = ("#FBF1D6", "#2A2414")
GOLD_INK = ("#FFFFFF", "#2A2414")
DANGER = ("#C62828", "#FF8080")
DANGER_SOFT = ("#FDECEC", "#2A1618")
DANGER_BORDER = ("#EBB4B4", "#5A2A2E")
SIGNOUT = ("#D64545", "#E5484D")       # the red Sign out button
SIGNOUT_HOVER = ("#B83333", "#C93A3F")
WARN = ("#C2410C", "#FF8A3D")          # orange: "Change master password"
WARN_HOVER = ("#9A3412", "#FF9F5E")
BRAND_GREEN = ("#16925A", "#3DDC97")   # the logo and wordmark never change color
SIDE = ("#FBF9F3", "#12161D")          # sidebars
TRACK = ("#E9E2D2", "#2A303C")
TIP_BG = ("#FBF8F1", "#141820")
TOAST_BG = ("#1B1F24", "#EEF1F6")
TOAST_FG = ("#F7F4EC", "#0E1116")
TOAST_LINK = ("#7BEBB9", "#137F4E")
DOTS = "•" * 10

# Password strength: 0-1 weak (red), 2 okay (yellow), 3 strong, 4 very strong.
# These never follow the accent color, so a weak password always looks like a warning.
STRENGTH_COLORS = [("#C62828", "#FF6B6B"), ("#C62828", "#FF6B6B"), ("#A16207", "#FACC15"),
                   ("#4D7C0F", "#9BE15D"), ("#137F4E", "#3DDC97")]
STRENGTH_LABELS = ["Very weak", "Weak", "Okay", "Strong", "Very strong"]

# Accent colors (Settings > Appearance): key, name, dark mode, light mode
ACCENTS = [
    ("green", "Green", "#3DDC97", "#137F4E"), ("mint", "Mint", "#86EFAC", "#15803D"),
    ("lime", "Lime", "#A3E635", "#4D7C0F"), ("teal", "Teal", "#2DD4BF", "#0F766E"),
    ("cyan", "Cyan", "#22D3EE", "#0E7490"), ("sky", "Sky", "#7DD3FC", "#0369A1"),
    ("blue", "Blue", "#5AB4FF", "#1D4ED8"), ("indigo", "Indigo", "#8C9EFF", "#4F46E5"),
    ("violet", "Violet", "#B18CFF", "#6E46C8"), ("purple", "Purple", "#D88CFF", "#9333EA"),
    ("pink", "Pink", "#F9A8D4", "#BE185D"), ("rose", "Rose", "#FF7AA2", "#B8325F"),
    ("red", "Red", "#FF6B6B", "#B91C1C"), ("coral", "Coral", "#FF8A65", "#C2410C"),
    ("orange", "Orange", "#FFA64D", "#B45309"), ("yellow", "Yellow", "#FDE047", "#854D0E"),
    ("gold", "Gold", "#F2C14E", "#8F6510"), ("brown", "Brown", "#D4A373", "#7C4A1E"),
    ("slate", "Slate", "#94A3B8", "#475569"), ("silver", "Silver", "#CBD5E1", "#334155"),
    ("mono", "Mono", "#F3F4F6", "#111827"),
]


def _mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def apply_accent(key):
    """Switch buttons and highlights to another color. Screens drawn after
    this use the new color (the open screen is redrawn right away)."""
    global ACCENT, ACCENT_HOVER, ACCENT_INK, ACCENT_DISABLED_INK, ACCENT_SOFT, ACCENT_SOFT_HOVER
    _k, _n, dark, light = next((a for a in ACCENTS if a[0] == key), ACCENTS[0])
    ACCENT = (light, dark)
    ACCENT_HOVER = (_mix(light, "#000000", 0.15), _mix(dark, "#FFFFFF", 0.18))
    ACCENT_INK = ("#FFFFFF", "#0B1116")
    ACCENT_DISABLED_INK = (_mix(light, "#FFFFFF", 0.7), _mix(dark, "#0E1116", 0.55))
    ACCENT_SOFT = (_mix("#F7F4EC", light, 0.12), _mix("#0E1116", dark, 0.12))
    ACCENT_SOFT_HOVER = (_mix("#F7F4EC", light, 0.2), _mix("#0E1116", dark, 0.2))


def _light_color(hexcolor):
    r, g, b = (int(hexcolor.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b > 186


_toggle_cache = {}


def toggle_image(on):
    """An on/off switch drawn the same on every computer: on = your accent color with the
    knob on the right, off = grey with the knob on the left. The knob always contrasts."""
    key = (on, ACCENT, STYLE)
    if key not in _toggle_cache:
        from PIL import Image, ImageDraw
        knobs, tracks = switch_colors()

        def draw(i):
            w, h, k = 46, 26, 4
            img = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            track = ACCENT[i] if on else tracks[i]
            r = h * k // 2 if STYLE == "basic" else 3 * k
            d.rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=r, fill=track)
            pad = 3 * k
            size = h * k - 2 * pad
            x = (w * k - pad - size) if on else pad
            knob = knobs[i] if on else "#FFFFFF"
            if STYLE == "basic":
                d.ellipse([x, pad, x + size, pad + size], fill=knob)
            else:
                d.rectangle([x, pad, x + size, pad + size], fill=knob)
            return img.resize((w * 2, h * 2), Image.LANCZOS)
        _toggle_cache[key] = ctk.CTkImage(light_image=draw(0), dark_image=draw(1), size=(46, 26))
    return _toggle_cache[key]


def switch_colors():
    """(knob, off-track) colors that always stand out from the on-track (your accent color),
    from the off-track, and from the card behind the switch, in both themes."""
    knobs, tracks = [], []
    for accent, off in ((ACCENT[0], "#B5AD9B"), (ACCENT[1], "#4A5262")):
        knob = "#1B1F24" if _light_color(accent) else "#FFFFFF"
        knobs.append(knob)
        tracks.append(off if knob == "#FFFFFF" else "#D9DEE7")
    return tuple(knobs), tuple(tracks)


def health_color(score, dark=True):
    i = 1 if dark else 0
    if score >= 90:
        return STRENGTH_COLORS[4][i]
    if score >= 70:
        return STRENGTH_COLORS[3][i]
    if score >= 50:
        return STRENGTH_COLORS[2][i]
    return STRENGTH_COLORS[1][i]


def ago_seconds(when: float) -> str:
    secs = max(0, time.time() - when)
    for size, word in ((31536000, "year"), (2592000, "month"), (604800, "week"), (86400, "day"),
                       (3600, "hour"), (60, "minute")):
        if secs >= size:
            n = int(secs // size)
            return f"{n} {word}{'s' if n != 1 else ''} ago"
    return "just now"


def ago(iso: str) -> str:
    """'2026-03-01T10:00:00+00:00' -> '8 months ago'."""
    from datetime import datetime
    try:
        return ago_seconds(datetime.fromisoformat(iso).timestamp())
    except (TypeError, ValueError):
        return "a while ago"

# ---- fonts: Poppins (bundled, free OFL license) ----
FAMILY = None


def resource(rel):
    # packed app: files sit next to the program; from source: the project folder above app/
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


def _register_font_file(path):
    """Make a bundled font usable by this app only (nothing is installed)."""
    if IS_WIN:
        return ctk.FontManager.windows_load_font(path, private=True, enumerable=True)
    if IS_MAC:
        import ctypes
        import ctypes.util
        cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
        ct = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreText"))
        cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        cf.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                                               ctypes.c_long, ctypes.c_bool]
        ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
        ct.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
        raw = path.encode("utf-8")
        url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
        return bool(ct.CTFontManagerRegisterFontsForURL(url, 1, None))  # 1 = this app only
    return ctk.FontManager.load_font(path)


def _font_file(name):
    """Path to a font file. The fonts are built into the code (brand_data.py)
    so they're always packed into the app; they're written once to a cache
    folder because Windows and macOS need a real file to load a font from."""
    import base64
    try:
        import brand_data
        data = base64.b64decode("".join(brand_data.FONTS_B64[name]))
        folder = os.path.join(tempfile.gettempdir(), "HushKey-fonts")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name)
        if not os.path.isfile(path) or os.path.getsize(path) != len(data):
            with open(path, "wb") as f:
                f.write(data)
        return path
    except Exception:
        return resource(os.path.join("assets", "fonts", name))


# Fonts you can pick in Settings > Appearance (all free, OFL license, bundled)
FONT_CHOICES = [("poppins", "Poppins", "Poppins"), ("dmsans", "DM Sans", "DMSans"),
                ("nunito", "Nunito", "Nunito"), ("pixel", "Pixelify Sans", "PixelifySans")]
FONT_LABELS = {"poppins": "Poppins", "dmsans": "DM Sans", "nunito": "Nunito", "pixel": "Pixel"}
_AVAILABLE = set()


def load_fonts(root, choice="poppins"):
    """Load the bundled fonts once the window exists, then use the chosen one
    (Poppins unless you pick another in Settings)."""
    global _AVAILABLE
    try:
        import tkinter.font as tkfont
    except ImportError:
        return
    for _key, _family, stem in FONT_CHOICES:
        for name in (stem + "-Regular.ttf", stem + "-Bold.ttf"):
            try:
                _register_font_file(_font_file(name))
            except Exception:
                traceback.print_exc()
    try:
        _AVAILABLE = set(tkfont.families(root))
    except Exception:
        _AVAILABLE = set()
    set_font(choice)


def set_font(choice):
    """Use one of FONT_CHOICES; falls back to a good built-in font if it didn't load."""
    global FAMILY
    wanted = next((f for k, f, _s in FONT_CHOICES if k == choice), "Poppins")
    for candidate in (wanted, "Poppins", "Avenir Next" if IS_MAC else "Segoe UI", "Helvetica"):
        if candidate in _AVAILABLE:
            FAMILY = candidate
            return
    FAMILY = None


# ---- style: "basic" (rounded) or "pixel" (square corners) ----
STYLE = "basic"


def _radius(r):
    """Corner roundness for the current style."""
    if STYLE == "pixel" and r:
        return min(r, 2)
    return r


def _install_style():
    """Make every box and button follow the style, without touching each one by hand."""
    for cls in (ctk.CTkFrame, ctk.CTkButton, ctk.CTkEntry, ctk.CTkLabel, ctk.CTkSegmentedButton,
                ctk.CTkScrollableFrame, ctk.CTkProgressBar, ctk.CTkSwitch, ctk.CTkTextbox, ctk.CTkCheckBox,
                ctk.CTkOptionMenu, ctk.CTkScrollbar):
        if getattr(cls.__init__, "_hk_style", False):
            continue
        orig = cls.__init__

        def init(self, *args, _orig=orig, cls=cls, **kw):
            if STYLE == "pixel":
                kw["corner_radius"] = _radius(kw.get("corner_radius") or 6)
                if cls is ctk.CTkSwitch:
                    kw["button_corner_radius"] = 2
            _orig(self, *args, **kw)
        init._hk_style = True
        cls.__init__ = init


_install_style()


# ---- scrolling: faster, and it glides instead of jumping ----
WHEEL_STEP = 110     # pixels per mouse-wheel notch


def smooth_scroll(canvas, pixels):
    """Scroll a canvas by some pixels, easing toward the spot over a few frames."""
    try:
        region = canvas.cget("scrollregion").split()
        total = float(region[3]) - float(region[1]) if len(region) == 4 else 0
        view = canvas.winfo_height()
    except Exception:
        return
    if total <= view:
        return
    top = getattr(canvas, "_hk_target", None)
    if top is None or not getattr(canvas, "_hk_moving", False):
        top = canvas.yview()[0] * total
    top = max(0.0, min(total - view, top + pixels))
    canvas._hk_target = top
    if getattr(canvas, "_hk_moving", False):
        return

    def step():
        try:
            now = canvas.yview()[0] * total
        except Exception:
            return
        gap = canvas._hk_target - now
        if abs(gap) < 1:
            canvas.yview_moveto(canvas._hk_target / total)
            canvas._hk_moving = False
            return
        canvas.yview_moveto((now + gap * 0.35) / total)
        canvas.after(10, step)
    canvas._hk_moving = True
    step()


def wheel_pixels(event):
    """How far one wheel event should scroll, on Windows, Mac and Linux."""
    if getattr(event, "num", None) == 4:
        return -WHEEL_STEP
    if getattr(event, "num", None) == 5:
        return WHEEL_STEP
    delta = getattr(event, "delta", 0) or 0
    if IS_MAC:
        return -delta * 12          # trackpads send many small steps
    return -delta / 120 * WHEEL_STEP


def _smooth_wheel(self, event):
    check = getattr(self, "_check_if_valid_scroll", None)
    if (check is not None and not check(event.widget)) or getattr(self, "_shift_pressed", False):
        return
    if self._parent_canvas.yview() != (0.0, 1.0):
        px = wheel_pixels(event)
        if px:
            smooth_scroll(self._parent_canvas, px)


ctk.CTkScrollableFrame._mouse_wheel_all = _smooth_wheel


def font(size=14, weight="normal", mono=False):
    if mono:
        return ctk.CTkFont(family=MONO, size=size, weight=weight)
    if FAMILY:
        return ctk.CTkFont(family=FAMILY, size=size, weight=weight)
    return ctk.CTkFont(size=size, weight=weight)


# ---- settings (theme, last version seen); nothing secret goes here ----

def _settings_path(data_dir=None):
    from vault import default_data_dir
    return os.path.join(data_dir or default_data_dir(), "settings.json")


def load_settings(data_dir=None) -> dict:
    import json
    try:
        with open(_settings_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict, data_dir=None) -> None:
    import json
    path = _settings_path(data_dir)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        traceback.print_exc()


# ==========================================================================
# Logo + wordmark
# ==========================================================================

_logo_cache = {}


def logo_image(size, tile=False):
    """The HushKey logo, drawn in code (see brand.py) so it can't go missing.
    Light mode gets deeper green/gold so it stands out on off-white."""
    key = (size, tile)
    if key not in _logo_cache:
        dark = draw_logo(size * 2, tile=tile)  # 2x for sharp edges on high-res screens
        light = draw_logo(size * 2, tile=tile, light=True)
        _logo_cache[key] = ctk.CTkImage(light_image=light, dark_image=dark, size=(size, size))
    return _logo_cache[key]


def wordmark(parent, size=26):
    """'HushKey' with Hush in green and Key in gold."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(row, text="Hush", font=font(size, "bold"), text_color=BRAND_GREEN, padx=0).pack(side="left")
    ctk.CTkLabel(row, text="Key", font=font(size, "bold"), text_color=GOLD, padx=0).pack(side="left")
    return row


_icon_files = {}


def set_window_icon(win):
    """Put the HushKey logo in the title bar / taskbar (Windows) and dock (Mac)."""
    try:
        from PIL import ImageTk
        if IS_WIN:
            if "ico" not in _icon_files:
                path = os.path.join(tempfile.gettempdir(), f"hushkey-{__version__}.ico")
                draw_logo(256).save(path, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
                _icon_files["ico"] = path
            win.iconbitmap(_icon_files["ico"])
        photo = ImageTk.PhotoImage(draw_logo(128))
        win.iconphoto(True, photo)
        win._hushkey_icon = photo  # keep a reference so Tk doesn't drop it
    except Exception:
        traceback.print_exc()


_brand_cache = {}


def brand_image(slug, size):
    """An app logo for both themes (dark logos turn light in dark mode and
    light logos turn dark in light mode, so they never disappear).
    Cached, so 200 Riot logins share one image instead of making 200."""
    if not slug:
        return None
    key = (slug, size)
    if key not in _brand_cache:
        dark = brand_icons.render(slug, size * 2)
        if dark is None:
            return None
        light = brand_icons.render(slug, size * 2, light=True)
        if len(_brand_cache) > 600:
            _brand_cache.clear()
        _brand_cache[key] = ctk.CTkImage(light_image=light, dark_image=dark, size=(size, size))
    return _brand_cache[key]


_star_cache = {}


def star_image(filled: bool, size=18):
    """A gold star (favorite) or an outlined one, drawn so it looks the same
    on every computer (some fonts don't have a star character)."""
    key = (filled, size)
    if key not in _star_cache:
        import math
        from PIL import Image, ImageDraw

        def draw(dark):
            s = size * 8
            img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            pts = []
            for i in range(10):
                r = s * (0.48 if i % 2 == 0 else 0.2)
                a = math.radians(-90 + i * 36)
                pts.append((s / 2 + r * math.cos(a), s * 0.53 + r * math.sin(a)))
            gold = (242, 193, 78, 255) if dark else (176, 125, 18, 255)
            grey = (140, 149, 165, 255) if dark else (107, 114, 128, 255)
            if filled:
                d.polygon(pts, fill=gold)
            else:
                d.line(pts + [pts[0]], fill=grey, width=int(s * 0.07), joint="curve")
            return img.resize((size * 2, size * 2), Image.LANCZOS)
        _star_cache[key] = ctk.CTkImage(light_image=draw(False), dark_image=draw(True), size=(size, size))
    return _star_cache[key]


# ---- the theme switch: a key that slides between night and day ----

_switch_cache = {}


def key_switch_image():
    """One image for the theme switch; CustomTkinter shows the day picture in
    light mode and the night picture in dark mode by itself."""
    if "img" not in _switch_cache:
        _switch_cache["img"] = ctk.CTkImage(light_image=_draw_switch(False),
                                            dark_image=_draw_switch(True), size=(76, 38))
    return _switch_cache["img"]


def _draw_switch(dark: bool):
    """A pill-shaped switch whose knob is a green circle with a key in it.
    Night: key slid right, moon and stars on a dark track.
    Day:   key slid left, sun on an off-white track."""
    from PIL import Image, ImageDraw
    s = 4
    w, h = 76 * s, 38 * s
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    track = (29, 34, 44, 255) if dark else (237, 231, 214, 255)
    edge = (42, 48, 60, 255) if dark else (210, 199, 174, 255)
    gold = (242, 193, 78, 255) if dark else (176, 125, 18, 255)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=track, outline=edge, width=2 * s)
    if dark:  # moon + stars on the left
        cx, cy = 20 * s, 19 * s
        d.ellipse([cx - 8 * s, cy - 8 * s, cx + 8 * s, cy + 8 * s], fill=gold)
        d.ellipse([cx - 4 * s, cy - 11 * s, cx + 10 * s, cy + 3 * s], fill=track)
        for sx, sy in ((31, 11), (35, 24)):
            d.ellipse([(sx - 1.3) * s, (sy - 1.3) * s, (sx + 1.3) * s, (sy + 1.3) * s], fill=gold)
        kx = w - h // 2
    else:     # sun on the right
        cx, cy = 56 * s, 19 * s
        d.ellipse([cx - 5 * s, cy - 5 * s, cx + 5 * s, cy + 5 * s], fill=gold)
        import math
        for k in range(8):
            a = k * math.pi / 4
            d.line([cx + 7.5 * s * math.cos(a), cy + 7.5 * s * math.sin(a),
                    cx + 10 * s * math.cos(a), cy + 10 * s * math.sin(a)], fill=gold, width=2 * s)
        kx = h // 2
    # knob with a key inside
    r = 15 * s
    knob = (61, 220, 151, 255) if dark else (22, 146, 90, 255)
    d.ellipse([kx - r, h // 2 - r, kx + r, h // 2 + r], fill=knob)
    key = brand_icons.render("hk-key", 22 * s)
    if key is not None:
        ink = Image.new("RGBA", key.size, (8, 40, 26, 255) if dark else (255, 255, 255, 255))
        ink.putalpha(key.getchannel("A"))
        img.alpha_composite(ink, (int(kx - key.width / 2), int(h / 2 - key.height / 2)))
    return img.resize((76 * 2, 38 * 2), Image.LANCZOS)


# ==========================================================================
# Reusable pieces
# ==========================================================================

def primary_button(parent, text, command, **kw):
    kw.setdefault("height", 46)
    return ctk.CTkButton(parent, text=text, command=command, corner_radius=10,
                         fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_INK,
                         text_color_disabled=ACCENT_DISABLED_INK, font=font(15, "bold"), **kw)


def ghost_button(parent, text, command, **kw):
    kw.setdefault("height", 46)
    return ctk.CTkButton(parent, text=text, command=command, corner_radius=10,
                         fg_color="transparent", hover_color=RAISED, border_width=1,
                         border_color=BORDER, text_color=TEXT, font=font(14), **kw)


def link_button(parent, text, command, size=13, color=None):
    return ctk.CTkButton(parent, text=text, command=command, fg_color="transparent",
                         hover=False, text_color=color or ACCENT, width=0, height=24,
                         font=font(size, "bold"))


FIELD_WIDTH = 376


def entry(parent, placeholder="", show=None, mono=False, **kw):
    kw.setdefault("width", FIELD_WIDTH)
    e = ctk.CTkEntry(parent, placeholder_text=placeholder, height=46, corner_radius=10,
                     fg_color=BG, border_color=BORDER, border_width=1, text_color=TEXT,
                     placeholder_text_color=SUBTLE, font=font(15, mono=mono), **kw)
    if show:
        e.configure(show=show)
    return e


def field_label(parent, text):
    return ctk.CTkLabel(parent, text=text, font=font(13, "bold"), text_color=LABEL, anchor="w")


def checkbox(parent, text, checked=True, var=None):
    var = var if var is not None else ctk.BooleanVar(value=checked)
    box = ctk.CTkCheckBox(parent, text=text, variable=var, onvalue=True, offvalue=False,
                          font=font(13), text_color=LABEL, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                          border_color=BORDER, checkmark_color=ACCENT_INK, corner_radius=6)
    return box, var


class PasswordField(ctk.CTkFrame):
    """A password box with an optional Show/Hide button."""

    def __init__(self, parent, placeholder="", visible=False, toggle=True, width=FIELD_WIDTH):
        super().__init__(parent, fg_color="transparent")
        self.visible = visible
        self.entry = entry(self, placeholder, show=None if visible else "•", mono=visible,
                           width=width - 72 if toggle else width)
        self.entry.pack(side="left", fill="x", expand=True)
        self.toggle = None
        if toggle:
            self.toggle = ctk.CTkButton(self, text="Hide" if visible else "Show", width=64, height=46,
                                        corner_radius=10, fg_color=RAISED, hover_color=BORDER,
                                        text_color=MUTED, font=font(13), command=self.flip)
            self.toggle.pack(side="left", padx=(8, 0))

    def flip(self):
        self.set_visible(not self.visible)

    def set_visible(self, visible: bool):
        self.visible = visible
        self.entry.configure(show="" if visible else "•", font=font(15, mono=visible))
        if self.toggle:
            self.toggle.configure(text="Hide" if visible else "Show")

    def get(self):
        return self.entry.get()

    def set(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def focus(self):
        self.entry.focus_set()

    def bind_key(self, func):
        self.entry.bind("<KeyRelease>", func, add="+")

    def bind_enter(self, func):
        self.entry.bind("<Return>", func, add="+")


class StrengthBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.bar = ctk.CTkProgressBar(self, height=6, corner_radius=3, fg_color=TRACK, progress_color=ACCENT)
        self.bar.pack(side="left", fill="x", expand=True)
        self.label = ctk.CTkLabel(self, text="", width=110, anchor="e", font=font(12), text_color=MUTED)
        self.label.pack(side="left", padx=(10, 0))
        self.update_for("")

    def update_for(self, pw: str):
        score, label = password_strength(pw)
        self.bar.set(score / 4)
        self.bar.configure(progress_color=STRENGTH_COLORS[score])
        self.label.configure(text=label if pw else "", text_color=STRENGTH_COLORS[score] if pw else MUTED)


class LogoPicker(ctk.CTkFrame):
    """'Choose a logo for this login'. Type to search, or click the arrow to
    browse the top apps & games and HushKey's everyday icons.

    The list FLOATS on top of the form, like a dropdown on a website, so the
    pop-up window never has to grow (CustomTkinter pop-ups can't always grow,
    which is why an earlier version showed nothing)."""

    MAX_RESULTS = 12
    LIST_HEIGHT = 270

    def __init__(self, parent, slug=""):
        super().__init__(parent, fg_color="transparent")
        self.slug = slug or ""
        self.picked_by_hand = bool(slug)
        self.open = False
        self.results = None
        self._shown_query = None

        field_label(self, "Choose a logo for this login (optional)").pack(fill="x")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(6, 0))
        self.row = row
        self.preview = ctk.CTkLabel(row, text="", width=46, height=46, corner_radius=10, fg_color=RAISED,
                                    text_color=SUBTLE, font=font(18, "bold"))
        self.preview.pack(side="left")
        self.search = ctk.CTkEntry(row, placeholder_text="Search logos, e.g. riot",
                                   width=FIELD_WIDTH - 46 - 56 - 16, height=46, corner_radius=10,
                                   fg_color=BG, border_color=BORDER, text_color=TEXT,
                                   placeholder_text_color=SUBTLE, font=font(14))
        self.search.pack(side="left", fill="x", expand=True, padx=8)
        self.arrow = ctk.CTkButton(row, text="▾", width=46, height=46, corner_radius=10, fg_color=RAISED,
                                   hover_color=BORDER, text_color=TEXT, font=font(18), command=self.toggle)
        self.arrow.pack(side="left")
        self.search.bind("<KeyRelease>", self._typed, add="+")
        self.search.bind("<Return>", self._pick_top, add="+")
        self.preview.bind("<Button-1>", lambda _e: self.toggle())

        under = ctk.CTkFrame(self, fg_color="transparent")
        under.pack(fill="x", pady=(2, 0))
        self.note = ctk.CTkLabel(under, text="", font=font(12), text_color=SUBTLE, anchor="w",
                                 justify="left", wraplength=300)
        self.note.pack(side="left", fill="x", expand=True)
        link_button(under, "Use my own picture…", self.pick_picture, size=12).pack(side="right")

        # close the list when clicking anywhere else in the window
        self.after(50, lambda: self.winfo_toplevel().bind("<Button-1>", self._click_anywhere, add="+"))
        self._refresh_preview()
        if self.slug:
            self.search.insert(0, brand_icons.title(self.slug) or "")

    # ---- preview -------------------------------------------------------------

    def _refresh_preview(self):
        img = brand_image(self.slug, 30)
        if img:
            self.preview.configure(image=img, text="")
        else:
            self.preview.configure(image=None, text="?")
            try:  # CustomTkinter keeps the old picture unless it's cleared directly
                self.preview._label.configure(image="")
            except Exception:
                pass

    # ---- the floating list ---------------------------------------------------

    def _ensure_list(self):
        if self.results is None or not self.results.winfo_exists():
            # a child of the pop-up window itself, so it can float over the form
            self.results = ctk.CTkScrollableFrame(self.winfo_toplevel(), height=self.LIST_HEIGHT,
                                                  fg_color=RAISED, corner_radius=12, border_width=1,
                                                  border_color=ACCENT)
            self._shown_query = None

    def _query(self):
        q = self.search.get().strip()
        # showing the chosen logo's name? then browse everything again
        if self.slug and q == (brand_icons.title(self.slug) or ""):
            return ""
        return q

    def _option(self, slug, name):
        ctk.CTkButton(self.results, text="  " + name, image=brand_image(slug, 24), compound="left",
                      anchor="w", height=38, corner_radius=8,
                      fg_color=ACCENT_SOFT if slug == self.slug else "transparent",
                      hover_color=BORDER, text_color=TEXT, font=font(14),
                      command=lambda s=slug: self.choose(s)).pack(fill="x", padx=4, pady=1)

    def _heading(self, text):
        ctk.CTkLabel(self.results, text=text.upper(), font=font(11, "bold"), text_color=ACCENT,
                     anchor="w").pack(fill="x", padx=10, pady=(10, 2))

    def _fill(self, query):
        for w in self.results.winfo_children():
            w.destroy()
        ctk.CTkButton(self.results, text="  No logo (show the first letter)", anchor="w", height=34,
                      corner_radius=8, fg_color="transparent", hover_color=BORDER, text_color=MUTED,
                      font=font(13), command=lambda: self.choose("")).pack(fill="x", padx=4, pady=(4, 1))
        if query:
            hits = brand_icons.search(query, self.MAX_RESULTS)
            for slug, name in hits:
                self._option(slug, name)
            if not hits:
                ctk.CTkLabel(self.results, text="No logo found. Try another name, or\n"
                                                "click “Use my own picture…” below.",
                             font=font(13), text_color=SUBTLE, justify="left").pack(padx=10, pady=8, anchor="w")
        else:
            for title, items in brand_icons.sections():
                self._heading(title)
                for slug, name in items:
                    self._option(slug, name)
        self._shown_query = query

    def show_results(self):
        try:
            self._ensure_list()
            query = self._query()
            if query != self._shown_query:
                self._fill(query)
            if not self.open:
                self.results.place(in_=self.row, relx=0, rely=1.0, y=6, relwidth=1.0, anchor="nw")
                self.open = True
                self.arrow.configure(text="▴")
            self.results._parent_frame.lift()
        except Exception as exc:
            traceback.print_exc()
            self.note.configure(text=f"Couldn't show logos: {exc}", text_color=DANGER)

    def hide_results(self):
        if self.open and self.results is not None and self.results.winfo_exists():
            self.results.place_forget()
        self.open = False
        if self.arrow.winfo_exists():
            self.arrow.configure(text="▾")

    def toggle(self):
        self.hide_results() if self.open else self.show_results()

    def _typed(self, event=None):
        if event is not None and getattr(event, "keysym", "") in ("Return", "Escape", "Tab"):
            if event.keysym == "Escape":
                self.hide_results()
            return
        self.show_results()

    def _pick_top(self, _e=None):
        query = self._query()
        hits = brand_icons.search(query, 1) if query else []
        if hits:
            self.choose(hits[0][0])

    def _click_anywhere(self, event):
        if not self.open or self.results is None:
            return
        clicked = str(event.widget)
        if clicked.startswith(str(self.results._parent_frame)) or clicked.startswith(str(self.row)):
            return
        self.hide_results()

    # ---- choosing --------------------------------------------------------------

    def choose(self, slug, by_hand=True):
        self.slug = slug or ""
        self.picked_by_hand = by_hand
        self.search.delete(0, "end")
        if slug:
            self.search.insert(0, brand_icons.title(slug) or "")
        self._refresh_preview()
        self.note.configure(text="" if by_hand or not slug else "Suggested from the client name. Change it any time.",
                            text_color=SUBTLE)
        self._shown_query = None
        self.hide_results()

    def pick_picture(self):
        """Any picture from the computer (e.g. a logo you saved). It's shrunk
        to a small square and saved encrypted with the login."""
        from tkinter import filedialog
        self.hide_results()
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(), title="Choose a picture for this login",
            filetypes=[("Pictures", "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.ico"), ("All files", "*.*")])
        if not path:
            return
        try:
            icon = brand_icons.picture_to_icon(path)
        except (ValueError, OSError) as exc:
            self.note.configure(text=str(exc), text_color=DANGER)
            return
        self.choose(icon)

    def suggest_from(self, client_name):
        """Auto-pick a logo from the client name, unless the user chose one."""
        if self.picked_by_hand:
            return
        slug = brand_icons.suggest(client_name) or ""
        if slug != self.slug:
            self.choose(slug, by_hand=False)


# ==========================================================================
# The app
# ==========================================================================

# ==========================================================================
# Backgrounds: a picture behind the whole vault screen (Settings > Appearance)
# ==========================================================================

BACKGROUNDS = [
    ("none", "Plain"), ("cherry_blossom", "Cherry Blossom"), ("princess_castle", "Princess Castle"),
    ("ocean_dusk", "Ocean Dusk"), ("fairy_forest", "Fairy Forest"), ("aurora_peaks", "Aurora Peaks"),
    ("ramen_shop", "Ramen Shop"), ("samurai_sunset", "Samurai Sunset"), ("knights_keep", "Knight's Keep"),
    ("neon_city", "Neon City"), ("space_voyage", "Space Voyage"), ("dragon_mountain", "Dragon Mountain"),
    ("soccer_stadium", "Soccer Stadium"), ("sunny_beach", "Sunny Beach"), ("race_track", "Race Track"),
    ("sky_ruins", "Sky Ruins"),
]
# how far the picture fades toward the theme color: darker in dark mode, lighter in light mode
BG_DIM = {"low": 0.25, "medium": 0.42, "high": 0.6}
_bg_source = {}
_bg_thumbs = {}


def background_file(key):
    return resource(os.path.join("assets", "backgrounds", key + ".jpg"))


def background_source(key):
    """The full picture, loaded once."""
    if key not in _bg_source:
        from PIL import Image
        try:
            _bg_source[key] = Image.open(background_file(key)).convert("RGB")
        except OSError:
            _bg_source[key] = None
    return _bg_source[key]


_pic_cache = {}


def background_picture(key, w, h, dim, dark):
    """The picture filling w x h, faded toward the theme color (dark or light). The last few
    are kept, so switching theme or coming back to a screen doesn't redo the work."""
    k = (key, w, h, dim, dark)
    if k not in _pic_cache:
        pic = _make_background_picture(key, w, h, dim, dark)
        if len(_pic_cache) >= 6:
            _pic_cache.pop(next(iter(_pic_cache)))
        _pic_cache[k] = pic
    return _pic_cache[k]


def _make_background_picture(key, w, h, dim, dark):
    from PIL import Image, ImageOps
    src = background_source(key)
    if src is None or w < 2 or h < 2:
        return None
    img = ImageOps.fit(src, (w, h), Image.LANCZOS)
    veil = Image.new("RGB", (w, h), _hex(BG[1] if dark else BG[0]))
    return Image.blend(img, veil, BG_DIM.get(dim, 0.42))


def background_thumb(key, w=120, h=68):
    """A small preview for the picker in Settings."""
    k = (key, w, h)
    if k not in _bg_thumbs:
        from PIL import Image, ImageOps
        src = background_source(key) if key != "none" else None
        if src is None:
            dark = Image.new("RGB", (w * 2, h * 2), (22, 26, 34))
            light = Image.new("RGB", (w * 2, h * 2), (255, 255, 255))
            _bg_thumbs[k] = ctk.CTkImage(light_image=light, dark_image=dark, size=(w, h))
        else:
            img = ImageOps.fit(src, (w * 2, h * 2), Image.LANCZOS)
            _bg_thumbs[k] = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
    return _bg_thumbs[k]


_thumb_pil = {}


def _bg_thumb_pil(key, w, h):
    k = (key, w, h)
    if k not in _thumb_pil:
        from PIL import Image, ImageOps
        src = None
        if key != "none":
            try:
                # JPEGs can be decoded straight at a small size: much faster than the full picture
                src = Image.open(background_file(key))
                src.draft("RGB", (w, h))
                src = src.convert("RGB")
            except OSError:
                src = None
        _thumb_pil[k] = ImageOps.fit(src, (w, h), Image.LANCZOS) if src is not None else None
    return _thumb_pil[k]


def _ui_font(size, bold=False):
    """The chosen font as a PIL font (for pictures that contain words)."""
    from PIL import ImageFont
    stem = next((st for _k, fam, st in FONT_CHOICES if fam == FAMILY), "Poppins")
    try:
        return ImageFont.truetype(_font_file(f"{stem}-{'Bold' if bold else 'Regular'}.ttf"), size)
    except Exception:
        return ImageFont.load_default()


class PickGrid(ctk.CTkLabel):
    """A grid of choices drawn as ONE picture (for the 21 colors and 16 backgrounds).
    Showing one picture is far quicker than making dozens of buttons, so Settings opens fast.
    draw(dark, cur) returns the picture; clicking a cell calls on_pick(value)."""

    def __init__(self, parent, values, cols, cell, draw, get, on_pick):
        super().__init__(parent, text="", cursor="hand2")
        self.values, self.cols, self.cell = values, cols, cell
        self._hk_maker, self._hk_getter, self._hk_pick = draw, get, on_pick
        self.bind("<Button-1>", self._hk_click)
        self.paint()

    def paint(self):
        """Redraw only when the choice, accent color, theme or font changed, and only for
        the theme that's showing (switching theme repaints it)."""
        dark = ctk.get_appearance_mode().lower() == "dark"
        state = (self._hk_getter(), ACCENT, dark, FAMILY, STYLE)
        if getattr(self, "_hk_state", None) == state:
            return
        self._hk_state = state
        pic = self._hk_maker(dark, state[0])
        self.configure(image=ctk.CTkImage(light_image=pic, dark_image=pic, size=(pic.width // 2, pic.height // 2)))

    def _hk_click(self, e):
        sc = self._get_widget_scaling()
        col, row = int(e.x / sc // self.cell[0]), int(e.y / sc // self.cell[1])
        i = row * self.cols + col
        if 0 <= col < self.cols and 0 <= i < len(self.values):
            self._hk_pick(self.values[i])


def accent_grid_picture(dark, cur):
    from PIL import Image, ImageDraw
    k, cols, cw = 2, 7, 48
    rows = (len(ACCENTS) + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw * k, rows * cw * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (key, _n, dk, lt) in enumerate(ACCENTS):
        x, y = (i % cols) * cw * k + 4 * k, (i // cols) * cw * k + 4 * k
        r = _radius(12) * k
        on = key == cur
        if on:
            d.rounded_rectangle([x - 2 * k, y - 2 * k, x + 42 * k, y + 42 * k], radius=r + 2 * k,
                                fill=_hex(TEXT[1] if dark else TEXT[0]))
        d.rounded_rectangle([x + (2 if on else 0) * k, y + (2 if on else 0) * k, x + (38 if on else 40) * k,
                             y + (38 if on else 40) * k], radius=r, fill=_hex(dk if dark else lt))
        if on:
            ink = (11, 17, 22) if dark else (255, 255, 255)
            d.line([(x + 13 * k, y + 21 * k), (x + 18 * k, y + 26 * k), (x + 28 * k, y + 14 * k)], fill=ink,
                   width=3 * k, joint="curve")
    return img


def warm_background_thumbs():
    """Make the Settings picker's thumbnails ahead of time (runs in the background)."""
    for key, _label in BACKGROUNDS:
        _bg_thumb_pil(key, 240, 136)


def background_grid_picture(dark, cur):
    from PIL import Image, ImageDraw
    k, cols, cw, ch = 2, 4, 140, 104
    rows = (len(BACKGROUNDS) + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw * k, rows * ch * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pick = (lambda pair: _hex(pair[1] if dark else pair[0]))
    f = _ui_font(12 * k)
    fb = _ui_font(12 * k, bold=True)
    for i, (key, label) in enumerate(BACKGROUNDS):
        x, y = (i % cols) * cw * k, (i // cols) * ch * k
        on = key == cur
        d.rounded_rectangle([x, y + 4 * k, x + 132 * k, y + 100 * k], radius=_radius(12) * k,
                            fill=pick(ACCENT_SOFT if on else SURFACE), outline=pick(ACCENT if on else BORDER),
                            width=2 * k)
        th = _bg_thumb_pil(key, 120 * k, 68 * k)
        if th is None:
            d.rounded_rectangle([x + 6 * k, y + 10 * k, x + 126 * k, y + 78 * k], radius=_radius(6) * k,
                                fill=pick(BG), outline=pick(BORDER), width=k)
        else:
            mask = Image.new("L", th.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, th.width - 1, th.height - 1], radius=_radius(6) * k,
                                                   fill=255)
            img.paste(th, (x + 6 * k, y + 10 * k), mask)
        d.text((x + 66 * k, y + 89 * k), label, font=fb if on else f, fill=pick(ACCENT if on else TEXT),
               anchor="mm")
    return img


_pfonts = {}


def _preview_font(stem, px, bold):
    """A font for pictures, loaded once per size."""
    key = (stem, px, bold)
    if key not in _pfonts:
        from PIL import ImageFont
        try:
            _pfonts[key] = ImageFont.truetype(_font_file(f"{stem}-{'Bold' if bold else 'Regular'}.ttf"), px)
        except Exception:
            _pfonts[key] = ImageFont.load_default()
    return _pfonts[key]


def appearance_preview(settings, dark):
    """A small picture of the vault with the chosen colors, font, style, background,
    dim and see-through setting, so you can see a change without leaving Settings."""
    from PIL import Image, ImageDraw, ImageFont
    k = 2                                   # drawn at 2x for sharp text
    W, H = 560 * k, 260 * k
    c = (lambda pair: pair[1] if dark else pair[0])
    rgb = (lambda pair: _hex(c(pair)))
    key = settings.get("background", "none")
    pic = background_picture(key, W, H, settings.get("bg_dim", "medium"), dark) if key != "none" else None
    opacity = box_opacity(settings)
    see = pic is not None and opacity < 100
    img = (pic.convert("RGBA") if pic is not None else Image.new("RGBA", (W, H), rgb(BG) + (255,)))
    pixel = settings.get("style") == "pixel"
    r = (lambda v: (2 if pixel else v) * k)
    stem = next((st for kk, _f, st in FONT_CHOICES if kk == settings.get("font", "poppins")), "Poppins")

    def fnt(size, bold=False):
        return _preview_font(stem, size * k, bold)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    edge = ((255, 255, 255, 70) if dark else (30, 34, 42, 70)) if see else rgb(BORDER) + (255,)

    def box(x0, y0, x1, y1, rad, fill, outline=None, width=1):
        d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], radius=r(rad), fill=fill, outline=outline,
                            width=width * k)

    def tint(kind):
        if not see:
            return rgb(SIDE if kind == "panel" else SURFACE) + (255,)
        return rgb(BG) + (box_alpha(kind, opacity, dark),)

    def text(x, y, t, size, color, bold=False, anchor="lm"):
        f = fnt(size, bold)
        if see:
            d.text((x * k + k, y * k + k), t, font=f, fill=rgb(BG) + (255,), anchor=anchor)
        d.text((x * k, y * k), t, font=f, fill=(color if isinstance(color, tuple) and len(color) == 4
                                                else rgb(color) + (255,)), anchor=anchor)
        return d.textlength(t, font=f) / k

    # sidebar
    box(8, 8, 150, H / k - 8, 12, tint("panel"), edge)
    logo = draw_logo(22 * k, tile=False, light=not dark)
    layer.alpha_composite(logo, (18 * k, 18 * k))
    wx = 46 + text(46, 29, "Hush", 13, BRAND_GREEN, True)
    text(wx, 29, "Key", 13, GOLD, True)
    box(14, 50, 144, 74, 8, rgb(ACCENT_SOFT) + ((215 if see else 255),))
    box(22, 58, 30, 66, 2, rgb(ACCENT) + (255,))
    text(38, 62, "All Logins", 11, ACCENT, True)
    star = _star_pil(True, 11 * k, dark)
    layer.alpha_composite(star, (20 * k, 81 * k))
    text(38, 87, "Favorites", 11, TEXT)
    text(22, 110, "FOLDERS", 8, SUBTLE, True)
    d.ellipse([22 * k, 123 * k, 29 * k, 130 * k], fill=(140, 158, 255, 255))
    text(38, 127, "Gaming", 11, TEXT)
    box(14, H / k - 58, 144, H / k - 14, 10, tint("row"), edge)
    d.arc([22 * k, (H / k - 50) * k, 50 * k, (H / k - 22) * k], 0, 360, fill=(255, 255, 255, 40) if dark
          else (0, 0, 0, 30), width=4 * k)
    d.arc([22 * k, (H / k - 50) * k, 50 * k, (H / k - 22) * k], -90, 200, fill=_hex(health_color(82, dark)) + (255,),
          width=4 * k)
    text(58, H / k - 42, "Vault Health", 10, TEXT, True)
    text(58, H / k - 28, "Good · 82/100", 9, (health_color(82, False), health_color(82, True)))

    def pill(x, y, label, kind, size=9, right=False, icon=None):
        """A small button like the real ones: primary, soft (picked) or ghost. Returns its left/right edge."""
        bold = kind in ("primary", "soft")
        tw = text(0, -50, label, size, TEXT, bold) + 16 + (13 if icon else 0)
        xa, xb = (x - tw, x) if right else (x, x + tw)
        h = size + 11
        if kind == "primary":
            box(xa, y, xb, y + h, 7, rgb(ACCENT) + (255,))
            ink = ACCENT_INK
        elif kind == "soft":
            box(xa, y, xb, y + h, 7, rgb(ACCENT_SOFT) + ((235 if see else 255),), rgb(ACCENT) + (255,))
            ink = ACCENT
        else:
            box(xa, y, xb, y + h, 7, tint("button"), edge)
            ink = TEXT
        tx = xa + 8
        if icon is not None:
            layer.alpha_composite(icon, (int(tx * k), int((y + h / 2) * k - icon.height / 2)))
            tx += 13
        text(tx, y + h / 2, label, size, ink, bold)
        return xa if right else xb

    compact = settings.get("density") == "compact"
    show_user = settings.get("show_usernames", False)
    # details panel (right)
    p0, p1 = W / k - 148, W / k - 8
    box(p0, 8, p1, H / k - 8, 12, tint("panel"), edge)
    text(p0 + 10, 20, "›  Hide", 8, SUBTLE)
    box(p0 + 10, 32, p0 + 40, 62, 8, rgb(RAISED) + ((235 if see else 255),))
    icon = brand_icons.render("netflix", 18 * k, light=not dark)
    if icon is not None:
        layer.alpha_composite(icon.convert("RGBA"), (int((p0 + 16) * k), int(38 * k)))
    text(p0 + 48, 47, "Netflix (family)", 10, TEXT, True)
    for i, (label, extra) in enumerate((("USERNAME", 0), ("PASSWORD", 14))):
        y0 = 72 + i * 52
        box(p0 + 10, y0, p1 - 10, y0 + 38 + extra, 8, tint("row"), edge)
        text(p0 + 18, y0 + 11, label, 7, SUBTLE, True)
        text(p0 + 18, y0 + 26, "••••••••", 9, TEXT)
        box(p1 - 46, y0 + 8, p1 - 16, y0 + 24, 6, rgb(ACCENT) + (255,) if i else tint("button"), None if i else edge)
        text(p1 - 31, y0 + 16, "Copy", 7, ACCENT_INK if i else TEXT, True, anchor="mm")
        if extra:
            box(p0 + 18, y0 + 40, p1 - 18, y0 + 44, 2, rgb(TRACK) + (255,))
            box(p0 + 18, y0 + 40, p0 + 18 + (p1 - p0 - 36) * 0.5, y0 + 44, 2, rgb(STRENGTH_COLORS[2]) + (255,))
    box(p0 + 10, H / k - 38, p1 - 10, H / k - 16, 7, tint("button"), edge)
    text((p0 + p1) / 2, H / k - 27, "Edit", 9, TEXT, anchor="mm")

    # top bar
    x0, x1 = 162, p0 - 10
    text(x0, 22, "All Logins", 14, TEXT, True)
    gear = _gear_pil(10 * k, rgb(TEXT))
    sx = pill(x1, 12, "Settings", "ghost", right=True, icon=gear)
    pill(sx - 6, 12, "+  Add Login", "primary", right=True)
    box(x0, 40, x1, 60, 7, rgb(SURFACE) + (255,), rgb(BORDER) + (255,))
    text(x0 + 10, 50, "Search your logins", 9, SUBTLE)
    pill(x0, 66, "Hide usernames" if show_user else "Show usernames", "soft" if show_user else "ghost", size=8)
    cx = pill(x1, 66, "Compact", "soft" if compact else "ghost", size=8, right=True)
    pill(cx - 4, 66, "Comfortable", "ghost" if compact else "soft", size=8, right=True)

    # logins, in the chosen density
    rows = [("Netflix (family)", "netflix", "Used twice", True, "family@mail.com"),
            ("Spotify", "spotify", "", False, "me@mail.com"), ("Steam", "steam", "", False, "gamer_99"),
            ("GitHub", "github", "", False, "dev"), ("Discord", "discord", "", False, "me#1234")]
    y = 92
    rh, gap = (30, 4) if compact else (40, 6)
    for title, slug, note, on, user in rows:
        if y + rh > H / k - 8:
            break
        fill = rgb(ACCENT_SOFT) + ((205 if see else 255),) if on else tint("row")
        box(x0, y, x1, y + rh, 8, fill, rgb(ACCENT) + (255,) if on else edge, 2 if on else 1)
        tz = rh - 12
        box(x0 + 6, y + 6, x0 + 6 + tz, y + 6 + tz, 6, rgb(RAISED) + ((235 if see else 255),))
        iz = 14 if compact else 18
        icon = brand_icons.render(slug, iz * k, light=not dark)
        if icon is not None:
            layer.alpha_composite(icon.convert("RGBA"), (int((x0 + 6 + (tz - iz) / 2) * k),
                                                         int((y + 6 + (tz - iz) / 2) * k)))
        tx = x0 + 12 + tz
        shown = user if show_user else "••••••••"
        if compact:
            tw = text(tx, y + rh / 2, title, 10, TEXT, True)
            room = x1 - 26 - (text(0, -50, note, 8, SUBTLE) + 16 if note else 0) - (tx + tw + 8)
            while shown and text(0, -50, shown, 8, MUTED) > room:   # don't run into the note
                shown = shown[:-2] + "…" if len(shown) > 2 else ""
            text(tx + tw + 8, y + rh / 2, shown, 8, MUTED)
        else:
            text(tx, y + 14, title, 10, TEXT, True)
            text(tx, y + 27, shown, 8, MUTED)
        if note:
            nx = x1 - 24 - text(0, -50, note, 8, SUBTLE)
            d.ellipse([(nx - 8) * k, (y + rh / 2 - 2) * k, (nx - 4) * k, (y + rh / 2 + 2) * k],
                      fill=_hex(c(STRENGTH_COLORS[2])) + (255,))
            text(nx, y + rh / 2, note, 8, SUBTLE)
        layer.alpha_composite(_star_pil(on, 11 * k, dark), (int((x1 - 18) * k), int((y + rh / 2 - 5.5) * k)))
        y += rh + gap
    img.alpha_composite(layer)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=r(14), fill=255)
    out.paste(img, (0, 0), mask)
    return out


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _star_pil(filled, size, dark):
    import math
    from PIL import Image, ImageDraw
    s = size * 8
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = []
    for i in range(10):
        r = s * (0.48 if i % 2 == 0 else 0.2)
        a = math.radians(-90 + i * 36)
        pts.append((s / 2 + r * math.cos(a), s * 0.53 + r * math.sin(a)))
    gold = (242, 193, 78, 255) if dark else (176, 125, 18, 255)
    grey = (140, 149, 165, 255) if dark else (107, 114, 128, 255)
    if filled:
        d.polygon(pts, fill=gold)
    else:
        d.line(pts + [pts[0]], fill=grey, width=int(s * 0.07), joint="curve")
    return img.resize((size, size), Image.LANCZOS)


def box_opacity(settings) -> int:
    """How solid the boxes over a background picture are: 100 = solid (the default), lower = more see-through."""
    try:
        return max(0, min(100, int(settings.get("box_opacity", 100))))
    except (TypeError, ValueError):
        return 100


def box_alpha(kind, opacity, dark):
    """Fill alpha (0-255) for a see-through box. The sidebar and panel stay a little more solid than
    the login rows, so text on them is always easy to read."""
    o = opacity / 100
    a = 20 + 235 * o + (0 if dark else 15 * (1 - o))
    a *= {"row": 1.0, "button": 1.2, "panel": 1.4}[kind]
    return int(max(0, min(255, a)))


def _gear_pil(size, rgb):
    """A small gear (the Settings button), drawn big and shrunk for smooth edges."""
    import math
    from PIL import Image, ImageDraw
    s = size * 8
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    teeth, pts = 8, []
    for i in range(teeth * 4):
        # each tooth: two points out, two points in
        r = s * (0.48 if i % 4 in (1, 2) else 0.36)
        a = math.radians(i * 360 / (teeth * 4) - 90 + 360 / (teeth * 8))
        pts.append((s / 2 + r * math.cos(a), s / 2 + r * math.sin(a)))
    d.polygon(pts, fill=rgb + (255,))
    hole = s * 0.15
    d.ellipse([s / 2 - hole, s / 2 - hole, s / 2 + hole, s / 2 + hole], fill=(0, 0, 0, 0))
    return img.resize((size, size), Image.LANCZOS)


_shared_photos = {}


class _Glass:
    """Drawing helpers shared by the see-through vault screen and its login list.
    Everything is drawn on a canvas, so the picture really shows through: boxes are
    tinted, outlined images and text sits right on top with a soft shadow."""

    def _glass_init(self, app, see, opacity=100):
        self.app, self.see, self.opacity = app, see, opacity
        self._photos, self._fonts, self._n = {}, {}, 0

    @property
    def dark(self):
        return ctk.get_appearance_mode().lower() == "dark"

    def _c(self, pair):
        return pair if isinstance(pair, str) else (pair[1] if self.dark else pair[0])

    def _sc(self):
        try:
            return self._get_widget_scaling()
        except Exception:
            return 1.0

    def _font(self, size, weight="normal", mono=False):
        import tkinter.font as tkfont
        px = int(round(size * self._sc()))
        k = (px, weight, mono, FAMILY)
        if k not in self._fonts:
            fam = MONO if mono else (FAMILY or "TkDefaultFont")
            self._fonts[k] = tkfont.Font(root=self, family=fam, size=-px, weight=weight)
        return self._fonts[k]

    def _photo(self, key, make):
        # Small pictures (rounded boxes, icons, stars) are shared by every screen, so coming back
        # to the vault doesn't draw them all again. The big background slices stay with this screen.
        if key in _shared_photos:
            return _shared_photos[key]
        shared = key[0] not in ("pic", "slice") and len(_shared_photos) < 1500
        cache = _shared_photos if shared else self._photos
        if key not in cache:
            from PIL import ImageTk
            cache[key] = ImageTk.PhotoImage(make(), master=self.winfo_toplevel())
        return cache[key]

    def _rgba(self, pair, alpha=255):
        return _hex(self._c(pair)) + (alpha,)

    def _tint(self, strength="row"):
        """See-through fill for boxes: the theme color, partly clear."""
        if not self.see:
            return self._rgba(SURFACE if strength == "row" else SIDE)
        return self._rgba(BG, box_alpha(strength, self.opacity, self.dark))

    def _edge(self):
        if not self.see:
            return self._rgba(BORDER)
        return (255, 255, 255, 70) if self.dark else (30, 34, 42, 70)

    def rbox(self, w, h, r, fill, outline=None, lw=1):
        """A rounded box image (fill/outline are RGBA tuples)."""
        w, h = max(2, int(w)), max(2, int(h))
        r = _radius(r)
        key = ("rbox", w, h, int(r * self._sc()), fill, outline, lw)

        def make():
            from PIL import Image, ImageDraw
            k = 3
            img = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
            rr = int(min(r * self._sc() * k, h * k / 2))
            width = int(max(1, lw * self._sc()) * k) if outline else 0
            ImageDraw.Draw(img).rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=rr, fill=fill,
                                                  outline=outline, width=width)
            return img.resize((w, h), Image.LANCZOS)
        return self._photo(key, make)

    def hit(self, w, h):
        """An invisible box that catches clicks (canvas images react anywhere in their area)."""
        import tkinter as tk
        w, h = max(1, int(w)), max(1, int(h))
        key = ("hit", w, h)
        if key not in self._photos:
            self._photos[key] = tk.PhotoImage(master=self, width=w, height=h)
        return self._photos[key]

    def text(self, x, y, txt, size, weight="normal", color=TEXT, anchor="w", width=None, tags=(), mono=False,
             shadow=None):
        c, f = self.canvas, self._font(size, weight, mono)
        kw = {"width": int(width)} if width else {}
        self._last_shadow = None
        if shadow == "halo":   # text right on the picture: a soft outline all around
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1)):
                self._last_shadow = c.create_text(x + dx, y + dy, text=txt, font=f, fill=self._c(BG),
                                                  anchor=anchor, tags=tags, **kw)
        elif shadow if shadow is not None else self.see:
            self._last_shadow = c.create_text(x + 1, y + 1, text=txt, font=f, fill=self._c(BG), anchor=anchor,
                                              tags=tags, **kw)
        return c.create_text(x, y, text=txt, font=f, fill=self._c(color), anchor=anchor, tags=tags, **kw)

    def _pair(self, main):
        """The text item plus its shadow, so both can change together."""
        return tuple(i for i in (self._last_shadow, main) if i)

    def clickable(self, tags, cmd):
        tag = f"c{self._n}"
        self._n += 1
        c = self.canvas
        c.tag_bind(tag, "<Button-1>", lambda _e: cmd())
        c.tag_bind(tag, "<Enter>", lambda _e: c.configure(cursor="hand2"))
        c.tag_bind(tag, "<Leave>", lambda _e: c.configure(cursor=""))
        return tuple(tags) + (tag,)

    def button(self, x, y, label, cmd, kind="ghost", h=34, w=None, size=13, tags=("chrome",), anchor="nw",
               icon=None):
        """A pill button drawn on the canvas. Returns its box (x0, y0, x1, y1).
        icon: (picture, its width) shown before the label."""
        sc = self._sc()
        bold = kind in ("primary", "soft", "gold")
        f = self._font(size, "bold" if bold else "normal")
        h = int(h * sc)
        gap = int(8 * sc) if icon else 0
        extra = icon[1] + gap if icon else 0
        w = int(w * sc) if w else f.measure(label) + int(28 * sc) + extra
        if anchor == "ne":
            x -= w
        t = self.clickable(tags, cmd)
        styles = {
            "primary": (self._rgba(ACCENT), None, ACCENT_INK),
            "gold": (self._rgba(GOLD), None, GOLD_INK),
            "soft": (self._rgba(ACCENT_SOFT, 235 if self.see else 255), self._rgba(ACCENT), ACCENT),
            "ghost": (self._tint("button"), self._edge(), TEXT),
            "plain": (None, None, SUBTLE),
            "link": (None, None, ACCENT),
            "goldlink": (None, None, GOLD),
            "danger": (None, None, SIGNOUT),
        }
        fill, line, ink = styles[kind]
        if fill or line:
            self.canvas.create_image(x, y, anchor="nw", image=self.rbox(w, h, 10, fill or (0, 0, 0, 0), line),
                                     tags=t)
        else:
            self.canvas.create_image(x, y, anchor="nw", image=self.hit(w, h), tags=t)
        bare = kind in ("plain", "danger", "link", "goldlink")
        if icon:
            left = x + (w - f.measure(label) - extra) / 2
            self.canvas.create_image(left, y + h / 2, anchor="w", image=icon[0], tags=t)
        main = self.text(x + w / 2 + extra / 2, y + h / 2, label, size, "bold" if bold else "normal", ink,
                         anchor="center",
                         tags=t, shadow="halo" if bare else (self.see and kind == "ghost"))
        self._last_label = self._pair(main)
        return x, y, x + w, y + h


class Stand:
    """Stands in for a label or button on the see-through screen, so the rest of
    the app can keep calling .configure(text=...) on it."""

    def __init__(self, glass, key, text="", color=None):
        self.glass, self.key, self.text, self.color, self.state = glass, key, text, color, "normal"
        self.command = None

    def configure(self, text=None, text_color=None, state=None, **_):
        if text is not None:
            self.text = text
        if text_color is not None:
            self.color = text_color
        if state is not None:
            self.state = state
        self.glass.restand(self)

    def cget(self, key):
        return {"text": self.text, "state": self.state}.get(key)

    def winfo_exists(self):
        try:
            return bool(self.glass.winfo_exists())
        except Exception:
            return False

    def invoke(self):
        if self.command:
            self.command()


class ArtList(_Glass, ctk.CTkFrame):
    """The login list on one canvas. It shows its own slice of the screen's picture,
    so the picture looks like one piece behind everything. The picture stays still
    while the logins scroll, and is only re-made when the window size changes."""

    def __init__(self, parent, app, glass, see_through=True, opacity=100):
        ctk.CTkFrame.__init__(self, parent, fg_color=BG, corner_radius=0, border_width=0)
        import tkinter as tk
        self._glass_init(app, see_through, opacity)
        self.glass = glass
        self.offset = (0, 0)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self._c(BG), yscrollincrement=20)
        self.canvas.configure(yscrollcommand=self._scrolled)
        self.canvas.pack(fill="both", expand=True)
        self._rows, self._items = [], {}
        self._more = self._empty = self._restore = None
        self._bg_item = self._bg_key = None
        self._seen_w = self._drawn_w = 0
        self._y = 0
        self._resize_job = None
        self.canvas.bind("<Configure>", self._configured)
        self.canvas.tag_bind("thumb", "<B1-Motion>", self._drag)
        self.canvas.tag_bind("thumb", "<Button-1>", self._grab)
        if not getattr(app, "_art_wheel_on", False):   # one shared wheel hook; it never removes other lists' hooks
            app._art_wheel_on = True
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                app.bind_all(ev, lambda e: ArtList.wheel(app, e), add="+")

    # -- scrolling
    @staticmethod
    def wheel(app, e):
        art = getattr(app, "art", None)
        if art is None or not art.winfo_exists():
            return
        c = art.canvas
        x, y = c.winfo_pointerx() - c.winfo_rootx(), c.winfo_pointery() - c.winfo_rooty()
        if not (0 <= x < c.winfo_width() and 0 <= y < c.winfo_height()):
            return
        px = wheel_pixels(e)
        if px:
            smooth_scroll(c, px)

    def _scrolled(self, a, b):
        a, b = float(a), float(b)
        c = self.canvas
        top = c.canvasy(0)
        if self._bg_item is not None:
            c.coords(self._bg_item, 0, top)
        c.delete("thumb")
        if b - a < 0.999:   # a slim scroll handle on the right, drawn over the picture
            h = c.winfo_height()
            sc = self._sc()
            th = max(int(30 * sc), int(h * (b - a)))
            ty = top + int((h - th) * (a / max(1e-6, 1 - (b - a))))
            w = int(6 * sc)
            c.create_image(c.winfo_width() - w - 2, ty, anchor="nw", tags=("thumb",),
                           image=self.rbox(w, th, 3, self._rgba(MUTED, 170)))

    def _grab(self, e):
        self._grab_y, self._grab_top = e.y, self.canvas.yview()[0]

    def _drag(self, e):
        h = max(1, self.canvas.winfo_height())
        self.canvas.yview_moveto(self._grab_top + (e.y - self._grab_y) / h)

    # -- the picture
    def _configured(self, e):
        if e.width == self._seen_w and e.width == self._drawn_w:
            self.refresh_bg()
            return
        # the screen only resizes the list after the window settles, so redraw right away
        self._relayout()

    def refresh_bg(self):
        c = self.canvas
        w, h = c.winfo_width(), c.winfo_height()
        if w < 10 or h < 10:
            return
        c.configure(bg=self._c(BG))
        key = ("bg", self.glass.bg_key(), self.offset, w, h)
        if self._bg_key != key:
            photo = self.glass.slice(self.offset[0], self.offset[1], w, h)
            if photo is None:
                return
            self._bg_key = key
            if self._bg_item is None:
                self._bg_item = c.create_image(0, 0, anchor="nw", image=photo, tags=("bg",))
            else:
                c.itemconfigure(self._bg_item, image=photo)
        c.tag_lower("bg")
        c.coords(self._bg_item, 0, c.canvasy(0))
        self._scrolled(*c.yview())

    # -- rows
    def _row_box(self, w, h, on):
        r = 10 if self.app.compact else 12
        if on:
            fill = self._rgba(ACCENT_SOFT, (200 if self.dark else 215) if self.see else 255)
            return self.rbox(w, h, r, fill, self._rgba(ACCENT), 2)
        return self.rbox(w, h, r, self._tint("row"), self._edge(), 1.5 if self.see else 1)

    def _tile(self, size):
        return self.rbox(size, size, size / self._sc() * 0.22, self._rgba(RAISED, 235 if self.see else 255))

    def clear(self, keep_scroll=False):
        self._restore = self.canvas.yview()[0] if keep_scroll else None
        self.canvas.delete("row")
        self.canvas.delete("more")
        if self._empty is not None:
            self._empty.destroy()
            self._empty = None
        self._rows, self._items, self._more, self._y = [], {}, None, 0
        self.refresh_bg()

    def finish(self):
        self._set_region()
        if self._restore is not None:
            self.canvas.yview_moveto(self._restore)
            self._restore = None

    def _set_region(self):
        h = max(self._y + 8 * self._sc(), self.canvas.winfo_height())
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), h))

    def add_row(self, e, info):
        self._rows.append((e, info))
        self._draw_row(e, info)
        self._set_region()

    def _draw_row(self, e, info):
        c, sc, compact = self.canvas, self._sc(), self.app.compact
        W = max(200, c.winfo_width())
        self._drawn_w = W
        h = int((44 if compact else 64) * sc)
        gap = int((4 if compact else 8) * sc)
        y = int(self._y + gap / 2)
        w = int(W - 14 * sc)
        eid = e["id"]
        sel = self.clickable(("row",), lambda: self.app.select(eid))
        card = c.create_image(0, y, anchor="nw", image=self._row_box(w, h, eid == self.app.sel_id), tags=sel)
        self._items[eid] = (card, w, h)
        tile = int((32 if compact else 44) * sc)
        tx, cy = int(12 * sc), y + h // 2
        c.create_image(tx, cy, anchor="w", image=self._tile(tile), tags=sel)
        icon = int((18 if compact else 24) * sc)
        img = None
        if e.get("icon"):
            pil = brand_icons.render(e["icon"], icon * 2, light=not self.dark)
            if pil is not None:
                from PIL import Image
                img = self._photo(("icon", e["icon"], icon, self.dark), lambda: pil.resize((icon, icon), Image.LANCZOS))
        if img:
            c.create_image(tx + tile // 2, cy, image=img, tags=sel)
        else:
            c.create_text(tx + tile // 2, cy, text=(e["title"][:1] or "?").upper(),
                          font=self._font(15 if compact else 17, "bold"), fill=self._c(ACCENT), tags=sel)
        x = tx + tile + int(12 * sc)
        right = w - int(8 * sc)
        star = int(18 * sc)
        sx = right - int(17 * sc)
        fav = self.clickable(("row",), lambda: self.app.toggle_fav(eid))
        c.create_image(sx - 17 * sc, cy - 17 * sc, anchor="nw", image=self.hit(34 * sc, 34 * sc), tags=fav)
        c.create_image(sx, cy, image=self._photo(("star", e["fav"], star, self.dark),
                                                 lambda: _star_pil(e["fav"], star, self.dark)), tags=fav)
        right = sx - int(24 * sc)
        if info.get("remove"):
            bx0, _, _, _ = self.button(right, cy - 14 * sc, "Remove", lambda: self.app.remove_from_folder(eid),
                                       "ghost", h=28, size=11, tags=("row",), anchor="ne")
            right = bx0 - int(8 * sc)
        if info.get("note"):
            label, color = info["note"]
            t = self.text(right, cy, label, 11, "normal", SUBTLE, anchor="e", tags=sel)
            x0 = c.bbox(t)[0] - int(13 * sc)
            r = 3.5 * sc
            c.create_oval(x0 - r, cy - r, x0 + r, cy + r, fill=self._c(color), outline="", tags=sel)
        if compact:
            n = self.text(x, cy, e["title"], 14, "bold", TEXT, tags=sel)
            self.text(c.bbox(n)[2] + int(12 * sc), cy, info["user"], 12, "normal", MUTED, tags=sel)
        else:
            self.text(x, cy - int(9 * sc), e["title"], 15, "bold", TEXT, tags=sel)
            self.text(x, cy + int(11 * sc), info["user"], 12, "normal", MUTED, tags=sel)
        self._y = y + h + gap / 2

    def set_selected(self, old, new):
        for eid, on in ((old, False), (new, True)):
            if eid in self._items:
                item, w, h = self._items[eid]
                self.canvas.itemconfigure(item, image=self._row_box(w, h, on))

    def add_more(self, text, command):
        c, sc = self.canvas, self._sc()
        W = max(200, c.winfo_width())
        f = self._font(13)
        w = f.measure(text) + int(40 * sc)
        x0, _, _, y1 = self.button((W - w) // 2, self._y + 8 * sc, text, command, "ghost", h=40, tags=("more",))
        self._more = (text, command)
        self._y = y1 + 12 * sc
        self._set_region()

    def remove_more(self):
        if self._more is not None:
            self.canvas.delete("more")
            self._more = None

    def empty_holder(self):
        """A solid box for the empty-list message (it has buttons, so it stays a normal widget)."""
        box = ctk.CTkFrame(self.canvas, fg_color=SURFACE, corner_radius=14, border_width=1, border_color=BORDER)
        W = max(200, self.canvas.winfo_width())
        self.canvas.create_window(0, int(10 * self._sc()), anchor="nw", window=box, width=int(W - 14 * self._sc()),
                                  tags=("row",))
        self._empty = box
        return box

    def _relayout(self):
        self._resize_job = None
        self._seen_w = self.canvas.winfo_width()
        rows, more = self._rows, self._more
        frac = self.canvas.yview()[0]
        self.canvas.delete("row")
        self.canvas.delete("more")
        self._rows, self._items, self._y, self._more = [], {}, 0, None
        self.refresh_bg()
        if self._empty is not None:
            self._empty = None
            self.app.refresh_rows(keep_scroll=True)
            return
        for e, info in rows:
            self.add_row(e, info)
        if more:
            self.add_more(*more)
        self._set_region()
        self.canvas.yview_moveto(frac)


class GlassMain(_Glass, ctk.CTkFrame):
    """The vault screen with a background picture behind everything: the sidebar,
    the top bar, the logins and the details panel are see-through boxes over it."""

    SIDE, PANEL, RAIL = 236, 372, 46

    def __init__(self, parent, app, key, dim="medium", opacity=100):
        ctk.CTkFrame.__init__(self, parent, fg_color=BG, corner_radius=0)
        import tkinter as tk
        see_through = key != "none" and opacity < 100
        self._glass_init(app, see_through, opacity)
        self.key, self.dim = key, dim
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self._c(BG))
        self.canvas.pack(fill="both", expand=True)
        self._pic = None           # (key, PIL picture) for the current size
        self._job = None
        self._size = (0, 0)
        self.stands = {"status": Stand(self, "status", "Usernames and passwords stay hidden until you ask.", MUTED),
                       "sync": Stand(self, "sync", "", SUBTLE),
                       "recovery": Stand(self, "recovery", "Turn on")}
        self._stand_items = {}
        self.search = ctk.CTkEntry(self.canvas, placeholder_text="Search your logins", height=34, corner_radius=0,
                                   border_width=0, fg_color=SURFACE, text_color=TEXT,
                                   placeholder_text_color=SUBTLE, font=font(14))
        self._search_win = self.canvas.create_window(-999, -999, anchor="nw", window=self.search, tags=("win",))
        self.art = ArtList(self.canvas, app, self, see_through, opacity)
        self._art_win = self.canvas.create_window(-999, -999, anchor="nw", window=self.art, tags=("win",))
        self.form_slot = ctk.CTkFrame(self.canvas, fg_color=SIDE, width=1, height=1, corner_radius=0)
        self._form_win = self.canvas.create_window(-999, -999, anchor="nw", window=self.form_slot, tags=("win",))
        self.canvas.bind("<Configure>", self._configured)
        ctk.AppearanceModeTracker.add(self._mode_changed, self)

    def destroy(self):
        try:
            ctk.AppearanceModeTracker.remove(self._mode_changed)
        except Exception:
            pass
        ctk.CTkFrame.destroy(self)

    def _mode_changed(self, _mode=None):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(20, lambda: self.app.refresh_rows(keep_scroll=True))

    def _configured(self, e):
        if (e.width, e.height) == self._size or e.width < 300 or e.height < 200:
            return   # minimized, or nothing changed
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(80, self.redraw)

    # -- the picture
    def bg_key(self):
        return (self.key, self._size, self.dim, self.dark)

    def picture(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self._size = (w, h)
        if self._pic is None or self._pic[0] != self.bg_key():
            self._pic = (self.bg_key(), background_picture(self.key, w, h, self.dim, self.dark))
            for k in [k for k in self._photos if k[0] in ("pic", "slice")]:
                del self._photos[k]
        return self._pic[1]

    def slice(self, x, y, w, h):
        pic = self.picture()
        if pic is None:
            return None
        return self._photo(("slice", x, y, w, h), lambda: pic.crop((x, y, x + w, y + h)))

    # -- stand-ins
    def restand(self, stand):
        items = self._stand_items.get(stand.key)
        if items and self.canvas.winfo_exists():
            for i in items:
                self.canvas.itemconfigure(i, text=stand.text)
            if stand.color is not None:
                self.canvas.itemconfigure(items[-1], fill=self._c(stand.color))

    def _stand_text(self, stand, x, y, size=12, anchor="w", width=None, tags=("chrome",)):
        t = self.text(x, y, stand.text, size, "normal", stand.color or MUTED, anchor=anchor, width=width, tags=tags,
                      shadow="halo")
        self._stand_items[stand.key] = self._pair(t)
        return t

    # -- layout
    def redraw(self):
        self._job = None
        c, a, sc = self.canvas, self.app, self._sc()
        if not c.winfo_exists() or a.vault is None:
            return
        W, H = c.winfo_width(), c.winfo_height()
        if W < 300 or H < 200:
            return
        c.configure(bg=self._c(BG))
        c.delete("chrome")
        self._stand_items = {}
        pic = self.picture()
        if pic is not None:
            c.create_image(0, 0, anchor="nw", image=self._photo(("pic", W, H, self.bg_key()), lambda: pic),
                           tags=("chrome", "pic"))
        m = int(10 * sc)
        side = int(self.SIDE * sc)
        right = W
        if a.sel_id is not None:
            right = W - int((self.PANEL if a.settings.get("panel_open", True) else self.RAIL) * sc)
        self._sidebar(m, m, side, H - m)
        self._main(side + int(16 * sc), right - int(16 * sc), W, H)
        is_open = a.sel_id is not None and a.settings.get("panel_open", True)
        if a.sel_id is not None:
            before = set(c.find_all())
            if is_open:
                self._panel(right, m, W - m, H - m)
            else:
                self._rail(right, m, W - m, H - m)
            tag = f"panel{self._n}"
            self._n += 1
            for i in c.find_all():
                if i not in before:
                    c.addtag_withtag(tag, i)
            self._panel_tag, self._panel_box = tag, (right, m, W - m, H - m, is_open)
            if is_open and not getattr(self, "_was_open", False) and a.animate:
                shift = W - right   # slide in from the right edge
                c.move(tag, shift, 0)
                moved = [shift]

                def slide(p):
                    step = shift * (1 - p) - moved[0]
                    c.move(tag, step, 0)
                    moved[0] += step
                a.glide(8, slide)
        self._was_open = is_open
        self._layout_key = (W, H, a.sel_id is not None, is_open)
        c.tag_lower("pic")
        c.tag_raise("win")

    def redraw_panel(self):
        """Clicking another login only changes the details panel: redraw just that part."""
        a, c = self.app, self.canvas
        W, H = c.winfo_width(), c.winfo_height()
        is_open = a.sel_id is not None and a.settings.get("panel_open", True)
        if getattr(self, "_layout_key", None) != (W, H, a.sel_id is not None, is_open) \
                or not getattr(self, "_panel_tag", None) or not is_open:
            return self.redraw()
        c.delete(self._panel_tag)
        x0, y0, x1, y1, _ = self._panel_box
        before = set(c.find_all())
        self._panel(x0, y0, x1, y1)
        tag = f"panel{self._n}"
        self._n += 1
        for i in c.find_all():
            if i not in before:
                c.addtag_withtag(tag, i)
        self._panel_tag = tag
        c.tag_raise("win")

    def _card(self, x0, y0, x1, y1):
        self.canvas.create_image(x0, y0, anchor="nw", tags=("chrome",),
                                 image=self.rbox(x1 - x0, y1 - y0, 16, self._tint("panel"), self._edge()))

    def _sidebar(self, x0, y0, x1, y1):
        c, a, sc = self.canvas, self.app, self._sc()
        self._card(x0, y0, x1, y1)
        pad = int(16 * sc)
        y = y0 + int(18 * sc)
        lz = int(38 * sc)
        c.create_image(x0 + pad, y, anchor="nw", tags=("chrome",),
                       image=self._photo(("logo", lz, self.dark), lambda: draw_logo(lz, tile=False, light=not self.dark)))
        tx = x0 + pad + lz + int(8 * sc)
        t = self.text(tx, y + lz / 2, "Hush", 21, "bold", BRAND_GREEN, tags=("chrome",), shadow=False)
        self.text(c.bbox(t)[2], y + lz / 2, "Key", 21, "bold", GOLD, tags=("chrome",), shadow=False)
        y += lz + int(18 * sc)
        entries = a.vault.list_entries()
        favs = sum(1 for e in entries if e["fav"])
        y = self._nav(x0, x1, y, "All Logins", len(entries), a.view == "all", lambda: a.set_view("all"), "box")
        y = self._nav(x0, x1, y, "Favorites", favs, a.view == "favorites", lambda: a.set_view("favorites"), "star")
        y += int(14 * sc)
        self.text(x0 + pad + int(8 * sc), y + 12 * sc, "FOLDERS", 11, "bold", SUBTLE, tags=("chrome",))
        self.button(x1 - int(10 * sc), y, "+", a.open_folder_form, "link", h=26, w=28, size=18, anchor="ne")
        y += int(30 * sc)
        counts = {}
        for e in entries:
            if e["folder"]:
                counts[e["folder"]] = counts.get(e["folder"], 0) + 1
        for f in a.vault.folders():
            y = self._nav(x0, x1, y, f["name"], counts.get(f["id"], 0), a.view == "folder:" + f["id"],
                          lambda fid=f["id"]: a.set_view("folder:" + fid), f.get("color") or self._c(ACCENT))
        form = a._folder_form is not None and a._folder_form.winfo_exists()
        if not a.vault.folders() and not form:
            self.text(x0 + pad + int(8 * sc), y + 10 * sc, "Click + to make a folder", 12, "normal", SUBTLE,
                      tags=("chrome",))
        c.coords(self._form_win, (x0 + int(10 * sc), y + int(4 * sc)) if form else (-999, -999))
        if form:
            c.itemconfigure(self._form_win, width=x1 - x0 - int(20 * sc))
        # bottom: vault health + sync
        by = y1 - int(14 * sc)
        if a.syncer is not None:
            s = self.stands["sync"]
            t = self._stand_text(s, x0 + pad + int(4 * sc), by - 8 * sc, 12, tags=self.clickable(
                ("chrome",), a._sync_label_clicked))
            by -= int(28 * sc)
        hh = int(80 * sc)
        hx0, hy0 = x0 + int(10 * sc), by - hh
        tags = self.clickable(("chrome",), a.show_security)
        c.create_image(hx0, hy0, anchor="nw", tags=tags,
                       image=self.rbox(x1 - x0 - int(20 * sc), hh, 14, self._tint("row"), self._edge()))
        score = getattr(a, "_score", 100)
        rz = int(58 * sc)
        c.create_image(hx0 + int(10 * sc), hy0 + hh / 2, anchor="w", tags=tags,
                       image=self._photo(("ring", score, rz, self.dark), lambda: self._ring(score, rz)))
        self.text(hx0 + int(10 * sc) + rz / 2, hy0 + hh / 2, str(score), 16, "bold", TEXT, anchor="center",
                  tags=tags)
        wx = hx0 + rz + int(20 * sc)
        word = health_word(score)
        n = getattr(a, "_open_tips", 0)
        self.text(wx, hy0 + 22 * sc, "Vault Health", 13, "bold", TEXT, tags=tags)
        self.text(wx, hy0 + 41 * sc, f"{word} · {score}/100", 12, "normal",
                  (health_color(score, False), health_color(score, True)), tags=tags)
        self.text(wx, hy0 + 59 * sc, f"{n} optional tip{'s' if n != 1 else ''} →" if n else "All caught up →",
                  11, "normal", SUBTLE, tags=tags)

    def _ring(self, score, size):
        from PIL import Image, ImageDraw
        s = size * 4
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        w = int(s * 0.11)
        d.ellipse([w // 2, w // 2, s - w // 2, s - w // 2], outline="#2A303C" if self.dark else "#E9E2D2", width=w)
        if score > 0:
            d.arc([w // 2, w // 2, s - w // 2, s - w // 2], -90, -90 + 360 * score / 100,
                  fill=health_color(score, self.dark), width=w)
        return img.resize((size, size), Image.LANCZOS)

    def _nav(self, x0, x1, y, label, count, on, cmd, icon):
        c, sc = self.canvas, self._sc()
        h = int(38 * sc)
        tags = self.clickable(("chrome",), cmd)
        rx0, rw = x0 + int(8 * sc), x1 - x0 - int(16 * sc)
        if on:
            c.create_image(rx0, y, anchor="nw", tags=tags,
                           image=self.rbox(rw, h, 10, self._rgba(ACCENT_SOFT, 215 if self.see else 255)))
        else:
            c.create_image(rx0, y, anchor="nw", tags=tags, image=self.hit(rw, h))
        cy, ix = y + h / 2, rx0 + int(18 * sc)
        if icon == "star":
            z = int(15 * sc)
            c.create_image(ix, cy, tags=tags, image=self._photo(("star", True, z, self.dark),
                                                                lambda: _star_pil(True, z, self.dark)))
        else:
            r = (6 if icon == "box" else 5) * sc
            col = self._c(ACCENT if on else SUBTLE) if icon == "box" else icon
            c.create_image(ix, cy, tags=tags, image=self.rbox(2 * r, 2 * r, 3, _hex(col) + (255,)))
        self.text(ix + int(16 * sc), cy, label, 14 if icon in ("box", "star") else 13, "bold" if on else "normal",
                  ACCENT if on else TEXT, tags=tags)
        self.text(rx0 + rw - int(12 * sc), cy, str(count), 12, "normal", SUBTLE, anchor="e", tags=tags)
        return y + h + int(2 * sc)

    def _main(self, x0, x1, W, H):
        c, a, sc = self.canvas, self.app, self._sc()
        y = int(20 * sc)
        folder = None
        if a.view.startswith("folder:"):
            folder = next((f for f in a.vault.folders() if f["id"] == a.view[7:]), None)
        title = "Favorites" if a.view == "favorites" else (folder["name"] if folder else "All Logins")
        t = self.text(x0, y + 19 * sc, title, 22, "bold", TEXT, tags=("chrome",), shadow="halo")
        if folder:
            bx = c.bbox(t)[2] + int(10 * sc)
            bx = self.button(bx, y + 6 * sc, "Rename", lambda: a.rename_folder(folder), "plain", h=26, size=12)[2]
            self.button(bx, y + 6 * sc, "Delete folder", lambda: a.delete_folder(folder), "plain", h=26, size=12)
        gz = int(16 * sc)
        gear = self._photo(("gear", gz, self._c(TEXT)), lambda: _gear_pil(gz, _hex(self._c(TEXT))))
        px0 = self.button(x1, y, "Settings", lambda: a.show_settings("general"), "ghost", h=38, size=14,
                          anchor="ne", icon=(gear, gz))[0]
        self.button(px0 - int(10 * sc), y, "+  Add Login", a.open_add, "primary", h=38, w=128, size=14, anchor="ne")
        y += int(52 * sc)
        sync_off = a.syncer is not None and not a.syncer.enabled and a.syncer._session is None
        if a.cloud.configured and (not a.vault.has_recovery or sync_off):
            text = ("Turn on sync to use HushKey on all your computers"
                    + ("" if a.vault.has_recovery else " and to reset your master password by email if you forget it")
                    + ". Only encrypted data is uploaded.")
            bh = int(60 * sc)
            c.create_image(x0, y, anchor="nw", tags=("chrome",),
                           image=self.rbox(x1 - x0, bh, 12, self._rgba(GOLD_SOFT, 230 if self.see else 255),
                                           self._rgba(GOLD)))
            self.text(x0 + 16 * sc, y + bh / 2, text, 13, "normal", TEXT, width=x1 - x0 - 150 * sc, tags=("chrome",),
                      shadow=False)
            r = self.stands["recovery"]
            r.command = a.turn_on_recovery
            self.button(x1 - 12 * sc, y + (bh - 36 * sc) / 2, r.text,
                        lambda: a.turn_on_recovery() if r.state == "normal" else None, "gold", h=36, w=100,
                        size=14, anchor="ne")
            self._stand_items["recovery"] = self._last_label
            y += bh + int(12 * sc)
        sh = int(42 * sc)
        c.create_image(x0, y, anchor="nw", tags=("chrome",),
                       image=self.rbox(x1 - x0, sh, 12, self._rgba(SURFACE), self._rgba(BORDER)))
        c.coords(self._search_win, x0 + int(12 * sc), y + int(4 * sc))
        c.itemconfigure(self._search_win, width=x1 - x0 - int(24 * sc), height=sh - int(8 * sc))
        y += sh + int(10 * sc)
        on = a.settings.get("show_usernames", False)
        self.button(x0, y, "Hide usernames" if on else "Show usernames", a.toggle_usernames,
                    "soft" if on else "ghost", h=30, size=12)
        comp = a.compact
        bx = self.button(x1, y, "Compact", lambda: a.set_density("Compact"), "soft" if comp else "ghost", h=30,
                         size=12, anchor="ne")[0]
        self.button(bx - int(6 * sc), y, "Comfortable", lambda: a.set_density("Comfortable"),
                    "ghost" if comp else "soft", h=30, size=12, anchor="ne")
        y += int(40 * sc)
        foot = int(34 * sc)
        lh = max(int(60 * sc), H - y - foot)
        self.art.offset = (int(x0), int(y))
        c.coords(self._art_win, x0, y)
        c.itemconfigure(self._art_win, width=int(x1 - x0), height=lh)
        self.art.refresh_bg()
        fy = H - foot / 2
        self._stand_text(self.stands["status"], x0, fy, 12)
        v = self.text(x1, fy, f"v{__version__}", 11, "normal", SUBTLE, anchor="e", tags=("chrome",), shadow="halo")
        if a.update_release is not None:
            self.button(c.bbox(v)[0] - int(8 * sc), fy - 13 * sc, f"HushKey v{a.update_release.version} is ready: "
                        "update now", a.show_update_dialog, "goldlink", h=26, size=12, anchor="ne")

    def _rail(self, x0, y0, x1, y1):
        self._card(x0, y0, x1, y1)
        self.button(x0 + (x1 - x0) / 2 - 16 * self._sc(), y0 + 12 * self._sc(), "‹", self.app.open_panel, "ghost",
                    h=32, w=32, size=16)

    def _panel(self, x0, y0, x1, y1):
        c, a, sc = self.canvas, self.app, self._sc()
        try:
            e = a.vault.get(a.sel_id)
        except VaultError:
            a.sel_id = None
            return
        self._card(x0, y0, x1, y1)
        pad = int(18 * sc)
        x0p, x1p = x0 + pad, x1 - pad
        y = y0 + int(10 * sc)
        self.button(x0p - 8 * sc, y, "›  Hide", a.close_panel, "plain", h=28, size=12)
        y += int(38 * sc)
        tz = int(58 * sc)
        c.create_image(x0p, y, anchor="nw", tags=("chrome",), image=self.rbox(tz, tz, 14, self._rgba(RAISED, 235)))
        img = None
        if e["icon"]:
            iz = int(32 * sc)
            pil = brand_icons.render(e["icon"], iz * 2, light=not self.dark)
            if pil is not None:
                from PIL import Image
                img = self._photo(("icon", e["icon"], iz, self.dark), lambda: pil.resize((iz, iz), Image.LANCZOS))
        if img:
            c.create_image(x0p + tz / 2, y + tz / 2, image=img, tags=("chrome",))
        else:
            self.text(x0p + tz / 2, y + tz / 2, (e["title"][:1] or "?").upper(), 22, "bold", ACCENT, anchor="center",
                      tags=("chrome",), shadow=False)
        sz = int(22 * sc)
        st = self.clickable(("chrome",), lambda: a.toggle_fav(e["id"]))
        c.create_image(x1p - sz / 2, y + tz / 2, tags=st, image=self._photo(
            ("star", e["fav"], sz, self.dark), lambda: _star_pil(e["fav"], sz, self.dark)))
        nx = x0p + tz + int(12 * sc)
        t = self.text(nx, y + 4 * sc, e["title"], 18, "bold", TEXT, anchor="nw", width=x1p - nx - 34 * sc,
                      tags=("chrome",))
        ty = c.bbox(t)[3]
        if e["url"]:
            site = e["url"].split("//")[-1].split("/")[0].removeprefix("www.")
            ty = self.button(nx - 14 * sc, ty, f"{site} · Open site ↗", lambda: webbrowser.open(e["url"]), "link",
                             h=24, size=12)[3]
        y = max(y + tz, ty) + int(14 * sc)
        a._revealed = {"user": False, "pass": False}
        a._secret_widgets = {}
        y = self._secret(x0p, x1p, y, "USERNAME", "user", e["username"] or "(none)", 0, False)
        y = self._secret(x0p, x1p, y + 10 * sc, "PASSWORD", "pass", e["password"], 1, True)
        # folders
        y += int(14 * sc)
        self.text(x0p, y + 8 * sc, "FOLDER", 11, "bold", SUBTLE, tags=("chrome",), shadow="halo")
        y += int(24 * sc)
        folders = a.vault.folders()
        cur = next((f for f in folders if f["id"] == e["folder"]), None)
        if cur:
            y = self._chip(x0p, y, cur.get("color") or self._c(ACCENT), cur["name"] + "   ×",
                           lambda: a.remove_from_folder(e["id"]), on=True)[3] + int(6 * sc)
        if not folders:
            t = self.text(x0p, y + 8 * sc, "No folders yet. Click + under Folders to make one.", 12, "normal", SUBTLE,
                          width=x1p - x0p, anchor="nw", tags=("chrome",))
            y = c.bbox(t)[3] + int(6 * sc)
        else:
            others = [f for f in folders if f["id"] != e["folder"]]
            if others:
                t = self.text(x0p, y + 14 * sc, "Move to" if cur else "Add to", 12, "normal", SUBTLE,
                              tags=("chrome",), shadow="halo")
                x = c.bbox(t)[2] + int(8 * sc)
                for f in others:
                    w = self._font(12).measure(f["name"]) + int(34 * sc)
                    if x + w > x1p:
                        x, y = x0p, y + int(34 * sc)
                    x = self._chip(x, y, f.get("color") or self._c(ACCENT), f["name"],
                                   lambda fid=f["id"]: a.move_to_folder(e["id"], fid))[2] + int(6 * sc)
                y += int(34 * sc)
        # suggestion
        r = a._report.get(e["id"])
        if a._tip_visible(r):
            _, tip = a._tip_text(r)
            y += int(8 * sc)
            tw = x1p - x0p
            probe = c.create_text(0, -9999, text=tip, font=self._font(12), width=tw - 40 * sc, anchor="nw")
            th = c.bbox(probe)[3] - c.bbox(probe)[1]
            c.delete(probe)
            f12 = self._font(12)
            fits = (f12.measure("Make a stronger one") + f12.measure("Not now") + f12.measure("Don't remind me")
                    + 104 * sc) < tw
            bh = th + int((62 if fits else 96) * sc)
            c.create_image(x0p, y, anchor="nw", tags=("chrome",),
                           image=self.rbox(tw, bh, 10, self._tint("row"), self._edge()))
            d = 3.5 * sc
            c.create_oval(x0p + 14 * sc - d, y + 18 * sc - d, x0p + 14 * sc + d, y + 18 * sc + d,
                          fill=self._c(a._tip_color(r)), outline="", tags=("chrome",))
            self.text(x0p + 26 * sc, y + 10 * sc, tip, 12, "normal", MUTED, anchor="nw", width=tw - 40 * sc,
                      tags=("chrome",))
            by = y + th + int(22 * sc)
            bx = self.button(x0p + 10 * sc, by, "Make a stronger one", lambda: a.open_edit(e["id"], fresh=True),
                             "soft", h=28, size=12)[2]
            if not fits:
                bx, by = x0p + 2 * sc, by + 34 * sc
            bx = self.button(bx + 2 * sc, by, "Not now", lambda: a.snooze_tip(e["id"]), "plain", h=28, size=12)[2]
            self.button(bx, by, "Don't remind me", lambda: a.mute_tip(e["id"]), "plain", h=28, size=12)
        # bottom
        bh = int(40 * sc)
        by = y1 - pad - bh
        dx = self.button(x1p, by, "Delete", lambda: a.delete_entry(e["id"]), "plain", h=40, w=80, size=14,
                         anchor="ne")[0]
        self.button(x0p, by, "Edit", lambda: a.open_edit(e["id"]), "ghost", h=40, w=(dx - x0p) / sc - 8, size=14)
        self.text(x0p, by - 16 * sc, "Password changed " + ago(e["changed"]), 12, "normal", SUBTLE, tags=("chrome",),
                  shadow="halo")

    def _chip(self, x, y, color, label, cmd, on=False):
        c, sc = self.canvas, self._sc()
        w = self._font(12, "bold" if on else "normal").measure(label) + int(34 * sc)
        h = int(28 * sc)
        tags = self.clickable(("chrome",), cmd)
        fill = self._rgba(ACCENT_SOFT, 225 if self.see else 255) if on else self._tint("button")
        c.create_image(x, y, anchor="nw", tags=tags,
                       image=self.rbox(w, h, 14, fill, self._rgba(ACCENT) if on else self._edge()))
        c.create_image(x + 14 * sc, y + h / 2, tags=tags, image=self.rbox(8 * sc, 8 * sc, 3, _hex(self._c(color)) + (255,)))
        self.text(x + 24 * sc, y + h / 2, label, 12, "bold" if on else "normal", ACCENT if on else MUTED, tags=tags,
                  shadow=False)
        return x, y, x + w, y + h

    def _secret(self, x0, x1, y, label, key, value, which, accent_copy):
        c, a, sc = self.canvas, self.app, self._sc()
        strength = key == "pass"
        h = int((92 if strength else 64) * sc)
        c.create_image(x0, y, anchor="nw", tags=("chrome",),
                       image=self.rbox(x1 - x0, h, 12, self._tint("row"), self._edge()))
        self.text(x0 + 14 * sc, y + 18 * sc, label, 11, "bold", SUBTLE, tags=("chrome",))
        shown = Stand(self, "secret-" + key, DOTS, TEXT)
        t = self.text(x0 + 14 * sc, y + 40 * sc, DOTS, 14, "normal", TEXT, width=150 * sc, tags=("chrome",),
                      mono=strength)
        self._stand_items[shown.key] = self._pair(t)
        bx = self.button(x1 - 12 * sc, y + 16 * sc, "Copy", lambda: a.copy(a.sel_id, which),
                         "primary" if accent_copy else "ghost", h=30, w=58, size=12, anchor="ne")[0]
        btn = Stand(self, "btn-" + key, "Show", TEXT)
        self.button(bx - 6 * sc, y + 16 * sc, "Show", lambda: btn.invoke(), "ghost", h=30, w=54, size=12,
                    anchor="ne")
        self._stand_items[btn.key] = self._last_label

        def flip():
            a._revealed[key] = not a._revealed[key]
            shown.configure(text=value if a._revealed[key] else DOTS)
            btn.configure(text="Hide" if a._revealed[key] else "Show")
            if a._revealed[key]:
                a.reveal_deadline = time.time() + REVEAL_SECONDS
                a.revealed_id = a.sel_id
        btn.command = flip
        a._secret_widgets[key] = (shown, btn)
        if strength:
            score, _ = password_strength(value)
            ty = y + h - int(20 * sc)
            tw = x1 - x0 - int(28 * sc) - int(90 * sc)
            c.create_image(x0 + 14 * sc, ty, anchor="w", tags=("chrome",),
                           image=self.rbox(tw, 8 * sc, 4, self._rgba(TRACK)))
            c.create_image(x0 + 14 * sc, ty, anchor="w", tags=("chrome",),
                           image=self.rbox(max(8 * sc, tw * max(score, 1) / 4), 8 * sc, 4,
                                           self._rgba(STRENGTH_COLORS[score])))
            self.text(x1 - 14 * sc, ty, STRENGTH_LABELS[score], 12, "bold", STRENGTH_COLORS[score], anchor="e",
                      tags=("chrome",))
        return y + h


class HushKeyApp(ctk.CTk):
    def __init__(self, data_dir: str | None = None, cloud: Cloud | None = None, updater=None):
        self.data_dir = data_dir
        self.settings = load_settings(data_dir)
        theme = self.settings.get("theme", "dark")
        ctk.set_appearance_mode(theme if theme in ("light", "dark") else "system")
        apply_accent(self.settings.get("accent", "green"))
        global STYLE
        STYLE = "pixel" if self.settings.get("style") == "pixel" else "basic"
        super().__init__(fg_color=BG)
        load_fonts(self, self.settings.get("font", "poppins"))
        self.title(APP_NAME)
        self.minsize(880, 640)
        self._place_window()
        set_window_icon(self)

        self.cloud = cloud or Cloud()
        self.syncer = None
        self._last_session = None   # the latest email-code sign-in, used to turn on sync
        self._sync_job = None
        self._sync_busy = False
        self._sync_again = False
        self._sync_blocked = False
        self._last_auto_sync = time.time()
        self.updater = updater if updater is not None else updater_mod.Updater()
        self.update_release = None   # newer version found on GitHub
        self.update_file = None      # its downloaded, verified installer
        self.update_error = ""
        self._installing = False
        self.vault: Vault | None = None
        self.last_email = ""
        self.failed = 0
        self.wait_until = 0.0
        self.last_activity = time.time()
        self.revealed_id = None
        self.reveal_deadline = 0.0
        self.clip = None
        self.screen = 0           # bumps every screen change; stale callbacks are ignored
        self._jobs = queue.Queue()
        self.rows = {}
        self.art = None
        self.glass = None
        self.remember_var = None
        self.view, self.sel_id = "all", None
        self._new_vault = False
        self.leak_checker = leakcheck.leaked_ids

        self.body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.body.pack(fill="both", expand=True)

        for ev in ("<Any-KeyPress>", "<Any-ButtonPress>", "<Motion>"):
            self.bind_all(ev, self._touch, add="+")
        self.bind_all("<Button-1>", self._click_anywhere, add="+")
        self._geo_job = None
        self.bind("<Configure>", self._window_moved, add="+")
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.after(60, self._poll_jobs)
        self.after(1000, self._tick)
        # load the logo list in the background so the first search is instant
        threading.Thread(target=brand_icons.load, daemon=True).start()

        # first time opening a new version? say so on the sign-in screen
        seen = self.settings.get("last_version")
        notice = f"HushKey was updated to v{__version__}." if seen and seen != __version__ else ""
        if seen != __version__:
            self.settings["last_version"] = __version__
            save_settings(self.settings, self.data_dir)
        self.stay_var = None
        self._try_auto_signin(notice)
        if self.updater is not None and self.updater.enabled:
            self.after(1500, self.check_for_update)

    # ------------------------------------------------------------ window position

    def _place_window(self):
        """First launch: 1000x700 in the middle of the screen. After that:
        exactly where (and how big) it was when you last closed it."""
        import re
        w, h = 1000, 700
        saved = self.settings.get("window") or ""
        m = re.fullmatch(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", saved)
        try:
            self.update_idletasks()
            sw = max(self.winfo_screenwidth(), self.winfo_vrootwidth())
            sh = max(self.winfo_screenheight(), self.winfo_vrootheight())
            scale = self._get_window_scaling() if hasattr(self, "_get_window_scaling") else 1.0
        except Exception:
            sw, sh, scale = 1920, 1080, 1.0
        if m:
            sw_, sh_, sx, sy = (int(v) for v in m.groups())
            w, h = max(880, min(sw_, int(sw / scale))), max(640, min(sh_, int(sh / scale)))
            # only reuse the spot if the window would still be on screen
            if -int(w * scale) + 120 < sx < sw - 120 and 0 <= sy < sh - 80:
                self.geometry(f"{w}x{h}+{sx}+{sy}")
                if self.settings.get("window_zoomed") and IS_WIN:
                    self.after(50, lambda: self.state("zoomed"))
                return
        x = max(0, int((self.winfo_screenwidth() - w * scale) / 2))
        y = max(0, int((self.winfo_screenheight() - h * scale) / 2.2))
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _window_moved(self, event=None):
        if event is not None and event.widget is not self:
            return
        if self._geo_job is not None:
            try:
                self.after_cancel(self._geo_job)
            except Exception:
                pass
        self._geo_job = self.after(800, self._save_window)

    def _save_window(self):
        self._geo_job = None
        try:
            zoomed = IS_WIN and self.state() == "zoomed"
            if not zoomed:
                self.settings["window"] = self.geometry()
            self.settings["window_zoomed"] = bool(zoomed)
            save_settings(self.settings, self.data_dir)
        except Exception:
            pass

    # ------------------------------------------------------------ stay signed in

    def _key_folder(self):
        from vault import default_data_dir
        return self.data_dir or default_data_dir()

    def _try_auto_signin(self, notice=""):
        """If this computer is remembered, open the vault without asking for
        the master password (until the 30 days are up or the user signs out)."""
        addr = self.settings.get("auto_signin_email")
        if not addr:
            return self.show_signin(notice, ok=True)
        v = self._vault_for(addr)
        key = device_lock.load(addr, self._key_folder())
        try:
            if key is None or not v.exists():
                raise VaultError("This computer isn't remembered anymore. Please sign in.")
            v.unlock_with_device_key(key)
        except VaultError as exc:
            self._forget_auto_signin(addr)
            self.last_email = addr
            return self.show_signin((notice + " " if notice else "") + str(exc), ok=False)
        self._enter(v, addr, full=False)
        self._status(text=(notice + " " if notice else "") + "Signed in automatically.",
                              text_color=ACCENT)

    def _remember_device(self, v: Vault, addr: str):
        """'Remember this device for 30 days': skip email codes AND stay
        signed in when the app is closed and opened again."""
        try:
            v.remember_device()
            key = v.enable_auto_signin()
            device_lock.save(addr, key, self._key_folder())
            self.settings["auto_signin_email"] = addr
            save_settings(self.settings, self.data_dir)
        except Exception:
            traceback.print_exc()
            try:
                v.disable_auto_signin()
            except Exception:
                pass

    def _forget_auto_signin(self, addr):
        device_lock.delete(addr, self._key_folder())
        if self.settings.get("auto_signin_email") == addr:
            self.settings.pop("auto_signin_email", None)
            save_settings(self.settings, self.data_dir)

    # ------------------------------------------------------------ theme

    @property
    def is_dark(self):
        return ctk.get_appearance_mode().lower() == "dark"

    def toggle_theme(self):
        new = "light" if self.is_dark else "dark"
        ctk.set_appearance_mode(new)
        self.settings["theme"] = new
        save_settings(self.settings, self.data_dir)

    def theme_switch(self, parent):
        """The key switch: slide the key to turn the lights on or off."""
        return ctk.CTkButton(parent, text="", image=key_switch_image(), width=76, height=38,
                             fg_color="transparent", hover=False, command=self.toggle_theme)

    # ---------------------------------------------------------------- helpers

    # ---------------------------------------------------------------- smooth transitions

    @property
    def animate(self):
        return self.settings.get("animations", True) and not getattr(self, "_testing", False)

    def glide(self, steps, apply, done=None, ms=12):
        """Run a short animation: apply(t) for t from 0 to 1 with an ease-out curve.
        About 100 ms in total, so it feels quick and never holds anything up."""
        if not self.animate:
            apply(1.0)
            return done() if done else None
        token = object()
        self._glide_token = getattr(self, "_glide_token", {})

        def step(i=1):
            t = i / steps
            try:
                apply(1 - (1 - t) ** 3)
            except Exception:
                return
            if i < steps:
                self.after(ms, lambda: step(i + 1))
            elif done:
                done()
        step()
        return token

    def _fade_in(self):
        """The new screen fades in quickly instead of popping in."""
        if not self.animate or getattr(self, "_no_fade", False):
            return
        try:
            self.attributes("-alpha", 0.9)
        except Exception:
            return
        self.after(20, lambda: self.glide(5, lambda t: self.attributes("-alpha", 1.0 if t >= 1 else 0.9 + 0.1 * t),
                                          ms=16))

    def _clear(self):
        if not (self.vault and self.vault.is_unlocked):
            self._fade_in()   # only for sign-in and lock screens: inside the vault, screens switch instantly
        self.screen += 1
        self.rows = {}
        self.revealed_id = None
        self._secret_widgets = {}
        self._on_security = False
        self._settings_body = None
        self._settings_shell = None
        self._painters = None
        self._preview_lbl = None
        self.listbox = None
        self.art = None
        self.glass = None
        old = self.body.winfo_children()
        for w in old:   # take the old screen off first, so Tk doesn't re-lay it out piece by piece
            w.pack_forget()
            w.place_forget()
        # ...and delete it after the new screen is up, a little at a time, so the click feels instant
        self._throw_away(old)

    def _throw_away(self, widgets):
        """Delete a screen that's already hidden in small slices (a big page can take a few tenths
        of a second to delete in one go), starting once the new screen has been drawn."""
        queue = []
        for w in widgets:
            queue += [c for c in w.winfo_children() if isinstance(c, ctk.CTkBaseClass)]
            queue.append(w)

        def step():
            end = time.perf_counter() + 0.012
            while queue and time.perf_counter() < end:
                w = queue.pop(0)
                try:
                    if w.winfo_exists():
                        w.destroy()
                except Exception:
                    pass
            if queue:
                self.after(15, step)
        self.after(80, lambda: self.after_idle(step))

    def _card(self, width=440):
        picture = self._signin_backdrop()
        # over a picture the box has square corners, so no plain-colored corners show around it
        card = ctk.CTkFrame(self.body, width=width, fg_color=SURFACE, corner_radius=0 if picture else 18,
                            border_width=1, border_color=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center")
        if not picture:
            self.theme_switch(self.body).place(relx=1.0, x=-24, y=20, anchor="ne")
        inner = ctk.CTkFrame(card, fg_color="transparent", width=width - 64)
        inner.pack(padx=32, pady=30, fill="both")
        return inner

    def _signin_backdrop(self):
        """The background picture behind the sign-in box, only if turned on in Settings."""
        key = self.settings.get("background", "none")
        if not self.settings.get("bg_signin", False) or key == "none" or background_source(key) is None:
            return False
        import tkinter as tk
        from PIL import ImageTk
        lbl = tk.Label(self.body, bd=0, highlightthickness=0, bg=BG[1] if self.is_dark else BG[0])
        lbl.place(x=0, y=0, relwidth=1, relheight=1)
        lbl._job = None

        def paint():
            lbl._job = None
            if not lbl.winfo_exists():
                return
            w, h = lbl.winfo_width(), lbl.winfo_height()
            pic = background_picture(key, w, h, self.settings.get("bg_dim", "medium"), self.is_dark)
            if pic is not None:
                lbl.image = ImageTk.PhotoImage(pic, master=lbl)
                lbl.configure(image=lbl.image)

        def resized(_e=None):
            if lbl._job:
                lbl.after_cancel(lbl._job)
            lbl._job = lbl.after(80, paint)
        lbl.bind("<Configure>", resized)
        return True

    def _brand_header(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(pady=(0, 14))
        ctk.CTkLabel(top, text="", image=logo_image(44)).pack(side="left", padx=(0, 10))
        wordmark(top, 28).pack(side="left")

    def _heading(self, parent, title, subtitle="", step=""):
        if step:
            ctk.CTkLabel(parent, text=step.upper(), font=font(12, "bold"), text_color=ACCENT,
                         anchor="w").pack(fill="x")
        ctk.CTkLabel(parent, text=title, font=font(24, "bold"), text_color=TEXT, anchor="w",
                     justify="left", wraplength=380).pack(fill="x", pady=(4, 0))
        if subtitle:
            ctk.CTkLabel(parent, text=subtitle, font=font(14), text_color=MUTED, anchor="w",
                         justify="left", wraplength=376).pack(fill="x", pady=(6, 0))

    def _message(self, parent):
        lbl = ctk.CTkLabel(parent, text="", font=font(13), text_color=DANGER, anchor="w",
                           justify="left", wraplength=376)
        lbl.pack(fill="x", pady=(10, 0))

        def say(text, ok=False):
            if lbl.winfo_exists():
                lbl.configure(text=text, text_color=ACCENT if ok else DANGER)
        return say

    def _button_row(self, parent, cancel_cmd, ok_text, ok_cmd, cancel_text="Cancel"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(18, 0))
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=2)
        ghost_button(row, cancel_text, cancel_cmd).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ok = primary_button(row, ok_text, ok_cmd)
        ok.grid(row=0, column=1, sticky="ew")
        return ok

    def run_bg(self, work, on_ok, on_err, busy_button=None, busy_text="Working…"):
        """Run slow work (network, hashing) off the main thread so the window
        never freezes. Results come back through a queue the UI checks."""
        token = self.screen
        old_text = None
        if busy_button is not None:
            old_text = busy_button.cget("text")
            busy_button.configure(state="disabled", text=busy_text)

        def finish(cb, value):
            if token != self.screen:
                return  # user moved on (e.g. pressed Cancel); ignore
            if busy_button is not None and busy_button.winfo_exists():
                busy_button.configure(state="normal", text=old_text)
            cb(value)

        def worker():
            try:
                result = work()
                self._jobs.put((finish, on_ok, result))
            except Exception as exc:  # noqa: BLE001 - shown to the user
                self._jobs.put((finish, on_err, exc))

        threading.Thread(target=worker, daemon=True).start()

    def run_quiet(self, work, on_ok=None, on_err=None):
        """Background work that should finish even if the screen changes
        (syncing, update checks)."""
        def finish(cb, value):
            if cb is not None and self.winfo_exists():
                cb(value)

        def worker():
            try:
                result = work()
                self._jobs.put((finish, on_ok, result))
            except Exception as exc:  # noqa: BLE001
                self._jobs.put((finish, on_err, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_jobs(self):
        try:
            while True:
                finish, cb, value = self._jobs.get_nowait()
                finish(cb, value)
        except queue.Empty:
            pass
        self.after(60, self._poll_jobs)

    def _touch(self, _e=None):
        self.last_activity = time.time()

    def _tick(self):
        limit = int(self.settings.get("lock_after", DEFAULT_LOCK_SECONDS))
        if limit and self.vault and self.vault.is_unlocked and time.time() - self.last_activity > limit:
            label = next((t for s_, t in LOCK_CHOICES if s_ == limit), f"{limit // 60} min")
            self.lock_app(f"Locked after {label.replace('min', 'minutes') if label != '1 min' else '1 minute'}"
                          " of no activity.")
        if (self.vault and self.vault.is_unlocked and self.syncer is not None
                and time.time() - self._last_auto_sync > 60):
            self._last_auto_sync = time.time()
            self.request_sync(delay=0)   # pick up changes made on your other computers
        if self.revealed_id and time.time() > self.reveal_deadline:
            self.hide_revealed()   # a shown username/password hides itself again
        self.after(1000, self._tick)

    @staticmethod
    def _err_text(exc):
        if isinstance(exc, (VaultError, CloudError)):
            return str(exc)
        traceback.print_exception(exc)
        return "Something unexpected went wrong. Please try again."

    def _vault_for(self, email):
        return Vault(email, self.data_dir)

    # =============================================================== SIGN IN

    def show_signin(self, notice="", ok=False):
        self._clear()
        c = self._card()
        self._brand_header(c)
        ctk.CTkLabel(c, text="Welcome back", font=font(22, "bold"), text_color=TEXT).pack()
        ctk.CTkLabel(c, text="Sign in to unlock your vault", font=font(14), text_color=MUTED).pack(pady=(4, 18))

        field_label(c, "Email").pack(fill="x")
        email = entry(c, "you@example.com")
        email.pack(fill="x", pady=(6, 12))
        if self.last_email:
            email.insert(0, self.last_email)

        field_label(c, "Master password").pack(fill="x")
        pw = PasswordField(c, "Your master password")
        pw.pack(fill="x", pady=(6, 4))

        link_row = ctk.CTkFrame(c, fg_color="transparent")
        link_row.pack(fill="x")
        link_button(link_row, "Forgot master password?",
                    lambda: self.show_forgot_email(email.get())).pack(side="right")

        stay_box, self.stay_var = checkbox(c, "Remember this device for 30 days", checked=False)
        stay_box.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(c, text="Stay signed in when you close HushKey. Clicking Sign out turns it off.",
                     font=font(11), text_color=SUBTLE, anchor="w").pack(fill="x", padx=(30, 0))

        say = self._message(c)
        if notice:
            say(notice, ok)

        def submit(_e=None):
            addr = normalize_email(email.get())
            if not looks_like_email(addr):
                return say("Enter the email you signed up with.")
            if not pw.get():
                return say("Enter your master password.")
            wait = self.wait_until - time.time()
            if wait > 0:
                return say(f"Too many tries. Wait {int(wait) + 1}s and try again.")
            v = self._vault_for(addr)
            stay = bool(self.stay_var is not None and self.stay_var.get())
            if not v.exists():
                if self.cloud.configured:
                    return self._sign_in_new_computer(addr, pw.get(), say, unlock_btn, stay)
                return say("There's no HushKey vault for this email on this computer. "
                           "Check the spelling, or create a vault.")

            def ok_cb(_):
                self.failed = 0
                self.last_email = addr
                self._after_password(v, addr, say, unlock_btn,
                                     stay=bool(self.stay_var is not None and self.stay_var.get()))

            def err_cb(exc):
                if isinstance(exc, WrongPassword):
                    self.failed += 1
                    delay = min(60, 2 ** self.failed) if self.failed >= 3 else 0
                    self.wait_until = time.time() + delay
                    pw.set("")
                    hint = (" Changed it on another computer? Use your old password here once; "
                            "it updates after syncing.") if self.cloud.configured and self.failed == 1 else ""
                    say("Wrong email or master password." + (f" Wait {delay}s before trying again." if delay else "")
                        + hint)
                else:
                    say(self._err_text(exc))

            typed = pw.get()
            self.run_bg(lambda: v.unlock(typed), ok_cb, err_cb, unlock_btn, "Unlocking…")

        unlock_btn = primary_button(c, "Unlock vault", submit)
        unlock_btn.pack(fill="x", pady=(16, 0))
        email.bind("<Return>", submit)
        pw.bind_enter(submit)

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(pady=(14, 0))
        ctk.CTkLabel(row, text="New here?", font=font(13), text_color=MUTED).pack(side="left")
        link_button(row, "Create a vault", self.show_create).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(c, text="Encrypted on this device. Your master password never leaves it.",
                     font=font(12), text_color=SUBTLE).pack(pady=(14, 0))
        ctk.CTkLabel(c, text=f"v{__version__}", font=font(11), text_color=SUBTLE).pack(pady=(4, 0))
        self._update_slot = ctk.CTkFrame(c, fg_color="transparent", width=1, height=1)
        self._update_slot.pack()
        self._show_update_link()
        (pw.focus() if self.last_email else email.focus_set())

    def _after_password(self, v: Vault, addr: str, say, button, stay=False):
        """Right password. On a computer that isn't remembered, also ask for
        a code sent to the user's email (two-step sign-in)."""
        if not self.cloud.configured or v.is_device_remembered():
            if stay:
                self._remember_device(v, addr)
            return self._enter(v, addr)

        def cancel():
            v.lock()
            self.show_signin()

        def done(_):
            if self.remember_var is not None and self.remember_var.get():
                self._remember_device(v, addr)
            self._enter(v, addr)

        def failed(exc):
            v.lock()
            say(self._err_text(exc))

        self.run_bg(lambda: self.cloud.send_code(addr),
                    lambda _: self.show_code(
                        addr, "Enter your sign-in code",
                        "This computer isn't remembered yet, so we emailed you a 8-digit code.",
                        # a correct code also switches on email recovery for older vaults
                        on_verified=lambda s: (lambda: self._ensure_recovery(v, s)),
                        on_done=done, on_cancel=cancel, remember=True, remember_default=stay),
                    failed, button, "Sending code…")

    def _sign_in_new_computer(self, addr, master, say, button, stay):
        """No vault on this computer yet: after an 8-digit email code, download
        the encrypted vault from your account and open it with your master
        password. Nothing readable ever comes from the server."""
        syncer = Syncer(self.cloud, addr, self._key_folder())

        def fetch_and_open(session):
            def work():
                data = syncer.download_for_new_computer(session)
                v = Vault.save_cloud_copy(addr, self.data_dir, data)
                try:
                    v.unlock(master)
                except VaultError:
                    for path in (v.path, v.backup_path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass
                    syncer.forget()
                    return None
                return v
            return work

        def done(v):
            if v is None:
                return self.show_signin("That master password doesn't match the vault in your HushKey "
                                        "account. Check it and try again.")
            if self.remember_var is not None and self.remember_var.get():
                self._remember_device(v, addr)
            self._enter(v, addr)
            self._status(text="Welcome! Your vault was brought over from your other computer "
                                       "and is now synced.", text_color=ACCENT)

        self.run_bg(lambda: self.cloud.send_code(addr),
                    lambda _: self.show_code(
                        addr, "Sign in on this computer",
                        "To bring your vault to this computer, we emailed you an 8-digit code.",
                        on_verified=fetch_and_open, on_done=done, on_cancel=self.show_signin,
                        done_text="Bringing your vault…", remember=True, remember_default=stay),
                    lambda exc: say(self._err_text(exc)), button, "Sending code…")

    def _ensure_recovery(self, v: Vault, session):
        """Give a vault made before email was set up its recovery key.
        Runs in the background, right after the user proved their email."""
        if self.cloud.configured and v.is_unlocked and not v.has_recovery:
            secret = new_recovery_secret()
            self.cloud.store_secret(session, v.vault_id, secret)  # online first...
            v.enable_recovery(secret)                             # ...then the vault

    def turn_on_recovery(self):
        """Turn on sync (and email recovery, if it's off) with an 8-digit code."""
        v, addr = self.vault, self.vault.email

        def done(_):
            self._sync_blocked = False
            # Keep the sign-in from the code so sync actually stays on.
            # (v2.0.9 forgot this, so the "Turn on sync" banner never went away.)
            if self.syncer is not None and self._last_session and self._last_session[0] == addr:
                try:
                    self.syncer.remember_session(self._last_session[1])
                except Exception:
                    traceback.print_exc()
            self._last_session = None
            self.show_main()
            if self.syncer is not None:
                self.request_sync(delay=300)
            self._status(text="Sync and email recovery are on. Sign in on any computer with "
                                       "your email and master password.", text_color=ACCENT)

        self.run_bg(lambda: self.cloud.send_code(addr),
                    lambda _: self.show_code(
                        addr, "Turn on sync",
                        "We emailed you an 8-digit code to confirm it's your email.",
                        on_verified=lambda s: (lambda: self._ensure_recovery(v, s)),
                        on_done=done, on_cancel=self.show_main, done_text="Turning on…"),
                    lambda exc: self._status(text=self._err_text(exc), text_color=DANGER),
                    self.recovery_btn, "Sending code…")

    # ------------------------------------------------------------ sync

    def request_sync(self, delay=1500):
        """Sync soon (changes are grouped, so typing fast doesn't spam the server)."""
        if self.syncer is None or self._sync_blocked:
            return
        if self._sync_job is not None:
            try:
                self.after_cancel(self._sync_job)
            except Exception:
                pass
        self._sync_job = self.after(delay, self._sync_now)

    def _sync_now(self):
        self._sync_job = None
        syncer, v = self.syncer, self.vault
        if syncer is None or v is None or not v.is_unlocked or self._sync_blocked:
            return
        if self._sync_busy:
            self._sync_again = True
            return
        if not syncer.enabled and syncer._session is None:
            syncer.state = "off"
            return self._show_sync_state()
        self._sync_busy = True
        syncer.state = "syncing"
        self._show_sync_state()

        def fetched(row):
            if self.vault is not v or not v.is_unlocked:
                return self._sync_finished()
            before = id(v._data)
            try:
                plan = syncer.reconcile(v, row)
            except VaultMismatch as exc:
                self._sync_finished("mismatch")
                return CombineDialog(self, exc.cloud_data)
            except TamperError as exc:
                return self._sync_finished("error", str(exc))
            if v.this_computer_removed():
                return self._computer_removed()
            if id(v._data) != before and hasattr(self, "listbox") and self.listbox.winfo_exists():
                self.refresh_rows()   # changes arrived from another computer
            self.run_quiet(lambda: syncer.upload(plan), lambda _: self._sync_finished("ok"), failed)

        def failed(exc):
            if isinstance(exc, SessionExpired):
                self._sync_finished("paused")
            elif isinstance(exc, CloudError):
                self._sync_finished("offline")
            else:
                traceback.print_exception(exc)
                self._sync_finished("error", "Sync hit a problem. It will try again.")

        self.run_quiet(syncer.fetch, fetched, failed)

    def _computer_removed(self):
        """Another of your computers removed this one: sign out and delete the copy here.
        Your vault is safe in your account; sign in again any time with your email."""
        v, addr = self.vault, self.vault.email
        self._sync_busy = False
        try:
            if self.syncer is not None:
                self.syncer.forget()
            v.disable_auto_signin()
        except Exception:
            traceback.print_exc()
        self._forget_auto_signin(addr)
        v.delete_local_copy()
        self.vault, self.syncer = None, None
        self.last_email = addr
        self.show_signin("This computer was removed from your HushKey account on another computer, so the "
                         "copy here was deleted. To use it again, sign in with your email and master password.")

    def _sync_finished(self, state=None, message=""):
        self._sync_busy = False
        if self.syncer is not None and state:
            self.syncer.state = state
        if state == "mismatch":
            self._sync_blocked = True
        self._show_sync_state(message)
        if self._sync_again:
            self._sync_again = False
            self.request_sync(delay=200)

    def _show_sync_state(self, message=""):
        label = getattr(self, "sync_label", None)
        if label is None or not label.winfo_exists() or self.syncer is None:
            return
        state = self.syncer.state
        colors = {"ok": ACCENT, "syncing": SUBTLE, "offline": GOLD, "paused": GOLD, "error": DANGER}
        text = self.syncer.status_text()
        if state == "paused":
            text = "Sync paused: click to confirm your email"
        elif state == "mismatch":
            text = "Sync off: two different vaults"
        label.configure(text=text, text_color=colors.get(state, SUBTLE))
        if message and getattr(self, "status", None) is not None and self.status.winfo_exists():
            self._status(text=message, text_color=DANGER if state == "error" else MUTED)

    def _sync_label_clicked(self, _e=None):
        if self.syncer is not None and self.syncer.state in ("paused", "off"):
            self.turn_on_recovery()
        elif self.syncer is not None and self.syncer.state == "mismatch":
            self._sync_blocked = False
            self.request_sync(delay=0)

    # ========================================================= CREATE VAULT

    def show_create(self):
        self._clear()
        c = self._card()
        recovery_on = self.cloud.configured
        self._heading(c, "Create your vault",
                      "Your email is how you sign in and how you recover your vault "
                      "if you ever forget your master password." if recovery_on else
                      "Heads up: email recovery isn't set up in this copy of HushKey, "
                      "so a forgotten master password can't be recovered.")

        field_label(c, "Email").pack(fill="x", pady=(18, 0))
        email = entry(c, "you@example.com")
        email.pack(fill="x", pady=(6, 12))

        field_label(c, f"Master password (at least {MIN_MASTER_LENGTH} characters)").pack(fill="x")
        pw = PasswordField(c, "Something long you'll remember", visible=True)
        pw.pack(fill="x", pady=(6, 6))
        bar = StrengthBar(c)
        bar.pack(fill="x", pady=(0, 12))
        pw.bind_key(lambda _e: bar.update_for(pw.get()))

        field_label(c, "Retype it (hidden, from memory)").pack(fill="x")
        confirm = PasswordField(c, "Type it again", toggle=False)
        confirm.pack(fill="x", pady=(6, 0))

        say = self._message(c)

        def submit(_e=None):
            addr = normalize_email(email.get())
            if not looks_like_email(addr):
                return say("Enter a real email address. You'll need it to recover your vault.")
            try:
                check_new_master(pw.get(), confirm.get())
            except VaultError as exc:
                return say(str(exc))
            v = self._vault_for(addr)
            if v.exists():
                return say("There's already a vault for this email on this computer. Sign in instead.")
            master = pw.get()

            if not recovery_on:
                self.run_bg(lambda: v.create(master), lambda _: (setattr(self, "_new_vault", True),
                                                                 self._enter(v, addr)),
                            lambda exc: say(self._err_text(exc)), go, "Creating…")
                return

            def after_code(session):
                secret, vid = new_recovery_secret(), new_vault_id()

                def work():
                    self.cloud.store_secret(session, vid, secret)  # online first...
                    v.create(master, secret, vid)                   # ...then the local vault
                return work

            def done(_):
                if self.remember_var is not None and self.remember_var.get():
                    self._remember_device(v, addr)
                self._new_vault = True
                self._enter(v, addr)

            self.run_bg(lambda: self.cloud.send_code(addr),
                        lambda _: self.show_code(
                            addr, "Confirm your email",
                            "We sent a welcome email with your 8-digit sign-up code.",
                            on_verified=after_code, on_done=done,
                            on_cancel=self.show_create, done_text="Creating your vault…",
                            remember=True),
                        lambda exc: say(self._err_text(exc)), go, "Sending code…")

        go = self._button_row(c, self.show_signin, "Continue" if recovery_on else "Create vault", submit)
        email.bind("<Return>", submit)
        confirm.bind_enter(submit)
        email.focus_set()

    def _enter(self, v: Vault, addr: str, full=True):
        if self.vault is not v:
            self.view, self.sel_id = "all", None
            self._leaked_hashes, self._leak_done, self._leak_checked = set(), False, 0
        self.vault = v
        self.last_email = addr
        self.syncer = None
        if self.cloud.configured:
            self.syncer = Syncer(self.cloud, addr, self._key_folder())
            if self._last_session and self._last_session[0] == addr:
                try:
                    self.syncer.remember_session(self._last_session[1])
                except Exception:
                    traceback.print_exc()
            self._last_session = None
            v.on_change = self.request_sync
        try:
            v.touch_computer(signed_in=full)   # for the list in Settings > Sync & devices
        except Exception:
            traceback.print_exc()
        self.show_main()
        if not getattr(self, "_thumbs_warm", False):   # so Settings > Appearance opens quickly
            self._thumbs_warm = True
            self.after(1500, lambda: self.run_quiet(warm_background_thumbs))
        if self.syncer is not None:
            self.request_sync(delay=300)
        self.after(2500, self.start_leak_check)

    # ============================================================ CODE SCREEN

    def show_code(self, addr, title, intro, on_verified, on_done, on_cancel,
                  done_text="Checking…", step="", remember=False, remember_default=True):
        """Shared 'enter the 8-digit code' screen.

        The code is checked by the email service: it must be the exact code
        sent to this email, it works once, and it expires after 10 minutes.
        on_verified(session) returns a function to run in the background after
        a correct code (e.g. download the recovery secret); on_done gets its result.
        """
        self._clear()
        c = self._card()
        self._heading(c, title, f"{intro} It was sent to {addr}. "
                                "Check your spam folder if you don't see it.", step)

        field_label(c, "8-digit code from the email").pack(fill="x", pady=(18, 0))
        code = ctk.CTkEntry(c, placeholder_text="12345678", width=FIELD_WIDTH, height=60, corner_radius=10,
                            fg_color=BG, border_color=BORDER, text_color=TEXT,
                            placeholder_text_color=SUBTLE, justify="center", font=font(28, "bold", mono=True))
        code.pack(fill="x", pady=(6, 6))

        self.remember_var = None
        if remember:
            box, self.remember_var = checkbox(c, f"Remember this device for {REMEMBER_DAYS} days "
                                                 "(stay signed in)", checked=remember_default)
            box.pack(fill="x", pady=(6, 4))

        resend_row = ctk.CTkFrame(c, fg_color="transparent")
        resend_row.pack(fill="x")
        ctk.CTkLabel(resend_row, text="Didn't get it?", font=font(13), text_color=MUTED).pack(side="left")

        say = self._message(c)

        def resend():
            self.run_bg(lambda: self.cloud.send_code(addr), lambda _: say("New code sent.", ok=True),
                        lambda exc: say(self._err_text(exc)))
        link_button(resend_row, "Resend code", resend).pack(side="left", padx=(4, 0))

        def submit(_e=None):
            typed = code.get()

            def work():
                session = self.cloud.verify_code(addr, typed)
                self._last_session = (addr, session)   # used to turn on sync
                return on_verified(session)()

            def wrong(exc):
                code.delete(0, "end")
                say(self._err_text(exc))

            self.run_bg(work, on_done, wrong, verify, done_text)

        verify = self._button_row(c, on_cancel, "Verify code", submit)
        code.bind("<Return>", submit)
        code.focus_set()

    # ======================================================= FORGOT PASSWORD

    def show_forgot_email(self, prefill=""):
        self._clear()
        c = self._card()
        self._heading(c, "Forgot your master password?",
                      "Enter the email you signed up with. We'll send a code to that email only.",
                      "Step 1 of 3")
        field_label(c, "Email").pack(fill="x", pady=(18, 0))
        email = entry(c, "you@example.com")
        email.pack(fill="x", pady=(6, 0))
        if prefill.strip():
            email.insert(0, prefill.strip())
        say = self._message(c)

        def submit(_e=None):
            addr = normalize_email(email.get())
            if not looks_like_email(addr):
                return say("Enter the email you signed up with.")
            v = self._vault_for(addr)
            if not v.exists():
                return say("There's no HushKey vault for this email on this computer.")
            try:
                has = v.has_recovery
            except VaultError as exc:
                return say(str(exc))
            if not has:
                return say("This vault was made before email recovery was set up, so it has no recovery "
                           "key yet. If you remember your master password, sign in once and click "
                           "“Turn on” to switch on email recovery.")
            if not self.cloud.configured:
                return say("Email recovery isn't set up in this copy of HushKey.")

            def got_secret(session):
                return lambda: v.start_recovery(self.cloud.fetch_secret(session, v.vault_id))

            self.run_bg(lambda: self.cloud.send_code(addr),
                        lambda _: self.show_code(
                            addr, "Check your email", "We sent you a 8-digit code.",
                            on_verified=got_secret,
                            on_done=lambda reset: self.show_forgot_new(reset, addr),
                            on_cancel=lambda: self.show_signin(), step="Step 2 of 3"),
                        lambda exc: say(self._err_text(exc)), send, "Sending code…")

        send = self._button_row(c, lambda: self.show_signin(), "Send code", submit)
        email.bind("<Return>", submit)
        email.focus_set()

    def show_forgot_new(self, reset, addr):
        self._clear()
        c = self._card()
        self._heading(c, "Create a new master password",
                      "Type it once where you can see it, then again from memory.", "Step 3 of 3")

        field_label(c, "New master password").pack(fill="x", pady=(18, 0))
        pw = PasswordField(c, f"At least {MIN_MASTER_LENGTH} characters", visible=True)
        pw.pack(fill="x", pady=(6, 6))
        bar = StrengthBar(c)
        bar.pack(fill="x", pady=(0, 12))

        field_label(c, "Retype it (hidden, from memory)").pack(fill="x")
        confirm = PasswordField(c, "Type it again", toggle=False)
        confirm.pack(fill="x", pady=(6, 0))

        match = ctk.CTkLabel(c, text="", font=font(13), anchor="w")
        match.pack(fill="x", pady=(8, 0))

        def on_key(_e=None):
            bar.update_for(pw.get())
            if not confirm.get():
                match.configure(text="")
            elif confirm.get() == pw.get():
                match.configure(text="✓  Passwords match", text_color=ACCENT)
            else:
                match.configure(text="Passwords don't match yet", text_color=MUTED)
        pw.bind_key(on_key)
        confirm.bind_key(on_key)

        say = self._message(c)
        ctk.CTkLabel(c, text="Nothing changes until you click Reset password. "
                             "Cancel and your old master password still works.",
                     font=font(12), text_color=SUBTLE, wraplength=376, justify="left",
                     anchor="w").pack(fill="x", pady=(6, 0))

        def cancel():
            reset.cancel()
            self.show_signin()

        def submit(_e=None):
            try:
                check_new_master(pw.get(), confirm.get())
            except VaultError as exc:
                return say(str(exc))
            new, again = pw.get(), confirm.get()
            self.last_email = addr
            self.run_bg(lambda: reset.complete(new, again),
                        lambda _: self.show_signin("Your master password was reset. "
                                                   "Sign in with your new password.", ok=True),
                        lambda exc: say(self._err_text(exc)), btn, "Resetting…")

        btn = self._button_row(c, cancel, "Reset password", submit)
        confirm.bind_enter(submit)
        pw.focus()

    # ============================================================= MAIN VAULT
    #
    #  [ sidebar ] [ list of logins                ] [ details panel ]
    #   All / Favorites / Folders / Vault health       opens when you click a login,
    #                                                  the arrow hides it again

    TIPS_PAGE = 8    # security tips built at once; "Show more" builds the next ones
    PAGE_SIZE = 50   # logins drawn at once; "Show more" draws the next 50
    BATCH = 10       # logins drawn per step, so the window never freezes

    def _status(self, text="", text_color=None):
        """The small message line under the list (safe on any screen)."""
        lbl = getattr(self, "status", None)
        if lbl is not None and lbl.winfo_exists():
            lbl.configure(text=text, text_color=text_color or MUTED)

    def status_message(self, text, ok=False):
        self._status(text, ACCENT if ok else MUTED)

    def show_main(self):
        self._clear()
        self._touch()
        self.view = getattr(self, "view", "all")
        if self.view.startswith("folder:") and not any(
                f["id"] == self.view[7:] for f in self.vault.folders()):
            self.view = "all"
        self.sel_id = getattr(self, "sel_id", None)
        self._menu = None
        self._toast_frame = None
        self._folder_form = None
        bg = self.settings.get("background", "none")
        if bg == "none" or background_source(bg) is None:
            bg = "none"
        # The vault screen is always drawn on one canvas (with or without a picture). Building it
        # from hundreds of separate widgets made every click take a second or more.
        return self._show_main_glass(bg)

    def _show_main_glass(self, bg):
        """The vault screen, drawn on one canvas, with or without a background picture."""
        g = GlassMain(self.body, self, bg, self.settings.get("bg_dim", "medium"), box_opacity(self.settings))
        g.pack(fill="both", expand=True)
        self.glass = g
        self._layout = self._main = g
        self.art = self.listbox = g.art
        self.search = g.search
        self.search.bind("<KeyRelease>", self._search_typed)
        self._search_job = None
        self.status = g.stands["status"]
        self.sync_label = g.stands["sync"] if self.syncer is not None else None
        self.recovery_btn = g.stands["recovery"]
        self.form_slot = g.form_slot
        self.health_ring = None
        self.profile_btn = "!glass-profile"
        self._update_slot = None
        self.panel = self.rail = self._panel_line = None
        self.update_idletasks()
        self.refresh_rows()
        self._show_sync_state()

    # ---------------------------------------------------------------- sidebar

    def _build_sidebar(self, side):
        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(20, 18))
        ctk.CTkLabel(brand, text="", image=logo_image(38)).pack(side="left", padx=(0, 8))
        wordmark(brand, 21).pack(side="left")
        self.nav_box = ctk.CTkFrame(side, fg_color="transparent")
        self.nav_box.pack(fill="x", padx=12)
        head = ctk.CTkFrame(side, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(18, 2))
        ctk.CTkLabel(head, text="FOLDERS", font=font(11, "bold"), text_color=SUBTLE).pack(side="left", padx=12)
        ctk.CTkButton(head, text="+", width=28, height=26, corner_radius=7, command=self.open_folder_form,
                      fg_color="transparent", hover_color=RAISED, text_color=ACCENT,
                      font=font(18, "bold")).pack(side="right")
        self.folder_box = ctk.CTkFrame(side, fg_color="transparent", width=1, height=1)
        self.folder_box.pack(fill="x", padx=12)
        self.form_slot = ctk.CTkFrame(side, fg_color="transparent", width=1, height=1)
        self.form_slot.pack(fill="x", padx=12)

        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=12, pady=(0, 14))
        self.health_card = ctk.CTkFrame(bottom, fg_color=SURFACE, corner_radius=14, border_width=1,
                                        border_color=BORDER, cursor="hand2")
        self.health_card.pack(fill="x")
        self.sync_label = None
        if self.syncer is not None:
            self.sync_label = ctk.CTkLabel(bottom, text="", font=font(12), text_color=SUBTLE,
                                           anchor="w", cursor="hand2")
            self.sync_label.pack(fill="x", padx=8, pady=(8, 0))
            self.sync_label.bind("<Button-1>", self._sync_label_clicked)
        self.health_ring = ctk.CTkLabel(self.health_card, text="", width=58, height=58, font=font(16, "bold"),
                                        text_color=TEXT, compound="center")
        self.health_ring.pack(side="left", padx=(10, 10), pady=10)
        words = ctk.CTkFrame(self.health_card, fg_color="transparent")
        words.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(words, text="Vault Health", font=font(13, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
        self.health_line = ctk.CTkLabel(words, text="", font=font(12), text_color=MUTED, anchor="w")
        self.health_line.pack(fill="x")
        self.health_tips = ctk.CTkLabel(words, text="", font=font(11), text_color=SUBTLE, anchor="w")
        self.health_tips.pack(fill="x")
        for w in (self.health_card, self.health_ring, words, self.health_line, self.health_tips,
                  *words.winfo_children()):
            w.bind("<Button-1>", lambda _e: self.show_security())

    def _nav_button(self, parent, text, count, on, cmd, dot=None, icon=""):
        row = ctk.CTkFrame(parent, fg_color=ACCENT_SOFT if on else "transparent", corner_radius=10,
                           height=38, cursor="hand2")
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)
        if dot:
            ctk.CTkFrame(row, width=10, height=10, corner_radius=3, fg_color=dot).pack(side="left", padx=(14, 10))
        elif icon == "★":
            ctk.CTkLabel(row, text="", image=star_image(True, 15), width=18).pack(side="left", padx=(10, 8))
        else:
            ctk.CTkFrame(row, width=12, height=12, corner_radius=3, fg_color=ACCENT if on else SUBTLE).pack(
                side="left", padx=(13, 11))
        name = ctk.CTkLabel(row, text=text, font=font(14 if not dot else 13, "bold" if on else "normal"),
                            text_color=ACCENT if on else TEXT, anchor="w")
        name.pack(side="left", fill="x", expand=True)
        num = ctk.CTkLabel(row, text=str(count), font=font(12), text_color=SUBTLE)
        num.pack(side="right", padx=12)
        for w in (row, name, num, *row.winfo_children()):
            w.bind("<Button-1>", lambda _e: cmd())
        return row

    def _draw_nav(self, entries):
        if self.glass is not None:
            return
        for box in (self.nav_box, self.folder_box):
            for w in box.winfo_children():
                w.destroy()
        favs = sum(1 for e in entries if e["fav"])
        self._nav_button(self.nav_box, "All Logins", len(entries), self.view == "all",
                         lambda: self.set_view("all"), icon="▦")
        self._nav_button(self.nav_box, "Favorites", favs, self.view == "favorites",
                         lambda: self.set_view("favorites"), icon="★")
        counts = {}
        for e in entries:
            if e["folder"]:
                counts[e["folder"]] = counts.get(e["folder"], 0) + 1
        for f in self.vault.folders():
            self._nav_button(self.folder_box, f["name"], counts.get(f["id"], 0),
                             self.view == "folder:" + f["id"],
                             lambda fid=f["id"]: self.set_view("folder:" + fid), dot=f.get("color") or ACCENT)
        if not self.vault.folders() and self._folder_form is None:
            ctk.CTkLabel(self.folder_box, text="Click + to make a folder", font=font(12),
                         text_color=SUBTLE, anchor="w").pack(fill="x", padx=12, pady=(2, 0))

    def set_view(self, view):
        self.view = view
        self._close_menu()
        if self.search.get():
            self.search.delete(0, "end")
        self.refresh_rows()

    FOLDER_COLORS = [("Yellow", "#F2C14E"), ("Orange", "#FFA64D"), ("Red", "#FF6B6B"), ("Pink", "#F9A8D4"),
                     ("Purple", "#B18CFF"), ("Blue", "#5AB4FF"), ("Teal", "#2DD4BF"), ("Green", "#3DDC97")]

    def open_folder_form(self):
        if self._folder_form is not None and self._folder_form.winfo_exists():
            return self._folder_form.name.focus_set()
        box = ctk.CTkFrame(self.form_slot, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=ACCENT)
        box.pack(fill="x", pady=(6, 0))
        self._folder_form = box
        box.name = ctk.CTkEntry(box, placeholder_text="Folder name", height=34, corner_radius=8,
                                fg_color=BG, border_color=BORDER, text_color=TEXT,
                                placeholder_text_color=SUBTLE, font=font(13))
        box.name.pack(fill="x", padx=10, pady=(10, 8))
        box.color = self.FOLDER_COLORS[0][1]
        swatches = ctk.CTkFrame(box, fg_color="transparent")
        swatches.pack(fill="x", padx=10)
        btns = []

        def pick(color):
            box.color = color
            for b, c in btns:
                b.configure(border_color=TEXT if c == color else SURFACE)
        for name, color in self.FOLDER_COLORS:
            b = ctk.CTkButton(swatches, text="", width=20, height=20, corner_radius=6, fg_color=color,
                              hover_color=color, border_width=2, command=lambda c=color: pick(c))
            b.pack(side="left", padx=(0, 4))
            btns.append((b, color))
        pick(box.color)
        msg = ctk.CTkLabel(box, text="", font=font(11), text_color=DANGER, anchor="w")
        msg.pack(fill="x", padx=10)
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(2, 10))

        def create(_e=None):
            try:
                fid = self.vault.add_folder(box.name.get(), box.color)
            except VaultError as exc:
                return msg.configure(text=str(exc))
            self.close_folder_form()
            self.set_view("folder:" + fid)
        primary_button(row, "Create", create, height=30, width=90).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Cancel", command=self.close_folder_form, width=64, height=30,
                      fg_color="transparent", hover_color=RAISED, text_color=SUBTLE,
                      font=font(12)).pack(side="left", padx=(6, 0))
        box.name.bind("<Return>", create)
        box.name.bind("<Escape>", lambda _e: self.close_folder_form())
        if self.glass is not None:
            self.glass.redraw()
        box.name.focus_set()

    def close_folder_form(self):
        if self._folder_form is not None and self._folder_form.winfo_exists():
            self._folder_form.destroy()
        self._folder_form = None
        self.refresh_rows(keep_scroll=True)

    def rename_folder(self, folder):
        dlg = ctk.CTkInputDialog(text="New name for this folder:", title="Rename folder",
                                 fg_color=SURFACE, button_fg_color=ACCENT, button_hover_color=ACCENT_HOVER,
                                 button_text_color=ACCENT_INK, entry_fg_color=BG, entry_border_color=BORDER,
                                 entry_text_color=TEXT, text_color=TEXT)
        name = dlg.get_input()
        if name:
            try:
                self.vault.rename_folder(folder["id"], name)
            except VaultError as exc:
                return self._status(str(exc), DANGER)
            self.refresh_rows(keep_scroll=True)

    def delete_folder(self, folder):
        if not messagebox.askyesno(APP_NAME, f"Delete the folder “{folder['name']}”?\n\n"
                                   "Your logins stay in your vault. They just won't be in a folder.",
                                   parent=self, icon="warning"):
            return
        self.vault.delete_folder(folder["id"])
        self.view = "all"
        self.refresh_rows()
        self.toast(f"Folder “{folder['name']}” deleted. Its logins are still in All Logins.")

    # ---------------------------------------------------------------- health

    def _health_image(self, score, size=58):
        key = (score, size, self.is_dark)
        cache = getattr(self, "_ring_cache", {})
        self._ring_cache = cache
        if key not in cache:
            def ring(dark):
                from PIL import Image, ImageDraw
                s = size * 4
                img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                w = int(s * 0.11)
                track = "#2A303C" if dark else "#E9E2D2"
                d.ellipse([w // 2, w // 2, s - w // 2, s - w // 2], outline=track, width=w)
                col = health_color(score, dark)
                if score > 0:
                    d.arc([w // 2, w // 2, s - w // 2, s - w // 2], -90, -90 + 360 * score / 100,
                          fill=col, width=w)
                return img.resize((size * 2, size * 2), Image.LANCZOS)
            cache[key] = ctk.CTkImage(light_image=ring(False), dark_image=ring(True), size=(size, size))
        return cache[key]

    def _security_rows(self):
        """The security report (leak results are saved with each login)."""
        return self.vault.security_report()

    def _update_health(self, report):
        score = health_score(self.vault.entry_count, report)
        self._score = score
        open_tips = [r for r in report if self._tip_visible(r, ignore_setting=True)]
        self._open_tips = len(open_tips)
        if getattr(self, "health_ring", None) is not None and self.health_ring.winfo_exists():
            self.health_ring.configure(image=self._health_image(score), text=str(score))
            word = health_word(score)
            self.health_line.configure(text=f"{word} · {score}/100",
                                       text_color=(health_color(score, False), health_color(score, True)))
            n = len(open_tips)
            self.health_tips.configure(text=f"{n} optional tip{'s' if n != 1 else ''} →" if n else "All caught up →")

    def _tip_visible(self, r, ignore_setting=False):
        if r is None or r.get("mute") or r.get("snooze", 0) > time.time():
            return False
        return ignore_setting or self.settings.get("show_suggestions", True)

    @staticmethod
    def _tip_text(r):
        if r["kind"] == "leaked":
            return ("Found in a data leak", "This password showed up in a public data leak. "
                    "Changing it soon is a good idea.")
        if r["kind"] == "reused":
            others = r["reused_with"]
            names = ", ".join(others[:2]) + (f" and {len(others) - 2} more" if len(others) > 2 else "")
            return ("Used twice" if len(others) == 1 else f"Used {len(others) + 1} times",
                    f"You use this password for {names} too. A unique one keeps them safer.")
        return ("Could be stronger", "This password is short or easy to guess. "
                "A longer one only takes a click to make.")

    def _tip_color(self, r):
        return STRENGTH_COLORS[0] if r["kind"] == "leaked" else STRENGTH_COLORS[2]

    # ---------------------------------------------------------------- list

    def _search_typed(self, _e=None):
        """Search after a short pause in typing, not on every single key."""
        if self._search_job is not None:
            try:
                self.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.after(180, self.refresh_rows)

    @property
    def compact(self):
        return self.settings.get("density") == "compact"

    def set_density(self, value):
        self.settings["density"] = "compact" if value == "Compact" else "comfortable"
        save_settings(self.settings, self.data_dir)
        self.refresh_rows(keep_scroll=True)

    def _style_users_btn(self):
        if self.glass is not None:
            return self.glass.redraw()
        on = self.settings.get("show_usernames", False)
        self.users_btn.configure(text="  Hide usernames" if on else "  Show usernames",
                                 fg_color=ACCENT_SOFT if on else "transparent",
                                 hover_color=ACCENT_SOFT_HOVER if on else RAISED,
                                 text_color=ACCENT if on else MUTED, width=140)

    def toggle_usernames(self):
        self.settings["show_usernames"] = not self.settings.get("show_usernames", False)
        save_settings(self.settings, self.data_dir)
        self._style_users_btn()
        self.refresh_rows(keep_scroll=True)

    def refresh_rows(self, highlight=None, keep_scroll=False):
        if not (self.vault and self.vault.is_unlocked) or not getattr(self, "listbox", None) \
                or not self.listbox.winfo_exists():
            return
        self._search_job = None
        if self.art is not None:
            self.art.clear(keep_scroll)
        else:
            for w in self.listbox.winfo_children():
                w.destroy()
        self.rows = {}
        self.more_btn = None
        entries = self.vault.list_entries()
        ids = {e["id"] for e in entries}
        if self.sel_id not in ids:
            self.sel_id = None
        report = self._security_rows()
        self._report = {r["id"]: r for r in report}
        self._draw_nav(entries)
        self._update_health(report)
        if self.glass is not None:
            return self._refresh_glass(entries, highlight)

        folder = None
        if self.view.startswith("folder:"):
            folder = next((f for f in self.vault.folders() if f["id"] == self.view[7:]), None)
        title = "Favorites" if self.view == "favorites" else (folder["name"] if folder else "All Logins")
        self.title_lbl.configure(text=title)
        for w in self.folder_tools.winfo_children():
            w.destroy()
        if folder:
            link_button(self.folder_tools, "Rename", lambda: self.rename_folder(folder), size=12,
                        color=SUBTLE).pack(side="left")
            link_button(self.folder_tools, "Delete folder", lambda: self.delete_folder(folder), size=12,
                        color=SUBTLE).pack(side="left", padx=(8, 0))

        query = self.search.get().strip().lower()
        items = [e for e in entries if query in e["title"].lower()]
        if self.view == "favorites":
            items = [e for e in items if e["fav"]]
        elif folder:
            items = [e for e in items if e["folder"] == folder["id"]]
        if highlight and highlight not in [e["id"] for e in items[:self.PAGE_SIZE]]:
            items.sort(key=lambda e: e["id"] != highlight)  # a just-saved login goes on page one
        self._list_items = items
        self._shown = 0
        self._render_token = object()
        self._draw_panel()
        if not items:
            self._empty_state(len(entries), query, folder)
            return
        self._draw_page(highlight)

    def _refresh_glass(self, entries, highlight=None):
        query = self.search.get().strip().lower()
        folder = None
        if self.view.startswith("folder:"):
            folder = next((f for f in self.vault.folders() if f["id"] == self.view[7:]), None)
        items = [e for e in entries if query in e["title"].lower()]
        if self.view == "favorites":
            items = [e for e in items if e["fav"]]
        elif folder:
            items = [e for e in items if e["folder"] == folder["id"]]
        self._list_items = items
        self._shown = 0
        self._render_token = object()
        self.glass.redraw()
        if not items:
            self._empty_state(len(entries), query, folder)
            return self.art.finish()
        if highlight and highlight not in [e["id"] for e in items[:self.PAGE_SIZE]]:
            items.sort(key=lambda e: e["id"] != highlight)
        self._draw_page(highlight)

    def _empty_state(self, total, query, folder):
        if self.art is not None:
            box = self.art.empty_holder()
        else:
            box = ctk.CTkFrame(self.listbox, fg_color="transparent", corner_radius=14, border_width=1,
                               border_color=BORDER)
            box.pack(fill="x", pady=(10, 0), padx=(0, 6))
        if total == 0 and getattr(self, "_new_vault", False):
            # the welcome only shows right after making a new vault
            ctk.CTkLabel(box, text="Your vault is ready", font=font(20, "bold"), text_color=TEXT).pack(pady=(26, 4))
            ctk.CTkLabel(box, text="Add your first login, or bring them all over from Google, "
                                   "Chrome or another password manager.", font=font(13), text_color=MUTED,
                         wraplength=440).pack()
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(pady=(16, 6))
            primary_button(row, "+  Add Your First Login", self.open_add, height=40, width=214).pack(side="left")
            ghost_button(row, "Import", self.open_import, height=40, width=100).pack(side="left", padx=(10, 0))

            def skip():
                self._new_vault = False
                self.refresh_rows()
            link_button(box, "Skip for now", skip, size=12, color=SUBTLE).pack(pady=(0, 20))
            return
        if total == 0:
            text, sub = "No logins yet", "Click “+ Add Login”, or import them from Google or another app."
        elif query:
            text, sub = "No logins match your search", "Try a different name."
        elif self.view == "favorites":
            text, sub = "No favorites yet", "Click the star next to any login to pin it here."
        else:
            text, sub = "This folder is empty", "Open a login and pick this folder to add it here."
        ctk.CTkLabel(box, text=text, font=font(15, "bold"), text_color=TEXT).pack(pady=(28, 2))
        ctk.CTkLabel(box, text=sub, font=font(13), text_color=MUTED).pack(pady=(0, 28))

    def _draw_page(self, highlight=None):
        if self.art is not None:
            self.art.remove_more()
        elif self.more_btn is not None and self.more_btn.winfo_exists():
            self.more_btn.destroy()
        self.more_btn = None
        end = min(self._shown + self.PAGE_SIZE, len(self._list_items))
        self._draw_batch(self._shown, end, self._render_token, highlight)

    def _draw_batch(self, start, end, token, highlight):
        if token is not self._render_token or not self.listbox.winfo_exists():
            return  # the list was redrawn (search, sign out) - stop
        # the drawn list is cheap: a whole page at once, so rows don't pop in 10 at a time
        stop = end if self.art is not None else min(start + self.BATCH, end)
        for e in self._list_items[start:stop]:
            self._make_row(e)
        self._shown = stop
        if stop < end:
            self.after(1, lambda: self._draw_batch(stop, end, token, highlight))
            return
        left = len(self._list_items) - self._shown
        if self.art is not None:
            if left > 0:
                self.art.add_more(f"Show {min(left, self.PAGE_SIZE)} more  ({left} not shown)", self._draw_page)
            self.art.finish()
        elif left > 0:
            self.more_btn = ghost_button(self.listbox, f"Show {min(left, self.PAGE_SIZE)} more  "
                                                       f"({left} not shown)", self._draw_page, height=40)
            self.more_btn.pack(pady=(8, 12))
        if highlight in self.rows:
            self.select(highlight)

    def _make_row(self, e):
        if self.art is not None:
            r = self._report.get(e["id"])
            show_user = self.settings.get("show_usernames", False)
            info = {"user": (self.vault.username(e["id"]) or "(no username)") if show_user else "••••••••",
                    "note": (self._tip_text(r)[0], self._tip_color(r)) if self._tip_visible(r) else None,
                    "remove": self.view.startswith("folder:")}
            self.art.add_row(e, info)
            self.rows[e["id"]] = {"art": True}
            return
        entry_id, compact = e["id"], self.compact
        on = entry_id == self.sel_id
        row = ctk.CTkFrame(self.listbox, fg_color=ACCENT_SOFT if on else SURFACE,
                           corner_radius=10 if compact else 12, border_width=1,
                           border_color=ACCENT if on else BORDER, cursor="hand2")
        row.pack(fill="x", pady=2 if compact else 4, padx=(0, 6))
        tile = 32 if compact else 44
        img = brand_image(e["icon"], 18 if compact else 24)
        avatar = ctk.CTkLabel(row, text="" if img else (e["title"][:1] or "?").upper(), image=img,
                              width=tile, height=tile, corner_radius=9, fg_color=RAISED,
                              text_color=ACCENT, font=font(15 if compact else 17, "bold"))
        avatar.pack(side="left", padx=(12, 12), pady=6 if compact else 10)
        texts = ctk.CTkFrame(row, fg_color="transparent")
        texts.pack(side="left", fill="x", expand=True)
        name = ctk.CTkLabel(texts, text=e["title"], font=font(14 if compact else 15, "bold"),
                            text_color=TEXT, anchor="w")
        show_user = self.settings.get("show_usernames", False)
        user_text = (self.vault.username(entry_id) or "(no username)") if show_user else "••••••••"
        user = ctk.CTkLabel(texts, text=user_text, font=font(12), text_color=MUTED, anchor="w")
        if compact:
            name.pack(side="left")
            user.pack(side="left", padx=(12, 0))
        else:
            name.pack(fill="x")
            user.pack(fill="x")
        widgets = [row, avatar, texts, name, user]

        r = self._report.get(entry_id)
        if self._tip_visible(r):
            label, _ = self._tip_text(r)
            note = ctk.CTkFrame(row, fg_color="transparent")
            note.pack(side="left", padx=(6, 4))
            ctk.CTkFrame(note, width=7, height=7, corner_radius=4,
                         fg_color=self._tip_color(r)).pack(side="left", padx=(0, 6))
            nl = ctk.CTkLabel(note, text=label, font=font(11), text_color=SUBTLE)
            nl.pack(side="left")
            widgets += [note, nl]

        star = ctk.CTkButton(row, text="", image=star_image(e["fav"]), width=34, height=34, corner_radius=9,
                             fg_color="transparent", hover_color=RAISED,
                             command=lambda: self.toggle_fav(entry_id))
        star.pack(side="right", padx=(0, 8))
        if self.view.startswith("folder:"):
            ctk.CTkButton(row, text="Remove", width=64, height=28, corner_radius=8, fg_color="transparent",
                          hover_color=RAISED, border_width=1, border_color=BORDER, text_color=MUTED,
                          font=font(11), command=lambda: self.remove_from_folder(entry_id)
                          ).pack(side="right", padx=(0, 4))
        for w in widgets:
            w.bind("<Button-1>", lambda _e, i=entry_id: self.select(i))
        self.rows[entry_id] = {"frame": row}

    # ---------------------------------------------------------------- actions

    def select(self, entry_id):
        self._close_menu()
        old = self.rows.get(self.sel_id)
        if self.art is not None and self.art.winfo_exists():
            self.art.set_selected(self.sel_id, entry_id)
            old = None
        if old and "frame" in old and old["frame"].winfo_exists():
            old["frame"].configure(fg_color=SURFACE, border_color=BORDER)
        self.sel_id = entry_id
        self.settings["panel_open"] = True
        new = None if self.art is not None else self.rows.get(entry_id)
        if new and new["frame"].winfo_exists():
            new["frame"].configure(fg_color=ACCENT_SOFT, border_color=ACCENT)
        self._draw_panel()

    def open_panel(self):
        self.settings["panel_open"] = True
        save_settings(self.settings, self.data_dir)
        self._draw_panel()

    def close_panel(self):
        self.settings["panel_open"] = False
        save_settings(self.settings, self.data_dir)
        self._draw_panel()

    def toggle_fav(self, entry_id):
        fav = not self.vault.get(entry_id)["fav"]
        self.vault.set_meta(entry_id, fav=fav)
        self.refresh_rows(keep_scroll=True)
        self._status("Added to Favorites." if fav else "Removed from Favorites.", ACCENT if fav else MUTED)

    def move_to_folder(self, entry_id, folder_id):
        name = next((f["name"] for f in self.vault.folders() if f["id"] == folder_id), "folder")
        self.vault.set_meta(entry_id, folder=folder_id)
        self.refresh_rows(keep_scroll=True)
        self.toast(f"Moved to {name}.")

    def remove_from_folder(self, entry_id):
        e = self.vault.get(entry_id)
        old = e["folder"]
        name = next((f["name"] for f in self.vault.folders() if f["id"] == old), "the folder")
        self.vault.set_meta(entry_id, folder=None)
        self.refresh_rows(keep_scroll=True)

        def undo():
            if self.vault and self.vault.is_unlocked and any(f["id"] == old for f in self.vault.folders()):
                self.vault.set_meta(entry_id, folder=old)
                self.refresh_rows(keep_scroll=True)
        self.toast(f"{e['title']} removed from {name}.", "Undo", undo)

    def snooze_tip(self, entry_id):
        self.vault.set_meta(entry_id, snooze=time.time() + TIP_SNOOZE_DAYS * 86400)
        self.refresh_rows(keep_scroll=True)
        self.toast(f"Okay, hidden for {TIP_SNOOZE_DAYS} days.")

    def mute_tip(self, entry_id):
        title = self.vault.get(entry_id)["title"]
        self.vault.set_meta(entry_id, mute=True)
        self.refresh_rows(keep_scroll=True)
        self.toast(f"You won't see this tip for {title} again.", "Turn off all suggestions",
                   self.suggestions_off)

    def suggestions_off(self):
        self.settings["show_suggestions"] = False
        save_settings(self.settings, self.data_dir)
        self.refresh_rows(keep_scroll=True)

        def undo():
            self.settings["show_suggestions"] = True
            save_settings(self.settings, self.data_dir)
            self.refresh_rows(keep_scroll=True)
        self.toast("Suggestions are off. Turn them back on in Settings › Security.", "Undo", undo)

    # ---------------------------------------------------------------- toast

    def toast(self, text, action_text="", action=None, seconds=7):
        """A small message at the bottom, with an optional button like Undo."""
        if self._toast_frame is not None and self._toast_frame.winfo_exists():
            self._toast_frame.destroy()
        host = getattr(self, "_main", None)
        if host is None or not host.winfo_exists():
            return self._status(text, ACCENT)
        t = ctk.CTkFrame(host, fg_color=TOAST_BG, corner_radius=12)
        t.place(relx=0.5, rely=1.0, y=-20, anchor="s")
        self.glide(8, lambda p: t.winfo_exists() and t.place(y=-20 - 28 * p))
        self._toast_frame = t
        ctk.CTkLabel(t, text=text, font=font(13), text_color=TOAST_FG).pack(side="left", padx=(16, 8), pady=8)

        def close():
            if t.winfo_exists():
                t.destroy()
        if action is not None:
            def act():
                close()
                action()
            ctk.CTkButton(t, text=action_text, command=act, width=0, height=30, corner_radius=8,
                          fg_color="transparent", hover=False, text_color=TOAST_LINK,
                          font=font(13, "bold")).pack(side="left", padx=(0, 4))
        ctk.CTkButton(t, text="×", command=close, width=30, height=30, corner_radius=8,
                      fg_color="transparent", hover=False, text_color=TOAST_FG,
                      font=font(13)).pack(side="left", padx=(0, 6))
        self.after(seconds * 1000, close)

    # ---------------------------------------------------------------- details panel

    def _draw_panel(self):
        if self.glass is not None:
            return self.glass.redraw_panel()
        if getattr(self, "panel", None) is None or not self.panel.winfo_exists():
            return   # not on the vault screen
        for w in self.panel.winfo_children():
            w.destroy()
        self.panel.grid_forget()
        self.rail.grid_forget()
        self._panel_line.grid_forget()
        self._revealed = {"user": False, "pass": False}
        if self.sel_id is None:
            self._panel_was_open = False
            return
        self._panel_line.grid(row=0, column=3, sticky="ns")
        if not self.settings.get("panel_open", True):
            self._panel_was_open = False
            self.rail.grid(row=0, column=4, sticky="ns")
            return
        was_open = getattr(self, "_panel_was_open", False)
        self.panel.grid(row=0, column=4, sticky="ns")
        self._panel_was_open = True
        try:
            e = self.vault.get(self.sel_id)
        except VaultError:
            self.sel_id = None
            return self._draw_panel()
        clip = ctk.CTkFrame(self.panel, fg_color="transparent")
        clip.pack(fill="both", expand=True, padx=18, pady=(12, 18))
        p = ctk.CTkFrame(clip, fg_color="transparent")
        p.place(x=0, y=0, relwidth=1, relheight=1)
        if not was_open:   # slide the details in from the right
            self.glide(8, lambda t: p.winfo_exists() and p.place(x=int(120 * (1 - t))))

        ctk.CTkButton(p, text="›  Hide", command=self.close_panel, width=70, height=28, corner_radius=8,
                      fg_color="transparent", hover_color=RAISED, text_color=SUBTLE, font=font(12),
                      anchor="w").pack(anchor="w", pady=(0, 8))

        head = ctk.CTkFrame(p, fg_color="transparent")
        head.pack(fill="x")
        img = brand_image(e["icon"], 32)
        ctk.CTkLabel(head, text="" if img else (e["title"][:1] or "?").upper(), image=img, width=58, height=58,
                     corner_radius=14, fg_color=RAISED, text_color=ACCENT,
                     font=font(22, "bold")).pack(side="left", padx=(0, 12))
        names = ctk.CTkFrame(head, fg_color="transparent")
        names.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(names, text=e["title"], font=font(18, "bold"), text_color=TEXT, anchor="w",
                     justify="left", wraplength=190).pack(fill="x")
        if e["url"]:
            site = e["url"].split("//")[-1].split("/")[0].removeprefix("www.")
            link_button(names, f"{site} · Open site ↗", lambda: webbrowser.open(e["url"]),
                        size=12).pack(anchor="w")
        ctk.CTkButton(head, text="", image=star_image(e["fav"], 22), width=36, height=36, corner_radius=9,
                      fg_color="transparent", hover_color=RAISED,
                      command=lambda: self.toggle_fav(e["id"])).pack(side="right")

        self._secret_card(p, "USERNAME", "user", e["username"] or "(none)", 0, accent_copy=False)
        card = self._secret_card(p, "PASSWORD", "pass", e["password"], 1, accent_copy=True)
        score, _ = password_strength(e["password"])
        bar_row = ctk.CTkFrame(card, fg_color="transparent")
        bar_row.pack(fill="x", padx=14, pady=(0, 12))
        bar = ctk.CTkProgressBar(bar_row, height=8, corner_radius=4, fg_color=TRACK,
                                 progress_color=STRENGTH_COLORS[score])
        bar.set(max(score, 1) / 4)
        bar.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(bar_row, text=STRENGTH_LABELS[score], font=font(12, "bold"),
                     text_color=STRENGTH_COLORS[score], width=84, anchor="e").pack(side="left")

        self._folder_section(p, e)

        r = self._report.get(e["id"])
        if self._tip_visible(r):
            _, text = self._tip_text(r)
            tip = ctk.CTkFrame(p, fg_color=TIP_BG, corner_radius=10, border_width=1, border_color=BORDER)
            tip.pack(fill="x", pady=(12, 0))
            line = ctk.CTkFrame(tip, fg_color="transparent")
            line.pack(fill="x", padx=12, pady=(10, 4))
            ctk.CTkFrame(line, width=7, height=7, corner_radius=4,
                         fg_color=self._tip_color(r)).pack(side="left", anchor="n", pady=(6, 0), padx=(0, 8))
            ctk.CTkLabel(line, text=text, font=font(12), text_color=MUTED, anchor="w", justify="left",
                         wraplength=250).pack(side="left", fill="x")
            acts = ctk.CTkFrame(tip, fg_color="transparent")
            acts.pack(fill="x", padx=10, pady=(0, 10))
            ctk.CTkButton(acts, text="Make a stronger one", command=lambda: self.open_edit(e["id"], fresh=True),
                          height=28, width=146, corner_radius=7, fg_color="transparent", hover_color=ACCENT_SOFT,
                          border_width=1, border_color=ACCENT, text_color=ACCENT,
                          font=font(12, "bold")).pack(side="left")
            for label, cmd, w in (("Not now", lambda: self.snooze_tip(e["id"]), 62),
                                  ("Don't remind me", lambda: self.mute_tip(e["id"]), 116)):
                ctk.CTkButton(acts, text=label, command=cmd, height=28, width=w, corner_radius=7,
                              fg_color="transparent", hover_color=RAISED, text_color=SUBTLE,
                              font=font(12)).pack(side="left", padx=(2, 0))

        bottom = ctk.CTkFrame(p, fg_color="transparent")
        bottom.pack(side="bottom", fill="x")
        ctk.CTkLabel(bottom, text="Password changed " + ago(e["changed"]), font=font(12), text_color=SUBTLE,
                     anchor="w").pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(bottom, fg_color="transparent")
        row.pack(fill="x")
        ghost_button(row, "Edit", lambda: self.open_edit(e["id"]), height=40).pack(side="left", fill="x",
                                                                                  expand=True)
        ctk.CTkButton(row, text="Delete", command=lambda: self.delete_entry(e["id"]), width=80, height=40,
                      corner_radius=10, fg_color="transparent", hover_color=DANGER_SOFT, text_color=SUBTLE,
                      font=font(14)).pack(side="left", padx=(8, 0))

    def _secret_card(self, parent, label, key, value, which, accent_copy):
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(14 if key == "user" else 10, 0))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=10)
        texts = ctk.CTkFrame(row, fg_color="transparent")
        texts.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(texts, text=label, font=font(11, "bold"), text_color=SUBTLE, anchor="w").pack(fill="x")
        shown = ctk.CTkLabel(texts, text=DOTS, font=font(14, mono=key == "pass"), text_color=TEXT, anchor="w",
                             wraplength=150, justify="left")
        shown.pack(fill="x")
        btn = ctk.CTkButton(row, text="Show", width=54, height=30, corner_radius=8, fg_color="transparent",
                            hover_color=RAISED, border_width=1, border_color=BORDER, text_color=TEXT,
                            font=font(12))

        def flip():
            self._revealed[key] = not self._revealed[key]
            shown.configure(text=value if self._revealed[key] else DOTS)
            btn.configure(text="Hide" if self._revealed[key] else "Show")
            if self._revealed[key]:
                self.reveal_deadline = time.time() + REVEAL_SECONDS
                self.revealed_id = self.sel_id
        btn.configure(command=flip)
        btn.pack(side="left", padx=(6, 0))
        if accent_copy:
            primary_button(row, "Copy", lambda: self.copy(self.sel_id, which), width=58, height=30).pack(
                side="left", padx=(6, 0))
        else:
            ctk.CTkButton(row, text="Copy", command=lambda: self.copy(self.sel_id, which), width=58, height=30,
                          corner_radius=8, fg_color="transparent", hover_color=RAISED, border_width=1,
                          border_color=BORDER, text_color=TEXT, font=font(12)).pack(side="left", padx=(6, 0))
        self._secret_widgets = getattr(self, "_secret_widgets", {})
        self._secret_widgets[key] = (shown, btn)
        return card

    def _folder_section(self, p, e):
        folders = self.vault.folders()
        ctk.CTkLabel(p, text="FOLDER", font=font(11, "bold"), text_color=SUBTLE, anchor="w").pack(
            fill="x", pady=(14, 4))
        cur = next((f for f in folders if f["id"] == e["folder"]), None)
        if cur:
            chip = ctk.CTkFrame(p, fg_color=ACCENT_SOFT, corner_radius=15, border_width=1, border_color=ACCENT)
            chip.pack(anchor="w", pady=(0, 6))
            ctk.CTkFrame(chip, width=9, height=9, corner_radius=3, fg_color=cur.get("color") or ACCENT).pack(
                side="left", padx=(12, 6))
            ctk.CTkLabel(chip, text=cur["name"], font=font(12, "bold"), text_color=ACCENT).pack(side="left")
            ctk.CTkButton(chip, text="×", width=26, height=26, corner_radius=13, fg_color="transparent",
                          hover_color=ACCENT_SOFT_HOVER, text_color=ACCENT, font=font(11),
                          command=lambda: self.remove_from_folder(e["id"])).pack(side="left", padx=(2, 3), pady=2)
        others = [f for f in folders if f["id"] != e["folder"]]
        if not folders:
            ctk.CTkLabel(p, text="No folders yet. Click + under Folders to make one.", font=font(12),
                         text_color=SUBTLE, anchor="w").pack(fill="x")
            return
        if others:
            grid = ctk.CTkFrame(p, fg_color="transparent")
            grid.pack(fill="x")
            ctk.CTkLabel(grid, text="Move to" if cur else "Add to", font=font(12), text_color=SUBTLE).grid(
                row=0, column=0, sticky="w", padx=(0, 6))
            for i, f in enumerate(others):
                self._chip(grid, f.get("color") or ACCENT, f["name"],
                           lambda fid=f["id"]: self.move_to_folder(e["id"], fid)).grid(
                    row=(i + 1) // 3, column=(i + 1) % 3, sticky="w", padx=(0, 6), pady=2)

    def _chip(self, parent, color, name, cmd):
        """A small rounded button with a colored dot, like the folder chips."""
        chip = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=14, border_width=1,
                            border_color=BORDER, height=28, cursor="hand2")
        dot = ctk.CTkFrame(chip, width=8, height=8, corner_radius=3, fg_color=color)
        dot.pack(side="left", padx=(10, 6))
        lbl = ctk.CTkLabel(chip, text=name, font=font(12), text_color=MUTED, height=24)
        lbl.pack(side="left", padx=(0, 10), pady=2)
        for w in (chip, dot, lbl):
            w.bind("<Button-1>", lambda _e: cmd())
            w.bind("<Enter>", lambda _e: chip.configure(fg_color=RAISED))
            w.bind("<Leave>", lambda _e: chip.configure(fg_color="transparent"))
        return chip

    def delete_entry(self, entry_id):
        title = self.vault.get(entry_id)["title"]
        if messagebox.askyesno(APP_NAME, f"Delete “{title}”? This can't be undone.", parent=self,
                               icon="warning"):
            self.vault.delete(entry_id)
            self.sel_id = None
            self.refresh_rows(keep_scroll=True)
            self._status(f"Deleted “{title}”.", MUTED)

    def hide_revealed(self):
        for shown, btn in getattr(self, "_secret_widgets", {}).values():
            if shown.winfo_exists():
                shown.configure(text=DOTS)
                btn.configure(text="Show")
        self._revealed = {"user": False, "pass": False}
        self.revealed_id = None

    # ---------------------------------------------------------------- profile menu

    def _close_menu(self):
        if getattr(self, "_menu", None) is not None and self._menu.winfo_exists():
            self._menu.destroy()
        self._menu = None

    def _click_anywhere(self, event):
        m = getattr(self, "_menu", None)
        if m is None or not m.winfo_exists():
            return
        w = str(event.widget)
        if w.startswith(str(m)) or w.startswith(str(self.profile_btn)):
            return
        self._close_menu()

    def open_help(self):
        repo = getattr(updater_mod, "__repo__", "") or ""
        try:
            from version import __repo__ as repo  # noqa: F811
        except Exception:
            pass
        webbrowser.open(f"https://github.com/{repo}#readme" if repo else "https://github.com/")

    # ------------------------------------------------------------- clipboard

    def copy(self, entry_id, which):
        value = self.vault.reveal(entry_id)[which]
        if not value:
            self._status("That login has no username saved.", MUTED)
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        token = object()
        self.clip = (token, value)
        what = "Username" if which == 0 else "Password"
        self._status(f"{what} copied. It's cleared from your clipboard in {CLIPBOARD_CLEAR_SECONDS} seconds.",
                     ACCENT)
        self.after(CLIPBOARD_CLEAR_SECONDS * 1000, lambda: self.wipe_clipboard(token))

    def copy_text(self, value, what="Password"):
        """Copy any text; it's wiped from the clipboard after a short time."""
        self.clipboard_clear()
        self.clipboard_append(value)
        token = object()
        self.clip = (token, value)
        self._status(f"{what} copied. It's cleared from your clipboard in {CLIPBOARD_CLEAR_SECONDS} seconds.",
                     ACCENT)
        self.after(CLIPBOARD_CLEAR_SECONDS * 1000, lambda: self.wipe_clipboard(token))

    def wipe_clipboard(self, token=None):
        if not self.clip or (token is not None and token is not self.clip[0]):
            return
        try:
            if self.clipboard_get() == self.clip[1]:
                self.clipboard_clear()
                self.clipboard_append("")
        except Exception:
            pass
        self.clip = None
        self._status("Clipboard cleared.", SUBTLE)

    # ---------------------------------------------------------- add / edit

    def open_add(self):
        self._close_menu()
        EntryDialog(self, "Add a Login", None, on_save=self._save_new)

    def _save_new(self, title, username, password, icon):
        new_id = self.vault.add(title, username, password, icon)
        if self.view.startswith("folder:"):
            self.vault.set_meta(new_id, folder=self.view[7:])
        elif self.view == "favorites":
            self.vault.set_meta(new_id, fav=True)
        self._new_vault = False
        self.sel_id = new_id
        self.refresh_rows(highlight=new_id)
        self._status(f"Saved “{title}”.", ACCENT)
        return new_id

    def open_edit(self, entry_id, fresh=False):
        try:
            current = self.vault.get(entry_id)
        except VaultError as exc:
            self._status(str(exc), DANGER)
            return

        def save(title, username, password, icon):
            self.vault.update(entry_id, title, username, password, icon)
            self.refresh_rows(keep_scroll=True)
            self._status(f"Updated “{title}”.", ACCENT)

        def delete():
            self.vault.delete(entry_id)
            self.sel_id = None
            self.refresh_rows(keep_scroll=True)
            self._status(f"Deleted “{current['title']}”.", MUTED)

        EntryDialog(self, "Edit Login", current, on_save=save, on_delete=delete, fresh=fresh)

    def open_change_master(self):
        ChangeMasterWarning(self)

    def open_import(self):
        self._close_menu()
        ImportDialog(self)

    def open_export(self):
        self._close_menu()
        ExportDialog(self)

    # =========================================================== SETTINGS

    SETTINGS_TABS = [("general", "General"), ("appearance", "Appearance"), ("security", "Security"),
                     ("sync", "Sync & devices"), ("import", "Import & export"), ("about", "About")]

    def _page_frame(self):
        """A full page (Settings, Security tips) that keeps the vault open."""
        self._clear()
        self._touch()
        self.status = None
        self._menu = None
        self._toast_frame = None
        page = ctk.CTkFrame(self.body, fg_color="transparent", corner_radius=0)
        page.pack(fill="both", expand=True)
        self._main = page
        return page

    def show_settings(self, tab="general", fresh=False):
        """Settings stays built while you're in it: the menu on the left never redraws, each tab is
        built the first time you open it and just shown again after that. Calling this for the tab
        you're already on rebuilds that tab (something on it changed) and keeps your place."""
        shell = getattr(self, "_settings_shell", None)
        if fresh or shell is None or not shell["page"].winfo_exists() \
                or getattr(self, "_main", None) is not shell["page"]:
            return self._settings_new_page(tab)
        self._touch()
        self._toast_frame = None
        tabs, cur = shell["tabs"], self._settings_tab
        if tab != cur and tab in tabs:
            return self._settings_switch(cur, tab)
        old = tabs.pop(tab, None)
        keep = old["body"]._parent_canvas.yview()[0] if old is not None else None
        self._settings_build_tab(tab)
        self._settings_switch(None if cur == tab else cur, tab, old=old, keep=keep)

    def _settings_new_page(self, tab):
        old_page = None
        shell = getattr(self, "_settings_shell", None)
        if shell is not None and shell["page"].winfo_exists() and getattr(self, "_main", None) is shell["page"]:
            # already in Settings (e.g. the style changed): build the new page on top of the old one,
            # then remove the old one, so the screen never goes blank
            old_page = shell["page"]
            self._touch()
            self.status, self._menu, self._toast_frame = None, None, None
            page = ctk.CTkFrame(self.body, fg_color=BG, corner_radius=0)
            self._main = page
        else:
            page = self._page_frame()
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure(2, weight=1)
        nav = ctk.CTkFrame(page, fg_color=SIDE, corner_radius=0, width=236)
        nav.grid(row=0, column=0, rowspan=2, sticky="ns")
        nav.pack_propagate(False)
        ctk.CTkFrame(page, fg_color=BORDER, corner_radius=0, width=1).grid(row=0, column=1, rowspan=2,
                                                                          sticky="ns")
        link_button(nav, "←  Back to vault", self.show_main, size=13, color=MUTED).pack(anchor="w", padx=16,
                                                                                         pady=(20, 6))
        ctk.CTkLabel(nav, text="Settings", font=font(24, "bold"), text_color=TEXT, anchor="w").pack(
            fill="x", padx=20, pady=(0, 14))
        buttons = {}
        for key, label in self.SETTINGS_TABS:
            b = ctk.CTkButton(nav, text=label, command=lambda k=key: self.show_settings(k), height=40,
                              corner_radius=10, anchor="w", font=font(14))
            b.pack(fill="x", padx=10, pady=1)
            buttons[key] = b
        ctk.CTkButton(nav, text="Sign out", command=self.sign_out, height=40, corner_radius=10, anchor="w",
                      fg_color=DANGER_SOFT, hover_color=DANGER_BORDER, text_color=SIGNOUT,
                      font=font(14, "bold")).pack(side="bottom", fill="x", padx=10, pady=16)
        self._settings_shell = {"page": page, "nav": buttons, "tabs": {}, "lit": None}
        self._settings_tab = None
        self._settings_build_tab(tab)
        self._settings_switch(None, tab)
        if old_page is not None:
            page.place(x=0, y=0, relwidth=1, relheight=1)
            page.lift()
            page.update_idletasks()
            old_page.destroy()

    def _settings_build_tab(self, tab):
        page = self._settings_shell["page"]
        t = {"grid": [], "painters": [], "preview": None, "update_slot": None}
        self._painters = t["painters"]
        if tab == "appearance":   # a live preview that stays put while you scroll the choices
            top = ctk.CTkFrame(page, fg_color="transparent")
            top.grid(row=0, column=2, sticky="ew", padx=34, pady=(18, 0))
            ctk.CTkLabel(top, text="PREVIEW", font=font(11, "bold"), text_color=SUBTLE, anchor="w").pack(fill="x")
            pic = getattr(self, "_last_preview", None)
            if pic is None:
                from PIL import Image
                pic = Image.new("RGBA", (1120, 520), (0, 0, 0, 0))
            t["preview"] = self._preview_lbl = ctk.CTkLabel(top, text="", width=560, height=260,
                                                            image=ctk.CTkImage(light_image=pic, dark_image=pic,
                                                                               size=(560, 260)))
            t["preview"].pack(anchor="w", pady=(4, 0))
            line = ctk.CTkFrame(page, fg_color=BORDER, corner_radius=0, height=1)
            line.grid(row=0, column=2, sticky="sew", padx=34)
            t["grid"] += [top, line]
        body = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        inner = ctk.CTkFrame(body, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=34, pady=(14 if tab == "appearance" else 24, 24))
        ctk.CTkLabel(inner, text=dict(self.SETTINGS_TABS)[tab], font=font(24, "bold"), text_color=TEXT,
                     anchor="w").pack(fill="x")
        self._settings_body, self._settings_tab = body, tab
        getattr(self, "_settings_" + tab)(inner)
        t["update_slot"] = self._update_slot if tab == "about" else None
        t["status"] = self.status = ctk.CTkLabel(inner, text="", font=font(12), text_color=MUTED, anchor="w")
        t["status"].pack(fill="x", pady=(18, 0))
        body.grid(row=1, column=2, sticky="nsew")
        t["grid"].append(body)
        t["body"] = body
        self._settings_shell["tabs"][tab] = t

    def _settings_switch(self, cur, tab, old=None, keep=None):
        """Show a built tab and hide the one you were on (nothing is rebuilt)."""
        shell = self._settings_shell
        t = shell["tabs"][tab]
        for w in t["grid"]:
            w.grid()
        if cur is not None and cur in shell["tabs"]:
            for w in shell["tabs"][cur]["grid"]:
                w.grid_remove()
        if old is not None:
            for w in old["grid"]:
                w.destroy()
        if keep:
            t["body"].update_idletasks()
            t["body"]._parent_canvas.yview_moveto(keep)
        self._settings_body, self._settings_tab = t["body"], tab
        self.status, self._painters, self._preview_lbl = t["status"], t["painters"], t["preview"]
        if t["update_slot"] is not None:
            self._update_slot = t["update_slot"]
        self._paint_settings_nav()
        if tab == "appearance":
            self._update_preview()

    def _paint_settings_nav(self):
        shell = getattr(self, "_settings_shell", None)
        if shell is None:
            return
        lit = (self._settings_tab, ACCENT)
        if lit == shell["lit"]:
            return
        for key, b in shell["nav"].items():
            on = key == self._settings_tab
            b.configure(font=font(14, "bold" if on else "normal"), fg_color=ACCENT_SOFT if on else "transparent",
                        hover_color=ACCENT_SOFT_HOVER if on else RAISED, text_color=ACCENT if on else TEXT)
        shell["lit"] = lit

    def _settings_forget_others(self):
        """Colors changed: the other tabs are rebuilt the next time they're opened."""
        shell = getattr(self, "_settings_shell", None)
        if shell is None:
            return
        for key in [k for k in shell["tabs"] if k != self._settings_tab]:
            for w in shell["tabs"].pop(key)["grid"]:
                w.destroy()

    def _section(self, parent, title, sub=""):
        ctk.CTkLabel(parent, text=title, font=font(15, "bold"), text_color=TEXT, anchor="w").pack(
            fill="x", pady=(22, 0))
        if sub:
            ctk.CTkLabel(parent, text=sub, font=font(12), text_color=MUTED, anchor="w", justify="left",
                         wraplength=560).pack(fill="x", pady=(2, 0))

    def _choice_row(self, parent, options, current, on_pick, wrap=8):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        for i, (value, label) in enumerate(options):
            on = value == current
            ctk.CTkButton(row, text=label, command=lambda v=value: on_pick(v), height=36, width=76,
                          corner_radius=10, fg_color=ACCENT if on else SURFACE,
                          hover_color=ACCENT_HOVER if on else RAISED, border_width=1,
                          border_color=ACCENT if on else BORDER, text_color=ACCENT_INK if on else TEXT,
                          font=font(13, "bold" if on else "normal")).grid(row=i // wrap, column=i % wrap,
                                                                          padx=(0, 6), pady=3, sticky="w")
        return row

    def _switch_row(self, parent, title, sub, key, default=True, on_change=None):
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(10, 0))
        words = ctk.CTkFrame(card, fg_color="transparent")
        words.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        ctk.CTkLabel(words, text=title, font=font(14, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(words, text=sub, font=font(12), text_color=MUTED, anchor="w", justify="left",
                     wraplength=430).pack(fill="x")
        state = {"on": bool(self.settings.get(key, default))}
        toggle = ctk.CTkButton(card, text="", image=toggle_image(state["on"]), width=52, height=30,
                               fg_color="transparent", hover=False, cursor="hand2")

        def flip():
            state["on"] = not state["on"]
            toggle.configure(image=toggle_image(state["on"]))
            self.settings[key] = state["on"]
            save_settings(self.settings, self.data_dir)
            if on_change:
                on_change()
        toggle.configure(command=flip)
        toggle.pack(side="right", padx=12)
        card.toggle = toggle
        if getattr(self, "_painters", None) is not None:
            seen = {"accent": ACCENT}

            def repaint():
                if ACCENT != seen["accent"] and toggle.winfo_exists():
                    toggle.configure(image=toggle_image(state["on"]))
                    seen["accent"] = ACCENT
            self._painters.append(repaint)
        return card

    def _settings_general(self, c):
        self._section(c, "Signed in as")
        ctk.CTkLabel(c, text=self.vault.email, font=font(14), text_color=MUTED, anchor="w").pack(fill="x",
                                                                                                pady=(4, 0))
        self._section(c, "Lock HushKey after", "If you don't use HushKey for this long, it locks and asks for "
                                              "your master password. The timer runs while HushKey is open "
                                              "or minimized, and starts over when you close it.")
        cur = int(self.settings.get("lock_after", DEFAULT_LOCK_SECONDS))

        def pick(v):
            self.settings["lock_after"] = v
            save_settings(self.settings, self.data_dir)
            self.show_settings("general")
        self._choice_row(c, LOCK_CHOICES, cur, pick)
        if cur == 0:
            ctk.CTkLabel(c, text="Suggestion: “Never” is handy at home, but on a shared or work computer "
                                 "a time limit keeps your vault safer.", font=font(12), text_color=GOLD,
                         anchor="w", justify="left", wraplength=560).pack(fill="x", pady=(8, 0))
        self._section(c, "This computer")
        until = self.vault.auto_signin_until
        remembered = until > time.time() or (self.cloud.configured and self.vault.is_device_remembered())
        text = ("Remembered until " + time.strftime("%b %d", time.localtime(until)) +
                ": HushKey opens without your master password.") if until > time.time() else \
            ("Remembered: no email code needed when you sign in." if remembered else
             "Not remembered. To stay signed in, tick “Remember this device” when you sign in.")
        ctk.CTkLabel(c, text=text, font=font(13), text_color=MUTED, anchor="w", justify="left",
                     wraplength=560).pack(fill="x", pady=(6, 0))
        if remembered:
            def forget():
                self.forget_device()
                self.show_settings("general")
                self._status("This computer is forgotten. Next time you'll sign in with your master password.",
                             ACCENT)
            ghost_button(c, "Forget this device", forget, height=38, width=170).pack(anchor="w", pady=(10, 0))
        self._section(c, "Copied passwords", f"Anything you copy is cleared from your clipboard after "
                                             f"{CLIPBOARD_CLEAR_SECONDS} seconds.")

    def _settings_appearance(self, c):
        """Every choice here updates in place (no rebuilding the page), and the preview at the
        top redraws in the background, so picking things is instant and nothing flashes."""
        self._section(c, "Theme")

        def theme(v):
            self.settings["theme"] = v
            save_settings(self.settings, self.data_dir)
            ctk.set_appearance_mode({"light": "light", "dark": "dark"}.get(v, "system"))
            self.refresh_appearance()
        self._live_choice(c, [("dark", "Dark"), ("light", "Light"), ("system", "Match my computer")],
                          lambda: self.settings.get("theme", "dark"), theme)
        self._settings_style(c)
        self._settings_accent(c)
        self._settings_background(c)
        self._section(c, "Density", "Comfortable gives each login more room. Compact fits more on screen.")

        def density(v):
            self.settings["density"] = v
            save_settings(self.settings, self.data_dir)
            self.refresh_appearance()
        self._live_choice(c, [("comfortable", "Comfortable"), ("compact", "Compact")],
                          lambda: "compact" if self.compact else "comfortable", density)
        self._section(c, "Password strength colors", "These never change with your accent color, "
                                                    "so a weak password always looks like a warning.")
        legend = ctk.CTkFrame(c, fg_color="transparent")
        legend.pack(anchor="w", pady=(8, 0))
        for i in (1, 2, 3, 4):
            ctk.CTkFrame(legend, width=22, height=8, corner_radius=4, fg_color=STRENGTH_COLORS[i]).pack(
                side="left", padx=(0, 6))
            ctk.CTkLabel(legend, text=STRENGTH_LABELS[i], font=font(12), text_color=MUTED).pack(
                side="left", padx=(0, 14))

    def _live_choice(self, parent, options, get, on_pick, wrap=8):
        """A row of choices that restyles itself when you pick (no page rebuild)."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        btns = {}

        def colors(on):
            return dict(fg_color=ACCENT if on else SURFACE, hover_color=ACCENT_HOVER if on else RAISED,
                        border_color=ACCENT if on else BORDER, text_color=ACCENT_INK if on else TEXT)
        cur = get()
        for i, (value, label) in enumerate(options):
            b = ctk.CTkButton(row, text=label, command=lambda v=value: on_pick(v), height=36, width=76,
                              corner_radius=10, border_width=1, font=font(13), **colors(value == cur))
            b.grid(row=i // wrap, column=i % wrap, padx=(0, 6), pady=3, sticky="w")
            btns[value] = b
        state = {"cur": cur, "accent": ACCENT}

        def paint():
            now = get()
            if now == state["cur"] and ACCENT == state["accent"]:
                return   # nothing changed for this row
            for v, b in btns.items():
                if ACCENT != state["accent"] or v in (now, state["cur"]):
                    b.configure(**colors(v == now))
            state.update(cur=now, accent=ACCENT)
        self._painters.append(paint)
        return row

    def refresh_appearance(self, rebuild=False):
        """After a change in Appearance: restyle the choices and redraw the preview."""
        if rebuild:
            return self.show_settings("appearance", fresh=True)
        self._paint_settings_nav()
        for paint in list(getattr(self, "_painters", [])):
            try:
                paint()
            except Exception:
                traceback.print_exc()
        self._update_preview()

    def _update_preview(self):
        lbl = getattr(self, "_preview_lbl", None)
        if lbl is None or not lbl.winfo_exists():
            return
        token = object()
        self._preview_token = token
        snapshot, dark = dict(self.settings), self.is_dark

        def done(pic):
            self._last_preview = pic
            if self._preview_token is token and lbl.winfo_exists():
                lbl.configure(image=ctk.CTkImage(light_image=pic, dark_image=pic,
                                                 size=(pic.width // 2, pic.height // 2)))
        self.run_quiet(lambda: appearance_preview(snapshot, dark), done)

    def _refont(self):
        """Switch every word on screen to the chosen font, without rebuilding anything."""
        stack = [self]
        while stack:
            w = stack.pop()
            stack.extend(w.winfo_children())
            f = getattr(w, "_font", None)
            if isinstance(f, ctk.CTkFont) and not getattr(w, "_hk_keep_font", False) \
                    and f.cget("family") != MONO and FAMILY:
                f.configure(family=FAMILY)

    def _settings_style(self, c):
        self._section(c, "Style", "Basic has soft rounded corners. Pixel gives HushKey square, retro corners "
                                  "and the pixel font.")

        def set_style(v):
            global STYLE
            if v == self.settings.get("style", "basic"):
                return
            self.settings["style"] = v
            if v == "pixel" and self.settings.get("font", "poppins") == "poppins":
                self.settings["font"] = "pixel"
            elif v == "basic" and self.settings.get("font") == "pixel":
                self.settings["font"] = "poppins"
            save_settings(self.settings, self.data_dir)
            STYLE = v
            set_font(self.settings.get("font", "poppins"))
            _toggle_cache.clear()
            self.refresh_appearance(rebuild=True)   # corners are set when a box is made, so redraw the page
        self._live_choice(c, [("basic", "Basic"), ("pixel", "Pixel")],
                          lambda: self.settings.get("style", "basic"), set_style)
        self._switch_row(c, "Smooth animations", "The details panel, menus and messages slide in quickly. "
                                                 "Turn off for instant changes.", "animations", default=True)
        self._section(c, "Font")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        btns = {}

        def set_fnt(v):
            self.settings["font"] = v
            save_settings(self.settings, self.data_dir)
            set_font(v)
            self._refont()
            self.refresh_appearance()
        def colors(on):
            return dict(fg_color=ACCENT if on else SURFACE, hover_color=ACCENT_HOVER if on else RAISED,
                        border_color=ACCENT if on else BORDER, text_color=ACCENT_INK if on else TEXT)
        start = self.settings.get("font", "poppins")
        for i, (key, family, _stem) in enumerate(FONT_CHOICES):
            fam = family if family in _AVAILABLE else FAMILY
            b = ctk.CTkButton(row, text=FONT_LABELS[key], command=lambda v=key: set_fnt(v), height=40, width=110,
                              corner_radius=10, border_width=1, **colors(key == start),
                              font=ctk.CTkFont(family=fam, size=14) if fam else font(14))
            b._hk_keep_font = True   # each button shows its own font
            b.grid(row=0, column=i, padx=(0, 6), pady=3, sticky="w")
            btns[key] = b
        state = {"cur": start, "accent": ACCENT}

        def paint():
            now = self.settings.get("font", "poppins")
            if now == state["cur"] and ACCENT == state["accent"]:
                return
            for k, b in btns.items():
                if ACCENT != state["accent"] or k in (now, state["cur"]):
                    b.configure(**colors(k == now))
            state.update(cur=now, accent=ACCENT)
        self._painters.append(paint)

    def _settings_accent(self, c):
        title = ctk.CTkLabel(c, text="", font=font(15, "bold"), text_color=TEXT, anchor="w")
        title.pack(fill="x", pady=(22, 0))
        ctk.CTkLabel(c, text="Buttons and highlights use your color. The HushKey logo stays green.", font=font(12),
                     text_color=MUTED, anchor="w").pack(fill="x", pady=(2, 0))
        get = (lambda: self.settings.get("accent", "green"))
        grid = PickGrid(c, [a[0] for a in ACCENTS], 7, (48, 48), accent_grid_picture, get, self.set_accent)
        grid.pack(anchor="w", pady=(10, 0))

        def paint():
            title.configure(text="Accent color · " + next((a[1] for a in ACCENTS if a[0] == get()), "Green"))
            grid.paint()
        title.configure(text="Accent color · " + next((a[1] for a in ACCENTS if a[0] == get()), "Green"))
        self._painters.append(paint)

    def _settings_background(self, c):
        title = ctk.CTkLabel(c, text="", font=font(15, "bold"), text_color=TEXT, anchor="w")
        title.pack(fill="x", pady=(22, 0))
        ctk.CTkLabel(c, text="A picture behind your vault. It fades darker in dark mode and lighter in light "
                             "mode, so everything stays easy to read.", font=font(12), text_color=MUTED,
                     anchor="w", justify="left", wraplength=560).pack(fill="x", pady=(2, 0))
        def pick(key):
            was = self.settings.get("background", "none")
            self.settings["background"] = key
            save_settings(self.settings, self.data_dir)
            # the picture options below only show when a picture is chosen
            self.refresh_appearance(rebuild=(was == "none") != (key == "none"))
        get = (lambda: self.settings.get("background", "none"))
        grid = PickGrid(c, [b[0] for b in BACKGROUNDS], 4, (140, 104), background_grid_picture, get, pick)
        grid.pack(anchor="w", pady=(10, 0))

        def paint():
            title.configure(text="Background · " + dict(BACKGROUNDS).get(get(), "Plain"))
            grid.paint()
        title.configure(text="Background · " + dict(BACKGROUNDS).get(get(), "Plain"))
        self._painters.append(paint)
        if self.settings.get("background", "none") == "none":
            return
        self._section(c, "Dim the picture", "More dim makes your logins easier to read.")

        def set_dim(v):
            self.settings["bg_dim"] = v
            save_settings(self.settings, self.data_dir)
            self.refresh_appearance()
        self._live_choice(c, [("low", "Low"), ("medium", "Medium"), ("high", "High")],
                          lambda: self.settings.get("bg_dim", "medium"), set_dim)
        self._opacity_row(c)
        self._switch_row(c, "Show it on the sign-in screen", "Off: the sign-in screen stays plain. "
                                                             "The sign-in box itself is always solid.",
                         "bg_signin", default=False)

    def _opacity_row(self, c):
        """A slider for how solid the boxes over the picture are. 100% (the default) is solid."""
        card = ctk.CTkFrame(c, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(10, 0))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(top, text="Box opacity", font=font(14, "bold"), text_color=TEXT, anchor="w").pack(side="left")
        value = ctk.CTkLabel(top, text="", font=font(13, "bold"), text_color=ACCENT, anchor="e")
        value.pack(side="right")
        ctk.CTkLabel(card, text="How much of the picture shows through your logins, the sidebar and the details "
                                "panel. 100% is solid. Lower lets more of the picture through; text keeps a soft "
                                "shadow so it stays readable.", font=font(12), text_color=MUTED, anchor="w",
                     justify="left", wraplength=520).pack(fill="x", padx=16)

        def words(v):
            return f"{v}%  ·  solid" if v >= 100 else f"{v}%"
        job = {"id": None}

        def apply():
            job["id"] = None
            save_settings(self.settings, self.data_dir)
            self._update_preview()

        def slide(v):
            v = int(round(float(v)))
            if v == box_opacity(self.settings) and job["id"] is None:
                return
            self.settings["box_opacity"] = v
            value.configure(text=words(v))
            if job["id"] is None:   # redraw the preview at most every 80 ms while dragging
                job["id"] = self.after(80, apply)
        slider = ctk.CTkSlider(card, from_=0, to=100, number_of_steps=20, command=slide, height=18,
                               progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                               fg_color=TRACK)
        slider.set(box_opacity(self.settings))
        slider.pack(fill="x", padx=12, pady=(10, 4))
        ends = ctk.CTkFrame(card, fg_color="transparent")
        ends.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(ends, text="See-through", font=font(11), text_color=SUBTLE).pack(side="left")
        ctk.CTkLabel(ends, text="Solid", font=font(11), text_color=SUBTLE).pack(side="right")
        value.configure(text=words(box_opacity(self.settings)))
        card.slider = slider
        seen = {"accent": ACCENT}

        def repaint():
            if ACCENT != seen["accent"] and slider.winfo_exists():
                slider.configure(progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_HOVER)
                value.configure(text_color=ACCENT)
                seen["accent"] = ACCENT
        self._painters.append(repaint)
        return card

    def set_accent(self, key):
        self.settings["accent"] = key
        save_settings(self.settings, self.data_dir)
        apply_accent(key)
        self._settings_forget_others()   # the other tabs use the accent color too
        if getattr(self, "_settings_tab", None) == "appearance" and getattr(self, "_painters", None) is not None \
                and getattr(self, "_settings_body", None) is not None and self._settings_body.winfo_exists():
            return self.refresh_appearance()
        self.show_settings("appearance")

    def _settings_security(self, c):
        self._section(c, "Master password", "The one password that unlocks everything. "
                                            "Change it if you think someone else knows it.")
        ctk.CTkButton(c, text="Change master password", command=self.open_change_master, height=40, width=220,
                      corner_radius=10, fg_color=WARN, hover_color=WARN_HOVER, text_color=("#FFFFFF", "#2A1606"),
                      font=font(14, "bold")).pack(anchor="w", pady=(10, 0))
        self._section(c, "Suggestions")
        self._switch_row(c, "Show suggestions", "Small, optional tips (like “Used twice”) on logins that could "
                                                "be safer. Turn off to never see them.", "show_suggestions")
        self._switch_row(c, "Check for leaked passwords", "Privately checks your passwords against known data "
                                                          "leaks. Only the first 5 characters of a scrambled "
                                                          "version ever leave your computer.", "leak_check",
                         on_change=self._leak_setting_changed)
        link_button(c, "Open Security tips →", self.show_security, size=13).pack(anchor="w", pady=(12, 0))

    def _leak_setting_changed(self):
        if self.settings.get("leak_check", True):
            self._leak_done = False
            self.start_leak_check()
        else:
            pass   # saved results stay until the check runs again

    def _settings_sync(self, c):
        if not self.cloud.configured:
            self._section(c, "Sync isn't set up in this copy of HushKey",
                          "Your vault stays on this computer only.")
            return
        on = self.syncer is not None and (self.syncer.enabled or self.syncer._session is not None)
        self._section(c, "Sync across your computers",
                      "Your vault is encrypted on this computer before it's uploaded, so nobody but you "
                      "can read it. Sign in on another computer with your email and master password.")
        state = ctk.CTkLabel(c, text="", font=font(13, "bold"), text_color=ACCENT, anchor="w")
        state.pack(fill="x", pady=(10, 0))
        if on:
            state.configure(text=self.syncer.status_text() or "Sync is on")
            ghost_button(c, "Sync now", lambda: self.request_sync(delay=0), height=38, width=120).pack(
                anchor="w", pady=(10, 0))
        else:
            state.configure(text="Sync is off", text_color=GOLD)
            self.recovery_btn = primary_button(c, "Turn on sync", self.turn_on_recovery, height=40, width=160)
            self.recovery_btn.pack(anchor="w", pady=(10, 0))
        self._settings_computers(c, on)
        self._section(c, "Email recovery", "On: you can reset a forgotten master password with a code sent "
                                           "to your email." if self.vault.has_recovery else
                      "Off: turn on sync to also turn on email recovery.")

    def _settings_computers(self, c, sync_on):
        self._section(c, "Your computers", "Every computer that has opened your vault. Don't recognize one? "
                                           "Remove it.")
        try:
            items = self.vault.computers()
        except VaultError:
            items = []
        for comp in items:
            card = ctk.CTkFrame(c, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=BORDER)
            card.pack(fill="x", pady=(10, 0))
            words = ctk.CTkFrame(card, fg_color="transparent")
            words.pack(side="left", fill="x", expand=True, padx=16, pady=10)
            top = ctk.CTkFrame(words, fg_color="transparent")
            top.pack(fill="x")
            ctk.CTkLabel(top, text=comp.get("name") or "Computer", font=font(14, "bold"), text_color=TEXT,
                         anchor="w").pack(side="left")
            if comp["this"]:
                ctk.CTkLabel(top, text=" This computer ", font=font(11, "bold"), text_color=ACCENT,
                             fg_color=ACCENT_SOFT, corner_radius=8).pack(side="left", padx=(8, 0))
            if comp.get("removed"):
                line = f"{comp.get('system', '')} · Removed. It signs out the next time it connects."
                color = DANGER
            else:
                line = f"{comp.get('system', '')} · Last used {ago_seconds(comp.get('last') or 0)}"
                color = MUTED
            ctk.CTkLabel(words, text=line, font=font(12), text_color=color, anchor="w").pack(fill="x")
            if not comp["this"] and not comp.get("removed"):
                ctk.CTkButton(card, text="Remove", command=lambda k=comp["key"], n=comp.get("name"):
                              self.remove_computer(k, n), width=90, height=34, corner_radius=10,
                              fg_color=DANGER_SOFT, hover_color=DANGER_BORDER, text_color=SIGNOUT,
                              font=font(13, "bold")).pack(side="right", padx=14)
        if not sync_on:
            ctk.CTkLabel(c, text="Turn on sync to see your other computers here.", font=font(12),
                         text_color=SUBTLE, anchor="w").pack(fill="x", pady=(8, 0))

    def remove_computer(self, key, name):
        if not messagebox.askyesno(
                APP_NAME, f"Remove “{name}” from your HushKey account?\n\n"
                "• That computer signs out and deletes its copy of your vault the next time it connects.\n"
                "• To be safe, all your other computers are also signed out of sync right away. "
                "They'll ask for an email code once, then keep syncing.\n\n"
                "If you don't recognize this computer, also change your master password "
                "(Settings › Security).", parent=self, icon="warning"):
            return
        try:
            self.vault.remove_computer(key)
        except VaultError as exc:
            return self._status(str(exc), DANGER)
        self.show_settings("sync")
        self._status(f"“{name}” was removed.", ACCENT)
        if self.syncer is not None:
            def done(_):
                self._status(f"“{name}” was removed, and other computers were signed out of sync.", ACCENT)
                self.request_sync(delay=0)

            def failed(exc):
                self._status(f"“{name}” was removed. It signs out the next time it syncs.", MUTED)
                self.request_sync(delay=0)
            self.run_quiet(self.syncer.sign_out_others, done, failed)

    def _settings_import(self, c):
        self._section(c, "Import", "Bring your logins over from Google, Chrome, or another password manager.")
        ghost_button(c, "Import Logins", self.open_import, height=40, width=160).pack(anchor="w", pady=(10, 0))
        self._section(c, "Export", "Save an encrypted HushKey backup, or a spreadsheet (CSV) file.")
        ghost_button(c, "Export Logins", self.open_export, height=40, width=160).pack(anchor="w", pady=(10, 0))

    def _settings_about(self, c):
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(row, text="", image=logo_image(56, tile=True)).pack(side="left", padx=(0, 14))
        words = ctk.CTkFrame(row, fg_color="transparent")
        words.pack(side="left")
        wordmark(words, 22).pack(anchor="w")
        ctk.CTkLabel(words, text=f"Version {__version__} · A simple, private password manager",
                     font=font(13), text_color=MUTED).pack(anchor="w")
        slot = ctk.CTkFrame(c, fg_color="transparent", width=1, height=1)
        slot.pack(anchor="w", pady=(10, 0))
        self._update_slot = slot
        if self.update_release is not None:
            self._show_update_link()
        else:
            ctk.CTkLabel(slot, text="You're on the newest version.", font=font(12), text_color=SUBTLE).pack()
        self._section(c, "Your privacy", "Everything is encrypted on your computer. Your master password "
                                         "never leaves it, and nobody else can read your vault.")
        link_button(c, "Help and instructions on GitHub ↗", self.open_help, size=13).pack(anchor="w",
                                                                                        pady=(12, 0))
        ctk.CTkLabel(c, text="Logos from Simple Icons (CC0). Font: Poppins (Open Font License).",
                     font=font(11), text_color=SUBTLE, anchor="w").pack(fill="x", pady=(16, 0))

    # =========================================================== SECURITY TIPS

    def start_leak_check(self):
        """Once per session, in the background. Results stay in memory only."""
        if not self.settings.get("leak_check", True) or getattr(self, "_leak_busy", False) \
                or getattr(self, "_leak_done", False) or not (self.vault and self.vault.is_unlocked):
            return
        hashes = self.vault.password_hashes()
        if not hashes:
            return
        self._leak_busy = True
        vault = self.vault

        def done(ids):
            self._leak_busy = False
            if self.vault is not vault or not vault.is_unlocked:
                return
            self._leak_done = True
            self._leak_checked = time.time()
            # saved with the logins, so the score never jumps on the next open
            current = vault.password_hashes()
            still = {i for i in ids if current.get(i) == hashes.get(i)}   # skip passwords changed meanwhile
            if vault.set_leaked(still):
                self._refresh_current()   # only redraw if a result actually changed

        def failed(_exc):
            self._leak_busy = False   # offline: try again next time

        self.run_quiet(lambda: self.leak_checker(hashes), done, failed)

    def _refresh_current(self):
        if getattr(self, "listbox", None) is not None and self.listbox.winfo_exists():
            self.refresh_rows(keep_scroll=True)
        elif getattr(self, "_on_security", False):
            self.show_security()

    def show_security(self):
        page = self._page_frame()
        self._on_security = True
        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)
        c = ctk.CTkFrame(scroll, fg_color="transparent", width=760)
        c.pack(padx=30, pady=22, fill="x")
        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x")
        ghost_button(top, "←  Vault", self._leave_security, height=36, width=96).pack(side="left")
        checked = getattr(self, "_leak_checked", 0)
        when = ("Leak check: on, checked " + ago_seconds(checked)) if checked else \
            ("Leak check: checking…" if getattr(self, "_leak_busy", False) else
             ("Leak check: off" if not self.settings.get("leak_check", True) else "Leak check: waiting for internet"))
        ctk.CTkLabel(top, text=when, font=font(12), text_color=SUBTLE).pack(side="right")

        head = ctk.CTkFrame(c, fg_color="transparent")
        head.pack(fill="x", pady=(18, 10))
        ring = ctk.CTkLabel(head, text="", compound="center", font=font(34, "bold"), text_color=TEXT)
        ring.pack(side="left", padx=(0, 22))
        words = ctk.CTkFrame(head, fg_color="transparent")
        words.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(words, text="Security tips", font=font(26, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
        summary = ctk.CTkLabel(words, text="", font=font(14), text_color=LABEL, anchor="w", justify="left",
                               wraplength=520)
        summary.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(words, text="These are suggestions, not requirements. Fix what you like and skip the rest.",
                     font=font(12), text_color=MUTED, anchor="w", justify="left", wraplength=520).pack(fill="x")
        tips_box = ctk.CTkFrame(c, fg_color="transparent")
        tips_box.pack(fill="x")
        more_slot = ctk.CTkFrame(c, fg_color="transparent", width=1, height=1)
        more_slot.pack(fill="x")
        # Only a page of tips is built at a time: a card per tip for a big vault took seconds to draw.
        state = {"tips": [], "rows": {}, "more": None}

        def update_head():
            report = self._security_rows()
            score = health_score(self.vault.entry_count, report)
            state["tips"] = [r for r in report if self._tip_visible(r, ignore_setting=True)]
            n = len(state["tips"])
            ring.configure(text=str(score), image=self._health_image(score, 120))
            shape = "great" if score >= 90 else ("good" if score >= 70 else "okay")
            summary.configure(text=(f"Your vault is in {shape} shape. {n} suggestion"
                                    f"{'s' if n != 1 else ''} could make it even safer.")
                              if n else "Nice work! Nothing to suggest right now.")

        def fill(limit, now=4):
            # a few cards right away, the rest a few at a time, so the page shows up at once
            if not tips_box.winfo_exists():
                return   # left the page
            shown, built = state["rows"], 0
            for r in state["tips"]:
                if len(shown) >= limit:
                    break
                if r["id"] in shown:
                    continue
                if built == now:
                    self.after(1, lambda: fill(limit, 3))
                    return
                shown[r["id"]] = tip_row(r)
                built += 1
            if state["more"] is not None:
                state["more"].destroy()
                state["more"] = None
            left = len(state["tips"]) - len(shown)
            if left > 0:
                step = min(left, self.TIPS_PAGE)
                state["more"] = ghost_button(more_slot, f"Show {step} more  ({left} not shown)",
                                             lambda: fill(len(shown) + self.TIPS_PAGE), height=40)
                state["more"].pack(pady=(8, 4))
            if not state["tips"] and not done.winfo_manager():
                done.pack(fill="x", pady=6)

        def act(entry_id, **meta):
            # "Not now" / "Don't remind me" only remove that one card instead of rebuilding the page
            self.vault.set_meta(entry_id, **meta)
            row = state["rows"].pop(entry_id, None)
            if row is not None:
                row.destroy()
            update_head()
            fill(max(len(state["rows"]) + 1, self.TIPS_PAGE))

        def tip_row(r):
            label, why = self._tip_text(r)
            row = ctk.CTkFrame(tips_box, fg_color=SURFACE, corner_radius=14, border_width=1, border_color=BORDER)
            row.pack(fill="x", pady=4)
            img = brand_image(r["icon"], 24)
            ctk.CTkLabel(row, text="" if img else (r["title"][:1] or "?").upper(), image=img, width=42, height=42,
                         corner_radius=10, fg_color=RAISED, text_color=ACCENT,
                         font=font(16, "bold")).pack(side="left", padx=14, pady=12)
            t = ctk.CTkFrame(row, fg_color="transparent")
            t.pack(side="left", fill="x", expand=True)
            line = ctk.CTkFrame(t, fg_color="transparent")
            line.pack(fill="x")
            ctk.CTkLabel(line, text=r["title"], font=font(15, "bold"), text_color=TEXT).pack(side="left")
            ctk.CTkFrame(line, width=7, height=7, corner_radius=4, fg_color=self._tip_color(r)).pack(
                side="left", padx=(10, 6))
            ctk.CTkLabel(line, text=label, font=font(12), text_color=MUTED).pack(side="left")
            ctk.CTkLabel(t, text=why, font=font(12), text_color=MUTED, anchor="w", justify="left",
                         wraplength=380).pack(fill="x")
            for text, cmd, main_btn, w in (("Fix", lambda i=r["id"]: self.open_edit(i, fresh=True), True, 64),
                                           ("Not now", lambda i=r["id"]: act(
                                               i, snooze=time.time() + TIP_SNOOZE_DAYS * 86400), False, 70),
                                           ("Don't remind me", lambda i=r["id"]: act(i, mute=True), False, 124)):
                ctk.CTkButton(row, text=text, command=cmd, height=34, width=w, corner_radius=9,
                              fg_color="transparent", hover_color=ACCENT_SOFT if main_btn else RAISED,
                              border_width=1 if main_btn else 0, border_color=ACCENT,
                              text_color=ACCENT if main_btn else SUBTLE,
                              font=font(13, "bold" if main_btn else "normal")).pack(side="left", padx=(0, 8))
            return row

        done = ctk.CTkFrame(more_slot, fg_color=ACCENT_SOFT, corner_radius=14)
        ctk.CTkLabel(done, text="You're all caught up", font=font(16, "bold"), text_color=ACCENT).pack(pady=(18, 2))
        ctk.CTkLabel(done, text="HushKey will let you know if anything new comes up.", font=font(12),
                     text_color=MUTED).pack(pady=(0, 18))
        update_head()
        fill(self.TIPS_PAGE)

        how = ctk.CTkFrame(c, fg_color="transparent", width=1, height=1)
        how.pack(fill="x", pady=(14, 0))
        box = ctk.CTkLabel(c, text="HushKey turns each password into a scrambled code (a hash) on your computer "
                                   "and sends only the first 5 characters to Have I Been Pwned. Hundreds of "
                                   "passwords share those 5 characters, so nobody learns yours. The final check "
                                   "happens on your computer.", font=font(12), text_color=LABEL, anchor="w",
                           justify="left", wraplength=640, fg_color=SURFACE, corner_radius=10)

        def flip():
            if box.winfo_manager():
                box.pack_forget()
                btn.configure(text="▸  How the leak check keeps your passwords private")
            else:
                box.pack(fill="x", after=how, ipadx=12, ipady=10)
                btn.configure(text="▾  How the leak check keeps your passwords private")
        btn = ctk.CTkButton(how, text="▸  How the leak check keeps your passwords private", command=flip,
                            fg_color="transparent", hover=False, text_color=SUBTLE, font=font(13), anchor="w")
        btn.pack(anchor="w")
        self._switch_row(c, "Show suggestions in my vault", "Adds a small note like “Used twice” next to "
                                                            "logins that could be safer. Your score here still "
                                                            "updates.", "show_suggestions")
        self.status = ctk.CTkLabel(c, text="", font=font(12), text_color=MUTED, anchor="w")
        self.status.pack(fill="x", pady=(12, 0))
        self.start_leak_check()

    def _leave_security(self):
        self._on_security = False
        self.show_main()

    # =========================================================== LOCKED

    def lock_app(self, notice=""):
        """Auto-lock: close the vault but keep who you are, and show a small
        unlock card (no email needed). 'Remember this device' stays on."""
        if not (self.vault and self.vault.is_unlocked):
            return
        self.wipe_clipboard()
        addr = self.vault.email
        self.vault.on_change = None
        self.vault.lock()
        self.vault = None
        self.syncer = None
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkToplevel):
                w.destroy()
        self.last_email = addr
        self.show_locked(addr, notice)

    def show_locked(self, addr, notice=""):
        self._clear()
        c = self._card(width=380)
        ctk.CTkLabel(c, text="", image=logo_image(56)).pack()
        ctk.CTkLabel(c, text="HushKey is locked", font=font(20, "bold"), text_color=TEXT).pack(pady=(8, 0))
        ctk.CTkLabel(c, text=addr, font=font(13), text_color=MUTED).pack(pady=(2, 14))
        pw = PasswordField(c, "Master password", width=316)
        pw.pack(fill="x")
        say = self._message(c)
        if notice:
            say(notice, ok=True)

        def submit(_e=None):
            if not pw.get():
                return say("Enter your master password.")
            wait = self.wait_until - time.time()
            if wait > 0:
                return say(f"Too many tries. Wait {int(wait) + 1}s and try again.")
            v = self._vault_for(addr)

            def ok_cb(_):
                self.failed = 0
                self._after_password(v, addr, say, btn)

            def err_cb(exc):
                if isinstance(exc, WrongPassword):
                    self.failed += 1
                    delay = min(60, 2 ** self.failed) if self.failed >= 3 else 0
                    self.wait_until = time.time() + delay
                    pw.set("")
                    say("Wrong master password." + (f" Wait {delay}s before trying again." if delay else ""))
                else:
                    say(self._err_text(exc))
            typed = pw.get()
            self.run_bg(lambda: v.unlock(typed), ok_cb, err_cb, btn, "Unlocking…")

        btn = primary_button(c, "Unlock", submit, height=44)
        btn.pack(fill="x", pady=(12, 0))
        pw.bind_enter(submit)
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(pady=(12, 0))
        link_button(row, "Forgot password?", lambda: self.show_forgot_email(addr), size=12,
                    color=MUTED).pack(side="left")
        ctk.CTkLabel(row, text="·", text_color=SUBTLE).pack(side="left", padx=6)
        def sign_out():
            self._forget_auto_signin(addr)   # a real sign out: next time asks for the password
            self.show_signin("You're signed out.", ok=True)
        link_button(row, "Sign out", sign_out, size=12, color=MUTED).pack(side="left")
        pw.focus()

    # ------------------------------------------------------------ sign out

    def sign_out(self, notice="", forget=True):
        """Sign out. The Sign out button also turns off 'Remember this device',
        so the next time HushKey opens it asks for the master password.
        (Closing the window, or the 5-minute auto-lock, does not.)"""
        self.wipe_clipboard()
        if self.vault:
            if forget and self.vault.is_unlocked:
                try:
                    self.vault.disable_auto_signin()
                except VaultError:
                    pass
                self._forget_auto_signin(self.vault.email)
            self.vault.lock()
        self.vault = None
        if self.vault is not None:
            self.vault.on_change = None
        self.syncer = None
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkToplevel):
                w.destroy()
        self.vault = None
        self.show_signin(notice or "You're signed out.", ok=True)
        if forget and self.update_release is not None:
            self.after(400, self.show_update_dialog)   # end of a session: offer the update

    def quit_app(self):
        """Closing the window (X / red button) keeps 'Remember this device'.
        If an update is downloaded, it installs now, so the next time you open
        HushKey you're on the newest version."""
        self.wipe_clipboard()
        self._save_window()
        if self.vault:
            self.vault.on_change = None
            self.vault.lock()
        if self.update_file and not self._installing:
            self._start_install(relaunch=False)
        self.destroy()

    # ------------------------------------------------------------ updates

    UPDATE_CHECK_MINUTES = 10   # while HushKey is open it keeps looking for a new release

    def check_for_update(self):
        # look again in a while, so a release published while HushKey is open still shows up
        job = getattr(self, "_update_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._update_job = self.after(self.UPDATE_CHECK_MINUTES * 60 * 1000, self.check_for_update)
        if getattr(self, "_update_checking", False) or getattr(self, "_installing", False):
            return

        def found(release):
            self._update_checking = False
            if release is None:
                return
            if self.update_release is not None and self.update_release.version == release.version:
                return   # already told them about this one
            self.update_release = release
            self.update_file = None   # an older download (if any) is not the newest any more
            self._show_update_link()
            ok, reason = self.updater.can_install()
            self.update_error = "" if ok else reason
            self.show_update_dialog()
            if ok:
                self.run_quiet(lambda: self.updater.download(release), self._update_downloaded,
                               self._update_failed)

        def offline(_exc):
            self._update_checking = False   # no internet: the next check tries again
        self._update_checking = True
        self.run_quiet(self.updater.check, found, offline)

    def _show_update_link(self):
        """A small gold 'update' link on the current screen."""
        if getattr(self, "glass", None) is not None and self.glass.winfo_exists():
            return self.glass.redraw()
        slot = getattr(self, "_update_slot", None)
        if self.update_release is None or slot is None or not slot.winfo_exists() or slot.winfo_children():
            return
        link_button(slot, f"HushKey v{self.update_release.version} is ready: update now",
                    self.show_update_dialog, size=12, color=GOLD).pack()

    def _update_downloaded(self, path):
        self.update_file = path
        dlg = self._update_dialog()
        if dlg is not None:
            dlg.downloaded()

    def _update_failed(self, exc):
        self.update_error = str(exc) if isinstance(exc, updater_mod.UpdateError) else \
            "The update couldn't be downloaded. HushKey will try again next time."
        dlg = self._update_dialog()
        if dlg is not None:
            dlg.failed(self.update_error)

    def _update_dialog(self):
        for w in self.winfo_children():
            if isinstance(w, UpdateDialog) and w.winfo_exists():
                return w
        return None

    def show_update_dialog(self):
        if self.update_release is None:
            return
        dlg = self._update_dialog()
        if dlg is None:
            UpdateDialog(self, self.update_release)
        else:
            dlg.lift()

    def update_now(self):
        if not self.update_file:
            return
        if self.vault:
            self.vault.on_change = None
        self._start_install(relaunch=True)
        self.wipe_clipboard()
        self._save_window()
        self.destroy()

    def _start_install(self, relaunch):
        try:
            self._installing = True
            self.updater.install(self.update_file, relaunch=relaunch)
        except Exception:
            self._installing = False
            traceback.print_exc()


# ==========================================================================
# Pop-up windows
# ==========================================================================

class Dialog(ctk.CTkToplevel):
    def __init__(self, app: HushKeyApp, title, width=500):
        super().__init__(app, fg_color=SURFACE)
        self.app = app
        self.title(title)
        self.resizable(False, False)
        self.transient(app)
        self.inner = ctk.CTkFrame(self, fg_color="transparent", width=width - 56)
        self.inner.pack(padx=28, pady=24, fill="both", expand=True)
        self.bind("<Escape>", lambda _e: self.destroy(), add="+")
        # Windows opens pop-ups behind the main window sometimes, and
        # CustomTkinter swaps in its own icon after 200ms; fix both.
        self.after(250, self._front)

    def center(self):
        """Put the pop-up in the middle of the HushKey window (kept on screen)."""
        import tkinter
        try:
            self.update_idletasks()
            w = max(self.winfo_reqwidth(), self.winfo_width(), 1)
            h = max(self.winfo_reqheight(), self.winfo_height(), 1)
            x = self.app.winfo_rootx() + (self.app.winfo_width() - w) // 2
            y = self.app.winfo_rooty() + (self.app.winfo_height() - h) // 2
            x = max(0, min(x, self.winfo_screenwidth() - w))
            y = max(0, min(y, self.winfo_screenheight() - h - 48))
            tkinter.Wm.wm_geometry(self, f"+{x}+{y}")  # pixels, so no extra scaling
        except Exception:
            traceback.print_exc()

    def _front(self):
        if self.winfo_exists():
            set_window_icon(self)
            self.center()
            self.lift()
            self.focus_force()
            try:
                self.grab_set()
            except Exception:
                pass


class EntryDialog(Dialog):
    def __init__(self, app, title, current, on_save, on_delete=None, fresh=False):
        super().__init__(app, title)
        self.on_save, self.on_delete = on_save, on_delete
        self.generated = 0
        c = self.inner
        ctk.CTkLabel(c, text=title, font=font(20, "bold"), text_color=TEXT, anchor="w").pack(fill="x")

        field_label(c, "Client name").pack(fill="x", pady=(14, 0))
        self.name = entry(c, "Type client name", width=FIELD_WIDTH + 68)
        self.name.pack(fill="x", pady=(6, 10))

        self.logo = LogoPicker(c, slug=(current or {}).get("icon", ""))
        self.logo.pack(fill="x", pady=(0, 6))
        self.name.bind("<KeyRelease>", lambda _e: self.logo.suggest_from(self.name.get()), add="+")

        field_label(c, "Username").pack(fill="x")
        self.user = entry(c, "Type username or email", width=FIELD_WIDTH + 68)
        self.user.pack(fill="x", pady=(6, 10))

        field_label(c, "Password").pack(fill="x")
        self.pw = PasswordField(c, "Type a password, or generate below", width=FIELD_WIDTH + 68)
        self.pw.pack(fill="x", pady=(6, 6))
        self.bar = StrengthBar(c)
        self.bar.pack(fill="x")
        self.pw.bind_key(lambda _e: self.bar.update_for(self.pw.get()))

        # Password generator: the new password is only shown and copied, never typed in for you,
        # so your current password can't be replaced by accident. You paste it in yourself.
        self.gen = ctk.CTkButton(c, text="Generate a strong password", command=self.generate, height=32, width=0,
                                 corner_radius=9, fg_color="transparent", hover_color=ACCENT_SOFT,
                                 border_width=1, border_color=ACCENT, text_color=ACCENT, font=font(13, "bold"))
        self.gen.pack(anchor="w", pady=(12, 0))
        self.gen_box = ctk.CTkFrame(c, fg_color=RAISED, corner_radius=10)
        row = ctk.CTkFrame(self.gen_box, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(10, 4))
        self.gen_out = ctk.CTkEntry(row, height=34, corner_radius=8, fg_color=BG, border_color=BORDER,
                                    text_color=TEXT, font=font(14, mono=True))
        self.gen_out.pack(side="left", fill="x", expand=True)
        primary_button(row, "Copy", self.copy_generated, width=64, height=34).pack(side="left", padx=(8, 0))
        ctk.CTkButton(row, text="New one", command=self.generate, width=74, height=34, corner_radius=8,
                      fg_color="transparent", hover_color=BORDER, border_width=1, border_color=BORDER,
                      text_color=TEXT, font=font(12)).pack(side="left", padx=(6, 0))
        paste = "Cmd+V" if IS_MAC else "Ctrl+V"
        self.gen_hint = ctk.CTkLabel(
            self.gen_box, text=f"To use it: click Copy, then paste it into the Password box above ({paste}). "
                               + ("Your current password stays until you paste the new one in."
                                  if current else "It's only saved once it's pasted in."),
            font=font(12), text_color=GOLD, anchor="w", justify="left", wraplength=420)
        self.gen_hint.pack(fill="x", padx=12, pady=(0, 10))
        self.pw.bind_key(lambda _e: self._check_pasted())
        self.pw.entry.bind("<<Paste>>", lambda _e: self.after(20, self._check_pasted), add="+")

        self.say = ctk.CTkLabel(c, text="", font=font(13), text_color=DANGER, anchor="w")
        self.say.pack(fill="x", pady=(8, 0))

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        if on_delete:
            ctk.CTkButton(row, text="Delete", command=self.delete, width=90, height=44, corner_radius=10,
                          fg_color="transparent", hover_color=DANGER_SOFT, border_width=1,
                          border_color=DANGER_BORDER, text_color=DANGER, font=font(14)).pack(side="left")
        primary_button(row, "Save Login", self.save, width=130, height=44).pack(side="right")
        ghost_button(row, "Cancel", self.destroy, width=100, height=44).pack(side="right", padx=(0, 10))

        if current:
            self.name.insert(0, current["title"])
            self.user.insert(0, current["username"])
            self.pw.set(current["password"])
            self.bar.update_for(current["password"])
        if fresh:   # "Make a stronger one" / "Fix": show a new strong password to copy in
            self.generate()
        self.bind("<Return>", self._enter_key)
        self.bind("<Escape>", self._escape)
        self.center()
        self.after(300, self.name.focus_set)

    def _escape(self, _e=None):
        """Escape closes the logo list first; pressed again it closes the form."""
        if self.logo.open:
            self.logo.hide_results()
            return "break"
        self.destroy()

    def _enter_key(self, event=None):
        # Enter in the logo search picks the top logo instead of saving
        if event is not None and str(event.widget).startswith(str(self.logo.search)):
            return
        self.save()

    def generate(self):
        """Make a new password and SHOW it (read-only). It doesn't touch the
        Password box: the user copies and pastes it in on purpose."""
        self.generated += 1
        self.new_password = generate_password()
        self.gen_out.configure(state="normal")
        self.gen_out.delete(0, "end")
        self.gen_out.insert(0, self.new_password)
        self.gen_out.configure(state="readonly")   # can be selected and copied, not typed in
        if not self.gen_box.winfo_ismapped():
            self.gen_box.pack(fill="x", pady=(8, 0), after=self.gen)
            self.gen.pack_forget()
        self._check_pasted()

    def copy_generated(self):
        self.app.copy_text(self.new_password, "New password")
        self.gen_hint.configure(text="Copied! Now paste it into the Password box above "
                                     f"({'Cmd' if IS_MAC else 'Ctrl'}+V).", text_color=GOLD)

    def _check_pasted(self):
        """Tell the user when the new password is really in the Password box."""
        if self.bar is not None:
            self.bar.update_for(self.pw.get())
        new = getattr(self, "new_password", "")
        if new and self.pw.get() == new:
            self.gen_hint.configure(text="Pasted. Click Save Login to keep it, and change it on the website "
                                         "too.", text_color=ACCENT)

    def save(self):
        title, user, pw = self.name.get().strip(), self.user.get().strip(), self.pw.get()
        if not title:
            return self.say.configure(text="Type a client name first.")
        if not pw:
            return self.say.configure(text="Type or paste a password first.")
        try:
            self.on_save(title, user, pw, self.logo.slug)
        except VaultError as exc:
            return self.say.configure(text=str(exc))
        self.destroy()

    def delete(self):
        if messagebox.askyesno(APP_NAME, f"Delete “{self.name.get()}”? This can't be undone.",
                               parent=self, icon="warning"):
            try:
                self.on_delete()
            except VaultError as exc:
                return self.say.configure(text=str(exc))
            self.destroy()


class ChangeMasterWarning(Dialog):
    """'Are you sure?' before changing the master password."""

    def __init__(self, app):
        super().__init__(app, "Change master password", width=460)
        c = self.inner
        ctk.CTkLabel(c, text="⚠", font=font(30), text_color=WARN).pack(anchor="w")
        ctk.CTkLabel(c, text="Are you sure?", font=font(20, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(c, text="Your master password unlocks everything. After you change it:\n\n"
                             "•  Use the new one on every computer you use HushKey on.\n"
                             "•  The old one stops working right away.\n"
                             "•  Write it down somewhere safe if you need to.",
                     font=font(13), text_color=LABEL, anchor="w", justify="left", wraplength=400).pack(
            fill="x", pady=(8, 10))
        box, self.agree = checkbox(c, "I understand, and I'll remember my new password", checked=False)
        box.pack(fill="x")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(18, 0))
        self.go = ctk.CTkButton(row, text="Continue", command=self.next, width=130, height=42, corner_radius=10,
                                fg_color=WARN, hover_color=WARN_HOVER, text_color=("#FFFFFF", "#2A1606"),
                                font=font(14, "bold"), state="disabled")
        self.go.pack(side="right")
        ghost_button(row, "Cancel", self.destroy, width=100, height=42).pack(side="right", padx=(0, 10))
        self.agree.trace_add("write", lambda *_: self.go.configure(
            state="normal" if self.agree.get() else "disabled"))
        self.center()

    def next(self):
        if not self.agree.get():
            return
        app = self.app
        self.destroy()
        ChangeMasterDialog(app)


class ChangeMasterDialog(Dialog):
    def __init__(self, app):
        super().__init__(app, "Change master password")
        c = self.inner
        ctk.CTkLabel(c, text="Change master password", font=font(20, "bold"), text_color=TEXT,
                     anchor="w").pack(fill="x")
        field_label(c, "Current master password").pack(fill="x", pady=(16, 0))
        self.current = PasswordField(c, "Your current password")
        self.current.pack(fill="x", pady=(6, 12))
        field_label(c, "New master password").pack(fill="x")
        self.new = PasswordField(c, f"At least {MIN_MASTER_LENGTH} characters", visible=True)
        self.new.pack(fill="x", pady=(6, 6))
        bar = StrengthBar(c)
        bar.pack(fill="x", pady=(0, 12))
        self.new.bind_key(lambda _e: bar.update_for(self.new.get()))
        field_label(c, "Retype new password (hidden, from memory)").pack(fill="x")
        self.again = PasswordField(c, "Type it again", toggle=False)
        self.again.pack(fill="x", pady=(6, 0))
        self.say = ctk.CTkLabel(c, text="", font=font(13), text_color=DANGER, anchor="w", wraplength=420)
        self.say.pack(fill="x", pady=(8, 0))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        self.ok = primary_button(row, "Change password", self.submit, width=170, height=44)
        self.ok.pack(side="right")
        ghost_button(row, "Cancel", self.destroy, width=100, height=44).pack(side="right", padx=(0, 10))
        self.bind("<Return>", lambda _e: self.submit())
        self.center()

    def submit(self):
        cur, new, again = self.current.get(), self.new.get(), self.again.get()
        vault = self.app.vault

        def done(_):
            if self.winfo_exists():
                self.destroy()
            self.app._status(text="Master password changed.", text_color=ACCENT)

        def fail(exc):
            if self.winfo_exists():
                self.say.configure(text=self.app._err_text(exc))

        self.app.run_bg(lambda: vault.change_master(cur, new, again), done, fail, self.ok, "Saving…")


class ImportDialog(Dialog):
    """Import passwords: Google instructions -> choose the export file ->
    review and Accept or Decline -> import and delete the file."""

    def __init__(self, app):
        super().__init__(app, "Import passwords", width=600)
        self.vars = []
        self.show_instructions()

    def _reset(self):
        for w in self.inner.winfo_children():
            w.destroy()

    def _title(self, title, sub=""):
        ctk.CTkLabel(self.inner, text=title, font=font(20, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
        if sub:
            ctk.CTkLabel(self.inner, text=sub, font=font(13), text_color=MUTED, anchor="w", justify="left",
                         wraplength=520).pack(fill="x", pady=(4, 0))

    def _error_label(self):
        self.say = ctk.CTkLabel(self.inner, text="", font=font(13), text_color=DANGER, anchor="w",
                                justify="left", wraplength=520)
        self.say.pack(fill="x", pady=(8, 0))

    def _buttons(self, left_text, left_cmd, right_text, right_cmd):
        row = ctk.CTkFrame(self.inner, fg_color="transparent")
        row.pack(fill="x", pady=(12, 0))
        ok = primary_button(row, right_text, right_cmd, height=44)
        ok.pack(side="right")
        ghost_button(row, left_text, left_cmd, width=110, height=44).pack(side="right", padx=(0, 10))
        return ok

    # ---- step 1: how to get the file from Google ---------------------------

    def show_instructions(self):
        self._reset()
        self._title("Import passwords",
                    "Bring your passwords over from Google in about a minute. They're encrypted into "
                    "HushKey on this computer only. Nothing is uploaded.")
        box = ctk.CTkFrame(self.inner, fg_color=RAISED, corner_radius=12)
        box.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(box, text="Get your passwords from Google", font=font(15, "bold"), text_color=TEXT,
                     anchor="w").pack(fill="x", padx=16, pady=(14, 6))
        steps = [
            "Open Google Chrome on this computer.",
            "Click the ⋮ menu (top right) → Passwords and autofill → Google Password Manager.",
            "Click Settings → Export passwords → Download file. Google may ask for your "
            "computer's password to confirm it's you.",
            "Come back here and click “Choose the file”. It's usually in your Downloads "
            "folder, named “Google Passwords.csv”.",
        ]
        for n, text in enumerate(steps, 1):
            line = ctk.CTkFrame(box, fg_color="transparent")
            line.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(line, text=str(n), width=26, height=26, corner_radius=13, fg_color=ACCENT,
                         text_color=ACCENT_INK, font=font(12, "bold")).pack(side="left", anchor="n")
            ctk.CTkLabel(line, text=text, font=font(13), text_color=TEXT, anchor="w", justify="left",
                         wraplength=440).pack(side="left", padx=(10, 0), fill="x")
        link_button(box, "No Chrome? Open Google Password Manager in my browser",
                    self.open_google).pack(anchor="w", padx=12, pady=(6, 12))
        ctk.CTkLabel(self.inner, text="Coming from another app? Exports from Bitwarden, LastPass, 1Password, "
                                      "Apple Passwords, Microsoft Edge, Firefox and Dashlane work too, and so "
                                      "does a HushKey backup (.hushkey).",
                     font=font(12), text_color=SUBTLE, anchor="w", justify="left",
                     wraplength=520).pack(fill="x", pady=(10, 0))
        self._error_label()
        self._buttons("Cancel", self.destroy, "Choose the file…", self.choose_file)
        self.center()

    def open_google(self):
        import webbrowser
        webbrowser.open("https://passwords.google.com")
        self.say.configure(text="Opened passwords.google.com. Click the ⚙ Settings icon → Export passwords "
                                "→ Export, then come back here.", text_color=ACCENT)

    def choose_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self, title="Choose your password export",
            filetypes=[("Password exports", "*.csv *.hushkey"), ("All files", "*.*")])
        if not path:
            return
        if path.lower().endswith(".hushkey"):
            return self.show_backup_password(path)
        try:
            result = importer.read_csv_file(path, self.app.vault.existing_keys())
        except importer.ImportError_ as exc:
            return self.say.configure(text=str(exc), text_color=DANGER)
        except OSError:
            return self.say.configure(text="HushKey couldn't open that file.", text_color=DANGER)
        self.show_review(path, result)

    # ---- step 1b: a HushKey backup needs its master password -----------------

    def show_backup_password(self, path):
        self._reset()
        self._title("Open your HushKey backup",
                    f"“{os.path.basename(path)}” is encrypted. Type the master password you had when "
                    "you made this backup.")
        pw = PasswordField(self.inner, "Backup's master password", width=FIELD_WIDTH + 140)
        pw.pack(fill="x", pady=(14, 0))
        self._error_label()

        def open_it(_e=None):
            typed = pw.get()

            def work():
                b = Vault.open_backup(path, typed)
                try:
                    entries = b.all_entries()
                finally:
                    b.lock()
                existing = {(t.lower(), u.lower()) for t, u in self.app.vault.existing_keys()}
                items = []
                for e in entries:
                    dup = (e["title"].lower(), e["username"].lower()) in existing
                    items.append(importer.Item(title=e["title"], username=e["username"],
                                               password=e["password"], url=e.get("url", ""),
                                               icon=e.get("icon", ""), duplicate=dup, selected=not dup))
                return importer.ImportResult(source="HushKey backup", items=items)

            def fail(exc):
                if self.winfo_exists():
                    self.say.configure(text=self.app._err_text(exc), text_color=DANGER)

            self.app.run_bg(work, lambda res: self.winfo_exists() and self.show_review(path, res, backup=True),
                            fail, ok, "Opening…")

        ok = self._buttons("Back", self.show_instructions, "Open backup", open_it)
        pw.bind_enter(open_it)
        pw.focus()
        self.center()

    # ---- step 2: review, then Accept or Decline ------------------------------

    def show_review(self, path, result, backup=False):
        self._reset()
        n = len(result.items)
        dups = sum(1 for i in result.items if i.duplicate)
        sub = f"Found {n} login{'s' if n != 1 else ''} in “{os.path.basename(path)}” ({result.source})."
        if dups:
            sub += f" {dups} already {'is' if dups == 1 else 'are'} in HushKey and won't be added twice."
        if result.skipped:
            sub += f" {result.skipped} item{'s' if result.skipped != 1 else ''} without a password were skipped."
        self._title("Review before importing", sub)

        bar = ctk.CTkFrame(self.inner, fg_color="transparent")
        bar.pack(fill="x", pady=(10, 4))
        self.count = ctk.CTkLabel(bar, text="", font=font(12, "bold"), text_color=MUTED)
        self.count.pack(side="left")
        link_button(bar, "Select none", lambda: self._set_all(False), size=12).pack(side="right")
        link_button(bar, "Select all", lambda: self._set_all(True), size=12).pack(side="right", padx=(0, 8))

        rows = ctk.CTkScrollableFrame(self.inner, height=260, fg_color=RAISED, corner_radius=12)
        rows.pack(fill="x")
        # every login gets its tick box value now; the rows themselves are drawn
        # a few at a time so a 500-login Google export doesn't freeze the window
        self.vars = [(item, ctk.BooleanVar(value=item.selected)) for item in result.items]
        self._review_rows = rows
        self._review_token = object()
        self._draw_review(0, self._review_token)
        self._update_count()

        note = ctk.CTkFrame(self.inner, fg_color=ACCENT_SOFT, corner_radius=12)
        note.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(note, text="When you click Accept, the selected logins are encrypted into your vault on "
                                "this computer. Nothing is uploaded, and passwords stay hidden until you "
                                "click them.", font=font(12), text_color=TEXT, anchor="w", justify="left",
                     wraplength=500).pack(fill="x", padx=14, pady=10)
        self.delete_var = None
        if not backup:
            box, self.delete_var = checkbox(
                self.inner, f"Delete “{os.path.basename(path)}” after importing "
                            "(recommended: it isn't encrypted)", checked=True)
            box.pack(fill="x", pady=(10, 0))
        self._error_label()

        def accept():
            chosen = [it for it, var in self.vars if var.get()]
            if not chosen:
                return self.say.configure(text="Tick at least one login, or click Decline.", text_color=DANGER)
            try:
                added = self.app.vault.add_many([it.__dict__ for it in chosen])
            except VaultError as exc:
                return self.say.configure(text=str(exc), text_color=DANGER)
            msg = f"Imported {added} login{'s' if added != 1 else ''}."
            if self.delete_var is not None and self.delete_var.get():
                if importer.secure_delete(path):
                    msg += f" “{os.path.basename(path)}” was securely deleted."
                else:
                    msg += f" Couldn't delete “{os.path.basename(path)}”: please delete it yourself."
            self.app.refresh_rows()
            self.app._status(text=msg, text_color=ACCENT)
            self.destroy()

        def decline():
            if not backup:
                self.app._status(
                    text="Import cancelled, nothing was added. Your export file wasn't touched: "
                         "delete it when you're done, since it isn't encrypted.", text_color=MUTED)
            self.destroy()

        self.accept_btn = self._buttons("Decline", decline, "Accept & import", accept)
        self._update_count()
        self.center()

    def _draw_review(self, start, token, batch=25):
        if token is not self._review_token or not self._review_rows.winfo_exists():
            return
        stop = min(start + batch, len(self.vars))
        for item, var in self.vars[start:stop]:
            line = ctk.CTkFrame(self._review_rows, fg_color="transparent")
            line.pack(fill="x", padx=4, pady=2)
            box, _ = checkbox(line, "", var=var)
            box.configure(width=24, command=self._update_count)
            box.pack(side="left")
            img = brand_image(item.icon, 22)
            ctk.CTkLabel(line, text="" if img else (item.title[:1] or "?").upper(), image=img, width=34,
                         height=34, corner_radius=8, fg_color=SURFACE, text_color=ACCENT,
                         font=font(13, "bold")).pack(side="left", padx=(2, 10))
            names = ctk.CTkFrame(line, fg_color="transparent")
            names.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(names, text=item.title, font=font(13, "bold"), text_color=TEXT, anchor="w",
                         height=18).pack(fill="x")
            ctk.CTkLabel(names, text=item.username or "(no username)", font=font(11), text_color=MUTED,
                         anchor="w", height=16).pack(fill="x")
            if item.duplicate:
                ctk.CTkLabel(line, text="Already in HushKey", font=font(11, "bold"), text_color=GOLD,
                             fg_color=GOLD_SOFT, corner_radius=6, height=22).pack(side="right", padx=6)
        if stop < len(self.vars):
            self.after(1, lambda: self._draw_review(stop, token))

    def _set_all(self, value):
        for _item, var in self.vars:
            var.set(value)
        self._update_count()

    def _update_count(self):
        picked = sum(1 for _i, v in self.vars if v.get())
        if getattr(self, "count", None) is not None and self.count.winfo_exists():
            self.count.configure(text=f"{picked} of {len(self.vars)} selected")
        if getattr(self, "accept_btn", None) is not None and self.accept_btn.winfo_exists():
            self.accept_btn.configure(text=f"Accept & import {picked}")


class ExportDialog(Dialog):
    """Export: an encrypted backup (recommended) or a plain CSV for moving to
    another password manager (asks for the master password first)."""

    def __init__(self, app):
        super().__init__(app, "Export your vault", width=560)
        c = self.inner
        ctk.CTkLabel(c, text="Export your vault", font=font(20, "bold"), text_color=TEXT, anchor="w").pack(fill="x")

        a = ctk.CTkFrame(c, fg_color=ACCENT_SOFT, corner_radius=12, border_width=1, border_color=ACCENT)
        a.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(a, text="Encrypted backup (.hushkey)  ·  recommended", font=font(14, "bold"),
                     text_color=ACCENT, anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        ctk.CTkLabel(a, text="A locked copy of your whole vault. Safe to keep on a USB drive or in cloud "
                             "storage: it only opens with your master password. To restore it, click "
                             "Import and choose the file.", font=font(12), text_color=TEXT, anchor="w",
                     justify="left", wraplength=470).pack(fill="x", padx=16)
        primary_button(a, "Save encrypted backup…", self.save_backup, height=40).pack(anchor="w", padx=16, pady=12)

        b = ctk.CTkFrame(c, fg_color=DANGER_SOFT, corner_radius=12, border_width=1, border_color=DANGER_BORDER)
        b.pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(b, text="Spreadsheet (.csv)  ·  NOT encrypted", font=font(14, "bold"),
                     text_color=DANGER, anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        ctk.CTkLabel(b, text="Only for moving to another password manager. Anyone who opens this file can "
                             "read every password, so delete it right after you've imported it.",
                     font=font(12), text_color=TEXT, anchor="w", justify="left",
                     wraplength=470).pack(fill="x", padx=16)
        self.pw = PasswordField(b, "Type your master password to confirm", width=FIELD_WIDTH + 40)
        self.pw.pack(fill="x", padx=16, pady=(10, 0))
        ctk.CTkButton(b, text="Save unencrypted CSV…", command=self.save_csv, height=40, corner_radius=10,
                      fg_color="transparent", hover_color=DANGER_SOFT, border_width=1, border_color=DANGER,
                      text_color=DANGER, font=font(14, "bold")).pack(anchor="w", padx=16, pady=12)

        self.say = ctk.CTkLabel(c, text="", font=font(13), text_color=DANGER, anchor="w", justify="left",
                                wraplength=500)
        self.say.pack(fill="x", pady=(10, 0))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        ghost_button(row, "Close", self.destroy, width=100, height=44).pack(side="right")
        self.center()

    def save_backup(self):
        from datetime import date
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self, title="Save encrypted backup", defaultextension=".hushkey",
            initialfile=f"HushKey backup {date.today().isoformat()}.hushkey",
            filetypes=[("HushKey backup", "*.hushkey")])
        if not path:
            return
        try:
            self.app.vault.export_backup(path)
        except (OSError, VaultError) as exc:
            return self.say.configure(text=f"Couldn't save the backup: {exc}", text_color=DANGER)
        self.say.configure(text=f"Encrypted backup saved: {os.path.basename(path)}", text_color=ACCENT)

    def save_csv(self):
        from tkinter import filedialog
        if not self.app.vault.check_master(self.pw.get()):
            self.pw.set("")
            return self.say.configure(text="That's not your master password.", text_color=DANGER)
        path = filedialog.asksaveasfilename(
            parent=self, title="Save unencrypted CSV", defaultextension=".csv",
            initialfile="HushKey passwords.csv", filetypes=[("CSV spreadsheet", "*.csv")])
        if not path:
            return
        try:
            importer.write_csv(path, self.app.vault.all_entries())
        except (OSError, VaultError) as exc:
            return self.say.configure(text=f"Couldn't save the file: {exc}", text_color=DANGER)
        self.pw.set("")
        self.say.configure(text=f"Saved {os.path.basename(path)}. Delete it as soon as you've imported it "
                                "into the other app.", text_color=GOLD)


class UpdateDialog(Dialog):
    """'A new version of HushKey is ready': what's new + Update now / Later."""

    def __init__(self, app, release):
        super().__init__(app, "Update available", width=520)
        self.release = release
        c = self.inner
        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text="", image=logo_image(48)).pack(side="left", padx=(0, 12))
        names = ctk.CTkFrame(top, fg_color="transparent")
        names.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(names, text="A new version of HushKey is ready", font=font(18, "bold"),
                     text_color=TEXT, anchor="w").pack(fill="x")
        pills = ctk.CTkFrame(names, fg_color="transparent")
        pills.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(pills, text=f"  v{release.version}  ", font=font(12, "bold"), text_color=ACCENT_INK,
                     fg_color=ACCENT, corner_radius=8, height=24).pack(side="left")
        ctk.CTkLabel(pills, text=f"You have v{__version__}", font=font(12), text_color=MUTED).pack(
            side="left", padx=(8, 0))

        ctk.CTkLabel(c, text="WHAT'S NEW", font=font(11, "bold"), text_color=ACCENT, anchor="w").pack(
            fill="x", pady=(16, 4))
        notes = ctk.CTkTextbox(c, height=150, fg_color=RAISED, text_color=TEXT, corner_radius=10,
                               font=font(13), wrap="word", border_width=0)
        notes.pack(fill="x")
        notes.insert("1.0", release.notes)
        notes.configure(state="disabled")

        self.state_label = ctk.CTkLabel(c, text="", font=font(12), text_color=SUBTLE, anchor="w",
                                        justify="left", wraplength=440)
        self.state_label.pack(fill="x", pady=(10, 0))

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(12, 0))
        self.now_btn = primary_button(row, "Update now", self.update_now, width=150, height=44)
        self.now_btn.pack(side="right")
        ghost_button(row, "Later", self.later, width=100, height=44).pack(side="right", padx=(0, 10))

        if app.update_error and not app.update_file:
            self.failed(app.update_error)
        elif app.update_file:
            self.downloaded()
        else:
            self.now_btn.configure(state="disabled", text="Downloading…")
            self.state_label.configure(text="Downloading the update in the background…")
        self.center()

    def downloaded(self):
        if not self.winfo_exists():
            return
        self.now_btn.configure(state="normal", text="Update now")
        self.state_label.configure(
            text="Ready. Update now (takes a few seconds and reopens HushKey), or click Later and "
                 "it updates by itself the next time you close HushKey. Your vault is kept.",
            text_color=MUTED)

    def failed(self, reason):
        if not self.winfo_exists():
            return
        self.state_label.configure(text=reason, text_color=GOLD)
        self.now_btn.configure(state="normal", text="Download page", command=self.open_page)

    def open_page(self):
        import webbrowser
        repo = getattr(self.app.updater, "repo", "")
        webbrowser.open(f"https://github.com/{repo}/releases/latest" if repo else "https://github.com")
        self.destroy()

    def update_now(self):
        self.now_btn.configure(state="disabled", text="Updating…")
        self.update_idletasks()
        self.app.update_now()

    def later(self):
        if self.app.update_file:
            self.app.status_message("The update will install when you close HushKey.")
        self.destroy()


class CombineDialog(Dialog):
    """Two different vaults (made separately on two computers) for one
    account: combine them into the one that's already synced."""

    def __init__(self, app, cloud_data):
        super().__init__(app, "Combine your vaults", width=540)
        self.cloud_data = cloud_data
        c = self.inner
        ctk.CTkLabel(c, text="Combine your vaults", font=font(20, "bold"), text_color=TEXT,
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(c, text="Your HushKey account already has a vault from another computer, and this "
                             "computer has a different one. To sync, HushKey will add the logins from this "
                             "computer into your account's vault. Nothing is deleted.\n\n"
                             "Enter the master password you use on your other computer. From now on it's "
                             "your master password everywhere.",
                     font=font(13), text_color=MUTED, anchor="w", justify="left",
                     wraplength=470).pack(fill="x", pady=(6, 0))
        self.pw = PasswordField(c, "Master password from your other computer", width=FIELD_WIDTH + 100)
        self.pw.pack(fill="x", pady=(14, 0))
        self.say = ctk.CTkLabel(c, text="", font=font(13), text_color=DANGER, anchor="w", justify="left",
                                wraplength=470)
        self.say.pack(fill="x", pady=(8, 0))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        self.ok = primary_button(row, "Combine", self.combine, width=140, height=44)
        self.ok.pack(side="right")
        ghost_button(row, "Not now", self.destroy, width=110, height=44).pack(side="right", padx=(0, 10))
        self.pw.bind_enter(lambda _e: self.combine())
        self.center()

    def combine(self):
        typed, app = self.pw.get(), self.app

        def opened(other):
            v = app.vault
            if v is None or not v.is_unlocked:
                return
            remembered = app.settings.get("auto_signin_email") == v.email
            copied = v.adopt(other)
            other.lock()
            if remembered:
                app._remember_device(v, v.email)
            app._sync_blocked = False
            app.refresh_rows()
            app.status_message(f"Vaults combined: {copied} login{'s' if copied != 1 else ''} added. "
                               "Use your other computer's master password from now on.", ok=True)
            app.request_sync(delay=0)
            if self.winfo_exists():
                self.destroy()

        def failed(exc):
            if self.winfo_exists():
                self.ok.configure(state="normal", text="Combine")
                self.say.configure(text=app._err_text(exc))

        self.ok.configure(state="disabled", text="Combining…")
        app.run_quiet(lambda: Vault.open_cloud_copy(self.cloud_data, typed), opened, failed)


# ==========================================================================
# Self-test: open every screen on a real machine, then close (used by GitHub)
# ==========================================================================

def _selftest_import(app, tmp, require):
    """Import a small Google-style file through the real review screen."""
    path = os.path.join(tmp, "Google Passwords.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write("name,url,username,password,note\n"
                "discord.com,https://discord.com/login,john,disc-pw,\n"
                "netflix.com,https://www.netflix.com,john@x.com,nflx-pw,\n")
    dlg = [w for w in app.winfo_children() if isinstance(w, ImportDialog)][0]
    before = app.vault.entry_count
    dlg.show_review(path, importer.read_csv_file(path, app.vault.existing_keys()))
    require(len(dlg.vars) == 2, "review lists both logins")
    dlg.accept_btn.invoke()
    require(app.vault.entry_count == before + 2, "accept imports them")
    require(not os.path.exists(path), "export file deleted after accept")


def selftest() -> int:
    failures = []
    log_path = os.environ.get("HUSHKEY_SELFTEST_LOG")
    tmp = tempfile.mkdtemp(prefix="hushkey-selftest-")
    app = HushKeyApp(data_dir=tmp, cloud=Cloud("", ""), updater=updater_mod.Updater(repo=""))
    app.leak_checker = lambda hashes: set()   # no internet needed for the self-test

    def report(exc, val, tb):
        failures.append("".join(traceback.format_exception(exc, val, tb)))
    app.report_callback_exception = report

    def require(cond, what):
        if not cond:
            raise AssertionError(what)

    def dialog():
        return [w for w in app.winfo_children() if isinstance(w, EntryDialog)][0]

    secret = new_recovery_secret()
    v = Vault("test@example.com", tmp)
    v.create("selftest password", secret)
    steps = [
        lambda: require(draw_logo(64).size == (64, 64), "logo draws"),
        lambda: require(brand_icons.count() > 3000, "logo list bundled"),
        lambda: require(brand_icons.render("riotgames", 32) is not None, "Riot logo draws"),
        lambda: app.show_create(),
        lambda: app.show_forgot_email("test@example.com"),
        lambda: app.show_code("test@example.com", "Enter your sign-in code", "Test.",
                              on_verified=lambda s: (lambda: None), on_done=lambda _: None,
                              on_cancel=app.show_signin, remember=True),
        lambda: app.show_forgot_new(Vault("test@example.com", tmp).start_recovery(secret), "test@example.com"),
        lambda: app._enter(v, "test@example.com"),
        lambda: app.toggle_theme(),
        lambda: require(not app.is_dark, "switched to light mode"),
        lambda: app.toggle_theme(),
        lambda: require(app.is_dark, "switched back to dark mode"),
        lambda: require(load_settings(tmp).get("theme") == "dark", "theme choice saved"),
        lambda: v.add("Riot main", "summoner99", "hunter2!", "riotgames") and app.refresh_rows(),
        lambda: v.add("My bank", "me", "pw12345!") and app.refresh_rows(),
        lambda: app.select(app.vault.list_titles()[0][0]),
        lambda: require(app.glass._panel_box[4], "clicking a login opens the details panel"),
        lambda: [w[1].invoke() for w in app._secret_widgets.values()],
        lambda: app.copy(app.vault.list_titles()[0][0], 1),
        lambda: app.close_panel(),
        lambda: require(not app.glass._panel_box[4], "the arrow hides the panel"),
        lambda: app.open_panel(),
        lambda: app.toggle_fav(app.vault.list_titles()[0][0]),
        lambda: app.set_view("favorites"),
        lambda: require(len(app.rows) == 1, "favorites view"),
        lambda: app.vault.add_folder("Gaming", "#8C9EFF") and app.set_view("all"),
        lambda: app.move_to_folder(app.vault.list_titles()[0][0], app.vault.folders()[0]["id"]),
        lambda: app.remove_from_folder(app.vault.list_titles()[0][0]),
        lambda: app.open_folder_form(),
        lambda: app.close_folder_form(),
        lambda: app.show_settings("general"),
        lambda: require(app._settings_tab == "general", "the Settings button opens Settings"),
        lambda: app.show_main(),
        lambda: app.set_density("Compact"),
        lambda: app.toggle_usernames(),
        lambda: [app.show_settings(k) for k, _ in app.SETTINGS_TABS],
        lambda: app.set_accent("coral"),
        lambda: app.set_accent("green"),
        lambda: app.show_security(),
        lambda: app.open_change_master(),
        lambda: require([w for w in app.winfo_children() if isinstance(w, ChangeMasterWarning)],
                        "master password warning opens"),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: require(all(background_source(k) is not None for k, _ in BACKGROUNDS[1:]),
                        "all backgrounds bundled"),
        lambda: app.settings.update(background="soccer_stadium", box_opacity=40, bg_dim="high"),
        lambda: app.show_main(),
        lambda: require(app.glass is not None and len(app.rows) >= 1, "logins show over a background"),
        lambda: app.select(app.vault.list_titles()[0][0]),
        lambda: app._secret_widgets["pass"][1].invoke(),
        lambda: require(app._secret_widgets["pass"][1].cget("text") == "Hide", "Show works on the picture screen"),
        lambda: app.hide_revealed(),
        lambda: app.open_folder_form(),
        lambda: app.close_folder_form(),
        lambda: app.close_panel(),
        lambda: app.open_panel(),
        lambda: app.set_density("Compact"),
        lambda: app.set_density("Comfortable"),
        lambda: app.settings.update(style="pixel", font="pixel", bg_signin=True),
        lambda: (globals().update(STYLE="pixel"), set_font("pixel"), app.show_settings("appearance")),
        lambda: app.show_main(),
        lambda: require(any(c["this"] for c in app.vault.computers()), "this computer is listed"),
        lambda: app.show_settings("sync"),
        lambda: app.show_settings("appearance"),
        lambda: require(appearance_preview(app.settings, app.is_dark).size == (1120, 520), "appearance preview draws"),
        lambda: require(appearance_preview(dict(app.settings, density="compact", box_opacity=30,
                                                background="ocean_dusk"), app.is_dark).size == (1120, 520),
                        "preview draws compact and see-through"),
        lambda: require(box_opacity({}) == 100 and box_opacity({"box_opacity": 35}) == 35,
                        "boxes are solid unless the opacity is lowered"),
        lambda: app.show_settings("general"),
        lambda: setattr(app, "_hk_body", app._settings_shell["tabs"]["appearance"]["body"]),
        lambda: app.show_settings("appearance"),
        lambda: require(app._settings_body is app._hk_body, "going back to a Settings tab reuses it"),
        lambda: app.check_for_update(),
        lambda: require(getattr(app, "_update_job", None) is not None, "keeps checking for updates while open"),
        lambda: (globals().update(STYLE="basic"), set_font("poppins"), app.settings.update(style="basic",
                                                                                           font="poppins")),
        lambda: app.toggle_theme(),
        lambda: app.toggle_theme(),
        lambda: app.settings.update(background="none", box_opacity=40),
        lambda: app.show_main(),
        lambda: require(app.glass is not None and not app.glass.see and app.glass.picture() is None,
                        "without a background the vault uses the fast canvas screen, with solid boxes"),
        lambda: app.open_add(),
        lambda: dialog().generate(),
        lambda: dialog().logo.toggle(),
        lambda: require(dialog().logo.open and len(dialog().logo.results.winfo_children()) > 60
                        and "Couldn't" not in str(dialog().logo.note.cget("text")),
                        "logo dropdown opens with the top apps + everyday icons"),
        lambda: require(dialog()._escape() == "break" and not dialog().logo.open, "Escape closes the list"),
        lambda: (dialog().logo.search.insert(0, "riot"), dialog().logo.show_results()),
        lambda: require(dialog().logo.open, "typing opens the list"),
        lambda: dialog().logo.choose("riotgames"),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: app.open_edit(app.vault.list_titles()[0][0], fresh=True),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: app.open_import(),
        lambda: require([w for w in app.winfo_children() if isinstance(w, ImportDialog)], "import opens"),
        lambda: _selftest_import(app, tmp, require),
        lambda: app.open_export(),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: ChangeMasterDialog(app),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: setattr(app, "update_release", updater_mod.Release("9.9.9", "• Test notes", "u", "s")),
        lambda: app.show_update_dialog(),
        lambda: require(app._update_dialog() is not None, "update popup opens"),
        lambda: app._update_dialog().destroy(),
        lambda: CombineDialog(app, {}),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: app._save_window(),
        lambda: require(load_settings(tmp).get("window"), "window position saved"),
        lambda: app.lock_app("Locked after 5 minutes of no activity."),
        lambda: require(app.vault is None, "auto-lock closes the vault"),
        lambda: app.sign_out(),
        lambda: app.quit_app(),
    ]

    def run(i=0):
        try:
            steps[i]()
        except Exception:
            failures.append(f"step {i}:\n" + traceback.format_exc())
        if i < len(steps) - 1:
            app.after(300, lambda: run(i + 1))

    app.after(500, run)
    app.after(60_000, app.destroy)  # safety net
    app.mainloop()
    result = "SELFTEST " + ("FAILED" if failures else "PASSED") + f" ({len(steps)} steps)"
    text = "\n".join(failures + [result])
    print(text, file=sys.stderr if failures else sys.stdout)
    if log_path:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    HushKeyApp().mainloop()
