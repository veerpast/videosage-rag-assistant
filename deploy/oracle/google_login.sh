#!/usr/bin/env bash
set -euo pipefail

if systemctl is-active --quiet videosage-worker; then
    echo "Stop the worker first: sudo systemctl stop videosage-worker"
    exit 1
fi

DISPLAY_NUMBER=:100
RUNTIME_DIR=/tmp/videosage-google-login
mkdir -p "$RUNTIME_DIR"
chmod 0700 "$RUNTIME_DIR"

cleanup() {
    jobs -pr | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

Xvfb "$DISPLAY_NUMBER" -screen 0 1280x720x24 -nolisten tcp &
sleep 1
x11vnc -display "$DISPLAY_NUMBER" -localhost -nopw -forever -shared \
    -rfbport 5901 -quiet &
/usr/share/novnc/utils/novnc_proxy \
    --listen localhost:6080 --vnc localhost:5901 &

echo "Open http://127.0.0.1:6080/vnc.html through an SSH local tunnel."
echo "Sign in to the dedicated Google bot account, then press Ctrl+C here."

DISPLAY="$DISPLAY_NUMBER" XDG_RUNTIME_DIR="$RUNTIME_DIR" \
    /opt/videosage/.venv/bin/python \
    /opt/videosage/deploy/oracle/google_login.py
