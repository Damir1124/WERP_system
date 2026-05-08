# Prompt — WERP / Osnova 2.0

> Используй этот промпт как стартовое сообщение в Cursor при начале работы над любой P-задачей.
> Подставь нужный приоритет в блоке `[ЗАДАЧА]` и убери инструкцию в скобках.

---

## Системный контекст (вставляй всегда)

```
Ты работаешь над проектом WERP / Osnova 2.0 — Django ERP-системой для компании по доставке питьевой воды (Самарканд, Узбекистан).

ОБЯЗАТЕЛЬНО прочитай файл CLAUDE.md в корне проекта перед любыми действиями. Этот файл — единственный источник истины об архитектуре, моделях, сигналах, соглашениях по коду и текущем состоянии задач.

Стек: Django 5.1.6, DRF 3.15.2, PostgreSQL 17, Django Channels 4.1.0, Redis, aiogram 3.x (бот).
Язык кода: Python. Язык комментариев и verbose_name: русский + английский (mixed).
```

---

## [ЗАДАЧА] — выбери нужный блок и вставь после системного контекста

### Если работаешь над P3 (Telegram Bot + Mini App)

```
Реализуй задачу [P3] из CLAUDE.md: Telegram Mini App с тремя ролевыми профилями и aiogram-бот.

Начни с этапа: [ВЫБЕРИ ОДИН ИЗ НИЖЕ]
```

**Доступные этапы P3 (выбери один за раз):**

```
Этап P3-A — Модели и миграции:
  - Добавить Worker.tg_id (BigIntegerField, unique, null=True)
  - Добавить Worker.is_admin (BooleanField, default=False)
  - Добавить Order.assigned_courier (FK → Worker, null=True, SET_NULL)
  - Создать и применить миграции
  Файлы: apps/workers/models.py, apps/logistics/models.py

Этап P3-B — bot_bridge API (идентификация и курьер):
  - GET /api/bot/identify/?tg_id=<id> → роль + имя
  - GET /api/bot/courier/pool/ → PENDING заказы
  - POST /api/bot/courier/order/<id>/assign/ → взять заказ
  - GET /api/bot/courier/trip/current/ → рейс + summary (empty_expected, cash_expected, card_expected)
  - GET /api/bot/courier/colleagues/ → курьеры с открытой сменой сегодня
  Файлы: apps/bot_bridge/views.py, serializers.py, urls.py, permissions.py

Этап P3-C — bot_bridge API (клиент и админ):
  - GET /api/bot/client/products/
  - POST /api/bot/client/order/
  - GET /api/bot/client/orders/
  - GET /api/bot/client/order/<id>/status/ (+ инфо о курьере)
  - GET /api/bot/admin/stats/today/
  - GET /api/bot/admin/shifts/
  - GET /api/bot/admin/stock/alerts/
  - GET /api/bot/admin/orders/recent/
  Файлы: apps/bot_bridge/views.py, serializers.py, urls.py

Этап P3-D — Уведомления (notify.py):
  - async notify_client_order_accepted(order) — уведомить клиента о курьере
  - async notify_courier_new_order(courier, order) — уведомить курьера о новом заказе в пул
  Файлы: apps/bot_bridge/notify.py

Этап P3-E — aiogram бот (структура и авторизация):
  - Создать структуру tg_bot/ (см. CLAUDE.md раздел 3.1)
  - bot.py, config.py, __main__.py
  - middlewares/auth.py: определить роль через /api/bot/identify/
  - /start хэндлер с ветвлением по роли
  Файлы: tg_bot/ (новая директория)

Этап P3-F — aiogram роутеры:
  - routers/courier.py: открыть смену, открыть рейс, кнопка Mini App
  - routers/client.py: приветствие, кнопка Mini App, уведомления
  - routers/admin.py: /stats, /shifts, /stock, /orders команды
  - keyboards/: inline и reply клавиатуры для каждой роли
  Файлы: tg_bot/routers/, tg_bot/keyboards/

Этап P3-G — Mini App фронтенд (курьер):
  - React SPA: Pool.jsx, Trip.jsx, Shifts.jsx, Colleagues.jsx
  - TripSummary компонент: счётчики пустых/наличных/карты
  - API-клиент с заголовком X-Telegram-ID
  Файлы: frontend/courier/

Этап P3-H — Mini App фронтенд (клиент):
  - React SPA: Catalog.jsx, OrderForm.jsx, MyOrders.jsx
  - Telegram WebApp инициализация (window.Telegram.WebApp)
  Файлы: frontend/client/

Этап P3-WS — WebSockets (DashboardConsumer):
  - DashboardConsumer в accounting/consumers.py
  - Отправка обновлений Finance при post_save FinancialTransactions
  - routing.py + asgi.py
  Файлы: apps/accounting/consumers.py, routing.py, config/asgi.py
```

---

### Если работаешь над P1

```
Реализуй задачу [P1] из CLAUDE.md: исправить баг card_profit в update_finance_record.

Задача: в apps/accounting/utils.py функция update_finance_record считает card_profit
как сумму card_amount для ВСЕХ транзакций, включая MINUS.
Нужно фильтровать только транзакции с type=PLUS.

Файл: apps/accounting/utils.py, строка ~33.
После правки убедись что сигналы в accounting/signals.py вызывают update_finance_record корректно.
Тесты: вручную создай MINUS-транзакцию с card_amount > 0 и проверь что Finance.card_profit не изменился.
```

---

### Если работаешь над P2 (Генератор путевых листов)

```
Реализуй задачу [P2] из CLAUDE.md: генератор путевых листов .docx.

Функция generate_waybill(courier_id: int, date: date) -> bytes в apps/warehouse/utils.py.
Данные для документа берутся из:
  - Worker (ФИО курьера)
  - Garage (авто: vehicle_name, plate_number)
  - CourierTrip (рейсы за дату, full_loaded, get_trip_summary())
  - Order (заказы рейса: клиент, адрес, продукт, кол-во, оплата)

Библиотека: python-docx (уже в requirements.txt).
Подключить endpoint: GET /api/warehouse/waybill/<courier_id>/?date=YYYY-MM-DD
  → возвращает файл .docx как FileResponse.
Файлы: apps/warehouse/utils.py, apps/warehouse/views.py, apps/warehouse/urls.py
```

---

### Если работаешь над P4

```
Реализуй задачу [P4] из CLAUDE.md: подключение URL-маршрутов для всех приложений.

Создай urls.py для каждого приложения согласно спецификации в CLAUDE.md раздел 4.2.
Обнови WERP_system/urls.py — добавь все include и media-маршруты.
Для каждого нового urls.py также создай заглушки views.py если их нет.
Порядок: сначала создай все urls.py, затем обнови главный роутер, затем проверь
  что python manage.py check не выдаёт ошибок.
Файлы: apps/logistics/urls.py, apps/warehouse/urls.py, apps/clients/urls.py,
  apps/workers/urls.py, apps/products/urls.py, WERP_system/urls.py
```

---

### Если работаешь над P5

```
Реализуй задачу [P5] из CLAUDE.md: полная настройка Django Admin для всех моделей.

Реализуй согласно спецификации в CLAUDE.md раздел 5.2. Для каждого приложения:
  - clients/admin.py: ClientAdmin с fieldsets и readonly_fields
  - products/admin.py: ProductAdmin с list_editable
  - workers/admin.py: WorkerAdmin + GarageInline
  - warehouse/admin.py: Stock, Movement, Garage, InventoryAdjustment Admin
  - logistics/admin.py: CourierShiftAdmin (+ CourierTripInline), CourierTripAdmin (+ OrderInline), OrderAdmin
  - accounting/admin.py: Contract (+ SubjectContractInline), Installment, Salary (+ SalaryPaymentInline), FinancialTransactions, Finance

Добавить в WERP_system/urls.py (или apps/__init__.py):
  admin.site.site_header = "Osnova 2.0 — ERP"
  admin.site.site_title = "WERP Admin"
  admin.site.index_title = "Панель управления"

Делай по одному приложению за раз, начни с clients.
```

---

### Если работаешь над P6

```
Реализуй задачу [P6] из CLAUDE.md: веб-дашборд (Templates + Bootstrap 5).

Создай приложение apps/dashboard/ согласно спецификации в CLAUDE.md раздел 6.
Порядок реализации:
  1. apps/dashboard/__init__.py, apps.py, urls.py
  2. templates/dashboard/base.html (navbar + sidebar)
  3. apps/dashboard/views.py — все 5 view-классов
  4. templates/dashboard/index.html (Finance карточки + таблицы)
  5. templates/dashboard/shifts.html + shift_detail.html
  6. templates/dashboard/stock.html + finance.html
  7. static/css/dashboard.css
  8. Подключить в settings.py и WERP_system/urls.py

Не используй JS-фреймворки — только Bootstrap 5 CDN + минимальный vanilla JS.
Для WebSocket-обновлений (live данные) — смотри P3-WS этап.
```

---

## Универсальные правила (добавляй всегда в конец промпта)

```
ПРАВИЛА РАБОТЫ:

1. СНАЧАЛА читай CLAUDE.md, особенно раздел «Важные особенности кода» и граф зависимостей.
   Никогда не нарушай направление импортов: clients/products/workers не импортируют из других apps.

2. СИГНАЛЫ: используй @receiver декоратор. Никогда не вызывай instance.save() внутри
   post_save того же sender — только queryset.update() или update_fields=[...].

3. МИГРАЦИИ: после каждого изменения модели — python manage.py makemigrations <appname>.
   Никогда не редактируй миграции вручную.

4. ИМЕНОВАНИЕ:
   - Модели: PascalCase существительное
   - Поля: snake_case
   - Сигналы: {action}_{model}_{event}
   - verbose_name: на русском

5. АВТОРИЗАЦИЯ БОТА: курьер идентифицируется по заголовку X-Telegram-ID: <tg_id>.
   Worker.tg_id — для курьеров/администраторов. Client.tg_id — для клиентов.

6. ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ: если нужна ссылка из workers на warehouse — используй
   строковую ссылку 'warehouse.Garage', не прямой импорт.

7. ОДИН ФАЙЛ ЗА РАЗ: не пиши весь модуль сразу. Покажи план → жди подтверждения →
   реализуй по одному файлу → проверяй на ошибки импортов.

8. ПОСЛЕ КАЖДОГО ФАЙЛА: запускай python manage.py check (для Django-файлов) и
   сообщай о любых предупреждениях или ошибках.

9. СУЩЕСТВУЮЩИЙ КОД: перед созданием нового файла проверь есть ли он уже в проекте
   командой find . -name "filename.py" | head -5.

10. УСТАРЕВШИЕ МОДЕЛИ: не трогай DeliveryLog, DeliveryLogMove, DeliveryJournal —
    они оставлены для совместимости с существующей БД.
```
