# Ошибка подсчета card_profit в update_finance_record

**Дата обнаружения:** 2026-04-27 (предположительно)  
**Модуль:** `accounting`  
**Критичность:** Средняя (искажает финансовую отчётность)  
**Статус:** Не исправлен (требуется изменение кода)

## Описание
В функции `update_finance_record` (файл `apps/accounting/utils.py`) неправильно рассчитывается поле `card_profit` модели `Finance`.

### Текущая реализация (строка ~33):
```python
card_profit = sum(t.card_amount for t in transactions)
```

**Проблема:** Суммируются `card_amount` всех транзакций, включая транзакции типа `MINUS` (расходы). В результате `card_profit` отражает не прибыль по карте, а общий оборот по карте (доходы + расходы).

### Ожидаемое поведение
`card_profit` должен считать только доходы по карте, т.е. сумму `card_amount` для транзакций с `type=PLUS`.

## Влияние на систему
1. **Финансовая отчётность:** В дневной сводке (`Finance`) поле `card_profit` завышено на сумму карточных расходов.
2. **Аналитика:** Диспетчер видит некорректную прибыль по безналу, что может привести к ошибочным бизнес-решениям.
3. **Автоматизация:** Ошибка тиражируется при каждом обновлении `Finance` (после каждой транзакции).

## Воспроизведение
1. Создать транзакцию `FinancialTransactions` с `type=PLUS`, `card_amount=10000` (доход по карте).
2. Создать транзакцию `FinancialTransactions` с `type=MINUS`, `card_amount=5000` (расход по карте).
3. Вызвать `update_finance_record(date)`.
4. Проверить запись `Finance` за эту дату: `card_profit` будет `15000` (ожидается `10000`).

## Причина
Логическая ошибка в агрегации: разработчик не учёл, что `card_amount` есть и у доходов, и у расходов. В бизнес-логике `card_profit` — это чистая прибыль по безналу (доходы минус расходы), но текущая реализация складывает абсолютные значения.

## Решение
Изменить строку в `apps/accounting/utils.py`:

```python
# Было:
card_profit = sum(t.card_amount for t in transactions)

# Стало:
card_profit = sum(t.card_amount for t in transactions if t.type == FinancialTransactions.TypeTransaction.PLUS)
```

Или, если `card_profit` должен быть чистой прибылью (доходы минус расходы):
```python
card_profit = sum(
    t.card_amount if t.type == FinancialTransactions.TypeTransaction.PLUS else -t.card_amount
    for t in transactions
)
```

**Рекомендация:** Уточнить у бизнес-аналитика, как именно должен считаться `card_profit`. Судя по названию поля (`profit` — прибыль), вероятно, нужен второй вариант.

## Зависимости
- **Файл:** `apps/accounting/utils.py`
- **Модель:** `FinancialTransactions.TypeTransaction`
- **Сигналы:** `accounting/signals.py` вызывает `update_finance_record` после каждой транзакции.

## Побочные эффекты
После исправления все существующие записи `Finance` останутся с некорректными значениями. Может потребоваться скрипт пересчёта исторических данных.

## Ссылки
- [[docs/Index|Главный индекс]]
- [[CLAUDE.md#p1-исправить-баг-в-update_finance_record-card_profit|Roadmap: исправить баг]]
- [[docs/Modules/Accounting|Модуль Финансов (Accounting)]]