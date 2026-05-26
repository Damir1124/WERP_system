#!/usr/bin/env python
"""
Скрипт для обновления exchange_qty в существующих заказах.
Устанавливает exchange_qty = quantity для всех позиций с продуктом WATER.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.logistics.models import OrderItem
from apps.products.models import Product
from django.db.models import F

# Получаем продукт WATER
water_products = Product.objects.filter(type_product=Product.TypeProduct.WATER)
if not water_products.exists():
    print("Продукт WATER не найден")
    sys.exit(1)

water_product = water_products.first()
print(f"Продукт WATER: {water_product.name} (ID: {water_product.id})")

# Находим все позиции с этим продуктом и exchange_qty = 0
items = OrderItem.objects.filter(product=water_product, exchange_qty=0)
print(f"Найдено позиций для обновления: {items.count()}")

# Обновляем
updated = 0
for item in items:
    if item.exchange_qty == 0:
        item.exchange_qty = item.quantity
        item.save(update_fields=['exchange_qty'])
        updated += 1
        print(f"  Обновлена позиция {item.id}: quantity={item.quantity}, exchange_qty={item.exchange_qty}")

print(f"Обновлено {updated} позиций")

# Также проверим, есть ли позиции с sell_with_qty > exchange_qty (нарушение нового правила)
invalid_items = OrderItem.objects.filter(product=water_product, sell_with_qty__gt=F('exchange_qty'))
if invalid_items.exists():
    print(f"\nВНИМАНИЕ: Найдено {invalid_items.count()} позиций с sell_with_qty > exchange_qty:")
    for item in invalid_items:
        print(f"  Позиция {item.id}: quantity={item.quantity}, exchange_qty={item.exchange_qty}, sell_with_qty={item.sell_with_qty}")
    print("Рекомендуется исправить вручную.")
else:
    print("\nВсе позиции соответствуют правилу sell_with_qty <= exchange_qty")