# Деплой WERP / Osnova 2.0 на VPS (Linux + Docker)

Актуальное руководство по развёртыванию на сервере. Дополняет
[`Concepts_Deployment.md`](Concepts_Deployment.md) обновлённой схемой стека.

## Стек (docker compose)

| Сервис      | Что делает                              | Внутр. порт |
|-------------|-----------------------------------------|-------------|
| `db`        | PostgreSQL 17                           | 5432        |
| `redis`     | Redis 7 (кэш, Channels, Celery, FSM)    | 6379        |
| `web`       | Gunicorn (WSGI) — HTTP API/админ        | 8000        |
| `web-asgi`  | Uvicorn (ASGI) — WebSockets Dashboard   | 8001        |
| `celery-worker` | фоновые задачи Celery               | —           |
| `celery-beat`   | расписание Celery Beat               | —           |
| `bot`       | Telegram-бот (aiogram, webhook)         | 8001        |
| `nginx`     | входная дверь: SSL + статика + прокси   | 80/443      |

Один `Dockerfile` (web/worker/beat/asgi), отдельный `Dockerfile.bot` (бота).

## Предварительно на сервере

```bash
# Docker + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # затем re-login

# Код
git clone https://github.com/Damir1124/WERP_system.git
cd WERP_system
cp .env.example .env              # заполнить реальные значения
```

## `.env` для продакшена

Заполнить обязательно:
- `DJANGO_SECRET_KEY` (новый, см. `.env.example`)
- `ALLOWED_HOSTS=werp.uz,www.werp.uz` — реальный домен
- `CORS_ALLOWED_ORIGINS=https://werp.uz`
- `DB_PASSWORD`
- `BOT_TOKEN` (от @BotFather)
- `USE_WEBHOOK=true`, `WEBHOOK_HOST=https://werp.uz`
- `ADMIN_IDS` (свой Telegram ID)

## Первый запуск стека

```bash
docker compose up -d --build
# Затем миграции + статика + суперпользователь
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py createsuperuser
```

## Получение SSL (Let's Encrypt) через certbot

Nginx-конфиг использует плейсхолдер `YOUR_DOMAIN`. Перед certbot замени его
на реальный домен в `nginx.conf` (или отредактируй через certbot). Telegram
**требует** HTTPS, поэтому сертификат обязателен.

```bash
# 1. certbot внутри сети Nginx монтирует /var/www/certbot (см. compose).
#    Проще всего выдать через сам Nginx. Сначала получим через --webroot:
docker run --rm -v "$PWD/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$PWD/certbot_conf:/etc/letsencrypt" \
  -v "$PWD/certbot_www:/var/www/certbot" \
  -p 80:80 certbot/certbot \
  certonly --webroot -w /var/www/certbot -d YOUR_DOMAIN

# 2. Или (проще) отредактировать nginx.conf: заменить YOUR_DOMAIN на домен,
#    а сертификаты оставить первыми. Затем выполнить на хосте:
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN    # домен из server_name

# 3. Автообновление
sudo certbot renew --dry-run
```

После выдачи сертификата пути `fullchain.pem`/`privkey.pem` в `nginx.conf`
уже совпадают с `/etc/letsencrypt/live/YOUR_DOMAIN/`. Перезапуск Nginx:
`docker compose restart nginx`.

## Webhook бота

При `USE_WEBHOOK=true` бот сам вызывает `set_webhook` со значением
`WEBHOOK_HOST + WEBHOOK_PATH` в `'.env'`. Nginx проксирует `/webhook` на
сервис `bot`. Убедись, что `WEBHOOK_HOST` указывает на твой домен.

## Регулярный деплой изменений

```bash
bash deploy.sh
```

Выполняет (см. скрипт): бэкап БД → `git pull --ff-only` → миграции →
`collectstatic` → пересборка → health-check `/health/`.

## Бэкапы БД

`deploy.sh` сохраняет `pg_dump` в `./backups/`. Для автоматизации добавь
задачу в crontab:

```cron
# ежедневно в 02:30
30 2 * * * cd /path/to/WERP_system && docker compose exec -T db pg_dump -U $DB_USER $DB_NAME > backups/auto_$(date +%F).sql
```

## Health-check

Обычный мониторинг дёргает `https://YOUR_DOMAIN/health/` (открыт, без
авторизации). Отвечает 200, когда БД и Redis доступны.

## Проверка перед деплоем

```bash
# Тесты (в образе — pytest-django есть; на хосте: pip install pytest-django)
pytest -q

# Нет ли неприменённых миграций
python manage.py makemigrations --check --dry-run

# Валидность compose
docker compose config
```