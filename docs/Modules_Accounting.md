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
- `product`: товар (может быть `null`)
- `quantity`: количество товара

#### `Installment` — рассрочки клиентов
- `client`, `product`: ссылки
- `amount`: общая сумма рассрочки
- `paid_amount`: уже оплаченная сумма
- `due_date`: дата следующего платежа
- `status`: `ACTIVE`, `OVERDUE`, `CLOSED`
- Методы `make_payment()`, `check_status()`

#### `PaymentsInstallment` — платежи по рассрочке
(не показан в текущем фрагменте, но существует согласно CLAUDE.md)

#### `Salary` — баланс зарплаты сотрудника
- `worker`: ссылка на `Worker`
- `balance`: текущий баланс (может быть отрицательным при штрафах)
- `last_payment`: дата последней выплаты

#### `SalaryPayment` — выплаты зарплаты
- `salary`: ссылка на `Salary`
- `amount`: сумма выплаты
- `payment_type`: `SALARY`, `FINE`, `BONUS`
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
Обнуляет баланс зарплаты, если с последней выплаты (`last_payment`) прошло >30 дней. Предотвращает накопление долгов при увольнении.

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