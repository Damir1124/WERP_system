#!/usr/bin/env python
"""
Исправленный скрипт для тестирования системы смен и рейсов (пункт 3.0.1)
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
from django.utils import timezone

def main():
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ СМЕН И РЕЙСОВ (пункт 3.0.1)")
    print("=" * 60)
    
    # 1. Проверка существующих данных
    print("\n1. ПРОВЕРКА СУЩЕСТВУЮЩИХ ДАННЫХ:")
    print(f"   Курьеров: {Worker.objects.count()}")
    print(f"   Клиентов: {Client.objects.count()}")
    print(f"   Продуктов: {Product.objects.count()}")
    print(f"   Смен: {CourierShift.objects.count()}")
    print(f"   Рейсов: {CourierTrip.objects.count()}")
    print(f"   Заказов: {Order.objects.count()}")
    
    # 2. Создание тестовых данных (если нужно)
    print("\n2. СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ:")
    
    # Создаем курьера
    if Worker.objects.count() == 0:
        courier = Worker.objects.create(
            full_name="Тестовый Курьер",
            worker_type=Worker.WorkerType.COURIER
        )
        print(f"   ✅ Создан курьер: {courier}")
    else:
        courier = Worker.objects.first()
        print(f"   ✅ Используем существующего курьера: {courier}")
    
    # Создаем клиента (правильное поле name вместо full_name)
    if Client.objects.count() == 0:
        client = Client.objects.create(
            name="Тестовый Клиент",  # ПРАВИЛЬНОЕ ПОЛЕ!
            phone="+79991234567",
            address="Тестовый адрес"
        )
        print(f"   ✅ Создан клиент: {client}")
    else:
        client = Client.objects.first()
        print(f"   ✅ Используем существующего клиента: {client}")
    
    # Создаем продукты BOTTLE_20L и BOTTLE
    bottle_20l, created = Product.objects.get_or_create(
        type_product=Product.TypeProduct.BOTTLE_20L,
        defaults={'name': 'Вода 20л с тарой', 'price': 1000}
    )
    if created:
        print(f"   ✅ Создан продукт BOTTLE_20L: {bottle_20l}")
    else:
        print(f"   ✅ Используем существующий BOTTLE_20L: {bottle_20l}")
    
    bottle, created = Product.objects.get_or_create(
        type_product=Product.TypeProduct.BOTTLE,
        defaults={'name': 'Тара 20л', 'price': 500}
    )
    if created:
        print(f"   ✅ Создан продукт BOTTLE: {bottle}")
    else:
        print(f"   ✅ Используем существующий BOTTLE: {bottle}")
    
    # 3. Создание смены
    print("\n3. СОЗДАНИЕ СМЕНЫ:")
    shift = CourierShift.objects.create(courier=courier)
    print(f"   ✅ Создана смена: {shift}")
    print(f"      Статус: {shift.get_status_display()}")
    print(f"      Дата: {shift.date}")
    print(f"      Наличные: {shift.cash_total}, Безнал: {shift.card_total}")
    
    # 4. Создание рейса
    print("\n4. СОЗДАНИЕ РЕЙСА:")
    trip = CourierTrip.objects.create(
        shift=shift,
        full_loaded=10,
        full_returned=0
    )
    print(f"   ✅ Создан рейс: {trip}")
    print(f"      Загружено полных: {trip.full_loaded}")
    print(f"      Статус: {trip.get_status_display()}")
    
    # 5. Создание заказа (ожидающего доставки)
    print("\n5. СОЗДАНИЕ ЗАКАЗА (ожидает доставки):")
    order = Order.objects.create(
        trip=trip,
        client=client,
        product=bottle_20l,
        quantity=2,
        status=Order.Status.PENDING,
        payment_type=Order.PaymentType.CASH
    )
    print(f"   ✅ Создан заказ: {order}")
    print(f"      Статус: {order.get_status_display()}")
    print(f"      Количество: {order.quantity}")
    print(f"      Цена (авторасчет): {order.price}")
    print(f"      Тип оплаты: {order.get_payment_type_display()}")
    
    # 6. Подтверждение доставки
    print("\n6. ПОДТВЕРЖДЕНИЕ ДОСТАВКИ:")
    print("   Меняем статус заказа на DELIVERED...")
    order.status = Order.Status.DELIVERED
    order.container_op = Order.ContainerOp.EXCHANGE
    order.save()  # Здесь должны сработать сигналы!
    
    print(f"   ✅ Заказ обновлен:")
    print(f"      Статус: {order.get_status_display()}")
    print(f"      Операция с тарой: {order.get_container_op_display()}")
    print(f"      Цена: {order.price}")
    
    # 7. Проверка обновления смены
    print("\n7. ПРОВЕРКА ОБНОВЛЕНИЯ СМЕНЫ:")
    shift.refresh_from_db()
    print(f"   Наличные за смену: {shift.cash_total} (ожидается: {order.price})")
    print(f"   Безнал за смену: {shift.card_total} (ожидается: 0)")
    
    if shift.cash_total == order.price:
        print("   ✅ Сигнал update_shift_totals_on_order сработал корректно!")
    else:
        print("   ❌ ПРОБЛЕМА: Сигнал не сработал или сработал некорректно")
    
    # 8. Проверка сводки по рейсу
    print("\n8. ПРОВЕРКА СВОДКИ ПО РЕЙСУ:")
    summary = trip.get_trip_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    if summary['delivered'] == order.quantity:
        print("   ✅ Метод get_trip_summary() работает корректно!")
    else:
        print(f"   ❌ ПРОБЛЕМА: delivered={summary['delivered']}, ожидается {order.quantity}")
    
    # 9. Закрытие смены
    print("\n9. ЗАКРЫТИЕ СМЕНЫ:")
    shift.close()
    shift.refresh_from_db()
    print(f"   Статус смены: {shift.get_status_display()}")
    print(f"   Время закрытия: {shift.closed_at}")
    
    if shift.status == CourierShift.Status.CLOSED:
        print("   ✅ Метод close() работает корректно!")
    else:
        print("   ❌ ПРОБЛЕМА: Смена не закрылась")
    
    # 10. Итоговая проверка
    print("\n" + "=" * 60)
    print("ИТОГОВАЯ ПРОВЕРКА:")
    print("=" * 60)
    
    checks = [
        ("Смена создана", shift is not None),
        ("Рейс создан", trip is not None),
        ("Заказ создан", order is not None),
        ("Цена рассчитана", order.price == bottle_20l.price * order.quantity),
        ("Смена обновлена (cash_total)", shift.cash_total == order.price),
        ("Сводка рейса работает", summary['delivered'] == order.quantity),
        ("Смена закрывается", shift.status == CourierShift.Status.CLOSED),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"   {status} {check_name}")
        if not check_result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("   Система смен и рейсов работает корректно.")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("   Требуется отладка сигналов или логики.")
    print("=" * 60)
    
    # 11. Дополнительная информация для отладки
    print("\nДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ДЛЯ ОТЛАДКИ:")
    print(f"   ID смены: {shift.id}")
    print(f"   ID рейса: {trip.id}")
    print(f"   ID заказа: {order.id}")
    print(f"   Цена продукта: {bottle_20l.price}")
    print(f"   Ожидаемая цена заказа: {bottle_20l.price * order.quantity}")
    
    # Проверка сигналов вручную
    print("\nПРОВЕРКА СИГНАЛОВ:")
    from apps.logistics.signals import update_shift_totals_on_order
    from django.db.models.signals import post_save
    
    # Проверяем, подключен ли сигнал
    receivers = post_save.receivers
    print(f"   Всего receivers для post_save: {len(receivers)}")
    
    # Проверяем конкретно наш сигнал
    print("\nДля дальнейшей отладки:")
    print("1. Проверьте файл apps/logistics/signals.py")
    print("2. Убедитесь, что сигналы импортируются в apps.py")
    print("3. Проверьте логи Django (если есть настройки logging)")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ОШИБКА ВЫПОЛНЕНИЯ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)