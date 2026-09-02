# Концепция: Полная очистка проекта (2026-08-31)

## Зачем это нужно в нашем проекте

Проект WERP развивался итеративно: добавлялись новые модели (P0: `CourierShift → CourierTrip → Order`), новые API-эндпоинты, новые роутеры бота. При этом **старый код не удалялся** — он помечался как «Deprecated» и оставался в репозитории. Это привело к:

1. **Дубликатам** — один и тот же класс определён дважды (например, `CourierColleaguesView`), второй молча переопределяет первый.
2. **Мёртвому коду** — роутеры, которые не подключены в `bot.py`, сериализаторы, которые никто не вызывает.
3. **Мусору** — логи сборки, разовые скрипты, файлы в папке `None` (ошибка пути загрузки).
4. **Устаревшим полям** — `Client.address` помечен как «устарело» ещё в миграции `0005`, но продолжал жить в модели и API.

## Как это работает (с нуля)

### Принцип: «Источник правды» (Single Source of Truth)

В любой системе, которая развивается, должен быть **один** источник правды для каждой сущности:

- **Модели** — `Order` (не `DeliveryJournal`), `ClientAddress` (не `Client.address`).
- **Валидация телефона** — `apps/bot_bridge/phone_validator.py` (не копия в `tg_bot/utils/`).
- **View** — один класс на один URL (не два класса с одинаковым именем).

Когда появляется дубликат, Python не выдаёт ошибку — он просто **переопределяет** первый класс вторым. Это самая опасная форма дубликата: код «работает», но работает не тот класс, который вы читаете.

### Что было удалено и почему

| Категория | Что удалено | Почему |
|-----------|-------------|--------|
| Корневые файлы | `check_products.py`, `courier_full_screens_v2.html`, `dsh-docker-helper.py`, `README-icons.md` | Разовые скрипты и макеты, не используются в рантайме |
| Устаревшие view | `CourierDeliveryListView`, `DeliveryConfirmationView`, `UpdateQuantityView`, `TodayDeliveriesView`, `MarkAsDeliveredView`, `PublicProductListView`, `ClientOrderView` | Все возвращали `410 Gone` — «заглушки» для старых клиентов, которые уже перешли на новые эндпоинты |
| Устаревшие сериализаторы | `DeliveryConfirmationSerializer`, `QuantityUpdateSerializer`, `OrderCreateSerializer` | Ссылались на удалённые модели `DeliveryJournal` |
| Дубликаты | Второй `CourierColleaguesView` (строки 1837+), `tg_bot/utils/phone_validator.py` | Дубликат класса молча переопределял рабочий; копия валидатора расходилась с оригиналом |
| Неиспользуемые модули | `bot_bridge/models.py`, `bot_bridge/signals.py`, `tg_bot/routers/client_order.py`, `placeholder.html`, `templates/miniapp/` | Пустые файлы-заглушки; роутер не подключён в `bot.py`; старые сборки SPA |
| Мусор | `frontend/courier/*.txt`, `media/contracts/None/` | Логи сборки esbuild; файлы, загруженные в несуществующую папку `None` |
| Разовые скрипты | `tests/tg_bot/*`, `tests/logistics/check_*.py`, `FINAL_REPORT_3.0.1.md` | Ручные проверки с захардкоженными tg_id, не являются pytest-тестами |
| Устаревшие поля | `Client.address`, пустой `Order.save()` | `Client.address` заменён на `ClientAddress`; `Order.save()` был заглушкой |

### Почему миграции НЕ удалялись

Миграции `logistics/0010_remove_legacy_models.py` и `0011_delete_deliveryjournal.py` уже **применены к БД**. Удаление файла миграции не откатит БД — оно лишь сломает историю миграций (`django_migrations` таблица будет ссылаться на несуществующий файл). Правильный путь — **новая миграция** для новых изменений:

```
apps/clients/migrations/0007_remove_client_address.py
    - Remove field address from client
```

## Ловушки и частые ошибки

1. **Удаление поля модели без миграции** — Django не выдаст ошибку при `check`, но упадёт при обращении к полю в рантайме. Всегда запускай `makemigrations` после изменения `models.py`.
2. **Удаление «Deprecated» view** — перед удалением проверь, что старые клиенты (Mini App, бот) не вызывают эти URL. В нашем случае фронтенд использует только `/api/bot/*` новые эндпоинты.
3. **Дубликат класса** — если видишь два класса с одним именем в одном файле, это почти всегда баг. Python переопределит первый вторым.
4. **Копия утилиты** — если утилита скопирована в два места, они рано или поздно разойдутся (в нашем случае в копии осталась устаревшая проверка кода оператора). Единый источник правды — `apps/bot_bridge/phone_validator.py`.

## В нашем коде

- [`apps/bot_bridge/views.py`](../../apps/bot_bridge/views.py) — после удаления дубликата остался один `CourierColleaguesView` (строки ~1750).
- [`apps/bot_bridge/serializers.py`](../../apps/bot_bridge/serializers.py) — удалены 3 устаревших сериализатора.
- [`apps/clients/models.py`](../../apps/clients/models.py) — поле `address` удалено, адреса только через `ClientAddress`.
- [`apps/clients/migrations/0007_remove_client_address.py`](../../apps/clients/migrations/0007_remove_client_address.py) — новая миграция.
- [`apps/bot_bridge/phone_validator.py`](../../apps/bot_bridge/phone_validator.py) — единый источник правды для валидации телефона.

## Связанные концепции

- [[Concepts_ProjectConfig|Конфигурация проекта]]
- [[Concepts_WarehouseProductSeparation|Разделение контуров учёта]] — тот же принцип «один источник правды»