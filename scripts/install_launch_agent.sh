#!/bin/sh
# Install DataVeil as a per-user macOS service (no sudo; loopback only).
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python_bin="$project_dir/venv/bin/python"
plist_path="$HOME/Library/LaunchAgents/local.dataveil.gateway.plist"
log_dir="$HOME/Library/Logs/DataVeil"
uid=$(id -u)

if [ ! -x "$python_bin" ]; then
  echo "Missing virtual environment: $python_bin" >&2
  exit 1
fi

mkdir -p "$(dirname "$plist_path")" "$log_dir"
cat > "$plist_path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>local.dataveil.gateway</string>
  <key>ProgramArguments</key>
  <array>
    <string>$python_bin</string><string>-m</string><string>dv</string><string>start</string>
    <string>--host</string><string>127.0.0.1</string><string>--port</string><string>8787</string>
    <string>--profile</string><string>work</string>
  </array>
  <key>WorkingDirectory</key><string>$project_dir</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$log_dir/gateway.out.log</string>
  <key>StandardErrorPath</key><string>$log_dir/gateway.err.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$uid/local.dataveil.gateway" 2>/dev/null || true
launchctl bootstrap "gui/$uid" "$plist_path"
launchctl kickstart -k "gui/$uid/local.dataveil.gateway"
echo "Installed and started DataVeil gateway service."
