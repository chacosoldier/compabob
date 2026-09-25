#!/usr/bin/env bash
# Compabob: Telegram module: optional always-on installer.
#
# The default, supported way to run the bot is by hand:
#     bash modules/telegram/poll.sh
# That is the low-maintenance path. This script is only for running the poller
# unattended in the background. A background daemon is the part of any kit most
# likely to need attention after an OS update, so treat this as opt-in.
#
# It only GENERATES the service file and prints the command to activate it. It
# never touches your system scheduler on its own.
set -euo pipefail

MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$MODULE_DIR/../.." && pwd)"
GEN_DIR="$MODULE_DIR/generated"
POLLER="$MODULE_DIR/poll.sh"
mkdir -p "$GEN_DIR" "$PROJECT_DIR/reports/telegram"

OS="$(uname -s)"
echo "Telegram module installer. Detected OS: $OS"
echo

if [ "$OS" = "Darwin" ]; then
  LABEL="com.compabob.telegram"
  PLIST="$GEN_DIR/$LABEL.plist"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$POLLER</string>
  </array>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$PROJECT_DIR/reports/telegram/launchd.out</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR/reports/telegram/launchd.err</string>
</dict>
</plist>
EOF
  echo "  generated $PLIST"
  echo
  echo "To activate, run:"
  echo "  cp \"$PLIST\" ~/Library/LaunchAgents/"
  echo "  launchctl load ~/Library/LaunchAgents/$LABEL.plist"
  echo
  echo "To stop later:"
  echo "  launchctl unload ~/Library/LaunchAgents/$LABEL.plist && rm ~/Library/LaunchAgents/$LABEL.plist"

elif [ "$OS" = "Linux" ]; then
  UNIT="$GEN_DIR/compabob-telegram.service"
  cat > "$UNIT" <<EOF
[Unit]
Description=Compabob: Telegram poller
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=/bin/bash $POLLER
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
  echo "  generated $UNIT"
  echo
  echo "To activate as a systemd user service, run:"
  echo "  mkdir -p ~/.config/systemd/user"
  echo "  cp \"$UNIT\" ~/.config/systemd/user/"
  echo "  systemctl --user daemon-reload"
  echo "  systemctl --user enable --now compabob-telegram.service"
  echo
  echo "No systemd? Run it under your own supervisor, or simply:"
  echo "  nohup bash \"$POLLER\" >/dev/null 2>&1 &"
  echo
  echo "To stop later: systemctl --user disable --now compabob-telegram.service"

else
  echo "Unsupported OS for automatic scheduling: $OS"
  echo "Run the poller by hand instead:  bash modules/telegram/poll.sh"
  exit 1
fi

echo
echo "After activating, set  telegram: true  in config/user.config.yaml."
