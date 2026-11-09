#!/bin/zsh
cd -- "${0:A:h}"
../.venv/bin/python follow.py watch --target 1 --dry-run
