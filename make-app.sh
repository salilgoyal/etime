#!/bin/bash
# Build etime.app: a small launcher that runs this repo's main.py with its .venv.
#
#   ./make-app.sh                  # installs to ~/Applications/etime.app
#   ./make-app.sh /Applications    # or somewhere else
#
# The app runs the code in this folder, so edits take effect on the next launch.
# Rebuild only if you move the repo. A rebuild changes the app's signature, so
# macOS will ask for Accessibility again.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$HOME/Applications}"
APP="$DEST/etime.app"

if [ ! -x "$REPO/.venv/bin/python" ]; then
    echo "No .venv found in $REPO — create it first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

mkdir -p "$DEST"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

clang -O2 -Wall -mmacosx-version-min=12.0 \
    -DETIME_REPO="\"$REPO\"" \
    -o "$APP/Contents/MacOS/etime" "$REPO/app/launcher.c"

# Icon: app/icon.png (drawn by app/make_icon.py) at every size macOS asks for.
ICONSET="$(mktemp -d)/etime.iconset"
mkdir -p "$ICONSET" "$APP/Contents/Resources"
for size in 16 32 128 256 512; do
    sips -z $size $size "$REPO/app/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    sips -z $((size * 2)) $((size * 2)) "$REPO/app/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/etime.icns"
rm -rf "$(dirname "$ICONSET")"

# LSUIElement: the launcher itself stays out of the Dock; the Python process it
# starts is the one with the windows (and the Dock icon).
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>etime</string>
    <key>CFBundleDisplayName</key>
    <string>etime</string>
    <key>CFBundleIdentifier</key>
    <string>local.etime.launcher</string>
    <key>CFBundleIconFile</key>
    <string>etime</string>
    <key>CFBundleExecutable</key>
    <string>etime</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF

codesign --force --sign - "$APP"

echo "Built $APP"
echo "Logs: ~/.etime/etime.log"
