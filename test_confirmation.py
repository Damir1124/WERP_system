#!/usr/bin/env python
import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.bot_bridge.views import OrderConfirmationView
from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.workers.models import Worker
from apps.products.models import Product
from apps.clients.models import Client

# Используем существующие данные
worker = Worker.objects.filter(worker_type='COURIER').first()
if not worker:
    print('Нет курьера, пропускаем тест')
    sys.exit(0)

client = Client.objects.first()
if not client:
    print('Нет клиента, пропускаем тест')
    sys.exit(0)

water_product = Product.objects.filter(type_product='19W').first()
if not water_product:
    print('Нет продукта WATER')
    sys.exit(1)

# Используем существующую смену и рейс
shift = CourierShift.objects.filter(courier=worker, status='OPEN').first()
if not shift:
    print('Нет открытой смены, пропускаем тест')
    sys.exit(0)

trip = CourierTrip.objects.filter(shift=shift, status='ACTIVE').first()
if not trip:
    print('Нет активного рейса, пропускаем тест')
    sys.exit(0)

# Используем существующий заказ с статусом PD
order = Order.objects.filter(trip=trip, status='PD').first()
if not order:
    # Создаём заказ
    order = Order.objects.create(
        trip=trip,
        client=client,
        payment_type='CASH',
        status='PD'
    )
    print(f'Создан заказ {order.id}')
else:
    print(f'Используем существующий заказ {order.id}')

# Используем или создаём позицию заказа
order_item = OrderItem.objects.filter(order=order, product=water_product).first()
if not order_item:
    order_item = OrderItem.objects.create(
        order=order,
        product=water_product,
        quantity=5,
        price=75000,
        exchange_qty=5,
        sell_with_qty=0,
        defective_qty=0
    )
    print(f'Создана позиция {order_item.id}')
else:
    print(f'Используем существующую позицию {order_item.id}')

# Тестируем подтверждение с изменением контейнерных операций
factory = APIRequestFactory()
view = OrderConfirmationView.as_view()

# Имитируем запрос от курьера
request = factory.post('/api/bot/courier/orders/confirm/', {
    'order_id': order.id,
    'confirmed': True,
    'items': [
        {
            'item_id': order_item.id,
            'exchange_qty': 3,
            'sell_with_qty': 2,
            'defective_qty': 0
        }
    ],
    'note': 'Тестовое подтверждение'
}, format='json')

# Устанавливаем аутентификацию
request.courier = worker

# Вызываем view
response = view(request)
print('Статус ответа:', response.status_code)
print('Тело ответа:', json.dumps(response.data, indent=2, ensure_ascii=False))

# Проверяем, что заказ обновился
order.refresh_from_db()
print(f'Статус заказа после подтверждения: {order.status}')
print(f'Дата доставки: {order.delivered_at}')

# Проверяем, что позиция обновилась
order_item.refresh_from_db()
print(f'Позиция: exchange_qty={order_item.exchange_qty}, sell_with_qty={order_item.sell_with_qty}, defective_qty={order_item.defective_qty}')

# Проверяем, создалась ли позиция BOTTLE
bottle_items = OrderItem.objects.filter(order=order, product__type_product='BT')
print(f'Создано позиций BOTTLE: {bottle_items.count()}')
for item in bottle_items:
    print(f'  BOTTLE позиция: id={item.id}, quantity={item.quantity}, price={item.price}')

# Проверяем сигналы склада
from apps.warehouse.models import StockBalance, StockMovement
water_balance = StockBalance.objects.filter(product=water_product).first()
if water_balance:
    print(f'Остаток WATER после списания: {water_balance.quantity}')
bottle_balance = StockBalance.objects.filter(product__type_product='BT').first()
if bottle_balance:
    print(f'Остаток BOTTLE после списания: {bottle_balance.quantity}')

print('\nТест завершён.')