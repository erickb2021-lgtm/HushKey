# 🔒 HushKey

A simple, secure password manager for **Windows and Mac**, built to learn file handling and hashing.

<p align="center">
  <a href="../../releases/latest/download/HushKey-Windows.exe"><img alt="Download for Windows" src="https://img.shields.io/badge/Download_for-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" height="44"></a>
  &nbsp;&nbsp;
  <a href="../../releases/latest/download/HushKey-Mac.zip"><img alt="Download for Mac" src="https://img.shields.io/badge/Download_for-Mac-000000?style=for-the-badge&logo=apple&logoColor=white" height="44"></a>
</p>

<p align="center"><sub>Always the newest version · <a href="../../releases">All releases</a></sub></p>

## Download

Click a button above, or go to **[Releases](../../releases/latest)** and grab the one for your computer:

| Your computer | Download | How to open |
|---|---|---|
| **Windows** | `HushKey-Windows.exe` | Double-click to install (no admin needed). It opens HushKey when done and adds it to the Start Menu. If a blue "Windows protected your PC" box appears, click **More info → Run anyway** (see [why](#is-it-safe)). |
| **Mac** (Apple Silicon, M1 or newer) | `HushKey-Mac.zip` | Unzip, drag **HushKey.app** into Applications. The first time, **right-click → Open → Open** (the app isn't signed with a paid Apple developer account, so macOS asks once). |

## How it works

1. **First launch:** you create a master password (8+ characters). It can't be recovered, so don't forget it.
2. **Every launch after:** enter the master password to unlock.
3. Click **+ Add** and fill in:
   - **Client:** `Riot account 1`
   - **Username:** `xxxxxx`
   - **Password:** `xxxxx` (or click **Generate** for a strong random one)
4. The list shows each **Client** name, with usernames and passwords hidden as `••••••••••`. **Click an entry to reveal it**; clicking another hides the previous one, and it hides itself again after 30 seconds.
5. **Copy Password** puts it on your clipboard and wipes it after 20 seconds.
6. HushKey **locks itself after 5 minutes** of no activity.

## Hashing vs. encryption (the part you're learning)

**Hashing is one-way.** You can turn `hunter2` into a hash, but you can never turn the hash back into `hunter2`. That's perfect for the **master password**: HushKey never stores it. It stores a hash, and at login it hashes what you type and checks whether the two hashes match.

**But your saved passwords can't just be hashed**, because you need to *see them again* when you click. A hash can't be reversed, so a hashed Riot password would be gone forever. So saved logins are **encrypted** instead (a two-way lock that needs a key), and the key itself comes from hashing your master password.

```
master password ──► PBKDF2-SHA256 (600,000 rounds, random salt) ──► 96 bytes
                                                                       │
              ┌────────────────────────────┬───────────────────────────┴─┐
         bytes 0-31                   bytes 32-63                    bytes 64-95
              │                            │                              │
        SHA-256 again               encryption key                   seal key
              │                     (memory only)                   (memory only)
  saved as "verifier"                      │                              │
  (checks your login)          Fernet (AES + tamper check)     HMAC fingerprint of the
                               locks every Client,             WHOLE file, so deleted or
                               Username and Password           swapped entries are caught
```

Key ideas in the code (`vault.py`):

- **Salt:** 16 random bytes mixed into the hash, so two people with the same master password get completely different hashes, and precomputed "rainbow tables" are useless.
- **600,000 rounds:** hashing is repeated on purpose so each guess takes ~0.3s. Fine for you once, painful for someone trying millions of guesses.
- **Constant-time compare** (`hmac.compare_digest`): the check takes the same time no matter how close a guess is, so timing leaks nothing.
- **Split key:** the verifier, encryption key and seal key come from different parts of the hash, so the saved verifier tells an attacker nothing about the other two.
- **Anti-tamper seal:** the whole file carries an HMAC fingerprint. If anyone edits, deletes or swaps entries, or weakens the settings (e.g. lowers the 600,000 rounds), HushKey refuses to open it and shows a security warning instead of trusting it.
- **Login throttling:** after 3 wrong master passwords, the app makes you wait (2s, 4s, 8s… up to 60s).
- **Less on screen:** revealed entries re-hide after 30s, copied passwords leave the clipboard after 20s, and the vault auto-locks after 5 minutes.

**Even if someone opens the vault file directly**, they see only scrambled text. Not even the Client names are readable.

## File handling

Your vault is a single JSON file:

- **Mac:** `~/Library/Application Support/HushKey/vault.json`
- **Windows:** `%APPDATA%\HushKey\vault.json`

Saving uses an **atomic write**: write to a temp file, flush it to disk, then swap it in with `os.replace()`. If your computer crashes mid-save, you keep the old vault instead of a half-written broken one.

Before each save, HushKey keeps the previous version as `vault.json.bak` in the same folder. If the tamper check ever fails, that backup is your way back.

To **back up** your vault, copy that file. To **reset** HushKey (lose everything), delete it.

## Project files

| File | What it does |
|---|---|
| `vault.py` | Hashing, encryption, reading/writing the vault file. No UI. |
| `app.py` | The window (Tkinter, built into Python). |
| `test_vault.py` | Tests: `python -m unittest -v` |
| `build_mac.sh` / `build_windows.bat` | Build the app on your own computer. |
| `packaging/` | Windows installer script and .exe version details. |
| `.github/workflows/build.yml` | GitHub builds both apps for you automatically. |

## Run from source

```bash
pip install -r requirements.txt
python app.py
```

(On Mac, use `python3`. If you installed Python from python.org, Tkinter is included.)

## Publishing a new version

1. Push your code to GitHub (`git add .`, `git commit -m "..."`, `git push`).
2. On your repo page, click **Releases → Draft a new release**.
3. Click **Choose a tag**, type `v1.0.0` (bump it each time: `v1.0.1`, `v1.1.0`…), and click **Create new tag**.
4. Give it a title like `HushKey 1.0.0` and click **Publish release**.
5. Open the **Actions** tab and wait for the green check (about 5 minutes). The downloads then appear on the release, and the buttons at the top of this page start working.

## Is it safe?

- **Every download has a fingerprint.** Each release includes `.sha256.txt` files. To check your download wasn't changed:
  - Windows (PowerShell): `Get-FileHash HushKey-Windows.exe`
  - Mac (Terminal): `shasum -a 256 HushKey-Mac.zip`
  
  The result should match the `.sha256.txt` file.
- **Built in the open.** GitHub builds every download straight from the code in this repo. You can see each build in the Actions tab.
- **Why Windows may still warn:** SmartScreen trusts apps signed with a paid code-signing certificate and apps that many people have already downloaded. New, unsigned apps get "Windows protected your PC" no matter how safe they are. The Windows build is set up to avoid common false virus alarms (a standard installer, its own PyInstaller bootloader, no self-unpacking single .exe, and proper version details). If Defender still flags it, you can report the false positive at [microsoft.com/wdsi/filesubmission](https://www.microsoft.com/en-us/wdsi/filesubmission). The only way to remove the warning entirely is code signing. Free options for open-source projects include [SignPath Foundation](https://signpath.org).

## Limits (honest ones)

- This is a learning project, not audited security software.
- Python can't fully wipe secrets from memory after locking.
- Someone who copies your vault file can try guessing your master password on their own computer, where the app's wait timer doesn't apply. The 600,000 rounds slow that down, but a **long master password** (a phrase of 4+ random words) is your real protection.
- Nothing can protect you if your computer already has malware such as a keylogger.
- The Mac build is for Apple Silicon (M1 and newer). Intel Macs can run it from source.
