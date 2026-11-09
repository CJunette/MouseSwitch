"""Native menu bar UI; all Cocoa calls stay on the main thread."""
import fcntl
import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import queue
import re
import subprocess
import threading

from AppKit import (NSApplication, NSApplicationActivationPolicyAccessory, NSImage,
                    NSMenu, NSMenuItem, NSStatusBar, NSVariableStatusItemLength,
                    NSWorkspace)
from Foundation import NSObject, NSTimer, NSURL, NSMakeSize
from follow import watch

LABEL = "local.changliu.mouse-follow"
DATA = Path.home() / "Library" / "Application Support" / "MouseFollow"
DATA.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA / "follow.log"
CORE_GRAPHICS = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
CORE_GRAPHICS.CGPreflightListenEventAccess.restype = ctypes.c_bool
CORE_GRAPHICS.CGRequestListenEventAccess.restype = ctypes.c_bool


def startup_enabled():
    result = subprocess.run(["/bin/launchctl", "print-disabled", f"gui/{os.getuid()}"],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "无法读取自动启动状态")
    # launchctl versions render booleans either as true/false or disabled/enabled.
    return not re.search(r'"' + re.escape(LABEL) + r'"\s*=>\s*(?:true|disabled)\b',
                         result.stdout)


class MenuApp(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "computermouse", "键鼠联动")
        if image:
            image.setSize_(NSMakeSize(18, 18))
            image.setTemplate_(True)
            self.item.button().setImage_(image)
        self.menu = NSMenu.alloc().init()
        self.status = self.add_item("正在启动…", None)
        self.status.setEnabled_(False)
        mapping = self.add_item("Mac 通道 2 → Windows 通道 1", None)
        mapping.setEnabled_(False)
        self.menu.addItem_(NSMenuItem.separatorItem())
        self.pause_item = self.add_item("暂停联动", "togglePause:")
        self.startup_item = self.add_item("登录时自动启动", "toggleStartup:")
        self.startup_item.setState_(1 if startup_enabled() else 0)
        self.add_item("打开运行日志", "openLog:")
        self.add_item("打开输入监控设置", "openPermissions:")
        self.menu.addItem_(NSMenuItem.separatorItem())
        self.add_item("退出（下次登录仍可自动启动）", "quit:")
        self.item.setMenu_(self.menu)
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.5, self, "refresh:", None, True)
        # Without this grant macOS can return an EMPTY HID enumeration rather
        # than an access error. Show the permission state instead of 'waiting'.
        if not CORE_GRAPHICS.CGPreflightListenEventAccess():
            CORE_GRAPHICS.CGRequestListenEventAccess()
        self.worker = threading.Thread(target=self.run_watcher, daemon=True)
        self.worker.start()
        logging.info("Menu bar application started; no terminal window required")

    def run_watcher(self):
        while not CORE_GRAPHICS.CGPreflightListenEventAccess():
            self.events.put(("error", "请在输入监控中允许 Mouse Follow，然后重新打开程序"))
            if self.stop_event.wait(2):
                return
        watch(1, False, stop_event=self.stop_event, pause_event=self.pause_event,
              on_status=lambda kind, message: self.events.put((kind, message)))

    def add_item(self, title, action):
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
        if action:
            item.setTarget_(self)
        self.menu.addItem_(item)
        return item

    def refresh_(self, timer):
        latest = None
        while True:
            try:
                latest = self.events.get_nowait()
            except queue.Empty:
                break
        if latest:
            kind, message = latest
            marker = {"armed": "✓", "paused": "Ⅱ", "error": "!",
                      "waiting": "…", "checking": "…", "switching": "↔"}[kind]
            self.item.button().setTitle_(marker)
            self.item.button().setToolTip_("键鼠联动：" + message)
            self.status.setTitle_(message[:100])
            logging.info("Menu status: %s — %s", kind, message)

    def togglePause_(self, sender):
        if self.pause_event.is_set():
            self.pause_event.clear()
            sender.setTitle_("暂停联动")
        else:
            self.pause_event.set()
            sender.setTitle_("恢复联动")

    def toggleStartup_(self, sender):
        try:
            enable = not startup_enabled()
            result = subprocess.run(["/bin/launchctl", "enable" if enable else "disable",
                                     f"gui/{os.getuid()}/{LABEL}"], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr.strip())
            sender.setState_(1 if startup_enabled() else 0)
        except Exception as exc:
            logging.exception("Cannot update login startup")
            self.events.put(("error", "无法更新自动启动：" + str(exc)))

    def openLog_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(str(LOG_FILE)))

    def openPermissions_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"))

    def quit_(self, sender):
        self.stop_event.set()
        self.worker.join(timeout=8)
        NSApplication.sharedApplication().terminate_(None)


def main():
    # flock releases automatically on exit and prevents duplicate menu watchers.
    lock = (DATA / "instance.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[RotatingFileHandler(LOG_FILE, maxBytes=1_000_000,
                                                      backupCount=2, encoding="utf-8")])
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = MenuApp.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
