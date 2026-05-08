# Модуль Bot Bridge (Мост для Telegram-бота)

**Создан:** 2026-04-27
**Обновлён:** 2026-05-07
**Статус:** Реализован (P0 адаптирован, P3 частично)
**Зависимости:** `rest_framework`, `apps.logistics`, `apps.clients`, `apps.products`, `apps.workers`

## Назначение
Приложение `bot_bridge` служит API-шлюзом между Telegram-ботом (на Aiogram) и Django-системой. Оно предоставляет курьерам возможность:
- Получать список назначенных доставок
- Подтверждать выполнение доставки
- Изменять количество товара на месте
- Просматривать каталог продуктов
- Получать информацию о клиентах
- Управлять своим профилем

## Архитектура

### Файловая структура
```
apps/bot_bridge/
├── __init__.py
├── apps.py              # Конфигурация приложения
├── models.py            # (пока пустой, для будущих моделей)
├── serializers.py       # Сериализаторы DRF
├── views.py             # APIView-классы
├── permissions.py       # Кастомные permissions
└── urls.py              # Маршруты API
```

### Маршруты API
Все эндпоинты доступны по префиксу `/api/bot/`:

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/api/bot/courier/profile/` | Профиль курьера |
| GET | `/api/bot/courier/deliveries/` | Список доставок курьера (старая модель) |
| GET | `/api/bot/courier/deliveries/today/` | Доставки на сегодня (старая модель) |
| POST | `/api/bot/courier/deliveries/confirm/` | Подтверждение доставки (старая модель) |
| POST | `/api/bot/courier/deliveries/update-quantity/` | Изменение количества товара (старая модель) |
| GET | `/api/bot/products/` | Каталог продуктов |
| GET | `/api/bot/clients/` | Поиск клиентов |
| POST | `/api/bot/courier/deliveries/{id}/mark-delivered/` | Пометка доставки как выполненной (старая модель) |
| **Новые эндпоинты для моделей P0** | | |
| GET | `/api/bot/courier/shifts/` | Список смен курьера |
| GET | `/api/bot/courier/trips/` | Список рейсов активной смены |
| GET | `/api/bot/courier/trips/{trip_id}/orders/` | Заказы рейса |
| POST | `/api/bot/courier/orders/confirm/` | Подтверждение заказа (P0) |
| POST | `/api/bot/courier/orders/update-quantity/` | Изменение количества в заказе (P0) |
| POST | `/api/bot/courier/orders/create/` | Создание нового заказа в рейсе |

## Авторизация
Курьер аутентифицируется через **Telegram ID**, который передаётся в заголовке `X-Telegram-ID`.

### Permission-класс `IsCourier`
1. Извлекает `tg_id` из заголовка
2. Ищет `Worker` с таким `tg_id` (поле пока отсутствует, временно используется `id`)
3. Проверяет, что сотрудник имеет тип `COURIER`
4. При успехе добавляет объект `courier` в `request`

**Важно:** Для полноценной работы необходимо добавить поле `tg_id` в модель `Worker` (задача P1).

## Сериализаторы

### `DeliveryJournalSerializer`
Представляет журнал доставки с вложенными продуктами (`DeliveryJournalProductsSerializer`).

Поля:
- `id`, `courier`, `courier_name`, `date`
- `card_price`, `total_price`
- `products` (массив строк журнала)

### `ProductSerializer`
Каталог товаров. Включает `type_product_display` для читаемого отображения типа.

### `ClientSerializer`
Данные клиента, включая геопозицию (`latitude`, `longitude`) и `tg_id`.

### `DeliveryConfirmationSerializer`
Валидатор для подтверждения доставки:
- `delivery_journal_id` (int)
- `confirmed` (bool)
- `actual_quantity` (int, опционально)
- `note` (str, опционально)

### Новые сериализаторы для моделей P0
API адаптировано для работы с моделями `CourierShift`, `CourierTrip`, `Order` из `apps/logistics/models.py`.

#### `OrderSerializer`
Сериализатор для заказа (модель `Order`). Включает читаемые поля:
- `product_name`, `client_name`
- `status_display`, `payment_type_display`, `container_op_display`
- Все основные поля модели

#### `CourierTripSerializer`
Сериализатор для рейса курьера. Включает:
- `shift_id` (ID смены)
- `status_display`
- Вложенные `orders` (список заказов)

#### `CourierShiftSerializer`
Сериализатор для смены курьера. Включает:
- `courier_name`
- `status_display`
- Вложенные `trips` (список рейсов)

#### `OrderConfirmationSerializer`
Валидатор для подтверждения заказа (P0):
- `order_id` (int)
- `confirmed` (bool)
- `container_op` (выбор из `Order.ContainerOp.choices`, опционально)
- `note` (str, опционально)

#### `OrderQuantityUpdateSerializer`
Валидатор для изменения количества в заказе:
- `order_id` (int)
- `new_quantity` (int, min_value=1)

#### `OrderCreateModelSerializer`
Сериализатор для создания заказа курьером (ModelSerializer). Проверяет, что рейс принадлежит текущему курьеру.

## Views (логика)

### `CourierDeliveryListView`
Возвращает доставки курьера начиная с текущей даты. Использует `IsCourier` permission.

### `DeliveryConfirmationView`
Обрабатывает подтверждение или отмену доставки. Если передано `actual_quantity`, обновляет количество в соответствующей строке продукта (логика требует доработки).

### `UpdateQuantityView`
Изменяет количество в `DeliveryJournalProducts`. Автоматически пересчитывает цену и обновляет итоги журнала через сигналы.

### `ProductListView`
Каталог всех продуктов, отсортированный по типу и имени.

### `ClientInfoView`
Поиск клиентов по телефону или адресу (подстрока).

### Новые представления для моделей P0

#### `CourierShiftListView`
Возвращает список смен курьера (отсортированные по дате). Использует `IsCourier` permission.

#### `CourierTripListView`
Возвращает список рейсов для активной (открытой) смены курьера. Если активной смены нет, возвращает `{"active_shift": false}`.

#### `OrderListView`
Возвращает список заказов для конкретного рейса. Проверяет, что рейс принадлежит текущему курьеру.

#### `OrderConfirmationView`
Подтверждение или отмена заказа (P0). При подтверждении:
- Обновляет статус заказа на `DELIVERED`
- Устанавливает `delivered_at = timezone.now()`
- Записывает операцию с тарой (`container_op`) и примечание

#### `OrderQuantityUpdateView`
Изменение количества в заказе. Автоматически пересчитывает цену (через `save()` модели `Order`).

#### `CreateOrderView`
Создание нового заказа в рейсе. Использует `OrderCreateModelSerializer` с проверкой принадлежности рейса курьеру.

## Интеграция с системой

### Сигналы
При изменении `DeliveryJournalProducts` срабатывают существующие сигналы в `logistics/signals.py` и `warehouse/signals.py`, что обеспечивает:
- Автоматический пересчёт `total_price` и `card_price` в `DeliveryJournal`
- Списание тары со склада через `PRODUCT_MAP` (BOTTLE_20L → BOTTLE)
- Создание финансовой транзакции в `accounting`

### Зависимости от других задач
1. **P1: Добавить tg_id в Worker** — без этого авторизация работает в тестовом режиме (использует `id` вместо `tg_id`).
2. **P1: Добавить FK Client в DeliveryJournal** — пока связь клиента с доставкой отсутствует, но это не мешает базовой работе.
3. **DRF установлен** — добавлен в `requirements.txt` и `INSTALLED_APPS`.

## Пример запроса
```bash
curl -X GET http://localhost:8000/api/bot/courier/deliveries/today/ \
  -H "X-Telegram-ID: 123456789"
```

Ответ:
```json
[
  {
    "id": 42,
    "courier": 5,
    "courier_name": "Иванов Иван",
    "date": "2026-04-27",
    "card_price": 15000,
    "total_price": 30000,
    "products": [
      {
        "id": 101,
        "product": 2,
        "product_name": "Вода 20L с тарой",
        "quantity": 3,
        "price": 15000,
        "payment_type": "CH",
        "payment_type_display": "Наличные"
      }
    ]
  }
]
```

## Реализация P3: Telegram Mini App и aiogram-бот

**Выполнено (этап 3.1):**

1. **Архитектура бота (aiogram 3.x)** — создана структура `tg_bot/`:
   - `tg_bot/__main__.py` — точка входа с поддержкой polling/webhook
   - `tg_bot/config.py` — конфигурация через переменные окружения (BOT_TOKEN, USE_WEBHOOK, DJANGO_API_URL)
   - `tg_bot/bot.py` — инициализация бота, диспетчера, подключение middleware и роутеров
   - `tg_bot/middlewares/auth.py` — `AuthMiddleware` для идентификации пользователя через Django API (`/api/bot/identify/`)
   - `tg_bot/routers/` — отдельные роутеры для трёх ролей: курьер, клиент, администратор
   - `tg_bot/keyboards/` — reply‑ и inline‑клавиатуры для каждой роли

2. **Расширение модели Worker** — добавлены поля:
   - `tg_id` (BigIntegerField, unique=True, null=True) — для связи с Telegram ID
   - `is_admin` (BooleanField) — флаг администратора бота
   - Миграция `workers.0002_worker_is_admin_worker_tg_id` создана и применена.

3. **Endpoint идентификации** — `IdentifyView` в `bot_bridge/views.py`:
   - GET `/api/bot/identify/?tg_id=...` возвращает `{"role": "courier"|"client"|"admin", "name": "...", "id": ..., "worker_type": "..."}`
   - Используется middleware бота для автоматического определения роли пользователя.

4. **Роутеры и команды**:
   - **Курьер:** `/start`, `/deliveries`, `/profile`, `/shift`
   - **Клиент:** `/start`, `/catalog`, `/order`, `/status`
   - **Администратор:** `/start`, `/stats`, `/broadcast`, `/users`

5. **Конфигурация и тестирование**:
   - Обновлён `.env` с переменными бота
   - Создан `requirements_bot.txt` с зависимостями aiogram, aiohttp, python‑dotenv
   - Протестирован endpoint идентификации с тестовым Worker (tg_id=123456789)

**Что осталось сделать (следующие этапы P3):**
- Настройка WebSocket‑уведомлений (живой мониторинг)
- Реализация Telegram Mini App (TWA) — фронтенд для клиентов и курьеров
- Интеграция с геопозицией и автоматическим распределением заказов
- Настройка webhook для продакшена

## Ограничения и планы развития
1. **Поле `tg_id` в Worker добавлено** — теперь авторизация работает через Telegram ID.
2. **Отсутствует веб‑сокет уведомление** — бот должен опрашивать API (polling).
3. **Нет валидации геопозиции** — координаты клиента не проверяются.
4. **В будущем:** Завершить WebSocket‑уведомления (P3), Telegram Mini App (P3), автоматическое распределение заказов (P3).

## Ссылки
- [[docs/Index|Главный индекс]]
- [[CLAUDE.md|Архитектурный справочник]]
- [[docs/Concepts/TelegramBotAuth|Авторизация Telegram бота]]