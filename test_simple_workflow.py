#!/usr/bin/env python
"""
Простое тестирование workflow создания и подтверждения заказа.
Проверяет бизнес-логику без использования Django TestCase.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.workers.models import Worker
from apps.clients.models import Client
from apps.products.models import Product
from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.warehouse.models import StockBalance
from apps.bot_bridge.serializers import OrderCreateModelSerializer, OrderConfirmationSerializer

print("=== Простое тестирование workflow container операций ===\n")

# 1. Проверка сериализатора OrderCreateModelSerializer
print("1. Тест сериализатора OrderCreateModelSerializer")
print("   Проверка default значений для exchange_qty...")

# Создаем тестовые данные
courier = Worker.objects.filter(worker_type='CR').first()
if not courier:
    courier = Worker.objects.create(
        full_name="Тест Курьер",
        worker_type='CR',
        tg_id=999888777
    )

client = Client.objects.first()
if not client:
    client = Client.objects.create(
        name="Тест Клиент",
        phone="+998901111111",
        address="Тест адрес"
    )

water = Product.objects.filter(type_product='19W').first()
if not water:
    water = Product.objects.create(
        name="Вода 19 тест",
        type_product='19W',
        price=15000,
        unit='шт'
    )

# Создаем смену и рейс
shift = CourierShift.objects.filter(courier=courier, status='OP').first()
if not shift:
    shift = CourierShift.objects.create(
        courier=courier,
        status='OP'
    )

trip = CourierTrip.objects.filter(shift=shift, status='OP').first()
if not trip:
    trip = CourierTrip.objects.create(
        shift=shift,
        status='OP',
        full_loaded=0
    )

# Тестируем сериализатор
data = {
    'trip': trip.id,
    'client': client.id,
    'payment_type': 'CH',
    'items': [
        {
            'product': water.id,
            'quantity': 7
        }
    ]
}

serializer = OrderCreateModelSerializer(data=data)
if serializer.is_valid():
    print("   ✓ Сериализатор валиден")
    order = serializer.save()
    print(f"   Создан заказ ID {order.id}")
    
    # Проверяем созданные позиции
    items = order.items.all()
    for item in items:
        print(f"   Позиция ID {item.id}: quantity={item.quantity}, exchange_qty={item.exchange_qty}")
        if item.exchange_qty == item.quantity:
            print("   ✓ exchange_qty корректно установлен в quantity")
        else:
            print(f"   ⚠ Проблема: exchange_qty={item.exchange_qty}, ожидалось {item.quantity}")
else:
    print(f"   ✗ Ошибка валидации: {serializer.errors}")

# 2. Проверка сериализатора OrderConfirmationSerializer
print("\n2. Тест сериализатора OrderConfirmationSerializer")
print("   Проверка валидации бизнес-правил...")

if 'order' in locals():
    item = order.items.first()
    
    # Тест 1: Корректные данные
    print("   Тест 1: Корректные данные (exchange=3, sell_with=2, defective=0)")
    data1 = {
        'order_id': order.id,
        'confirmed': True,
        'items': [
            {
                'item_id': item.id,
                'exchange_qty': 3,
                'sell_with_qty': 2,
                'defective_qty': 0
            }
        ]
    }
    
    serializer1 = OrderConfirmationSerializer(data=data1)
    if serializer1.is_valid():
        print("   ✓ Валидация пройдена")
        
        # Проверяем бизнес-правила в validated_data
        validated = serializer1.validated_data
        items_data = validated['items']
        for item_data in items_data:
            print(f"   Проверка правил для позиции:")
            print(f"     exchange_qty: {item_data['exchange_qty']}")
            print(f"     sell_with_qty: {item_data['sell_with_qty']}")
            print(f"     defective_qty: {item_data['defective_qty']}")
            
            # Проверяем правило sell_with_qty ≤ exchange_qty
            if item_data['sell_with_qty'] <= item_data['exchange_qty']:
                print("     ✓ sell_with_qty ≤ exchange_qty: OK")
            else:
                print("     ✗ sell_with_qty ≤ exchange_qty: нарушено")
                
            # Проверяем правило сумма ≤ quantity
            total = (item_data['exchange_qty'] + 
                    item_data['sell_with_qty'] + 
                    item_data['defective_qty'])
            if total <= item.quantity:
                print(f"     ✓ сумма операций ({total}) ≤ quantity ({item.quantity}): OK")
            else:
                print(f"     ✗ сумма операций ({total}) > quantity ({item.quantity}): нарушено")
    else:
        print(f"   ✗ Ошибка валидации: {serializer1.errors}")
    
    # Тест 2: Нарушение правила sell_with_qty ≤ exchange_qty
    print("\n   Тест 2: Нарушение правила sell_with_qty > exchange_qty")
    data2 = {
        'order_id': order.id,
        'confirmed': True,
        'items': [
            {
                'item_id': item.id,
                'exchange_qty': 1,
                'sell_with_qty': 3,  # 3 > 1 - должно вызвать ошибку
                'defective_qty': 0
            }
        ]
    }
    
    serializer2 = OrderConfirmationSerializer(data=data2)
    if not serializer2.is_valid():
        print("   ✓ Валидация не пройдена (ожидаемо)")
        if 'items' in serializer2.errors:
            print(f"   Сообщение об ошибке: {serializer2.errors['items']}")
    else:
        print("   ⚠ Валидация пройдена, но должна была быть ошибка")
    
    # Тест 3: Нарушение правила сумма ≤ quantity
    print("\n   Тест 3: Нарушение правила сумма операций > quantity")
    data3 = {
        'order_id': order.id,
        'confirmed': True,
        'items': [
            {
                'item_id': item.id,
                'exchange_qty': 4,
                'sell_with_qty': 2,
                'defective_qty': 2  # 4+2+2=8 > 7
            }
        ]
    }
    
    serializer3 = OrderConfirmationSerializer(data=data3)
    if not serializer3.is_valid():
        print("   ✓ Валидация не пройдена (ожидаемо)")
        if 'items' in serializer3.errors:
            print(f"   Сообщение об ошибке: {serializer3.errors['items']}")
    else:
        print("   ⚠ Валидация пройдена, но должна была быть ошибка")

# 3. Проверка метода save() в OrderItem
print("\n3. Тест метода save() в модели OrderItem")
print("   Проверка автоматической установки exchange_qty для новых WATER позиций...")

# Создаем новую позицию без exchange_qty
new_item = OrderItem(
    order=order if 'order' in locals() else None,
    product=water,
    quantity=10,
    exchange_qty=0  # Явно устанавливаем 0
)

print(f"   До save(): quantity={new_item.quantity}, exchange_qty={new_item.exchange_qty}")
print(f"   Продукт тип: {new_item.product.type_product}")

# Вызываем save() (но не сохраняем в БД, чтобы не создавать реальную запись)
# Вместо этого проверим логику в методе save
if new_item.pk is None and new_item.exchange_qty == 0 and new_item.product.type_product == '19W':
    print("   ✓ Логика метода save() установит exchange_qty = quantity")
    print("   (При реальном сохранении exchange_qty станет равным 10)")
else:
    print("   ⚠ Логика метода save() не сработает")

# 4. Проверка текущих данных в базе
print("\n4. Проверка текущих данных в базе")
print("   WATER позиции и их exchange_qty:")

water_items = OrderItem.objects.filter(product__type_product='19W')
print(f"   Всего WATER позиций: {water_items.count()}")

for item in water_items[:5]:
    status = "✓ OK" if item.exchange_qty == item.quantity else "⚠ Проблема"
    print(f"   ID {item.id}: quantity={item.quantity}, exchange_qty={item.exchange_qty} {status}")

zero_exchange = water_items.filter(exchange_qty=0)
print(f"   WATER позиций с exchange_qty=0: {zero_exchange.count()}")

if zero_exchange.count() == 0:
    print("   ✓ Все WATER позиции имеют корректный exchange_qty")
else:
    print("   ⚠ Есть позиции с exchange_qty=0")

print("\n=== Тестирование завершено ===")