<p align="center"><img src="assets/icon-512.png" width="120" alt="HushKey logo"></p>

<h1 align="center">HushKey</h1>

<p align="center">A simple, secure password manager for <b>Windows and Mac</b>.<br>Your logins stay encrypted on your computer, and you can recover your vault by email.</p>

<p align="center">
  <a href="../../releases/latest/download/HushKey-Windows.exe"><img alt="Download for Windows" src="https://img.shields.io/badge/Download_for-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" height="44"></a>
  &nbsp;&nbsp;
  <a href="../../releases/latest/download/HushKey-Mac.zip"><img alt="Download for Mac" src="https://img.shields.io/badge/Download_for-Mac-000000?style=for-the-badge&logo=apple&logoColor=white" height="44"></a>
</p>

<p align="center"><sub>Always the newest version · <a href="../../releases">All releases</a></sub></p>

## Download

| Your computer | Download | How to open |
|---|---|---|
| **Windows** | `HushKey-Windows.exe` | Double-click to install (no admin needed). It opens HushKey when done and adds it to the Start Menu. If a blue "Windows protected your PC" box appears, click **More info → Run anyway** (see [why](#is-it-safe)). |
| **Mac** (Apple Silicon, M1 or newer) | `HushKey-Mac.zip` | Unzip, drag **HushKey** into Applications. The first time, **right-click → Open → Open** (the app isn't signed with a paid Apple developer account, so macOS asks once). |

## How to use it

1. **Create a vault:** enter your email and a master password. Type the password once where you can see it, then again **hidden, from memory**. We email you a code to confirm the email is yours.
2. **Sign in** with your email and master password.
3. Click **+ Add login** and fill in:
   - **Client name:** `Riot account 1`
   - **Username:** `xxxxxx`
   - **Password:** type one, or click **"Click this to generate a password for you"**. Click it as many times as you like until you get one you like.
4. Usernames and passwords are **always hidden** (`••••••••••`). **Click a login** to reveal it. Click again to hide it, or it hides itself after 30 seconds.
5. **Copy user / Copy pass** copies to your clipboard, and HushKey wipes it after 20 seconds.
6. **Sign out** when you're done. HushKey also signs you out after 5 minutes of no activity.

### Forgot your master password?

On the sign-in screen, click **Forgot master password?**

1. Enter your email → **Send code**.
2. Enter the 6-digit code from the email → **Verify code**.
3. Create a new master password (visible), then retype it **hidden, from memory** → **Reset password**.

You can **Cancel** at any step. **Nothing changes until you click Reset password**, so if you suddenly remember your old password, it still works. All your saved logins are kept.

## How the security works

**Hashing is one-way.** You can turn `hunter2` into a hash, but never turn the hash back into `hunter2`. That's perfect for checking your master password without ever storing it.

**Your saved logins can't just be hashed**, because you need to *see them again*. So they're **encrypted** (a two-way lock that needs a key).

HushKey uses a trick called **key wrapping**:

```
                       ┌────────────────────────────────────────┐
                       │      VAULT KEY (random, 32 bytes)      │
                       │  encrypts every Client, Username and   │
                       │  Password + seals the file vs tampering│
                       └───────────▲────────────────▲───────────┘
                                   │                │
                    locked copy #1 │                │ locked copy #2
                                   │                │
  master password ─► PBKDF2-SHA256 ┘                └─ recovery secret (online, Supabase)
  (600,000 rounds + random salt;                       only downloadable after a correct
   part of the hash checks your login)                 6-digit code sent to YOUR email
```

- **To open a vault you need either** your master password, **or** this computer's vault file **plus** access to your email. The online service never sees the vault file, and the vault file alone is useless.
- **Salt:** random bytes mixed into the hash, so two people with the same password get completely different hashes.
- **600,000 rounds:** each guess takes ~0.3s on purpose. Fine for you once, painful for someone trying millions.
- **Constant-time compare:** checking a password takes the same time however close a guess is, so timing leaks nothing.
- **Anti-tamper seal:** the whole vault file carries an HMAC fingerprint. If anyone edits, deletes or swaps entries or weakens the settings, HushKey refuses to open it and shows a security warning.
- **Login throttling:** after 3 wrong master passwords, HushKey makes you wait (2s, 4s, 8s… up to 60s).
- **Even the Client names are encrypted** on disk, and vault file names are hashed so nobody can see whose vault is whose.

## File handling

Each email gets its own vault file:

- **Mac:** `~/Library/Application Support/HushKey/`
- **Windows:** `%APPDATA%\HushKey\`

Saving uses an **atomic write**: write to a temp file, flush it to disk, then swap it in with `os.replace()`. A crash mid-save leaves the old vault, never a broken one. The previous version is also kept as a `.bak` file next to it.

## Project files

| File | What it does |
|---|---|
| `vault.py` | Hashing, encryption, key wrapping, reading/writing vault files. |
| `cloud.py` | Talks to Supabase for email codes and recovery secrets. |
| `cloud_config.py` | Your Supabase project's address and public key. |
| `app.py` | The windows and screens (CustomTkinter). |
| `test_vault.py`, `test_cloud.py` | Tests: `python -m unittest -v` |
| `supabase/setup.sql` | Database table + security rules for Supabase. |
| `SETUP_EMAIL_RECOVERY.md` | Step-by-step guide to turn on email recovery. |
| `assets/` | Logo and app icons. `packaging/make_icons.py` redraws them. |
| `packaging/` | Windows installer script and .exe version details. |
| `.github/workflows/build.yml` | GitHub builds, tests and publishes both apps. |

## Run from source

```bash
pip install -r requirements.txt
python app.py
```

On Mac, use `python3`. Install Python from python.org so the window library (Tkinter) is included.

## Publishing a new version

1. Upload your changed files to GitHub, **keeping them in the same folders**.
2. On your repo page, click **Releases → Draft a new release**.
3. Click **Choose a tag**, type the next version (e.g. `v2.0.0`), and click **Create new tag**.
4. Click **Publish release**.
5. Open the **Actions** tab and wait for the green check (~5–10 minutes). GitHub runs all the tests, opens every screen on a real Windows PC and a real Mac to make sure nothing crashes, then attaches the downloads. The buttons at the top of this page then serve the new version.

## Is it safe?

- **Every download has a fingerprint.** Each release includes `.sha256.txt` files. To check your download wasn't changed:
  - Windows (PowerShell): `Get-FileHash HushKey-Windows.exe`
  - Mac (Terminal): `shasum -a 256 HushKey-Mac.zip`
- **Built in the open.** GitHub builds every download straight from the code in this repo. You can watch each build in the Actions tab.
- **Why Windows may still warn:** SmartScreen trusts apps signed with a paid code-signing certificate and apps many people have already downloaded. New, unsigned apps get "Windows protected your PC" no matter how safe they are. The Windows build avoids common false virus alarms (standard installer, its own PyInstaller bootloader, no self-unpacking single .exe, proper version details). If Defender ever flags it, report the false positive at [microsoft.com/wdsi/filesubmission](https://www.microsoft.com/en-us/wdsi/filesubmission). Free code signing for open-source projects: [SignPath Foundation](https://signpath.org).

## Limits (honest ones)

- This is a learning project, not audited security software.
- Python can't fully wipe secrets from memory after signing out.
- Someone who has your vault file **and** can read your email could reset your master password. Protect your email account with 2-step verification.
- Someone who copies your vault file can try guessing your master password on their own computer, where the wait timer doesn't apply. A **long master password** (4+ random words) is your real protection.
- Nothing can protect you if your computer already has malware such as a keylogger.
- The Mac build is for Apple Silicon (M1 and newer). Intel Macs can run it from source.
- **Upgrading from 1.0:** version 2 uses email accounts and a new vault format, so vaults made in 1.0 aren't opened. Create a new vault and re-add your logins.
