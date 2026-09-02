# Баг: Поиск клиента по телефону не работает в tg_bot при создании заказа

## Симптом

При создании заказа через Telegram-бота (кнопочный поток) курьер вводит номер телефона клиента, но бот всегда сообщает «Новый клиент!», даже если клиент с таким номером существует в базе данных. В результате:

- Не показываются сохранённые адреса клиента
- Не подтягивается имя клиента
- Для каждого заказа создаётся дубликат клиента

В то же время в Mini App ([`OrderCreate.jsx`](frontend/courier/src/pages/OrderCreate.jsx:144)) поиск работает корректно.

## Причина

Две независимые проблемы:

### 1. Неправильный query-параметр (основной баг)

В [`tg_bot/routers/courier_create_order.py:49`](tg_bot/routers/courier_create_order.py:49) запрос к API шёл с параметром `?phone=`, а backend [`ClientSearchView`](apps/bot_bridge/views.py:1386) ожидает `?q=`:

```python
# БЫЛО (неправильно):
client_data = await api_client.get(f'/clients/search/?phone={validated_phone}')

# Backend читает:
query = request.query_params.get('q', '').strip()  # всегда пусто!
```

**Почему возникло:** разработчик бота предположил, что параметр называется `phone`, а фронтенд использует `q` (сокращение от «query»). При копировании логики из Mini App в бота название параметра не было сверено.

### 2. Потеря сообщения об ошибке в `api_client`

В [`tg_bot/api_client.py:28-29`](tg_bot/api_client.py:28) при любом HTTP-коде, отличном от 200, возвращалось `{"error": f"HTTP {resp.status}"}`. Даже если backend возвращал осмысленный JSON `{"error": "Клиент не найден"}`, бот видел только `{"error": "HTTP 404"}`.

## Где в коде

| Файл | Строка | Проблема |
|------|--------|----------|
| [`tg_bot/routers/courier_create_order.py`](tg_bot/routers/courier_create_order.py:49) | 49 | `?phone=` вместо `?q=` |
| [`tg_bot/api_client.py`](tg_bot/api_client.py:28) | 28-29 | Потеря реальной ошибки из JSON-ответа |

## Решение

### Исправление 1: query-параметр

```python
# БЫЛО:
client_data = await api_client.get(f'/clients/search/?phone={validated_phone}')

# СТАЛО:
client_data = await api_client.get(f'/clients/search/?q={validated_phone}')
```

### Исправление 2: сохранение ошибки из JSON-ответа

```python
# БЫЛО:
else:
    logger.error(f"GET {url} вернул {resp.status}: {await resp.text()}")
    return {"error": f"HTTP {resp.status}"}

# СТАЛО:
else:
    body = await resp.text()
    logger.error(f"GET {url} вернул {resp.status}: {body}")
    try:
        err_data = await resp.json(content_type=None)
        if isinstance(err_data, dict) and 'error' in err_data:
            return {"error": err_data['error']}
    except Exception:
        pass
    return {"error": f"HTTP {resp.status}"}
```

## Дополнительные улучшения (по требованию пользователя)

После исправления основного бага логика поиска была доработана до полного соответствия Mini App:

### Загрузка и показ сохранённых адресов

При нахождении клиента бот теперь загружает его адреса через [`/clients/addresses/{phone}/`](apps/bot_bridge/urls.py:49) и показывает их как inline-кнопки (до 3-х):

```python
addresses_data = await api_client.get(f'/clients/addresses/{validated_phone}/')
saved_addresses = addresses_data.get('addresses', []) if isinstance(addresses_data, dict) else []
```

### Сохранение адреса после создания заказа

После успешного создания заказа адрес сохраняется в историю клиента через [`/clients/addresses/save/`](apps/bot_bridge/urls.py:50):

```python
client_id_for_address = (
    (data.get('client_data') or {}).get('id')
    or (result.get('client') or {}).get('id')
)
if client_id_for_address and (address or latitude or longitude):
    await api_client.post('/clients/addresses/save/', data={
        'client_id': client_id_for_address,
        'address_text': address or '',
        'latitude': latitude or None,
        'longitude': longitude or None
    })
```

## Как не допустить снова

1. **Параметры API должны быть едины для всех клиентов.** Если фронтенд использует `?q=`, то и бот, и любые другие интеграции должны использовать `?q=`. Документировать это в docstring эндпоинта.
2. **HTTP-клиент должен сохранять тело ответа при ошибках.** `{"error": "HTTP 404"}` бесполезен — нужно возвращать реальную ошибку из JSON-ответа backend'а.
3. **При копировании логики из одного клиента в другой всегда сверять имена параметров запроса.** Это частая ошибка при параллельной разработке фронтенда и бота.

## Связанные концепции

- [[Concepts_TelegramBot|Telegram Bot (aiogram 3.x) в WERP]] — архитектура бота, FSM, роутеры
- [[Modules_BotBridge|Мост Telegram (BotBridge)]] — API-шлюз, эндпоинты, авторизация
- [[Bugs_ClientAddressesRouting|Список адресов не показывается (404)]] — предыдущий баг с маршрутами адресов
- [[Bugs_PhoneNormalization|Нормализация телефона в get_client_addresses]] — баг с форматом телефона