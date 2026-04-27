# Модуль Логистики (Logistics)

**Создан:** 2026-04-27 (предположительно)  
**Статус:** Реализован (ядро системы)  
**Зависимости:** `apps.workers`, `apps.products`, `apps.clients` (планируется)

## Назначение
Модуль `logistics` — это ядро системы доставки. Он отвечает за:
- Учёт рейсов курьеров (`DeliveryLog`) и движения тары (`DeliveryLogMove`)
- Финансовые отчёты курьеров (`DeliveryJournal`) и строки продуктов (`DeliveryJournalProducts`)
- Автоматический расчёт стоимости заказов на основе количества и типа оплаты
- Синхронизацию с складом (`warehouse`) и финансами (`accounting`) через сигналы

## Архитектура

### Модели

#### `DeliveryLog` — рейс курьера
- `courier`: ссылка на `Worker` (курьер)
- `total_quantity`: общее количество тары в рейсе (вычисляется автоматически)
- `total_sold`: общее количество проданной воды (вычисляется автоматически)
- `date`: дата рейса

**Методы:**
- `calculate_total_quantity()` — суммирует `TAKEN` и вычитает `BROUGHT`/`RETURNED` из связанных `DeliveryLogMove`
- `calculate_total_sold()` — учитывает последовательные `BROUGHT` для правильного подсчёта продаж
- `check_total_quantity()` — сверяет `total_quantity` с фактическими продажами `BOTTLE_20L`

#### `DeliveryLogMove` — движение тары в рейсе
- `delivery_log`: ссылка на `DeliveryLog`
- `action`: `TAKEN` (взял со склада), `BROUGHT` (привёз обратно), `RETURNED` (вернул клиенту)
- `quantity`: количество бутылей
- `date`: дата движения

**Логика:** При сохранении вызывает `delivery_log.calculate_total_quantity()`.

#### `DeliveryJournal` — финансовый отчёт курьера
- `courier`: ссылка на `Worker`
- `date`: дата отчёта
- `card_price`: сумма оплаты картой (автоматически пересчитывается)
- `total_price`: общая сумма наличными (автоматически пересчитывается)

**Методы:**
- `update_total_price()` — пересчитывает `total_price` и `card_price` на основе связанных `DeliveryJournalProducts`

**Отсутствует:** связь с клиентом (`client` FK) — задача P1.

#### `DeliveryJournalProducts` — строка продукта в отчёте
- `delivery_journal`: ссылка на `DeliveryJournal` (`related_name='products'`)
- `product`: ссылка на `Product`
- `quantity`: количество (по умолчанию 1)
- `price`: цена (автоматически = `product.price * quantity`, если не задана)
- `payment_type`: `CARD` (карта), `CASH` (наличные), `BONUS` (бонусы)
- `note`: описание (например, «клиент попросил дополнительную бутыль»)

**Логика:** При сохранении:
1. Если `price` не указана, вычисляет как `product.price * quantity`
2. Вызывает `delivery_journal.update_total_price()`

## Сигналы (`logistics/signals.py`)

### `post_save(DeliveryLogMove)`
- Вызывает `delivery_log.calculate_total_quantity()`
- Обновляет `total_quantity` в родительском `DeliveryLog`

### `post_save(DeliveryLog)`
- Вызывает `check_total_quantity()` для сверки с продажами

### `pre_save(DeliveryJournalProducts)`
- Пересчитывает цену при изменении `quantity`

### `post_save(DeliveryJournalProducts)`
- Вызывает `delivery_journal.update_total_price()`
- Запускает цепочку сигналов в `warehouse` и `accounting`

## Взаимодействие с другими модулями

### `warehouse` (склад)
При сохранении `DeliveryJournalProducts`:
1. Сигнал `warehouse/signals.py` `pre_save` сохраняет `_old_quantity`
2. Сигнал `warehouse/signals.py` `post_save` списывает/возвращает тару через `PRODUCT_MAP` (`BOTTLE_20L` → `BOTTLE`)

### `accounting` (финансы)
При сохранении `DeliveryJournal`:
1. Сигнал `accounting/signals.py` создаёт `FinancialTransactions` с `type=PLUS`
2. Вызывается `update_finance_record(date)`

### `workers` (сотрудники)
`DeliveryJournal.courier` и `DeliveryLog.courier` ссылаются на `Worker`.

### `products` (товары)
`DeliveryJournalProducts.product` ссылается на `Product`.

## Бизнес-логика

### Автоматический расчёт цены
Цена строки продукта вычисляется автоматически на основе `product.price`. Это гарантирует, что оператор не ошибётся вручную.

### Учёт тары
- `BOTTLE_20L` (вода с тарой) — это то, что продаёт курьер.
- `BOTTLE` (тара) — это то, что списывается со склада при продаже `BOTTLE_20L`.
- Маппинг происходит в `warehouse/signals.py` через `PRODUCT_MAP`.

### Типы оплаты
- `CASH` — наличные, увеличивают `total_price`
- `CARD` — карта, увеличивают `card_price`
- `BONUS` — бонусы, уменьшают `total_price` (скидка)

## Примеры использования

### Создание отчёта курьера
```python
from apps.logistics.models import DeliveryJournal, DeliveryJournalProducts
from apps.workers.models import Worker
from apps.products.models import Product

courier = Worker.objects.get(full_name="Иванов Иван")
product = Product.objects.get(name="Вода 20L с тарой")

journal = DeliveryJournal.objects.create(
    courier=courier,
    date=date.today()
)

line = DeliveryJournalProducts.objects.create(
    delivery_journal=journal,
    product=product,
    quantity=5,
    payment_type=DeliveryJournalProducts.PaymentsType.CASH
)
# Автоматически: price = product.price * 5
# Автоматически: journal.total_price обновится
# Автоматически: создастся финансовая транзакция
# Автоматически: со склада спишется 5 тар (BOTTLE)
```

### Получение отчётов за день
```python
from datetime import date

today = date.today()
journals = DeliveryJournal.objects.filter(date=today).select_related('courier')
for j in journals:
    print(f"{j.courier}: {j.total_price} сум, картой: {j.card_price}")
```

## Ограничения и известные проблемы

1. **Нет связи с клиентом** — `DeliveryJournal` не знает, кому доставлена вода (требуется P1).
2. **Ручное создание отчётов** — пока нет API для бота (частично решено в `bot_bridge`).
3. **Нет проверки дубликатов** — можно создать несколько отчётов на одного курьера за день.
4. **Сложная логика `total_sold`** — метод `calculate_total_sold()` может давать ошибки при неправильной последовательности движений.

## Планы развития (Roadmap)
- **P1:** Добавить FK `Client` в `DeliveryJournal`
- **P2:** API для бота (подтверждение доставки, изменение количества)
- **P3:** Утилита автораспределения заказов по ближайшим курьерам

## Ссылки
- [[docs/Index|Главный индекс]]
- [[docs/Modules_Warehouse|Модуль Склада]]
- [[docs/Modules_Accounting|Модуль Финансов]]
- [[docs/Modules_BotBridge|Модуль Bot Bridge]]
- [[CLAUDE.md|Архитектурный справочник]]