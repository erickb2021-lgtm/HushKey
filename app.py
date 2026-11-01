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

from cloud import Cloud, CloudError
from vault import (MIN_MASTER_LENGTH, TamperError, Vault, VaultError,
                   WrongPassword, check_new_master, generate_password,
                   looks_like_email, new_recovery_secret, new_vault_id,
                   normalize_email, password_strength)

APP_NAME = "HushKey"
AUTO_LOCK_SECONDS = 5 * 60      # sign out after 5 minutes with no activity
CLIPBOARD_CLEAR_SECONDS = 20    # wipe copied passwords after 20s
REVEAL_SECONDS = 30             # a clicked login hides itself again after 30s

IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"
MONO = "Menlo" if IS_MAC else ("Consolas" if IS_WIN else "DejaVu Sans Mono")

# ---- colors (the green "safe" theme) ----
BG = "#0E1116"
SURFACE = "#161A22"
RAISED = "#1D222C"
BORDER = "#2A303C"
TEXT = "#EEF1F6"
MUTED = "#A2AAB8"
SUBTLE = "#8C95A5"
ACCENT = "#3DDC97"
ACCENT_HOVER = "#5BE6AA"
ACCENT_INK = "#08281A"
ACCENT_SOFT = "#14231D"
DANGER = "#FF8080"
DANGER_SOFT = "#2A1618"
DOTS = "•" * 10


def resource(rel: str) -> str:
    """Path to a bundled file, both from source and inside the packaged app."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def font(size=14, weight="normal", mono=False):
    return ctk.CTkFont(family=MONO, size=size, weight=weight) if mono else ctk.CTkFont(size=size, weight=weight)


# ==========================================================================
# Reusable pieces
# ==========================================================================

def primary_button(parent, text, command, **kw):
    kw.setdefault("height", 46)
    return ctk.CTkButton(parent, text=text, command=command, corner_radius=10,
                         fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_INK,
                         text_color_disabled="#2F5E48", font=font(15, "bold"), **kw)


def ghost_button(parent, text, command, **kw):
    kw.setdefault("height", 46)
    return ctk.CTkButton(parent, text=text, command=command, corner_radius=10,
                         fg_color="transparent", hover_color=RAISED, border_width=1,
                         border_color=BORDER, text_color=TEXT, font=font(14), **kw)


def link_button(parent, text, command, size=13):
    return ctk.CTkButton(parent, text=text, command=command, fg_color="transparent",
                         hover=False, text_color=ACCENT, width=0, height=24,
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
    return ctk.CTkLabel(parent, text=text, font=font(13, "bold"), text_color="#C9CFDA", anchor="w")


class PasswordField(ctk.CTkFrame):
    """A password box with an optional Show/Hide button."""

    def __init__(self, parent, placeholder="", visible=False, toggle=True):
        super().__init__(parent, fg_color="transparent")
        self.visible = visible
        self.entry = entry(self, placeholder, show=None if visible else "•", mono=visible,
                           width=FIELD_WIDTH - 72 if toggle else FIELD_WIDTH)
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


def logo_image(size):
    try:
        from PIL import Image
        return ctk.CTkImage(Image.open(resource("assets/logo.png")), size=(size, size))
    except Exception:
        return None


# ==========================================================================
# The app
# ==========================================================================

class HushKeyApp(ctk.CTk):
    def __init__(self, data_dir: str | None = None, cloud: Cloud | None = None):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=BG)
        self.title(APP_NAME)
        self.geometry("980x660")
        self.minsize(860, 600)
        try:
            if IS_WIN:
                self.iconbitmap(resource("assets/HushKey.ico"))
        except Exception:
            pass

        self.data_dir = data_dir
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

        self.body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.body.pack(fill="both", expand=True)

        for ev in ("<Any-KeyPress>", "<Any-ButtonPress>", "<Motion>"):
            self.bind_all(ev, self._touch, add="+")
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.after(60, self._poll_jobs)
        self.after(1000, self._tick)
        self.show_signin()

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
        inner = ctk.CTkFrame(card, fg_color="transparent", width=width - 64)
        inner.pack(padx=32, pady=30, fill="both")
        return inner

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
        img = logo_image(64)
        if img:
            ctk.CTkLabel(c, text="", image=img).pack(pady=(0, 10))
        ctk.CTkLabel(c, text="Welcome back", font=font(26, "bold"), text_color=TEXT).pack()
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
                self.vault = v
                self.show_main()

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
        (pw.focus() if self.last_email else email.focus_set())

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

            self.run_bg(lambda: self.cloud.send_code(addr),
                        lambda _: self.show_code(
                            addr, "Confirm your email", "",
                            on_verified=after_code,
                            on_done=lambda _: self._enter(v, addr),
                            on_cancel=self.show_create, done_text="Creating your vault…"),
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

    def show_code(self, addr, title, step, on_verified, on_done, on_cancel, done_text="Checking…"):
        """Shared 'enter the 6-digit code' screen.

        on_verified(session) returns a function to run in the background after a
        correct code (e.g. download the recovery secret); on_done gets its result.
        """
        self._clear()
        c = self._card()
        self._heading(c, title, f"We sent a code to {addr}. Enter it below. "
                                "Check your spam folder if you don't see it.", step)

        field_label(c, "Code from the email").pack(fill="x", pady=(18, 0))
        code = ctk.CTkEntry(c, placeholder_text="123456", width=FIELD_WIDTH, height=60, corner_radius=10,
                            fg_color=BG, border_color=BORDER, text_color=TEXT,
                            placeholder_text_color=SUBTLE, justify="center", font=font(28, "bold", mono=True))
        code.pack(fill="x", pady=(6, 6))

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

            self.run_bg(work, on_done, lambda exc: say(self._err_text(exc)), verify, done_text)

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
                return say("Email recovery wasn't turned on when this vault was made, so it can't be reset.")
            if not self.cloud.configured:
                return say("Email recovery isn't set up in this copy of HushKey.")

            def got_secret(session):
                return lambda: v.start_recovery(self.cloud.fetch_secret(session, v.vault_id))

            self.run_bg(lambda: self.cloud.send_code(addr),
                        lambda _: self.show_code(
                            addr, "Check your email", "Step 2 of 3",
                            on_verified=got_secret,
                            on_done=lambda reset: self.show_forgot_new(reset, addr),
                            on_cancel=lambda: self.show_signin()),
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
        img = logo_image(40)
        if img:
            ctk.CTkLabel(top, text="", image=img).pack(side="left", padx=(0, 12))
        titles = ctk.CTkFrame(top, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="My vault", font=font(20, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
        self.subtitle = ctk.CTkLabel(titles, text="", font=font(12), text_color=MUTED, anchor="w")
        self.subtitle.pack(fill="x")
        ghost_button(top, "Sign out", lambda: self.sign_out(), width=100, height=40).pack(side="right")
        ghost_button(top, "Change master password", self.open_change_master,
                     height=40).pack(side="right", padx=(0, 10))

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

        self.status = ctk.CTkLabel(wrap, text="Everything stays hidden until you click a login.",
                                   font=font(12), text_color=SUBTLE, anchor="w")
        self.status.pack(fill="x", pady=(10, 0))
        self.refresh_rows()

    def refresh_rows(self, highlight=None):
        if not (self.vault and self.vault.is_unlocked):
            return
        self.hide_revealed()
        for w in self.listbox.winfo_children():
            w.destroy()
        self.rows = {}
        n = self.vault.entry_count
        self.subtitle.configure(text=f"{self.vault.email} · {n} login{'s' if n != 1 else ''}")
        query = self.search.get().strip().lower()
        items = [(i, t) for i, t in self.vault.list_titles() if query in t.lower()]
        if not items:
            msg = ("No logins yet. Click “+ Add login” to save your first one." if n == 0
                   else "No logins match your search.")
            ctk.CTkLabel(self.listbox, text=msg, font=font(14), text_color=MUTED).pack(pady=40)
            return
        for entry_id, title in items:
            self._make_row(entry_id, title)
        if highlight in self.rows:
            self.reveal(highlight)

    def _make_row(self, entry_id, title):
        row = ctk.CTkFrame(self.listbox, fg_color=SURFACE, corner_radius=12, border_width=1,
                           border_color=BORDER)
        row.pack(fill="x", pady=5, padx=(0, 6))
        row.grid_columnconfigure(1, weight=3)
        row.grid_columnconfigure(2, weight=2)
        row.grid_columnconfigure(3, weight=2)

        avatar = ctk.CTkLabel(row, text=(title[:1] or "?").upper(), width=42, height=42, corner_radius=10,
                              fg_color=RAISED, text_color=ACCENT, font=font(17, "bold"))
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
                          fg_color=RAISED, hover_color=BORDER, text_color="#C9CFDA",
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

    def _save_new(self, title, username, password):
        new_id = self.vault.add(title, username, password)
        self.refresh_rows()
        self.status.configure(text=f"Saved “{title}”.", text_color=ACCENT)
        return new_id

    def open_edit(self, entry_id):
        try:
            current = self.vault.get(entry_id)
        except VaultError as exc:
            self.status.configure(text=str(exc), text_color=DANGER)
            return

        def save(title, username, password):
            self.vault.update(entry_id, title, username, password)
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
    def __init__(self, app: HushKeyApp, title, width=480):
        super().__init__(app, fg_color=SURFACE)
        self.app = app
        self.title(title)
        self.resizable(False, False)
        self.transient(app)
        self.inner = ctk.CTkFrame(self, fg_color="transparent", width=width - 56)
        self.inner.pack(padx=28, pady=24, fill="both", expand=True)
        self.bind("<Escape>", lambda _e: self.destroy())
        # Windows sometimes opens pop-ups behind the main window; bring it forward.
        self.after(120, self._front)

    def _front(self):
        if self.winfo_exists():
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

        field_label(c, "Client name").pack(fill="x", pady=(16, 0))
        self.name = entry(c, "e.g. Riot account 1")
        self.name.pack(fill="x", pady=(6, 12))

        field_label(c, "Username").pack(fill="x")
        self.user = entry(c, "Your username or email for that site")
        self.user.pack(fill="x", pady=(6, 12))

        field_label(c, "Password").pack(fill="x")
        self.pw = PasswordField(c, "Type a password, or generate below")
        self.pw.pack(fill="x", pady=(6, 6))
        self.bar = StrengthBar(c)
        self.bar.pack(fill="x")
        self.pw.bind_key(lambda _e: self.bar.update_for(self.pw.get()))

        self.gen = ctk.CTkButton(c, text="Click this to generate a password for you", command=self.generate,
                                 height=50, corner_radius=12, fg_color=ACCENT_SOFT, hover_color="#1A3328",
                                 border_width=2, border_color=ACCENT, text_color=ACCENT_HOVER,
                                 font=font(14, "bold"))
        self.gen.pack(fill="x", pady=(16, 4))
        self.gen_hint = ctk.CTkLabel(c, text="We'll make a long, random password. Click as many times as you like.",
                                     font=font(12), text_color=MUTED, wraplength=420)
        self.gen_hint.pack(fill="x")

        self.say = ctk.CTkLabel(c, text="", font=font(13), text_color=DANGER, anchor="w")
        self.say.pack(fill="x", pady=(8, 0))

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        if on_delete:
            ctk.CTkButton(row, text="Delete", command=self.delete, width=90, height=44, corner_radius=10,
                          fg_color="transparent", hover_color=DANGER_SOFT, border_width=1,
                          border_color="#5A2A2E", text_color=DANGER, font=font(14)).pack(side="left")
        primary_button(row, "Save login", self.save, width=130, height=44).pack(side="right")
        ghost_button(row, "Cancel", self.destroy, width=100, height=44).pack(side="right", padx=(0, 10))

        if current:
            self.name.insert(0, current["title"])
            self.user.insert(0, current["username"])
            self.pw.set(current["password"])
            self.bar.update_for(current["password"])
        self.bind("<Return>", lambda _e: self.save())
        self.after(150, self.name.focus_set)

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
            return self.say.configure(text="Give it a client name, like “Riot account 1”.")
        if not pw:
            return self.say.configure(text="Type a password, or click the generate button.")
        try:
            self.on_save(title, user, pw)
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
    from vault import new_recovery_secret as nrs
    failures = []
    tmp = tempfile.mkdtemp(prefix="hushkey-selftest-")
    app = HushKeyApp(data_dir=tmp, cloud=Cloud("", ""))

    def report(exc, val, tb):
        failures.append("".join(traceback.format_exception(exc, val, tb)))
    app.report_callback_exception = report

    secret = nrs()
    v = Vault("test@example.com", tmp)
    v.create("selftest password", secret)
    steps = [
        lambda: app.show_create(),
        lambda: app.show_forgot_email("test@example.com"),
        lambda: app.show_code("test@example.com", "Check your email", "Step 2 of 3",
                              on_verified=lambda s: (lambda: None), on_done=lambda _: None,
                              on_cancel=app.show_signin),
        lambda: app.show_forgot_new(Vault("test@example.com", tmp).start_recovery(secret), "test@example.com"),
        lambda: app._enter(v, "test@example.com"),
        lambda: v.add("Riot account 1", "summoner99", "hunter2!") and app.refresh_rows(),
        lambda: app.reveal(app.vault.list_titles()[0][0]),
        lambda: app.copy(app.vault.list_titles()[0][0], 1),
        lambda: app.open_add(),
        lambda: [w for w in app.winfo_children() if isinstance(w, EntryDialog)][0].generate(),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: app.open_edit(app.vault.list_titles()[0][0]),
        lambda: [w.destroy() for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)],
        lambda: app.open_change_master(),
        lambda: app.sign_out(),
        lambda: app.quit_app(),
    ]

    def run(i=0):
        if i < len(steps):
            try:
                steps[i]()
            except Exception:
                failures.append(f"step {i}:\n" + traceback.format_exc())
            if i < len(steps) - 1:
                app.after(300, lambda: run(i + 1))

    app.after(500, run)
    app.after(30_000, app.destroy)  # safety net
    app.mainloop()
    for f in failures:
        print(f, file=sys.stderr)
    print("SELFTEST", "FAILED" if failures else "PASSED", f"({len(steps)} steps)")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    HushKeyApp().mainloop()
