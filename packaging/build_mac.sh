#!/bin/bash
# Build HushKey.app on a Mac.   Run:  bash packaging/build_mac.sh
set -e
cd "$(dirname "$0")/.."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pyinstaller
python -m unittest discover -s tests
python app/app.py --selftest
pyinstaller --noconfirm --clean --windowed --name HushKey \
  --icon assets/HushKey.icns --add-data "assets:assets" \
  --collect-data customtkinter \
  --paths app --osx-bundle-identifier com.erickbardales.hushkey app/app.py
echo ""
echo "Done! Your app is at: dist/HushKey.app  (drag it into Applications)"
