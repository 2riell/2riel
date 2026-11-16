#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .build-venv-mac
.build-venv-mac/bin/python -m pip install -r requirements.txt pyinstaller==6.16.0
.build-venv-mac/bin/python -m unittest discover -v
.build-venv-mac/bin/python -m PyInstaller --noconfirm --clean --windowed --onedir --name FishingLab --osx-bundle-identifier com.fishinglab.desktop --collect-submodules mss.darwin --exclude-module pynput --hidden-import AppKit --hidden-import Quartz --hidden-import ApplicationServices app.py
/usr/libexec/PlistBuddy -c 'Set :NSHighResolutionCapable true' dist/FishingLab.app/Contents/Info.plist || /usr/libexec/PlistBuddy -c 'Add :NSHighResolutionCapable bool true' dist/FishingLab.app/Contents/Info.plist
codesign --force --deep --sign - dist/FishingLab.app
# GUI/import validation only: CI cannot grant interactive Screen Recording access.
dist/FishingLab.app/Contents/MacOS/FishingLab --gui-smoke-test
mkdir -p mac-download
cp README.md mac-download/README.md
ditto -c -k --sequesterRsrc --keepParent dist/FishingLab.app mac-download/FishingLab-macOS.zip
shasum -a 256 mac-download/FishingLab-macOS.zip > mac-download/SHA256.txt
