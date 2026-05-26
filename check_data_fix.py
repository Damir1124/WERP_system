#!/usr/bin/env python
"""
Проверка данных после исправлений для container_op логики.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.logistics.models import Order, OrderItem
from apps.products.models import Product

print('=== Проверка данных после исправлений ===\n')

print('1. Проверка OrderItem с WATER продуктами (тип 19W):')
water_items = OrderItem.objects.filter(product__type_product='19W')
print(f'   Всего WATER позиций: {water_items.count()}')
for item in water_items[:10]:
    print(f'   ID {item.id}: product="{item.product.name}", quantity={item.quantity}, '
          f'exchange_qty={item.exchange_qty}, sell_with_qty={item.sell_with_qty}, '
          f'defective_qty={item.defective_qty}')

print('\n2. Проверка OrderItem с другими продуктами:')
other_items = OrderItem.objects.exclude(product__type_product='19W')
print(f'   Всего других позиций: {other_items.count()}')
for item in other_items[:5]:
    print(f'   ID {item.id}: product="{item.product.name}" ({item.product.type_product}), '
          f'quantity={item.quantity}, exchange_qty={item.exchange_qty}')

print('\n3. Проверка заказа 53 (создан через админку):')
try:
    order = Order.objects.get(id=53)
    print(f'   Заказ {order.id}: статус={order.status}, позиций={order.orderitem_set.count()}')
    for item in order.orderitem_set.all():
        print(f'     - {item.product.name} ({item.product.type_product}): '
              f'qty={item.quantity}, exchange={item.exchange_qty}, '
              f'sell_with={item.sell_with_qty}, defective={item.defective_qty}')
except Order.DoesNotExist:
    print('   Заказ 53 не найден')

print('\n4. Проверка проблемы exchange_qty = 0:')
zero_exchange = water_items.filter(exchange_qty=0)
print(f'   WATER позиций с exchange_qty=0: {zero_exchange.count()}')
if zero_exchange.exists():
    print('   Список проблемных позиций:')
    for item in zero_exchange[:5]:
        print(f'     ID {item.id}: product="{item.product.name}", quantity={item.quantity}')

print('\n5. Проверка метода save() в OrderItem:')
water = Product.objects.filter(type_product='19W').first()
if water:
    print(f'   Тестовый продукт WATER: {water.name} (ID {water.id})')
    # Проверяем логику метода save
    from apps.logistics.models import OrderItem
    import inspect
    source = inspect.getsource(OrderItem.save)
    if 'exchange_qty = self.quantity' in source:
        print('   ✓ Метод save() содержит логику установки exchange_qty = quantity для WATER')
    else:
        print('   ✗ Метод save() не содержит нужную логику')
else:
    print('   Нет WATER продуктов в базе')

print('\n=== Проверка завершена ===')