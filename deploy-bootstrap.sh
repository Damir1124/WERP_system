#!/usr/bin/env bash
# ============================================================================
# deploy-bootstrap.sh — деплой WERP с «нуля» на чистом VPS (Linux)
#
# Что делает автоматически:
#  1. Устанавливает Docker + Docker Compose plugin (если ещё нет)
#  2. Клонирует репозиторий проекта (если ещё нет)
#  3. Создаёт .env из .env.example, запрашивая у тебя домен и секреты
#     (DJANGO_SECRET_KEY генерируется автоматически)
#  4. Подставляет твой домен в nginx.conf
#  5. Получает SSL-сертификат (Let's Encrypt) через certbot
#  6. Собирает и запускает весь стек
#  7. Применяет миграции, собирает статику, создаёт суперпользователя
#  8. Показывает health-check
#
# Запуск (на VPS):
#   bash deploy-bootstrap.sh
#
# Требования: Ubuntu/Debian, пользователь с sudo, интернет.
# ============================================================================
set -euo pipefail

# ── Цветной вывод ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}!! ${NC} $*"; }
err()   { echo -e "${RED}XX ${NC} $*" >&2; }

REPO_URL="https://github.com/Damir1124/WERP_system.git"
APP_DIR="${APP_DIR:-$HOME/WERP_system}"

# ── 1. Проверка root / sudo ─────────────────────────────────────────────────
if [ "$(id -u)" = "0" ]; then
  SUDO=""
else
  SUDO="sudo"
fi
[ -n "$SUDO" ] || SUDO="sudo"

# ── 2. Установка Docker ─────────────────────────────────────────────────────
if command -v docker >/dev/null 2>&1; then
  info "Docker уже установлен: $(docker --version)"
else
  info "Устанавливаю Docker..."
  curl -fsSL https://get.docker.com | $SUDO sh
  $SUDO usermod -aG docker "$USER"
  info "Docker установлен."
fi
if ! docker compose version >/dev/null 2>&1; then
  $SUDO apt-get update -y >/dev/null
  $SUDO apt-get install -y docker-compose-plugin >/dev/null
  info "Compose plugin установлен."
fi

# ── 3. Клонирование кода ────────────────────────────────────────────────────
if [ -d "$APP_DIR/.git" ]; then
  info "Код уже есть: $APP_DIR"
  cd "$APP_DIR"
elif [ -d "$APP_DIR" ]; then
  cd "$APP_DIR"
else
  info "Клонирую репозиторий..."
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi
# Переключаемся на ветку с деплой-подготовкой (если не master)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "master" ] && git show-ref --verify --quiet refs/remotes/origin/feature/deploy; then
  info "Использую ветку feature/deploy (там лежит деплой-подготовка)."
  git fetch origin --quiet
  git checkout feature/deploy 2>/dev/null || git checkout -b feature/deploy origin/feature/deploy
fi

# ── 4. Запрос домена ────────────────────────────────────────────────────────
if [ -z "${DOMAIN:-}" ]; then
  echo ""
  read -rp "Введи твой домен (например werp.uz или app.example.com): " DOMAIN
fi
DOMAIN="${DOMAIN// /}"
if [ -z "$DOMAIN" ]; then
  err "Домен не указан — прерываю. Запусти снова и введи домен."
  exit 1
fi
info "Домен: $DOMAIN"

# ── 5. Создание .env ────────────────────────────────────────────────────────
if [ -f ".env" ]; then
  info ".env уже существует — оставляю как есть. Пересоздать: удали .env и запусти снова."
else
  info "Создаю .env из шаблона..."
  cp .env.example .env

  # Читаем настоящий BOT_TOKEN/DB_PASSWORD/ADMIN_IDS, если переданы
  BOT_TOKEN="${BOT_TOKEN:-}"
  DB_PASSWORD="${DB_PASSWORD:-}"
  ADMIN_IDS="${ADMIN_IDS:-}"
  if [ -z "$BOT_TOKEN" ]; then
    echo ""
    read -rp "Введи BOT_TOKEN (от @BotFather): " BOT_TOKEN
  fi
  if [ -z "$DB_PASSWORD" ]; then
    read -rp "Придумай пароль для базы данных (DB_PASSWORD): " DB_PASSWORD
  fi
  if [ -z "$ADMIN_IDS" ]; then
    read -rp "Свой Telegram ID (для ADMIN_IDS): " ADMIN_IDS
  fi

  # Генерируем секретный ключ Django (без символа $ — во избежание проблем compose)
  SECRET_KEY=$(head -c 50 /dev/urandom | base64 | tr -d '/+=' | head -c 50)
  SECRET_KEY="${SECRET_KEY//$/X}"   # удалить возможный $

  # Заполняем .env
  sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=${SECRET_KEY}|" .env
  sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}|" .env
  sed -i "s|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=https://${DOMAIN}|" .env
  sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${DB_PASSWORD}|" .env
  sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=${BOT_TOKEN}|" .env
  sed -i "s|^WEBHOOK_HOST=.*|WEBHOOK_HOST=https://${DOMAIN}|" .env
  sed -i "s|^MINI_APP_URL=.*|MINI_APP_URL=https://${DOMAIN}/static/miniapp|" .env
  sed -i "s|^ADMIN_IDS=.*|ADMIN_IDS=${ADMIN_IDS}|" .env

  # DOMAIN в webhook URL бота (после бота он сам set_webhook)
  info ".env создан и заполнен."
fi

# ── 6. Подставляем домен в nginx.conf ───────────────────────────────────────
if grep -q "YOUR_DOMAIN" nginx.conf; then
  info "Подставляю домен $DOMAIN в nginx.conf..."
  sed -i "s|YOUR_DOMAIN|${DOMAIN}|g" nginx.conf
else
  info "nginx.conf уже содержит реальный домен."
fi

# ── 7. SSL: сначала получаем сертификат (nginx пока не занят, порт 80 свободен)
# ─────────────────────────────────────────────────────────────────────────────
info "Готовлю SSL. Убедись, что DNS домена $DOMAIN указывает на IP этого сервера!"
mkdir -p certbot_www certbot_conf
SSL_OK=0
if ! docker run --rm \
  -v "$PWD/certbot_www:/var/www/certbot" \
  -v "$PWD/certbot_conf:/etc/letsencrypt" \
  -p 80:80 certbot/certbot \
  certonly --webroot -w /var/www/certbot -d "$DOMAIN" -d "www.$DOMAIN" \
  --agree-tos --email "admin@$DOMAIN" --no-eff-email --non-interactive; then
  warn "certbot (webroot) не смог выдать сертификат."
  warn "Попробую standalone на порту 80 (должен быть свободен)..."
  if docker run --rm \
    -v "$PWD/certbot_conf:/etc/letsencrypt" \
    -p 80:80 certbot/certbot \
    certonly --standalone -d "$DOMAIN" -d "www.$DOMAIN" \
    --agree-tos --email "admin@$DOMAIN" --no-eff-email --non-interactive; then
    SSL_OK=1
  else
    warn "Не удалось выдать сертификат (DNS может ещё не указывать на этот сервер)."
    warn "Сгенерирую ВРЕМЕННЫЙ self-signed сертификат, чтобы стек запустился."
    SSL_OK=0
  fi
else
  SSL_OK=1
fi

# ── 8. Если нет настоящего сертификата — создаём временный self-signed ─────
if [ "$SSL_OK" = "0" ]; then
  info "Создаю временный self-signed сертификат для первичного запуска..."
  # Генерируем self-signed на хосте в certbot_conf/live/<domain>/
  mkdir -p "certbot_conf/live/$DOMAIN"
  openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
    -keyout "certbot_conf/live/$DOMAIN/privkey.pem" \
    -out "certbot_conf/live/$DOMAIN/fullchain.pem" \
    -subj "/CN=$DOMAIN" >/dev/null 2>&1
fi

# Подставляем реальный путь сертификатов в nginx.conf
sed -i "s|/etc/letsencrypt/live/YOUR_DOMAIN/|/etc/letsencrypt/live/${DOMAIN}/|g" nginx.conf
info "Пути сертификатов в nginx.conf настроены на /etc/letsencrypt/live/${DOMAIN}/"

# ── 9. Запуск стека ─────────────────────────────────────────────────────────
info "Собираю и запускаю контейнеры (первый раз может занять несколько минут)..."
docker compose up -d --build

# ── 10. Миграции + статика + суперпользователь ───────────────────────────────
info "Применяю миграции БД..."
docker compose exec -T web python manage.py migrate --noinput
info "Собираю статику..."
docker compose exec -T web python manage.py collectstatic --noinput
echo ""
if ! docker compose exec -T web python -c "import django; django.setup(); from django.contrib.auth import get_user_model; U=get_user_model(); print('admin-exists') if U.objects.filter(is_superuser=True).exists() else print('no-admin')" 2>/dev/null | grep -q admin-exists; then
  warn "Создай суперпользователя админки:"
  echo "    docker compose exec web python manage.py createsuperuser"
fi

# ── 11. Итог ─────────────────────────────────────────────────────────────────
echo ""
info "Деплой выполнен. Сервисы:"
docker compose ps
echo ""
info "Проверка health:"
sleep 3
curl -s -o /dev/null -w "https://${DOMAIN}/health/ → HTTP %{http_code}\n" "https://${DOMAIN}/health/" || true
echo ""
echo "Админка: https://${DOMAIN}/admin/"
echo "Если certbot пока не выдал сертификат — повтори после настройки DNS: bash deploy.sh"
warn "ВАЖНО: запиши DB_PASSWORD и не теряй файл .env — в нём секреты."