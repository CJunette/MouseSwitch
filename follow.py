#!/usr/bin/env python3
"""OG80 departure watcher and direct-Bluetooth MX Master 3S ChangeHost client.

No keyboard reports or keystrokes are read. No automatic startup is installed.
"""
import argparse
import json
import logging
import platform
import time
from dataclasses import dataclass
from pathlib import Path

LOG = logging.getLogger("mouse-follow")


def inventory():
    import hid
    devices = hid.enumerate()
    keyboard = any("IQUNIX OG80" in (d.get("product_string") or "").upper()
                   and d.get("usage_page") == 1 and d.get("usage") == 6
                   for d in devices)
    mouse = [d for d in devices if d["vendor_id"] == 0x046D
             and d["product_id"] == 0xB034
             and d.get("usage_page") == 0xFF43
             and d.get("usage") == 0x0202]
    if len(mouse) > 1:
        raise RuntimeError("More than one MX Master 3S; refusing ambiguous control")
    return keyboard, mouse[0] if mouse else None


def frame(feature, function, params=()):
    data = bytes([0x11, 0xFF, feature, (function << 4) | 0x0D, *params])
    if len(data) > 20:
        raise ValueError("HID++ request too long")
    return data.ljust(20, b"\0")


def reply_matches(reply, feature, function):
    header = (function << 4) | 0x0D
    if len(reply) < 7 or reply[0] not in (0x10, 0x11) or reply[1] not in (0, 255):
        return False
    if reply[2] in (0x8F, 0xFF) and reply[3:5] == [feature, header]:
        raise RuntimeError(f"HID++ device error: {reply[5]:#x}")
    return reply[2:4] == [feature, header]


class Mouse:
    def __init__(self, info):
        import hid
        self.handle = hid.device()
        try:
            self.handle.open_path(info["path"])
        except OSError as exc:
            raise RuntimeError("Cannot open mouse HID interface. On macOS check Input "
                               "Monitoring for the launching terminal/Python, then restart it. "
                               "Do not assume a channel switch succeeded.") from exc

    def close(self):
        self.handle.close()

    def request(self, feature, function, params=()):
        # Drain stale responses before issuing a new request.
        for _ in range(64):
            if not self.handle.read(64, 1):
                break
        data = frame(feature, function, params)
        if self.handle.write(data) != len(data):
            raise RuntimeError("Incomplete HID++ write")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            reply = self.handle.read(64, 100)
            if reply_matches(reply, feature, function):
                return reply
        raise RuntimeError("HID++ response timed out")

    def feature_index(self):
        reply = self.request(0, 0, [0x18, 0x14, 0])
        if not reply[4]:
            raise RuntimeError("Mouse does not expose ChangeHost (0x1814)")
        return reply[4]

    def info(self):
        index = self.feature_index()
        reply = self.request(index, 0)
        return index, {"host_count": reply[4], "current_channel": reply[5] + 1}

    def switch(self, channel):
        index, info = self.info()
        if not 1 <= channel <= info["host_count"]:
            raise RuntimeError("Target channel is outside the device host count")
        if channel == info["current_channel"]:
            raise RuntimeError("Already on target channel; check channel mapping")
        # setCurrentHost disconnects immediately, so it normally has no reply.
        data = frame(index, 1, [channel - 1])
        if self.handle.write(data) != len(data):
            raise RuntimeError("Incomplete ChangeHost write")


@dataclass
class WatchState:
    seen_since: float | None = None
    absent_since: float | None = None
    armed: bool = False
    previous_poll: float | None = None

    def update(self, now, keyboard, mouse):
        # Large scheduling gaps include sleep/resume: require a fresh baseline.
        if self.previous_poll is not None and now - self.previous_poll > 5:
            self.reset()
        self.previous_poll = now
        if keyboard and mouse:
            self.absent_since = None
            if self.seen_since is None:
                self.seen_since = now
            if now - self.seen_since >= 3:
                self.armed = True
            return False
        self.seen_since = None
        if not mouse:
            self.reset()
            return False
        if not self.armed:
            return False
        if self.absent_since is None:
            self.absent_since = now
        if now - self.absent_since >= 2:
            self.reset()
            return True
        return False

    def reset(self):
        self.seen_since = self.absent_since = None
        self.armed = False


def switch_once(channel, info=None):
    if info is None:
        _, info = inventory()
    if info is None:
        raise RuntimeError("MX Master 3S is not connected to this computer")
    mouse = Mouse(info)
    try:
        mouse.switch(channel)
    finally:
        mouse.close()
    for _ in range(20):
        time.sleep(0.25)
        if inventory()[1] is None:
            LOG.info("Mouse left this computer; target channel %s requested", channel)
            return
    raise RuntimeError("Mouse still enumerates here; switch is UNCONFIRMED")


def watch(channel, dry_run, stop_event=None, pause_event=None, on_status=None,
          local_name="Mac", local_channel=2, target_name="Windows", on_presence=None,
          trigger_label=None):
    state = WatchState()
    last_presence = None
    last_status = None

    def report(kind, message):
        nonlocal last_status
        if (kind, message) != last_status and on_status:
            on_status(kind, message)
        last_status = (kind, message)

    LOG.info("Watching OG80 departure -> mouse channel %s; dry-run=%s", channel, dry_run)
    while not (stop_event and stop_event.is_set()):
        try:
            if pause_event and pause_event.is_set():
                state.reset()
                report("paused", "已暂停联动")
                time.sleep(0.5)
                continue
            keyboard, mouse = inventory()
            presence = (keyboard, mouse is not None)
            if on_presence:
                on_presence(*presence)
            if presence != last_presence:
                LOG.info("Presence: OG80=%s, MX Master 3S=%s", *presence)
                if not all(presence):
                    LOG.info("Waiting for BOTH devices on this computer. "
                             "Local channel: Windows=1, Mac=2. Watcher remains running.")
                last_presence = presence
            # Verify permission and protocol while both devices are here, rather
            # than waiting to discover an access problem when the keyboard leaves.
            if keyboard and mouse and state.seen_since is None and not state.armed and not dry_run:
                report("checking", "正在检查鼠标控制接口")
                handle = Mouse(mouse)
                try:
                    _, host_info = handle.info()
                    if channel == host_info["current_channel"]:
                        raise RuntimeError("Mouse is already on the target channel; check host mapping")
                    LOG.info("Mouse control ready: current channel=%s, target=%s",
                             host_info["current_channel"], channel)
                finally:
                    handle.close()
            was_armed = state.armed
            trigger = state.update(time.time(), keyboard, mouse is not None)
            if state.armed and not was_armed:
                LOG.info("Armed: keyboard and mouse both present")
            if state.armed and keyboard:
                report("armed", f"监听就绪，等待 {trigger_label or f'Fn＋{channel}'}")
            elif keyboard and mouse:
                report("checking", "正在等待连接稳定")
            elif state.armed:
                report("checking", "检测到键盘离开，正在确认")
            else:
                missing = "键盘" if mouse else ("鼠标" if keyboard else "键盘和鼠标")
                report("waiting", f"等待{missing}连接 {local_name}")
            if trigger:
                if dry_run:
                    LOG.info("DRY RUN: would switch mouse to channel %s", channel)
                else:
                    # Recheck to avoid acting on a keyboard that already returned.
                    if not inventory()[0] and not (pause_event and pause_event.is_set()) \
                            and not (stop_event and stop_event.is_set()):
                        report("switching", f"正在将鼠标切到 {target_name} 通道 {channel}")
                        # Use the mouse interface just observed at the moment of
                        # departure. Re-enumerating here can briefly lose a valid
                        # Bluetooth HID path while the keyboard is switching.
                        switch_once(channel, mouse)
                        report("waiting", f"已请求切到 {target_name}；等待设备返回 {local_name}")
        except Exception as exc:
            # Unknown enumeration/transport state must never mean 'keyboard left'.
            state.reset()
            report("error", str(exc))
            LOG.exception("Watcher paused this attempt; waiting for a fresh baseline")
            time.sleep(2)
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "probe", "switch", "watch"])
    parser.add_argument("--target", type=int, choices=[1, 2, 3])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command in ("switch", "watch") and args.target is None:
        parser.error("--target is required (Windows=1, Mac=2)")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(
                            Path(__file__).with_name("follow.log"), encoding="utf-8")])
    try:
        if args.command == "status":
            keyboard, mouse = inventory()
            print(json.dumps({"platform": platform.system(), "og80_present": keyboard,
                              "mx_master_3s_present": mouse is not None}, indent=2))
        elif args.command == "probe":
            _, info = inventory()
            if not info:
                raise RuntimeError("MX Master 3S not found")
            mouse = Mouse(info)
            try:
                index, host_info = mouse.info()
                print(json.dumps({"change_host_index": index, **host_info}, indent=2))
            finally:
                mouse.close()
        elif args.command == "switch":
            switch_once(args.target)
        else:
            watch(args.target, args.dry_run)
    except KeyboardInterrupt:
        LOG.info("Stopped")
    except Exception as exc:
        LOG.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
