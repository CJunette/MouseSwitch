#!/bin/zsh
# Install the adjacent release app for the current user without sudo.
set -euo pipefail
RELEASE_DIR="${0:A:h}"
SOURCE_APP="$RELEASE_DIR/Mouse Follow.app"
DEST_APP="$HOME/Applications/Mouse Follow.app"
LABEL="local.changliu.mouse-follow"
AGENT_DIR="$HOME/Library/LaunchAgents"
AGENT_PATH="$AGENT_DIR/$LABEL.plist"
DATA_DIR="$HOME/Library/Application Support/MouseFollow"
USER_DOMAIN="gui/$(id -u)"

if [[ ! -d "$SOURCE_APP" ]]; then
  osascript -e 'display alert "Mouse Follow" message "Mouse Follow.app must be next to Install.command." as critical'
  exit 1
fi

mkdir -p "$HOME/Applications" "$AGENT_DIR" "$DATA_DIR"
launchctl bootout "$USER_DOMAIN/$LABEL" 2>/dev/null || true
if [[ -e "$DEST_APP" ]]; then
  mv "$DEST_APP" "$HOME/Applications/Mouse Follow.previous-$(date +%Y%m%d-%H%M%S).app"
fi
ditto "$SOURCE_APP" "$DEST_APP"

cat > "$AGENT_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$DEST_APP/Contents/MacOS/Mouse Follow</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>15</integer>
  <key>LimitLoadToSessionType</key><string>Aqua</string>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$DATA_DIR/launchd.stdout.log</string>
  <key>StandardErrorPath</key><string>$DATA_DIR/launchd.stderr.log</string>
</dict></plist>
PLIST

launchctl enable "$USER_DOMAIN/$LABEL"
launchctl bootstrap "$USER_DOMAIN" "$AGENT_PATH"
osascript -e 'display notification "Installed and set to launch at login." with title "Mouse Follow"'
