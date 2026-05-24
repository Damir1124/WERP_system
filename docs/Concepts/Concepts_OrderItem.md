# Концепция: Многопозиционные заказы (OrderItem)

## Зачем это нужно в нашем проекте

В реальном бизнесе доставки воды клиент за один визит может заказать:
- 2 бутыли воды 20L с тарой
- 1 бутыль воды 5L
- Возврат 3 пустых бутылей (обмен)
- Продажа 1 бутыли с тарой (клиент оставляет тару у себя)
- Сдача 1 бракованной бутыли

До этапа 3.7 система поддерживала только **один продукт на заказ**. Это создавало проблемы:
1. Курьеру приходилось создавать несколько заказов для одного клиента.
2. Учёт тары был через флаги (`container_op`), что не позволяло разделить обмен, продажу с тарой и брак.
3. Финансовые транзакции агрегировались неправильно — каждый заказ создавал отдельную транзакцию.

**Решение:** Модель `OrderItem` позволяет хранить несколько позиций в одном заказе, с отдельными полями для каждого типа операции с тарой.

## Как это работает (с нуля)

### Аналогия из ресторана

Представьте, что заказ в системе — это **чек в ресторане**:
- **Order** — сам чек (номер стола, способ оплаты, статус «оплачен»).
- **OrderItem** — строки в чеке: «Стейк — 1 шт.», «Салат — 2 шт.», «Вода — 3 бутылки».

Каждая строка (`OrderItem`) содержит:
- **Продукт** (что заказано)
- **Количество** (сколько)
- **Цену** (цена за единицу)
- **Дополнительные поля для тары** (сколько вернули, сколько продали с тарой, сколько брака)

Когда курьер подтверждает доставку, система проходит по всем строкам чека и:
1. Списывает со склада продукты (вода)
2. Учитывает тару (возврат, продажа с тарой, брак)
3. Суммирует стоимость всех строк для финансового учёта

### Техническая реализация

**Модели:**
```python
class Order(models.Model):
    # Убраны product, quantity, price, container_op
    trip = models.ForeignKey(CourierTrip, ...)
    client = models.ForeignKey(Client, ...)
    payment_type = models.CharField(choices=...)
    status = models.CharField(choices=...)
    
    def get_total_price(self):
        return sum(item.price for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', ...)
    product = models.ForeignKey(Product, ...)
    quantity = models.IntegerField(default=1)
    price = models.IntegerField(null=True, blank=True)  # цена за позицию
    exchange_qty = models.IntegerField(default=0)      # возврат тары
    sell_with_qty = models.IntegerField(default=0)     # продажа с тарой
    defective_qty = models.IntegerField(default=0)     # брак тары
```

**Почему три отдельных поля для тары вместо одного `container_op`?**
- `exchange_qty` — клиент возвращает пустую тару, она поступает на склад для повторного использования.
- `sell_with_qty` — клиент покупает тару вместе с водой (например, первый заказ), тара списывается со склада навсегда.
- `defective_qty` — бракованная тара, которую нельзя использовать повторно, списывается в утиль.

Это позволяет точно отслеживать движение тары и избегать путаницы.

## Схема потока данных

```
Клиент заказывает через Mini App
    ↓
Создаётся Order с пустым trip (ждёт назначения)
    ↓
Курьер берёт заказ → Order.trip заполняется
    ↓
На месте клиент просит добавить ещё продуктов
    ↓
Курьер через бот добавляет OrderItem (или изменяет quantity)
    ↓
При подтверждении доставки (status=DELIVERED):
    ├── Сигнал recalculate_order_price обновляет price каждого OrderItem
    ├── Сигнал update_shift_totals_on_order добавляет сумму к cash_total/card_total
    ├── Сигнал update_stock_on_order:
    │   ├── Для каждого OrderItem списывает quantity продукта
    │   ├── Учитывает exchange_qty, sell_with_qty, defective_qty для тары
    │   └── Создаёт StockMovement
    └── Сигнал create_transaction_on_order создаёт FinancialTransactions
```

## Ловушки и частые ошибки

1. **Рекурсия в сигналах**  
   Сигнал `recalculate_order_price` привязан к `OrderItem`. Если внутри него вызвать `item.save()`, может возникнуть бесконечный цикл.  
   **Решение:** Использовать `update_fields` и проверку `if instance.price != new_price`.

2. **Агрегация total_price**  
   Метод `order.get_total_price()` выполняет запрос `SUM` по связанным `OrderItem`. При частых вызовах может создавать нагрузку.  
   **Решение:** Кэшировать результат в поле `Order.total_price` (пока не реализовано) или использовать `prefetch_related` в API.

3. **Миграция данных**  
   Существующие заказы до рефакторинга имеют поля `product`, `quantity`, `price`. Миграция `0004` создаёт для каждого старого заказа один `OrderItem` с теми же данными.

4. **Валидация в API**  
   Новый `OrderCreateModelSerializer` принимает список `items`. Нужно проверять, что все `product_id` существуют и `quantity` > 0.

## В нашем коде

- **Модели:** [`apps/logistics/models.py`](apps/logistics/models.py:243) — определение `OrderItem`.
- **Сигналы:** [`apps/logistics/signals.py`](apps/logistics/signals.py:22) — `recalculate_order_price` для `OrderItem`.
- **Склад:** [`apps/warehouse/signals.py`](apps/warehouse/signals.py:358) — `update_stock_on_order` с итерацией по `order.items.all()`.
- **Финансы:** [`apps/accounting/signals.py`](apps/accounting/signals.py:272) — `create_transaction_on_order` использует `order.get_total_price()`.
- **API:** [`apps/bot_bridge/serializers.py`](apps/bot_bridge/serializers.py:40) — `OrderItemSerializer`, [`apps/bot_bridge/views.py`](apps/bot_bridge/views.py:397) — `CreateOrderView` с поддержкой списка позиций.

## Связанные концепции

- [[Concepts_DjangoSignals|Сигналы Django]] — как работают pre_save/post_save.
- [[Modules_Logistics|Модуль Логистики]] — полное описание моделей Order и OrderItem.
- [[Modules_Warehouse|Модуль Склада]] — как учитывается тара через маппинг продуктов.