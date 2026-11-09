"""Windows notification-area application for Mouse Follow."""
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk
import pystray

from follow import watch
from install_windows import set_startup, startup_enabled

APP_NAME = "Mouse Follow"
DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MouseFollow"
DATA.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA / "follow.log"
SETTINGS_FILE = DATA / "settings.json"
DEFAULT_MAPPING = {
    "mouse_destination_channel": 2,
}


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


STATUS_COLORS = {
    "armed": "#16a34a",
    "paused": "#6b7280",
    "error": "#dc2626",
    "waiting": "#f59e0b",
    "checking": "#3b82f6",
    "switching": "#8b5cf6",
}


def make_icon(color):
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Mirrors the Mac menu-bar app's "computermouse" symbol.
    draw.rounded_rectangle((5, 10, 42, 39), radius=4, outline=color, width=5)
    draw.line((14, 47, 34, 47), fill=color, width=5)
    draw.line((24, 39, 24, 47), fill=color, width=5)
    draw.rounded_rectangle((43, 25, 58, 54), radius=8, outline=color, width=5)
    draw.line((50, 31, 50, 39), fill=color, width=4)
    return image


class TrayApp:
    def __init__(self):
        self.stop_event = threading.Event()
        self.show_event = threading.Event()
        self.pause_event = threading.Event()
        self.status_kind = "checking"
        self.status_message = "正在启动…"
        self.status_lock = threading.Lock()
        self.observation = None
        self.mapping = load_mapping()
        self.worker = None
        self.worker_generation = 0
        self.mapping_message = "当前映射已加载"
        self.mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "MouseFollowTray")
        if ctypes.windll.kernel32.GetLastError() == 183:
            raise RuntimeError("Mouse Follow is already running")
        self.icon = pystray.Icon(APP_NAME, make_icon(STATUS_COLORS["checking"]), APP_NAME,
                                 self.menu())

    def menu(self):
        return pystray.Menu(
            pystray.MenuItem("打开状态窗口", lambda: self.show_event.set(), default=True),
            pystray.MenuItem(self.status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.pause_text, self.toggle_pause),
            pystray.MenuItem("登录后自动启动", self.toggle_startup,
                             checked=lambda _: startup_enabled()),
            pystray.MenuItem("打开运行日志", self.open_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.quit),
        )

    def status_text(self, _):
        with self.status_lock:
            return "状态：" + self.status_message

    def pause_text(self, _):
        return "恢复联动" if self.pause_event.is_set() else "暂停联动"

    def report(self, kind, message):
        with self.status_lock:
            self.status_kind, self.status_message = kind, message

    def observed(self, keyboard, mouse):
        with self.status_lock:
            self.observation = (keyboard, mouse, time.monotonic())

    def device_text(self):
        with self.status_lock:
            sample = self.observation
        if self.pause_event.is_set():
            return "已暂停检测"
        if sample is None or time.monotonic() - sample[2] > 4:
            return "等待最新设备读数…"
        def location(present):
            return "已连接 Windows" if present else "Windows 未检测到"
        return f"鼠标：{location(sample[1])}\n键盘：{location(sample[0])}"

    def update_tray(self, kind, message):
        self.icon.icon = make_icon(STATUS_COLORS.get(kind, STATUS_COLORS["checking"]))
        self.icon.title = APP_NAME + " — " + message
        self.icon.update_menu()

    def run_watcher(self, mapping, generation, stop_event):
        def report(kind, message):
            if generation == self.worker_generation:
                self.report(kind, message)

        def observed(keyboard, mouse):
            if generation == self.worker_generation:
                self.observed(keyboard, mouse)

        watch(mapping["mouse_destination_channel"], False, stop_event=stop_event,
              pause_event=self.pause_event, on_status=report, local_name="Windows",
              local_channel=1, target_name="Mac",
              on_presence=observed,
              trigger_label=f"键盘 Fn＋2 → 鼠标通道 {mapping['mouse_destination_channel']}")

    def start_watcher(self):
        self.worker_generation += 1
        generation = self.worker_generation
        self.stop_event = threading.Event()
        self.worker = threading.Thread(target=self.run_watcher,
                                       args=(self.mapping.copy(), generation, self.stop_event),
                                       name="MouseFollow", daemon=True)
        self.worker.start()

    def setup(self, icon):
        icon.visible = True
        self.start_watcher()
        self.icon.notify("已在通知区域后台运行。右键图标可查看状态或退出。", APP_NAME)
        logging.info("Windows notification-area application started")

    def toggle_pause(self, icon, item):
        if self.pause_event.is_set():
            self.pause_event.clear()
        else:
            self.pause_event.set()
        self.icon.update_menu()

    def apply_mapping(self, mouse_value):
        try:
            mapping = validate_mapping({
                "mouse_destination_channel": mouse_value.get(),
            })
            save_mapping(mapping)
        except ValueError as exc:
            self.mapping_message = str(exc)
            return
        self.mapping = mapping
        self.mapping_message = "已保存映射，正在重新开始监听"
        threading.Thread(target=self.restart_watcher, name="MouseFollowRestart", daemon=True).start()

    def restart_watcher(self):
        previous_stop = self.stop_event
        previous_worker = self.worker
        previous_stop.set()
        if previous_worker:
            previous_worker.join(timeout=4)
        self.start_watcher()

    def toggle_startup(self, icon, item):
        try:
            set_startup(not startup_enabled())
            self.icon.update_menu()
        except Exception as exc:
            logging.exception("Cannot update login startup")
            self.report("error", "无法更新登录启动：" + str(exc))

    def open_log(self, icon, item):
        LOG_FILE.touch(exist_ok=True)
        os.startfile(LOG_FILE)

    def quit(self, icon, item):
        self.stop_event.set()
        self.worker.join(timeout=8)
        self.icon.stop()

    def run(self):
        window = tk.Tk()
        window.title("Mouse Follow · 键鼠联动")
        self.window_icon = ImageTk.PhotoImage(make_icon(STATUS_COLORS["checking"]))
        window.iconphoto(True, self.window_icon)
        panel = ttk.Frame(window, padding=18)
        panel.pack(fill="both", expand=True)
        devices = ttk.Label(panel)
        devices.pack(anchor="w", pady=(0, 8))
        status = ttk.Label(panel, text="正在启动…", wraplength=360)
        status.pack(anchor="w", pady=(0, 14))
        mapping_box = ttk.LabelFrame(panel, text="设备映射", padding=10)
        mapping_box.pack(fill="x", pady=(0, 12))
        mouse_value = tk.StringVar(value=str(self.mapping["mouse_destination_channel"]))
        choices = ("1", "2", "3")
        ttk.Label(mapping_box, text="键盘 Fn＋2 → 鼠标通道").grid(row=0, column=0, sticky="w")
        ttk.Combobox(mapping_box, textvariable=mouse_value, values=choices,
                     state="readonly", width=5).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(mapping_box, text="保存映射",
                   command=lambda: self.apply_mapping(mouse_value)).grid(
                       row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        mapping_status = ttk.Label(mapping_box, wraplength=360)
        mapping_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        pause = ttk.Button(panel, command=lambda: self.toggle_pause(None, None))
        pause.pack(side="left")
        ttk.Button(panel, text="隐藏到托盘", command=window.withdraw).pack(side="left", padx=8)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)
        rendered = None
        def refresh():
            nonlocal rendered
            if self.stop_event.is_set():
                window.destroy()
                return
            if self.show_event.is_set():
                self.show_event.clear()
                window.deiconify()
                window.lift()
            devices.configure(text=self.device_text())
            with self.status_lock:
                current = self.status_kind, self.status_message
            status.configure(text="状态：" + current[1])
            mapping_status.configure(text=self.mapping_message)
            pause.configure(text=self.pause_text(None))
            window.after(250, refresh)
            if current != rendered and self.icon.visible:
                rendered = current
                self.window_icon = ImageTk.PhotoImage(
                    make_icon(STATUS_COLORS.get(current[0], STATUS_COLORS["checking"])))
                window.iconphoto(True, self.window_icon)
                try:
                    self.update_tray(*current)
                except Exception:
                    logging.exception("Could not refresh tray status")
        threading.Thread(target=self.icon.run, kwargs={"setup": self.setup}, daemon=True).start()
        refresh()
        window.mainloop()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[RotatingFileHandler(LOG_FILE, maxBytes=1_000_000,
                                                      backupCount=2, encoding="utf-8")])
    TrayApp().run()


if __name__ == "__main__":
    main()
