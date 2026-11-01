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
| **Windows** | `HushKey-Windows.exe` | Double-click it. If Windows SmartScreen appears, click **More info → Run anyway**. |
| **Mac** (Apple Silicon, M1 or newer) | `HushKey-Mac.zip` | Unzip, drag **HushKey.app** into Applications. The first time, **right-click → Open → Open** (the app isn't signed with a paid Apple developer account, so macOS asks once). |

## How it works

1. **First launch:** you create a master password (8+ characters). It can't be recovered, so don't forget it.
2. **Every launch after:** enter the master password to unlock.
3. Click **+ Add** and fill in:
   - **Client:** `Riot account 1`
   - **Username:** `xxxxxx`
   - **Password:** `xxxxx` (or click **Generate** for a strong random one)
4. The list shows each **Client** name, with usernames and passwords hidden as `••••••••••`. **Click an entry to reveal it**; clicking another hides the previous one.
5. **Copy Password** puts it on your clipboard and wipes it after 20 seconds.
6. HushKey **locks itself after 5 minutes** of no activity.

## Hashing vs. encryption (the part you're learning)

**Hashing is one-way.** You can turn `hunter2` into a hash, but you can never turn the hash back into `hunter2`. That's perfect for the **master password**: HushKey never stores it. It stores a hash, and at login it hashes what you type and checks whether the two hashes match.

**But your saved passwords can't just be hashed**, because you need to *see them again* when you click. A hash can't be reversed, so a hashed Riot password would be gone forever. So saved logins are **encrypted** instead (a two-way lock that needs a key), and the key itself comes from hashing your master password.

```
master password ──► PBKDF2-SHA256 (600,000 rounds, random salt) ──► 64 bytes
                                                                     │
                         ┌───────────────────────────────────────────┴──────────┐
                     first 32 bytes                                       last 32 bytes
                         │                                                       │
                   SHA-256 again                                        encryption key
                         │                                         (only in memory while unlocked)
             saved as "verifier" in the file                                     │
             (used to check your login)                      Fernet (AES + tamper check) locks
                                                             every Client, Username and Password
```

Key ideas in the code (`vault.py`):

- **Salt:** 16 random bytes mixed into the hash, so two people with the same master password get completely different hashes, and precomputed "rainbow tables" are useless.
- **600,000 rounds:** hashing is repeated on purpose so each guess takes ~0.3s. Fine for you once, painful for someone trying millions of guesses.
- **Constant-time compare** (`hmac.compare_digest`): the check takes the same time no matter how close a guess is, so timing leaks nothing.
- **Split key:** the saved verifier and the encryption key come from different halves of the hash, so the verifier tells an attacker nothing about the key.
- **Tamper check:** if anyone edits the vault file, decryption refuses instead of returning garbage.
- **Login throttling:** after 3 wrong master passwords, the app makes you wait (2s, 4s, 8s… up to 60s).

**Even if someone opens the vault file directly**, they see only scrambled text. Not even the Client names are readable.

## File handling

Your vault is a single JSON file:

- **Mac:** `~/Library/Application Support/HushKey/vault.json`
- **Windows:** `%APPDATA%\HushKey\vault.json`

Saving uses an **atomic write**: write to a temp file, flush it to disk, then swap it in with `os.replace()`. If your computer crashes mid-save, you keep the old vault instead of a half-written broken one.

To **back up** your vault, copy that file. To **reset** HushKey (lose everything), delete it.

## Project files

| File | What it does |
|---|---|
| `vault.py` | Hashing, encryption, reading/writing the vault file. No UI. |
| `app.py` | The window (Tkinter, built into Python). |
| `test_vault.py` | Tests: `python -m unittest -v` |
| `build_mac.sh` / `build_windows.bat` | Build the app on your own computer. |
| `.github/workflows/build.yml` | GitHub builds both apps for you automatically. |

## Run from source

```bash
pip install -r requirements.txt
python app.py
```

(On Mac, use `python3`. If you installed Python from python.org, Tkinter is included.)

## Publishing a new version

```bash
git add .
git commit -m "Describe your change"
git push
git tag v1.0.0
git push origin v1.0.0
```

Pushing the tag makes GitHub build both apps and publish a Release with the Windows and Mac downloads. Bump the number (`v1.0.1`, `v1.1.0`…) each time.

## Limits (honest ones)

- This is a learning project, not audited security software.
- Python can't fully wipe secrets from memory after locking.
- The Mac build is for Apple Silicon (M1 and newer). Intel Macs can run it from source.
