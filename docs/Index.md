# База знаний Osnova 2.0

## Архитектура и Модули
* [[Modules_Accounting|Модуль Финансов (Accounting)]] — логика транзакций. **P2: API для курьера реализовано**
* [[Modules_BotBridge|Мост Telegram (Bot Bridge)]] — API шлюз. **P0: API адаптировано под модели CourierShift, CourierTrip, Order**
* [[Modules_Clients|Модуль Клиентов (Clients)]] — CRM.
* [[Modules_Logistics|Модуль Логистики (Logistics)]] — ядро доставок.
* [[Modules_Warehouse|Модуль Склада (Warehouse)]] — остатки и автопарк. **P2: Генератор путевых листов и инвентаризация реализованы**
* [[Modules_Products|Модуль Продуктов (Products)]] — каталог товаров. **Добавлено поле track_inventory**
* [[Modules_Workers|Модуль Сотрудников (Workers)]] — курьеры и упаковщики.

## Разбор багов (Post-mortems)
* [[Bugs_RecursiveSignals|Бесконечный цикл в сигналах post_save]]
* [[Bugs_CardProfitCalc|Ошибка подсчета card_profit]]

## Теоретические справки
* [[Concepts_DjangoSignals|Как работают сигналы в Django]]
* [[Concepts_WebSockets|WebSockets и Django Channels]]
* [[Concepts_TelegramBotAuth|Авторизация Telegram бота через tg_id]]

## Статус выполнения задач P2
**Задача P2 выполнена полностью:**
1. ✅ **Создание приложения `bot_bridge`** - API-шлюз для Telegram-бота
2. ✅ **API эндпоинты для курьера (бонусы/штрафы)** - в модуле Accounting
3. ✅ **Генератор путевых листов (docx)** - в модуле Warehouse
4. ✅ **Инвентаризация склада через админку** - модель InventoryAdjustment

## Статус выполнения задач P0 (адаптация API)
**Адаптация API bot_bridge под модели P0 выполнена:**
1. ✅ **Изучение моделей** `CourierShift`, `CourierTrip`, `Order` в `logistics/models.py`
2. ✅ **Адаптация сериализаторов** — добавлены `OrderSerializer`, `CourierTripSerializer`, `CourierShiftSerializer`, `OrderConfirmationSerializer`, `OrderQuantityUpdateSerializer`, `OrderCreateModelSerializer`
3. ✅ **Адаптация представлений** — добавлены `CourierShiftListView`, `CourierTripListView`, `OrderListView`, `OrderConfirmationView`, `OrderQuantityUpdateView`, `CreateOrderView`
4. ✅ **Добавление URL-маршрутов** — новые эндпоинты для работы с P0
5. ✅ **Проверка корректности** — синтаксическая проверка кода
6. ✅ **Обновление документации** — раздел [[Modules_BotBridge]] дополнен информацией о P0

## Ссылки
* [CLAUDE.md](../CLAUDE.md) — архитектурный справочник проекта.
* [Roadmap](../CLAUDE.md#3-roadmap-что-делать-дальше) — приоритетные задачи.
* [Обновления P2](../CLAUDE.md#p2-создать-приложение-bot_bridge) — детали реализации задачи P2.