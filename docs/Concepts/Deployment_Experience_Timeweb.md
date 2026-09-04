# Опыт деплоя WERP на Timeweb (выжимка) — что сработало, что нет

> Краткий конспект реального опыта развёртывания проекта на VPS Timeweb Cloud.
> Цель — не повторить ошибок и быстро вспомнить, как всё устроено.

---

## 1. Стек и окружение

- **VPS Timeweb Cloud**, 3.8 ГБ ОЗУ (по факту доступно ~2.6 ГБ), 1 внешний IPv4 `186.246.8.100`.
- ОС: Ubuntu (Debian-семейство), доступ через **веб-консоль** в панели (SSH через ПК работал нестабильно — порт 22).
- Домен `24ecolife.ru` -> DNS на NS Timeweb (`ns1/ns2.timeweb.ru`), A-записи на `186.246.8.100`.
- Стек: Docker Compose (Postgres, Redis, Django/gunicorn, Uvicorn-ASGI, Celery worker/beat, bot, nginx).

## 2. Деплой

- Код на GitHub (ветка `feature/deploy`), публичный репозиторий (нужнo для `raw`-доступа к `deploy-bootstrap.sh`).
- Авто-деплой: `deploy-bootstrap.sh` (скачивал по raw; нельзя `<(curl)` — только `curl -o` + `bash`).
- Первый запуск: `docker compose up -d --build`. Из-за Docker Hub `429` приходилось повторять; добавили в Dockerfiles `build-essential/gcc` (psycopg2 компилируется), убрали конфликт версий redis (только `requirements.txt`).

## 3. SSH / сеть

- **Порт 22 (SSH)** снаружи долго был закрыт — помогло добавление правила firewall в панели Timeweb (TCP 22/80/443 для всех адресов) **+ перезагрузка сервера** (правила реально применились после reboot).
- Если с ПК `ssh` не идёт — заходить через **веб-консоль** в панели (работает всегда).
- С некоторых регионов/сетей до сервера бывает нестабильный маршрут (то открывается, то нет) — это сеть, не код.

## 4. SSL (Let's Encrypt) — главный геморрой

### Что НЕ сработало (возились долго)
- **HTTP-он challenge** (через порт 80): падал, пока порт 80 был закрыт; потом «secondary validation timeout» (нестабильность сети до IP).
- **DNS-01** (через TXT-записи): спотыкался о:
  - Публикацию TXT у Timeweb не мгновенно (Let's Encrypt не успевал увидеть свежий токен).
  - Технические мелочи: в контейнере certbot нет `dig`/`curl`/`bash` (только `sh`).

### Что СРАБОТАЛО (итог)
- Выдать через **webroot на порту 80**, когда порт 80 стал открыт:
  ```bash
  docker run --rm \
    -v "$PWD/certbot_conf:/etc/letsencrypt" \
    -v "$PWD/certbot_www:/var/www/certbot" \
    certbot/certbot certonly --webroot -w /var/www/certbot \
    -d 24ecolife.ru --agree-tos --email admin@24ecolife.ru --no-eff-email --non-interactive
  ```
- Сертификат fall под `live/24ecolife.ru-0001/` (с `-0001`, т.к. была старая self-signed папка).
- **nginx.conf** должен указывать на **стабильный путь** `live/24ecolife.ru/` (без `-0001`), а скрипт `renew-cert.sh` после продления копирует туда свежий набор.

### Автопродление
- `renew-cert.sh` (cron nightly 03:22 + @reboot): запускает `certbot renew --quiet`, затем копирует `fullchain.pem`/`privkey.pem` из свежайшего lineage (`live/24ecolife.ru-0001/...`) в `live/24ecolife.ru/` и перезапускает nginx.
- Проверка: `certbot renew --dry-run` -> «all simulated renewals succeeded» (по рабочему конфигу `24ecolife.ru-0001.conf`).
- Удалить битый старый `renewal/24ecolife.ru.conf` (parse-failure), оставить рабочий `-0001.conf`.

### Грабли, которые запомнить
- Certbot создаёт папку с суффиксом (`-0001`, `-0002`) — nginx смотреть на это нельзя; держать **стабильный путь** `live/24ecolife.ru/`, обновляемый скриптом.
- Пока в `_acme-challenge` живут старые TXT — Let's Encrypt видит старое значение -> "Incorrect TXT". Очищать DNS-записи перед повтором.
- Rate-limit Let's Encrypt: ~5 неудачных попыток/час на домен. Не спамить.

## 5. Бот (Telegram) — НЕ РАБОТАЕТ с этого VPS

- **Симптом:** бот не отвечает, в логах `TelegramNetworkError: Request timeout error` при `set_webhook`.
- **Причина:** с этого VPS **не проходит TCP-доступ до `api.telegram.org`** (проверка: `timeout 10 bash -c 'cat </dev/null >/dev/tcp/api.telegram.org/443'` -> FAIL; `curl https://api.telegram.org/` -> 000). Хоть DNS резолвится (149.154.166.110), соединение блокируется.
- Это **региональная/сетевая блокировка дата-центра**, не код. В РФ `api.telegram.org` у пользователей мессенджера может работать по другим каналам, но у VPS-провайдера TCP к api.telegram.org закрыт.
- **Важно:** у бота был баг **двойного пути webhook** `/webhook/webhook` — исправить `tg_bot/__main__.py` (`url=WEBHOOK_URL`, т.к. путь уже в config). Но даже после исправления бот упёрся в сеть до api.telegram.org.

### Как решить бот (варианты)
1. **Прокси для aiogram** (`BOT_PROXY_URL`, SOCKS5/HTTP) на сервер с доступом к TG.
2. **Отдельный VPS в регионе с открытым api.telegram.org** (не РФ/СНГ).
3. Запускать бота на машине с доступом к TG (локальный ngrok и т.п.), а Django — на VPS.

## 6. Что итожна работает / НЕ работает

| Компонент | Статус |
|---|---|
| Django-сайт, админка, API | ✅ работает, настоящий SSL |
| Nginx, статика, WebSocket (ASGI) | ✅ |
| Celery worker/beat | ✅ (запущены) |
| Автопродление SSL | ✅ настроено (cron + renew-cert.sh) |
| Telegram-бот | ❌ блокировка сети до api.telegram.org |

## 7. Полезные проверки

```bash
# Доступ к api.telegram.org
curl -s -m 15 -o /dev/null -w "TG:%{http_code}\n" https://api.telegram.org/
timeout 10 bash -c 'cat</dev/null >/dev/tcp/api.telegram.org/443' && echo OK || echo FAIL

# Порт/слушатели
sudo ss -tlnp | grep -E ':80|:443'
sudo ufw status verbose
sudo iptables -L INPUT -n | head

# Память (OOM-убийства воркеров)
free -h
docker compose logs web --tail 20

# Сертификат
docker run --rm -v "$PWD/certbot_conf:/etc/letsencrypt" certbot/certbot certificates
```

---

## Вывод одной строкой (по итогу)
Сайт/деплой/SSL/автопродление — настроены и работают. **Бот заработал после переезда на VPS в Амстердаме** (где открыт `api.telegram.org`). Итоговый вариант см. ниже.

---

## ФИНАЛ: переезд на Амстердам (что решило проблему бота)

### Предыстория
На Timeweb (РФ/близкая сеть) `api.telegram.org` был **заблокирован** (TCP 443 FAIL), поэтому бот не мог подключиться. Бесплатные прокси нестабильны. Решение — сменить регион сервера.

### Как переехали (быстро, из снимка)
1. **Нидерланды (Амстердам)** — VPS с доступом к api.telegram.org (проверка: `timeout 10 bash -c 'cat</dev/null >/dev/tcp/api.telegram.org/443'` → `TG OK`).
2. **Создали новый VPS из снимка** старого Timeweb — приехали: Docker, .env, nginx, certbot (SSL), код.
3. Перевел **DNS** домена `24ecolife.ru` (A-записи @ и www) на новый IPv4 `201.51.10.172`.

### Грабли при переезде (важно!)
- **nginx не поднимался** (`YOUR_DOMAIN` в nginx.conf). Причина: в репо nginx.conf хранит плейсхолдер `YOUR_DOMAIN`, а `sed`-подстановка была только на старом сервере. Фикс: `sed -i 's|YOUR_DOMAIN|24ecolife.ru|g' nginx.conf` → `docker compose restart nginx`.
- **Webhook бота был двойным `/webhook/webhook`** — исправили в коде (`tg_bot/__main__.py`: `url=WEBHOOK_URL`, а не `+ WEBHOOK_PATH`). Отметка: лог-строка 68 ещё печатает `/webhook/webhook`, но реальный webhook правильный.
- После перевода DNS: `getWebhookInfo` показал `ip_address: 201.51.10.172` → Telegram шлёт апдейты на новый сервер.

### Ключевые проверки после переезда
- `timeout 10 bash -c 'cat</dev/null >/dev/tcp/api.telegram.org/443'` → `TG OK` (регион подходит).
- `curl -s https://api.telegram.org/bot<TOK>/getWebhookInfo` → `"url": "https://24ecolife.ru/webhook"`, `"ip_address": "201.51.10.172"`, без `last_error_message`.
- `docker compose ps` — все контейнеры Up (web, nginx, db, redis, celery, bot).

### Итоговый статус (работает)
| Компонент | Статус |
|---|---|
| Сайт / админка / API | ✅ (настоящий SSL) |
| Корневая страница Eco Life | ✅ |
| SSL + автопродление (cron) | ✅ |
| WebSocket / Dashboard | ✅ |
| Telegram-бот | ✅ (прямой доступ, Амстердам) |
| Celery | ✅ |

### Чего не делать / запомнить
- **Не** использовать VPS в РФ/близких сетях для бота (TocketteTG заблокирован).
- **Не** хранить `YOUR_DOMAIN` в nginx.conf без подстановки на сервере.
- **Не** светить BOT_TOKEN в чатах/логах — отзывай у @BotFather при утечке.
- Регион выбирать с открытым api.telegram.org (Нидерланды/Германия/Финляндия) — проверка `timeout ... tcp api.telegram.org/443`.