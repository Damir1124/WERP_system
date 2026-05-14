# Концепция: Telegram Mini App (TWA) — фронтенд для бэкендера

## Зачем это нужно в нашем проекте

В WERP мы используем Telegram Mini App для трёх ролевых профилей:
- **Курьер** — управление сменами, рейсами, подтверждение доставок
- **Клиент** — просмотр каталога, оформление заказов, отслеживание статуса
- **Администратор** — мониторинг статистики, склада, активных смен

**Почему именно Mini App, а не просто бот?**
- Бот ограничен текстовыми командами и inline-кнопками
- Mini App — полноценный веб-интерфейс внутри Telegram с таблицами, формами, фильтрами
- Можно показывать сложные данные (пул заказов, счётчики рейса, историю)
- Пользовательский опыт как в нативном приложении

## Как это работает (с нуля)

### Что такое TWA (Telegram Web App)

TWA — это обычная веб-страница (HTML + JS + CSS), которая открывается **внутри Telegram** как модальное окно. Для пользователя это выглядит как нативное приложение.

**Схема работы:**
```
Пользователь нажимает кнопку в боте
        │
        └─► Telegram открывает URL (твоя веб-страница) внутри себя
                │
                └─► Страница читает window.Telegram.WebApp.initData
                        │  (содержит tg_id пользователя, подписанный Telegram)
                        └─► Страница делает fetch() к Django API
                                │  (передаёт initData в заголовке для авторизации)
                                └─► Django отвечает данными → страница их рендерит
```

### Жёсткое требование Telegram

URL Mini App **обязан** работать по HTTPS. На локальной разработке — использовать ngrok или Cloudflare Tunnel.

## Выбранный стек фронтенда (рекомендация для этого проекта)

| Компонент | Технология | Зачем |
|-----------|-----------|-------|
| Фреймворк | **React 18** (через Vite) | Компонентный подход, большое сообщество |
| Сборщик | **Vite** | Быстрая сборка, простая настройка, `npm run build` → статика |
| Стили | **Tailwind CSS** | Утилитарные классы, не надо писать CSS вручную |
| Telegram SDK | `@twa-dev/sdk` | TypeScript-обёртка над `window.Telegram.WebApp` |
| HTTP-клиент | `fetch` (встроенный) | Запросы к Django DRF API |
| Хостинг | **Статика через Django + Nginx** | Нет отдельного сервера, всё в одном месте |

## Структура фронтенд-проекта

```
frontend/
├── courier/          — Mini App для курьера
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx       — ReactDOM.createRoot(...)
│       ├── App.jsx        — роутинг между экранами
│       ├── tg.js          — инициализация Telegram.WebApp
│       ├── api.js         — fetch-функции к /api/bot/courier/...
│       └── pages/
│           ├── Pool.jsx       — пул заказов
│           ├── Trip.jsx       — активный рейс + счётчики
│           ├── OrderConfirm.jsx — подтверждение доставки
│           ├── Shifts.jsx     — история смен
│           └── Colleagues.jsx — коллеги онлайн
│
└── client/           — Mini App для клиента
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── tg.js
        ├── api.js
        └── pages/
            ├── Catalog.jsx     — каталог товаров
            ├── OrderForm.jsx   — оформление заказа
            └── MyOrders.jsx    — история заказов
```

## Как Django узнаёт кто делает запрос (авторизация TWA)

**Проблема:** Браузер внутри Telegram не знает логин/пароль Django.
**Решение:** Telegram подписывает данные пользователя (`initData`) своим секретным ключом. Django проверяет подпись.

### Реализованная валидация (2026-05-11)

Вместо отдельного permission‑класса мы добавили проверку подписи непосредственно в `IdentifyView` и вынесли логику в утилиты.

**Файл `apps/bot_bridge/utils.py`:**
```python
def verify_telegram_init_data(init_data: str) -> bool:
    """
    Проверяет подпись initData от Telegram Mini App.
    Алгоритм: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data:
        return False
    
    # Разбираем строку на параметры
    parsed = parse_qs(init_data, keep_blank_values=False)
    
    # Извлекаем hash
    hash_value = parsed.get('hash', [None])[0]
    if not hash_value:
        return False
    
    # Удаляем hash из параметров для вычисления HMAC
    del parsed['hash']
    
    # Сортируем ключи в алфавитном порядке
    sorted_params = sorted(parsed.items(), key=lambda x: x[0])
    
    # Формируем строку данных в формате "key=value" с разделителем "\n"
    data_check_string = '\n'.join(
        f"{key}={value[0]}" for key, value in sorted_params
    )
    
    # Секретный ключ: HMAC_SHA256(BOT_TOKEN, "WebAppData")
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        # Если BOT_TOKEN не установлен, пропускаем проверку (для разработки)
        return True
    
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()
    
    # Вычисляем HMAC_SHA256(secret_key, data_check_string)
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Сравниваем хеши
    return hmac.compare_digest(computed_hash, hash_value)
```

**Обновлённый `IdentifyView` (`apps/bot_bridge/views.py`):**
- Принимает заголовок `X-Telegram-Init-Data`.
- Вызывает `verify_telegram_init_data()`.
- При неверной подписи возвращает `401 Unauthorized`.
- При успехе извлекает `tg_id` из `initData` и ищет пользователя в базе.
- Сохраняет обратную совместимость с параметром `tg_id` (для бота).

**Почему мы не сделали отдельный permission?**
На текущем этапе достаточно проверять подпись только в `IdentifyView`, потому что все последующие запросы от фронтенда используют `tg_id`, извлечённый из проверенных данных. Однако для продакшена рекомендуется добавить `TelegramInitDataPermission` ко всем защищённым эндпоинтам.

### Настройка CORS

Чтобы браузер Telegram разрешил кросс‑доменные запросы, добавлен `django-cors-headers`:

```python
# settings.py
INSTALLED_APPS += ['corsheaders']
MIDDLEWARE.insert(1, 'corsheaders.middleware.CorsMiddleware')

CORS_ALLOWED_ORIGINS = [
    "https://monkhood-chaperone-stinger.ngrok-free.dev",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_HEADERS += ['X-Telegram-ID', 'X-Telegram-Init-Data']
```

> **Важно:** Без CORS браузер блокирует запросы от Mini App к API, и кнопки не работают.

## Ловушки и частые ошибки

1. **`localhost` не работает** — Telegram требует HTTPS и публичный домен. Решение: ngrok/Cloudflare Tunnel.
2. **`initData` может быть пустым** — если пользователь открыл страницу не через Telegram (прямая ссылка). Проверяй `if (window.Telegram?.WebApp)`.
3. **Сборка не попадает в статику Django** — проверь `vite.config.js`: `outDir` должен вести в `../../static/miniapp/courier/`.
4. **CORS ошибки** — Django должен разрешать запросы с домена Mini App. Добавь домен в `CORS_ALLOWED_ORIGINS`.
5. **Telegram WebApp SDK не инициализируется** — убедись что скрипт загружается до вызова `WebApp.ready()`.

## В нашем коде

**Фронтенд:**
- `frontend/courier/src/tg.js` — инициализация Telegram SDK
- `frontend/courier/src/api.js` — обёртка fetch с заголовками авторизации
- `frontend/courier/src/App.jsx` — роутинг и навигация

**Бэкенд:**
- `apps/bot_bridge/permissions.py` — `TelegramInitDataPermission`
- `apps/bot_bridge/views.py` — endpoints для Mini App (courier pool, trip, client orders)
- `tg_bot/keyboards/courier.py` — кнопки открывающие Mini App

## Порядок действий при реализации P3 (для AI)

> Это чёткий порядок. Не начинать следующий шаг, не завершив предыдущий.

```
1. [Django] Добавить tg_id, is_admin в Worker. Миграция.
2. [Django] Добавить /api/bot/identify/ endpoint.
3. [Django] Добавить все новые bot_bridge endpoints (courier pool, trip, client orders, admin stats).
4. [Django] Написать TelegramInitDataPermission в bot_bridge/permissions.py.
5. [Django] Написать notify.py для уведомлений клиентам.
6. [Bot] Создать tg_bot/ структуру. Настроить роутеры по ролям.
7. [Frontend] Создать frontend/courier/ через Vite (шаги 1-8 выше).
8. [Frontend] Создать frontend/client/ аналогично.
9. [Build] npm run build в обоих приложениях → файлы в static/miniapp/.
10. [Django] python manage.py collectstatic.
11. [Nginx] Настроить конфиг. Получить SSL.
12. [Bot] Прописать HTTPS URL кнопок Mini App.
13. [Тест] Проверить открытие TWA в Telegram → запросы доходят до Django.