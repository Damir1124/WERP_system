# Баг: Нормализация телефона в `get_client_addresses`

## Симптом
Эндпоинт `get_client_addresses` возвращал `{"addresses": []}` (пусто), хотя клиент с таким номером телефона существует и у него есть сохранённые адреса.

## Причина
Фронтенд передаёт номер телефона вместе с префиксом `+`, например `+998950090759`. В базе данных телефоны хранятся **без** `+` — `998950090759` (поле `Client.phone` имеет `max_length=13`, формат E.164 без `+`).

Код искал точное совпадение:
```python
client = Client.objects.get(phone=phone)  # phone = "+998950090759"
```
Запись с `phone="+998950090759"` в БД отсутствует → `DoesNotExist` → перехват → пустой список.

> 💡 **Почему так вышло:** форма ввода на фронте форматирует номер для читаемости/валидации с `+`, а БД-слой хранит «чистый» числовой вид. Две точки входа (поиск клиента `ClientSearchView` уже нормализовал, а `get_client_addresses` — нет) рассинхронизировались.

## Где в коде
- `apps/clients/views.py:54-89` — `get_client_addresses` (до исправления: точный `Client.objects.get(phone=phone)`)
- `apps/clients/views.py:1411-1449` — `ClientSearchView` (уже нормализует — эталон)
- `apps/clients/models.py:7` — `phone = CharField(max_length=13, unique=True)` (хранится без `+`)

## Решение
```python
# ДО (проблемный код)
client = Client.objects.get(phone=phone)

# ПОСЛЕ (исправление)
normalized_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
client = (
    Client.objects.filter(phone=phone).first()
    or Client.objects.filter(phone=normalized_phone).first()
)
if not client:
    return Response({'addresses': []})
```

Логика: сначала пробуем точное совпадение (на случай, если фронт уже прислал нормализованный вид), затем — по очищенному номеру.

## Как не допустить снова
1. **Единая утилита нормализации.** В проекте уже есть `apps/bot_bridge/phone_validator.py` — используйте его функцию во ВСЕХ местах, где телефон сравнивается с БД (поиск, адреса, регистрация). Не дублируйте `replace('+', '')` разрозненно.
2. **Договоритесь о каноническом формате хранения** (в проекте — `998...` без `+`) и нормализуйте на границе ввода, а не в каждом view по отдельности.
3. Покрыть `get_client_addresses` тестом с телефоном `+998...` и `998...`.

## Связанные концепции
- [[Modules_Clients|Модуль Клиентов]] — поле `phone`, модель `ClientAddress`
- [[Bugs_ClientAddressesRouting|Маршрутизация api/bot/clients/addresses]] — тот же эндпоинт, другая причина пустого списка
