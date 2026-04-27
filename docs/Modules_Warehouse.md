# Модуль Warehouse & Garage

**Назначение:** Управление складом и автопарком.

## Модели

### StockBalance
Баланс позиций на складе.
- `product` (FK → Product) - продукт
- `quantity` - количество на складе
- `last_received_date` - дата последнего прибавления
- `last_departure_date` - дата последнего убавления

### StockMovement
Движение позиций со склада.
- `sold_product` (FK → Product) - проданный продукт
- `contract` (FK → Contract) - связанный контракт
- `operation_type` (Buy/Sell) - тип операции
- `quantity` - количество
- `data` - дата операции
- `note` - примечание

### Garage
Учет транспортных средств.
- `vehicle_name` - название автомобиля
- `plate_number` - номерной знак
- `milage` - пробег
- `year` - год выпуска
- `courier` (OneToOne → Worker) - курьер

### InventoryAdjustment (P2 реализовано)
Ручная корректировка остатков на складе через админку.
- `product` (FK → Product) - продукт для корректировки
- `adjustment_type` (INC/DEC/SET) - тип корректировки: увеличение, уменьшение, установка значения
- `quantity` - количество для изменения
- `reason` (обязательное поле) - причина корректировки
- `adjusted_by` (FK → Worker) - кто выполнил корректировку
- `created_at` - дата корректировки
- `note` - дополнительные примечания

**Логика работы:** При сохранении `InventoryAdjustment` автоматически обновляется `StockBalance` и создается запись в `StockMovement` для аудита.

## Логика
- Автоматическое списание товаров при продаже
- Маппинг товаров (BOTTLE → BOTTLE_20L)
- Отслеживание остатков в реальном времени
- **Выборочный учет на складе:** Поле `track_inventory` в модели `Product` определяет, нужно ли вести учет остатков для данного продукта

## Сигналы
- `post_save` в `logistics` → списание со склада (только для продуктов с `track_inventory=True`)
- `post_save` в `accounting` → обновление баланса (только для продуктов с `track_inventory=True`)
- `post_save` в `SubjectContract` → обновление остатков по контрактам (только для продуктов с `track_inventory=True`)

## Утилиты (`warehouse/utils.py`) - P2 реализовано

### Генератор путевых листов (.docx)
Функция `generate_waybill(courier_id, date) -> bytes` создает документ в формате .docx с информацией:
- Данные курьера и автомобиля (из модели `Garage`)
- Информация о смене (`CourierShift`)
- Рейсы за смену (`CourierTrip`) с детализацией
- Заказы в каждом рейсе (`Order`)
- Сводка по остаткам тары в машине
- Подписи курьера, диспетчера и бухгалтера

**Дополнительные функции:**
- `generate_waybill_for_today(courier_id)` - генерация на сегодня
- `generate_waybill_for_shift(shift_id)` - генерация для конкретной смены

**Зависимости:** `python-docx` добавлен в `requirements.txt`

## Задачи P2 реализованы
- ✅ **Генератор путевых листов (.docx)** - реализован в `warehouse/utils.py`
- ✅ **Ручная корректировка склада через админку** - реализована моделью `InventoryAdjustment`

## Связи
- `Product` ← `StockBalance`
- `Contract` ← `StockMovement`
- `Worker` ← `Garage`
- `Product` ← `InventoryAdjustment`

## Пример использования генератора путевых листов
```python
from apps.warehouse.utils import generate_waybill

# Генерация путевого листа для курьера на сегодня
docx_bytes = generate_waybill(courier_id=5)
with open('путевой_лист.docx', 'wb') as f:
    f.write(docx_bytes)
```

## Пример корректировки инвентаря через админку
1. В админке перейти в "Корректировки инвентаря"
2. Добавить новую корректировку:
   - Продукт: "Тара (BOTTLE)"
   - Тип корректировки: "Увеличение"
   - Количество: 10
   - Причина: "Инвентаризация выявила расхождение"
   - Кто выполнил: [Выбрать сотрудника]
3. При сохранении автоматически обновится `StockBalance` и создастся запись в `StockMovement`

[[Index]] | [[Modules_Accounting]] | [[Modules_Logistics]] | [[Modules_Products]]