"""Install or remove the current user's Mouse Follow login startup entry on Windows."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
STARTUP = (Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu"
           / "Programs" / "Startup")
STARTUP_FILE = STARTUP / "Mouse Follow.vbs"


def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable)}"'
    application = ROOT / "MouseFollow.exe"
    if application.is_file():
        return f'"{application}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        raise RuntimeError("pythonw.exe is missing from the project environment")
    script = ROOT / "win_tray.py"
    if not script.is_file():
        raise RuntimeError("win_tray.py is missing")
    return f'"{pythonw}" "{script}"'


def startup_enabled():
    return STARTUP_FILE.is_file()


def set_startup(enabled):
    if enabled:
        STARTUP.mkdir(parents=True, exist_ok=True)
        command = launch_command().replace('"', '""')
        STARTUP_FILE.write_text(
            'CreateObject("WScript.Shell").Run "' + command + '", 1, False\r\n',
            encoding="utf-16")
    else:
        STARTUP_FILE.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true")
    group.add_argument("--remove", action="store_true")
    group.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise RuntimeError("This installer is for Windows only")
    if args.status:
        print("enabled" if startup_enabled() else "disabled")
    elif args.install:
        set_startup(True)
        print("Login startup enabled. It will launch Mouse Follow after you sign in.")
    else:
        set_startup(False)
        print("Login startup disabled.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
