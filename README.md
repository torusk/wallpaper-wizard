# 🧙 wallpaper-wizard

デスクトップに小さな魔法使いを浮かべ、ダブルクリックすると画面全体が光り、壁紙が切り替わる macOS アプリ。

![魔法使い](wizard.png)

## ✨ 特徴

- ふわふわ上下に浮遊する魔法使いの画像（`wizard.png`）
- ダブルクリックで画面全体が白くフラッシュ → 壁紙チェンジ
- メニューバーの杖アイコンから「今すぐ壁紙切替／壁紙フォルダを開く／ウィザード表示・隠す／終了」
- 右クリックでウィザードを閉じる（アプリはメニューバーに常駐したまま）
- ドラッグで好きな位置に移動可能
- サイズ・浮遊の動きはコード先頭の定数で自由に調整可能

## 📋 必要環境

- macOS（Apple Silicon / Intel）
- Python 3.13+ （[uv](https://github.com/astral-sh/uv) 推奨）
- PyObjC（`pyobjc-framework-Cocoa`）

## 🚀 クイックスタート

### 1. リポジトリをクローン
```bash
git clone https://github.com/torusk/wallpaper-wizard.git
cd wallpaper-wizard
```

### 2. 依存パッケージをインストール
```bash
uv sync
```

### 3. 魔法使いの画像を用意
`wizard.png` をプロジェクトフォルダに置いてください。  
（既存のサンプル画像を使うか、好きな画像を `wizard.png` という名前で配置）

### 4. 壁紙画像を用意（任意）
`~/Pictures/wallpapers/` フォルダを作り、壁紙にしたい `.jpg` または `.png` 画像を入れてください。
フォルダが空の場合、`wizard.png` が壁紙として使われます。
（起動中はメニューバーの🧙 →「壁紙フォルダを開く」でFinderから直接画像を放り込めます。追加した画像は再起動不要で即反映されます）

### 5. 実行
```bash
uv run python wizard_float.py
```
（クラッシュ後にロックファイルが残っても自動で上書きされるため、事前の削除は不要です）

## ⚙️ 設定

`wizard_float.py` の先頭にある定数でカスタマイズできます。

```python
WIZARD_SIZE = 64           # アイコンの最大サイズ（ピクセル）
FLOAT_AMPLITUDE = 6.0      # 浮遊の上下幅（ピクセル）
FLOAT_PERIOD = 2.5         # 浮遊の周期（秒）
```

## 🖥️ アプリ化＆オート起動

### .app をビルド（ダブルクリック起動）
```bash
bash scripts/build_app.sh
```
`wizard.png` からアイコンを生成し、`/Applications/Wizard.app` を作成します（Dock には表示されない常駐型）。
Finder からダブルクリック、または `open -a Wizard` で起動。ログは `~/Library/Logs/Wizard.log` に出力されます。

このアプリはリポジトリのコードをそのまま実行するラッパーです。コードを修正しても再ビルドは不要で、次回起動時から反映されます（`wizard.png` を差し替えた場合はアイコン更新のために再ビルドしてください）。

### ログイン時オート起動
```bash
cp scripts/com.torusk.wallpaper-wizard.plist ~/Library/LaunchAgents/ && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.torusk.wallpaper-wizard.plist
```

### アンインストール
```bash
launchctl bootout gui/$(id -u)/com.torusk.wallpaper-wizard; rm -rf ~/Library/LaunchAgents/com.torusk.wallpaper-wizard.plist /Applications/Wizard.app
```

## 📄 ライセンス

MIT License

## 👤 作者

[@torusk](https://github.com/torusk)
