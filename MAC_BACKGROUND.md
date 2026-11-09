# Mac 菜单栏与登录启动

## 日常使用

菜单栏显示鼠标图标，旁边的标记表示状态：

| 标记 | 含义 |
| --- | --- |
| ✓ | 监听已就绪，Fn+1 可带鼠标切到 Windows |
| … | 等待设备返回 Mac 通道 2，或等待连接稳定 |
| Ⅱ | 已暂停，不自动切换 |
| ! | 权限或通信错误，点菜单查看具体原因 |
| ↔ | 正在请求鼠标切换 |

菜单可暂停/恢复、开关“登录时自动启动”、打开日志和输入监控设置、退出程序。

“设备映射”子菜单中显示并保存 `键盘 Fn＋1 → 鼠标通道`。默认通道为 1（Windows）。选择 1、2 或 3 后，菜单会勾选当前选择，保存到本机设置，并自动重启后台监听。你当前的两台电脑配置应保持为 **Fn＋1 → 鼠标通道 1**；除非你改变了鼠标的 Easy-Switch 配对关系，否则不要选择其他通道。
退出只结束本次运行；如果自动启动仍勾选，下次登录会重新启动。要长期停用，先取消勾选，再退出。
关闭终端和 ChatGPT 不影响菜单栏程序。自动启动发生在用户登录 Mac 后，不在 FileVault 解锁前运行。

程序安装在 `~/Applications/Mouse Follow.app`。重新打开可在 Finder 进入该位置，双击应用；仓库里的 Mac-Start.command 也会优先打开已安装的菜单栏程序。
已安装应用带有独立 Python 与依赖，无需保留开发用虚拟环境或固定源码目录来运行。

## 权限

菜单栏版本需要 macOS 输入监控权限，终端版本的授权不一定适用。
首次启动会调用系统授权请求；按照 macOS 提示打开“系统设置 → 隐私与安全性 → 输入监控”允许程序。
如需手动添加，选择 `~/Applications/Mouse Follow.app`。如果系统显示底层 Python，核对它是否来自该应用内的 `Contents/Resources/runtime/bin/python3.12`。
授权后若 macOS 要求重新打开，退出菜单栏程序，然后重新打开应用。
未授权时显示错误状态，不会把空的 HID 枚举误报为正常就绪。

## 安装或从源码更新

在本项目当前开发环境中：

```sh
../.venv/bin/python -m pip install -r requirements-mac.txt
../.venv/bin/python install_mac.py
../.venv/bin/python install_mac.py --install-prepared
```

第一步安装 Cocoa 界面依赖，第二步在 `build/` 准备可检查的应用与 LaunchAgent，第三步安装到当前用户目录并启动。
安装需要有权写入 `~/Applications`、`~/Library/LaunchAgents`、`~/Library/Application Support/MouseFollow`，不使用 sudo。
打包使用此项目 uv standalone CPython 3.12 的可搬移运行环境；不能直接用 macOS 系统 Python 或任意 framework Python 代替。源文件可以由 Git 同步；运行环境按电脑分别创建。
更新会保留先前安装的应用为 `Mouse Follow.previous-时间.app`，并停止该仓库旧的终端 watcher。旧备份可在确认新版正常后自行删除。

## 启动与日志

- 当前用户 LaunchAgent：`~/Library/LaunchAgents/local.changliu.mouse-follow.plist`
- 日志：`~/Library/Application Support/MouseFollow/follow.log`，单文件 1 MB，保留两个轮换文件。
- 启动错误：同目录下 `launchd.stderr.log`。
- 菜单通过 launchctl enable/disable 管理登录启动开关。正常退出不会立即自动重启；异常退出可由 launchd 重启。
- 应用用进程锁避免重复菜单栏实例。

## 验证记录

2026-11-09：独立应用运行环境导入 Cocoa/hidapi 成功；LaunchAgent 处于 running，RunAtLoad 已配置。
新应用获得鼠标控制权限后，成功读取当前通道 2；用户确认从菜单栏版本按 Fn+1 后鼠标自动切到 Windows。
10 项硬件无关测试通过，包括暂停、停止、缺席等待与状态逻辑。未通过重启整台 Mac 验证登录流程；已通过实际 LaunchAgent 启动验证。
Windows 端菜单栏/托盘与自动启动不包含在本次 Mac 实现中。
