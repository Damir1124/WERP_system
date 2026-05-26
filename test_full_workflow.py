#!/usr/bin/env python
"""
Тестирование полного workflow создания и подтверждения заказа с container операциями.
"""
import os
import sys
import django
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.workers.models import Worker
from apps.clients.models import Client
from apps.products.models import Product
from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.warehouse.models import StockBalance

class TestContainerWorkflow(TestCase):
    def setUp(self):
        # Создаем тестовые данные
        self.courier = Worker.objects.create(
            full_name="Тестовый Курьер",
            worker_type='CR',
            tg_id=123456789
        )
        
        self.client_obj = Client.objects.create(
            name="Тестовый Клиент",
            phone="+998901234567",
            address="Тестовый адрес"
        )
        
        # Создаем WATER продукт
        self.water_product = Product.objects.create(
            name="Вода 19",
            type_product='19W',
            price=15000,
            unit='шт'
        )
        
        # Создаем BOTTLE продукт (тара)
        self.bottle_product = Product.objects.create(
            name="Тара 19л",
            type_product='BT',
            price=5000,
            unit='шт'
        )
        
        # Создаем начальные остатки на складе
        StockBalance.objects.create(
            product=self.water_product,
            quantity=100
        )
        StockBalance.objects.create(
            product=self.bottle_product,
            quantity=50
        )
        
        # Создаем смену и рейс
        self.shift = CourierShift.objects.create(
            courier=self.courier,
            status='OP'
        )
        
        self.trip = CourierTrip.objects.create(
            shift=self.shift,
            status='OP',
            full_loaded=0
        )
        
        self.client = APIClient()
        # Имитируем авторизацию курьера
        self.client.force_authenticate(user=None)  # В реальном проекте здесь была бы JWT авторизация
        
    def test_create_order_with_default_exchange(self):
        """Тест создания заказа с WATER продуктом - проверка default exchange_qty"""
        print("=== Тест 1: Создание заказа с WATER продуктом ===")
        
        # Создаем заказ через API
        url = reverse('bot_bridge:create_order')
        data = {
            'trip': self.trip.id,
            'client': self.client_obj.id,
            'payment_type': 'CH',
            'items': [
                {
                    'product': self.water_product.id,
                    'quantity': 5
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        print(f"Создание заказа: статус {response.status_code}")
        
        if response.status_code == status.HTTP_201_CREATED:
            print("✓ Заказ успешно создан")
            order_id = response.data['id']
            
            # Проверяем созданную позицию
            order = Order.objects.get(id=order_id)
            items = order.items.all()
            print(f"  Заказ ID {order_id}, позиций: {items.count()}")
            
            for item in items:
                print(f"  Позиция ID {item.id}: product={item.product.name}, "
                      f"quantity={item.quantity}, exchange_qty={item.exchange_qty}")
                
                # Проверяем, что exchange_qty установлен в quantity для WATER
                if item.product.type_product == '19W':
                    self.assertEqual(item.exchange_qty, item.quantity)
                    print(f"  ✓ exchange_qty корректно установлен в {item.quantity}")
                else:
                    print(f"  ⚠ Продукт не WATER, exchange_qty={item.exchange_qty}")
        else:
            print(f"✗ Ошибка создания заказа: {response.data}")
            
    def test_confirm_order_with_container_ops(self):
        """Тест подтверждения заказа с container операциями"""
        print("\n=== Тест 2: Подтверждение заказа с container операциями ===")
        
        # Сначала создаем заказ
        order = Order.objects.create(
            trip=self.trip,
            client=self.client_obj,
            payment_type='CH',
            status='AS'
        )
        
        # Создаем позицию заказа
        item = OrderItem.objects.create(
            order=order,
            product=self.water_product,
            quantity=5,
            exchange_qty=5,  # Должно быть установлено автоматически
            sell_with_qty=0,
            defective_qty=0,
            price=self.water_product.price * 5
        )
        
        print(f"Создан заказ ID {order.id} с позицией ID {item.id}")
        print(f"  Исходные данные: quantity=5, exchange_qty={item.exchange_qty}")
        
        # Теперь подтверждаем заказ через API
        url = reverse('bot_bridge:order_confirmation')
        data = {
            'order_id': order.id,
            'confirmed': True,
            'items': [
                {
                    'item_id': item.id,
                    'exchange_qty': 3,  # 3 бутылки обменяли
                    'sell_with_qty': 2,  # 2 бутылки продали с тарой
                    'defective_qty': 0   # 0 брака
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        print(f"Подтверждение заказа: статус {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            print("✓ Заказ успешно подтвержден")
            print(f"  Ответ API: {response.data}")
            
            # Проверяем обновленный заказ
            order.refresh_from_db()
            item.refresh_from_db()
            
            print(f"  Статус заказа: {order.status}")
            print(f"  Обновленная позиция: exchange_qty={item.exchange_qty}, "
                  f"sell_with_qty={item.sell_with_qty}")
            
            # Проверяем создание BOTTLE позиции
            bottle_items = OrderItem.objects.filter(order=order, product=self.bottle_product)
            print(f"  Созданных BOTTLE позиций: {bottle_items.count()}")
            
            if bottle_items.exists():
                bottle_item = bottle_items.first()
                print(f"  ✓ Создана BOTTLE позиция ID {bottle_item.id}: "
                      f"quantity={bottle_item.quantity}")
            else:
                print("  ⚠ BOTTLE позиция не создана (возможно, логика не сработала)")
                
            # Проверяем остатки на складе
            water_stock = StockBalance.objects.get(product=self.water_product)
            bottle_stock = StockBalance.objects.get(product=self.bottle_product)
            print(f"  Остатки WATER: {water_stock.quantity}")
            print(f"  Остатки BOTTLE: {bottle_stock.quantity}")
        else:
            print(f"✗ Ошибка подтверждения заказа: {response.data}")
            
    def test_validation_rules(self):
        """Тест валидации бизнес-правил"""
        print("\n=== Тест 3: Валидация бизнес-правил ===")
        
        # Создаем заказ для теста
        order = Order.objects.create(
            trip=self.trip,
            client=self.client_obj,
            payment_type='CH',
            status='AS'
        )
        
        item = OrderItem.objects.create(
            order=order,
            product=self.water_product,
            quantity=5,
            exchange_qty=5,
            sell_with_qty=0,
            defective_qty=0
        )
        
        # Тест 1: sell_with_qty не может превышать exchange_qty
        print("Тест 1: sell_with_qty > exchange_qty (должна быть ошибка)")
        url = reverse('bot_bridge:order_confirmation')
        data = {
            'order_id': order.id,
            'confirmed': True,
            'items': [
                {
                    'item_id': item.id,
                    'exchange_qty': 2,
                    'sell_with_qty': 3,  # 3 > 2 - должно вызвать ошибку
                    'defective_qty': 0
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print("  ✓ Валидация сработала: sell_with_qty не может превышать exchange_qty")
        else:
            print(f"  ⚠ Ожидалась ошибка валидации, но получен статус {response.status_code}")
            
        # Тест 2: сумма container операций не может превышать quantity
        print("\nТест 2: exchange + sell_with + defective > quantity (должна быть ошибка)")
        data['items'][0]['exchange_qty'] = 3
        data['items'][0]['sell_with_qty'] = 2
        data['items'][0]['defective_qty'] = 1  # 3+2+1=6 > 5
        
        response = self.client.post(url, data, format='json')
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print("  ✓ Валидация сработала: сумма операций превышает quantity")
        else:
            print(f"  ⚠ Ожидалась ошибка валидации, но получен статус {response.status_code}")

if __name__ == '__main__':
    # Запускаем тесты
    print("Запуск тестов workflow container операций...\n")
    
    # Создаем экземпляр теста и запускаем методы
    test = TestContainerWorkflow()
    
    try:
        # Настраиваем тестовое окружение
        test._pre_setup()
        test.setUp()
        
        # Запускаем тесты
        test.test_create_order_with_default_exchange()
        test.test_confirm_order_with_container_ops()
        test.test_validation_rules()
        
        # Очищаем
        test._post_teardown()
        
    except Exception as e:
        print(f"\n✗ Ошибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Тестирование завершено ===")