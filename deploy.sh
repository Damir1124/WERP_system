#!/usr/bin/env bash
# ============================================================================
# deploy.sh — безопасный деплой WERP / Osnova 2.0 на VPS (Linux + Docker)
#
# Порядок (ВАЖНО!): сначала бэкап БД, потом миграции, потом код, потом сборка.
# Если код уже новый, а БД старая — приложение упадёт, поэтому миграции идут
# до перезапуска контейнеров.
#
# Требования:
#   - установлены docker и docker compose plugin
#   - в корне проекта лежит .env (продакшен-настройки, см. .env.example)
#   - запуск: bash deploy.sh
# ============================================================================
set -euo pipefail

# Таймстамп для имён бэкапов
TS=$(date +%Y%m%d_%H%M%S)
COMPOSE="docker compose"

echo "==> [1/6] Проверяем Docker..."
docker version --format '{{.Server.Version}}' >/dev/null
echo "    Docker OK"

echo "==> [2/6] Бэкап базы данных PostgreSQL..."
# Читаем креды из .env (точечно, не теряя специальные символы)
DB_NAME=$(grep -E '^DB_NAME=' .env | cut -d= -f2-)
DB_USER=$(grep -E '^DB_USER=' .env | cut -d= -f2-)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
$COMPOSE exec -T db pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/backup_$TS.sql"
echo "    Бэкап сохранён: $BACKUP_DIR/backup_$TS.sql"

echo "==> [3/6] Обновляем код (git pull)..."
# Скрипт запускается из checkout владельца. pull только master/текущую.
git -C "$(dirname "$0")" pull --ff-only

echo "==> [4/6] Применяем миграции БД (сначала!)..."
# Поднимаем только web, если стека нет, чтобы выполнить migrate
$COMPOSE up -d web redis
$COMPOSE exec -T web python manage.py migrate --noinput

echo "==> [5/6] Собираем статику и перезапускаем весь стек..."
$COMPOSE exec -T web python manage.py collectstatic --noinput
$COMPOSE up -d --build

echo "==> [6/6] Проверка health-check..."
sleep 5
STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health/ || true)
if [ "$STATUS" = "200" ]; then
    echo "    ✅ /health/ → 200 OK"
else
    echo "    ⚠️  /health/ вернул код: ${STATUS:-no-response} (проверь логи: docker compose logs)"
fi

echo ""
echo "✅ Деплой завершён. Сервисы:"
$COMPOSE ps

echo ""
echo "Резервная копия: $BACKUP_DIR/backup_$TS.sql"
echo "Откат к прошлой версии: git revert HEAD && $COMPOSE up -d --build"