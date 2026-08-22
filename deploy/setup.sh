#!/usr/bin/env bash
set -euo pipefail

# Prostudio v1 — Oracle Cloud (A1.Flex ARM, Ubuntu 22.04) one-shot setup.
# Usage:  sudo bash setup.sh <PUBLIC_IP>
# Example: sudo bash setup.sh 129.151.100.12

PUBLIC_IP="${1:?usage: sudo bash setup.sh <PUBLIC_IP>}"
APP_DIR="/opt/prostudio-v1"
REPO="https://github.com/ajayspi/Prostudio-v1.git"

echo "==> Installing system packages (ffmpeg, python, nginx, node)…"
apt-get update -y
apt-get install -y ffmpeg python3 python3-venv python3-pip git curl

# Node.js 22 (LTS)
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | tr -d 'v' | cut -d. -f1)" -lt 22 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

echo "==> Cloning repo…"
rm -rf "$APP_DIR"
git clone "$REPO" "$APP_DIR"

echo "==> Backend: venv + deps…"
python3 -m venv "$APP_DIR/backend/.venv"
"$APP_DIR/backend/.venv/bin/pip" install --upgrade pip
"$APP_DIR/backend/.venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

echo "==> Frontend: install + production build (baking in backend URL)…"
cd "$APP_DIR/frontend"
npm ci
NEXT_PUBLIC_API_URL="http://${PUBLIC_IP}:8000" npm run build

echo "==> Installing systemd services…"
cp "$APP_DIR/deploy/prostudio-v1-backend.service"  /etc/systemd/system/
cp "$APP_DIR/deploy/prostudio-v1-frontend.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now prostudio-v1-backend
systemctl enable --now prostudio-v1-frontend

echo ""
echo "=============================================================="
echo " Done. Services:"
echo "   backend  -> http://${PUBLIC_IP}:8000/api/health"
echo "   frontend -> http://${PUBLIC_IP}:3000"
echo ""
echo " Check status:  systemctl status prostudio-v1-backend prostudio-v1-frontend"
echo " Logs:          journalctl -u prostudio-v1-backend -f"
echo "=============================================================="
