#!/bin/zsh
cd -- "${0:A:h}" || exit 1
echo '联动监听将持续运行。启动时鼠标不在 Mac 也会等待，不再退出。'
echo '请先将键盘和鼠标都切到 2；看到 Armed 后，再按 Fn+1 测试。'
echo '本窗口请保持打开。按 Ctrl+C 停止。'
../.venv/bin/python follow.py watch --target 1
result=$?
echo "监听已停止，退出码：$result。按回车关闭。"
read
exit "$result"
