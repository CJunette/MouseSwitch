# 鼠标跟随键盘：两端联调记录

此文件供 Windows 或 Mac 上的 ChatGPT Work / Codex 在打开本地项目后继续工作。
它记录项目事实与待办，不代表已经获得任何额外的系统权限或外部发布授权。

## 用户目标与配置

用户希望 IQUNIX OG80 按 Fn+1 / Fn+2 时，Logitech MX Master 3S 自动跟随切换。
- Windows：键盘 Fn+1、鼠标通道 1。
- MacBook：键盘 Fn+2、鼠标通道 2。
- 均为蓝牙直连。不需要网络通信，不需要 Logi Options+。
- Mac 实测设备：键盘名 IQUNIX OG80 BT2，鼠标 VID 046D、PID B034。
- 键盘 VID/PID 冒用 Apple 设备标识，程序按产品名和键盘 usage 识别，不能只按 VID/PID。

## 当前已验证

2026-11-09，Mac 枚举成功。用户在 macOS 授权输入监控后，终端以及获准的沙盒外执行成功读取 ChangeHost：feature index=10，host_count=3，current_channel=2。
程序不硬编码 feature index；每次通过 0x1814 动态查询。
用户按 Fn+1，Mac watcher 检测键盘离开，成功发送鼠标切换。用户确认鼠标自动切到 Windows。
Mac 的 8 项状态逻辑、启动等待、权限失败恢复与协议匹配单元测试通过。Windows 未实测成功，不能宣称双向已完成。

## 最新修复

旧版 Mac-Start 先执行 probe，鼠标当时不在 Mac 就立即退出。日志在 15:31:24 记录 MX Master 3S not found，此后没有 watcher 启动日志，终端窗口存在不等于 watcher 正在运行。
新版 Start 直接进入持续等待的 watcher。键鼠不在当前电脑时不退出；两者都出现时验证控制接口，保持 3 秒后显示 Armed，再允许离开触发。
Windows-Start 同样不因启动时鼠标缺席而退出。诊断 probe 仍是只读命令。
修复版 Mac 启动器已于 15:38:38 在终端启动，15:38:41 Armed，15:38:58 日志确认鼠标离开并请求通道 1；用户随后确认此次鼠标已自动切到 Windows，修复版 Mac → Windows 联动通过。监听继续在用户终端运行。

## Windows 当前阻塞与下一步

用户第一次跳过了 Setup，出现“系统找不到指定的路径”。执行 Setup 后发现没有可用的 Python 3.10+。
请在 Windows 上直接排查；不要使用 WSL 的 Python，必须访问 Windows 原生蓝牙 HID。

1. 确认这整个目录已解压到可写的本地目录；检查 py / python 是否可用，版本至少 3.10。
2. 帮用户安装合适的 Windows Python（支持标准 venv 与 pip；用户当前请求是继续修复此项目），遵守该会话实际权限提示。
3. 执行 Windows-Setup.cmd。它创建 Windows 本机 .venv 并安装 hidapi==0.15.0。不要复制 Mac 的 .venv 或 .python。
4. 键盘、鼠标先都手动切到 1，再运行 follow.py status 和 probe。验证产品名、PID、usage_page=FF43、usage=0202，记录实际输出。
5. 运行 Windows-Preview.cmd，按 Fn+2 观察 DRY RUN，验证 Windows 枚举能反映键盘断开。不能用包含已配对离线设备的列表代替实际连接状态。
6. 两端 Start 都运行，测试 Fn+2 自动将鼠标切回 Mac；然后测试往返。只将实际成功的方向标为通过。
7. 更新此文件的实测记录，并导出需传回 Mac 的源码补丁和简短结果。

## 文件与运行

- follow.py：跨平台 HID++ 控制与离开监听。
- requirements.txt：固定依赖。
- Mac-Start.command / Windows-Start.cmd：真实监听；保持窗口打开，Ctrl+C 停止。
- Mac-Diagnose.command：Mac 只读状态和接口诊断。
- Windows-Setup.cmd：首次创建环境、装依赖、诊断。
- *Preview*：只记录触发，不发送切换。
- follow.log：本机运行日志，不必同步或公开。
- test_follow.py：执行 python -m unittest -v，属于硬件无关测试。

## 两端代码共享

现在项目没有 Git 远程仓库，两台电脑的副本不会自动同步。修改源码后需要传回更新文件，并记录改动。
可以后续在用户选择的私有 Git 仓库中保存源码；不要提交 .venv、.python、缓存、日志或本机设置。不要未经请求发布到公开仓库。
ChatGPT 云项目的聊天/上传文件与本地项目文件夹不是一回事。Windows 要直接安装依赖、测试蓝牙，必须打开 Windows 本地目录，并有本地执行权限。

## 行为边界

只读取 HID 枚举和鼠标控制回复，不读取键盘按键。键盘断开约 2 秒后触发；关机、持续掉线也会被识别为离开。
启动时设备缺席不触发。键鼠同时在本机至少 3 秒才 armed。大于 5 秒的轮询间隔重置状态，用于减少休眠误触发。
发送后鼠标从本机枚举消失只是离开确认，目标电脑是否实际可用需用户/目标端验证。
不要同时运行多份 watcher。未安装开机启动。
