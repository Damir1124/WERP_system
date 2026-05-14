# Концепция: Telegram Bot (aiogram 3.x) в WERP

**Область применения:** `tg_bot/`, `bot_bridge`, `workers`  
**Связанные задачи:** P3 (Telegram Mini App с тремя ролевыми профилями)

## Зачем это нужно в нашем проекте

Telegram-бот в WERP служит **универсальным интерфейсом** для трёх типов пользователей:

1. **Курьер** — получает список заказов, подтверждает доставку, изменяет количество на месте.
2. **Клиент** — просматривает каталог, делает заказ, отслеживает статус доставки.
3. **Администратор** — видит сводную статистику, управляет пользователями, отправляет уведомления.

Бот заменяет отдельное мобильное приложение — всё работает внутри Telegram, что снижает порог входа для курьеров и клиентов.

## Как это работает (с нуля)

### Архитектура aiogram 3.x

Aiogram — асинхронный фреймворк для Telegram Bot API. В WERP мы используем **модульную архитектуру**:

```
tg_bot/
├── __main__.py          # Точка входа (polling/webhook)
├── config.py            # Переменные окружения (BOT_TOKEN, DJANGO_API_URL)
├── bot.py               # Инициализация Bot и Dispatcher
├── middlewares/
│   └── auth.py          # AuthMiddleware — идентификация пользователя
├── routers/
│   ├── courier.py       # Команды для курьера
│   ├── client.py        # Команды для клиента
│   └── admin.py         # Команды для администратора
└── keyboards/
    ├── courier.py       # Reply‑ и inline‑клавиатуры
    ├── client.py
    └── admin.py
```

### Поток запроса

1. **Пользователь отправляет сообщение** → Telegram сервер передаёт его боту.
2. **Aiogram Dispatcher** получает update, передаёт его через цепочку middleware.
3. **AuthMiddleware** извлекает `tg_id` из `message.from.id` и отправляет запрос к Django API (`/api/bot/identify/`).
4. **Django возвращает роль** (`courier`/`client`/`admin`) и данные пользователя.
5. **Middleware добавляет `request.state.user`** с полями `role`, `name`, `id`, `worker_type`.
6. **Dispatcher выбирает подходящий router** на основе `state.user.role`.
7. **Обработчик команды** выполняет бизнес‑логику (запрос к API Django) и отправляет ответ.

### Ролевая авторизация

Вместо единого потока команд мы разделили бота на **три независимых роутера**. Это даёт два преимущества:

- **Изоляция кода** — команды курьера не смешиваются с командами клиента.
- **Безопасность** — пользователь не может вызвать команду чужой роли (роутер просто не зарегистрирован для него).

**Как это реализовано:**

```python
# tg_bot/middlewares/auth.py
async def __call__(self, handler, event, data):
    tg_id = event.from_user.id
    user_info = await self.identify_user(tg_id)  # запрос к /api/bot/identify/
    data['user'] = user_info
    return await handler(event, data)

# tg_bot/bot.py
dp.update.middleware(AuthMiddleware())
dp.include_router(courier.router)   # только если user.role == 'courier'
dp.include_router(client.router)    # только если user.role == 'client'
dp.include_router(admin.router)     # только если user.role == 'admin'
```

### Связь с Django (API‑шлюз)

Бот **не обращается к БД напрямую** — все данные он получает через REST API Django (`bot_bridge`). Это обеспечивает:

- **Единую точку валидации** — бизнес‑логика остаётся в Django.
- **Кеширование и оптимизацию** — можно добавить Redis‑кеш на стороне Django.
- **Логирование** — все действия фиксируются в Django‑админке.

**Пример запроса из бота:**

```python
async with aiohttp.ClientSession() as session:
    async with session.get(
        f"{DJANGO_API_URL}/courier/deliveries/today/",
        headers={"X-Telegram-ID": str(tg_id)}
    ) as resp:
        deliveries = await resp.json()
```

## Ловушки и частые ошибки

### 1. Блокирующие вызовы в обработчиках

**Неправильно:**
```python
@router.message(Command("start"))
async def start(message: Message):
    deliveries = requests.get(...)  # синхронный запрос блокирует event loop
```

**Правильно:** Использовать `aiohttp` или `asyncio.to_thread` для синхронных операций.

### 2. Отсутствие обработки недоступности API

Если Django API не отвечает, бот должен показать пользователю понятное сообщение, а не падать.

**Решение:** Обернуть запросы в `try/except aiohttp.ClientError` и иметь fallback‑ответ.

### 3. Хранение состояния в памяти

`MemoryStorage` (по умолчанию) теряет состояние при перезапуске бота. Для продакшена нужно `RedisStorage`.

### 4. Невалидный `tg_id`

Если пользователь не найден в базе (`/api/bot/identify/` возвращает `role: "unknown"`), бот должен предложить ему связаться с администратором.

## В нашем коде

- **`tg_bot/middlewares/auth.py`** — `AuthMiddleware` с методом `identify_user`.
- **`apps/bot_bridge/views.py`** — `IdentifyView` (GET `/api/bot/identify/`).
- **`apps/workers/models.py`** — поля `tg_id` и `is_admin`.
- **`tg_bot/routers/`** — примеры команд для каждой роли.

## Схема взаимодействия

```
Telegram User
    │
    ▼
Telegram Server
    │
    ▼
Aiogram Bot (tg_bot/__main__.py)
    │
    ▼
AuthMiddleware → Django API (/api/bot/identify/)
    │
    ▼
Router (courier/client/admin)
    │
    ▼
Handler → Django API (остальные endpoints)
    │
    ▼
Response → User
```

## Связанные концепции

- [[Concepts_TelegramBotAuth|Авторизация Telegram бота через tg_id]] — как работает endpoint идентификации.
- [[Modules_BotBridge|Модуль Bot Bridge]] — полное описание API‑шлюза.
- [[Concepts_WebSockets|WebSockets]] — для live‑уведомлений (следующий этап P3).