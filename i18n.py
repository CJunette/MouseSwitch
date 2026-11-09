"""Small, dependency-free UI translation helper."""
import locale
import os


def is_chinese():
    language = os.environ.get("LANG", "") or (locale.getlocale()[0] or "")
    return language.lower().startswith("zh")


def text(chinese, english):
    return chinese if is_chinese() else english


def status(kind, detail="", destination_channel=None):
    labels = {
        "armed": text("监听就绪", "Ready"),
        "paused": text("联动已暂停", "Paused"),
        "waiting": text("等待设备连接", "Waiting for devices"),
        "checking": text("正在检查连接", "Checking connection"),
        "switching": text("正在切换鼠标", "Switching mouse"),
    }
    if kind == "armed" and destination_channel:
        return text(f"监听就绪：键盘切换后，鼠标将切到通道 {destination_channel}",
                    f"Ready: mouse will switch to channel {destination_channel}")
    if kind == "error":
        return text("错误：", "Error: ") + detail
    return labels.get(kind, detail or text("正在运行", "Running"))
