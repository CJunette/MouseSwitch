"""Build the Windows Mouse Follow application with its own icon."""
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
ICON = ROOT / "mouse_follow.ico"


def create_icon():
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = "#16a34a"
    draw.rounded_rectangle((20, 40, 168, 156), radius=16, outline=color, width=20)
    draw.line((56, 188, 136, 188), fill=color, width=20)
    draw.line((96, 156, 96, 188), fill=color, width=20)
    draw.rounded_rectangle((172, 100, 232, 216), radius=30, outline=color, width=20)
    draw.line((202, 124, 202, 156), fill=color, width=16)
    image.save(ICON, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                             (128, 128), (256, 256)])


def main():
    create_icon()
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--windowed", "--name", "MouseFollow", "--icon", str(ICON),
        "--collect-submodules", "pystray", "--workpath", str(ROOT / "build" / "windows"),
        "--specpath", str(ROOT / "build" / "windows"), "--distpath", str(ROOT),
        str(ROOT / "win_tray.py"),
    ], check=True)
    print("Built:", ROOT / "MouseFollow.exe")


if __name__ == "__main__":
    main()
