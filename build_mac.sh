#!/bin/bash
# Build HushKey.app on a Mac.   Run:  bash build_mac.sh
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pyinstaller
python -m unittest
pyinstaller --noconfirm --windowed --name HushKey --osx-bundle-identifier com.hushkey.app app.py
echo ""
echo "Done! Your app is at: dist/HushKey.app  (drag it into Applications)"
