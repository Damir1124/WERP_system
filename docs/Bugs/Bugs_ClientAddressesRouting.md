# Баг: Список адресов клиента не показывается в Mini App курьера (404)

## Симптом
В форме создания заказа (`frontend/courier/src/pages/OrderCreate.jsx`) выпадающий список прошлых адресов клиента не появлялся. При этом:
- в БД адреса для клиента есть (проверено через shell — 3 записи `ClientAddress`);
- бэкенд перезапущен, фронтенд пересобран (`npm run build` проходит успешно);
- в консоли браузера явных ошибок нет, но список пуст.

## Причина
Фронтенд курьера делает запрос на `GET /api/bot/clients/addresses/<phone>/` (см. `frontend/courier/src/api.js` → `getClientAddresses`). Однако эндпоинты `clients/addresses/` были зарегистрированы **только** в `apps/clients/urls.py`, который монтируется как `/api/clients/`. В `apps/bot_bridge/urls.py` (монтируется как `/api/bot/`) этих маршрутов не было.

Результат: запрос курьера получал **404 Not Found**. Функция `apiFetch` бросала исключение, `setSavedAddresses` никогда не вызывался, и условие рендера `{savedAddresses.length > 0 && ...}` оставляло выпадающий список скрытым.

> 💡 **Почему это запутало:** данные в БД были, бэкенд «работал», но сам маршрут не существовал по тому префиксу, который зовёт фронтенд. Перезапуск и пересборка не могли это исправить — проблема была в маршрутизации, а не в данных или кэше.

## Где в коде
- `apps/clients/urls.py:12-13` — маршруты есть, но под префиксом `api/clients/`
- `apps/bot_bridge/urls.py` — маршрутов `clients/addresses/` **не было** (до исправления)
- `frontend/courier/src/api.js` — `getClientAddresses` строит путь `/clients/addresses/<phone>/` относительно `BASE_URL = .../api/bot`

## Решение
Добавлены импорт и маршруты в `apps/bot_bridge/urls.py`:

```python
# ДО (проблемный код)
# в urls.py bot_bridge маршрутов clients/addresses/ не было
# фронтенд звонит на /api/bot/clients/addresses/<phone>/ -> 404

# ПОСЛЕ (исправление)
from apps.clients.views import get_client_addresses, save_client_address
# ...
# Адреса клиента (зарегистрированы здесь, т.к. фронтенд курьера зовёт api/bot/clients/addresses/...)
path('clients/addresses/<str:phone>/', get_client_addresses, name='client_addresses'),
path('clients/addresses/save/', save_client_address, name='save_client_address'),
```

После исправления `curl http://localhost:8000/api/bot/clients/addresses/%2B998950090759/` возвращает корректный JSON с 3 адресами.

## Как не допустить снова
1. **Правило монтирования:** если фронтенд курьера вызывает `api/bot/...`, соответствующий эндпоинт ОБЯЗАН быть зарегистрирован в `apps/bot_bridge/urls.py`. `apps/clients/urls.py` (префикс `api/clients/`) используется только админкой/внешними вызовами.
2. **Проверяйте реальным HTTP-запросом (curl), а не только наличием данных в БД.** 404 легко пропустить, если смотреть только на логику view.
3. При добавлении нового эндпоинта, который дёргает фронт, сразу добавляйте маршрут в `bot_bridge/urls.py` и задокументируйте в `Modules_BotBridge.md`.

## Связанные концепции
- [[Modules_BotBridge|Модуль Bot Bridge]] — таблица маршрутов API
- [[Modules_Clients|Модуль Клиентов]] — модель `ClientAddress` и эндпоинты адресов
- [[Bugs_PhoneNormalization|Нормализация телефона]] — тот же эндпоинт, другая причина пустого списка
