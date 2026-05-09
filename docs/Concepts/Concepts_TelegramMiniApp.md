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

**Валидация в `bot_bridge/permissions.py`:**
```python
import hashlib
import hmac
from urllib.parse import parse_qsl
from rest_framework.permissions import BasePermission

class TelegramInitDataPermission(BasePermission):
    def has_permission(self, request, view):
        init_data = request.headers.get('X-Telegram-Init-Data', '')
        bot_token = settings.TELEGRAM_BOT_TOKEN

        # Алгоритм валидации из документации Telegram:
        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in sorted(parse_qsl(init_data))
            if k != 'hash'
        )
        secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        received_hash = dict(parse_qsl(init_data)).get('hash', '')
        return hmac.compare_digest(expected_hash, received_hash)
```

> **Упрощение для MVP:** На этапе разработки можно использовать только `X-Telegram-ID` заголовок без валидации подписи. Включить полную валидацию перед продакшеном.

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