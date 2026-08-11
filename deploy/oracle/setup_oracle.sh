#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run with sudo: sudo bash deploy/oracle/setup_oracle.sh <public-hostname>"
    exit 1
fi

PUBLIC_HOSTNAME="${1:-}"
if [[ -z "$PUBLIC_HOSTNAME" ]]; then
    echo "A DNS hostname pointing to this VM is required for free HTTPS."
    exit 1
fi
if [[ ! "$PUBLIC_HOSTNAME" =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "The hostname contains unsupported characters."
    exit 1
fi

APP_DIR=/opt/videosage
REPO_URL=https://github.com/veerpast/videosage-rag-assistant.git

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    caddy curl ffmpeg git iptables-persistent pulseaudio pulseaudio-utils \
    python3 python3-pip python3-venv xvfb

if [[ ! -d "$APP_DIR/.git" ]]; then
    git clone "$REPO_URL" "$APP_DIR"
else
    git -C "$APP_DIR" pull --ff-only origin main
fi

chown -R ubuntu:ubuntu "$APP_DIR"
sudo -u ubuntu python3 -m venv "$APP_DIR/.venv"
sudo -u ubuntu "$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
sudo -u ubuntu "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements-worker.txt"
"$APP_DIR/.venv/bin/python" -m playwright install-deps chromium
sudo -u ubuntu "$APP_DIR/.venv/bin/python" -m playwright install chromium

install -d -m 0750 -o root -g ubuntu /etc/videosage
if [[ ! -f /etc/videosage/worker.env ]]; then
    install -m 0640 -o root -g ubuntu \
        "$APP_DIR/deploy/oracle/worker.env.example" /etc/videosage/worker.env
fi

chmod 0755 "$APP_DIR/deploy/oracle/start_worker.sh"
install -m 0644 "$APP_DIR/deploy/oracle/videosage-worker.service" \
    /etc/systemd/system/videosage-worker.service

sed "s/worker\.example\.com/${PUBLIC_HOSTNAME}/" \
    "$APP_DIR/deploy/oracle/Caddyfile.example" >/etc/caddy/Caddyfile

loginctl enable-linger ubuntu
iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || \
    iptables -I INPUT -p tcp --dport 80 -j ACCEPT
iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || \
    iptables -I INPUT -p tcp --dport 443 -j ACCEPT
netfilter-persistent save

systemctl daemon-reload
systemctl enable caddy videosage-worker
systemctl restart caddy

echo "Edit /etc/videosage/worker.env, then run:"
echo "  sudo systemctl restart videosage-worker"
echo "  curl https://${PUBLIC_HOSTNAME}/health"
