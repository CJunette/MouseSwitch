# Mouse Follow

[中文说明](README.zh-CN.md) · [Download the latest release](https://github.com/CJunette/MouseSwitch/releases/latest)

Mouse Follow keeps a Logitech MX Master 3S mouse on the same Easy-Switch channel as an IQUNIX OG80 keyboard. When the keyboard leaves one computer using its `Fn+1` or `Fn+2` device key, the connected computer sends the mouse to the matching channel.

The application is designed for this pairing over direct Bluetooth:

| Computer | Keyboard key | Mouse channel |
| --- | --- | --- |
| Windows | `Fn+1` | 1 |
| MacBook | `Fn+2` | 2 |

Each device has a small background UI. Choose the mapping from the Windows status window or the Mac menu-bar icon. The setting is stored separately on each computer.

## Download and install

Open [Releases](https://github.com/CJunette/MouseSwitch/releases/latest) and download the package for your computer.

### Windows

1. Extract `MouseFollow-Windows.zip` somewhere permanent.
2. Run `MouseFollow.exe`.
3. Right-click the notification-area icon and open the status window.
4. Set `Keyboard Fn+1 → Mouse channel 1`, if it is not already selected.
5. Enable **Launch at login** from the tray menu if you want it to run automatically.

### macOS

1. Extract `MouseFollow-macOS.zip`.
2. Double-click `Install.command` beside `Mouse Follow.app`. It installs the app for the current user and enables launch at login.
3. In **System Settings → Privacy & Security → Input Monitoring**, allow Mouse Follow when prompted.
4. Click the menu-bar mouse icon and confirm `Keyboard Fn+1 → Mouse channel 1` for this MacBook.

The release builds are unsigned. If macOS blocks the first launch, right-click the app, choose **Open**, then approve it in Privacy & Security. The program requires no administrator password.

## How it works

Mouse Follow does not read key presses. It observes whether the OG80 is still connected to the current computer. After both keyboard and mouse have been stable locally for three seconds, the app treats a keyboard departure lasting roughly two seconds as a switch request and sends Logitech's HID++ `ChangeHost` command to the MX Master 3S.

This means that turning the keyboard off, running its battery flat, or a sustained Bluetooth dropout can also look like a switch. A short dropout is filtered, but this cannot distinguish every disconnect cause.

The mouse must already be paired with every target channel. The mouse leaving the current computer confirms the request was sent; it does not prove the target computer accepted the Bluetooth connection.

## Status markers

| Marker | Meaning |
| --- | --- |
| ✓ | Ready to follow the configured keyboard switch |
| … | Waiting for devices or for the connection to stabilize |
| Ⅱ | Switching is paused |
| ! | Permission or communication error |
| ↔ | A mouse switch is being requested |

## Build from source

Python 3.12 is recommended for macOS; Windows supports Python 3.10 or later.

```sh
# macOS development build
python -m pip install -r requirements-mac.txt
python install_mac.py --install

# Windows development build
py -3 -m pip install -r requirements-windows-build.txt
py -3 build_windows.py
```

The GitHub Actions release workflow builds downloadable applications when a tag matching `v*` is pushed. It produces `MouseFollow-Windows.zip` and `MouseFollow-macOS.zip`, then attaches them to a GitHub Release.

## Verification

Run the hardware-independent checks from the repository root:

```sh
python -m unittest -v
```

The MacBook-to-Windows direction has been tested with the hardware above. Test the reverse direction on your own Windows computer before relying on it.

## Acknowledgements

The HID++ `ChangeHost` implementation is informed by [mxswitch](https://github.com/marcocosta97/mxswitch) and the departure-watcher approach by [logi_mx_auto_switch](https://github.com/omar16100/logi_mx_auto_switch). Mouse Follow is an independent implementation and does not bundle their code or binaries.
