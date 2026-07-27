#!/bin/bash
# Wizard.app をビルドして /Applications にインストールするスクリプト。
# リポジトリのコードをそのまま実行する薄いラッパー（コード修正後は再ビルド不要）。
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Wizard"
APP_PATH="/Applications/${APP_NAME}.app"
BUNDLE_ID="com.torusk.wallpaper-wizard"
ICON_SRC="${REPO_DIR}/wizard.png"
WORK_DIR="$(mktemp -d)"
ICONSET_DIR="${WORK_DIR}/Wizard.iconset"

echo "📦 リポジトリ: ${REPO_DIR}"

# ── 1. アイコン生成（wizard.png → .icns） ──────────────
mkdir -p "${ICONSET_DIR}"
sips -z 16 16     "${ICON_SRC}" --out "${ICONSET_DIR}/icon_16x16.png"      >/dev/null
sips -z 32 32     "${ICON_SRC}" --out "${ICONSET_DIR}/icon_16x16@2x.png"   >/dev/null
sips -z 32 32     "${ICON_SRC}" --out "${ICONSET_DIR}/icon_32x32.png"      >/dev/null
sips -z 64 64     "${ICON_SRC}" --out "${ICONSET_DIR}/icon_32x32@2x.png"   >/dev/null
sips -z 128 128   "${ICON_SRC}" --out "${ICONSET_DIR}/icon_128x128.png"    >/dev/null
sips -z 256 256   "${ICON_SRC}" --out "${ICONSET_DIR}/icon_128x128@2x.png" >/dev/null
sips -z 256 256   "${ICON_SRC}" --out "${ICONSET_DIR}/icon_256x256.png"    >/dev/null
sips -z 512 512   "${ICON_SRC}" --out "${ICONSET_DIR}/icon_256x256@2x.png" >/dev/null
sips -z 512 512   "${ICON_SRC}" --out "${ICONSET_DIR}/icon_512x512.png"    >/dev/null
sips -z 1024 1024 "${ICON_SRC}" --out "${ICONSET_DIR}/icon_512x512@2x.png" >/dev/null
iconutil -c icns "${ICONSET_DIR}" -o "${WORK_DIR}/Wizard.icns"
echo "✅ アイコン生成完了"

# ── 2. .app バンドルの構築 ─────────────────────────────
rm -rf "${APP_PATH}"
mkdir -p "${APP_PATH}/Contents/MacOS" "${APP_PATH}/Contents/Resources"
cp "${WORK_DIR}/Wizard.icns" "${APP_PATH}/Contents/Resources/Wizard.icns"

cat > "${APP_PATH}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIconFile</key>
    <string>Wizard.icns</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# 起動スクリプト: ログを ~/Library/Logs/Wizard.log に出す
cat > "${APP_PATH}/Contents/MacOS/Wizard" << EOF
#!/bin/bash
export PATH="/opt/homebrew/bin:\$HOME/.local/bin:/usr/local/bin:\$PATH"
LOG_FILE="\$HOME/Library/Logs/Wizard.log"
exec >> "\$LOG_FILE" 2>&1
echo "===== \$(date '+%Y-%m-%d %H:%M:%S') 起動 ====="
cd "${REPO_DIR}" || exit 1
exec uv run python wizard_float.py
EOF
chmod +x "${APP_PATH}/Contents/MacOS/Wizard"

# ── 3. アドホック署名 ─────────────────────────────────
codesign --force --deep --sign - "${APP_PATH}" >/dev/null 2>&1 || true

rm -rf "${WORK_DIR}"
echo "✅ ${APP_PATH} にインストール完了"
echo "   起動: open -a ${APP_NAME}"
echo "   ログ: ~/Library/Logs/Wizard.log"
