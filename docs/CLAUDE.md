# CLAUDE.md — Архитектурный справочник проекта WERP / Osnova 2.0

## Связи
- [[]]

> **Для AI-помощников:** Этот файл — главный контекст проекта. Читай его перед любыми изменениями кода.
> Проект: ERP-система для компании по доставке питьевой воды (Самарканд, Узбекистан).
> Язык кода: Python/Django. Язык комментариев и переменных: русский + английский (mixed).

---

## 1. Архитектура проекта

### 1.1 Стек и зависимости

| Компонент         | Технология                   | Версия / Статус   |
| ----------------- | ---------------------------- | ----------------- |
| Backend framework | Django                       | 5.1.6 ✅          |
| REST API          | Django REST Framework (DRF)  | 3.15.2 ✅         |
| Telegram Bot      | Aiogram                      | 3.x (планируется) |
| Mini App фронтенд | React 18 + Vite              | планируется (P3)  |
| Стили Mini App    | Tailwind CSS                 | планируется (P3)  |
| Telegram SDK      | @twa-dev/sdk                 | планируется (P3)  |
| Веб-сервер        | Nginx + Gunicorn/Uvicorn     | планируется (P3)  |
| База данных       | PostgreSQL                   | 17 ✅             |
| Real-time         | Django Channels (WebSockets) | 4.1.0 ✅          |
| Channels Redis    | channels-redis               | 4.2.0 ✅          |
| Redis кэш         | django-redis                 | 5.4.0 ✅          |
| ASGI-сервер       | asgiref                      | 3.8.1 ✅          |
| Драйвер БД        | psycopg2                     | 2.9.10 ✅         |
| Работа с датами   | python-dateutil              | 2.9.0 ✅          |
| Генерация данных  | Faker                        | 37.0.0 ✅         |
| Генерация docx    | python-docx                  | 1.1.0 ✅          |
| Переменные среды  | python-dotenv                | 1.0.1 ✅          |

### 1.2 Структура приложений

```
apps/
├── clients/      — CRM: клиенты (ФИО, телефон, адрес, предоплата, геопозиция, tg_id)
├── products/     — Каталог товаров (вода, тара, кулеры, аксессуары)
├── workers/      — Сотрудники (курьеры, упаковщики)
├── warehouse/    — Склад: остатки, движения, автопарк, инвентаризация
├── logistics/    — Ядро: смены, рейсы, заказы (CourierShift → CourierTrip → Order)
├── accounting/   — Финансы: контракты, рассрочки, зарплаты, транзакции
└── bot_bridge/   — API-шлюз для Telegram-бота (DRF)
```

### 1.3 Граф зависимостей между модулями

```
products ←── warehouse ←── logistics ←── accounting
    ↑              ↑            ↑
clients         workers      clients
```

**Направление импортов (строгое правило):**
- `accounting` импортирует из `logistics`, `clients`, `products`, `workers`
- `warehouse` импортирует из `products`, `accounting`
- `logistics` импортирует из `workers`, `products`
- `clients`, `products`, `workers` — базовые модули, не импортируют из других apps

> ⚠️ ВАЖНО: `workers.models` импортирует `Garage` из `warehouse.models` — это циклическая зависимость. При рефакторинге нужно вынести `Garage` или использовать строковые ссылки.

### 1.4 Роль сигналов в системе

Сигналы — главный механизм автоматизации. Актуальная цепочка срабатывания при подтверждении заказа курьером:

```
Курьер подтверждает Order (status → DELIVERED)
        │
        ├─► [logistics/signals] post_save: recalculate_order_price
        │       price = product.price × quantity (если не задана вручную)
        │
        ├─► [logistics/signals] post_save: update_shift_totals_on_order
        │       if payment_type == CARD: shift.card_total += price
        │       else:                    shift.cash_total += price
        │       shift.save(update_fields=['cash_total', 'card_total'])
        │
        ├─► [warehouse/signals] post_save: update_stock_on_order
        │       PRODUCT_MAP: BOTTLE_20L → BOTTLE (подмена продукта)
        │       container_op EXCHANGE/SELL_WITH → списать BOTTLE со StockBalance
        │       container_op DEFECTIVE → НЕ списывать (брак возвращается)
        │       Создание записи StockMovement
        │
        └─► [accounting/signals] post_save: create_transaction_on_order
                FinancialTransactions(PLUS, amount=order.price, card_amount если CARD)
                Вызов utils.update_finance_record(date)
                Агрегация в модель Finance (income/consumption/profit/card_profit)
```

---

## 2. Что уже реализовано

### 2.1 `apps/clients` — CRM

**Модели:**
- `Client` — ФИО, телефон (unique), адрес, предоплата (balans), примечание, latitude, longitude, tg_id, created_at, updated_at

**Статус:** ✅ Полностью готово. Геопозиция и Telegram ID добавлены.

**Связи:** `Client` ← `Contract`, `Installment` (из accounting); `Client` ← `Order` (из logistics)

---

### 2.2 `apps/products` — Каталог товаров

**Модели:**
- `Product` — имя, тип, цена

**TypeProduct choices:**
```python
COOLERS   = "CL"   # Кулеры
ACCESSORY = 'AR'   # Аксессуары
WATER     = 'WE'   # Вода (без тары)
BOTTLE_20L = 'B20L' # Вода с тарой 20L (продаётся курьером)
BOTTLE    = 'BT'   # Тара (списывается со склада при продаже BOTTLE_20L)
```

**Ключевая логика:** При продаже `BOTTLE_20L` склад списывает `BOTTLE` (маппинг в `warehouse/signals.py`).

---

### 2.3 `apps/workers` — Сотрудники

**Модели:**
- `Worker` — ФИО, тип (PACKER/COURIER/OTHER), дата начисления зарплаты, note, created_at, updated_at

**Связи:** `Worker` ← `CourierShift` (logistics), `Salary` (accounting), `Garage` (warehouse, OneToOne)

> ⚠️ Техдолг: `workers/models.py` содержит `from apps.warehouse.models import Garage` — прямой импорт создаёт циклическую зависимость. Использовать строковую ссылку `'warehouse.Garage'` при рефакторинге.

---

### 2.4 `apps/warehouse` — Склад и автопарк

**Модели:**
- `StockBalance` — остаток продукта на складе (product FK, quantity, last_received_date, last_departure_date)
- `StockMovement` — лог движений (BUY/SELL, product FK, contract FK, quantity, note)
- `Garage` — автомобиль (vehicle_name, plate_number, milage, year, courier OneToOne → Worker)
- `InventoryAdjustment` — ручная корректировка остатков (product FK, adjustment_type: INC/DEC/SET, quantity, reason, adjusted_by FK → Worker)

**Сигналы (`warehouse/signals.py`):**
- `post_save(Product)` → `create_stock_balance_product`: авто-создание `StockBalance` при новом продукте
- `post_save(Order)` → `update_stock_on_order`: списание тары по PRODUCT_MAP (BOTTLE_20L → BOTTLE), логика по `container_op`
- `pre_save(SubjectContract)` → `track_subject_contract_changes`: отслеживание изменений контракта
- `post_save(SubjectContract)` / `pre_delete(SubjectContract)` → движения склада по контрактам

**Логика `InventoryAdjustment.save()`:** при сохранении автоматически обновляет `StockBalance` и создаёт запись `StockMovement` для аудита.

---

### 2.5 `apps/logistics` — Ядро доставок (НОВАЯ АРХИТЕКТУРА)

**Иерархия моделей:** `CourierShift` → `CourierTrip` → `Order`

**Модели:**

**`CourierShift` (Смена курьера):**
- `courier` FK → Worker
- `date` DateField (auto_now_add)
- `status` choices: OPEN/CLOSED
- `cash_total` IntegerField (default=0) — наличные за смену
- `card_total` IntegerField (default=0) — безнал за смену
- `opened_at` DateTimeField (auto_now_add)
- `closed_at` DateTimeField (null=True)
- Метод `close()` — устанавливает status=CLOSED, closed_at=now()

**`CourierTrip` (Рейс внутри смены):**
- `shift` FK → CourierShift (related_name='trips')
- `full_loaded` IntegerField — загружено полных баклажек
- `full_returned` IntegerField (default=0) — возвращено полных (недоставленных)
- `status` choices: ACTIVE/DONE
- `started_at` DateTimeField (auto_now_add)
- `finished_at` DateTimeField (null=True)
- Метод `get_trip_summary() → dict` — возвращает: full_loaded, delivered, full_returned, full_remain, empty_received, defective_received

**`Order` (Заказ — строка рейса, многопозиционный):**
- `trip` FK → CourierTrip (related_name='orders', null=True — заказ клиента до назначения курьера)
- `client` FK → Client (SET_NULL, null=True)
- `assigned_courier` FK → Worker (SET_NULL, null=True) — назначенный курьер
- `payment_type` choices: CASH/CARD/BONUS
- `status` choices: PENDING/DELIVERED/CANCELLED
- `note` CharField (null=True)
- `created_at` DateTimeField (auto_now_add)
- `delivered_at` DateTimeField (null=True)
- Метод `get_total_price() → int` — сумма всех `OrderItem.price`

> ⚠️ Поля `product`, `quantity`, `price`, `container_op` **удалены** из `Order` (миграция 0004). Они перенесены в модель `OrderItem`.

**`OrderItem` (Позиция заказа — новая модель P3.7):**
- `order` FK → Order (related_name='items')
- `product` FK → Product
- `quantity` IntegerField (default=1)
- `price` IntegerField (null=True) — авто-расчёт в `pre_save`: price = product.price × quantity
- `exchange_qty` IntegerField (default=0) — обмен тары (возврат пустой)
- `sell_with_qty` IntegerField (default=0) — продажа с тарой
- `defective_qty` IntegerField (default=0) — брак тары

**Логика учёта тары (через поля `OrderItem`):**

| Поле | Действие со складом | Результат в машине |
|---|---|---|
| `exchange_qty > 0` | Списать BOTTLE × exchange_qty | +exchange_qty пустых в машину |
| `sell_with_qty > 0` | Списать BOTTLE × sell_with_qty | 0 пустых |
| `defective_qty > 0` | НЕ списывать (брак возвращается) | +defective_qty бракованных |

**Устаревшие модели:**
- `DeliveryLog`, `DeliveryLogMove`, `DeliveryJournal` — **полностью удалены** из кода и БД
  (миграция `logistics.0010_remove_legacy_models`). Источник правды — `CourierShift → CourierTrip → Order → OrderItem`.

**Сигналы (`logistics/signals.py`):**
- `pre_save(OrderItem)` → `recalculate_order_price`: пересчёт `price = product.price × quantity` если не задана вручную или изменилось quantity
- `post_save(Order)` → `update_shift_totals_on_order`: **агрегация** (не инкремент!) cash_total/card_total в CourierShift при status=DELIVERED — пересчитывает через `OrderItem` все DELIVERED заказы смены

---

### 2.6 `apps/accounting` — Финансы

**Модели:**
- `Contract` — контракт (BUY=расход / SELL=доход, client FK, amount, file)
- `SubjectContract` — предмет контракта (contract FK, product FK, quantity, note)
- `Installment` — рассрочка (client FK, product FK, amount, paid_amount, status: ACTIVE/OVERDUE/CLOSED)
- `PaymentsInstallment` — платёж по рассрочке (installment FK, amount, payment_date)
- `Salary` — баланс зарплаты сотрудника (worker FK, balance, last_payment)
- `SalaryPayment` — платёж зарплаты (salary FK, amount, payment_type: SALARY/FINE/BONUS, date)
- `FinancialTransactions` — лог всех денежных операций (date, type: PLUS/MINUS, amount, card_amount, source)
- `Finance` — дневная сводка (income, consumption, profit, card_profit, date)

**Утилиты (`accounting/utils.py`):**
- `update_due_date(installment)` — следующий платёж = последний + 1 месяц
- `reset_balance_if_expired(salary)` — обнуление баланса если >30 дней с последней зарплаты
- `update_finance_record(date)` — агрегация транзакций за дату в `Finance`

**Сигналы (`accounting/signals.py`):**
- `Contract` pre/post_save/delete → создание/удаление `FinancialTransactions` + `update_finance_record`
- `Order` post_save (status=DELIVERED) → `create_transaction_on_order`: создание `FinancialTransactions(PLUS)` + `update_finance_record`
- `SalaryPayment` pre/post_save/delete → создание `FinancialTransactions` + `update_finance_record`
- `PaymentsInstallment` pre/post_save/delete → создание `FinancialTransactions` + `update_finance_record`
- `FinancialTransactions` pre/post_save → `update_finance_record` (при изменении даты — обновляет обе даты)

**⚠️ Известная проблема (P1):** `update_finance_record` считает `card_profit = sum(t.card_amount for t in ALL transactions)` — суммирует card_amount даже для MINUS-транзакций. Нужно фильтровать только PLUS-транзакции.

---

## 3. Roadmap: что делать дальше

> **Статус выполнения:** P0 ✅, P1 ✅, P2 ✅. Текущий приоритет: P4 → P5 → P6.

### [P0 — ✅ ВЫПОЛНЕНО] Система Смен и Рейсов

> Переход от `DeliveryJournal` к `CourierShift → CourierTrip → Order` завершён. Модели, сигналы и bot_bridge API реализованы. Описание моделей — в разделе 2.5.

**Что было сделано:**
1. ✅ Добавлены модели `CourierShift`, `CourierTrip`, `Order` в `apps/logistics/models.py`
2. ✅ Написаны сигналы: `recalculate_order_price`, `update_shift_totals_on_order` (logistics), `update_stock_on_order` (warehouse), `create_transaction_on_order` (accounting)
3. ✅ Создан `bot_bridge` API: открытие смены, рейса, подтверждение доставки, закрытие
4. ✅ Миграции применены

**Что осталось (техдолг):**
- ✅ Устаревшие модели `DeliveryLog`, `DeliveryLogMove`, `DeliveryJournal` удалены из кода, сигналов и админки. Таблицы удалены миграцией `logistics.0010_remove_legacy_models`.

---

### [P1 — ✅ ВЫПОЛНЕНО] Добавить геопозицию и Telegram ID в модель Client

**Что сделано:** Поля `latitude`, `longitude` (DecimalField) и `tg_id` (BigIntegerField, unique) добавлены в `Client`.

---

### [P1] Исправить баг в `update_finance_record` (card_profit)

**Что делать:** В `accounting/utils.py` строка `card_profit = sum(t.card_amount for t in transactions)` суммирует card_amount для всех транзакций. Нужно считать только для PLUS-транзакций.

**Файлы:**
- `apps/accounting/utils.py` — строка 33

**Зависимости:** нет

---

### [P2] Создать приложение `bot_bridge`

**Что делать:** Новое Django-приложение как API-шлюз между Telegram-ботом и Django.

**Файлы для создания:**
- `apps/bot_bridge/__init__.py`
- `apps/bot_bridge/apps.py`
- `apps/bot_bridge/serializers.py` — сериализаторы для Order, CourierShift, CourierTrip, Client, Product
- `apps/bot_bridge/views.py` — APIView: открытие смены, начало рейса, подтверждение доставки, закрытие рейса/смены
- `apps/bot_bridge/urls.py` — маршруты API
- `apps/bot_bridge/permissions.py` — авторизация курьера по tg_id

**Зависимости:** P1 (tg_id в Client), P0 (новые модели), DRF должен быть установлен

---

### [P2] API эндпоинты для курьера (бонусы/штрафы)

**Что делать:** DRF endpoint для получения курьером своего баланса зарплаты.

**Файлы:**
- `apps/accounting/serializers.py` — создать
- `apps/accounting/views.py` — добавить SalaryDetailView
- `apps/accounting/urls.py` — создать

**Зависимости:** bot_bridge (P2), DRF

---

### [P2] Генератор путевых листов (docx)

**Что делать:** Функция в `warehouse/utils.py`, принимающая `courier_id` и `date`, генерирующая `.docx` файл с данными из `Garage` и `CourierTrip`.

**Файлы:**
- `apps/warehouse/utils.py` — создать, функция `generate_waybill(courier_id, date) -> bytes`
- `requirements.txt` — добавить `python-docx`

**Зависимости:** P0 (новые модели)

---

### [P2] Инвентаризация склада через админку

**Что делать:** Добавить модель `InventoryAdjustment` для ручной корректировки остатков с обязательным полем `reason`. Зарегистрировать в admin.

**Файлы:**
- `apps/warehouse/models.py` — добавить модель `InventoryAdjustment`
- `apps/warehouse/signals.py` — сигнал post_save для обновления StockBalance
- `apps/warehouse/admin.py` — регистрация
- `apps/warehouse/migrations/` — миграция

**Зависимости:** нет

---

### [P3] WebSockets — живой мониторинг

**Что делать:** Django Channels consumer, который при каждом `post_save` в `FinancialTransactions` отправляет обновлённые данные Finance в WebSocket-группу `dashboard`.

**Файлы:**
- `apps/accounting/consumers.py` — создать `DashboardConsumer`
- `apps/accounting/routing.py` — WebSocket URL routing
- `config/asgi.py` — подключить Channels
- `requirements.txt` — добавить `channels`, `channels-redis`

**Зависимости:** Redis должен быть запущен

---

### [P3] Telegram Mini App (TWA) — три профиля: курьер, клиент, админ

> **Цель:** Единый Telegram-бот на aiogram 3.x с тремя ролевыми профилями, каждый открывает свой Mini App (TWA). Бот — точка входа и авторизации; вся бизнес-логика остаётся в Django через bot_bridge API.

---

#### 3.1 Архитектура бота (aiogram 3.x)

```
tg_bot/
├── __main__.py              — точка входа, запуск polling / webhook
├── bot.py                   — создание Bot и Dispatcher
├── config.py                — настройки (BOT_TOKEN, DJANGO_API_URL, MINI_APP_URL)
├── middlewares/
│   └── auth.py              — определение роли пользователя по tg_id через API
├── routers/
│   ├── courier.py           — хэндлеры для курьера
│   ├── client.py            — хэндлеры для клиента
│   └── admin.py             — хэндлеры для администратора
└── keyboards/
    ├── courier.py           — клавиатуры курьера (inline + reply)
    ├── client.py            — клавиатуры клиента
    └── admin.py             — клавиатуры администратора
```

**Авторизация и определение роли:**
- При старте (`/start`) бот отправляет `GET /api/bot/identify/?tg_id=<id>` → Django возвращает роль: `courier` / `client` / `admin` / `unknown`
- Middleware сохраняет роль в `FSMContext` / `data` для каждого апдейта
- Новый пользователь (`unknown`) → предложение зарегистрироваться как клиент

**Добавить в `Worker`:**
```python
tg_id = models.BigIntegerField(null=True, blank=True, unique=True, verbose_name='Telegram ID')
```
> ⚠️ Сейчас `tg_id` есть только у `Client`. Для идентификации курьеров нужно добавить поле `tg_id` в `Worker`.

**Новый endpoint идентификации** (`bot_bridge/views.py`):
```python
# GET /api/bot/identify/?tg_id=<id>
# Проверяет: Worker.tg_id → role=courier, Worker.is_admin → role=admin, Client.tg_id → role=client
# Ответ: {"role": "courier"|"client"|"admin"|"unknown", "name": "...", "id": ...}
```

---

#### 3.2 Профиль «Курьер» — Mini App пула заказов

**Что видит курьер в боте:**
- Кнопка «Открыть рабочий стол» → открывает TWA курьера
- Inline-уведомления: новый заказ в пул, статус рейса

**Mini App курьера (React/Vue SPA, размещается на отдельном домене или в `static/`):**

```
Экраны Mini App курьера:
├── Главный экран
│   ├── Статус смены (OPEN / нет смены)
│   ├── Кнопка «Открыть смену» (если нет активной)
│   └── Кнопка «Открыть рейс» (если смена открыта)
│
├── Пул заказов (таблица)
│   ├── Колонки: # | Клиент | Адрес | Продукт | Кол-во | Тип оплаты | Статус
│   ├── Фильтр: PENDING / все
│   ├── Взять заказ → POST /api/bot/courier/order/<id>/assign/
│   └── Отмена взятого заказа
│
├── Мой рейс (активный CourierTrip)
│   ├── Счётчики:
│   │   ├── Загружено полных (full_loaded)
│   │   ├── Доставлено (delivered count)
│   │   ├── Остаток полных в машине (full_loaded - delivered - full_returned)
│   │   ├── Пустых в машине (empty_received из EXCHANGE-заказов)
│   │   └── Брак (defective_received из DEFECTIVE-заказов)
│   ├── Сколько должно быть пустых баклажек (расчёт: кол-во EXCHANGE заказов в рейсе)
│   ├── Наличных должно быть в кармане (sum CASH-заказов со статусом DELIVERED)
│   ├── По карте должно быть (sum CARD-заказов со статусом DELIVERED)
│   └── Список заказов рейса с возможностью подтвердить каждый
│
├── Подтверждение заказа (форма)
│   ├── Выбор container_op: ОБМЕН / ПРОДАЖА С ТАРОЙ / БРАК
│   ├── Тип оплаты (cash/card/bonus)
│   ├── Примечание
│   └── Кнопка «Доставлено» → PATCH /api/bot/orders/<id>/deliver/
│
├── Смены и рейсы (история)
│   ├── Список своих CourierShift (дата, статус, наличные, безнал)
│   └── По клику → список CourierTrip → список Order
│
└── Таблица «Мои коллеги» (другие курьеры)
    ├── ФИО | Статус смены | Кол-во доставлено сегодня | Телефон (из Worker)
    └── Только для курьеров со статусом OPEN сегодня
```

**Новые API endpoints для курьерского Mini App** (`bot_bridge/views.py`):

```python
# --- Пул заказов ---
# GET  /api/bot/courier/pool/          — PENDING заказы без назначенного курьера или все рейса
# POST /api/bot/courier/order/<id>/assign/  — взять заказ (добавить в свой активный trip)

# --- Текущий рейс ---
# GET  /api/bot/courier/trip/current/  — активный CourierTrip + его заказы + summary
# Расчётные поля в ответе:
#   empty_expected  = кол-во EXCHANGE заказов в рейсе
#   cash_expected   = сумма CASH DELIVERED заказов
#   card_expected   = сумма CARD DELIVERED заказов

# --- Коллеги ---
# GET  /api/bot/courier/colleagues/    — курьеры с открытой сменой сегодня
```

> **Примечание по пулу заказов:** В текущей архитектуре заказы создаются диспетчером и уже привязаны к рейсу. Для реального пула нужно добавить промежуточный статус: `Order.status = POOL` (не назначен курьеру). Или пул = PENDING заказы клиентов (созданные через клиентский Mini App), которые диспетчер / курьер берёт в рейс.

---

#### 3.3 Профиль «Клиент» — Mini App каталога и заказов

**Что видит клиент в боте:**
- Приветствие с именем из `Client.name`
- Кнопка «Каталог и заказ» → открывает TWA клиента
- Уведомление о статусе заказа (через bot.send_message при изменении Order.status)

**Mini App клиента (React/Vue SPA):**

```
Экраны Mini App клиента:
├── Каталог товаров
│   ├── Список Product (тип, название, цена)
│   ├── Карточка товара: фото (если есть), описание, цена
│   └── Кнопка «Заказать»
│
├── Оформление заказа
│   ├── Выбор количества
│   ├── Тип оплаты (CASH / CARD)
│   ├── Адрес (подтягивается из Client, можно изменить)
│   └── Кнопка «Подтвердить» → POST /api/bot/client/order/
│
└── Мои заказы
    ├── История заказов клиента (Order по client.tg_id)
    └── Статус: PENDING (ожидает) | DELIVERED (доставлен) | CANCELLED
```

**Уведомление клиенту при доставке** (отправляется из Django через Webhook или отдельный сервис):
```
Курьер принял ваш заказ:
  Курьер: Иван Иванов
  Телефон: +998901234567
  Заказ: Вода 20л × 2 шт.
  Статус: В пути 🚚
```

**Новые API endpoints для клиентского Mini App**:
```python
# GET  /api/bot/client/products/           — каталог товаров (только WATER, BOTTLE_20L)
# POST /api/bot/client/order/              — создать заказ (status=PENDING, trip=None до назначения)
# GET  /api/bot/client/orders/             — история заказов клиента (by tg_id)
# GET  /api/bot/client/order/<id>/status/  — текущий статус + информация о курьере если DELIVERED
```

**Добавить в `Order`:**
```python
assigned_courier = models.ForeignKey(
    'workers.Worker', null=True, blank=True,
    on_delete=models.SET_NULL, related_name='assigned_orders',
    verbose_name='Назначенный курьер'
)
```
> Это поле нужно для отображения клиенту информации о курьере при доставке.

**Уведомление реализуется через** `bot_bridge/notify.py`:
```python
# async def notify_client_order_accepted(order: Order):
#     """Отправляет tg-уведомление клиенту когда курьер взял заказ"""
#     # bot.send_message(client.tg_id, text=...)
```

---

#### 3.4 Профиль «Администратор» — мини-статистика из Django Admin

**Что видит администратор в боте:**
- Кнопки быстрого доступа: «Статистика сегодня», «Активные смены», «Склад»
- Открыть TWA admin (опционально) или получить данные прямо в чате

**Команды администратора в боте:**
```
/stats        — сводка за сегодня (Finance: доход, расход, прибыль, безнал)
/shifts       — список активных смен сегодня (курьер, наличные, безнал, заказов)
/stock        — топ-5 позиций склада с критическими остатками (quantity < 10)
/orders       — последние 10 заказов (клиент, сумма, статус, курьер)
```

**Inline-кнопки в сообщении `/stats`:**
```
[ Смены сегодня ] [ Склад ] [ Финансы за неделю ]
```

**Ответ на `/stats` (форматированный текст, без TWA):**
```
📊 Сводка за 05.05.2026
━━━━━━━━━━━━━━━━
💰 Доход:    1 250 000 сум
📉 Расход:     180 000 сум
✅ Прибыль:  1 070 000 сум
💳 Безнал:     320 000 сум
━━━━━━━━━━━━━━━━
🚚 Активных смен: 3
📦 Заказов выполнено: 47
```

**Новые API endpoints для admin-профиля**:
```python
# GET /api/bot/admin/stats/today/   — Finance за сегодня + кол-во активных смен + заказов
# GET /api/bot/admin/shifts/        — активные CourierShift с courier, cash_total, card_total
# GET /api/bot/admin/stock/alerts/  — StockBalance где quantity < 10
# GET /api/bot/admin/orders/recent/ — последние N заказов
```

**Авторизация администратора:** Добавить флаг `is_admin` в модель `Worker`:
```python
is_admin = models.BooleanField(default=False, verbose_name='Администратор бота')
```

---

#### 3.5 Фронтенд Mini App — полное руководство для бэкендера

> ⚠️ **Контекст для AI:** Разработчик проекта — бэкендер на Python/Django. В проекте нет ни одного файла фронтенда. Этот раздел — полная инструкция с нуля: что установить, что создать, как связать с Django. AI должен создавать фронтенд-файлы самостоятельно, не ожидая что они уже существуют.

---

##### Что такое TWA (Telegram Web App) — кратко

TWA (Telegram Web App / Mini App) — это обычная веб-страница (HTML + JS + CSS), которая открывается **внутри Telegram** как модальное окно. Для пользователя это выглядит как нативное приложение. Telegram предоставляет JS SDK (`window.Telegram.WebApp`) для взаимодействия с ботом.

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

**Жёсткое требование Telegram:** URL Mini App **обязан** работать по HTTPS. На локальной разработке — использовать ngrok или Cloudflare Tunnel.

---

##### Выбранный стек фронтенда (рекомендация для этого проекта)

| Компонент | Технология | Зачем |
|-----------|-----------|-------|
| Фреймворк | **React 18** (через Vite) | Компонентный подход, большое сообщество |
| Сборщик | **Vite** | Быстрая сборка, простая настройка, `npm run build` → статика |
| Стили | **Tailwind CSS** | Утилитарные классы, не надо писать CSS вручную |
| Telegram SDK | `@twa-dev/sdk` | TypeScript-обёртка над `window.Telegram.WebApp` |
| HTTP-клиент | `fetch` (встроенный) | Запросы к Django DRF API |
| Хостинг | **Статика через Django + Nginx** | Нет отдельного сервера, всё в одном месте |

---

##### Структура фронтенд-проекта (создать рядом с Django)

```
корень проекта/
├── WERP_system/          — Django settings
├── apps/                 — Django apps
├── manage.py
├── static/               — статика Django
│
└── frontend/             — ВСЁ НОВОЕ: фронтенд Mini App
    ├── courier/          — Mini App для курьера
    │   ├── package.json
    │   ├── vite.config.js
    │   ├── index.html         — точка входа (Vite заполняет автоматически)
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

---

##### Пошаговая инструкция: создать Mini App курьера с нуля **POWERSHELL**

**Шаг 1 — Установить Node.js** (если не установлен) 
```bash
# Проверить наличие:
node --version   # нужен v18+
npm --version

# Установка на Ubuntu/Debian:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**Шаг 2 — Создать Vite + React проект**
```bash
cd /путь/к/проекту/frontend
npm create vite@latest courier -- --template react
cd courier
npm install
```

**Шаг 3 — Установить зависимости**
```bash
npm install @twa-dev/sdk        # Telegram WebApp SDK
npm install react-router-dom    # роутинг между страницами
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Шаг 4 — Настроить Tailwind** (`tailwind.config.js`):
```js
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: { extend: {} },
  plugins: [],
}
```
Добавить в `src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Шаг 5 — Настроить Vite** (`vite.config.js`):
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // base — путь где будет лежать собранное приложение
  // если раздаёт Django по /static/miniapp/courier/ то:
  base: '/static/miniapp/courier/',
  build: {
    outDir: '../../static/miniapp/courier',  // сборка прямо в Django static
    emptyOutDir: true,
  }
})
```

**Шаг 6 — Создать `src/tg.js`** (инициализация Telegram SDK):
```js
import WebApp from '@twa-dev/sdk'

// Вызывать один раз при старте приложения
export function initTelegram() {
  WebApp.ready()          // сообщить Telegram что приложение загрузилось
  WebApp.expand()         // раскрыть на весь экран
}

// tg_id текущего пользователя — использовать в каждом API запросе
export const tgUser = WebApp.initDataUnsafe?.user
export const tgId = tgUser?.id
export const initData = WebApp.initData  // подписанная строка — для авторизации на сервере
```

**Шаг 7 — Создать `src/api.js`** (запросы к Django):
```js
import { initData, tgId } from './tg.js'

const BASE_URL = import.meta.env.VITE_API_URL  // берётся из .env файла

async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-ID': tgId,           // идентификация курьера
      'X-Telegram-Init-Data': initData, // валидация на сервере
      ...options.headers,
    },
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  getPool:        ()       => apiFetch('/api/bot/courier/pool/'),
  getCurrentTrip: ()       => apiFetch('/api/bot/courier/trip/current/'),
  deliverOrder:   (id, data) => apiFetch(`/api/bot/orders/${id}/deliver/`, {
    method: 'PATCH', body: JSON.stringify(data)
  }),
  getColleagues:  ()       => apiFetch('/api/bot/courier/colleagues/'),
  getShifts:      ()       => apiFetch('/api/bot/courier/shifts/'),
  openShift:      ()       => apiFetch('/api/bot/shifts/', { method: 'POST' }),
  openTrip:       (data)   => apiFetch('/api/bot/trips/', { method: 'POST', body: JSON.stringify(data) }),
}
```

**Шаг 8 — Создать `.env` файл** (в папке `frontend/courier/`):
```
VITE_API_URL=https://yourdomain.com
```
> На локальной разработке: `VITE_API_URL=https://xxxx.ngrok.io` (через ngrok)

**Шаг 9 — Собрать и раздать через Django**
```bash
cd frontend/courier
npm run build
# → файлы появятся в static/miniapp/courier/
```
Django автоматически раздаёт всё из `STATICFILES_DIRS`. URL: `https://yourdomain.com/static/miniapp/courier/index.html`

---

##### Как Django узнаёт кто делает запрос (авторизация TWA)

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

---

##### Nginx — как раздать и Django, и Mini App по HTTPS

> **Контекст:** Без Nginx в продакшене не обойтись — Telegram требует HTTPS, а Django `runserver` не поддерживает SSL. Nginx терминирует SSL и проксирует запросы к Django (Gunicorn/Uvicorn).

**Схема:**
```
Интернет → Nginx (порт 443, SSL) → Gunicorn (порт 8000, Django)
                │
                └─► /static/ → Django collectstatic папка (статика без Python)
```

**Конфигурация `/etc/nginx/sites-available/werp`:**
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Статика Django (включает собранные Mini App)
    location /static/ {
        alias /путь/к/проекту/staticfiles/;  # после python manage.py collectstatic
        expires 7d;
        add_header Cache-Control "public";
    }

    # Медиафайлы (контракты)
    location /media/ {
        alias /путь/к/проекту/media/;
    }

    # Все остальные запросы → Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        # WebSockets (для Django Channels)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Редирект HTTP → HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}
```

**SSL сертификат (бесплатно через Let's Encrypt):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

**Django collectstatic** (собрать всю статику в одну папку для Nginx):
```bash
python manage.py collectstatic --noinput
# → все файлы из static/ и приложений попадут в staticfiles/
```

Добавить в `settings.py`:
```python
STATIC_ROOT = BASE_DIR / 'staticfiles'   # куда collectstatic кладёт файлы
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] # исходная папка (твоя + собранные Mini App)
```

---

##### Локальная разработка TWA (без домена)

Telegram не открывает `localhost`. Нужен публичный HTTPS-туннель:

```bash
# Вариант 1: ngrok (проще)
npm install -g ngrok
ngrok http 8000
# → получишь https://xxxx.ngrok.io → вставь в .env и в настройки бота

# Вариант 2: Cloudflare Tunnel (стабильнее, бесплатно)
cloudflared tunnel --url http://localhost:8000
```

В aiogram-боте URL кнопки Mini App:
```python
from aiogram.types import InlineKeyboardButton, WebAppInfo

button = InlineKeyboardButton(
    text="Открыть рабочий стол",
    web_app=WebAppInfo(url="https://xxxx.ngrok.io/static/miniapp/courier/index.html")
)
```

---

##### Порядок действий при реализации P3 (для AI)

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
```

---

#### 3.6 Файлы для создания/изменения (P3 полный список)

**Django backend:**
```
apps/bot_bridge/
├── views.py             — дополнить: identify, courier pool/trip/colleagues, client orders, admin stats
├── serializers.py       — дополнить: CourierPoolSerializer, TripSummarySerializer, ClientOrderSerializer
├── permissions.py       — дополнить: TelegramInitDataPermission (валидация TWA initData)
├── notify.py            — создать: async функции отправки уведомлений через бот
└── urls.py              — дополнить: все новые маршруты

apps/workers/models.py   — добавить поля: tg_id, is_admin в Worker
apps/logistics/models.py — добавить поле: assigned_courier в Order (optional)
```

**Telegram bot:**
```
tg_bot/
├── __main__.py
├── bot.py
├── config.py
├── middlewares/auth.py
├── routers/courier.py
├── routers/client.py
├── routers/admin.py
├── keyboards/courier.py
├── keyboards/client.py
└── keyboards/admin.py

requirements_bot.txt     — aiogram>=3.0, aiohttp, python-dotenv
```

**Mini App frontend (отдельный репозиторий или папка `frontend/`):**
```
frontend/
├── courier/             — Vite + React
│   └── src/
│       ├── pages/Pool.jsx, Trip.jsx, Shifts.jsx, Colleagues.jsx
│       ├── components/OrderCard.jsx, TripSummary.jsx
│       └── api/client.js  — fetch-обёртка с X-Telegram-ID заголовком
└── client/              — Vite + React
    └── src/
        ├── pages/Catalog.jsx, OrderForm.jsx, MyOrders.jsx
        └── api/client.js
```

**Зависимости P3:**
- P0 (модели CourierShift, CourierTrip, Order)
- P1 (Client.tg_id)
- P2 (bot_bridge API, DRF)
- Redis (для Channels, уже в стеке)
- aiogram 3.x установлен в bot-окружении
- Mini App хостится на HTTPS (требование Telegram)

---
#### 3.7 Рефакторинг ядра бэкенда: Переход на структуру OrderItem и перенос логики заказов

**Цель:** Переписать архитектуру базы данных и бизнес-логику с однотоварных заказов на многопозиционные (один заказ = много товаров в рамках одного визита). Отключить старый эндпоинт создания заказа клиентом на уровне API.

##### 1. Изменения в моделях (`apps/logistics/models.py`)

- **`Order`**: Полностью удалить поля `product`, `quantity`, `price`, `container_op`. Вместо них реализовать метод или свойство `get_total_price(self)` для динамического подсчета стоимости заказа на основе связанных позиций (`sum(item.price for item in self.items.all())`).
    
- **`OrderItem`** (Новая модель позиций заказа):
    ```
    class OrderItem(models.Model):
        order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='Заказ')
        product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name='Продукт')
        quantity = models.IntegerField(default=1, verbose_name='Количество')
        price = models.IntegerField(null=True, blank=True, verbose_name='Цена за позицию') # Авто-расчет: product.price * quantity
    
        # Специфические поля для учета тары (актуально только для продуктов с type == 'B20L')
        exchange_qty = models.IntegerField(default=0, verbose_name='Обмен тары (возврат)')
        sell_with_qty = models.IntegerField(default=0, verbose_name='Продажа с тарой')
        defective_qty = models.IntegerField(default=0, verbose_name='Брак тары')
    ```
    

##### 2. Рефакторинг цепочки сигналов (Бизнес-логика)

Так как автоматизация в проекте завязана на `post_save` заказа, логику обработчиков необходимо адаптировать под новую структуру данных:

- **`recalculate_order_price`** (`logistics/signals.py`): Перевести на `pre_save` модели **`OrderItem`**. Сигнал должен вычислять `product.price * quantity` и сохранять результат в `item.price` перед записью в БД.
    
- **`update_shift_totals_on_order`** (`logistics/signals.py`): Оставить на модели `Order` (срабатывает при изменении статуса заказа на `DELIVERED`), но теперь он берет агрегированную сумму всех позиций через `order.get_total_price()` и прибавляет её к финансовым итогам смены (`shift.cash_total` или `shift.card_total`).
    
- **`update_stock_on_order`** (`apps/warehouse/signals.py`): Переписать логику списания. При `Order.status == DELIVERED` сигнал должен запускать цикл по всем связанным `items`. Если у `item.product.type == 'B20L'` (Вода 20л), то склад списывает со склада/машины базовый продукт `BOTTLE` в количестве `exchange_qty + sell_with_qty`, а `defective_qty` приходует как брак. Для остальных типов продуктов списывается просто `quantity`.
    
- **`create_transaction_on_order`** (`apps/accounting/signals.py`): Срабатывает при закрытии `Order`, использует финальный `order.get_total_price()` для создания финансовой транзакции `FinancialTransactions(PLUS)`.
    

##### 3. Изменения в API-слое (`apps/bot_bridge`)

- **`serializers.py`**:
    
    - Создать `OrderItemSerializer` для сериализации позиций (включая поля тары).
        
    - Обновить `OrderSerializer`, добавив в него вложенный серилизатор позиций: `items = OrderItemSerializer(many=True, read_only=True)`.
        
- **`views.py`**:
    
    - **Отключение клиента:** Полностью удалить или заблокировать эндпоинт `POST /api/bot/client/order/` на уровне ViewSet/URL.
        
    - **Пул заказов:** Обновить эндпоинт создания заказа в пуле (`POST /api/bot/orders/`). Теперь он должен принимать ID клиента и массив `items` (список объектов с `product_id` и `quantity`), программно создавая `Order` и пачку `OrderItem`.
        
    - **Закрытие заказа:** Обновить эндпоинт подтверждения доставки (`PATCH /api/bot/orders/<id>/deliver/`). Теперь в теле запроса бэкенд ожидает массив данных по позициям (для каждой позиции передаются финальные `exchange_qty`, `sell_with_qty`, `defective_qty`).
        

**Файлы для изменения (Исключительно бэкенд):**

- `apps/logistics/models.py` (модификация `Order`, добавление `OrderItem`)
    
- `apps/logistics/signals.py` (перерасчет цен и обновление итогов смен)
    
- `apps/warehouse/signals.py` (построчный пересчет остатков тары)
    
- `apps/accounting/signals.py` (проводка транзакций по агрегированной стоимости)
    
- `apps/bot_bridge/serializers.py` (вложенные сериализаторы)
    
- `apps/bot_bridge/views.py` (изменение логики POST и PATCH запросов для заказов)
    

**Миграции:**

- Удалить старые тестовые заказы в БД перед миграцией, так как поля `product` и `quantity` удаляются из таблицы `Order`.
    
- Выполнить: `python manage.py makemigrations logistics` и `python manage.py migrate`.
### [P4] Подключение URL-маршрутов для всех приложений

> **Цель:** Каждое приложение должно иметь собственный `urls.py` и быть подключено в `WERP_system/urls.py`. Это необходимо для работы Django Admin, DRF API и будущих веб-страниц.

#### 4.1 Структура URL-пространства

```
/                          — корень (редирект на /admin/ или /dashboard/)
/admin/                    — Django Admin (уже подключён)
/api/bot/                  — bot_bridge API (уже подключён)
/api/accounting/           — accounting API (уже подключён)
/api/logistics/            — logistics API (новый)
/api/warehouse/            — warehouse API (новый)
/api/clients/              — clients API (новый)
/api/workers/              — workers API (новый)
/api/products/             — products API (новый)
/dashboard/                — веб-интерфейс (P6, новый)
/media/                    — медиафайлы (контракты)
```

#### 4.2 Файлы для создания/изменения

**`WERP_system/urls.py` — главный роутер:**
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # API для Telegram бота
    path('api/bot/', include('apps.bot_bridge.urls')),

    # API модулей
    path('api/accounting/', include('apps.accounting.urls')),
    path('api/logistics/', include('apps.logistics.urls')),
    path('api/warehouse/', include('apps.warehouse.urls')),
    path('api/clients/', include('apps.clients.urls')),
    path('api/workers/', include('apps.workers.urls')),
    path('api/products/', include('apps.products.urls')),

    # DRF авторизация
    path('api-auth/', include('rest_framework.urls')),

    # Веб-дашборд (P6)
    path('', include('apps.dashboard.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Новые `urls.py` для каждого приложения:**

`apps/logistics/urls.py`:
```python
from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # CourierShift
    path('shifts/', views.ShiftListView.as_view(), name='shift-list'),
    path('shifts/<int:pk>/', views.ShiftDetailView.as_view(), name='shift-detail'),
    path('shifts/<int:pk>/close/', views.ShiftCloseView.as_view(), name='shift-close'),

    # CourierTrip
    path('trips/', views.TripListView.as_view(), name='trip-list'),
    path('trips/<int:pk>/', views.TripDetailView.as_view(), name='trip-detail'),
    path('trips/<int:pk>/summary/', views.TripSummaryView.as_view(), name='trip-summary'),
    path('trips/<int:pk>/close/', views.TripCloseView.as_view(), name='trip-close'),

    # Order
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/deliver/', views.OrderDeliverView.as_view(), name='order-deliver'),
]
```

`apps/warehouse/urls.py`:
```python
from django.urls import path
from . import views

app_name = 'warehouse'

urlpatterns = [
    path('stock/', views.StockBalanceListView.as_view(), name='stock-list'),
    path('stock/<int:pk>/', views.StockBalanceDetailView.as_view(), name='stock-detail'),
    path('movements/', views.StockMovementListView.as_view(), name='movement-list'),
    path('garage/', views.GarageListView.as_view(), name='garage-list'),
    path('inventory/', views.InventoryAdjustmentListView.as_view(), name='inventory-list'),
    path('waybill/<int:courier_id>/', views.WaybillGenerateView.as_view(), name='waybill-generate'),
]
```

`apps/clients/urls.py`:
```python
from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.ClientListView.as_view(), name='client-list'),
    path('<int:pk>/', views.ClientDetailView.as_view(), name='client-detail'),
    path('<int:pk>/orders/', views.ClientOrderHistoryView.as_view(), name='client-orders'),
]
```

`apps/workers/urls.py`:
```python
from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('', views.WorkerListView.as_view(), name='worker-list'),
    path('<int:pk>/', views.WorkerDetailView.as_view(), name='worker-detail'),
    path('<int:pk>/salary/', views.WorkerSalaryView.as_view(), name='worker-salary'),
]
```

`apps/products/urls.py`:
```python
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product-list'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
]
```

**Файлы для создания:**
- `apps/logistics/urls.py`
- `apps/warehouse/urls.py`
- `apps/clients/urls.py`
- `apps/workers/urls.py`
- `apps/products/urls.py`
- `WERP_system/urls.py` — обновить (добавить новые include + media)

**Зависимости:** P2 (DRF установлен), views.py в каждом приложении

---

### [P5] Django Admin — полная настройка для всех моделей

> **Цель:** Создать удобный, функциональный интерфейс администратора с фильтрами, поиском, inline-редактированием и кастомными действиями для каждого модуля.

#### 5.1 Принципы оформления Admin

- Все `ModelAdmin` классы используют `list_display`, `list_filter`, `search_fields`, `ordering`
- Связанные модели отображаются через `TabularInline` или `StackedInline`
- Вычисляемые поля (итоги, статусы) — через `readonly_fields`
- Кастомные действия (`actions`) для массовых операций
- `date_hierarchy` для моделей с датами
- Группировка полей через `fieldsets`

#### 5.2 Спецификация по каждому приложению

**`apps/clients/admin.py`:**
```
ClientAdmin:
  list_display:   name, phone, address, balans, tg_id, created_at
  list_filter:    created_at
  search_fields:  name, phone, address
  readonly_fields: created_at, updated_at, latitude, longitude
  fieldsets:
    - "Основная информация": name, phone, address, balans, note
    - "Геолокация": latitude, longitude
    - "Telegram": tg_id
    - "Служебное": created_at, updated_at
```

**`apps/products/admin.py`:**
```
ProductAdmin:
  list_display:   name, type_product, price, track_inventory, created_at
  list_filter:    type_product, track_inventory
  search_fields:  name
  list_editable:  price, track_inventory
```

**`apps/workers/admin.py`:**
```
WorkerAdmin:
  list_display:   full_name, worker_type, date_for_payed, created_at
  list_filter:    worker_type
  search_fields:  full_name
  readonly_fields: created_at, updated_at
  inlines:        [GarageInline]  — показывает авто курьера прямо в карточке
```

**`apps/warehouse/admin.py`:**
```
StockBalanceAdmin:
  list_display:   product, quantity, last_received_date, last_departure_date
  list_filter:    product__type_product
  search_fields:  product__name
  readonly_fields: last_received_date, last_departure_date

StockMovementAdmin:
  list_display:   sold_product, operation_type, quantity, data, contract
  list_filter:    operation_type, data
  search_fields:  sold_product__name
  date_hierarchy: data

GarageAdmin:
  list_display:   vehicle_name, plate_number, courier, milage, year
  search_fields:  vehicle_name, plate_number, courier__full_name

InventoryAdjustmentAdmin:
  list_display:   product, adjustment_type, quantity, adjusted_by, created_at
  list_filter:    adjustment_type, created_at
  search_fields:  product__name, reason
  readonly_fields: created_at
  date_hierarchy: created_at
```

**`apps/logistics/admin.py` — РАСШИРИТЬ:**
```
CourierShiftAdmin:
  list_display:   courier, date, status, cash_total, card_total, opened_at, closed_at
  list_filter:    status, date, courier
  search_fields:  courier__full_name
  readonly_fields: cash_total, card_total, opened_at, closed_at, date
  date_hierarchy: date
  inlines:        [CourierTripInline]
  actions:        [close_selected_shifts]

CourierTripInline (TabularInline):
  model:          CourierTrip
  fields:         full_loaded, full_returned, status, started_at, finished_at
  readonly_fields: started_at, finished_at
  extra:          0

CourierTripAdmin:
  list_display:   id, shift, status, full_loaded, full_returned, started_at, finished_at
  list_filter:    status, shift__courier
  search_fields:  shift__courier__full_name
  readonly_fields: started_at, finished_at
  inlines:        [OrderInline]

OrderInline (TabularInline):
  model:          Order
  fields:         client, payment_type, status, assigned_courier, note, created_at, delivered_at
  readonly_fields: created_at, delivered_at
  extra:          0
  show_change_link: True

OrderItemInline (TabularInline):
  model:          OrderItem
  fields:         product, quantity, price, exchange_qty, sell_with_qty, defective_qty
  readonly_fields: price
  extra:          1

OrderAdmin:
  list_display:   id, trip, client, payment_type, status, total_price_display, assigned_courier, created_at, delivered_at
  list_filter:    status, payment_type, trip__shift__courier, trip__shift__date
  search_fields:  client__name, client__phone, note
  readonly_fields: created_at, delivered_at
  date_hierarchy: created_at
  inlines:        [OrderItemInline]
  actions:        [mark_as_delivered, mark_as_cancelled]

OrderItemAdmin:
  list_display:   id, order, product, quantity, price, exchange_qty, sell_with_qty, defective_qty
  list_filter:    product__type_product, order__status
  search_fields:  product__name, order__client__name
  readonly_fields: price
```

**`apps/accounting/admin.py` — РАСШИРИТЬ:**
```
ContractAdmin:
  list_display:   description, client, contract_type, amount, date
  list_filter:    contract_type, date
  search_fields:  description, client__name
  date_hierarchy: date
  inlines:        [SubjectContractInline]

SubjectContractInline (TabularInline):
  model:          SubjectContract
  extra:          1

InstallmentAdmin:
  list_display:   client, product, amount, paid_amount, status, due_date
  list_filter:    status, due_date
  search_fields:  client__name
  readonly_fields: created_at, updated_at
  inlines:        [PaymentsInstallmentInline]

SalaryAdmin:
  list_display:   worker, balance, last_payment
  search_fields:  worker__full_name
  readonly_fields: balance
  inlines:        [SalaryPaymentInline]

FinancialTransactionsAdmin:
  list_display:   date, transaction_type, amount, card_amount, source
  list_filter:    transaction_type, date
  date_hierarchy: date
  readonly_fields: date, amount, card_amount, source

FinanceAdmin:
  list_display:   date, income, consumption, profit, card_profit
  list_filter:    date
  date_hierarchy: date
  readonly_fields: income, consumption, profit, card_profit, date
```

**Кастомизация заголовка Admin:**
```python
# В WERP_system/urls.py или apps/__init__.py:
admin.site.site_header = "Osnova 2.0 — ERP"
admin.site.site_title = "WERP Admin"
admin.site.index_title = "Панель управления"
```

**Файлы для изменения:**
- `apps/clients/admin.py` — создать полный `ClientAdmin`
- `apps/products/admin.py` — создать `ProductAdmin`
- `apps/workers/admin.py` — создать `WorkerAdmin` с `GarageInline`
- `apps/warehouse/admin.py` — создать все 4 Admin-класса
- `apps/logistics/admin.py` — расширить: добавить `CourierShiftAdmin`, `CourierTripAdmin`, `OrderAdmin`
- `apps/accounting/admin.py` — расширить: добавить все inline и readonly

**Зависимости:** P0 (новые модели), P2 (InventoryAdjustment)

---

### [P6] Веб-интерфейс (Templates + Dashboard)

> **Цель:** Создать минималистичный веб-дашборд для диспетчера/администратора. Не замена Django Admin — дополнение для оперативного мониторинга в реальном времени.

#### 6.1 Новое приложение `apps/dashboard`

```
apps/dashboard/
├── __init__.py
├── apps.py
├── urls.py
├── views.py
└── templates/
    └── dashboard/
        ├── base.html          — базовый шаблон (navbar, sidebar, блок content)
        ├── index.html         — главная: сводка за сегодня (Finance)
        ├── shifts.html        — список смен курьеров за день
        ├── shift_detail.html  — детали смены: рейсы и заказы
        ├── stock.html         — остатки склада
        └── finance.html       — финансовая сводка по датам
```

#### 6.2 Структура шаблонов

**`base.html` — каркас:**
```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>{% block title %}Osnova 2.0{% endblock %}</title>
  <!-- Bootstrap 5 CDN -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/css/bootstrap.min.css">
  <!-- Bootstrap Icons -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11/font/bootstrap-icons.css">
  {% block extra_css %}{% endblock %}
</head>
<body>
  <!-- Navbar: логотип, имя пользователя, ссылка на /admin/ -->
  <nav class="navbar navbar-dark bg-dark">...</nav>

  <div class="container-fluid">
    <div class="row">
      <!-- Sidebar: ссылки на разделы -->
      <nav class="col-md-2 sidebar bg-light">
        <ul class="nav flex-column">
          <li><a href="{% url 'dashboard:index' %}">Главная</a></li>
          <li><a href="{% url 'dashboard:shifts' %}">Смены</a></li>
          <li><a href="{% url 'dashboard:stock' %}">Склад</a></li>
          <li><a href="{% url 'dashboard:finance' %}">Финансы</a></li>
          <li><a href="/admin/">Администрирование</a></li>
        </ul>
      </nav>

      <!-- Основной контент -->
      <main class="col-md-10 ms-sm-auto px-4">
        {% block content %}{% endblock %}
      </main>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js"></script>
  {% block extra_js %}{% endblock %}
</body>
</html>
```

**`index.html` — главная страница (дашборд):**
```
Карточки (Bootstrap cards):
  - Доход сегодня (Finance.income)
  - Расход сегодня (Finance.consumption)
  - Прибыль (Finance.profit)
  - Безнал (Finance.card_profit)

Таблица: Активные смены курьеров сегодня
  Колонки: Курьер | Статус | Наличные | Безнал | Кол-во заказов

Таблица: Последние 10 заказов (Order)
  Колонки: # | Клиент | Продукт | Кол-во | Сумма | Тип оплаты | Статус
```

**`shifts.html` — список смен:**
```
Фильтр по дате (date input)
Таблица: CourierShift
  Колонки: Курьер | Дата | Статус | Наличные | Безнал | Открыта | Закрыта | Действия
  Действие: кнопка "Детали" → shift_detail.html
```

**`shift_detail.html` — детали смены:**
```
Заголовок: Смена #N — Курьер — Дата
Карточки: Наличные | Безнал | Итого | Статус

Для каждого рейса (CourierTrip):
  Аккордеон/карточка:
    - Загружено / Доставлено / Остаток в машине / Пустых / Брак
    - Таблица заказов рейса (Order)
```

**`stock.html` — склад:**
```
Таблица: StockBalance
  Колонки: Продукт | Тип | Остаток | Последнее пополнение | Последний расход
  Цветовая индикация: красный если quantity < 10

Таблица: Последние 20 движений (StockMovement)
```

**`finance.html` — финансы:**
```
Фильтр: диапазон дат
Таблица: Finance по датам
  Колонки: Дата | Доход | Расход | Прибыль | Безнал
  Итоговая строка (sum)

График (Chart.js): прибыль по дням (опционально, P6+)
```

#### 6.3 CSS-стратегия

- **Фреймворк:** Bootstrap 5 (CDN, без сборки)
- **Иконки:** Bootstrap Icons (CDN)
- **Кастомный CSS:** `static/css/dashboard.css` — минимальный, только переопределения
- **Цветовая схема:**
  - Sidebar: `bg-light` с тёмными ссылками
  - Navbar: `bg-dark navbar-dark`
  - Карточки дохода: `border-success`
  - Карточки расхода: `border-danger`
  - Карточки прибыли: `border-primary`
  - Статус OPEN: `badge bg-success`
  - Статус CLOSED: `badge bg-secondary`
  - Статус PENDING: `badge bg-warning`
  - Статус DELIVERED: `badge bg-success`
  - Статус CANCELLED: `badge bg-danger`

#### 6.4 Views для dashboard

**`apps/dashboard/views.py`:**
```python
# DashboardIndexView — GET /
#   context: today_finance (Finance), active_shifts (CourierShift), recent_orders (Order[:10])

# ShiftListView — GET /shifts/?date=YYYY-MM-DD
#   context: shifts (CourierShift filtered by date), selected_date

# ShiftDetailView — GET /shifts/<pk>/
#   context: shift (CourierShift), trips (CourierTrip with prefetch orders)

# StockView — GET /stock/
#   context: stock_items (StockBalance with select_related product), recent_movements (StockMovement[:20])

# FinanceView — GET /finance/?from=&to=
#   context: finance_records (Finance filtered by date range), totals (aggregated)
```

**`apps/dashboard/urls.py`:**
```python
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardIndexView.as_view(), name='index'),
    path('shifts/', views.ShiftListView.as_view(), name='shifts'),
    path('shifts/<int:pk>/', views.ShiftDetailView.as_view(), name='shift-detail'),
    path('stock/', views.StockView.as_view(), name='stock'),
    path('finance/', views.FinanceView.as_view(), name='finance'),
]
```

**Файлы для создания:**
- `apps/dashboard/__init__.py`
- `apps/dashboard/apps.py`
- `apps/dashboard/urls.py`
- `apps/dashboard/views.py`
- `templates/dashboard/base.html`
- `templates/dashboard/index.html`
- `templates/dashboard/shifts.html`
- `templates/dashboard/shift_detail.html`
- `templates/dashboard/stock.html`
- `templates/dashboard/finance.html`
- `static/css/dashboard.css`

**Настройки Django (`settings.py`):**
```python
TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']
STATICFILES_DIRS = [BASE_DIR / 'static']
INSTALLED_APPS += ['apps.dashboard']
```

**Зависимости:** P0 (новые модели), P5 (Admin настроен), Bootstrap 5 (CDN — без установки)

---

## 4. Соглашения по коду

### 4.1 Как писать сигналы

```python
# ПРАВИЛО 1: Всегда используй @receiver декоратор, не connect()
# ПРАВИЛО 2: pre_save — для чтения старых значений и их сохранения как атрибутов instance
# ПРАВИЛО 3: post_save — для создания связанных объектов и агрегации

# Паттерн для отслеживания изменений:
@receiver(pre_save, sender=MyModel)
def track_changes(sender, instance, **kwargs):
    if instance.pk:  # только для обновлений, не для создания
        old = sender.objects.get(pk=instance.pk)
        instance._old_field = old.field  # сохраняем как атрибут

@receiver(post_save, sender=MyModel)
def handle_save(sender, instance, created, **kwargs):
    if created:
        # логика создания
    else:
        old_value = getattr(instance, '_old_field', None)
        # логика обновления

# ПРАВИЛО 4: Никогда не вызывай instance.save() внутри post_save того же sender
# (вызовет рекурсию). Используй queryset.update() или update_fields=[]
```

### 4.2 Как структурировать API endpoints (DRF)

```python
# Структура файлов в каждом app:
# apps/myapp/
#   serializers.py  — ModelSerializer классы
#   views.py        — APIView или ViewSet
#   urls.py         — urlpatterns

# Naming convention для views:
# List:    MyModelListView      (GET /api/mymodels/)
# Detail:  MyModelDetailView    (GET /api/mymodels/<pk>/)
# Action:  MyModelActionView    (POST /api/mymodels/<pk>/action/)

# Авторизация курьера через tg_id:
# Header: X-Telegram-ID: <tg_id>
# Permission class проверяет Worker.objects.get(tg_id=request.headers['X-Telegram-ID'])
```

### 4.3 Naming conventions

| Тип | Правило | Пример |
|-----|---------|--------|
| Модели | PascalCase, существительное | `DeliveryJournal` |
| Поля моделей | snake_case | `total_price`, `card_amount` |
| Сигналы | `{action}_{model}_{event}` | `update_stock_balance_on_delivery` |
| Утилиты | глагол + существительное | `update_finance_record`, `generate_waybill` |
| Choices классы | PascalCase внутри модели | `PaymentsType`, `ActionType` |
| Choices значения | UPPER_SNAKE | `BOTTLE_20L`, `CASH` |
| Verbose names | на русском языке | `verbose_name='Сумма картой'` |

### 4.4 Правила миграций

- После каждого изменения модели: `python manage.py makemigrations <appname>`
- Никогда не редактировать существующие миграции вручную
- Имена миграций генерируются автоматически

---

## 5. Контекст для AI-помощников

### Что это за проект

**WERP / Osnova 2.0** — Django ERP-система для компании по доставке питьевой воды в Самарканде. Курьеры через Telegram-бот управляют доставками, склад и финансы обновляются автоматически через Django signals.

### Ключевые бизнес-сущности

| Сущность | Модель | App | Статус |
|----------|--------|-----|--------|
| Клиент | `Client` | clients | ✅ готово (с tg_id, lat/lon) |
| Товар (вода/тара/кулер) | `Product` | products | ✅ готово |
| Курьер/сотрудник | `Worker` | workers | ✅ готово |
| Автомобиль курьера | `Garage` | warehouse | ✅ готово |
| Остаток на складе | `StockBalance` | warehouse | ✅ готово |
| Корректировка склада | `InventoryAdjustment` | warehouse | ✅ готово |
| Смена курьера | `CourierShift` | logistics | ✅ готово |
| Рейс внутри смены | `CourierTrip` | logistics | ✅ готово |
| Заказ | `Order` | logistics | ✅ готово |
| Контракт | `Contract` | accounting | ✅ готово |
| Рассрочка | `Installment` | accounting | ✅ готово |
| Зарплата | `Salary` + `SalaryPayment` | accounting | ✅ готово |
| Транзакция | `FinancialTransactions` | accounting | ✅ готово |
| Дневная сводка | `Finance` | accounting | ✅ готово |
| ~~DeliveryLog~~ | ~~`DeliveryLog`~~ | ~~logistics~~ | 🗑️ устарело |
| ~~DeliveryJournal~~ | ~~`DeliveryJournal`~~ | ~~logistics~~ | 🗑️ устарело |
| ~~DeliveryJournalProducts~~ | ~~`DeliveryJournalProducts`~~ | ~~logistics~~ | 🗑️ устарело |

### Главный flow системы (НОВЫЙ — после P0)

```
Курьер открывает CourierShift (утром)
        │
        └─► Курьер создаёт CourierTrip (загрузка машины, указывает full_loaded)
                │
                └─► Курьер подтверждает Order (status=DELIVERED + container_op)
                        │
                        ├─► [logistics/signals] recalculate_order_price
                        │       price = product.price × quantity
                        │
                        ├─► [logistics/signals] update_shift_totals_on_order
                        │       CourierShift.cash_total или card_total += price
                        │
                        ├─► [warehouse/signals] update_stock_on_order
                        │       EXCHANGE/SELL_WITH → списать BOTTLE
                        │       DEFECTIVE → не списывать
                        │
                        └─► [accounting/signals] create_transaction_on_order
                                FinancialTransactions(PLUS) + update_finance_record
```

### Текущая ветка разработки

`master` — основная ветка. P0 выполнен: новые модели, сигналы и bot_bridge API готовы.

### Что НЕ реализовано (приоритет)

| # | Приоритет | Задача | Статус |
|---|-----------|--------|--------|
| 1 | **P0** | `CourierShift`, `CourierTrip`, `Order` — новые модели в `apps/logistics/` | ✅ Выполнено |
| 2 | **P0** | Сигналы: `recalculate_order_price`, `update_shift_totals_on_order`, `update_stock_on_order`, `create_transaction_on_order` | ✅ Выполнено |
| 3 | **P0** | API в `bot_bridge`: открытие смены, рейса, подтверждение доставки, закрытие | ✅ Выполнено |
| 4 | **P1** | `Client.tg_id` и `Client.latitude/longitude` | ✅ Выполнено |
| 5 | **P1** | Исправить баг `card_profit` в `accounting/utils.py` | ⏳ Ожидает |
| 6 | **P2** | `bot_bridge` — serializers, permissions, полный API | ✅ Выполнено |
| 7 | **P2** | Генератор путевых листов `.docx` (`warehouse/utils.py`) | ⏳ Ожидает |
| 8 | **P2** | `InventoryAdjustment` — ручная корректировка склада | ✅ Выполнено |
| 9 | **P3** | WebSockets — Django Channels, `DashboardConsumer` | ⏳ Ожидает |
| 10 | **P3** | aiogram-бот: три профиля (курьер / клиент / админ), роль-авторизация по tg_id | ⏳ Ожидает |
| 10a | **P3** | Mini App курьера: пул заказов, активный рейс, счётчики пустых/наличных/карты, коллеги | ⏳ Ожидает |
| 10b | **P3** | Mini App клиента: каталог, оформление заказа, уведомление о курьере | ⏳ Ожидает |
| 10c | **P3** | Mini App / bot-команды администратора: статистика Finance, смены, алерты склада | ⏳ Ожидает |
| 10d | **P3** | Новые bot_bridge endpoints: identify, courier pool/trip/colleagues, client orders, admin stats | ⏳ Ожидает |
| 11 | **P4** | URLs — `urls.py` для всех приложений + обновить `WERP_system/urls.py` | ⏳ Ожидает |
| 12 | **P5** | Django Admin — полная настройка всех моделей с inline, фильтрами, actions | ⏳ Ожидает |
| 13 | **P6** | Веб-дашборд — приложение `dashboard`, шаблоны Bootstrap 5, 5 страниц | ⏳ Ожидает |

### Важные особенности кода

- В `workers/models.py` есть прямой импорт `from apps.warehouse.models import Garage` — потенциальная циклическая зависимость. При рефакторинге использовать строковую ссылку `'warehouse.Garage'`
- `update_finance_record` имеет баг: `card_profit` суммирует `card_amount` для всех транзакций, включая MINUS — исправить в P1 (фильтровать только PLUS)
- `Order.container_op` определяет логику списания тары: `EXCHANGE`/`SELL_WITH` → списать `BOTTLE`, `DEFECTIVE` → не списывать
- `DeliveryLog`, `DeliveryLogMove` — устаревшие модели, таблицы существуют в БД, но новый код их не использует. Удалить после подтверждения отсутствия зависимостей
- `DeliveryJournal` — класс-заглушка в `logistics/models.py` с docstring, без полей. Таблица пустая
- Авторизация бота: курьер идентифицируется по заголовку `X-Telegram-ID: <tg_id>`, проверяется через `Worker` (у Worker нет tg_id — хранится в `Client`; для курьеров нужно добавить `tg_id` в `Worker` или использовать отдельную таблицу связи)
