# Авторизация Telegram бота через tg_id

**Область применения:** `bot_bridge`, `workers`, `clients`  
**Связанные задачи:** P1 (добавить tg_id в Worker), P2 (создать bot_bridge)

## Концепция
Курьер (сотрудник типа `COURIER`) должен аутентифицироваться в API Django через свой Telegram ID — числовой идентификатор, который Telegram присваивает каждому пользователю.

### Почему именно Telegram ID?
1. **Уникальность:** У каждого пользователя Telegram уникальный `tg_id`, который не меняется.
2. **Безопасность:** Бот может получить `tg_id` из `message.from.id` и передать его в заголовке API.
3. **Удобство:** Курьеру не нужно вводить логин/пароль — достаточно быть авторизованным в Telegram.

## Реализация

### 1. Расширение модели Worker
Необходимо добавить поле `tg_id` в модель `Worker`:

```python
class Worker(models.Model):
    # ... существующие поля ...
    tg_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        verbose_name='Telegram ID'
    )
```

**Особенности:**
- `unique=True` — один Telegram ID может быть только у одного сотрудника.
- `null=True, blank=True` — пока не все сотрудники зарегистрированы в боте.

### 2. Permission-класс `IsCourier`
В `apps/bot_bridge/permissions.py` реализована логика:

```python
tg_id = request.headers.get('X-Telegram-ID')
courier = Worker.objects.get(tg_id=tg_id)
if courier.worker_type != Worker.WorkerType.COURIER:
    raise AuthenticationFailed('Доступ только для курьеров')
request.courier = courier
```

### 3. Передача tg_id из бота
Бот (на Aiogram) должен извлекать `tg_id` из контекста и добавлять в заголовок каждого запроса к API:

```python
# Пример на Aiogram 3.x
async def call_api(endpoint, data):
    tg_id = message.from.id
    headers = {'X-Telegram-ID': str(tg_id)}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'http://localhost:8000/api/bot/{endpoint}/',
            json=data,
            headers=headers
        ) as resp:
            return await resp.json()
```

## Поток авторизации
1. Курьер отправляет боту команду `/start`.
2. Бот сохраняет его `tg_id` в базе (или администратор заранее вносит в Django Admin).
3. При каждом действии (посмотреть доставки, подтвердить доставку) бот включает `X-Telegram-ID` в заголовок.
4. Django проверяет, есть ли сотрудник с таким `tg_id` и является ли он курьером.
5. Если да — возвращает данные или выполняет действие.

## Проблемы и решения

### Проблема 1: Связь один-к-одному
Один сотрудник может иметь только один Telegram аккаунт. Если курьер сменит аккаунт, нужно обновить `tg_id` в админке.

### Проблема 2: Безопасность заголовка
Заголовок `X-Telegram-ID` передаётся открытым текстом. Необходимо использовать HTTPS в продакшене.

### Проблема 3: Фейковые запросы
Злоумышленник может подделать заголовок. Защита:
- Использовать **JWT** или **HMAC** подпись запроса с секретным ключом бота.
- Или ограничить IP-адреса (если бот работает на том же сервере).

## Альтернативные подходы

### Токеновая аутентификация
1. Бот при первом обращении получает токен (генерируется Django).
2. Токен сохраняется в боте и передаётся в заголовке `Authorization: Token <token>`.
3. Плюс: можно отозвать токен. Минус: усложнение логики.

### Сессии Django
Использовать стандартную сессионную аутентификацию, но это требует cookies и неудобно для бота.

## Интеграция с другими модулями

### Клиенты (Client)
У клиентов тоже есть поле `tg_id` (добавлено в P1). Это позволяет:
- Клиенту делать заказы через Telegram Mini App.
- Боту идентифицировать клиента по `tg_id` и показывать его историю заказов.

### Уведомления
Зная `tg_id`, система может отправлять уведомления через Telegram Bot API:
```python
await bot.send_message(tg_id, "Ваша доставка подтверждена")
```

## Примеры кода

### Django: получение курьера по tg_id
```python
def get_courier_by_tg_id(tg_id):
    try:
        return Worker.objects.get(tg_id=tg_id, worker_type=Worker.WorkerType.COURIER)
    except Worker.DoesNotExist:
        return None
```

### Bot: middleware для добавления заголовка
```python
class TelegramIDMiddleware(aiohttp.ClientSession):
    def __init__(self, tg_id):
        self.tg_id = tg_id
        super().__init__(headers={'X-Telegram-ID': str(tg_id)})
```

## Дальнейшее развитие
1. **Двухфакторная аутентификация:** Запрос кода подтверждения при критических действиях.
2. **Роли:** Разделение прав внутри курьеров (старший курьер, новичок).
3. **Веб-интерфейс:** Позволить курьеру видеть свои доставки и в браузере (через тот же `tg_id`).

## Ссылки
- [[docs/Index|Главный индекс]]
- [[docs/Modules_BotBridge|Модуль Bot Bridge]]
- [[docs/Modules/Workers|Модуль Сотрудников]]