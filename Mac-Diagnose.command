#!/bin/zsh
cd -- "${0:A:h}"
../.venv/bin/python follow.py status
../.venv/bin/python follow.py probe
echo '诊断结束。请把以上结果发给我。按回车关闭。'
read
