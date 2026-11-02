<p align="center"><img src="assets/icon-512.png" width="120" alt="HushKey logo"></p>

<h1 align="center">HushKey</h1>

<p align="center">A simple, private password manager for <b>Windows and Mac</b>.<br>Your logins are encrypted on your computer, and only you can open them.</p>

<p align="center">
  <a href="../../releases/latest/download/HushKey-Windows.exe"><img alt="Download HushKey v2.0.10 for Windows" src="https://img.shields.io/badge/Download_v2.0.10_for-Windows-0078D4?style=for-the-badge&logo=data:image/svg%2Bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPHBhdGggZmlsbD0iI0ZGRkZGRiIgZD0iTTAgMGgxMS4zNzd2MTEuMzcySDBabTEyLjYyMyAwSDI0djExLjM3MkgxMi42MjNaTTAgMTIuNjIzaDExLjM3N1YyNEgwWm0xMi42MjMgMEgyNFYyNEgxMi42MjNaIi8%2BPC9zdmc%2B&logoColor=white" height="44"></a>
  &nbsp;&nbsp;
  <a href="../../releases/latest/download/HushKey-Mac.zip"><img alt="Download HushKey v2.0.10 for Mac" src="https://img.shields.io/badge/Download_v2.0.10_for-Mac-B07D12?style=for-the-badge&logo=apple&logoColor=white" height="44"></a>
</p>

<p align="center"><b>Latest version: v2.0.10</b> · <a href="../../releases">All releases</a></p>

## Download

| Your computer | Download | How to open |
|---|---|---|
| <img src="assets/windows.svg" height="14" alt=""> **Windows** (10 and 11) | `HushKey-Windows.exe` | Double-click to install (no admin needed). First time? Follow [Windows](#windows-first-time-only) below. |
| <img src="assets/apple.svg" height="15" alt=""> **Mac** (Apple Silicon, M1 or newer) | `HushKey-Mac.zip` | Unzip, then drag **HushKey** into Applications. First time? Follow [Mac](#mac-first-time-only) below. |

After the first install, HushKey updates itself.

### <img src="assets/windows.svg" height="18" alt=""> Windows (first time only)

HushKey isn't signed with a paid certificate yet, so Windows warns you once. It doesn't mean there's a virus.

1. **Edge** says *"isn't commonly downloaded"*: click **⋯** → **Keep** → **Show more** → **Keep anyway**.
2. **"Windows protected your PC"**: click **More info** → **Run anyway**.
3. Follow the installer. HushKey opens when it's done.

On some Windows 11 PCs, **Smart App Control** blocks unsigned apps with no "Run anyway" button. You can switch it off in **Windows Security → App & browser control**, but that lowers protection for all apps, so only do it if you're comfortable with that.

### <img src="assets/apple.svg" height="20" alt=""> Mac (first time only)

1. Unzip `HushKey-Mac.zip` and drag **HushKey** into **Applications**.
2. Open it. When the warning appears, click **Done**.
3. Go to **System Settings → Privacy & Security**, scroll down, and click **Open Anyway**.

Older macOS: right-click HushKey → **Open** → **Open**.

## How to use it

1. **Create a vault** with your email and a master password. You'll get an 8-digit code by email to confirm it's you.
2. Click **+ Add login**. Type a name, username and password, or click the button to generate a strong password.
3. **Click a login** to see its details. Usernames and passwords stay hidden until you click **Show**. **Copy** clears itself from your clipboard after 20 seconds.
4. **Organize** with the star (Favorites) and **Folders** (click **+** in the sidebar).
5. Everything else, like Settings, Security tips, Import, Export and Sign out, is in the menu at the top right.

**On another computer:** install HushKey and sign in with the same email and master password. Your logins come with you.

**Forgot your master password?** Click **Forgot master password?** on the sign-in screen and follow the steps. Nothing changes until you click **Reset password**.

## Features

- **Sync** across your computers. Only encrypted data is uploaded.
- **Favorites and folders**, including streaming-friendly hidden usernames.
- **Security tips** that point out weak, reused or leaked passwords. They're optional, and you can turn them off.
- **Import** from Google, Chrome, Bitwarden, LastPass, 1Password, Apple Passwords, Edge, Firefox or Dashlane. **Export** to an encrypted backup or a CSV file.
- **Auto-lock** after the time you choose (1 minute to 3 hours, or never).
- **Remember this device** for 30 days so it opens straight to your vault.
- **Light and dark mode**, 21 accent colors, and a compact view.
- **Automatic updates.**

## Security

HushKey is built with users first. Your privacy matters more than any feature.

- **Only you can read your vault.** Logins are encrypted on your computer with a key made from your master password (PBKDF2-SHA256, 600,000 rounds). Your master password never leaves your computer.
- **Sync is zero-knowledge.** The server only ever stores encrypted data, and every download is tamper-checked.
- **The leak check is private.** It sends only the first 5 characters of a scrambled version of each password, so nobody learns your passwords. You can turn it off.
- **Tamper seal.** If anyone changes your vault file, HushKey refuses to open it and warns you.
- **Every download is built in public** by GitHub from this code, and comes with a SHA-256 fingerprint.

## Limits

- HushKey is a personal project, not audited security software.
- Someone with your vault file **and** your email could reset your master password, so protect your email with 2-step verification.
- A long master password is your best protection. Four or more random words works well.
- Nothing can protect you from malware already on your computer.
- The Mac app needs Apple Silicon (M1 or newer).

## What's new

### v2.0.10

- **New look:** a sidebar with All logins, Favorites, Folders and Vault health. The details panel opens when you click a login, and the arrow hides it again.
- **New logo.**
- **Favorites and folders:** star any login. Make folders, then add, move or remove logins with Undo.
- **Hidden usernames** in the list, with a Show usernames button.
- **Security tips** with a score. Suggestions are small and optional: **Not now** hides one for 30 days, **Don't remind me** hides it for good, and you can turn them all off.
- **Leak check** that tells you if a password showed up in a known data leak, privately.
- **Settings page:** lock timer (1 minute to 3 hours, or never), 21 accent colors, compact view, theme, sync and more.
- **Quick unlock** after auto-lock: just your master password.
- **Change master password** now asks "Are you sure?" first.
- **The welcome screen** only shows for brand-new vaults.
- **Fixed:** the "Turn on sync" banner stayed after you turned sync on.
- **Tidier GitHub page:** code is now in folders.

### v2.0.9

- Sync across computers.
- Automatic updates.
- The window opens where you left it.

### v2.0.8

- Remember this device for 30 days.

### v2.0.7

- 8-digit email codes everywhere.
- Big vaults stay fast.

### v2.0.6

- Import from Google and other password managers.
- Export to an encrypted backup or CSV.

### v2.0.5

- Fixed a crash on start.

### v2.0.4

- Light and dark mode, a new font, a red Sign out button, and centered pop-ups.

## For developers

```bash
pip install -r requirements.txt
python app/app.py
```

- **Folders:** `app/` holds the code, `tests/` the tests (`python -m unittest discover -s tests`), and `packaging/` the build and installer scripts. `supabase/` sets up the database, and `docs/` has the [email recovery setup](docs/SETUP_EMAIL_RECOVERY.md).
- **Publishing:** upload your changes, then go to **Releases → Draft a new release**, use the next tag (like `v2.0.11`), and click **Publish**. GitHub tests and builds both apps, and everyone gets the update automatically.

## Credits

Font: [Poppins](https://fonts.google.com/specimen/Poppins) (Open Font License). App logos: [Simple Icons](https://simpleicons.org) (CC0). Brand logos belong to their owners. Leak check: [Have I Been Pwned](https://haveibeenpwned.com/Passwords).
