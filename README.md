<p align="center"><img src="assets/icon-512.png" width="120" alt="HushKey logo"></p>

<h1 align="center">HushKey</h1>

<p align="center">A simple, private password manager for <b>Windows and Mac</b>.<br>Your logins are encrypted on your computer, and only you can open them.</p>

<p align="center">
  <a href="../../releases/latest/download/HushKey-Windows.exe"><img alt="Download HushKey v2.0.12 for Windows" src="https://img.shields.io/badge/Download_v2.0.12_for-Windows-0078D4?style=for-the-badge&logo=data:image/svg%2Bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPHBhdGggZmlsbD0iI0ZGRkZGRiIgZD0iTTAgMGgxMS4zNzd2MTEuMzcySDBabTEyLjYyMyAwSDI0djExLjM3MkgxMi42MjNaTTAgMTIuNjIzaDExLjM3N1YyNEgwWm0xMi42MjMgMEgyNFYyNEgxMi42MjNaIi8%2BPC9zdmc%2B&logoColor=white" height="44"></a>
  &nbsp;&nbsp;
  <a href="../../releases/latest/download/HushKey-Mac.zip"><img alt="Download HushKey v2.0.12 for Mac" src="https://img.shields.io/badge/Download_v2.0.12_for-Mac-B07D12?style=for-the-badge&logo=apple&logoColor=white" height="44"></a>
</p>

<p align="center"><b>Latest version: v2.0.12</b> · <a href="../../releases">All releases</a></p>

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
2. Click **+ Add Login** and type a name, username and password. Or click **Generate a strong password**, then **Copy** it and paste it into the Password box.
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
- **Make it yours:** light and dark mode, 21 accent colors, Basic or Pixel style, 4 fonts, a compact view, and 15 pixel-art backgrounds.
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

### v2.0.12

**New**
- **New logo:** a shorter, thinner key on the Peaceful face, so the key's details stay clear even when the icon is small. Used for the app icon and inside the app.
- **Backgrounds:** pick one of 15 pixel-art pictures in Settings › Appearance: Cherry Blossom, Princess Castle, Ocean Dusk, Fairy Forest, Aurora Peaks, Ramen Shop, Samurai Sunset, Knight's Keep, Neon City, Space Voyage, Dragon Mountain, Soccer Stadium, Sunny Beach, Race Track and Sky Ruins. Each choice shows a preview.
- **See-through vault:** the picture shows behind the whole vault screen: the sidebar, your logins and the details panel. Boxes keep an outline and text keeps a soft shadow, so everything stays readable. Prefer solid boxes? Turn off **See-through boxes**.
- **Dim the picture:** Low, Medium or High. It fades darker in dark mode and lighter in light mode.
- **Sign-in screen** stays plain by default, with a solid sign-in box. You can turn on the picture there too.
- **Styles:** Basic (rounded) or Pixel (square, retro corners with a pixel font).
- **Fonts:** Poppins, DM Sans, Nunito or Pixel.
- Smooth with lots of logins, and when you resize, maximize or minimize the window: the picture is prepared once per window size and stays still while you scroll.

**Fixed**
- The Vault Health score could jump to a very different number for a moment and then go back. It now stays steady from the moment HushKey opens.
- On/off switches could be hard to read (the knob blended into the switch). They now always show clearly whether they're on or off.
- Changing a login's password now clears its old data-leak warning right away.
- The light/dark switch was removed from the vault screen; it's in Settings › Appearance.

### v2.0.11

**New**
- **Safer password generator:** "Generate a strong password" now shows a new password in its own box with **Copy** and **New one**. It never replaces your current password; it's only saved after you paste it into the Password box. HushKey tells you when it's pasted.
- **Smaller generate button** so the form is less crowded.
- **75 more logos** in the list, now called "Top apps & games": McDonald's, Starbucks, Burger King, KFC, Taco Bell, Uber Eats, Instacart, Target, Etsy, Nike, HBO Max, Crunchyroll, Apple Music, Visa, Robinhood, Lyft, Delta, Marriott, Notion and more.
- **Food icons:** Restaurant, Pizza, Burger and Coffee. Typing a name like Domino's, Chipotle, Wendy's or Dunkin' picks the matching one, for places that don't share their logo.

**Fixed**
- The desktop and Start menu shortcuts kept showing the old logo after updating.

### v2.0.10

**New**
- **New look:** a sidebar with All Logins, Favorites, Folders and a Vault Health score.
- **Details panel** opens when you click a login, with Show and Copy for the username and password, a colored strength bar, and Edit or Delete. The arrow hides it, and a small tab brings it back.
- **New logo,** inside the app and as the app icon.
- **Favorites:** star any login, then find it under Favorites.
- **Folders:** create, rename and delete them with any color. Add, move or remove logins, with **Undo**.
- **Hidden usernames** in the list, with a **Show usernames** button.
- **Comfortable or Compact** list.
- **Security tips page** with a score, pointing out weak, reused or leaked passwords. Each tip has Fix, **Not now** (hides it for 30 days) and **Don't remind me**, and you can turn all tips off.
- **Private leak check** using Have I Been Pwned. Only 5 characters of a scrambled version of each password are sent, and you can turn it off.
- **Settings page:**
  - General: lock timer from 1 minute to 3 hours, or never; forget this device.
  - Appearance: theme, 21 accent colors, density.
  - Security, Sync & devices, Import & export, and About.
- **Profile menu** (top right) with Settings, Security tips, Import, Export, Sync, Help, and a red Sign out.
- **Quick unlock** after auto-lock: just type your master password.
- **"Are you sure?"** before changing your master password.
- **Welcome screen** only for brand-new vaults.
- **Tidier GitHub page:** code is now in folders.

**Fixed**
- The "Turn on sync" banner stayed after turning sync on.
- Automatic updates didn't work in v2.0.9 because of a build setting. They work from v2.0.10 on.

### v2.0.9

**New**
- **Sync across computers:** sign in anywhere with your email, master password and an 8-digit code. Changes sync both ways about every minute, and only encrypted data is uploaded.
- **Automatic updates:** a pop-up shows what's new, with **Update now** or **Later** (installs when you close HushKey).
- **Window position:** opens centered the first time, then where you left it.
- **Windows install guide** for Edge, SmartScreen and Smart App Control.

**Fixed**
- "Remembered until…" showed twice at the bottom of the app.

### v2.0.8

**New**
- **Remember this device for 30 days:** HushKey opens straight to your vault. Closing it keeps you remembered, **Sign out** turns it off, and it switches off by itself after 30 days.

### v2.0.7

**New**
- **Mac first-launch steps** at the top of this page.
- **Big vaults stay fast:** logins load 50 at a time, and search waits until you stop typing.

**Fixed**
- Some screens and emails said 6-digit codes; they're all 8 digits now.

### v2.0.6

**New**
- **Import** from Google, Bitwarden, LastPass, 1Password, Apple Passwords, Edge, Firefox or Dashlane, with a review step before anything is saved.
- **The export file is securely deleted** after importing.
- **Export** an encrypted backup (.hushkey) or a CSV file, and restore a backup with Import.

### v2.0.5

**Fixed**
- HushKey could crash on start with "brand_icons.json.gz not found". The logo list and font are now built into the app.

### v2.0.4

**New**
- **Light and dark mode** with the key switch.
- **Poppins font.**
- **Red Sign out button.**
- **Pop-ups open centered.**
- **Version number** shown in the app.
- **Email recovery** turns on for older vaults when you sign in.

**Fixed**
- The logo picker showed an empty list. It now opens the top apps & games plus everyday icons, searches 3,400+ logos, and has "Use my own picture".
- Updating didn't always replace the running app or refresh the desktop icon.

## For developers

```bash
pip install -r requirements.txt
python app/app.py
```

- **Folders:** `app/` holds the code, `tests/` the tests (`python -m unittest discover -s tests`), and `packaging/` the build and installer scripts. `supabase/` sets up the database, and `docs/` has the [email recovery setup](docs/SETUP_EMAIL_RECOVERY.md).
- **Publishing:** upload your changes, then go to **Releases → Draft a new release**, use the next tag (like `v2.0.13`), and click **Publish**. GitHub tests and builds both apps, and everyone gets the update automatically.

## Credits

Fonts: [Poppins](https://fonts.google.com/specimen/Poppins), [DM Sans](https://fonts.google.com/specimen/DM+Sans), [Nunito](https://fonts.google.com/specimen/Nunito) and [Pixelify Sans](https://fonts.google.com/specimen/Pixelify+Sans) (Open Font License). App logos: [Simple Icons](https://simpleicons.org) (CC0). Brand logos belong to their owners. Leak check: [Have I Been Pwned](https://haveibeenpwned.com/Passwords).
