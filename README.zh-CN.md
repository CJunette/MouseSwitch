# Mouse Follow（键鼠联动）

[English](README.md) · [下载最新版本](https://github.com/CJunette/MouseSwitch/releases/latest)

Mouse Follow 让 IQUNIX OG80 键盘与 Logitech MX Master 3S 鼠标切换到同一个 Easy-Switch 通道。键盘通过 `Fn+1` 或 `Fn+2` 离开当前电脑后，当前电脑会请求鼠标切换到对应通道。

当前推荐配置：

| 电脑 | 键盘按键 | 鼠标通道 |
| --- | --- | --- |
| Windows | `Fn+1` | 1 |
| MacBook | `Fn+2` | 2 |

Windows 提供通知区域图标与状态窗口；macOS 提供菜单栏图标。两端都能定义和保存本机的“键盘按键 → 鼠标通道”映射。

## 下载与安装

从 [Releases](https://github.com/CJunette/MouseSwitch/releases/latest) 下载对应系统的压缩包。

### Windows

1. 解压 `MouseFollow-Windows.zip` 到长期保留的位置。
2. 双击 `MouseFollow.exe`。
3. 右键通知区域的图标，打开状态窗口。
4. 确认映射为 `键盘 Fn+1 → 鼠标通道 1`。
5. 如需开机后自动运行，在托盘菜单中勾选“登录后自动启动”。

### macOS

1. 解压 `MouseFollow-macOS.zip`。
2. 双击与 `Mouse Follow.app` 同目录的 `Install.command`。它会安装程序并启用登录后自动启动。
3. 系统提示时，到“系统设置 → 隐私与安全性 → 输入监控”允许 Mouse Follow。
4. 点击菜单栏鼠标图标，确认映射为 `键盘 Fn+1 → 鼠标通道 1`。

发布包没有 Apple 签名。若 macOS 第一次阻止打开，请右键应用后选择“打开”，再在“隐私与安全性”中确认。全程不需要管理员密码。

## 工作方式与限制

程序不读取任何按键内容，而是观察 OG80 是否仍连接在本机。键鼠同时稳定连接至少三秒后，键盘持续离开约两秒会被视为切换请求；程序随后向 MX Master 3S 发送 Logitech HID++ `ChangeHost` 命令。

因此，键盘关机、没电或持续蓝牙断开，也可能被识别为离开。程序会过滤短暂掉线，但无法区分所有断开原因。

鼠标必须预先配对到每个目标通道。鼠标从当前电脑断开只说明请求已成功发出，不保证目标电脑已经完成蓝牙连接。

## 状态图标

| 标记 | 含义 |
| --- | --- |
| ✓ | 就绪，等待设定的键盘切换 |
| … | 正在等待设备或连接稳定 |
| Ⅱ | 已暂停联动 |
| ! | 权限或通信错误 |
| ↔ | 正在请求切换鼠标 |

## 从源码构建

macOS 建议使用 Python 3.12；Windows 支持 Python 3.10 或以上。

```sh
# macOS 开发版
python -m pip install -r requirements-mac.txt
python install_mac.py --install

# Windows 开发版
py -3 -m pip install -r requirements-windows-build.txt
py -3 build_windows.py
```

推送匹配 `v*` 的 Git 标签时，GitHub Actions 会自动构建 Windows 和 macOS 下载包，并创建 GitHub Release。

## 验证

在仓库根目录运行：

```sh
python -m unittest -v
```

MacBook → Windows 已使用本项目对应硬件完成测试；Windows → MacBook 请先在自己的 Windows 电脑实测。

## 致谢

HID++ `ChangeHost` 的实现参考 [mxswitch](https://github.com/marcocosta97/mxswitch)，键盘离开后驱动鼠标的思路参考 [logi_mx_auto_switch](https://github.com/omar16100/logi_mx_auto_switch)。本项目独立实现，未打包它们的代码或二进制文件。
