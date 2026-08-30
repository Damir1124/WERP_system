# Модуль Финансов (Accounting)

**Создан:** 2026-04-27 (предположительно)  
**Статус:** Реализован (ядро)  
**Зависимости:** `apps.clients`, `apps.products`, `apps.logistics`, `apps.workers`

## Назначение
Модуль `accounting` отвечает за всю финансовую логику системы:
- Учёт контрактов (доходы/расходы)
- Рассрочки клиентов
- Зарплаты сотрудников (бонусы/штрафы)
- Логирование всех денежных операций (`FinancialTransactions`)
- Дневные финансовые сводки (`Finance`)

## Архитектура

### Модели

#### `Contract` — контракты (сделки)
- `contract_type`: `BUY` (расход) / `SELL` (доход)
- `client`: ссылка на клиента (может быть `null`)
- `amount`: сумма контракта
- `file`: загруженный документ (PDF, Word, Excel, изображения)

#### `SubjectContract` — предметы контракта
- `contract`: внешний ключ на `Contract`
- `product`: товар ассортимента (может быть `null`)
- `warehouse_product`: складской продукт (комплектующие — пакеты, тара, крышки; может быть `null`)
- `quantity`: количество товара

Предмет контракта может ссылаться либо на `product` (ассортимент), либо на `warehouse_product` (комплектующие). При закупке (BUY) комплектующих складской продукт приходуется напрямую, без маппинга.

#### `Installment` — рассрочки клиентов (шапка)
- `client`: ссылка на клиента
- `amount`: общая сумма рассрочки (авто-расчёт из позиций)
- `paid_amount`: уже оплаченная сумма
- `due_date`: дата следующего платежа
- `status`: `ACTIVE`, `OVERDUE`, `CLOSED`
- Методы `make_payment()`, `check_status()`, `recalc_amount()`
- Свойство `debt` — остаток долга

#### `InstallmentItem` — позиции рассрочки (несколько товаров)
- `installment`: внешний ключ на `Installment` (related_name=`items`)
- `product`: товар
- `quantity`: количество
- `price_per_unit`: цена за единицу (авто-подстановка из `product.price`)
- `subtotal`: сумма позиции (`price_per_unit * quantity`)

Одна рассрочка может содержать несколько позиций (например, кулер + аксессуары).

#### `PaymentsInstallment` — платежи по рассрочке
- `installment`: внешний ключ на `Installment`
- `amount`: сумма взноса
- `payment_date`: дата взноса
- `created_at`: дата создания

#### `Salary` — баланс зарплаты сотрудника
- `worker`: ссылка на `Worker`
- `balance`: текущий баланс (может быть отрицательным при штрафах)
- `last_payment`: дата последней выплаты

#### `SalaryPeriod` — зарплатный период (календарный месяц)
Агрегирует все начисления и выплаты за один месяц, чтобы владелец не держал в голове: сколько выдан аванс, сколько осталось к выдаче, в какую дату зарплата.

- `worker`: ссылка на `Worker`
- `month`: первый день расчётного месяца (например, `2026-08-01`)
- `salary_amount`: фиксированный оклад за месяц (авто-начисление)
- `bonuses`: сумма бонусов за месяц
- `fines`: сумма штрафов за месяц
- `advances`: сумма выданных авансов
- `paid_salary`: сумма выплаченной зарплаты
- `salary_date`: дата, когда должна быть выплачена зарплата
- `status`: `OPEN` (открыт) / `PAID` (выплачен) / `CLOSED` (закрыт)

Свойства:
- `accrued` — начислено: `salary_amount + bonuses - fines`
- `paid_total` — выплачено: `advances + paid_salary`
- `remaining` — остаток к выдаче: `accrued - paid_total`

Метод `recalc()` пересчитывает итоги периода из платежей (через `queryset.update()`, без рекурсии) и автоматически помечает период `PAID`, если остаток ≤ 0.

#### `SalaryPayment` — выплаты зарплаты
- `salary`: ссылка на `Salary`
- `period`: ссылка на `SalaryPeriod` (подставляется автоматически по дате платежа)
- `amount`: сумма выплаты
- `payment_type`: `SALARY` (зарплата), `ADVANCE` (аванс), `FINE` (штраф), `BONUS` (бонус)
- `date`: дата выплаты

#### `FinancialTransactions` — лог всех денежных операций
- `date`: дата операции
- `type`: `PLUS` (доход) / `MINUS` (расход)
- `amount`: сумма (всегда положительная)
- `card_amount`: сумма по карте (часть `amount`)
- `source`: текстовое описание источника (например, `"Contract #42"`, `"DeliveryJournal #15"`)

#### `Finance` — дневная сводка
- `date`: дата сводки
- `income`: общий доход за день
- `consumption`: общий расход за день
- `profit`: чистая прибыль (`income - consumption`)
- `card_profit`: прибыль по безналу (сейчас считается с ошибкой — см. [[docs/Bugs_CardProfitCalc]])

## Сигналы (`accounting/signals.py`)

Сигналы автоматически создают `FinancialTransactions` и обновляют `Finance` при любых финансовых событиях:

1. **`Contract`** `post_save` / `post_delete` → создание/удаление транзакции
2. **`DeliveryJournal`** `post_save` / `post_delete` → доход от доставки
3. **`SalaryPayment`** `post_save` / `post_delete` → расход на зарплату
4. **`PaymentsInstallment`** `post_save` / `post_delete` → доход от платежа по рассрочке
5. **`FinancialTransactions`** `post_save` → вызов `update_finance_record(date)`

### Порядок срабатывания
При сохранении `DeliveryJournal`:
1. Сигналы `logistics/signals.py` пересчитывают `total_price`
2. Сигналы `warehouse/signals.py` списывают тару
3. **Сигналы `accounting/signals.py`** создают `FinancialTransactions` с `type=PLUS`
4. Вызывается `update_finance_record(date)`, который агрегирует все транзакции дня в `Finance`

## Утилиты (`accounting/utils.py`)

### `update_due_date(installment)`
Рассчитывает следующую дату платежа по рассрочке: `due_date = последний_платёж + 1 месяц`.

### `reset_balance_if_expired(salary)`
Обнуляет баланс зарплаты, если последняя выплата (`last_payment`) была в прошлом календарном месяце. В отличие от старой логики (30 дней), учитывается именно смена месяца.

### `accrue_salary_for_period(worker, month)`
Начисляет фиксированный оклад сотруднику за указанный месяц. Создаёт (или обновляет) `SalaryPeriod` с окладом из `worker.salary_amount`. Если оклад изменился — обновляет начисление за месяц.

## Авто-начисление зарплаты (management-команда)

### `accrue_salaries`
Начисляет оклад всем сотрудникам за месяц. Запуск в начале каждого месяца (например, по cron 1-го числа):

```bash
python manage.py accrue_salaries
python manage.py accrue_salaries --month 2026-08-01
```

### Авто-создание карточки зарплаты
При создании `Worker` сигнал `create_salary_for_worker` автоматически создаёт запись `Salary`. При первом платеже в месяце сигнал `update_salary_on_payment` автоматически создаёт `SalaryPeriod` и привязывает платёж к нему.

### `update_finance_record(date)` **(критическая функция)**
Агрегирует все `FinancialTransactions` за указанную дату и создаёт/обновляет запись `Finance`.

**Алгоритм:**
1. Фильтрует транзакции по `date`
2. `income = sum(t.amount for t in transactions if t.type == PLUS)`
3. `consumption = sum(t.amount for t in transactions if t.type == MINUS)`
4. `profit = income - consumption`
5. `card_profit = sum(t.card_amount for t in transactions)` **← ОШИБКА!** Суммирует card_amount для всех транзакций, включая MINUS.

**Исправление:** см. [[docs/Bugs_CardProfitCalc]].

## Интеграция с другими модулями

### `logistics` → `accounting`
`DeliveryJournal` является источником дохода. При сохранении журнала сигнал создаёт `FinancialTransactions` с `amount = total_price + card_price`.

### `warehouse` → `accounting`
Контракты типа `BUY` (покупка товара) создают расходные транзакции.

### `workers` → `accounting`
`SalaryPayment` создаёт расходную транзакцию (`type=MINUS`).

### `clients` → `accounting`
`Installment` и `PaymentsInstallment` влияют на доходы.

## Примеры использования

### Создание контракта (доход)
```python
contract = Contract.objects.create(
    contract_type=Contract.ContractType.SELL,
    client=client,
    amount=500000,
    description="Поставка воды на месяц",
    date=date.today()
)
# Автоматически создаст FinancialTransactions(type=PLUS, amount=500000)
```

### Выплата зарплаты курьеру
```python
salary = Salary.objects.get(worker=courier)
payment = SalaryPayment.objects.create(
    salary=salary,
    amount=200000,
    payment_type=SalaryPayment.PaymentType.SALARY,
    date=date.today()
)
# Автоматически создаст FinancialTransactions(type=MINUS, amount=200000)
```

### Получение дневной сводки
```python
finance = Finance.objects.get(date=date.today())
print(f"Доход: {finance.income}, Расход: {finance.consumption}, Прибыль: {finance.profit}")
```

## Ограничения и известные проблемы

1. **Ошибка подсчёта `card_profit`** — суммируются card_amount всех транзакций, а не только PLUS.
2. **Нет валидации дубликатов** — можно создать несколько `FinancialTransactions` на одно событие.
3. **Нет истории изменений** — `Finance` перезаписывается, предыдущие значения теряются.
4. **Зависимость от порядка сигналов** — если сигналы `accounting` выполняются раньше `logistics`, `total_price` может быть неактуальным.

## API эндпоинты для курьера (бонусы/штрафы) - P2 реализовано

### Назначение
API для получения курьером информации о своей зарплате, бонусах и штрафах через Telegram-бота.

### Маршруты API
Все эндпоинты доступны по префиксу `/api/accounting/`:

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/api/accounting/salary/` | Детальная информация о зарплате курьера |
| GET | `/api/accounting/salary/summary/` | Сводка по зарплате за текущий месяц |
| GET | `/api/accounting/salary/payments/` | Список всех платежей по зарплате |
| GET | `/api/accounting/salary/bonuses/` | Последние бонусы (за 30 дней) |
| GET | `/api/accounting/salary/fines/` | Последние штрафы (за 30 дней) |

### Авторизация
Используется тот же permission-класс `IsCourier` из `bot_bridge`, который проверяет `X-Telegram-ID` в заголовках.

### Сериализаторы (`accounting/serializers.py`)
- `SalaryDetailSerializer` - детальная информация о зарплате с расширенной статистикой
- `SalaryPaymentSerializer` - информация о платежах по зарплате

### Views (`accounting/views.py`)
- `SalaryDetailView` - основная информация о зарплате курьера
- `SalarySummaryView` - сводка за текущий месяц
- `SalaryPaymentsListView` - список всех платежей
- `RecentBonusesView` - последние бонусы
- `RecentFinesView` - последние штрафы

### Пример запроса
```bash
curl -X GET http://localhost:8000/api/accounting/salary/ \
  -H "X-Telegram-ID: 123456789"
```

Ответ:
```json
{
  "id": 1,
  "worker": 5,
  "worker_name": "Иванов Иван",
  "balance": 150000,
  "last_payment": "2026-04-25",
  "total_bonuses": 50000,
  "total_fines": 10000,
  "total_salary": 200000,
  "payments": [
    {
      "id": 1,
      "amount": 200000,
      "payment_type": "SA",
      "payment_type_display": "Зарплата",
      "date": "2026-04-25",
      "note": "Аванс за апрель"
    }
  ]
}
```

## API эндпоинты для рассрочки

### Маршруты API
Все эндпоинты доступны по префиксу `/api/accounting/`:

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/api/accounting/installments/?client=<id>` | Список рассрочек клиента |
| GET | `/api/accounting/installments/<id>/` | Детальная информация о рассрочке |
| POST | `/api/accounting/installments/<id>/payments/` | Создание платежа по рассрочке |

### Сериализаторы (`accounting/serializers.py`)
- `InstallmentSerializer` — шапка рассрочки с позициями и платежами
- `InstallmentItemSerializer` — позиция рассрочки (товар, количество, цена)
- `PaymentsInstallmentSerializer` — платёж по рассрочке

### Views (`accounting/views.py`)
- `InstallmentListView` — список рассрочек клиента
- `InstallmentDetailView` — детальная информация
- `InstallmentPaymentCreateView` — создание платежа (создаёт PLUS-транзакцию через сигнал)

## Рассрочка по заказу

### Связь с заказом
`Installment.order` (OneToOneField на `Order`, nullable) — рассрочка может быть привязана к конкретному заказу. Один заказ = одна рассрочка.

### Авто-генерация позиций
При создании рассрочки с `order` сигнал [`generate_items_from_order`](apps/accounting/signals.py:40) автоматически:
1. Подставляет `issued_by` из курьера заказа (`assigned_courier`), если не указан вручную
2. Создаёт `InstallmentItem` из `OrderItem` (товар, количество, цена)
3. Пересчитывает `amount` из позиций
4. **Удаляет PLUS-транзакцию заказа** — доход фиксируется только по платежам (без двойного учёта)

### Восстановление при удалении
При удалении рассрочки сигнал [`restore_order_transaction_on_installment_delete`](apps/accounting/signals.py:78) восстанавливает PLUS-транзакцию заказа (если заказ доставлен).

### Страховка от двойного учёта
В [`create_transaction_on_order`](apps/accounting/signals.py:311) добавлена проверка: если заказ уже в рассрочке — PLUS-транзакция при DELIVERED не создаётся.

### Флоу в админке
1. Открыть `/admin/accounting/installment/` → «Добавить рассрочку»
2. Выбрать **Заказ** (позиции подтянутся автоматически)
3. Указать **Кто оформил** (если не указан — подставится курьер заказа)
4. Сохранить → позиции созданы, PLUS-транзакция заказа удалена
5. Вносить платежи в inline «Платежи по рассрочке»

## Напоминание владельцу о взносе

### Функция
[`notify_owner_installment_reminder`](apps/bot_bridge/notify.py:163) отправляет напоминание всем сотрудникам с `worker_type=OWNER` и `tg_id`.

### Текст напоминания
- Клиент и номер телефона
- Продукты (позиции рассрочки)
- Сумма, оплачено, остаток долга
- Дата платежа
- **Кто оформил** (курьер/сотрудник)
- Номер заказа (если рассрочка по заказу)

### Management-команда
[`send_installment_reminders`](apps/accounting/management/commands/send_installment_reminders.py:1) — ежедневная проверка: находит активные рассрочки с `due_date = сегодня` и остатком долга > 0, отправляет напоминания.

Запуск по cron:
```bash
python manage.py send_installment_reminders
```

## Планы развития (Roadmap)
- **P1:** Исправить баг `card_profit`
- **P2:** API эндпоинты для курьера (бонусы/штрафы) - **РЕАЛИЗОВАНО**
- **P3:** WebSockets для live-мониторинга финансов

## Ссылки
- [[docs/Index|Главный индекс]]
- [[docs/Bugs_CardProfitCalc|Ошибка подсчета card_profit]]
- [[docs/Modules_Clients|Модуль Клиентов]]
- [[docs/Modules_Logistics|Модуль Логистики]]
- [[docs/Modules_BotBridge|Модуль Bot Bridge]]
- [[CLAUDE.md|Архитектурный справочник]]