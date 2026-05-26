#!/usr/bin/env python
import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.logistics.models import Order, OrderItem
from apps.bot_bridge.serializers import OrderSerializer

# Берём первый заказ
order = Order.objects.first()
if order:
    serializer = OrderSerializer(order)
    print(json.dumps(serializer.data, indent=2, ensure_ascii=False))
else:
    print('Нет заказов')

# Проверим OrderItemSerializer
from apps.bot_bridge.serializers import OrderItemSerializer
items = OrderItem.objects.all()
for item in items:
    print(f'\nItem {item.id}:')
    serializer = OrderItemSerializer(item)
    print(json.dumps(serializer.data, indent=2, ensure_ascii=False))