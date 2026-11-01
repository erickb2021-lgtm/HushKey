"""
app.py - HushKey's window (Tkinter, which ships with Python on Mac and Windows).

All the security logic is in vault.py. This file only draws screens and calls it.
Run from source with:   python app.py
"""

import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk

from vault import (MIN_MASTER_LENGTH, Vault, VaultError, WrongPassword,
                   generate_password)

APP_TITLE = "HushKey"
MASK = "••••••••••"
AUTO_LOCK_SECONDS = 5 * 60       # lock after 5 minutes with no mouse/keyboard activity
CLIPBOARD_CLEAR_SECONDS = 20     # wipe copied passwords from the clipboard after 20s
REVEAL_SECONDS = 30              # a clicked entry re-hides itself after 30s

IS_MAC = sys.platform == "darwin"
UI_FONT = ("Helvetica Neue", 13) if IS_MAC else ("Segoe UI", 10)
TITLE_FONT = ("Helvetica Neue", 22, "bold") if IS_MAC else ("Segoe UI", 18, "bold")
SMALL_FONT = ("Helvetica Neue", 11) if IS_MAC else ("Segoe UI", 9)


class HushKeyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x500")
        self.minsize(620, 420)

        self.vault = Vault()
        self.failed_attempts = 0
        self.locked_until = 0.0
        self.last_activity = time.time()
        self.revealed_id = None
        self.clipboard_token = None

        style = ttk.Style(self)
        if "clam" in style.theme_names() and not IS_MAC:
            style.theme_use("clam")
        style.configure("Treeview", rowheight=28, font=UI_FONT)
        style.configure("Treeview.Heading", font=(UI_FONT[0], UI_FONT[1], "bold"))
        style.configure("Title.TLabel", font=TITLE_FONT)
        style.configure("Hint.TLabel", font=SMALL_FONT, foreground="#666")
        style.configure("Error.TLabel", font=SMALL_FONT, foreground="#c0392b")

        self.container = ttk.Frame(self, padding=20)
        self.container.pack(fill="both", expand=True)

        for event in ("<Any-KeyPress>", "<Any-ButtonPress>", "<Motion>"):
            self.bind_all(event, self._touch, add="+")
        self.after(1000, self._auto_lock_check)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.show_login()

    # ------------------------------------------------------------------ utils

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()
        self.revealed_id = None

    def _touch(self, _event=None):
        self.last_activity = time.time()

    def _auto_lock_check(self):
        if self.vault.is_unlocked and time.time() - self.last_activity > AUTO_LOCK_SECONDS:
            self.lock(reason="Locked after 5 minutes of inactivity.")
        self.after(1000, self._auto_lock_check)

    def _on_close(self):
        self._wipe_clipboard_if_ours()
        self.vault.lock()
        self.destroy()

    # ------------------------------------------------------------ login screen

    def show_login(self, message: str = ""):
        self._clear()
        creating = not self.vault.exists()

        box = ttk.Frame(self.container)
        box.place(relx=0.5, rely=0.45, anchor="center")

        ttk.Label(box, text="🔒 HushKey", style="Title.TLabel").pack(pady=(0, 6))
        ttk.Label(
            box,
            text=("Create a master password. It can't be recovered if you forget it."
                  if creating else "Enter your master password to unlock."),
            style="Hint.TLabel",
        ).pack(pady=(0, 16))

        ttk.Label(box, text="Master password").pack(anchor="w")
        pw = ttk.Entry(box, show="•", width=34, font=UI_FONT)
        pw.pack(pady=(2, 10))
        pw.focus_set()

        confirm = None
        if creating:
            ttk.Label(box, text="Confirm master password").pack(anchor="w")
            confirm = ttk.Entry(box, show="•", width=34, font=UI_FONT)
            confirm.pack(pady=(2, 10))

        err = ttk.Label(box, text=message, style="Error.TLabel", wraplength=300)
        err.pack(pady=(0, 8))

        def submit(_e=None):
            master = pw.get()
            if creating:
                if len(master) < MIN_MASTER_LENGTH:
                    err.config(text=f"Use at least {MIN_MASTER_LENGTH} characters.")
                    return
                if master != confirm.get():
                    err.config(text="The two passwords don't match.")
                    return
                err.config(text="Creating vault…")
                self.update_idletasks()
                try:
                    self.vault.create(master)
                except VaultError as ex:
                    err.config(text=str(ex))
                    return
                self.show_main()
                return

            # Unlocking: slow down repeated wrong guesses (2s, 4s, 8s … max 60s).
            wait = self.locked_until - time.time()
            if wait > 0:
                err.config(text=f"Too many attempts. Try again in {int(wait) + 1}s.")
                return
            err.config(text="Unlocking…")
            self.update_idletasks()
            try:
                self.vault.unlock(master)
            except WrongPassword:
                self.failed_attempts += 1
                delay = min(60, 2 ** self.failed_attempts) if self.failed_attempts >= 3 else 0
                self.locked_until = time.time() + delay
                extra = f" Wait {delay}s before trying again." if delay else ""
                err.config(text="Wrong master password." + extra)
                pw.delete(0, "end")
                return
            except VaultError as ex:
                err.config(text=str(ex))
                return
            self.failed_attempts = 0
            self.show_main()

        ttk.Button(box, text="Create Vault" if creating else "Unlock",
                   command=submit).pack(fill="x")
        pw.bind("<Return>", submit)
        if confirm is not None:
            confirm.bind("<Return>", submit)

    # ------------------------------------------------------------- main screen

    def show_main(self):
        self._clear()
        self._touch()

        top = ttk.Frame(self.container)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="🔒 HushKey", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Lock", command=self.lock).pack(side="right")
        ttk.Button(top, text="Change Master…", command=self.change_master_dialog
                   ).pack(side="right", padx=6)
        ttk.Button(top, text="+ Add", command=self.add_dialog).pack(side="right")

        search_row = ttk.Frame(self.container)
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_list())
        ttk.Entry(search_row, textvariable=self.search_var, font=UI_FONT
                  ).pack(side="left", fill="x", expand=True, padx=(6, 0))

        table_frame = ttk.Frame(self.container)
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_frame, columns=("title", "username", "password"),
                                 show="headings", selectmode="browse")
        self.tree.heading("title", text="Client")
        self.tree.heading("username", text="Username")
        self.tree.heading("password", text="Password")
        self.tree.column("title", width=240)
        self.tree.column("username", width=220)
        self.tree.column("password", width=200)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _e: self.edit_dialog())
        self.tree.bind("<Escape>", lambda _e: self._hide_revealed(deselect=True))

        actions = ttk.Frame(self.container)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Copy Username",
                   command=lambda: self._copy(0)).pack(side="left")
        ttk.Button(actions, text="Copy Password",
                   command=lambda: self._copy(1)).pack(side="left", padx=6)
        ttk.Button(actions, text="Hide",
                   command=lambda: self._hide_revealed(deselect=True)).pack(side="left")
        ttk.Button(actions, text="Delete", command=self.delete_selected).pack(side="right")
        ttk.Button(actions, text="Edit", command=self.edit_dialog).pack(side="right", padx=6)

        self.status = ttk.Label(self.container, style="Hint.TLabel",
                                text="Click an entry to reveal it. Double-click to edit.")
        self.status.pack(fill="x", pady=(8, 0))

        self.refresh_list()

    def refresh_list(self, select_id: str | None = None):
        self.revealed_id = None
        self.tree.delete(*self.tree.get_children())
        query = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        for entry_id, title in self.vault.list_titles():
            if query and query not in title.lower():
                continue
            self.tree.insert("", "end", iid=entry_id, values=(title, MASK, MASK))
        if select_id and self.tree.exists(select_id):
            self.tree.selection_set(select_id)
            self.tree.see(select_id)

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        entry_id = sel[0]
        if entry_id == self.revealed_id:
            return
        self._hide_revealed()
        username, password = self.vault.reveal(entry_id)  # decrypted only now
        title = self.tree.item(entry_id, "values")[0]
        self.tree.item(entry_id, values=(title, username, password))
        self.revealed_id = entry_id
        # Don't leave a password sitting on screen if you walk away.
        self.after(REVEAL_SECONDS * 1000, lambda: self._auto_hide(entry_id))

    def _auto_hide(self, entry_id):
        if self.revealed_id == entry_id and self.vault.is_unlocked:
            self._hide_revealed(deselect=True)
            self.status.config(text="Entry hidden again after "
                                    f"{REVEAL_SECONDS}s. Click it to reveal.")

    def _hide_revealed(self, deselect: bool = False):
        if self.revealed_id and self.tree.exists(self.revealed_id):
            title = self.tree.item(self.revealed_id, "values")[0]
            self.tree.item(self.revealed_id, values=(title, MASK, MASK))
        self.revealed_id = None
        if deselect:
            self.tree.selection_remove(*self.tree.selection())

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Select an entry first.", parent=self)
            return None
        return sel[0]

    # ---------------------------------------------------------------- clipboard

    def _copy(self, which: int):
        entry_id = self._selected_id()
        if not entry_id:
            return
        value = self.vault.reveal(entry_id)[which]
        self.clipboard_clear()
        self.clipboard_append(value)
        token = object()
        self.clipboard_token = (token, value)
        label = "Username" if which == 0 else "Password"
        self.status.config(text=f"{label} copied. Clipboard clears in {CLIPBOARD_CLEAR_SECONDS}s.")
        self.after(CLIPBOARD_CLEAR_SECONDS * 1000, lambda: self._wipe_clipboard_if_ours(token))

    def _wipe_clipboard_if_ours(self, token=None):
        """Clear the clipboard only if it still holds what we put there."""
        if not self.clipboard_token:
            return
        our_token, our_value = self.clipboard_token
        if token is not None and token is not our_token:
            return
        try:
            if self.clipboard_get() == our_value:
                self.clipboard_clear()
                self.clipboard_append("")
        except tk.TclError:
            pass
        self.clipboard_token = None
        if self.vault.is_unlocked and hasattr(self, "status") and self.status.winfo_exists():
            self.status.config(text="Clipboard cleared.")

    # ------------------------------------------------------------- add / edit

    def add_dialog(self):
        data = EntryDialog(self, "Add Entry").result
        if data:
            try:
                new_id = self.vault.add(*data)
            except VaultError as ex:
                messagebox.showerror(APP_TITLE, str(ex), parent=self)
                return
            self.refresh_list(select_id=new_id)
            self.status.config(text=f"Saved “{data[0]}”.")

    def edit_dialog(self):
        entry_id = self._selected_id()
        if not entry_id:
            return
        current = self.vault.get(entry_id)
        data = EntryDialog(self, "Edit Entry", current).result
        if data:
            try:
                self.vault.update(entry_id, *data)
            except VaultError as ex:
                messagebox.showerror(APP_TITLE, str(ex), parent=self)
                return
            self.refresh_list(select_id=entry_id)
            self.status.config(text=f"Updated “{data[0]}”.")

    def delete_selected(self):
        entry_id = self._selected_id()
        if not entry_id:
            return
        title = self.tree.item(entry_id, "values")[0]
        if messagebox.askyesno(APP_TITLE, f"Delete “{title}”? This can't be undone.",
                               parent=self, icon="warning"):
            self.vault.delete(entry_id)
            self.refresh_list()
            self.status.config(text=f"Deleted “{title}”.")

    def change_master_dialog(self):
        ChangeMasterDialog(self)

    # ------------------------------------------------------------------ lock

    def lock(self, reason: str = ""):
        self._wipe_clipboard_if_ours()
        self.vault.lock()
        self.show_login(message=reason)


class EntryDialog(tk.Toplevel):
    """Pop-up form: Client / Username / Password."""

    def __init__(self, parent, title, initial: dict | None = None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.result = None

        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Client (e.g. Riot account 1)").grid(row=0, column=0, columnspan=3, sticky="w")
        self.title_e = ttk.Entry(frame, width=40, font=UI_FONT)
        self.title_e.grid(row=1, column=0, columnspan=3, sticky="we", pady=(2, 10))

        ttk.Label(frame, text="Username").grid(row=2, column=0, columnspan=3, sticky="w")
        self.user_e = ttk.Entry(frame, width=40, font=UI_FONT)
        self.user_e.grid(row=3, column=0, columnspan=3, sticky="we", pady=(2, 10))

        ttk.Label(frame, text="Password").grid(row=4, column=0, columnspan=3, sticky="w")
        self.pw_e = ttk.Entry(frame, width=28, show="•", font=UI_FONT)
        self.pw_e.grid(row=5, column=0, sticky="we", pady=(2, 10))
        self.show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Show", variable=self.show_var,
                        command=self._toggle).grid(row=5, column=1, padx=6)
        ttk.Button(frame, text="Generate", command=self._generate).grid(row=5, column=2)

        self.err = ttk.Label(frame, text="", style="Error.TLabel")
        self.err.grid(row=6, column=0, columnspan=3, sticky="w")

        btns = ttk.Frame(frame)
        btns.grid(row=7, column=0, columnspan=3, sticky="e", pady=(8, 0))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Save", command=self._save).pack(side="right", padx=6)

        if initial:
            self.title_e.insert(0, initial["title"])
            self.user_e.insert(0, initial["username"])
            self.pw_e.insert(0, initial["password"])

        self.bind("<Return>", lambda _e: self._save())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.title_e.focus_set()
        self.grab_set()
        self.wait_window()

    def _toggle(self):
        self.pw_e.config(show="" if self.show_var.get() else "•")

    def _generate(self):
        self.pw_e.delete(0, "end")
        self.pw_e.insert(0, generate_password())
        self.show_var.set(True)
        self._toggle()

    def _save(self):
        title = self.title_e.get().strip()
        if not title:
            self.err.config(text="Client name is required.")
            return
        if not self.pw_e.get():
            self.err.config(text="Password is required.")
            return
        self.result = (title, self.user_e.get().strip(), self.pw_e.get())
        self.destroy()


class ChangeMasterDialog(tk.Toplevel):
    def __init__(self, parent: HushKeyApp):
        super().__init__(parent)
        self.app = parent
        self.title("Change Master Password")
        self.transient(parent)
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)
        self.fields = []
        for i, label in enumerate(("Current master password", "New master password",
                                   "Confirm new master password")):
            ttk.Label(frame, text=label).grid(row=i * 2, column=0, sticky="w")
            e = ttk.Entry(frame, show="•", width=34, font=UI_FONT)
            e.grid(row=i * 2 + 1, column=0, pady=(2, 10))
            self.fields.append(e)
        self.err = ttk.Label(frame, text="", style="Error.TLabel", wraplength=280)
        self.err.grid(row=6, column=0, sticky="w")
        btns = ttk.Frame(frame)
        btns.grid(row=7, column=0, sticky="e", pady=(8, 0))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Change", command=self._submit).pack(side="right", padx=6)

        self.bind("<Return>", lambda _e: self._submit())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.fields[0].focus_set()
        self.grab_set()
        self.wait_window()

    def _submit(self):
        old, new, confirm = (f.get() for f in self.fields)
        if new != confirm:
            self.err.config(text="New passwords don't match.")
            return
        self.err.config(text="Re-encrypting…")
        self.update_idletasks()
        try:
            self.app.vault.change_master(old, new)
        except VaultError as ex:
            self.err.config(text=str(ex))
            return
        messagebox.showinfo(APP_TITLE, "Master password changed.", parent=self.app)
        self.destroy()


if __name__ == "__main__":
    HushKeyApp().mainloop()
