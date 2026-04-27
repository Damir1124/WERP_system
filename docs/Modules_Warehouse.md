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

## Логика
- Автоматическое списание товаров при продаже
- Маппинг товаров (BOTTLE → BOTTLE_20L)
- Отслеживание остатков в реальном времени

## Сигналы
- `post_save` в `logistics` → списание со склада
- `post_save` в `accounting` → обновление баланса

## Задачи
- Генератор путевых листов (.docx)
- Ручная корректировка склада через админку

## Связи
- `Product` ← `StockBalance`
- `Contract` ← `StockMovement`
- `Worker` ← `Garage`

[[Index]] | [[Modules_Accounting]] | [[Modules_Logistics]]