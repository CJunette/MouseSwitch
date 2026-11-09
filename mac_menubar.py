"""Native menu bar UI; all Cocoa calls stay on the main thread."""
import fcntl
import ctypes
import json
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
from i18n import status as status_text
from i18n import text

LABEL = "local.changliu.mouse-follow"
DATA = Path.home() / "Library" / "Application Support" / "MouseFollow"
DATA.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA / "follow.log"
SETTINGS_FILE = DATA / "settings.json"
DEFAULT_MAPPING = {
    "mouse_destination_channel": 1,
}
CORE_GRAPHICS = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
CORE_GRAPHICS.CGPreflightListenEventAccess.restype = ctypes.c_bool
CORE_GRAPHICS.CGRequestListenEventAccess.restype = ctypes.c_bool


def validate_mapping(mapping):
    result = {}
    for key, default in DEFAULT_MAPPING.items():
        value = mapping.get(key, default)
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("通道必须是 1、2 或 3") from exc
        if value not in (1, 2, 3):
            raise ValueError("通道必须是 1、2 或 3")
        result[key] = value
    return result


def load_mapping(path=SETTINGS_FILE):
    try:
        return validate_mapping(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return DEFAULT_MAPPING.copy()


def save_mapping(mapping, path=SETTINGS_FILE):
    path.write_text(json.dumps(validate_mapping(mapping), indent=2), encoding="utf-8")


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
        self.mapping = load_mapping()
        self.worker = None
        self.worker_generation = 0
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "computermouse", "Mouse Follow")
        if image:
            image.setSize_(NSMakeSize(18, 18))
            image.setTemplate_(True)
            self.item.button().setImage_(image)
        self.menu = NSMenu.alloc().init()
        self.status = self.add_item(text("正在启动…", "Starting…"), None)
        self.status.setEnabled_(False)
        self.mapping_menu = NSMenu.alloc().initWithTitle_(text("设备映射", "Device mapping"))
        self.mapping_item = self.add_item(text("设备映射", "Device mapping"), None)
        self.mapping_item.setSubmenu_(self.mapping_menu)
        self.rebuild_mapping_menu()
        self.menu.addItem_(NSMenuItem.separatorItem())
        self.pause_item = self.add_item(text("暂停联动", "Pause switching"), "togglePause:")
        self.startup_item = self.add_item(text("登录时自动启动", "Launch at login"), "toggleStartup:")
        self.startup_item.setState_(1 if startup_enabled() else 0)
        self.add_item(text("打开运行日志", "Open log"), "openLog:")
        self.add_item(text("打开输入监控设置", "Open Input Monitoring settings"), "openPermissions:")
        self.menu.addItem_(NSMenuItem.separatorItem())
        self.add_item(text("退出（下次登录仍可自动启动）",
                           "Quit (will start again at next login)"), "quit:")
        self.item.setMenu_(self.menu)
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.5, self, "refresh:", None, True)
        # Without this grant macOS can return an EMPTY HID enumeration rather
        # than an access error. Show the permission state instead of 'waiting'.
        if not CORE_GRAPHICS.CGPreflightListenEventAccess():
            CORE_GRAPHICS.CGRequestListenEventAccess()
        self.start_watcher()
        logging.info("Menu bar application started; no terminal window required")

    def rebuild_mapping_menu(self):
        self.mapping_menu.removeAllItems()
        title = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            text("键盘 Fn＋1 → 鼠标通道", "Keyboard Fn+1 → Mouse channel"), None, "")
        title.setEnabled_(False)
        self.mapping_menu.addItem_(title)
        for channel in (1, 2, 3):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                text(f"鼠标通道 {channel}", f"Mouse channel {channel}"), "setMapping:", "")
            item.setTarget_(self)
            item.setTag_(channel)
            item.setState_(1 if channel == self.mapping["mouse_destination_channel"] else 0)
            self.mapping_menu.addItem_(item)

    def run_watcher(self, mapping, generation, stop_event):
        while not CORE_GRAPHICS.CGPreflightListenEventAccess():
            if generation == self.worker_generation:
                self.events.put(("error", text("请在输入监控中允许 Mouse Follow，然后重新打开程序",
                                                 "Allow Mouse Follow in Input Monitoring, then reopen it")))
            if stop_event.wait(2):
                return
        watch(mapping["mouse_destination_channel"], False, stop_event=stop_event,
              pause_event=self.pause_event, local_name="MacBook", local_channel=2,
              target_name="Windows",
            trigger_label=text(f"键盘 Fn＋1 → 鼠标通道 {mapping['mouse_destination_channel']}",
                               f"keyboard Fn+1 → mouse channel "
                               f"{mapping['mouse_destination_channel']}"),
              on_status=lambda kind, message: generation == self.worker_generation
              and self.events.put((kind, message)))

    def start_watcher(self):
        self.worker_generation += 1
        generation = self.worker_generation
        self.stop_event = threading.Event()
        self.worker = threading.Thread(target=self.run_watcher,
                                       args=(self.mapping.copy(), generation, self.stop_event),
                                       daemon=True)
        self.worker.start()

    def restart_watcher(self):
        previous_stop = self.stop_event
        previous_worker = self.worker
        previous_stop.set()
        if previous_worker:
            previous_worker.join(timeout=4)
        self.start_watcher()

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
            display = status_text(kind, message, self.mapping["mouse_destination_channel"])
            self.item.button().setToolTip_("Mouse Follow: " + display)
            self.status.setTitle_(display[:100])
            logging.info("Menu status: %s — %s", kind, message)

    def togglePause_(self, sender):
        if self.pause_event.is_set():
            self.pause_event.clear()
            sender.setTitle_(text("暂停联动", "Pause switching"))
        else:
            self.pause_event.set()
            sender.setTitle_(text("恢复联动", "Resume switching"))

    def setMapping_(self, sender):
        try:
            self.mapping = validate_mapping({"mouse_destination_channel": sender.tag()})
            save_mapping(self.mapping)
        except (OSError, ValueError) as exc:
            logging.exception("Cannot save mapping")
            self.events.put(("error", text("无法保存映射：", "Could not save mapping: ") + str(exc)))
            return
        self.rebuild_mapping_menu()
        self.events.put(("checking", text("已保存映射，正在重新开始监听",
                                           "Mapping saved; restarting watcher")))
        threading.Thread(target=self.restart_watcher, daemon=True).start()

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
            self.events.put(("error", text("无法更新自动启动：", "Could not update launch at login: ") + str(exc)))

    def openLog_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(str(LOG_FILE)))

    def openPermissions_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"))

    def quit_(self, sender):
        self.stop_event.set()
        if self.worker:
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
