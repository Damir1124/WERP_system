# Баг-репорт: Критические ошибки Mini App после P3.5

**Дата:** 2026-05-13  
**Статус:** ✅ Исправлено  
**Затронутые файлы:** `apps/bot_bridge/views.py`, `apps/bot_bridge/serializers.py`, `apps/bot_bridge/urls.py`, `apps/logistics/models.py`, `WERP_system/settings.py`, `WERP_system/urls.py`, `frontend/courier/src/*`, `frontend/client/` (создан с нуля)

---

## Общий симптом

После выполнения P3.5 (создание фронтенда Mini App) приложение не открывалось, кнопки не работали, фронтенд не был связан с бэкендом. Django возвращал ошибки 400/404/500 на большинство запросов.

---

## Баг 1: `Order.trip` — NOT NULL нарушение

### Симптом
`POST /api/bot/client/order/` возвращал `IntegrityError: null value in column "trip_id"` при создании заказа клиентом.

### Причина
В модели [`apps/logistics/models.py`](../../apps/logistics/models.py) поле `trip` было объявлено как обязательный FK:
```python
# ДО — обязательное поле, NULL запрещён
trip = models.ForeignKey(CourierTrip, on_delete=models.CASCADE, related_name='orders')
```
Но клиентские заказы создаются **без рейса** — они ждут назначения курьера. Рейс появляется позже, когда курьер берёт заказ из пула.

### Решение
```python
# ПОСЛЕ — разрешаем NULL
trip = models.ForeignKey(
    CourierTrip, on_delete=models.CASCADE, related_name='orders',
    null=True, blank=True, verbose_name='Рейс'
)
```
Создана и применена миграция `0003_order_trip_nullable`.

### Почему именно так
Архитектура «пул заказов» предполагает два жизненных цикла заказа:
1. **Клиентский заказ:** создаётся без рейса (`trip=None`) → курьер берёт из пула → `trip` заполняется
2. **Диспетчерский заказ:** создаётся сразу с рейсом (старый способ)

Оба сценария должны работать через одну модель `Order`.

---

## Баг 2: Несовпадение choices — фронтенд отправлял `'CASH'`, модель ожидала `'CH'`

### Симптом
Заказы создавались с неверным типом оплаты. Фильтрация по `payment_type=CASH` не работала.

### Причина
В модели `Order` choices определены как двухбуквенные коды:
```python
class PaymentType(models.TextChoices):
    CASH  = 'CH', 'Наличные'   # ← в БД хранится 'CH'
    CARD  = 'CD', 'Карта'
    BONUS = 'BS', 'Бонус'
```
Но фронтенд отправлял полные строки `'CASH'`, `'CARD'`, `'BONUS'`, которые Django не распознавал.

Аналогично для `CourierShift.Status`: `OPEN='OP'`, `CLOSED='CL'`, а фронтенд сравнивал `shift.status === 'OPEN'`.

### Решение
В [`apps/bot_bridge/views.py`](../../apps/bot_bridge/views.py) добавлен маппинг в `ClientOrderCreateView`:
```python
payment_map = {
    'CASH': Order.PaymentType.CASH,   # 'CASH' → 'CH'
    'CARD': Order.PaymentType.CARD,   # 'CARD' → 'CD'
    'BONUS': Order.PaymentType.BONUS, # 'BONUS' → 'BS'
    # Уже правильные значения тоже поддерживаем
    Order.PaymentType.CASH: Order.PaymentType.CASH,
    ...
}
payment_type = payment_map.get(payment_type_raw, Order.PaymentType.CASH)
```

В фронтенде [`frontend/courier/src/pages/Pool.jsx`](../../frontend/courier/src/pages/Pool.jsx) и [`Shifts.jsx`](../../frontend/courier/src/pages/Shifts.jsx) добавлены маппинги для отображения:
```jsx
// Pool.jsx — отображение типа оплаты
const map = {
  'CH': { label: 'Наличные', cls: 'bg-yellow-100 text-yellow-800' },
  'CD': { label: 'Карта', cls: 'bg-green-100 text-green-800' },
  ...
}

// Shifts.jsx — статус смены
shift.status === 'OP'  // открыта (не 'OPEN'!)
shift.status === 'CL'  // закрыта (не 'CLOSED'!)
```

### Как не допустить снова
**Правило:** Всегда используй константы модели вместо строк. В Django:
```python
Order.PaymentType.CASH   # правильно — 'CH'
'CASH'                   # неправильно — не совпадёт с БД
```
В React — всегда проверяй реальные значения через Django Admin или API-ответ, а не угадывай по названию.

---

## Баг 3: `WorkerSerializer` — несуществующее поле `type_worker`

### Симптом
`GET /api/bot/courier/profile/` возвращал `AttributeError: Got AttributeError when attempting to get a value for field 'type_worker'`.

### Причина
В [`apps/bot_bridge/serializers.py`](../../apps/bot_bridge/serializers.py) поле было названо неверно:
```python
# ДО — неверное имя поля
fields = ['id', 'full_name', 'type_worker', 'date_for_payed', 'tg_id']
```
В модели [`apps/workers/models.py`](../../apps/workers/models.py) поле называется `worker_type`.

### Решение
```python
# ПОСЛЕ — правильное имя + добавлено is_admin
fields = ['id', 'full_name', 'worker_type', 'date_for_payed', 'tg_id', 'is_admin']
```

---

## Баг 4: Битые импорты в `views.py`

### Симптом
Django не запускался: `ImportError: cannot import name 'DeliveryConfirmationSerializer'`.

### Причина
В [`apps/bot_bridge/views.py`](../../apps/bot_bridge/views.py) были импорты устаревших сериализаторов, которые существовали в файле, но не были импортированы в блоке `from ... import`:
```python
# В views.py использовались, но не импортировались:
DeliveryConfirmationSerializer  # ← использовался в DeliveryConfirmationView
QuantityUpdateSerializer        # ← использовался в UpdateQuantityView
```

### Решение
Устаревшие views (`DeliveryConfirmationView`, `UpdateQuantityView`) переведены в режим `410 Gone` — они больше не используют эти сериализаторы:
```python
class DeliveryConfirmationView(APIView):
    permission_classes = [IsCourier]
    def post(self, request):
        return Response({'error': 'Deprecated. Use /courier/orders/confirm/'}, 
                       status=status.HTTP_410_GONE)
```

---

## Баг 5: `CourierPoolView` — URL assign не совпадал с роутером

### Симптом
`POST /api/bot/courier/pool/123/assign/` возвращал `405 Method Not Allowed`.

### Причина
В старом `urls.py` оба URL (`/courier/pool/` и `/courier/pool/<id>/assign/`) указывали на один и тот же класс `CourierPoolView`. Но Django не передавал `order_id` в метод `post()` — он ожидал его как параметр URL, а view его не принимал.

### Решение
Разделили на два отдельных класса:
```python
# urls.py
path('courier/pool/', views.CourierPoolView.as_view()),           # GET — список
path('courier/pool/<int:order_id>/assign/', views.CourierAssignOrderView.as_view()),  # POST — взять

# views.py
class CourierPoolView(APIView):
    def get(self, request): ...  # только GET

class CourierAssignOrderView(APIView):
    def post(self, request, order_id): ...  # только POST с order_id
```

---

## Баг 6: `Trip.jsx` — неверная структура данных из API

### Симптом
Страница «Мой рейс» показывала нули везде, счётчики не работали.

### Причина
`GET /api/bot/courier/trip/current/` возвращает:
```json
{
  "active_shift": true,
  "trip": { "id": 1, "full_loaded": 10, "orders": [...] },
  "summary": { "delivered": 3, "cash_expected": 150000, ... }
}
```
Но старый [`Trip.jsx`](../../frontend/courier/src/pages/Trip.jsx) обращался к данным напрямую:
```jsx
// ДО — неверно
const [trip, setTrip] = useState(null)
setTrip(data)  // data = { active_shift, trip, summary }
// ...
<p>{trip.full_loaded}</p>  // undefined! нужно trip.trip.full_loaded
```

### Решение
Переработан `Trip.jsx` — теперь правильно деструктурирует ответ:
```jsx
// ПОСЛЕ — правильно
const [data, setData] = useState(null)
setData(result)  // result = { active_shift, trip, summary }
// ...
const trip = data.trip
const summary = data.summary || {}
<p>{summary.full_loaded ?? 0}</p>  // из summary
```

Также добавлены состояния для случаев «нет смены» и «нет рейса» с кнопками открытия.

---

## Баг 7: `CourierShiftListView` — не было POST-метода

### Симптом
`POST /api/bot/courier/shifts/` возвращал `405 Method Not Allowed`. Кнопка «Открыть смену» не работала.

### Причина
`CourierShiftListView` имел только метод `get()`.

### Решение
Добавлен метод `post()` с проверкой на уже открытую смену:
```python
def post(self, request):
    courier = request.courier
    existing = CourierShift.objects.filter(
        courier=courier, status=CourierShift.Status.OPEN
    ).first()
    if existing:
        return Response({'message': 'Смена уже открыта', 'shift': ...}, status=200)
    shift = CourierShift.objects.create(courier=courier)
    return Response({'message': 'Смена открыта', 'shift': ...}, status=201)
```

Аналогично добавлен `CourierTripListView.post()` для открытия рейса.

---

## Баг 8: CORS блокировал запросы с ngrok

### Симптом
Браузер показывал `CORS policy: No 'Access-Control-Allow-Origin' header`. Все API-запросы из Mini App блокировались.

### Причина
В [`WERP_system/settings.py`](../../WERP_system/settings.py) ngrok URL был захардкожен:
```python
CORS_ALLOWED_ORIGINS = [
    "https://monkhood-chaperone-stinger.ngrok-free.dev",  # ← конкретный URL
    ...
]
```
При смене ngrok URL (что происходит при каждом перезапуске бесплатного ngrok) CORS переставал работать.

### Решение
Заменено на regex-паттерн, разрешающий все ngrok-домены:
```python
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.ngrok-free\.dev$",
    r"^https://.*\.ngrok\.io$",
]
```

---

## Что было создано с нуля: Клиентский Mini App

Папка `frontend/client/` была полностью пустой. Создано полноценное React-приложение:

| Файл | Назначение |
|------|-----------|
| [`src/App.jsx`](../../frontend/client/src/App.jsx) | Роутинг, проверка регистрации, состояния загрузки |
| [`src/pages/Register.jsx`](../../frontend/client/src/pages/Register.jsx) | Форма регистрации нового клиента |
| [`src/pages/Catalog.jsx`](../../frontend/client/src/pages/Catalog.jsx) | Каталог товаров с иконками и ценами |
| [`src/pages/OrderForm.jsx`](../../frontend/client/src/pages/OrderForm.jsx) | Оформление заказа: кол-во, оплата, адрес |
| [`src/pages/MyOrders.jsx`](../../frontend/client/src/pages/MyOrders.jsx) | История заказов со статусами |
| [`src/api.js`](../../frontend/client/src/api.js) | Fetch-обёртка с X-Telegram-ID заголовком |
| [`src/tg.js`](../../frontend/client/src/tg.js) | Инициализация Telegram WebApp SDK |

**Новые API endpoints** добавлены в `bot_bridge`:
- `POST /api/bot/client/register/` — регистрация клиента
- `GET /api/bot/client/profile/?tg_id=<id>` — профиль клиента

---

## Связанные концепции
- [[Concepts_TelegramMiniApp|Telegram Mini App (TWA)]] — как работает initData, авторизация
- [[Concepts_TelegramBotAuth|Авторизация через tg_id]] — X-Telegram-ID заголовок
- [[Modules_BotBridge|Модуль Bot Bridge]] — полная документация API
