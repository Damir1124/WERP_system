# Модуль Bot Bridge (Мост для Telegram-бота)

**Создан:** 2026-04-27  
**Статус:** Реализован (P2)  
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
| GET | `/api/bot/courier/deliveries/` | Список доставок курьера |
| GET | `/api/bot/courier/deliveries/today/` | Доставки на сегодня |
| POST | `/api/bot/courier/deliveries/confirm/` | Подтверждение доставки |
| POST | `/api/bot/courier/deliveries/update-quantity/` | Изменение количества товара |
| GET | `/api/bot/products/` | Каталог продуктов |
| GET | `/api/bot/clients/` | Поиск клиентов |
| POST | `/api/bot/courier/deliveries/{id}/mark-delivered/` | Пометка доставки как выполненной |

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

## Ограничения и планы развития
1. **Нет поля `tg_id` в Worker** — временное решение использует `id`.
2. **Отсутствует веб‑сокет уведомление** — бот должен опрашивать API (polling).
3. **Нет валидации геопозиции** — координаты клиента не проверяются.
4. **В будущем:** Добавить WebSocket‑уведомления (P3), Telegram Mini App (P3), автоматическое распределение заказов (P3).

## Ссылки
- [[docs/Index|Главный индекс]]
- [[CLAUDE.md|Архитектурный справочник]]
- [[docs/Concepts/TelegramBotAuth|Авторизация Telegram бота]]