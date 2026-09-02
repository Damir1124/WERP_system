# Концепт: Разделение контуров учёта (Product vs WarehouseProduct)

> **Проблема:** В ERP-системе учёт продуктов ведётся в таблице `Product` (ассортимент: вода, тара, кулеры, аксессуары). Потребовалось вести учёт **складских продуктов** отдельно, не пересекаясь с `Product`, но при этом автоматически списывать складские остатки при продажах ассортимента.

## Почему нельзя просто добавить поля в Product?

`Product` используется в **54 местах** проекта: логистика (`OrderItem`), бухгалтерия (`SubjectContract`, `Installment`), бот (`bot_bridge`), дашборд. Любое изменение его структуры или поведения сигналов рискует сломать существующий учёт. Поэтому складской продукт — **полностью автономная сущность**.

## Варианты архитектуры (сравнение)

### 1. Полностью отдельная таблица `WarehouseProduct`
Своя модель без связи с `Product`, свои модели учёта.
- ✅ Полная изоляция, нулевой риск
- ❌ Нет связи с ассортиментом (нельзя авто-списывать при продажах)

### 2. Наследование `class WarehouseProduct(Product)` (MTI)
- ✅ Наследует поля
- ❌ `Product.objects.all()` не вернёт наследников; сигналы `post_save` на `Product` сработают и для наследника (конфликт с `create_stock_balance_product`); усложняет запросы. **Не рекомендовано.**

### 3. Отдельная модель + FK на `Product`
- ✅ Изоляция + возможность связи
- ❌ FK может быть пустым, нужна валидация; один Product → один складской продукт (недостаточно гибко)

### 4. GenericForeignKey (ContentType)
- ❌ Избыточен для двух типов сущностей, усложняет запросы и админку

## Выбранное решение: автономный контур + M2M-мост

```
Product (ассортимент) ──┐
                        ├── ProductWarehouseMapping (M2M, coefficient) ── WarehouseProduct (склад)
SubjectContract/Order ──┘
```

**Ключевая идея:** два независимых контура учёта, соединённых **промежуточной моделью** `ProductWarehouseMapping` с коэффициентом. Это позволяет:
- одному `Product` списывать **несколько** складских продуктов (продажа "Вода + тара" списывает и тару, и крышку);
- одному `WarehouseProduct` покрывать несколько продуктов ассортимента;
- задавать коэффициент (1 проданный продукт = N единиц складского).

## Модели

| Модель | Назначение |
|---|---|
| `WarehouseProduct` | Автономный складской продукт (`name`, `sku`, `unit`, `is_active`) |
| `WarehouseStockBalance` | Остатки (OneToOne к `WarehouseProduct`) |
| `WarehouseStockMovement` | Журнал приход/расход (IN/OUT) |
| `WarehouseInventoryAdjustment` | Ручные корректировки (INC/DEC/SET) |
| `ProductWarehouseMapping` | M2M-мост: `product` + `warehouse_product` + `coefficient` |

## Сигналы (паттерн)

Отдельный файл `warehouse_signals.py` — **не трогаем** существующий `signals.py`:

| Событие | Действие |
|---|---|
| `post_save WarehouseProduct` (created) | Создать `WarehouseStockBalance` |
| `post_save WarehouseStockMovement` | Обновить остаток (IN → +, OUT → −) |
| `post_save WarehouseInventoryAdjustment` | Обновить остаток + запись в журнал |
| `post_save Order` (DELIVERED) | Через маппинг списать `coefficient × quantity` |
| `post_save SubjectContract` (SELL) | То же списание |
| `post_save SubjectContract` (BUY) | Оприходовать через маппинг |

**Почему отдельный файл:** существующие сигналы в `signals.py` работают со старым контуром `StockBalance`. Новый контур — параллельный. Разделение файлов предотвращает случайные регрессии и упрощает ревью.

## Почему OneToOne для остатков?

В старом `StockBalance` FK на `Product` допускает дубли (баг: два баланса на один продукт). Для нового контура использован `OneToOneField` — у каждого складского продукта ровно один баланс. Это гарантирует целостность на уровне БД.

## Админка как интерфейс связи

`ProductWarehouseMappingInline` в `WarehouseProductAdmin` — прямо в карточке складского продукта выбираем, какие продукты ассортимента он покрывает и с каким коэффициентом. Это и есть "интерфейс, связывающий продажи продукта с изменением количества на складе".

## API

| Эндпоинт | Назначение |
|---|---|
| `/api/warehouse/warehouse-products/` | CRUD складских продуктов |
| `/api/warehouse/warehouse-stock/` | Остатки |
| `/api/warehouse/warehouse-movements/` | Журнал + приход/расход |
| `/api/warehouse/warehouse-adjustments/` | Корректировки |
| `/api/warehouse/warehouse-mappings/` | Маппинги |

## Итог

- ✅ Складские продукты хранятся отдельно, не пересекаются с `Product`
- ✅ Приход/расход/остатки — через `WarehouseStockMovement` и `WarehouseStockBalance`
- ✅ Существующий учёт `Product` работает без изменений (сигналы не тронуты)
- ✅ Взаимодействие — через `ProductWarehouseMapping` (M2M с коэффициентом)

[[Index]] | [[Modules_Warehouse]] | [[Modules_Products]]