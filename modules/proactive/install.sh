#!/usr/bin/env bash
# Generate schedule files for the proactive tasks. Does not touch your system
# scheduler directly: it generates the files and prints the command to activate
# them, so the final step is always an explicit one you take.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
GEN_DIR="$PROJECT_DIR/modules/proactive/generated"
RUNNER="$PROJECT_DIR/modules/proactive/run-task.sh"
mkdir -p "$GEN_DIR"

# Schedule: morning-brief daily at 07:00, weekly-review Friday at 17:00.
OS="$(uname -s)"
echo "Proactive module installer. Detected OS: $OS"
echo

if [ "$OS" = "Darwin" ]; then
  make_plist() {  # make_plist <task> <hour> <minute> [weekday]
    local task="$1" hour="$2" minute="$3" weekday="${4:-}"
    local label="com.compabob.proactive.$task"
    local plist="$GEN_DIR/$label.plist"
    local weekday_xml=""
    [ -n "$weekday" ] && weekday_xml="    <key>Weekday</key><integer>$weekday</integer>"
    cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$RUNNER</string>
    <string>$task</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>$hour</integer>
    <key>Minute</key><integer>$minute</integer>
$weekday_xml
  </dict>
  <key>StandardOutPath</key><string>$PROJECT_DIR/reports/proactive/launchd.out</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR/reports/proactive/launchd.err</string>
</dict>
</plist>
EOF
    echo "  generated $plist"
  }
  make_plist morning-brief 7 0
  make_plist weekly-review 17 0 5   # launchd Weekday: 0 or 7 = Sunday, so 5 = Friday
  echo
  echo "To activate, run:"
  echo "  cp $GEN_DIR/*.plist ~/Library/LaunchAgents/"
  echo "  launchctl load ~/Library/LaunchAgents/com.compabob.proactive.morning-brief.plist"
  echo "  launchctl load ~/Library/LaunchAgents/com.compabob.proactive.weekly-review.plist"
  echo
  echo "To deactivate later: launchctl unload the plists and delete them."

elif [ "$OS" = "Linux" ]; then
  CRON_FILE="$GEN_DIR/crontab.txt"
  cat > "$CRON_FILE" <<EOF
# Compabob: proactive tasks. Add these lines to your crontab (crontab -e).
0 7 * * *  cd "$PROJECT_DIR" && bash "$RUNNER" morning-brief
0 17 * * 5 cd "$PROJECT_DIR" && bash "$RUNNER" weekly-review
EOF
  echo "  generated $CRON_FILE"
  echo
  echo "To activate, add those lines to your crontab:"
  echo "  crontab -e        # then paste the contents of $CRON_FILE"
  echo "  (or: crontab -l | cat - \"$CRON_FILE\" | crontab -)"
  echo
  echo "To deactivate later: remove those lines with crontab -e."

else
  echo "Unsupported OS for automatic scheduling: $OS"
  echo "Run tasks manually instead: bash modules/proactive/run-task.sh morning-brief"
  exit 1
fi

echo
echo "Done. Test a task now with:"
echo "  bash modules/proactive/run-task.sh morning-brief"
