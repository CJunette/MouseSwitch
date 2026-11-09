"""Build a self-contained menu app and optionally install its login LaunchAgent.

Run with the project's Python after installing requirements-mac.txt.
No administrator privileges are used. Generated binaries are never committed.
"""
import argparse
import datetime
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import signal
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parent
LABEL = "local.changliu.mouse-follow"
APP_NAME = "Mouse Follow.app"
APP = Path.home() / "Applications" / APP_NAME
AGENT = Path.home() / "Library" / "LaunchAgents" / (LABEL + ".plist")
DATA = Path.home() / "Library" / "Application Support" / "MouseFollow"


def build():
    if sys.platform != "darwin":
        raise RuntimeError("This installer is for macOS only")
    import AppKit  # fail before installation if dependencies are missing
    import hid
    del AppKit, hid
    app = ROOT / "build" / APP_NAME
    if app.exists():
        shutil.rmtree(app)
    resources = app / "Contents" / "Resources"
    executable = app / "Contents" / "MacOS" / "MouseFollow"
    resources.mkdir(parents=True)
    executable.parent.mkdir()
    # This project's uv standalone CPython distribution is relocatable.
    # A framework/system Python is intentionally rejected instead of partially copied.
    runtime = Path(sys.base_prefix)
    if not (runtime / "bin" / "python3.12").is_file() or not (runtime / "lib" / "python3.12").is_dir():
        raise RuntimeError("Build with this project's standalone Python 3.12 environment")
    shutil.copytree(runtime, resources / "runtime", symlinks=True)
    destination = resources / "runtime" / "lib" / "python3.12" / "site-packages"
    shutil.copytree(Path(sysconfig.get_path("purelib")), destination, dirs_exist_ok=True,
                    symlinks=True)
    for name in ("follow.py", "i18n.py", "mac_menubar.py"):
        shutil.copy2(ROOT / name, resources / name)
    executable.write_text('#!/bin/zsh\nAPP_RES="${0:A:h:h}/Resources"\n'
                          'unset PYTHONHOME PYTHONPATH\n'
                          'exec "$APP_RES/runtime/bin/python3.12" "$APP_RES/mac_menubar.py"\n')
    executable.chmod(0o755)
    info = {"CFBundleExecutable": "MouseFollow", "CFBundleIdentifier": LABEL,
            "CFBundleName": "Mouse Follow", "CFBundleDisplayName": "键鼠联动",
            "CFBundlePackageType": "APPL", "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0", "LSUIElement": True,
            "NSHighResolutionCapable": True, "LSMinimumSystemVersion": "12.0"}
    (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(info))
    agent = {"Label": LABEL, "ProgramArguments": [str(APP / "Contents" / "MacOS" / "MouseFollow")],
             "WorkingDirectory": str(DATA), "RunAtLoad": True,
             "KeepAlive": {"SuccessfulExit": False}, "ThrottleInterval": 15,
             "LimitLoadToSessionType": "Aqua", "ProcessType": "Interactive",
             "StandardOutPath": str(DATA / "launchd.stdout.log"),
             "StandardErrorPath": str(DATA / "launchd.stderr.log"),
             "AssociatedBundleIdentifiers": [LABEL]}
    (ROOT / "build" / (LABEL + ".plist")).write_bytes(plistlib.dumps(agent))
    # Verify the copied runtime, independent of the development venv.
    subprocess.run([str(resources / "runtime" / "bin" / "python3.12"), "-c",
                    "import AppKit, hid; print('Bundled runtime imports OK')"], check=True)
    print("Prepared:", app)
    print("Prepared login agent:", ROOT / "build" / (LABEL + ".plist"))
    return app


def stop_legacy_watcher():
    listing = subprocess.run(["/bin/ps", "-axo", "pid=,command="],
                             capture_output=True, text=True, check=True)
    for line in listing.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        pid, command = parts
        try:
            args = shlex.split(command)
        except ValueError:
            continue
        if "follow.py" not in args or args[-3:] != ["watch", "--target", "1"]:
            continue
        cwd = subprocess.run(["/usr/sbin/lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"],
                             capture_output=True, text=True)
        if "n" + str(ROOT) in cwd.stdout.splitlines():
            os.kill(int(pid), signal.SIGTERM)
            print("Stopped this project's old terminal watcher:", pid)


def install(app):
    domain = f"gui/{os.getuid()}"
    subprocess.run(["/bin/launchctl", "bootout", f"{domain}/{LABEL}"],
                   capture_output=True)
    stop_legacy_watcher()
    APP.parent.mkdir(parents=True, exist_ok=True)
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    if APP.exists():
        backup = APP.with_name("Mouse Follow.previous-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".app")
        APP.rename(backup)
        print("Previous app preserved:", backup)
    shutil.copytree(app, APP, symlinks=True)
    shutil.copy2(ROOT / "build" / (LABEL + ".plist"), AGENT)
    subprocess.run(["/bin/launchctl", "enable", f"{domain}/{LABEL}"], check=True)
    subprocess.run(["/bin/launchctl", "bootstrap", domain, str(AGENT)], check=True)
    print("Installed:", APP)
    print("Login startup enabled:", AGENT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--install-prepared", action="store_true")
    args = parser.parse_args()
    app = ROOT / "build" / APP_NAME if args.install_prepared else build()
    if args.install or args.install_prepared:
        install(app)
