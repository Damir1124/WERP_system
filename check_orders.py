#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.logistics.models import Order, OrderItem
from apps.products.models import Product

print('Всего заказов:', Order.objects.count())
print('Всего позиций:', OrderItem.objects.count())

water = Product.objects.filter(type_product='19W').first()
if water:
    items = OrderItem.objects.filter(product=water)
    print('Позиций WATER:', items.count())
    for item in items:
        print(f'  ID {item.id}: order {item.order.id}, quantity={item.quantity}, exchange={item.exchange_qty}, sell_with={item.sell_with_qty}, defective={item.defective_qty}')
else:
    print('WATER продукт не найден')

# Также проверим заказы
orders = Order.objects.all()[:5]
print('\nПоследние заказы:')
for order in orders:
    print(f'  Order {order.id}: status={order.status}, trip={order.trip.id if order.trip else None}')