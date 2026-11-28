#!/usr/bin/env bash
# یک‌بار روی سرور (با کاربر root) اجرا شود:
#
#   curl -fsSL ... | bash     (یا فایل را کپی کنید)  →  bash setup-server.sh "<کلید عمومی SSH برای CI>"
#
# متغیرهای اختیاری:
#   DEPLOY_PATH=/opt/pharmacy     مسیر استقرار
#   OLD_PROJECT_DIR=/path/to/old  مسیر پروژه‌ی فعلی روی سرور (برای کپی .env موجود)
set -euo pipefail

PUBKEY="${1:?usage: setup-server.sh \"<ssh public key>\"}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/pharmacy}"
DEPLOY_USER="deploy"

[ "$(id -u)" -eq 0 ] || { echo "باید با root اجرا شود"; exit 1; }

# ---- Docker ----
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "▶ نصب Docker و Compose"
  apt-get update -y
  apt-get install -y docker.io docker-compose-v2 curl || {
    echo "❌ نصب خودکار Docker ناموفق بود (ممکن است میرور پارس‌پک مشکل داشته باشد)."
    echo "   Docker و Docker Compose v2 را دستی نصب کنید و اسکریپت را دوباره اجرا کنید."
    exit 1
  }
  systemctl enable --now docker
fi
command -v curl >/dev/null 2>&1 || apt-get install -y curl

# ---- کاربر deploy ----
if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"

install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
AUTH="/home/$DEPLOY_USER/.ssh/authorized_keys"
touch "$AUTH"
grep -qxF "$PUBKEY" "$AUTH" || echo "$PUBKEY" >> "$AUTH"
chmod 600 "$AUTH"; chown "$DEPLOY_USER:$DEPLOY_USER" "$AUTH"

# ---- مسیر استقرار ----
install -d -m 750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$DEPLOY_PATH" "$DEPLOY_PATH/incoming" "$DEPLOY_PATH/nginx"

# ---- فایل .env ----
if [ ! -f "$DEPLOY_PATH/.env" ]; then
  if [ -n "${OLD_PROJECT_DIR:-}" ] && [ -f "$OLD_PROJECT_DIR/.env" ]; then
    cp "$OLD_PROJECT_DIR/.env" "$DEPLOY_PATH/.env"
    echo "▶ .env از $OLD_PROJECT_DIR کپی شد (حتما مقادیر پروداکشن را بررسی کنید)"
  else
    SECRET="$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 50)"
    cat > "$DEPLOY_PATH/.env" <<ENVEOF
SECRET_KEY=$SECRET
DEBUG=False
ALLOWED_HOSTS=193.138.77.13,localhost,127.0.0.1

POSTGRES_DB=pharmacy_club
POSTGRES_USER=pharmacy_user
POSTGRES_PASSWORD=CHANGE_ME
DB_HOST=db
DB_PORT=5432

REDIS_URL=redis://redis:6379/0

SITE_NAME=داروخانه باشگاه مشتریان
SITE_URL=http://193.138.77.13

# پیامک کاوه‌نگار
KAVENEGAR_API_KEY=
KAVENEGAR_TEMPLATE=verify
ENVEOF
    echo "⚠ .env جدید ساخته شد. اگر دیتابیس قبلی دارید رمز آن را در POSTGRES_PASSWORD بگذارید!"
  fi
  chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_PATH/.env"
  chmod 600 "$DEPLOY_PATH/.env"
fi

echo
echo "✅ آماده است."
echo "   کاربر SSH برای CI:  $DEPLOY_USER"
echo "   مسیر استقرار:       $DEPLOY_PATH"
echo "   فایل تنظیمات:       $DEPLOY_PATH/.env   ← مقادیر را بررسی/ویرایش کنید"
