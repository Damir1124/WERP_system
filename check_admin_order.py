#!/usr/bin/env python
import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.logistics.models import Order, OrderItem
from apps.products.models import Product
from apps.bot_bridge.serializers import OrderSerializer

# Найдём заказ, созданный через админку (можно любой с статусом PD)
order = Order.objects.filter(status='PD').first()
if not order:
    print('Нет заказов со статусом PD')
    sys.exit(0)

print(f'Заказ {order.id}:')
print(f'  Статус: {order.status}')
print(f'  Создан: {order.created_at}')
print(f'  Клиент: {order.client.name if order.client else None}')

# Сериализуем
serializer = OrderSerializer(order)
data = serializer.data
print('\nДанные от OrderSerializer:')
print(json.dumps(data, indent=2, ensure_ascii=False))

# Проверим каждую позицию
items = order.items.all()
print(f'\nПозиций: {items.count()}')
for item in items:
    print(f'  Позиция {item.id}:')
    print(f'    Продукт: {item.product.name} (тип: {item.product.type_product})')
    print(f'    Quantity: {item.quantity}')
    print(f'    Exchange_qty: {item.exchange_qty}')
    print(f'    Sell_with_qty: {item.sell_with_qty}')
    print(f'    Defective_qty: {item.defective_qty}')
    # Проверим, является ли продукт WATER
    if item.product.type_product == '19W':
        print('    -> Это WATER, должен отображаться container_op')
    else:
        print('    -> Не WATER, container_op не нужен')

# Также проверим, какой API возвращает для этого заказа через CourierCurrentTripView
# (эмулируем запрос)
from apps.bot_bridge.views import CourierCurrentTripView
from rest_framework.test import APIRequestFactory
from apps.workers.models import Worker

courier = Worker.objects.filter(worker_type='COURIER').first()
if courier:
    factory = APIRequestFactory()
    request = factory.get('/api/bot/courier/trip/current/')
    request.courier = courier
    view = CourierCurrentTripView.as_view()
    response = view(request)
    print('\n--- Ответ от CourierCurrentTripView ---')
    print('Статус:', response.status_code)
    if response.status_code == 200:
        # Найдём наш заказ в ответе
        trip_data = response.data
        if trip_data.get('active_trip'):
            orders = trip_data.get('trip', {}).get('orders', [])
            for o in orders:
                if o['id'] == order.id:
                    print('Заказ найден в ответе:')
                    print(json.dumps(o, indent=2, ensure_ascii=False))
                    break
        else:
            print('Нет активного рейса')
    else:
        print('Ошибка:', response.data)
else:
    print('Нет курьера для теста')