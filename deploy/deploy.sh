#!/usr/bin/env bash
# روی سرور اجرا می‌شود (توسط GitHub Actions از طریق SSH).
# استفاده:  deploy.sh <tag>      مثال: deploy.sh 3f2a9c1
#
# پیش‌نیاز: داخل $DEPLOY_PATH این فایل‌ها آپلود شده‌اند:
#   incoming/image.tar.gz   ایمیج Docker (pharmacy-web:<tag>)
#   incoming/docker-compose.prod.yml
# و فایل .env (ساخته‌شده توسط setup-server.sh) کنار آن‌هاست.
set -euo pipefail

TAG="${1:?usage: deploy.sh <tag>}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/pharmacy}"
cd "$DEPLOY_PATH"

[ -f .env ] || { echo "❌ فایل $DEPLOY_PATH/.env وجود ندارد"; exit 1; }

# ---- نام پروژه‌ی compose: باید با پروژه‌ی قبلی یکی باشد تا دیتابیس/مدیا از بین نرود ----
if [ -z "${COMPOSE_PROJECT_NAME:-}" ]; then
  if [ -f .compose_project ]; then
    COMPOSE_PROJECT_NAME="$(cat .compose_project)"
  else
    mapfile -t vols < <(docker volume ls -q | grep -E '_postgres_data$' || true)
    if [ "${#vols[@]}" -eq 1 ]; then
      COMPOSE_PROJECT_NAME="${vols[0]%_postgres_data}"
    elif [ "${#vols[@]}" -gt 1 ]; then
      echo "❌ چند volume دیتابیس پیدا شد: ${vols[*]}"
      echo "   نام پروژه را دستی در $DEPLOY_PATH/.compose_project بنویسید (مثلا farmacy_customer_club) و دوباره اجرا کنید."
      exit 1
    else
      COMPOSE_PROJECT_NAME="farmacy_customer_club"
    fi
    echo "$COMPOSE_PROJECT_NAME" > .compose_project
  fi
fi
export COMPOSE_PROJECT_NAME
echo "▶ compose project: $COMPOSE_PROJECT_NAME"

# ---- فایل‌های جدید ----
mkdir -p nginx
cp incoming/docker-compose.prod.yml docker-compose.yml
# nginx/nginx.conf عمدا کپی نمی‌شود: تنظیمات SSL روی خود سرور نگهداری می‌شود
[ -f nginx/nginx.conf ] || { echo "❌ فایل $DEPLOY_PATH/nginx/nginx.conf وجود ندارد"; exit 1; }

# ---- لود ایمیج ----
echo "▶ loading image pharmacy-web:$TAG"
gunzip -c incoming/image.tar.gz | docker load

PREV_TAG=""
[ -f .current_tag ] && PREV_TAG="$(cat .current_tag)"

# ---- بالا آوردن ----
export WEB_TAG="$TAG"
echo "▶ docker compose up"
docker compose up -d --remove-orphans
# nginx آدرس کانتینر web را هنگام استارت resolve می‌کند؛ بعد از ساخت مجدد web باید ری‌استارت شود
docker compose restart nginx

# ---- بررسی سلامت ----
HOST_HEADER="$(grep -E '^ALLOWED_HOSTS=' .env | head -1 | cut -d= -f2- | cut -d, -f1 | tr -d '\r"' || true)"
if [ -z "$HOST_HEADER" ] || [ "$HOST_HEADER" = "*" ]; then HOST_HEADER="localhost"; fi

echo "▶ health check (Host: $HOST_HEADER)"
ok=0
for i in $(seq 1 40); do
  code="$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $HOST_HEADER" https://127.0.0.1/login/ || true)"
  if [ "$code" != "200" ]; then
    code="$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $HOST_HEADER" http://127.0.0.1/login/ || true)"
  fi
  if [ "$code" = "200" ]; then ok=1; break; fi
  sleep 3
done

if [ "$ok" -ne 1 ]; then
  echo "❌ سلامت‌سنجی ناموفق (آخرین کد HTTP: ${code:-none})"
  docker compose logs --tail=60 web || true
  if [ -n "$PREV_TAG" ] && docker image inspect "pharmacy-web:$PREV_TAG" >/dev/null 2>&1; then
    echo "↩ برگشت به نسخه‌ی قبلی: $PREV_TAG"
    WEB_TAG="$PREV_TAG" docker compose up -d --remove-orphans
    docker compose restart nginx
  fi
  exit 1
fi

echo "$TAG" > .current_tag
echo "✅ deploy OK: $TAG"

# ---- پاکسازی: ۳ ایمیج آخر نگه داشته می‌شود ----
docker images pharmacy-web --format '{{.Tag}}' | tail -n +4 | xargs -r -I{} docker rmi "pharmacy-web:{}" || true
docker image prune -f >/dev/null || true
rm -f incoming/image.tar.gz
