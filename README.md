# OG80 与 MX Master 3S 双机联动（待硬件验证）

**Mac 菜单栏版已安装并实测成功。** Mac 现可后台运行、显示状态图标并在用户登录后自动启动，无需保持终端窗口。日常操作、权限、更新与停用见 [MAC_BACKGROUND.md](MAC_BACKGROUND.md)。Windows 现提供通知区域后台版与登录启动安装器；首次仍应先完成预览测试。

通道固定为 Windows=1、Mac=2。Mac 监听 OG80 离开，通知鼠标切到 1；Windows 监听 OG80 离开，通知鼠标切到 2。

当前进度：Mac 已成功读取实际鼠标的 ChangeHost，feature index=10、host_count=3、current_channel=2。Mac → Windows 在终端版和菜单栏后台版均已实测成功。Mac 已注册用户登录自动启动；Windows → Mac 尚未实测，不能视为已完成双向硬件验证。

## Mac 下一步

1. 双击 `Mac-Diagnose.command`，在终端中运行只读诊断。
2. 如果显示 `Cannot open mouse HID interface`，检查 系统设置 → 隐私与安全性 → 输入监控，允许运行诊断的终端。如果需要添加 Python，可在文件选择器按 Command+Shift+G，定位到本工作目录下 `.python/cpython-3.12.16-macos-aarch64-none/bin/python3.12`。退出并重新打开终端后再诊断。系统授权需要本人操作；没有证据表明仅授权就一定能解决此机的 HID 打开失败。
3. 成功的 probe 应显示 `host_count` 和 `current_channel: 2`。如果仍打不开，请保留报错；下一条路线是安装 Logi Options+ 并评估其控制接口，或测试 Bolt 接收器。不要为了此程序关闭 SIP。
4. probe 成功后，运行 `Mac-Preview.command`：先让键鼠都在 Mac，等待 `Armed`；按 Fn+1，确认出现 `DRY RUN` 日志。此时鼠标不会切换。按 Fn+2 回到 Mac，并按 Ctrl+C 停止预览。
5. Windows 也完成诊断后，再分别运行两端的 Start 文件。Mac 目标是 1；Windows 目标是 2。两端窗口保持打开，Ctrl+C 停止。

启动器已修复：设备暂时不在本机时保持等待，不再因启动 probe 失败退出。键鼠都在本机后会验证控制接口，并在就绪后输出 Armed。

Mac 的 Python 和依赖已经放在当前工作目录，移动本目录或其父目录中的 `.venv` / `.python` 可能破坏启动路径。无需安装 Xcode。当前依赖为 `hidapi==0.15.0`。

## Windows

将本 `mouse-follow` 文件夹复制到 Windows，放在长期保留的位置。需要 Python 3.10 或以上，`py` 或 `python` 命令可用。先双击 `Windows-Setup.cmd` 创建本地虚拟环境、下载固定版本 hidapi、执行只读诊断。正常应显示 `og80_present: true`、`mx_master_3s_present: true`、`current_channel: 1`。

先用 `Windows-Preview.cmd` 验证离开检测（Fn+2）。通过后双击 `Windows-Start.cmd`，程序会在通知区域后台运行；右键其图标可查看状态、暂停/恢复、打开日志或退出。双击 `Windows-Install-Background.cmd` 会在当前用户的 Windows“启动”文件夹中登记登录后自动启动，并立即启动程序；不需要管理员权限。登录启动依赖本项目目录保持原位置，若移动项目目录，请重新运行安装器。此实现只匹配蓝牙直连、产品 ID 为 B034 的 MX Master 3S；如果 Windows 暴露不同产品 ID / 设备名，需要先适配，不能盲目启动。

## 行为与边界

- 不读取按键内容。只观察 OG80 是否存在，并向鼠标发送 ChangeHost。
- 启动时键盘不在本机不会触发；键鼠同时出现至少 3 秒后才准备触发。
- 键盘连续离开约 2 秒后触发，实际速度取决于蓝牙枚举刷新；还未测量本机时延。
- 大于 5 秒的轮询间隔（如休眠）会取消准备状态，重新等待键鼠同时出现。系统卡顿也可能暂时停止联动。
- 键盘关机、电量耗尽、持续蓝牙掉线与 Fn 切换无法仅靠设备消失区分，也会触发鼠标切换。两秒阈值只能过滤短暂掉线。
- 鼠标必须仍连接、可访问，且目标通道已经配对。鼠标休眠或通信失败可能需要手动按鼠标底部按钮。本版本失败会记录日志并取消本次动作，不持续重试。
- 鼠标离开本机只能确认发送后本地断开，不能证明它已经成功连接到目标电脑。
- 两台电脑都运行后才能双向自动切换；Windows 未运行时只能由 Mac 单向切出。
- 终端版日志写在 `follow.log`；后台版日志写在 `%LOCALAPPDATA%\MouseFollow\follow.log`。不要同时开多个 watcher。

## 实现参考

HID++ ChangeHost 动态查询和主机切换参考 [mxswitch](https://github.com/marcocosta97/mxswitch)。键盘离开后推送鼠标的方案参考 [logi_mx_auto_switch](https://github.com/omar16100/logi_mx_auto_switch)。本程序独立实现，未捆绑这两个项目的代码或二进制。hidapi 使用其自身许可，由 pip 安装。

逻辑测试：在本目录执行 `../.venv/bin/python -m unittest -v`。这些测试覆盖触发状态与协议匹配，不等于实际硬件联调。
