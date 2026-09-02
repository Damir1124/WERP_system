ё# Фича: Launcher — единая точка входа в Mini App

## Назначение

Launcher — это **единый статичный URL**, на который ведёт одна кнопка «Открыть приложение» в Telegram-боте. Он решает проблему: у Telegram Web App кнопки URL статичен, а интерфейс должен зависеть от роли пользователя.

**Зачем:** вместо того чтобы менять URL кнопки при каждой смене роли сотрудника, Launcher сам определяет роль и перенаправляет в нужный Mini App. При смене типа сотрудника в админке интерфейс меняется автоматически — без изменения кнопки.

## Как работает

```
Кнопка «Открыть приложение» → /static/miniapp/launcher/index.html
  → Launcher берёт Telegram.WebApp.initData
  → вызывает GET /api/bot/identify/
  → backend через resolve_user_role() определяет target_app
  → Launcher перенаправляет в нужный Mini App
```

## Ключевые файлы

| Файл | Роль |
|------|------|
| [`frontend/launcher/src/App.jsx`](../../frontend/launcher/src/App.jsx) | Логика Launcher: identify → redirect / registration |
| [`apps/bot_bridge/utils.py`](../../apps/bot_bridge/utils.py) | `resolve_user_role()` — единый источник истины о роли |
| [`apps/bot_bridge/views.py`](../../apps/bot_bridge/views.py) | `IdentifyView` — API `/api/bot/identify/` |
| [`WERP_system/urls.py`](../../WERP_system/urls.py) | Маршрут `/miniapp/launcher/` |

## Матрица перенаправления (target_app → URL)

| worker_type | target_app | Mini App |
|---|---|---|
| `courier` | `courier` | `/static/miniapp/courier/` |
| `operator` | `operator` | `/static/miniapp/operator/` |
| `owner` | `admin` | `/static/miniapp/owner/` |
| `is_admin` | `admin` | `/static/miniapp/owner/` |
| Client | `client` | `/static/miniapp/client/` |
| неизвестный | `registration` | экран регистрации в Launcher |

## Важные детали

- **Приоритет Worker над Client:** если один tg_id есть и в Worker, и в Client — открывается интерфейс работника. Порядок: `Worker (любой worker_type) → Client → UNKNOWN`.
- **Защита от дубля Client:** [`ClientRegisterView`](../../apps/bot_bridge/views.py:1397) перед созданием клиента проверяет `Worker.objects.filter(tg_id=tg_id)`. Если работник найден — возвращает `status: 'worker'`, дубль Client **не создаётся**. Клиентский Mini App при таком ответе перенаправляет пользователя обратно в Launcher (см. [`frontend/client/src/App.jsx`](../../frontend/client/src/App.jsx:83)).
- **Передача initData:** при редиректе Launcher сохраняет `initData` и `tg_id` в `sessionStorage`, чтобы целевой Mini App мог аутентифицироваться.
- **Безопасность:** Launcher лишь выполняет редирект по `target_app` от backend. Реальные права проверяются в `permissions.py` на каждом API-эндпоинте — нельзя открыть чужой интерфейс, подменив URL.
