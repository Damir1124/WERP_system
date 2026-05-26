#!/usr/bin/env python
"""
Исправление WATER позиций с exchange_qty=0.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.logistics.models import OrderItem
from apps.products.models import Product

print('=== Исправление WATER позиций с exchange_qty=0 ===\n')

# Находим все WATER продукты
water_products = Product.objects.filter(type_product='19W')
print(f'Найдено WATER продуктов: {water_products.count()}')

if not water_products.exists():
    print('Нет WATER продуктов в базе. Выход.')
    sys.exit(1)

# Находим все позиции с этими продуктами и exchange_qty=0
items_to_fix = OrderItem.objects.filter(
    product__in=water_products,
    exchange_qty=0
)

print(f'Найдено позиций для исправления: {items_to_fix.count()}')

if items_to_fix.exists():
    print('Исправляем позиции:')
    updated_count = 0
    for item in items_to_fix:
        old_exchange = item.exchange_qty
        item.exchange_qty = item.quantity
        item.save(update_fields=['exchange_qty'])
        print(f'  ID {item.id}: product="{item.product.name}", quantity={item.quantity}, '
              f'exchange_qty: {old_exchange} -> {item.exchange_qty}')
        updated_count += 1
    
    print(f'\nИсправлено позиций: {updated_count}')
else:
    print('Нет позиций для исправления.')

# Проверяем результат
print('\n=== Проверка после исправления ===')
water_items = OrderItem.objects.filter(product__type_product='19W')
zero_exchange = water_items.filter(exchange_qty=0)
print(f'Всего WATER позиций: {water_items.count()}')
print(f'WATER позиций с exchange_qty=0: {zero_exchange.count()}')

if zero_exchange.exists():
    print('Остались проблемные позиции:')
    for item in zero_exchange[:5]:
        print(f'  ID {item.id}: product="{item.product.name}", quantity={item.quantity}')
else:
    print('✓ Все WATER позиции имеют корректный exchange_qty')

print('\n=== Готово ===')