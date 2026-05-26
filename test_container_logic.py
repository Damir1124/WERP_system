#!/usr/bin/env python
"""
Тестирование логики контейнерных операций с новыми типами продуктов.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.products.models import Product
from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.workers.models import Worker
from apps.clients.models import Client
from django.utils import timezone

def setup_test_data():
    """Создание тестовых данных."""
    print("=== Настройка тестовых данных ===")
    
    # Создаем курьера
    courier, _ = Worker.objects.get_or_create(
        full_name="Тестовый Курьер",
        defaults={'phone': '+79990000000', 'worker_type': 'CR'}
    )
    print(f"Курьер: {courier.full_name}")
    
    # Создаем смену
    shift, _ = CourierShift.objects.get_or_create(
        courier=courier,
        date=timezone.now().date(),
        defaults={'opened_at': timezone.now()}
    )
    print(f"Смена: {shift.id}")
    
    # Создаем рейс
    trip, _ = CourierTrip.objects.get_or_create(
        shift=shift,
        defaults={'full_loaded': 10}
    )
    print(f"Рейс: {trip.id}")
    
    # Создаем клиента
    client, _ = Client.objects.get_or_create(
        phone='+79991112233',
        defaults={'name': 'Тестовый Клиент', 'address': 'ул. Тестовая'}
    )
    print(f"Клиент: {client.name}")
    
    # Получаем продукты
    water = Product.objects.filter(type_product=Product.TypeProduct.WATER).first()
    bottle20l = Product.objects.filter(type_product=Product.TypeProduct.BOTTLE_20L).first()
    bottle = Product.objects.filter(type_product=Product.TypeProduct.BOTTLE).first()
    
    if not water:
        water = Product.objects.create(
            name='Вода 19л',
            type_product=Product.TypeProduct.WATER,
            price=100,
            track_inventory=True
        )
        print(f"Создан продукт WATER: {water.name}")
    else:
        print(f"Продукт WATER: {water.name}")
    
    if not bottle20l:
        bottle20l = Product.objects.create(
            name='Вода с тарой 19л',
            type_product=Product.TypeProduct.BOTTLE_20L,
            price=300,
            track_inventory=True
        )
        print(f"Создан продукт BOTTLE_20L: {bottle20l.name}")
    else:
        print(f"Продукт BOTTLE_20L: {bottle20l.name}")
    
    if not bottle:
        bottle = Product.objects.create(
            name='Тара 19л',
            type_product=Product.TypeProduct.BOTTLE,
            price=200,
            track_inventory=True
        )
        print(f"Создан продукт BOTTLE: {bottle.name}")
    else:
        print(f"Продукт BOTTLE: {bottle.name}")
    
    return courier, shift, trip, client, water, bottle20l, bottle

def test_order_creation():
    """Тест создания заказа с контейнерными операциями."""
    print("\n=== Тест создания заказа ===")
    courier, shift, trip, client, water, bottle20l, bottle = setup_test_data()
    
    # Создаем заказ
    order = Order.objects.create(
        trip=trip,
        client=client,
        status=Order.Status.PENDING,
        payment_type=Order.PaymentType.CASH,
        note='Тестовый заказ'
    )
    print(f"Создан заказ #{order.id}")
    
    # Создаем позицию заказа с водой
    item = OrderItem.objects.create(
        order=order,
        product=water,
        quantity=2,
        price=water.price,
        exchange_qty=1,
        sell_with_qty=1,
        defective_qty=0
    )
    print(f"Создана позиция заказа: продукт={item.product.name}, quantity={item.quantity}, exchange_qty={item.exchange_qty}, sell_with_qty={item.sell_with_qty}")
    
    # Проверяем, что позиция создана
    assert item.id is not None
    print("✓ Позиция заказа создана успешно")
    
    # Симулируем подтверждение заказа (статус DELIVERED)
    order.status = Order.Status.DELIVERED
    order.delivered_at = timezone.now()
    order.save()
    
    print("Заказ переведен в статус DELIVERED")
    
    # Проверяем, что сигналы сработали (складские движения)
    from apps.warehouse.models import StockMovement
    movements = StockMovement.objects.filter(note__contains=f'Заказ #{order.id}')
    print(f"Количество складских движений: {movements.count()}")
    for mov in movements:
        print(f"  Движение: {mov.operation_type} продукт {mov.sold_product.name} количество {mov.quantity}")
    
    # Ожидаем, что есть движения для воды и тары
    # (это зависит от реализации сигналов)
    print("\n=== Тест завершен ===")
    
    # Очистка (опционально)
    # order.delete()
    # item.delete()

if __name__ == '__main__':
    test_order_creation()