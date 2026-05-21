#!/usr/bin/env bash
# Compabob LinkedIn outreach module: optional weekday-morning scheduler.
#
# The default, supported way to use this module is by hand:
#     bash modules/linkedin-outreach/draft.sh
# This script is only for drafting a card automatically every weekday morning.
# It GENERATES the schedule file and prints the command to activate it; it never
# touches your system scheduler on its own.
set -euo pipefail

MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$MODULE_DIR/../.." && pwd)"
GEN_DIR="$MODULE_DIR/generated"
DRAFT="$MODULE_DIR/draft.sh"
mkdir -p "$GEN_DIR" "$PROJECT_DIR/reports/linkedin-outreach"

OS="$(uname -s)"
echo "LinkedIn outreach module installer (OS: $OS)"
echo

if [ "$OS" = "Darwin" ]; then
  LABEL="com.compabob.linkedin-outreach"
  PLIST="$GEN_DIR/$LABEL.plist"
  WEEKDAYS=""
  for d in 1 2 3 4 5; do
    WEEKDAYS="$WEEKDAYS    <dict><key>Weekday</key><integer>$d</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
"
  done
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$DRAFT</string>
    <string>--scheduled</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
$WEEKDAYS  </array>
  <key>StandardOutPath</key><string>$PROJECT_DIR/reports/linkedin-outreach/launchd.out</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR/reports/linkedin-outreach/launchd.err</string>
</dict>
</plist>
EOF
  echo "  generated $PLIST"
  echo
  echo "To activate (drafts a card every weekday at 08:00), run:"
  echo "  cp \"$PLIST\" ~/Library/LaunchAgents/"
  echo "  launchctl load ~/Library/LaunchAgents/$LABEL.plist"
  echo
  echo "To stop later:"
  echo "  launchctl unload ~/Library/LaunchAgents/$LABEL.plist && rm ~/Library/LaunchAgents/$LABEL.plist"

elif [ "$OS" = "Linux" ]; then
  CRON_FILE="$GEN_DIR/crontab.txt"
  cat > "$CRON_FILE" <<EOF
# Compabob LinkedIn outreach. Drafts one card each weekday at 08:00.
0 8 * * 1-5  cd "$PROJECT_DIR" && bash "$DRAFT" --scheduled
EOF
  echo "  generated $CRON_FILE"
  echo
  echo "To activate, add that line to your crontab:"
  echo "  crontab -e        # then paste the contents of $CRON_FILE"
  echo
  echo "To deactivate later: remove that line with crontab -e."

else
  echo "Unsupported OS for automatic scheduling: $OS"
  echo "Run the module by hand instead:  bash modules/linkedin-outreach/draft.sh"
  exit 1
fi

echo
echo "A scheduled run only ever drafts a card. Nothing is sent: you still review"
echo "and send every invite by hand."
echo
echo "After activating, set  linkedin_outreach: true  in config/user.config.yaml."
