# CLAUDE.md — Архитектурный справочник проекта WERP / Osnova 2.0

> **Для AI-помощников:** Этот файл — главный контекст проекта. Читай его перед любыми изменениями кода.
> Проект: ERP-система для компании по доставке питьевой воды (Самарканд, Узбекистан).
> Язык кода: Python/Django. Язык комментариев и переменных: русский + английский (mixed).

---

## 1. Архитектура проекта

### 1.1 Стек и зависимости

| Компонент         | Технология                   | Версия            |
| ----------------- | ---------------------------- | ----------------- |
| Backend framework | Django                       | 5.1.6             |
| REST API          | Django REST Framework (DRF)  | планируется       |
| Telegram Bot      | Aiogram                      | 3.x (планируется) |
| База данных       | PostgreSQL                   | 17                |
| Real-time         | Django Channels (WebSockets) | планируется       |
| ASGI-сервер       | asgiref                      | 3.8.1             |
| Драйвер БД        | psycopg2                     | 2.9.10            |
| Работа с датами   | python-dateutil              | 2.9.0             |
| Генерация данных  | Faker                        | 37.0.0            |

### 1.2 Структура приложений

```
apps/
├── clients/      — CRM: клиенты (ФИО, телефон, адрес, предоплата)
├── products/     — Каталог товаров (вода, тара, кулеры, аксессуары)
├── workers/      — Сотрудники (курьеры, упаковщики)
├── warehouse/    — Склад: остатки, движения, автопарк
├── logistics/    — Ядро: журналы доставок, учёт тары
└── accounting/   — Финансы: контракты, рассрочки, зарплаты, транзакции
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

Сигналы — главный механизм автоматизации. Цепочка срабатывания при доставке:

```
Оператор сохраняет DeliveryJournalProducts
        │
        ├─► [logistics/signals] pre_save: recalculate_price
        │       Пересчёт цены если изменилось quantity
        │
        ├─► [warehouse/signals] pre_save: track_delivery_journal_changes
        │       Сохраняет _old_quantity для diff-расчёта
        │
        ├─► [logistics/signals] post_save: update_delivery_journal_totals
        │       Пересчёт total_price и card_price в DeliveryJournal
        │
        ├─► [warehouse/signals] post_save: update_stock_balance_on_delivery
        │       PRODUCT_MAP: BOTTLE_20L → BOTTLE (подмена продукта)
        │       Списание/возврат тары со StockBalance
        │       Создание записи StockMovement
        │
        └─► [accounting/signals] post_save: update_transactions_on_delivery
                Создание FinancialTransactions (PLUS)
                Вызов utils.update_finance_record(date)
                Агрегация в модель Finance (income/consumption/profit/card_profit)
```

---

## 2. Что уже реализовано

### 2.1 `apps/clients` — CRM

**Модели:**
- `Client` — ФИО, телефон (unique), адрес, предоплата (balans), примечание

**Статус:** Базовая модель готова. Нет геопозиции и Telegram ID.

**Связи:** `Client` ← `Contract`, `Installment` (из accounting)

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
- `Worker` — ФИО, тип (PACKER/COURIER/OTHER), дата начисления зарплаты

**Связи:** `Worker` ← `DeliveryLog`, `DeliveryJournal` (logistics), `Salary` (accounting), `Garage` (warehouse, OneToOne)

---

### 2.4 `apps/warehouse` — Склад и автопарк

**Модели:**
- `StockBalance` — остаток продукта на складе (product FK, quantity, даты)
- `StockMovement` — лог движений (BUY/SELL, product FK, contract FK, quantity)
- `Garage` — автомобиль (название, номер, пробег, год, courier OneToOne → Worker)

**Сигналы (`warehouse/signals.py`):**
- `post_save(Product)` → `create_stock_balance_product`: авто-создание `StockBalance` при новом продукте
- `pre_save(DeliveryJournalProducts)` → `track_delivery_journal_changes`: сохраняет `_old_quantity`
- `post_save(DeliveryJournalProducts)` → `update_stock_balance_on_delivery`: списание/возврат тары с PRODUCT_MAP
- `pre_save(SubjectContract)` → `track_subject_contract_changes`: отслеживание изменений контракта
- Сигналы для `SubjectContract` post_save/delete: движения склада по контрактам

---

### 2.5 `apps/logistics` — Ядро доставок

**Модели:**
- `DeliveryLog` — рейс курьера (courier FK, total_quantity, total_sold, date)
- `DeliveryLogMove` — движение тары в рейсе (TAKEN/BROUGHT/RETURNED, quantity, date)
- `DeliveryJournal` — финансовый отчёт курьера (courier FK, date, card_price, total_price)
- `DeliveryJournalProducts` — строка отчёта (product FK, quantity, price, payment_type: CARD/CASH/BONUS)

**Методы моделей:**
- `DeliveryLog.calculate_total_quantity()` — сумма TAKEN минус BROUGHT
- `DeliveryLog.calculate_total_sold()` — учёт последовательных BROUGHT
- `DeliveryLog.check_total_quantity()` — сверка с продажами BOTTLE_20L
- `DeliveryJournal.update_total_price()` — пересчёт total_price и card_price
- `DeliveryJournalProducts.save()` — авто-расчёт price = product.price × quantity

**Сигналы (`logistics/signals.py`):**
- `post_save(DeliveryLogMove)` → пересчёт total_quantity и total_sold в DeliveryLog
- `post_save(DeliveryLog)` → проверка соответствия total_quantity
- `pre_save(DeliveryJournalProducts)` → пересчёт цены при изменении quantity
- `post_save(DeliveryJournalProducts)` → пересчёт total_price и card_price в DeliveryJournal

**Отсутствует:** связь `DeliveryJournal` → `Client` (нет FK на клиента).

---

### 2.6 `apps/accounting` — Финансы

**Модели:**
- `Contract` — контракт (BUY=доход / SELL=расход, client FK, amount, file)
- `SubjectContract` — предмет контракта (contract FK, product FK, quantity)
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
- `DeliveryJournal` pre/post_save/delete → создание `FinancialTransactions` (total_price + card_amount) + `update_finance_record`
- `SalaryPayment` pre/post_save/delete → создание `FinancialTransactions` + `update_finance_record`
- `PaymentsInstallment` pre/post_save/delete → создание `FinancialTransactions` + `update_finance_record`
- `FinancialTransactions` pre/post_save → `update_finance_record` (при изменении даты — обновляет обе даты)

**Известная проблема:** `update_finance_record` считает `card_profit = sum(t.card_amount for t in ALL transactions)` — суммирует card_amount даже для MINUS-транзакций. Нужно фильтровать только PLUS.

---

## 3. Roadmap: что делать дальше

### [P1] Добавить геопозицию и Telegram ID в модель Client

**Что делать:** Добавить поля `latitude`, `longitude` (DecimalField, max_digits=9, decimal_places=6) и `tg_id` (BigIntegerField, unique, null=True) в `Client`.

**Файлы:**
- `apps/clients/models.py` — добавить поля
- `apps/clients/migrations/` — создать миграцию (`makemigrations`)

**Зависимости:** нет

---

### [P1] Добавить FK на Client в DeliveryJournal

**Что делать:** Добавить `client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)` в `DeliveryJournal`.

**Файлы:**
- `apps/logistics/models.py` — добавить поле client
- `apps/logistics/migrations/` — создать миграцию

**Зависимости:** нет (Client уже существует)

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
- `apps/bot_bridge/serializers.py` — сериализаторы для DeliveryJournal, Client, Product
- `apps/bot_bridge/views.py` — APIView: подтверждение доставки, изменение quantity, получение списка заказов
- `apps/bot_bridge/urls.py` — маршруты API
- `apps/bot_bridge/permissions.py` — авторизация курьера по tg_id

**Зависимости:** P1 (tg_id в Client), DRF должен быть установлен

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

**Что делать:** Функция в `warehouse/utils.py`, принимающая `courier_id` и `date`, генерирующая `.docx` файл с данными из `Garage` и `DeliveryJournal`.

**Файлы:**
- `apps/warehouse/utils.py` — создать, функция `generate_waybill(courier_id, date) -> bytes`
- `requirements.txt` — добавить `python-docx`

**Зависимости:** нет

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

### [P3] Утилита автораспределения заказов

**Что делать:** Функция в `logistics/utils.py`, которая по координатам клиента (latitude/longitude) находит ближайшего свободного курьера и назначает заказ.

**Файлы:**
- `apps/logistics/utils.py` — создать, функция `assign_nearest_courier(delivery_journal_id)`

**Зависимости:** P1 (геопозиция в Client), P1 (FK Client в DeliveryJournal)

---

### [P3] Telegram Mini App (TWA) — заказы от клиентов

**Что делать:** Отдельный API endpoint для клиентского Mini App: просмотр каталога `Product` и создание заказа в `DeliveryJournal`.

**Файлы:**
- `apps/bot_bridge/views.py` — добавить `ClientOrderView`, `ProductListView`
- `apps/bot_bridge/serializers.py` — добавить `ProductSerializer`, `OrderCreateSerializer`

**Зависимости:** bot_bridge (P2), P1 (tg_id в Client)

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

| Сущность | Модель | App |
|----------|--------|-----|
| Клиент | `Client` | clients |
| Товар (вода/тара/кулер) | `Product` | products |
| Курьер/сотрудник | `Worker` | workers |
| Автомобиль курьера | `Garage` | warehouse |
| Остаток на складе | `StockBalance` | warehouse |
| Рейс курьера (тара) | `DeliveryLog` | logistics |
| Финансовый отчёт курьера | `DeliveryJournal` | logistics |
| Строка отчёта | `DeliveryJournalProducts` | logistics |
| Контракт | `Contract` | accounting |
| Рассрочка | `Installment` | accounting |
| Зарплата | `Salary` + `SalaryPayment` | accounting |
| Транзакция | `FinancialTransactions` | accounting |
| Дневная сводка | `Finance` | accounting |

### Главный flow системы

1. Оператор создаёт `DeliveryJournal` + `DeliveryJournalProducts` в Django Admin
2. Сигналы автоматически: списывают тару со склада, создают финансовую транзакцию, обновляют дневную сводку `Finance`
3. Курьер (через Telegram-бот, **ещё не реализован**) подтверждает доставку или меняет количество
4. Диспетчер видит актуальные данные в Django Admin в реальном времени

### Текущая ветка разработки

`feat-bot-bridge` — разработка API-шлюза для Telegram-бота.

### Что НЕ реализовано (приоритет)

1. `bot_bridge` app — API для Telegram-бота
2. `Client.tg_id` и `Client.latitude/longitude`
3. `DeliveryJournal.client` FK
4. WebSockets (Django Channels)
5. DRF не установлен (нет в requirements.txt)

### Важные особенности кода

- В `workers/models.py` есть импорт `from apps.warehouse.models import Garage` — потенциальная циклическая зависимость
- `StockBalance` использует поле `quantitly` (опечатка в старых миграциях), в текущей модели — `quantity`
- `update_finance_record` имеет баг: `card_profit` суммирует `card_amount` для всех транзакций, включая MINUS
- Сигналы `logistics/signals.py` и `warehouse/signals.py` оба слушают `DeliveryJournalProducts` — порядок выполнения зависит от порядка регистрации в `AppConfig.ready()`
