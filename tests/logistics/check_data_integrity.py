#!/usr/bin/env python
"""
Проверка целостности данных системы смен и рейсов
"""

import os
import django
import sys

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
django.setup()

from apps.workers.models import Worker
from apps.logistics.models import CourierShift, CourierTrip, Order
from apps.products.models import Product
from apps.clients.models import Client

def check_data_integrity():
    print("=" * 60)
    print("ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ СИСТЕМЫ СМЕН И РЕЙСОВ")
    print("=" * 60)
    
    # 1. Проверка базовых моделей
    print("\n1. БАЗОВЫЕ МОДЕЛИ:")
    
    workers = Worker.objects.all()
    print(f"   Курьеров: {workers.count()}")
    if workers.count() > 0:
        for w in workers[:3]:  # Показываем первые 3
            print(f"     - {w.full_name} ({w.worker_type})")
    
    clients = Client.objects.all()
    print(f"   Клиентов: {clients.count()}")
    if clients.count() > 0:
        for c in clients[:3]:
            print(f"     - {c.name} ({c.phone})")
    
    products = Product.objects.all()
    print(f"   Продуктов: {products.count()}")
    if products.count() > 0:
        for p in products:
            print(f"     - {p.name} ({p.type_product}, {p.price} руб.)")
    
    # 2. Проверка новых моделей (система смен)
    print("\n2. СИСТЕМА СМЕН И РЕЙСОВ:")
    
    shifts = CourierShift.objects.all()
    print(f"   Смен: {shifts.count()}")
    for shift in shifts:
        print(f"\n   Смена #{shift.id}:")
        print(f"     Курьер: {shift.courier}")
        print(f"     Дата: {shift.date}")
        print(f"     Статус: {shift.get_status_display()}")
        print(f"     Наличные: {shift.cash_total}, Безнал: {shift.card_total}")
        
        # Проверяем рейсы в смене
        trips = shift.trips.all()
        print(f"     Рейсов в смене: {trips.count()}")
        
        for trip in trips:
            print(f"\n     Рейс #{trip.id}:")
            print(f"       Загружено: {trip.full_loaded}")
            print(f"       Возвращено: {trip.full_returned}")
            print(f"       Статус: {trip.get_status_display()}")
            
            # Проверяем заказы в рейсе
            orders = trip.orders.all()
            print(f"       Заказов в рейсе: {orders.count()}")
            
            for order in orders:
                print(f"\n       Заказ #{order.id}:")
                print(f"         Клиент: {order.client}")
                print(f"         Продукт: {order.product}")
                print(f"         Количество: {order.quantity}")
                print(f"         Цена: {order.price}")
                print(f"         Статус: {order.get_status_display()}")
                print(f"         Операция с тарой: {order.get_container_op_display() or 'Не указана'}")
                print(f"         Тип оплаты: {order.get_payment_type_display()}")
    
    # 3. Проверка связей и целостности
    print("\n3. ПРОВЕРКА СВЯЗЕЙ И ЦЕЛОСТНОСТИ:")
    
    # Проверяем, что у всех смен есть курьер
    shifts_without_courier = CourierShift.objects.filter(courier__isnull=True)
    print(f"   Смен без курьера: {shifts_without_courier.count()} ✅" if shifts_without_courier.count() == 0 else f"   Смен без курьера: {shifts_without_courier.count()} ❌")
    
    # Проверяем, что у всех рейсов есть смена
    trips_without_shift = CourierTrip.objects.filter(shift__isnull=True)
    print(f"   Рейсов без смены: {trips_without_shift.count()} ✅" if trips_without_shift.count() == 0 else f"   Рейсов без смены: {trips_without_shift.count()} ❌")
    
    # Проверяем, что у всех заказов есть рейс
    orders_without_trip = Order.objects.filter(trip__isnull=True)
    print(f"   Заказов без рейса: {orders_without_trip.count()} ✅" if orders_without_trip.count() == 0 else f"   Заказов без рейса: {orders_without_trip.count()} ❌")
    
    # Проверяем, что у всех заказов есть продукт
    orders_without_product = Order.objects.filter(product__isnull=True)
    print(f"   Заказов без продукта: {orders_without_product.count()} ✅" if orders_without_product.count() == 0 else f"   Заказов без продукта: {orders_without_product.count()} ❌")
    
    # 4. Проверка бизнес-логики
    print("\n4. ПРОВЕРКА БИЗНЕС-ЛОГИКИ:")
    
    # Проверяем расчет цен
    orders_with_wrong_price = []
    for order in Order.objects.all():
        if order.price is not None and order.product is not None:
            expected_price = order.product.price * order.quantity
            if order.price != expected_price:
                orders_with_wrong_price.append((order.id, order.price, expected_price))
    
    print(f"   Заказов с некорректной ценой: {len(orders_with_wrong_price)} ✅" if len(orders_with_wrong_price) == 0 else f"   Заказов с некорректной ценой: {len(orders_with_wrong_price)} ❌")
    if orders_with_wrong_price:
        for order_id, actual, expected in orders_with_wrong_price[:3]:
            print(f"     Заказ #{order_id}: цена {actual}, ожидается {expected}")
    
    # Проверяем сводки по рейсам
    print("\n   Сводки по рейсам:")
    for trip in CourierTrip.objects.all()[:5]:  # Проверяем первые 5 рейсов
        summary = trip.get_trip_summary()
        print(f"\n     Рейс #{trip.id}:")
        print(f"       Загружено: {summary['full_loaded']}")
        print(f"       Доставлено: {summary['delivered']}")
        print(f"       Осталось: {summary['full_remain']}")
        print(f"       Пустых получено: {summary['empty_received']}")
        
        # Проверяем логику остатков
        expected_remain = trip.full_loaded - summary['delivered'] - trip.full_returned
        if summary['full_remain'] == expected_remain:
            print(f"       ✅ Остаток рассчитан правильно")
        else:
            print(f"       ❌ Остаток неверный: {summary['full_remain']}, ожидается {expected_remain}")
    
    # 5. Рекомендации
    print("\n5. РЕКОМЕНДАЦИИ:")
    
    if shifts.count() == 0:
        print("   ❌ Нет тестовых смен. Создайте хотя бы одну смену для тестирования.")
    
    if trips.count() == 0:
        print("   ❌ Нет тестовых рейсов. Создайте хотя бы один рейс для тестирования.")
    
    if orders.count() == 0:
        print("   ❌ Нет тестовых заказов. Создайте хотя бы один заказ для тестирования.")
    
    if shifts.count() > 0 and trips.count() > 0 and orders.count() > 0:
        print("   ✅ Есть тестовые данные для полноценного тестирования.")
    
    # Проверяем наличие продуктов BOTTLE_20L и BOTTLE
    bottle_20l_exists = Product.objects.filter(type_product=Product.TypeProduct.BOTTLE_20L).exists()
    bottle_exists = Product.objects.filter(type_product=Product.TypeProduct.BOTTLE).exists()
    
    if not bottle_20l_exists:
        print("   ❌ Отсутствует продукт BOTTLE_20L (вода с тарой).")
    if not bottle_exists:
        print("   ❌ Отсутствует продукт BOTTLE (тара).")
    if bottle_20l_exists and bottle_exists:
        print("   ✅ Продукты BOTTLE_20L и BOTTLE присутствуют.")
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)

if __name__ == "__main__":
    try:
        check_data_integrity()
    except Exception as e:
        print(f"\n❌ ОШИБКА ПРИ ПРОВЕРКЕ: {e}")
        import traceback
        traceback.print_exc()