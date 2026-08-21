# Модуль Warehouse & Garage

**Назначение:** Управление складом и автопарком.

## Модели

### Garage
Учет транспортных средств.
- `vehicle_name` - название автомобиля
- `plate_number` - номерной знак
- `milage` - пробег
- `year` - год выпуска
- `courier` (OneToOne → Worker) - курьер

## Автономный контур складских продуктов (WarehouseProduct)

**Назначение:** Учёт складских продуктов **отдельно** от ассортимента `Product`. Полностью автономная сущность без наследования и без FK на `Product`.

### Модели
- **`WarehouseProduct`** — складской продукт (`name`, `sku`, `unit`, `is_active`)
- **`WarehouseStockBalance`** — остатки (OneToOne к `WarehouseProduct`)
- **`WarehouseStockMovement`** — журнал приход/расход (IN/OUT)
- **`WarehouseInventoryAdjustment`** — ручные корректировки (INC/DEC/SET)
- **`ProductWarehouseMapping`** — M2M-мост: `Product` ↔ `WarehouseProduct` с коэффициентом

### Логика
- При создании `WarehouseProduct` авто-создаётся `WarehouseStockBalance` (сигнал)
- При `WarehouseStockMovement` авто-обновляется остаток (IN → +, OUT → −)
- При `WarehouseInventoryAdjustment` авто-обновляется остаток + запись в журнал
- **Авто-списание при продажах:** при `Order` (статус DELIVERED) и `SubjectContract` (SELL) через маппинг списывается `coefficient × quantity` из `WarehouseStockBalance`
- **Закупки (BUY):** приходуют складские продукты через маппинг

### Сигналы
Отдельный файл `warehouse_signals.py` (подключён в `apps.py`). Старый контур `StockBalance`/`StockMovement`/`InventoryAdjustment` и его сигналы **полностью удалены**.

### API
- `/api/warehouse/warehouse-products/` — CRUD складских продуктов
- `/api/warehouse/warehouse-stock/` — остатки
- `/api/warehouse/warehouse-movements/` — журнал + приход/расход
- `/api/warehouse/warehouse-adjustments/` — корректировки
- `/api/warehouse/warehouse-mappings/` — маппинги

### Админка
- `WarehouseProductAdmin` с Inline `ProductWarehouseMappingInline` — связь складского продукта с продуктами ассортимента
- `WarehouseStockBalanceAdmin`, `WarehouseStockMovementAdmin` — только просмотр
- `WarehouseInventoryAdjustmentAdmin` — ручные корректировки
- `ProductWarehouseMappingAdmin` — сводное управление связями

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

## Автономный контур складских продуктов (WarehouseProduct)

**Назначение:** Учёт складских продуктов **отдельно** от ассортимента `Product`. Полностью автономная сущность без наследования и без FK на `Product`.

### Модели
- **`WarehouseProduct`** — складской продукт (`name`, `sku`, `unit`, `is_active`)
- **`WarehouseStockBalance`** — остатки (OneToOne к `WarehouseProduct`)
- **`WarehouseStockMovement`** — журнал приход/расход (IN/OUT)
- **`WarehouseInventoryAdjustment`** — ручные корректировки (INC/DEC/SET)
- **`ProductWarehouseMapping`** — M2M-мост: `Product` ↔ `WarehouseProduct` с коэффициентом

### Логика
- При создании `WarehouseProduct` авто-создаётся `WarehouseStockBalance` (сигнал)
- При `WarehouseStockMovement` авто-обновляется остаток (IN → +, OUT → −)
- При `WarehouseInventoryAdjustment` авто-обновляется остаток + запись в журнал
- **Авто-списание при продажах:** при `Order` (статус DELIVERED) и `SubjectContract` (SELL) через маппинг списывается `coefficient × quantity` из `WarehouseStockBalance`
- **Закупки (BUY):** приходуют складские продукты через маппинг

### Сигналы
Отдельный файл `warehouse_signals.py` (подключён в `apps.py`). Существующие сигналы в `signals.py` **не тронуты** — старый контур `StockBalance` работает параллельно.

### API
- `/api/warehouse/warehouse-products/` — CRUD складских продуктов
- `/api/warehouse/warehouse-stock/` — остатки
- `/api/warehouse/warehouse-movements/` — журнал + приход/расход
- `/api/warehouse/warehouse-adjustments/` — корректировки
- `/api/warehouse/warehouse-mappings/` — маппинги

### Админка
- `WarehouseProductAdmin` с Inline `ProductWarehouseMappingInline` — связь складского продукта с продуктами ассортимента
- `WarehouseStockBalanceAdmin`, `WarehouseStockMovementAdmin` — только просмотр
- `WarehouseInventoryAdjustmentAdmin` — ручные корректировки
- `ProductWarehouseMappingAdmin` — сводное управление связями

## Связи
- `Product` ← `StockBalance`
- `Contract` ← `StockMovement`
- `Worker` ← `Garage`
- `Product` ← `InventoryAdjustment`
- `Product` ↔ `WarehouseProduct` (M2M через `ProductWarehouseMapping`)

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