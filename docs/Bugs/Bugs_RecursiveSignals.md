# Баг: Бесконечный цикл в сигналах post_save

**Статус:** Не исправлен  
**Приоритет:** Высокий  
**Модули:** Accounting, Logistics, Warehouse

## Описание
При сохранении `DeliveryJournal` возникает цепочка сигналов, которая приводит к рекурсивному вызову `post_save`.

## Воспроизведение
1. Создать `DeliveryJournal` с товарами
2. Сигнал в `logistics/signals.py` обновляет `total_price`
3. Сигнал в `warehouse/signals.py` списывает товары со склада
4. Сигнал в `accounting/signals.py` создает финансовую транзакцию
5. Финансовая транзакция вызывает обновление `Finance`
6. Обновление `Finance` снова триггерит сигналы...

## Симптомы
- Бесконечное выполнение SQL запросов
- Блокировка базы данных
- Остановка сервера при высокой нагрузке

## Временное решение
Использовать `transaction.on_commit()` для отложенного выполнения:
```python
@receiver(post_save, sender=DeliveryJournal)
def update_finance_on_delivery(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: create_financial_transaction(instance))
```

## Постоянное решение
- Добавить флаг `skip_signals` в модели
- Использовать `update_fields` для предотвращения рекурсии
- Рефакторинг сигналов в единую очередь

[[Index]] | [[Bugs_CardProfitCalc]]