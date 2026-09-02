# Роль «Оператор» в Osnova 2.0

> Создана: 2026-08-10

## Зачем нужен оператор

Оператор — сотрудник, который управляет заказами, но **не выезжает на доставку**. В отличие от курьера, оператору не нужны смены, рейсы, учёт тары и подтверждение доставок.

Его задачи:
- Создавать заказы (по телефону от клиента)
- Редактировать заказы в статусе PENDING (адрес, товары)
- Удалять заказы в статусе PENDING
- Просматривать пул свободных заказов
- Просматривать заказы, взятые курьерами («В процессе»)
- Видеть, какой курьер взял заказ

## Что изменилось в коде

### Backend (Django)

#### 1. Модель Worker — новый тип сотрудника

[`apps/workers/models.py`](../../apps/workers/models.py:7)

```python
class WorkerType(models.TextChoices):
    PACKER = "packer", "Упаковщик"
    COURIER = "courier", "Курьер"
    OPERATOR = "operator", "Оператор"  # <-- новый тип
    OTHER = "other", "Прочие"
```

> 💡 **Почему отдельный тип, а не флаг:** Тип сотрудника влияет на доступ к Mini App и Telegram боту. Флаг `is_admin` даёт доступ к админ-панели, а `worker_type` определяет набор экранов. Оператор не должен видеть смены/рейсы.

#### 2. Новые permission-классы

[`apps/bot_bridge/permissions.py`](../../apps/bot_bridge/permissions.py)

- **`IsOperator`** — проверяет, что `worker_type == OPERATOR`. Используется для операторских эндпоинтов (список/редактирование/удаление заказов).
- **`IsCourierOrOperator`** — пропускает и курьеров, и операторов. Используется для общих эндпоинтов (пул, коллеги, продукты, клиенты, создание заказа).

> 💡 **Почему не один permission:** `IsCourier` проверяет только курьеров. Если бы мы добавили оператора в `IsCourier`, пришлось бы менять все вьюхи. Отдельный `IsCourierOrOperator` позволяет точечно открывать доступ.

#### 3. API-эндпоинты для оператора

[`apps/bot_bridge/views.py`](../../apps/bot_bridge/views.py)

| Эндпоинт | Метод | Назначение |
|----------|-------|-----------|
| `operator/orders/` | GET | Все заказы за 24ч, фильтр `?status=PD&status=DL` |
| `operator/orders/<id>/` | GET | Детали заказа |
| `operator/orders/<id>/update/` | PATCH | Редактирование (телефон, адрес, товары, примечание) |
| `operator/orders/<id>/delete/` | DELETE | Удаление (только PENDING) |

[`apps/bot_bridge/urls.py`](../../apps/bot_bridge/urls.py:63)

#### 4. IdentifyView — новая роль

[`apps/bot_bridge/views.py:80`](../../apps/bot_bridge/views.py:80)

```python
if worker.worker_type == Worker.WorkerType.COURIER:
    role = 'admin' if worker.is_admin else 'courier'
elif worker.worker_type == Worker.WorkerType.OPERATOR:
    role = 'admin' if worker.is_admin else 'operator'
```

#### 5. Admin — отображение типа

[`apps/workers/admin.py:45`](../../apps/workers/admin.py:45)

Метод `formfield_for_choice_field` явно перечислял только три типа. Добавлен `OPERATOR`.

### Frontend (Mini App курьера)

#### 1. App.jsx — проверка роли и навигация

[`frontend/courier/src/App.jsx`](../../frontend/courier/src/App.jsx)

- **Проверка доступа:** пропускает `role === 'operator'`
- **BottomNav оператора:** Пул / Коллеги / Заказы (вместо Рейс/Смена)
- **FAB-кнопка:** показывается и для оператора
- **TopBar:** бейдж «Оператор»

#### 2. AllOrders.jsx — страница всех заказов

[`frontend/courier/src/pages/AllOrders.jsx`](../../frontend/courier/src/pages/AllOrders.jsx)

Новая страница, отображает заказы за последние 24 часа:
- Фильтр по статусу: Все / Ожидают / Доставлены / Отменены
- Использует `OrderCard` с `isOperatorView={true}`
- Кнопки «✏️ Ред.» и «🗑️ Уд.» только для PENDING

#### 3. OrderEdit.jsx — редактирование заказа

[`frontend/courier/src/pages/OrderEdit.jsx`](../../frontend/courier/src/pages/OrderEdit.jsx)

Новая страница с формой редактирования:
- Поиск клиента по телефону (как в OrderCreate.jsx)
- Выбор/ввод адреса с сохранёнными адресами
- Редактирование товаров (добавление/удаление/количество)
- Примечание к заказу
- Кнопка «💾 Сохранить изменения» (sticky)

#### 4. OrderCard — новый проп isOperatorView

[`frontend/courier/src/components/OrderCard/OrderCard.jsx`](../../frontend/courier/src/components/OrderCard/OrderCard.jsx)

- `isOperatorView` — режим отображения для оператора
- `onEdit`, `onDelete` — колбэки для кнопок
- Показывает `assigned_courier_name` для оператора

#### 5. Pool.jsx — адаптация для оператора

[`frontend/courier/src/pages/Pool.jsx`](../../frontend/courier/src/pages/Pool.jsx)

- Принимает `role` проп
- Для оператора: не запрашивает `getCurrentTrip`
- Для оператора: не показывает кнопку «Взять заказ» и предупреждение о рейсе

### Telegram Bot (tg_bot)

#### 1. Новый роутер operator.py

[`tg_bot/routers/operator.py`](../../tg_bot/routers/operator.py)

Отдельный роутер с фильтром `role == 'operator'`:
- `/start` — показывает меню оператора
- **📦 Заказы** — пул заказов (как у курьера, но без кнопки «Взять»)
- **➕ Создать заказ** — FSM-создание (без выбора оплаты, сразу Наличные)
- **📋 В процессе** — список PENDING заказов, взятых курьерами
- **🆘 Помощь** — справка

#### 2. Новый файл keyboards/operator.py

[`tg_bot/keyboards/operator.py`](../../tg_bot/keyboards/operator.py)

Клавиатура: ➕ Создать заказ | 📦 Заказы | 📋 В процессе | 🆘 Помощь

#### 3. FSM-редактирование заказа

[`tg_bot/states/operator.py`](../../tg_bot/states/operator.py)

```python
class OperatorEditOrder(StatesGroup):
    waiting_for_address_choice = State()
    waiting_for_address_text = State()
    waiting_for_product_choice = State()
    waiting_for_product_quantity = State()
    waiting_for_product_add = State()
```

FSM-поток: выбор адреса (сохранённые/новый) → редактирование товаров (+/- количество) → добавление нового товара → сохранение

#### 4. api_client.py — новый метод delete

[`tg_bot/api_client.py:87`](../../tg_bot/api_client.py:87)

Добавлен метод `delete()` для DELETE-запросов.

#### 5. bot.py — регистрация роутера

[`tg_bot/bot.py`](../../tg_bot/bot.py)

- Импорт `operator_router`
- Фильтр: `role == 'operator'`
- `dp.include_router(operator_router.router)` — после admin, до courier

#### 6. courier_create_order.py — адаптация для оператора

[`tg_bot/routers/courier_create_order.py`](../../tg_bot/routers/courier_create_order.py)

- `proceed_to_payment`: если `is_operator` в state → пропускает выбор оплаты
- `confirm_create_order`: после создания показывает меню оператора
- `cancel_order_creation`: при отмене показывает меню оператора

## Связи с другими модулями

| Модуль | Что использует |
|--------|---------------|
| `workers` | Тип `OPERATOR` |
| `bot_bridge` | API-эндпоинты, permissions |
| `logistics` | Order (чтение/редактирование/удаление) |
| `frontend/courier` | Страницы AllOrders, OrderEdit, адаптация Pool, App, OrderCard |
| `tg_bot` | Роутер operator, клавиатура, FSM, api_client |

## ⚠️ Известные особенности

- Оператор не может брать заказы в работу (только создаёт и редактирует)
- Оператор не видит смены/рейсы/подтверждение доставки
- Редактирование доступно только для PENDING-заказов
- В списке заказов показываются только за последние 24 часа
- Оператор не выбирает тип оплаты при создании — всегда «Наличные»