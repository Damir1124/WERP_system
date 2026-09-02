# Feature: История смен и рейсов в Telegram боте

## Зачем это нужно

Курьеру нужна возможность просматривать историю своих смен и рейсов прямо в Telegram, не открывая Mini App. Это позволяет:

- Быстро оценить дневную выручку (наличные/карта)
- Посмотреть сколько воды доставлено за смену
- Провалиться в детали конкретного рейса — какие заказы были доставлены
- Увидеть статус каждого заказа (доставлен/отменён/в работе)

## Как это работает

### 3-уровневая навигация через inline-кнопки

Вся навигация реализована через `callback_query` и `edit_text` — без создания новых сообщений. Пользователь нажимает кнопки и видит, как меняется содержимое текущего сообщения.

```
Уровень 0: Список смен
    │
    ├── 🔴 02.08 | 150 000 сум  ──→  Уровень 1: Детали смены
    │                                   │
    │                                   ├── 🟢 Рейс #1 | 12 шт  ──→  Уровень 2: Детали рейса
    │                                   │                              │
    │                                   │                              ├── 🟢 Иванов | 2 шт  ──→  Уровень 3: Заказ #42
    │                                   │                              ├── 🟡 Петров | 1 шт  ──→  ...
    │                                   │                              └── ⬅️ Назад к смене
    │                                   │
    │                                   └── ⬅️ Назад к списку смен
    │
    └── 🔒 Закрыть смену
```

### Кэширование данных

При открытии «Смены и рейсы» бот загружает всю историю через [`ShiftHistoryView`](apps/bot_bridge/views.py:221) и сохраняет в модульном кэше `_shifts_cache[tg_id]`:

```python
# tg_bot/routers/courier.py:32
_shifts_cache: dict[int, list] = {}
```

Это позволяет навигировать по уровням без дополнительных API-запросов. Кэш живёт пока пользователь не закроет бот или не откроет «Смены и рейсы» заново.

**Почему кэш, а не FSM?** Данные только для чтения, не нужно хранить состояние между шагами. Проще и быстрее.

### Форматирование текста

Три функции-форматтера в [`courier.py`](tg_bot/routers/courier.py:650):

1. `_build_shift_list_text(shifts)` — сводка по всем сменам: общее количество, наличные/карта, доставлено воды/заказов
2. `_build_shift_detail_text(shift)` — детали одной смены: финансы, статистика, список рейсов
3. `_build_trip_detail_text(trip)` — детали рейса: загружено/доставлено/остаток/брак, список заказов

### Callback-хендлеры

| Хендлер | Callback data | Что делает |
|---------|--------------|------------|
| [`show_shift_detail`](tg_bot/routers/courier.py:748) | `shift_detail_{id}` | Показывает детали смены + кнопки рейсов |
| [`show_trip_detail`](tg_bot/routers/courier.py:766) | `trip_detail_{id}` | Показывает детали рейса + кнопки заказов |
| [`show_order_info`](tg_bot/routers/courier.py:793) | `order_info_{id}` | Показывает детали заказа (клиент, товары, сумма, статус) |
| [`back_to_shifts`](tg_bot/routers/courier.py:847) | `back_to_shifts` | Возврат к списку смен |
| [`back_to_shift`](tg_bot/routers/courier.py:861) | `back_to_shift_{id}` | Возврат к деталям смены |

### Важно: парсинг callback_data

Для `back_to_shift_{id}` используется `rsplit("_", 1)[1]`, а не `split("_")[2]`, потому что:

```python
"back_to_shift_5".split("_")    # ['back', 'to', 'shift', '5'] → [2] = 'shift' ❌
"back_to_shift_5".rsplit("_", 1)  # ['back_to_shift', '5']    → [1] = '5' ✅
```

Остальные callback_data (`shift_detail_5`, `trip_detail_5`, `order_info_5`) используют `split("_")[2]`, так как у них ровно 3 части, разделённых `_`.

## Клавиатуры

Три новых функции в [`keyboards/courier.py`](tg_bot/keyboards/courier.py:100):

1. `get_shifts_list_keyboard(shifts, has_active_shift)` — кнопки смен + «Закрыть смену»
2. `get_shift_detail_keyboard(trips, shift_id)` — кнопки рейсов + «Назад к списку смен»
3. `get_trip_detail_keyboard(orders, shift_id)` — кнопки заказов + «Назад к смене»

## Backend: ShiftHistoryView

Эндпоинт [`GET /api/bot/shifts/history/`](apps/bot_bridge/views.py:221) уже существовал и возвращает:

```json
[
  {
    "id": 1,
    "date": "2026-08-02",
    "status": "OP",
    "cash_total": 150000,
    "card_total": 75000,
    "stats": {"orders_count": 8, "water_delivered": 24},
    "trips": [
      {
        "id": 1,
        "status": "AC",
        "full_loaded": 24,
        "summary": {"delivered": 12, "full_remain": 0, ...},
        "orders": [
          {
            "id": 42,
            "status": "DL",
            "client_name": "Иванов",
            "payment_type": "CH",
            "total_price": 25000,
            "items": [{"product_name": "Вода 19л", "quantity": 2}]
          }
        ]
      }
    ]
  }
]
```

## Исправление: закрытие рейса с переносом заказов

**Проблема:** В [`TripCloseView`](apps/bot_bridge/views.py:451) при закрытии рейса незавершённые заказы откреплялись от рейса (`trip=None`) и возвращались в пул. Курьер терял контекст — заказы, которые он уже взял, но не доставил, становились доступны другим курьерам.

**Решение:** Заказы переносятся на следующий активный рейс в той же смене. Если следующего рейса нет — создаётся новый:

```python
# БЫЛО — заказы возвращаются в пул:
pending_orders.update(trip=None)

# СТАЛО — заказы переносятся в следующий рейс:
next_trip = CourierTrip.objects.filter(
    shift=trip.shift,
    status=CourierTrip.Status.ACTIVE
).exclude(id=trip.id).first()
if not next_trip:
    next_trip = CourierTrip.objects.create(
        shift=trip.shift,
        full_loaded=0,
        status=CourierTrip.Status.ACTIVE
    )
pending_orders.update(trip=next_trip)
```

## Связанные файлы

| Файл | Роль |
|------|------|
| [`tg_bot/routers/courier.py:32`](tg_bot/routers/courier.py:32) | Кэш `_shifts_cache` |
| [`tg_bot/routers/courier.py:650`](tg_bot/routers/courier.py:650) | Функции форматирования |
| [`tg_bot/routers/courier.py:730`](tg_bot/routers/courier.py:730) | Хендлер списка смен |
| [`tg_bot/routers/courier.py:748`](tg_bot/routers/courier.py:748) | Хендлер деталей смены |
| [`tg_bot/routers/courier.py:766`](tg_bot/routers/courier.py:766) | Хендлер деталей рейса |
| [`tg_bot/routers/courier.py:793`](tg_bot/routers/courier.py:793) | Хендлер деталей заказа |
| [`tg_bot/routers/courier.py:847`](tg_bot/routers/courier.py:847) | Навигация назад |
| [`tg_bot/keyboards/courier.py:100`](tg_bot/keyboards/courier.py:100) | Клавиатуры для всех уровней |
| [`apps/bot_bridge/views.py:423`](apps/bot_bridge/views.py:423) | TripCloseView — закрытие рейса |
| [`apps/bot_bridge/views.py:221`](apps/bot_bridge/views.py:221) | ShiftHistoryView — история смен |
| [`frontend/courier/src/pages/ShiftHistory.jsx`](frontend/courier/src/pages/ShiftHistory.jsx) | Mini App аналог (аккордеон) |