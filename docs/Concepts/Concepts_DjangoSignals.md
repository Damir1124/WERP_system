# Концепция: Django Signals

**Назначение:** Асинхронная связь между модулями.

## Основные сигналы
- `pre_save` - перед сохранением
- `post_save` - после сохранения
- `pre_delete` - перед удалением
- `post_delete` - после удаления

## Использование в Osnova 2.0

### 1. Логистика → Склад
```python
@receiver(post_save, sender=DeliveryJournal)
def update_stock_on_delivery(sender, instance, created, **kwargs):
    if created:
        # Списать товары со склада
        StockBalance.objects.filter(
            product__in=instance.products.all()
        ).update(quantity=F('quantity') - instance.quantity)
```

### 2. Склад → Финансы
```python
@receiver(post_save, sender=StockMovement)
def create_financial_transaction(sender, instance, created, **kwargs):
    if created and instance.operation_type == 'SELL':
        FinancialTransactions.objects.create(
            amount=instance.quantity * instance.sold_product.price,
            transaction_type='INCOME',
            source='WAREHOUSE'
        )
```

### 3. Финансы → Отчетность
```python
@receiver(post_save, sender=FinancialTransactions)
def update_finance_daily(sender, instance, created, **kwargs):
    if created:
        finance, _ = Finance.objects.get_or_create(date=instance.created_at.date())
        finance.total_income += instance.amount
        finance.save()
```

## Лучшие практики
1. **Избегайте рекурсии** - используйте `update_fields` или флаги
2. **Используйте `transaction.on_commit()`** для отложенного выполнения
3. **Логируйте ошибки** в сигналах
4. **Тестируйте изоляцию** сигналов

## Проблемы
- Сложность отладки
- Риск бесконечных циклов
- Зависимость от порядка выполнения

[[Index]] | [[Bugs_RecursiveSignals]] | [[Concepts_WebSockets]]