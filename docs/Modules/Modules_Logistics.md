# Модуль Логистики (Logistics)

**Создан:** 2026-04-27 (предположительно)
**Статус:** Реализован — ядро системы адаптировано под P0 (CourierShift/CourierTrip/Order)
**Зависимости:** `apps.workers`, `apps.products`, `apps.clients` (планируется)

## Назначение
Модуль `logistics` — это ядро системы доставки. Современная архитектура фокусируется на моделях смен и рейсов (`CourierShift`, `CourierTrip`, `Order`) и обеспечивает автономный пересчёт показателей (цена заказа, суммы смены, списание тары) через сигналы Django.

Ключевые ответственности:
- Учёт смен и рейсов курьеров (`CourierShift`, `CourierTrip`)
- Учёт заказов внутри рейса (`Order`)
- Автоматический пересчёт сумм и интеграция со складом и финансовым модулем через сигналы

## Ключевые модели (актуальные)

### `CourierShift` — смена курьера
- Хранит агрегаты по смене: `cash_total`, `card_total`, временные метки открытия/закрытия.
- Метод `close()` аккуратно закрывает смену и фиксирует время закрытия.

См. реализацию: [`apps/logistics/models.py`](apps/logistics/models.py:159).

### `CourierTrip` — рейс внутри смены
- Описывает один рейс внутри смены: сколько загружено полных баклажек, сколько возвращено и т.д.
- Метод `get_trip_summary()` даёт текущий снимок остатков в машине.

См. реализацию: [`apps/logistics/models.py`](apps/logistics/models.py:189).

### `Order` — заказ (строка рейса)
- Основной источник правды для доставок: содержит `trip`, `client`, `payment_type`, `status`.
- **Рефакторинг этапа 3.7**: удалены поля `product`, `quantity`, `price`, `container_op`. Теперь заказ может содержать несколько позиций через модель `OrderItem`.
- Метод `get_total_price()` вычисляет общую стоимость заказа как сумму `price` всех связанных `OrderItem`.
- Перевод в статус `DELIVERED` — триггер для всей цепочки обновлений: пересчёт суммы рейса/смены, списание на складе и создание финансовой транзакции.
- **Многоадресность (2026-07):** добавлено поле `delivery_address` (FK → `clients.ClientAddress`, `SET_NULL`, `related_name='orders'`). Вместо устаревшего `client.address` заказ ссылается на конкретную запись адреса. При создании заказа (`OrderCreateModelSerializer.create()`) адрес создаётся/находится по тексту или координатам и привязывается к `Order.delivery_address`.
- **Снимок адреса (2026-07):** рядом с FK добавлены собственные поля `delivery_address_text` / `delivery_latitude` / `delivery_longitude` — копия адреса **на момент создания заказа**. Они не зависят от `ClientAddress`, поэтому при авто-удалении 4-го адреса исторический заказ не теряет адрес (см. баг [[Bugs_AddressSnapshot]]). `OrderSerializer`, `OrderCard` и `notify.py` читают именно снимок. Лимит «3 адреса» в `save_client_address` и `create()` защищён: не удаляет `ClientAddress`, на который висят заказы (`orders__isnull=True`).

См. реализацию: [`apps/logistics/models.py`](apps/logistics/models.py:238) и логику сигналов в [`apps/logistics/signals.py`](apps/logistics/signals.py:61).

### `OrderItem` — позиция заказа (новая модель, этап 3.7)
- Реализует многопозиционную архитектуру заказов: один заказ может содержать несколько продуктов за один визит.
- Поля: `order` (ForeignKey), `product`, `quantity`, `price` (цена за позицию), `exchange_qty` (возврат тары), `sell_with_qty` (продажа с тарой), `defective_qty` (брак тары).
- **Почему так**: Позволяет клиенту заказать одновременно воду 20L, воду 5L и бутыли в одном заказе. Упрощает учёт тары через отдельные поля вместо флагов.
- Сигнал `recalculate_order_price` срабатывает при сохранении `OrderItem` и обновляет цену позиции на основе `product.price`.

См. реализацию: [`apps/logistics/models.py`](apps/logistics/models.py:267).

## Что стало с `DeliveryJournal` / `DeliveryJournalProducts`
`DeliveryJournal` и `DeliveryJournalProducts` — устаревшая модельная пара, использовавшаяся для ручных отчётов курьеров. В новой архитектуре P0 их роль полностью замещена моделью `Order` (строки рейса) и агрегатами `CourierTrip`/`CourierShift`.

- Файлы с моделями всё ещё присутствуют (при необходимости для обратной совместимости), но они помечены как deprecated и вынесены в раздел "Устаревшие модели" ниже.
- Новая система даёт преимущество: единый источник правды (`Order`), минимум ручных операций и предсказуемая обработка через сигналы.

## Контейнерные операции (Container Operations)

### Бизнес-логика операций с тарой
В системе реализована сложная логика учета тары (баклажек) при продаже воды 20л. Каждая позиция заказа (`OrderItem`) содержит три поля для учета операций с тарой:

1. **`exchange_qty`** (обмен тары) - клиент возвращает пустую баклажку, получает полную. Тара списывается со склада.
2. **`sell_with_qty`** (продажа с тарой) - клиент покупает воду вместе с баклажкой. Тара списывается со склада.
3. **`defective_qty`** (брак тары) - клиент возвращает бракованную баклажку. Тара не списывается, только логируется.

**Пример бизнес-логики:** Если клиент заказывает 2 бутыли воды 20л с операциями "1 обмен" и "1 с тарой", система:
- Создает 2 позиции `OrderItem` (или одну с соответствующими полями)
- При подтверждении доставки списывает 2 баклажки со склада (1 за обмен + 1 за продажу с тарой)
- Создает финансовую транзакцию на стоимость 2 бутылей воды

### Обновленные API эндпоинты для работы с контейнерными операциями

#### 1. `OrderConfirmationView` (`POST /api/bot/courier/orders/confirm/`)
Теперь принимает массив позиций с данными о таре вместо устаревшего поля `container_op`:

```json
{
  "order_id": 123,
  "confirmed": true,
  "note": "Доставлено успешно",
  "items": [
    {
      "item_id": 456,
      "exchange_qty": 1,
      "sell_with_qty": 1,
      "defective_qty": 0
    }
  ]
}
```

#### 2. `OrderQuantityUpdateView` (`POST /api/bot/courier/orders/update-quantity/`)
Теперь работает с конкретной позицией (`item_id`) вместо всего заказа:

```json
{
  "item_id": 456,
  "new_quantity": 5,
  "container_data": {
    "exchange_qty": 2,
    "sell_with_qty": 1,
    "defective_qty": 0
  }
}
```

### Сигналы для обработки контейнерных операций

1. **`update_stock_on_order`** (`apps/warehouse/signals.py`) - списывает тару со склада при подтверждении заказа:
   - Суммирует `exchange_qty + sell_with_qty` для списания
   - Логирует `defective_qty` без списания
   - Автоматически маппит продукт `BOTTLE_20L` на `BOTTLE` для списания

2. **`create_transaction_on_order`** (`apps/accounting/signals.py`) - создает финансовую транзакцию с учетом общей стоимости всех позиций заказа.

3. **`recalculate_order_price`** (`apps/logistics/signals.py`) - пересчитывает цену позиции при изменении количества или данных о таре.

### Валидация данных
- Сумма `exchange_qty + sell_with_qty + defective_qty` не может превышать `quantity` позиции
- Данные проверяются как на уровне сериализаторов, так и на уровне бизнес-логики
- При изменении количества проверяется, что новые данные о таре не превышают новое количество

## Автономность пересчёта (как это работает)

Центральный принцип: изменение состояния сущности в `logistics` (в первую очередь перевод `Order` в `DELIVERED`) вызывает детерминированную цепочку задач через Django-сигналы. Это даёт возможность модулям работать автономно — каждая подсистема подписана на изменения и отвечает только за свою часть.

**Изменения после этапа 3.7 (рефакторинг на OrderItem):**
- Цена заказа теперь рассчитывается как сумма `price` всех связанных `OrderItem` через метод `order.get_total_price()`.
- Сигнал `recalculate_order_price` теперь привязан к модели `OrderItem` и обновляет цену конкретной позиции.
- Складской сигнал `update_stock_on_order` итерирует по `order.items.all()` и учитывает новые поля количества (`exchange_qty`, `sell_with_qty`, `defective_qty`) для точного учёта тары.
- Финансовый сигнал `create_transaction_on_order` использует `order.get_total_price()` вместо прямого поля `price`.

Основная цепочка при подтверждении доставки (см. [`apps/logistics/signals.py`](apps/logistics/signals.py:61)):

1) pre_save/post_save: пересчёт цены позиции заказа
   - Сигнал `recalculate_order_price` (привязан к `OrderItem`) обеспечивает, что `OrderItem.price` соответствует `product.price * quantity` при изменениях.
   - Ссылка на код: [`apps/logistics/signals.py`](apps/logistics/signals.py:22).

2) post_save(Order, status=DELIVERED): обновление сумм смены
   - `update_shift_totals_on_order` аккумулирует `cash_total`/`card_total` в связанной `CourierShift` на основе `order.get_total_price()`.
   - Работа идёт через простое добавление значения и `shift.save(update_fields=[...])` — минимизация перезаписи полей.

3) post_save(Order, status=DELIVERED): обновление склада
   - `warehouse/signals.update_stock_on_order` переводит продаваемый продукт в маппинг (`BOTTLE_20L -> BOTTLE`) и создаёт `StockMovement` + корректирует `StockBalance`.
   - **Новое**: итерация по всем `OrderItem` заказа, учёт полей `exchange_qty`, `sell_with_qty`, `defective_qty` для точного списания тары.
   - Код и правила маппинга: [`apps/warehouse/signals.py`](apps/warehouse/signals.py:358).

4) post_save(Order, status=DELIVERED): создание финансовой транзакции
   - `accounting/signals.create_transaction_on_order` создаёт `FinancialTransactions` (+/-) на основе `order.get_total_price()` и вызывает `utils.update_finance_record(date)`.
   - Ссылка на код: [`apps/accounting/signals.py`](apps/accounting/signals.py:272).

Гарантии и практики для надёжности:
- Использование atomic transactions и transaction.on_commit: критические операции (списание товара, создание транзакции) выполняются внутри транзакций или отложены на `on_commit`, чтобы избежать рассинхронизации при откате.
- Идемпотентность: сигналы должны быть безопасны при повторном вызове — используйте `get_or_create`, проверку статуса и `update_fields` вместо полного save, где возможно.
- Логирование: каждая стадия логирует результат и предупреждения (см. `logger` в `apps/warehouse/signals.py` и `apps/logistics/signals.py`).
- Минимизация рекурсий: сигналы написаны так, чтобы не провоцировать бесконечные циклы (пересчёт в pre_save, агрегация в post_save с защитой по статусам).

Пример (схематично) — что происходит при подтверждении заказа с несколькими позициями:

```python
# В коде: курьер через бот пометил заказ доставленным
order.status = Order.Status.DELIVERED
order.delivered_at = timezone.now()
order.save()

# После commit срабатывают подписанные обработчики:
# 1) recalculate_order_price (для каждого OrderItem) -> гарантирует корректные цены позиций
# 2) update_shift_totals_on_order -> увеличивает cash/card в shift на сумму order.get_total_price()
# 3) update_stock_on_order -> создает StockMovement для каждого продукта с учётом тары
# 4) accounting handler -> создает FinancialTransactions на общую сумму заказа
```

Ссылки на реализацию: [`apps/logistics/models.py`](apps/logistics/models.py:277), [`apps/logistics/signals.py`](apps/logistics/signals.py:22), [`apps/warehouse/signals.py`](apps/warehouse/signals.py:358), [`apps/accounting/signals.py`](apps/accounting/signals.py:272).

## Устаревшие модели

— `DeliveryJournal`, `DeliveryJournalProducts` — оставлены в кодовой базе для исторической совместимости и для случаев, когда оператор выгружает отчёт вручную. Не использовать в новых процессах — вместо них работать с `Order` и агрегатами `CourierTrip`/`CourierShift`.

Места в коде: [`apps/logistics/models.py`](apps/logistics/models.py:95) (DeliveryJournal), [`apps/logistics/models.py`](apps/logistics/models.py:127) (DeliveryJournalProducts).

## Рекомендации разработчикам

- При добавлении новых сигналов следуйте шаблону: короткая функция-обработчик, явный фильтр по `status`/`created`, логирование, и использование `transaction.on_commit` при побочных эффектах.
- Для массовых операций (импорт/реплейс) отключайте сигналы через контекст-менеджер или указывайте флаг `bulk_update=True` и выполняйте явные пересчёты в конце.
- Покрывайте критические сценарии тестами (unit + integration), особенно гонки между обновлением заказа и закрытием смены.

## Примеры использования (P0)

Создание заказа и подтверждение доставки (микропроцесс):

```python
from apps.logistics.models import CourierShift, CourierTrip, Order
from apps.workers.models import Worker
from apps.products.models import Product
from django.utils import timezone

shift = CourierShift.objects.create(courier=Worker.objects.first())
trip = CourierTrip.objects.create(shift=shift, full_loaded=10)
product = Product.objects.get(name='Вода 20L с тарой')

order = Order.objects.create(trip=trip, product=product, quantity=2, payment_type=Order.PaymentType.CASH)

# Курьер доставил товар через бота -> меняем статус и сохраняем
order.status = Order.Status.DELIVERED
order.delivered_at = timezone.now()
order.save()

# После сохранения: автоматическое списание тары, обновление cash_total в shift и создание финансовой транзакции
```

## Ограничения и известные проблемы

- Если в одном моменте происходит много concurrent-операций (массовая выгрузка и подтверждения) — возможно появление race conditions. Решение: использовать DB-level блокировки, транзакции и тесты на конкурентность.
- Частые ручные правки устаревших `DeliveryJournal` могут приводить к расхождениям — рекомендовано отключить ручные отчёты и мигрировать пользователей на P0 API.

## Ссылки
- [[docs/Index|Главный индекс]]
- [[docs/Modules_Warehouse|Модуль Склада]]
- [[docs/Modules_Accounting|Модуль Финансов]]
- [[docs/Modules_BotBridge|Модуль Bot Bridge]]
- [[CLAUDE.md|Архитектурный справочник]]
