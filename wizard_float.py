#!/usr/bin/env python3
"""
wizard_float.py — 魔法使いをデスクトップに浮かべ、
ダブルクリックで画面全体が光ったあとに壁紙を切り替えるアプリ。
PyObjC 使用。
"""

import os
import sys
import tempfile
import atexit
import subprocess
from pathlib import Path
import math
import time

from AppKit import (
    NSApplication, NSApp, NSWindow, NSView,
    NSImageView, NSImage, NSColor, NSMenu, NSMenuItem,
    NSEvent, NSBackingStoreBuffered, NSFloatingWindowLevel,
    NSTimer, NSRunLoop, NSRunLoopCommonModes,
    NSScreen,
)
from Foundation import NSObject, NSMakeRect
import objc

# ─────────── 自由に調整できる設定 ───────────
WIZARD_SIZE = 96          # 魔法使いの最大サイズ（ピクセル）
FLOAT_AMPLITUDE = 6.0     # 浮遊する上下の幅（ピクセル）
FLOAT_PERIOD = 2.5        # 浮遊の周期（秒）小さいほど速い
# ───────────────────────────────────────────

# ── パス設定 ─────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(SCRIPT_DIR, "wizard.png")
WALLPAPER_DIR = os.path.expanduser("~/Pictures/wallpapers")
WALLPAPER_EXTS = (".jpg", ".jpeg", ".png")

def get_wallpapers():
    """壁紙フォルダから画像ファイル一覧を返す。なければ自画像を代用"""
    try:
        files = sorted([
            str(p) for p in Path(WALLPAPER_DIR).iterdir()
            if p.suffix.lower() in WALLPAPER_EXTS
        ])
        if files:
            return files
    except FileNotFoundError:
        pass
    if os.path.isfile(IMAGE_PATH):
        return [IMAGE_PATH]
    return []

wallpaper_files = get_wallpapers()
if not wallpaper_files:
    print("⚠️ 警告: 壁紙として使える画像がありません。")

current_index = 0

def set_wallpaper(path):
    """指定された画像をデスクトップピクチャに設定する（内部処理）"""
    # 方法1: Finder（多くの場合安定）
    script = f'tell application "Finder" to set desktop picture to POSIX file "{path}"'
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode == 0:
        return True, "Finder"
    # 方法2: System Events
    script2 = f'tell application "System Events" to set picture of every desktop to POSIX file "{path}"'
    result2 = subprocess.run(["osascript", "-e", script2], capture_output=True, text=True)
    if result2.returncode == 0:
        return True, "System Events"
    # 失敗
    return False, result.stderr.strip()

def change_wallpaper():
    """次の壁紙に切り替え、必要なら Dock を再起動して即反映"""
    global current_index
    if not wallpaper_files:
        print("壁紙ファイルがありません。")
        return
    path = wallpaper_files[current_index]
    success, method = set_wallpaper(path)
    if success:
        print(f"✅ 壁紙を変更しました ({method}) → {os.path.basename(path)}")
        current_index = (current_index + 1) % len(wallpaper_files)
        # 即座に反映させるため Dock を再起動（チラつきが気になる場合は下の行をコメントアウト）
        subprocess.run(["killall", "Dock"], capture_output=True)
    else:
        print(f"❌ 壁紙変更に失敗しました: {method}")

# ── 閃光エフェクト用のオーバーレイウィンドウ ─────────
class FlashOverlayWindow(NSWindow):
    """画面全体を白く光らせるウィンドウ。終了時に close しない"""

    def init(self):
        screen_frame = NSScreen.mainScreen().frame()
        self = objc.super(FlashOverlayWindow, self).initWithContentRect_styleMask_backing_defer_(
            screen_frame, 0, NSBackingStoreBuffered, False
        )
        if self is None:
            return None
        self.setLevel_(NSFloatingWindowLevel + 1)
        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.whiteColor())
        self.setHasShadow_(False)
        self.setIgnoresMouseEvents_(True)
        self.contentView().setWantsLayer_(True)
        self.contentView().layer().setBackgroundColor_(NSColor.whiteColor().CGColor())
        self.setAlphaValue_(0.0)
        self._on_complete = None
        self._phase = 0.0
        self._timer = None
        return self

    def run_animation(self, on_complete):
        self._on_complete = on_complete
        self._phase = 0.0
        self.setAlphaValue_(0.0)
        self.orderFront_(None)   # 前面に表示
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.02, self, "animationStep:", None, True
        )

    def animationStep_(self, timer):
        self._phase += 0.02
        if self._phase <= 0.3:
            alpha = min(1.0, self._phase / 0.3) * 0.9
        elif self._phase <= 0.6:
            alpha = 0.9
        else:
            fade_out = (self._phase - 0.6) / 0.3
            alpha = 0.9 * (1.0 - min(1.0, fade_out))
        self.setAlphaValue_(alpha)

        if self._phase >= 0.9:
            timer.invalidate()
            self.orderOut_(None)          # 画面から消す（close はしない！）
            if self._on_complete:
                self._on_complete()
            # close() を呼ばないのでアプリが終了しない

# ── 魔法使いをクリックできるビュー ─────────────────
class ClickableImageView(NSView):
    def acceptsFirstMouse_(self, event):
        return True

    def mouseDown_(self, event):
        loc = event.locationInWindow()
        self._drag_offset_x = loc.x
        self._drag_offset_y = loc.y
        self._dragged = False
        if event.clickCount() == 2:
            delegate = NSApp.delegate()
            if delegate and hasattr(delegate, 'start_magic_flash'):
                delegate.start_magic_flash()
            self._dragged = True  # ドラッグ開始扱いで誤動作防止

    def mouseDragged_(self, event):
        if not self._dragged:
            self._dragged = True
        sl = NSEvent.mouseLocation()
        new_x = sl.x - self._drag_offset_x
        new_y = sl.y - self._drag_offset_y
        self.window().setFrameOrigin_((new_x, new_y))
        delegate = NSApp.delegate()
        if delegate and hasattr(delegate, 'set_base_position'):
            delegate.set_base_position(new_x, new_y)

    def mouseUp_(self, event):
        self._dragged = False

    def rightMouseDown_(self, event):
        menu = NSMenu.alloc().initWithTitle_("")
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "ウィザードを閉じる", "terminate:", ""
        )
        menu.addItem_(item)
        NSMenu.popUpContextMenu_withEvent_forView_(menu, event, self)


# ── 魔法使いの浮遊ウィンドウ ──────────────────────
class FloatingWindow(NSWindow):
    def init(self):
        image = NSImage.alloc().initWithContentsOfFile_(IMAGE_PATH)
        if image is None:
            print(f"❌ 画像が見つかりません: {IMAGE_PATH}")
            sys.exit(1)
        orig_w, orig_h = image.size().width, image.size().height
        scale = WIZARD_SIZE / max(orig_w, orig_h)
        w, h = orig_w * scale, orig_h * scale
        frame = NSMakeRect(500, 300, w, h)
        self = objc.super(FloatingWindow, self).initWithContentRect_styleMask_backing_defer_(
            frame, 0, NSBackingStoreBuffered, False
        )
        if self is None:
            return None
        self.setLevel_(NSFloatingWindowLevel)
        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self.setHasShadow_(False)
        self.setIgnoresMouseEvents_(False)
        self.setMovableByWindowBackground_(False)

        # 透明背景（警告抑止のためローカル変数で保持）
        clear_cg = NSColor.clearColor().CGColor()
        self.contentView().setWantsLayer_(True)
        self.contentView().layer().setBackgroundColor_(clear_cg)

        # クリックビューを配置
        self.image_view = ClickableImageView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        self.image_view.setWantsLayer_(True)

        # 実際の画像を貼り付け
        iv = NSImageView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        iv.setImage_(image)
        iv.setImageScaling_(1)  # アスペクト比維持
        iv.setEditable_(False)
        self.image_view.addSubview_(iv)

        self.contentView().addSubview_(self.image_view)
        self.image_view.image = image
        return self


# ── アプリケーションデリゲート ─────────────────────
class AppDelegate(NSObject):
    __slots__ = ('window', 'animation_timer', 'base_x', 'base_y', 'start_time', 'overlay')

    def applicationDidFinishLaunching_(self, notification):
        self.window = FloatingWindow.alloc().init()
        self.window.makeKeyAndOrderFront_(None)
        self.window.center()

        origin = self.window.frame().origin
        self.base_x = origin.x
        self.base_y = origin.y
        self.start_time = time.monotonic()

        # ふわふわ上下アニメーション
        self.animation_timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            1/60.0, self, "animate:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.animation_timer, NSRunLoopCommonModes)
        self.overlay = None  # 光エフェクト保持用

    def animate_(self, timer):
        t = time.monotonic() - self.start_time
        dy = FLOAT_AMPLITUDE * math.sin(2 * math.pi * t / FLOAT_PERIOD)
        self.window.setFrameOrigin_((self.base_x, self.base_y + dy))

    def set_base_position(self, x, y):
        self.base_x = x
        self.base_y = y
        self.start_time = time.monotonic()

    def start_magic_flash(self):
        """ダブルクリック時の処理：光エフェクト → 壁紙変更"""
        self.overlay = FlashOverlayWindow.alloc().init()
        if self.overlay:
            self.overlay.run_animation(on_complete=change_wallpaper)

    def applicationShouldTerminateAfterLastWindowClosed_(self, app):
        return False   # 魔法使いは明示的に閉じるまで残す

# ── 多重起動防止 ───────────────────────────────
LOCK_FILE = os.path.join(tempfile.gettempdir(), "wizard_float.lock")
if os.path.exists(LOCK_FILE):
    print("すでに起動しています。")
    sys.exit(0)
with open(LOCK_FILE, "w") as f:
    f.write(str(os.getpid()))
atexit.register(lambda: os.remove(LOCK_FILE))

# ── 起動 ─────────────────────────────────────
app = NSApplication.sharedApplication()
delegate = AppDelegate.alloc().init()
app.setDelegate_(delegate)
app.run()