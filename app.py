"""
app.py - HushKey's windows and screens (CustomTkinter, works on Windows and Mac).

All security logic lives in vault.py (encryption, hashing, files) and
cloud.py (email codes). This file only draws screens and calls them.

Run from source:   python app.py
Screen check:      python app.py --selftest   (opens every screen, then closes)
"""

import os
import queue
import sys
import tempfile
import threading
import time
import traceback
from tkinter import messagebox

import customtkinter as ctk

import brand_icons
from brand import draw_logo
from cloud import Cloud, CloudError
from vault import (MIN_MASTER_LENGTH, REMEMBER_DAYS, Vault, VaultError,
                   WrongPassword, check_new_master, generate_password,
                   looks_like_email, new_recovery_secret, new_vault_id,
                   normalize_email, password_strength)
from version import __version__

APP_NAME = "HushKey"
AUTO_LOCK_SECONDS = 5 * 60      # sign out after 5 minutes with no activity
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
DOTS = "•" * 10

# ---- fonts: Poppins (bundled, free OFL license) ----
FAMILY = None


def resource(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
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


def load_fonts(root):
    """Pick the app font once the window exists: Poppins if it loaded,
    otherwise a good built-in font (Avenir Next on Mac, Segoe UI on Windows)."""
    global FAMILY
    try:
        import tkinter.font as tkfont
    except ImportError:
        return
    for name in ("Poppins-Regular.ttf", "Poppins-Bold.ttf"):
        try:
            _register_font_file(_font_file(name))
        except Exception:
            traceback.print_exc()
    try:
        families = set(tkfont.families(root))
    except Exception:
        families = set()
    for candidate in ("Poppins", "Avenir Next" if IS_MAC else "Segoe UI", "Helvetica"):
        if candidate in families:
            FAMILY = candidate
            break


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
    ctk.CTkLabel(row, text="Hush", font=font(size, "bold"), text_color=ACCENT, padx=0).pack(side="left")
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


def brand_image(slug, size):
    """An app logo for both themes (dark logos turn light in dark mode and
    light logos turn dark in light mode, so they never disappear)."""
    if not slug:
        return None
    dark = brand_icons.render(slug, size * 2)
    if dark is None:
        return None
    light = brand_icons.render(slug, size * 2, light=True)
    return ctk.CTkImage(light_image=light, dark_image=dark, size=(size, size))


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


def link_button(parent, text, command, size=13, color=ACCENT):
    return ctk.CTkButton(parent, text=text, command=command, fg_color="transparent",
                         hover=False, text_color=color, width=0, height=24,
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


def checkbox(parent, text, checked=True):
    var = ctk.BooleanVar(value=checked)
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
        self.bar = ctk.CTkProgressBar(self, height=6, corner_radius=3, fg_color=BORDER, progress_color=ACCENT)
        self.bar.pack(side="left", fill="x", expand=True)
        self.label = ctk.CTkLabel(self, text="", width=110, anchor="e", font=font(12), text_color=MUTED)
        self.label.pack(side="left", padx=(10, 0))
        self.update_for("")

    def update_for(self, pw: str):
        score, label = password_strength(pw)
        self.bar.set(score / 4)
        self.bar.configure(progress_color=DANGER if score <= 1 else ACCENT)
        self.label.configure(text=label)


class LogoPicker(ctk.CTkFrame):
    """'Choose a logo for this login'. Type to search, or click the arrow to
    browse the Top 50 apps & games and HushKey's everyday icons.

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

class HushKeyApp(ctk.CTk):
    def __init__(self, data_dir: str | None = None, cloud: Cloud | None = None):
        self.data_dir = data_dir
        self.settings = load_settings(data_dir)
        ctk.set_appearance_mode("light" if self.settings.get("theme") == "light" else "dark")
        super().__init__(fg_color=BG)
        load_fonts(self)
        self.title(APP_NAME)
        self.geometry("1000x700")
        self.minsize(880, 640)
        set_window_icon(self)

        self.cloud = cloud or Cloud()
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
        self.remember_var = None

        self.body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.body.pack(fill="both", expand=True)

        for ev in ("<Any-KeyPress>", "<Any-ButtonPress>", "<Motion>"):
            self.bind_all(ev, self._touch, add="+")
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
        self.show_signin(notice, ok=True)

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

    def _clear(self):
        self.screen += 1
        self.rows = {}
        self.revealed_id = None
        for w in self.body.winfo_children():
            w.destroy()

    def _card(self, width=440):
        card = ctk.CTkFrame(self.body, width=width, fg_color=SURFACE, corner_radius=18,
                            border_width=1, border_color=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center")
        self.theme_switch(self.body).place(relx=1.0, x=-24, y=20, anchor="ne")
        inner = ctk.CTkFrame(card, fg_color="transparent", width=width - 64)
        inner.pack(padx=32, pady=30, fill="both")
        return inner

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
        if self.vault and self.vault.is_unlocked and time.time() - self.last_activity > AUTO_LOCK_SECONDS:
            self.sign_out("Signed out after 5 minutes of no activity.")
        if self.revealed_id and self.revealed_id in self.rows:
            left = int(self.reveal_deadline - time.time())
            if left <= 0:
                self.hide_revealed()
            else:
                self.rows[self.revealed_id]["hint"].configure(text=f"Click to hide · hides in {left}s")
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
            if not v.exists():
                return say("There's no HushKey vault for this email on this computer. "
                           "Check the spelling, or create a vault.")

            def ok_cb(_):
                self.failed = 0
                self.last_email = addr
                self._after_password(v, addr, say, unlock_btn)

            def err_cb(exc):
                if isinstance(exc, WrongPassword):
                    self.failed += 1
                    delay = min(60, 2 ** self.failed) if self.failed >= 3 else 0
                    self.wait_until = time.time() + delay
                    pw.set("")
                    say("Wrong email or master password." + (f" Wait {delay}s before trying again." if delay else ""))
                else:
                    say(self._err_text(exc))

            self.run_bg(lambda: v.unlock(pw.get()), ok_cb, err_cb, unlock_btn, "Unlocking…")

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
        (pw.focus() if self.last_email else email.focus_set())

    def _after_password(self, v: Vault, addr: str, say, button):
        """Right password. On a computer that isn't remembered, also ask for
        a code sent to the user's email (two-step sign-in)."""
        if not self.cloud.configured or v.is_device_remembered():
            return self._enter(v, addr)

        def cancel():
            v.lock()
            self.show_signin()

        def done(_):
            if self.remember_var is not None and self.remember_var.get():
                v.remember_device()
            self._enter(v, addr)

        def failed(exc):
            v.lock()
            say(self._err_text(exc))

        self.run_bg(lambda: self.cloud.send_code(addr),
                    lambda _: self.show_code(
                        addr, "Enter your sign-in code",
                        "This computer isn't remembered yet, so we emailed you a 6-digit code.",
                        # a correct code also switches on email recovery for older vaults
                        on_verified=lambda s: (lambda: self._ensure_recovery(v, s)),
                        on_done=done, on_cancel=cancel, remember=True),
                    failed, button, "Sending code…")

    def _ensure_recovery(self, v: Vault, session):
        """Give a vault made before email was set up its recovery key.
        Runs in the background, right after the user proved their email."""
        if self.cloud.configured and v.is_unlocked and not v.has_recovery:
            secret = new_recovery_secret()
            self.cloud.store_secret(session, v.vault_id, secret)  # online first...
            v.enable_recovery(secret)                             # ...then the vault

    def turn_on_recovery(self):
        v, addr = self.vault, self.vault.email

        def done(_):
            self.show_main()
            self.status.configure(text="Email recovery is on. You can now reset your master "
                                       "password with a code sent to your email.", text_color=ACCENT)

        self.run_bg(lambda: self.cloud.send_code(addr),
                    lambda _: self.show_code(
                        addr, "Turn on email recovery",
                        "We emailed you a 6-digit code to confirm it's your email.",
                        on_verified=lambda s: (lambda: self._ensure_recovery(v, s)),
                        on_done=done, on_cancel=self.show_main, done_text="Turning on…"),
                    lambda exc: self.status.configure(text=self._err_text(exc), text_color=DANGER),
                    self.recovery_btn, "Sending code…")

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
                self.run_bg(lambda: v.create(master), lambda _: self._enter(v, addr),
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
                    v.remember_device()
                self._enter(v, addr)

            self.run_bg(lambda: self.cloud.send_code(addr),
                        lambda _: self.show_code(
                            addr, "Confirm your email",
                            "We sent a welcome email with your 6-digit sign-up code.",
                            on_verified=after_code, on_done=done,
                            on_cancel=self.show_create, done_text="Creating your vault…",
                            remember=True),
                        lambda exc: say(self._err_text(exc)), go, "Sending code…")

        go = self._button_row(c, self.show_signin, "Continue" if recovery_on else "Create vault", submit)
        email.bind("<Return>", submit)
        confirm.bind_enter(submit)
        email.focus_set()

    def _enter(self, v: Vault, addr: str):
        self.vault = v
        self.last_email = addr
        self.show_main()

    # ============================================================ CODE SCREEN

    def show_code(self, addr, title, intro, on_verified, on_done, on_cancel,
                  done_text="Checking…", step="", remember=False):
        """Shared 'enter the 6-digit code' screen.

        The code is checked by the email service: it must be the exact code
        sent to this email, it works once, and it expires after 10 minutes.
        on_verified(session) returns a function to run in the background after
        a correct code (e.g. download the recovery secret); on_done gets its result.
        """
        self._clear()
        c = self._card()
        self._heading(c, title, f"{intro} It was sent to {addr}. "
                                "Check your spam folder if you don't see it.", step)

        field_label(c, "6-digit code from the email").pack(fill="x", pady=(18, 0))
        code = ctk.CTkEntry(c, placeholder_text="123456", width=FIELD_WIDTH, height=60, corner_radius=10,
                            fg_color=BG, border_color=BORDER, text_color=TEXT,
                            placeholder_text_color=SUBTLE, justify="center", font=font(28, "bold", mono=True))
        code.pack(fill="x", pady=(6, 6))

        self.remember_var = None
        if remember:
            box, self.remember_var = checkbox(c, f"Remember this device for {REMEMBER_DAYS} days")
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
                            addr, "Check your email", "We sent you a 6-digit code.",
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

    def show_main(self):
        self._clear()
        self._touch()
        wrap = ctk.CTkFrame(self.body, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=28, pady=22)

        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text="", image=logo_image(46)).pack(side="left", padx=(0, 12))
        titles = ctk.CTkFrame(top, fg_color="transparent")
        titles.pack(side="left")
        wordmark(titles, 22).pack(anchor="w")
        self.subtitle = ctk.CTkLabel(titles, text="", font=font(12), text_color=MUTED, anchor="w")
        self.subtitle.pack(fill="x")
        ctk.CTkButton(top, text="Sign out", command=lambda: self.sign_out(), width=110, height=40,
                      corner_radius=10, fg_color=SIGNOUT, hover_color=SIGNOUT_HOVER,
                      text_color=("#FFFFFF", "#FFFFFF"), font=font(14, "bold")).pack(side="right")
        ghost_button(top, "Change master password", self.open_change_master,
                     height=40).pack(side="right", padx=(0, 10))
        self.theme_switch(top).pack(side="right", padx=(0, 12))

        self.recovery_btn = None
        if self.cloud.configured and not self.vault.has_recovery:
            banner = ctk.CTkFrame(wrap, fg_color=GOLD_SOFT, corner_radius=12, border_width=1, border_color=GOLD)
            banner.pack(fill="x", pady=(16, 0))
            ctk.CTkLabel(banner, text="Email recovery is off for this vault. Turn it on so you can reset "
                                      "your master password by email if you ever forget it.",
                         font=font(13), text_color=TEXT, anchor="w", justify="left",
                         wraplength=640).pack(side="left", padx=16, pady=12, fill="x", expand=True)
            self.recovery_btn = ctk.CTkButton(banner, text="Turn on", command=self.turn_on_recovery,
                                              width=110, height=38, corner_radius=10, fg_color=GOLD,
                                              hover_color=GOLD_HOVER, text_color=GOLD_INK,
                                              font=font(14, "bold"))
            self.recovery_btn.pack(side="right", padx=12)

        bar = ctk.CTkFrame(wrap, fg_color="transparent")
        bar.pack(fill="x", pady=(18, 12))
        self.search = ctk.CTkEntry(bar, placeholder_text="Search your logins", height=44, corner_radius=10,
                                   fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                                   placeholder_text_color=SUBTLE, font=font(14))
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda _e: self.refresh_rows())
        primary_button(bar, "+  Add login", self.open_add, width=140, height=44).pack(side="left", padx=(12, 0))

        self.listbox = ctk.CTkScrollableFrame(wrap, fg_color="transparent", corner_radius=0)
        self.listbox.pack(fill="both", expand=True)

        foot = ctk.CTkFrame(wrap, fg_color="transparent")
        foot.pack(fill="x", pady=(10, 0))
        self.status = ctk.CTkLabel(foot, text="Everything stays hidden until you click a login.",
                                   font=font(12), text_color=SUBTLE, anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        if self.cloud.configured and self.vault.is_device_remembered():
            self.forget_link = link_button(foot, "Forget this device", self.forget_device, size=12, color=MUTED)
            self.forget_link.pack(side="right")
        ctk.CTkLabel(foot, text=f"v{__version__}", font=font(11), text_color=SUBTLE).pack(side="right", padx=10)
        self.refresh_rows()

    def forget_device(self):
        self.vault.forget_device()
        if getattr(self, "forget_link", None) is not None and self.forget_link.winfo_exists():
            self.forget_link.destroy()
        self.status.configure(text="This computer will ask for an email code at the next sign-in.",
                              text_color=ACCENT)

    def refresh_rows(self, highlight=None):
        if not (self.vault and self.vault.is_unlocked):
            return
        self.hide_revealed()
        for w in self.listbox.winfo_children():
            w.destroy()
        self.rows = {}
        n = self.vault.entry_count
        self.subtitle.configure(text=f"My vault · {self.vault.email} · {n} login{'s' if n != 1 else ''}")
        query = self.search.get().strip().lower()
        items = [e for e in self.vault.list_entries() if query in e["title"].lower()]
        if not items:
            msg = ("No logins yet. Click “+ Add login” to save your first one." if n == 0
                   else "No logins match your search.")
            ctk.CTkLabel(self.listbox, text=msg, font=font(14), text_color=MUTED).pack(pady=40)
            return
        for e in items:
            self._make_row(e["id"], e["title"], e["icon"])
        if highlight in self.rows:
            self.reveal(highlight)

    def _make_row(self, entry_id, title, icon=""):
        row = ctk.CTkFrame(self.listbox, fg_color=SURFACE, corner_radius=12, border_width=1,
                           border_color=BORDER)
        row.pack(fill="x", pady=5, padx=(0, 6))
        row.grid_columnconfigure(1, weight=3)
        row.grid_columnconfigure(2, weight=2)
        row.grid_columnconfigure(3, weight=2)

        img = brand_image(icon, 26)
        avatar = ctk.CTkLabel(row, text="" if img else (title[:1] or "?").upper(), image=img,
                              width=46, height=46, corner_radius=10, fg_color=RAISED,
                              text_color=ACCENT, font=font(17, "bold"))
        avatar.grid(row=0, column=0, rowspan=2, padx=(14, 12), pady=12)

        name = ctk.CTkLabel(row, text=title, font=font(15, "bold"), text_color=TEXT, anchor="w")
        name.grid(row=0, column=1, sticky="sw")
        hint = ctk.CTkLabel(row, text="Click to reveal", font=font(12), text_color=MUTED, anchor="w")
        hint.grid(row=1, column=1, sticky="nw")

        cols = []
        for col, label in ((2, "USERNAME"), (3, "PASSWORD")):
            ctk.CTkLabel(row, text=label, font=font(11, "bold"), text_color=SUBTLE,
                         anchor="w").grid(row=0, column=col, sticky="sw", padx=(8, 0))
            val = ctk.CTkLabel(row, text=DOTS, font=font(14, mono=True), text_color=TEXT, anchor="w")
            val.grid(row=1, column=col, sticky="nw", padx=(8, 0))
            cols.append(val)

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=4, rowspan=2, padx=(8, 12))
        for text, cmd in (("Copy user", lambda: self.copy(entry_id, 0)),
                          ("Copy pass", lambda: self.copy(entry_id, 1)),
                          ("Edit", lambda: self.open_edit(entry_id))):
            ctk.CTkButton(btns, text=text, command=cmd, width=78, height=34, corner_radius=8,
                          fg_color=RAISED, hover_color=BORDER, text_color=LABEL,
                          font=font(12)).pack(side="left", padx=3)

        for w in (row, avatar, name, hint, *cols):
            w.bind("<Button-1>", lambda _e, i=entry_id: self.toggle_reveal(i))
        self.rows[entry_id] = {"frame": row, "hint": hint, "user": cols[0], "pass": cols[1]}

    def toggle_reveal(self, entry_id):
        if self.revealed_id == entry_id:
            self.hide_revealed()
        else:
            self.reveal(entry_id)

    def reveal(self, entry_id):
        self.hide_revealed()
        try:
            username, password = self.vault.reveal(entry_id)  # decrypted only now
        except VaultError as exc:
            self.status.configure(text=str(exc), text_color=DANGER)
            return
        r = self.rows[entry_id]
        r["user"].configure(text=username or "(none)")
        r["pass"].configure(text=password)
        r["frame"].configure(fg_color=ACCENT_SOFT, border_color=ACCENT)
        r["hint"].configure(text=f"Click to hide · hides in {REVEAL_SECONDS}s", text_color=ACCENT)
        self.revealed_id = entry_id
        self.reveal_deadline = time.time() + REVEAL_SECONDS

    def hide_revealed(self):
        r = self.rows.get(self.revealed_id)
        if r and r["frame"].winfo_exists():
            r["user"].configure(text=DOTS)
            r["pass"].configure(text=DOTS)
            r["frame"].configure(fg_color=SURFACE, border_color=BORDER)
            r["hint"].configure(text="Click to reveal", text_color=MUTED)
        self.revealed_id = None

    # ------------------------------------------------------------- clipboard

    def copy(self, entry_id, which):
        value = self.vault.reveal(entry_id)[which]
        if not value:
            self.status.configure(text="That login has no username saved.", text_color=MUTED)
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        token = object()
        self.clip = (token, value)
        what = "Username" if which == 0 else "Password"
        self.status.configure(text=f"{what} copied. It will be cleared from your clipboard in "
                                   f"{CLIPBOARD_CLEAR_SECONDS} seconds.", text_color=ACCENT)
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
        if getattr(self, "status", None) is not None and self.status.winfo_exists():
            self.status.configure(text="Clipboard cleared.", text_color=SUBTLE)

    # ---------------------------------------------------------- add / edit

    def open_add(self):
        EntryDialog(self, "Add a login", None, on_save=self._save_new)

    def _save_new(self, title, username, password, icon):
        new_id = self.vault.add(title, username, password, icon)
        self.refresh_rows()
        self.status.configure(text=f"Saved “{title}”.", text_color=ACCENT)
        return new_id

    def open_edit(self, entry_id):
        try:
            current = self.vault.get(entry_id)
        except VaultError as exc:
            self.status.configure(text=str(exc), text_color=DANGER)
            return

        def save(title, username, password, icon):
            self.vault.update(entry_id, title, username, password, icon)
            self.refresh_rows()
            self.status.configure(text=f"Updated “{title}”.", text_color=ACCENT)

        def delete():
            self.vault.delete(entry_id)
            self.refresh_rows()
            self.status.configure(text=f"Deleted “{current['title']}”.", text_color=MUTED)

        EntryDialog(self, "Edit login", current, on_save=save, on_delete=delete)

    def open_change_master(self):
        ChangeMasterDialog(self)

    # ------------------------------------------------------------ sign out

    def sign_out(self, notice=""):
        self.wipe_clipboard()
        if self.vault:
            self.vault.lock()
        self.vault = None
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkToplevel):
                w.destroy()
        self.show_signin(notice or "You're signed out.", ok=True)

    def quit_app(self):
        self.wipe_clipboard()
        if self.vault:
            self.vault.lock()
        self.destroy()


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
    def __init__(self, app, title, current, on_save, on_delete=None):
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

        self.gen = ctk.CTkButton(c, text="Click this to generate a password for you", command=self.generate,
                                 height=50, corner_radius=12, fg_color=ACCENT_SOFT, hover_color=ACCENT_SOFT_HOVER,
                                 border_width=2, border_color=ACCENT, text_color=ACCENT_HOVER,
                                 font=font(14, "bold"))
        self.gen.pack(fill="x", pady=(14, 4))
        self.gen_hint = ctk.CTkLabel(c, text="We'll make a long, random password. Click as many times as you like.",
                                     font=font(12), text_color=MUTED, wraplength=440)
        self.gen_hint.pack(fill="x")

        self.say = ctk.CTkLabel(c, text="", font=font(13), text_color=DANGER, anchor="w")
        self.say.pack(fill="x", pady=(8, 0))

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        if on_delete:
            ctk.CTkButton(row, text="Delete", command=self.delete, width=90, height=44, corner_radius=10,
                          fg_color="transparent", hover_color=DANGER_SOFT, border_width=1,
                          border_color=DANGER_BORDER, text_color=DANGER, font=font(14)).pack(side="left")
        primary_button(row, "Save login", self.save, width=130, height=44).pack(side="right")
        ghost_button(row, "Cancel", self.destroy, width=100, height=44).pack(side="right", padx=(0, 10))

        if current:
            self.name.insert(0, current["title"])
            self.user.insert(0, current["username"])
            self.pw.set(current["password"])
            self.bar.update_for(current["password"])
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
        self.generated += 1
        new = generate_password()
        self.pw.set(new)
        self.pw.set_visible(True)
        self.bar.update_for(new)
        self.gen.configure(text="Don't like it? Click again for a different one")
        times = "once" if self.generated == 1 else f"{self.generated} times"
        self.gen_hint.configure(text=f"Generated {times}. Keep clicking until you find one you like.")

    def save(self):
        title, user, pw = self.name.get().strip(), self.user.get().strip(), self.pw.get()
        if not title:
            return self.say.configure(text="Type a client name first.")
        if not pw:
            return self.say.configure(text="Type a password, or click the generate button.")
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
            self.app.status.configure(text="Master password changed.", text_color=ACCENT)

        def fail(exc):
            if self.winfo_exists():
                self.say.configure(text=self.app._err_text(exc))

        self.app.run_bg(lambda: vault.change_master(cur, new, again), done, fail, self.ok, "Saving…")


# ==========================================================================
# Self-test: open every screen on a real machine, then close (used by GitHub)
# ==========================================================================

def selftest() -> int:
    failures = []
    log_path = os.environ.get("HUSHKEY_SELFTEST_LOG")
    tmp = tempfile.mkdtemp(prefix="hushkey-selftest-")
    app = HushKeyApp(data_dir=tmp, cloud=Cloud("", ""))

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
        lambda: app.reveal(app.vault.list_titles()[0][0]),
        lambda: app.copy(app.vault.list_titles()[0][0], 1),
        lambda: app.open_add(),
        lambda: dialog().generate(),
        lambda: dialog().logo.toggle(),
        lambda: require(dialog().logo.open and len(dialog().logo.results.winfo_children()) > 60
                        and "Couldn't" not in str(dialog().logo.note.cget("text")),
                        "logo dropdown opens with the Top 50 + everyday icons"),
        lambda: require(dialog()._escape() == "break" and not dialog().logo.open, "Escape closes the list"),
        lambda: (dialog().logo.search.insert(0, "riot"), dialog().logo.show_results()),
        lambda: require(dialog().logo.open, "typing opens the list"),
        lambda: dialog().logo.choose("riotgames"),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: app.open_edit(app.vault.list_titles()[0][0]),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: app.open_change_master(),
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
