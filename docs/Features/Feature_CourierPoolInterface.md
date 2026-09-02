# Интерфейс пула заказов для курьера (Telegram Bot)

**Создан:** 2026-07-05  
**Статус:** Спецификация  
**Цель:** Реализовать удобный интерфейс пула заказов через кнопки Telegram (без Mini App)

---

## 1. Шапка со статистикой всех курьеров

### Формат отображения:
```
💧 💧 ✅ ⏳
Q | X  Y  Z  Имя Телефон
```

**Важно:** Q отделяется от X вертикальной чертой `|`

### Расшифровка показателей:

| Иконка | Показатель | Описание | Расчёт |
|--------|-----------|----------|--------|
| 💧 | **Q** | Остаток воды в машине | `trip.full_loaded - delivered_qty - trip.full_returned` |
| 💧 | **X** | Всего нужно воды (взятые заказы) | `SUM(order.items.quantity WHERE order.trip=current_trip AND product=BOTTLE_20L)` |
| ✅ | **Y** | Выполненных заказов | `COUNT(order WHERE status=DELIVERED AND trip=current_trip)` |
| ⏳ | **Z** | Взятых, но не завершённых | `COUNT(order WHERE status=PENDING AND trip=current_trip)` |

### Пример вывода:
```
📊 Курьеры на смене (05.07.2026):

💧 💧 ✅ ⏳
2 | 23  27 1  Muxammad +998945596336
0 | 24  24 0  Kamoljon +998915596336
0 | 25  25 0  Hikmatillo +998922366336
4 |  1   1 1  Yashnar +998777026336
8 | 25  25 2  Najmiddin +998774956336

💧 - Остаток в машине | Всего нужно
✅ - Выполнено
⏳ - В процессе
```

### API endpoint:
```
GET /api/bot/courier/colleagues/
```

**Ответ:**
```json
[
  {
    "courier_id": 5,
    "courier_name": "Muxammad",
    "phone": "+998945596336",
    "current_trip": {
      "id": 42,
      "full_remain": 2,
      "total_needed": 27,
      "delivered_count": 1,
      "pending_count": 1
    }
  },
  ...
]
```

---

## 2. Список заказов (кнопки)

### Формат кнопки:
```
#{order_id} | {quantity} | {address_short}
```

**Пример:**
```
#395 | 2 | Сино
#394 | 6 | Пушти областной, ориент макт 19
#393 | 5 | Победа
```

### Логика отображения:
- **Одна кнопка = один заказ**
- **address_short** = первые 30 символов адреса (или до первой запятой)
- **Сортировка:** по дате создания (новые сверху)
- **Фильтр:** только заказы со статусом `PENDING` и `trip=None` (не взятые)

### При нажатии на кнопку:

**Показывается детальная информация:**
```
📦 Заказ #395

👤 Клиент: Иванов И.И.
📞 Телефон: +998901234567
📍 Адрес: ул. Сино, дом 15, кв. 42

🚰 Товары:
• Вода 19л × 2 шт.
• Помпа × 1 шт.

💰 Сумма: 80 000 сум
💳 Оплата: Наличные

⏰ Создан: 15 минут назад

[✅ Взять заказ]
[⬅️ Назад в пул]
```

**Кнопки:**
- **[✅ Взять заказ]** → `callback_data: take_order_{order_id}`
- **[⬅️ Назад в пул]** → `callback_data: back_to_pool`

---

## 3. Кнопка создания заказа

### Расположение:
**Всегда видна внизу списка заказов:**
```
[➕ Создать новый заказ]
```

### FSM (Finite State Machine) для создания заказа:

```python
class CourierCreateOrder(StatesGroup):
    waiting_for_phone = State()
    waiting_for_address_choice = State()  # Автозаполнение или ручной ввод
    waiting_for_address_text = State()
    waiting_for_location = State()
    waiting_for_product_quantity = State()
    waiting_for_add_more_products = State()
    waiting_for_payment_type = State()
```

---

## 4. Форма создания заказа (пошагово)

### Шаг 1: Ввод телефона

**Бот:**
```
📞 Введите номер телефона клиента:
(формат: +998901234567)
```

**Валидация номера (умная):**

| Ввод пользователя | Результат после валидации |
|-------------------|---------------------------|
| `+998901234567` | `+998901234567` ✅ |
| `998901234567` | `+998901234567` ✅ (добавлен +) |
| `901234567` | `+998901234567` ✅ (добавлен +998) |
| `90 123 45 67` | `+998901234567` ✅ (удалены пробелы) |
| `+998 90 123-45-67` | `+998901234567` ✅ (удалены пробелы и дефисы) |
| `8901234567` | `+998901234567` ✅ (заменён 8 на +998) |
| `abc123` | ❌ Ошибка: "Введите корректный номер" |
| `+7901234567` | ❌ Ошибка: "Только узбекские номера (+998)" |

**Код валидации:**
```python
import re

def validate_uzbek_phone(phone: str) -> str:
    """
    Умная валидация узбекского номера телефона.
    Возвращает номер в формате +998XXXXXXXXX или вызывает ValueError.
    """
    # Удаляем все символы кроме цифр и +
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Удаляем + в начале для обработки
    if phone.startswith('+'):
        phone = phone[1:]
    
    # Если начинается с 8, заменяем на 998
    if phone.startswith('8') and len(phone) == 10:
        phone = '998' + phone[1:]
    
    # Если начинается с 9 (без кода страны), добавляем 998
    if phone.startswith('9') and len(phone) == 9:
        phone = '998' + phone
    
    # Проверяем, что начинается с 998
    if not phone.startswith('998'):
        raise ValueError("Номер должен начинаться с +998")
    
    # Проверяем длину (998 + 9 цифр = 12)
    if len(phone) != 12:
        raise ValueError(f"Неверная длина номера: {len(phone)} (должно быть 12)")
    
    # Проверяем, что все символы — цифры
    if not phone.isdigit():
        raise ValueError("Номер должен содержать только цифры")
    
    return '+' + phone
```

---

### Шаг 2: Поиск клиента и автозаполнение

**Логика:**

1. **Поиск клиента по телефону:**
   ```python
   client = Client.objects.filter(phone=validated_phone).first()
   ```

2. **Если клиент НАЙДЕН:**
   ```
   ✅ Клиент найден: Иванов И.И.
   
   Выберите адрес доставки:
   
   [📍 ул. Навои, 15, кв. 42] (последний адрес)
   [📍 Отправить геолокацию]
   [✍️ Ввести новый адрес]
   ```

3. **Если клиент НЕ НАЙДЕН:**
   ```
   📝 Новый клиент!
   Имя будет создано автоматически: "6336"
   
   Введите адрес доставки:
   (или отправьте геолокацию)
   
   [📍 Отправить геолокацию]
   ```

---

### Шаг 3: Ввод адреса

**Вариант A: Текстовый адрес**
```
Курьер: ул. Регистан, 8, кв. 5
Бот: ✅ Адрес сохранён
```

**Вариант B: Геолокация**
```
Курьер: [отправляет геолокацию]
Бот: ✅ Геолокация сохранена
     📍 Координаты: 39.654321, 66.975432
```

**Сохранение в БД:**
- Если **текстовый адрес:** `client.address = text`, `latitude/longitude = None`
- Если **геолокация:** `client.latitude = lat`, `client.longitude = lon`, `address = "Геолокация"`
- Если **оба:** сохраняем оба поля

**Обновление существующего клиента:**
```python
if client:
    # Перезаписываем адрес/координаты
    client.address = new_address
    client.latitude = new_latitude
    client.longitude = new_longitude
    client.save(update_fields=['address', 'latitude', 'longitude'])
```

---

### Шаг 4: Ввод товаров

**По умолчанию: Вода 19л**
```
🚰 Сколько баклажек воды 19л?
(введите число)
```

**Курьер:** `5`

**Бот:**
```
✅ Добавлено: Вода 19л × 5 шт.

Добавить ещё товары?

[➕ Добавить товар]
[✅ Продолжить к оплате]
```

**Если нажата [➕ Добавить товар]:**
```
Выберите товар:

[💧 Вода 19л]
[🧊 Помпа для воды]
[🥤 Стаканчики]
[🧴 Другое]
```

**После выбора товара:**
```
Сколько штук "Помпа для воды"?
```

**Курьер:** `1`

**Бот:**
```
✅ Добавлено: Помпа × 1 шт.

Текущий заказ:
• Вода 19л × 5 шт.
• Помпа × 1 шт.

[➕ Добавить ещё]
[✅ Продолжить к оплате]
```

---

### Шаг 5: Выбор типа оплаты

```
💳 Способ оплаты?

[💵 Наличные]
[💳 Карта]
[🎁 Бонусы]
```

---

### Шаг 6: Подтверждение и создание

```
📦 Подтверждение заказа:

👤 Клиент: 6336 (новый)
📞 Телефон: +998901234567
📍 Адрес: ул. Регистан, 8, кв. 5

🚰 Товары:
• Вода 19л × 5 шт. (75 000 сум)
• Помпа × 1 шт. (50 000 сум)

💰 Итого: 125 000 сум
💳 Оплата: Наличные

[✅ Создать заказ]
[❌ Отменить]
```

**После создания:**
```
✅ Заказ #396 создан!

Заказ автоматически добавлен в ваш текущий рейс.

[📦 Вернуться в пул]
[🚚 Мой рейс]
```

---

## 5. API endpoints (что нужно добавить)

### 5.1 Список коллег со статистикой
```
GET /api/bot/courier/colleagues/
Headers: X-Telegram-ID: {tg_id}
```

**Ответ:**
```json
[
  {
    "courier_id": 5,
    "courier_name": "Muxammad",
    "phone": "+998945596336",
    "current_trip": {
      "id": 42,
      "full_remain": 2,
      "total_needed": 27,
      "delivered_count": 1,
      "pending_count": 1
    }
  }
]
```

---

### 5.2 Создание заказа курьером
```
POST /api/bot/courier/orders/create/
Headers: X-Telegram-ID: {tg_id}
```

**Тело запроса:**
```json
{
  "phone": "+998901234567",
  "address": "ул. Регистан, 8, кв. 5",
  "latitude": 39.654321,
  "longitude": 66.975432,
  "items": [
    {"product_id": 2, "quantity": 5},
    {"product_id": 8, "quantity": 1}
  ],
  "payment_type": "CASH"
}
```

**Логика на бэкенде:**
1. Валидация телефона (функция `validate_uzbek_phone`)
2. Поиск/создание клиента:
   ```python
   client, created = Client.objects.get_or_create(
       phone=validated_phone,
       defaults={
           'name': phone[-4:],  # Последние 4 цифры
           'address': address,
           'latitude': latitude,
           'longitude': longitude
       }
   )
   if not created:
       # Обновляем адрес существующего клиента
       client.address = address
       client.latitude = latitude
       client.longitude = longitude
       client.save()
   ```
3. Создание заказа:
   ```python
   order = Order.objects.create(
       client=client,
       trip=courier.current_trip,  # Текущий рейс курьера
       assigned_courier=courier,
       payment_type=payment_type,
       status=Order.Status.PENDING
   )
   ```
4. Создание позиций заказа:
   ```python
   for item_data in items:
       OrderItem.objects.create(
           order=order,
           product_id=item_data['product_id'],
           quantity=item_data['quantity']
       )
   ```

**Ответ:**
```json
{
  "id": 396,
  "client": {
    "name": "6336",
    "phone": "+998901234567",
    "address": "ул. Регистан, 8, кв. 5"
  },
  "items": [
    {
      "product_name": "Вода 19л",
      "quantity": 5,
      "price": 75000
    },
    {
      "product_name": "Помпа",
      "quantity": 1,
      "price": 50000
    }
  ],
  "total_price": 125000,
  "payment_type": "CASH",
  "status": "PENDING"
}
```

---

### 5.3 Детали заказа
```
GET /api/bot/orders/{order_id}/
```

**Ответ:**
```json
{
  "id": 395,
  "client": {
    "name": "Иванов И.И.",
    "phone": "+998901234567",
    "address": "ул. Сино, дом 15, кв. 42",
    "latitude": 39.654321,
    "longitude": 66.975432
  },
  "items": [
    {
      "product_name": "Вода 19л",
      "quantity": 2,
      "price": 30000
    }
  ],
  "total_price": 30000,
  "payment_type": "CASH",
  "payment_type_display": "Наличные",
  "status": "PENDING",
  "created_at": "2026-07-05T14:10:00Z",
  "minutes_ago": 15
}
```

---

### 5.4 Взять заказ в рейс
```
POST /api/bot/courier/pool/{order_id}/assign/
Headers: X-Telegram-ID: {tg_id}
```

**Логика:**
1. Проверка активного рейса курьера
2. Назначение заказа:
   ```python
   order.trip = courier.current_trip
   order.assigned_courier = courier
   order.save()
   ```

**Ответ:**
```json
{
  "success": true,
  "message": "Заказ #395 добавлен в ваш рейс"
}
```

---

## 6. Структура роутера (tg_bot/routers/courier.py)

```python
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, Location
from aiogram.fsm.context import FSMContext

from tg_bot.states.courier import CourierCreateOrder
from tg_bot.utils.phone_validator import validate_uzbek_phone
from tg_bot.api_client import api_client

router = Router(name="courier")

# Пул заказов
@router.message(F.text == "📦 Пул заказов")
async def show_pool(message: Message):
    """Показать пул заказов со статистикой коллег"""
    tg_id = message.from_user.id
    
    # Получаем статистику коллег
    colleagues = await api_client.get(
        '/api/bot/courier/colleagues/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    # Получаем список заказов
    orders = await api_client.get(
        '/api/bot/courier/pool/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    # Формируем шапку со статистикой
    header = "📊 Курьеры на смене:\n\n💧 💧 ✅ ⏳\n"
    for colleague in colleagues.json():
        trip = colleague.get('current_trip', {})
        header += (
            f"{trip.get('full_remain', 0):2d} | "
            f"{trip.get('total_needed', 0):2d}  "
            f"{trip.get('delivered_count', 0):2d} "
            f"{trip.get('pending_count', 0)} "
            f"{colleague['courier_name']} {colleague['phone']}\n"
        )
    
    header += "\n💧 - Остаток | Всего нужно\n✅ - Выполнено\n⏳ - В процессе\n\n"
    
    # Формируем кнопки заказов
    buttons = []
    for order in orders.json()[:20]:  # Максимум 20 заказов
        address_short = order['client']['address'][:30]
        quantity = sum(item['quantity'] for item in order['items'])
        button_text = f"#{order['id']} | {quantity} | {address_short}"
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"order_details_{order['id']}"
        )])
    
    # Кнопка создания заказа
    buttons.append([InlineKeyboardButton(
        text="➕ Создать новый заказ",
        callback_data="create_order_start"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(header + "📦 Доступные заказы:", reply_markup=keyboard)

# Детали заказа
@router.callback_query(F.data.startswith("order_details_"))
async def show_order_details(callback: CallbackQuery):
    """Показать детали заказа"""
    order_id = int(callback.data.split("_")[2])
    
    response = await api_client.get(f'/api/bot/orders/{order_id}/')
    order = response.json()
    
    items_text = "\n".join([
        f"• {item['product_name']} × {item['quantity']} шт."
        for item in order['items']
    ])
    
    text = (
        f"📦 Заказ #{order_id}\n\n"
        f"👤 Клиент: {order['client']['name']}\n"
        f"📞 Телефон: {order['client']['phone']}\n"
        f"📍 Адрес: {order['client']['address']}\n\n"
        f"🚰 Товары:\n{items_text}\n\n"
        f"💰 Сумма: {order['total_price']:,} сум\n"
        f"💳 Оплата: {order['payment_type_display']}\n\n"
        f"⏰ Создан: {order['minutes_ago']} минут назад"
    )
    
    buttons = [
        [InlineKeyboardButton(text="✅ Взять заказ", callback_data=f"take_order_{order_id}")],
        [InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="back_to_pool")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)

# Взять заказ
@router.callback_query(F.data.startswith("take_order_"))
async def take_order(callback: CallbackQuery):
    """Взять заказ в свой рейс"""
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    
    response = await api_client.post(
        f'/api/bot/courier/pool/{order_id}/assign/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    if response.status == 200:
        await callback.message.edit_text(
            f"✅ Заказ #{order_id} добавлен в ваш рейс!\n\n"
            f"Используйте '🚚 Мой рейс' для просмотра."
        )
    else:
        error = response.json().get('error', 'Неизвестная ошибка')
        await callback.answer(f"❌ {error}", show_alert=True)

# Создание заказа - Шаг 1: Телефон
@router.callback_query(F.data == "create_order_start")
async def create_order_start(callback: CallbackQuery, state: FSMContext):
    """Начать создание заказа"""
    await callback.message.edit_text(
        "📞 Введите номер телефона клиента:\n"
        "(формат: +998901234567)"
    )
    await state.set_state(CourierCreateOrder.waiting_for_phone)

@router.message(CourierCreateOrder.waiting_for_phone)
async def create_order_phone(message: Message, state: FSMContext):
    """Обработка телефона с валидацией"""
    try:
        validated_phone = validate_uzbek_phone(message.text)
    except ValueError as e:
        await message.answer(f"❌ {str(e)}\n\nПопробуйте ещё раз:")
        return
    
    await state.update_data(phone=validated_phone)
    
    # Проверяем, есть ли клиент в БД
    response = await api_client.get(f'/api/bot/clients/search/?phone={validated_phone}')
    
    if response.status == 200:
        client = response.json()
        await state.update_data(client_exists=True, client_data=client)
        
        buttons = [
            [InlineKeyboardButton(
                text=f"📍 {client['address'][:40]}",
                callback_data="use_saved_address"
            )],
            [InlineKeyboardButton(
                text="📍 Отправить геолокацию",
                callback_data="send_location"
            )],
            [InlineKeyboardButton(
                text="✍️ Ввести новый адрес",
                callback_data="enter_new_address"
            )]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            f"✅ Клиент найден: {client['name']}\n\n"
            f"Выберите адрес доставки:",
            reply_markup=keyboard
        )
        await state.set_state(CourierCreateOrder.waiting_for_address_choice)
    else:
        await state.update_data(client_exists=False)
        await message.answer(
            f"📝 Новый клиент!\n"
            f"Имя будет создано автоматически: \"{validated_phone[-4:]}\"\n\n"
            f"Введите адрес доставки:\n"
            f"(или отправьте геолокацию)",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
                resize_keyboard=True
            )
        )
        await state.set_state(CourierCreateOrder.waiting_for_address_text)

# ... (продолжение в следующих шагах FSM)
```

---

## 7. Утилита валидации телефона

**Файл:** `tg_bot/utils/phone_validator.py`

```python
import re

def validate_uzbek_phone(phone: str) -> str:
    """
    Умная валидация узбекского номера телефона.
    
    Примеры:
        +998901234567 → +998901234567
        998901234567  → +998901234567
        901234567     → +998901234567
        90 123 45 67  → +998901234567
        8901234567    → +998901234567
    
    Raises:
        ValueError: Если номер невалиден
    """
    # Удаляем все символы кроме цифр и +
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Удаляем + в начале для обработки
    if phone.startswith('+'):
        phone = phone[1:]
    
    # Если начинается с 8, заменяем на 998
    if phone.startswith('8') and len(phone) == 10:
        phone = '998' + phone[1:]
    
    # Если начинается с 9 (без кода страны), добавляем 998
    if phone.startswith('9') and len(phone) == 9:
        phone = '998' + phone
    
    # Проверяем, что начинается с 998
    if not phone.startswith('998'):
        raise ValueError("Номер должен начинаться с +998")
    
    # Проверяем длину (998 + 9 цифр = 12)
    if len(phone) != 12:
        raise ValueError(f"Неверная длина номера (должно быть 12 цифр)")
    
    # Проверяем, что все символы — цифры
    if not phone.isdigit():
        raise ValueError("Номер должен содержать только цифры")
    
    return '+' + phone
```

---

## 8. Итоговый чеклист реализации

### Backend (Django):
- [ ] Добавить endpoint `GET /api/bot/courier/colleagues/` (статистика коллег)
- [ ] Добавить endpoint `POST /api/bot/courier/orders/create/` (создание заказа курьером)
- [ ] Добавить endpoint `GET /api/bot/clients/search/?phone=` (поиск клиента)
- [ ] Добавить поле `minutes_ago` в `OrderSerializer` (расчёт времени с создания)
- [ ] Реализовать логику автосоздания клиента (имя = последние 4 цифры)
- [ ] Реализовать логику обновления адреса существующего клиента

### Frontend (Telegram Bot):
- [ ] Создать `tg_bot/utils/phone_validator.py` (валидация телефона)
- [ ] Создать `tg_bot/states/courier.py` (FSM для создания заказа)
- [ ] Обновить `tg_bot/routers/courier.py`:
  - [ ] Хэндлер "📦 Пул заказов" (шапка + кнопки)
  - [ ] Хэндлер деталей заказа
  - [ ] Хэндлер "Взять заказ"
  - [ ] FSM создания заказа (7 шагов)
- [ ] Создать клавиатуры для выбора адреса, товаров, оплаты

### Тестирование:
- [ ] Тест валидации телефона (10+ вариантов ввода)
- [ ] Тест создания нового клиента
- [ ] Тест обновления адреса существующего клиента
- [ ] Тест создания многопозиционного заказа