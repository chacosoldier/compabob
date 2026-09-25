#!/usr/bin/env bash
# Compabob dictation module: optional schedulers for the cleanup proxy + the
# nightly learning loop.
#
# The default, supported way to use this module is by hand:
#     python3 modules/dictation/proxy.py        # run the cleanup endpoint
#     python3 modules/dictation/learn.py        # grow the glossary
# This script GENERATES launchd/cron files and prints the command to activate
# them; it never touches your system scheduler on its own.
set -euo pipefail

MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$MODULE_DIR/../.." && pwd)"
GEN_DIR="$MODULE_DIR/generated"
LOG_DIR="$PROJECT_DIR/reports/dictation"
PROXY="$MODULE_DIR/proxy.py"
LEARN="$MODULE_DIR/learn.py"
mkdir -p "$GEN_DIR" "$LOG_DIR"

# Prefer the module venv (see README), which holds pyyaml; fall back to python3.
PY="$MODULE_DIR/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "python3 not found on PATH. Install it, then create the module venv (see README)."
  exit 1
fi

OS="$(uname -s)"
echo "Dictation module installer (OS: $OS, python3: $PY)"
echo

if [ "$OS" = "Darwin" ]; then
  # --- proxy: KeepAlive long-running endpoint -------------------------
  PLABEL="com.compabob.dictation-proxy"
  PPLIST="$GEN_DIR/$PLABEL.plist"
  cat > "$PPLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$PLABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$PROXY</string>
  </array>
  <key>WorkingDirectory</key><string>$PROJECT_DIR</string>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>ThrottleInterval</key><integer>60</integer>
  <key>StandardOutPath</key><string>$LOG_DIR/proxy.out</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/proxy.err</string>
</dict>
</plist>
EOF
  echo "  generated $PPLIST"

  # --- learn: nightly glossary growth --------------------------------
  LLABEL="com.compabob.dictation-learn"
  LPLIST="$GEN_DIR/$LLABEL.plist"
  cat > "$LPLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LLABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$LEARN</string>
  </array>
  <key>WorkingDirectory</key><string>$PROJECT_DIR</string>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>5</integer><key>Minute</key><integer>30</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$LOG_DIR/learn.out</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/learn.err</string>
</dict>
</plist>
EOF
  echo "  generated $LPLIST"
  echo
  echo "To activate the cleanup proxy (starts now + on every login):"
  echo "  cp \"$PPLIST\" ~/Library/LaunchAgents/"
  echo "  launchctl load ~/Library/LaunchAgents/$PLABEL.plist"
  echo
  echo "To activate the nightly learning loop (05:30 daily):"
  echo "  cp \"$LPLIST\" ~/Library/LaunchAgents/"
  echo "  launchctl load ~/Library/LaunchAgents/$LLABEL.plist"
  echo
  echo "To stop either later:"
  echo "  launchctl unload ~/Library/LaunchAgents/<label>.plist && rm ~/Library/LaunchAgents/<label>.plist"

elif [ "$OS" = "Linux" ]; then
  CRON_FILE="$GEN_DIR/crontab.txt"
  cat > "$CRON_FILE" <<EOF
# Compabob dictation. Grows the glossary nightly at 05:30.
30 5 * * *  cd "$PROJECT_DIR" && $PY "$LEARN" >> "$LOG_DIR/learn.log" 2>&1
EOF
  echo "  generated $CRON_FILE"
  echo
  echo "Run the cleanup proxy as a background service, e.g.:"
  echo "  nohup $PY \"$PROXY\" >> \"$LOG_DIR/proxy.log\" 2>&1 &"
  echo "  (or wrap it in a systemd user unit for restart-on-boot)"
  echo
  echo "To activate the nightly learning loop, add the generated line to crontab:"
  echo "  crontab -e        # then paste the contents of $CRON_FILE"

else
  echo "Unsupported OS for automatic scheduling: $OS"
  echo "Run the module by hand:  python3 modules/dictation/proxy.py"
  exit 1
fi

echo
echo "After activating, set  dictation: true  in config/user.config.yaml."
