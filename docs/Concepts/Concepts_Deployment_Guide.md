# Деплой WERP / Osnova 2.0 на VPS (Linux + Docker)

Актуальное руководство по развёртыванию на сервере. Дополняет
[`Concepts_Deployment.md`](Concepts_Deployment.md) обновлённой схемой стека.

---

## 0. Полный путь для новичка (от нуля до работающего сайта)

Если ты не делал деплой раньше — следуй этому пути. Каждый шаг объяснён.

### 0.1 Арендуй VPS-сервер
VPS — это арендованный удалённый компьютер (Linux), который работает 24/7
в дата-центре. Провайдеры: DigitalOcean, Timeweb Cloud, Hetzner, Vultr.
- **Минимум для этого проекта:** 2 ГБ RAM, 2 CPU, 40 ГБ диска, Ubuntu 22.04/24.04.
- После аренды тебе дадут: **IP-адрес** сервера, **root-пароль** (или SSH-ключ).

### 0.2 Купи домен
Домен — это адрес сайта (например `werp.uz`). Регистраторы: Namecheap,
GoDaddy, reg.ru. Цена обычно 10–30$/год (`.uz` может быть дороже/особый порядок).
- Для Telegram-ботов/Mini App **обязателен** свой домен + HTTPS (tg иначе не откроет).

### 0.3 Направь DNS на сервер (важно!)
У провайдера домена создай DNS-записи **A-записи**, указывающие на IP твоего VPS:
```
@       A   <IP_твоего_сервера>
www     A   <IP_твоего_сервера>
```
Используй «DigitalOcean DNS» или любой DNS-хостинг. Записи распространяются
10–60 минут. Без этого SSL не выдастся.

### 0.4 Подключись по SSH
На ПК (Windows) открой терминал (PowerShell) и зайди на сервер:
```bash
ssh root@<IP_сервера>
```
Введи пароль, когда попросят.

### 0.5 Запусти автобootstrap
На сервере введи одну команду — скрипт сделает почти всё сам:
```bash
bash <(curl -s https://raw.githubusercontent.com/Damir1124/WERP_system/feature/deploy/deploy-bootstrap.sh)
```
Скрипт спросит: домен, BOT_TOKEN, пароль БД, твой Telegram ID — и затем:
установит Docker, клонирует проект, создаст `.env`, выдаст SSL (Let's Encrypt),
соберёт стек, применит миграции, соберёт статику. Всё автоматически.

### 0.6 Проверь и создай админку
После бootsattrp скрипт покажет статус и подскажет создать суперпользователя:
```bash
cd ~/WERP_system
docker compose exec web python manage.py createsuperuser
```

### 0.7 Готово
- Админка: `https://твой-домен/admin/`
- Health-check: `https://твой-домен/health/`
- Telegram-бот сам установит webhook на `https://твой-домен/webhook`.

Если на каком-то шаге что-то пошло не так — открой раздел «Устранение
неполадок» ниже или пингуй меня.

---

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

## Автобootstrap с нуля (рекомендуется)

Для полного новичка есть скрипт `deploy-bootstrap.sh`, который делает весь
деплой автоматически на чистом VPS: установка Docker → клонирование →
`.env` → SSL (Let's Encrypt или временный self-signed) → сборка стека →
миграции → статика.

Запуск на сервере (после настройки DNS на сервер):
```bash
bash <(curl -s https://raw.githubusercontent.com/Damir1124/WERP_system/feature/deploy/deploy-bootstrap.sh)
```
Или локально, если код уже склонирован:
```bash
cd WERP_system && bash deploy-bootstrap.sh
```

Скрипт спросит: домен, BOT_TOKEN, пароль БД, твой Telegram ID. Остальное —
сам. Если SSL ещё нельзя выдать (DNS не дожился), скрипт поставит временный
self-signed сертификат, чтобы стек заработал; позже повтори `bash deploy.sh`
после обновления DNS.

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