#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/videosage}"

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

if ! pgrep -f "Xvfb ${DISPLAY}" >/dev/null; then
    Xvfb "$DISPLAY" -screen 0 1280x720x24 -nolisten tcp &
fi

if ! pulseaudio --check; then
    pulseaudio --start --exit-idle-time=-1
fi

if ! pactl list short sinks | awk '{print $2}' | grep -Fxq "${PULSE_SINK_NAME:-Virtual_Sink}"; then
    pactl load-module module-null-sink \
        sink_name="${PULSE_SINK_NAME:-Virtual_Sink}" \
        sink_properties=device.description=VideoSage_Virtual_Sink
fi

pactl set-default-sink "${PULSE_SINK_NAME:-Virtual_Sink}"

exec /opt/videosage/.venv/bin/uvicorn worker.api:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips=127.0.0.1
