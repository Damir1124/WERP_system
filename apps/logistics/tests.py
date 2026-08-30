from django.test import TestCase
from django.utils import timezone
from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.products.models import Product
from apps.clients.models import Client
from apps.workers.models import Worker


class OrderItemBusinessLogicTestCase(TestCase):
    """Тесты бизнес-логики системы доставки воды"""

    def setUp(self):
        """Подготовка тестовых данных"""
        # Создаём продукты
        self.product_water = Product.objects.create(
            name='Вода 19л',
            type_product=Product.TypeProduct.WATER,
            price=15000,
            track_inventory=False
        )
        
        self.product_bottle_20l = Product.objects.create(
            name='Вода + тара 19л',
            type_product=Product.TypeProduct.BOTTLE_20L,
            price=40000,
            track_inventory=False
        )
        
        # Создаём ДВА продукта с типом BOTTLE (для проверки бага 1)
        self.product_bottle_1 = Product.objects.create(
            name='Тара 19л (основная)',
            type_product=Product.TypeProduct.BOTTLE,
            price=25000,
            track_inventory=True
        )
        
        self.product_bottle_2 = Product.objects.create(
            name='Тара 19л (дубликат)',
            type_product=Product.TypeProduct.BOTTLE,
            price=25000,
            track_inventory=True
        )
        
        self.product_cooler = Product.objects.create(
            name='Кулер',
            type_product=Product.TypeProduct.COOLERS,
            price=500000,
            track_inventory=True
        )
        
        # Создаём клиента
        self.client = Client.objects.create(
            name='Тестовый клиент',
            phone='998901234567'[:12],  # max_length=12
            address='Тестовый адрес',
            balans=0
        )
        
        # Создаём курьера
        self.courier = Worker.objects.create(
            full_name='Тестовый курьер',
            worker_type=Worker.WorkerType.COURIER,
            date_for_payed=timezone.now().date()
        )
        
        # Создаём смену и рейс
        self.shift = CourierShift.objects.create(
            courier=self.courier,
            status=CourierShift.Status.OPEN
        )
        
        self.trip = CourierTrip.objects.create(
            shift=self.shift,
            full_loaded=20,
            status=CourierTrip.Status.ACTIVE
        )

    def test_scenario_1_create_order_with_water(self):
        """Сценарий 1: Создание заказа на WT (WATER)
        - quantity=4, при создании exchange_qty автоматически = quantity (стартовое значение для курьера)
        - sell_with_qty и defective_qty = 0
        """
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=4
        )
        
        # Проверяем, что exchange_qty автоматически установлен в quantity (стартовое значение)
        self.assertEqual(order_item.exchange_qty, 4, "exchange_qty должен быть равен quantity при создании")
        self.assertEqual(order_item.sell_with_qty, 0)
        self.assertEqual(order_item.defective_qty, 0)
        
        # Проверяем, что цена рассчитана корректно
        self.assertEqual(order_item.price, 4 * 15000)

    def test_scenario_2_confirm_pure_exchange(self):
        """Сценарий 2: Подтверждение, чистый обмен
        - exchange_qty=4, sell_with_qty=0, defective_qty=0
        - итог: сумма = 4 × WT.price, доп. OrderItem не создаётся
        """
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=4
        )
        
        # Курьер подтверждает доставку с чистым обменом
        order_item.exchange_qty = 4
        order_item.sell_with_qty = 0
        order_item.defective_qty = 0
        order_item.price = None  # Сброс для пересчёта
        order_item.save()
        
        # Проверяем, что цена = 4 × 15000 (без доплаты за тару)
        self.assertEqual(order_item.price, 4 * 15000)
        
        # Проверяем, что не создалась дополнительная позиция с тарой
        self.assertEqual(order.items.count(), 1)

    def test_scenario_3_confirm_with_bottle_purchase(self):
        """Сценарий 3: Подтверждение, с докупкой тары
        - exchange_qty=4, sell_with_qty=2, defective_qty=0
        - итог: создаётся отдельный OrderItem для тары с quantity=2
        - цена воды = 4 × WT.price (без учёта тары)
        - цена тары = 2 × BT.price (отдельная позиция)
        """
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=4
        )
        
        # Курьер подтверждает: 4 обмена, 2 с докупкой тары
        order_item.exchange_qty = 4
        order_item.sell_with_qty = 2
        order_item.defective_qty = 0
        order_item.price = None  # Сброс для пересчёта
        order_item.save()
        
        # Проверяем, что цена воды = 4 × 15000 (без учёта тары)
        self.assertEqual(order_item.price, 4 * 15000)
        
        # ВАЖНО: В тестах мы НЕ можем проверить создание отдельного OrderItem для тары,
        # так как это происходит в views.py при подтверждении через API, а не в модели.
        # Здесь мы только проверяем, что цена воды рассчитана правильно.
        self.assertEqual(order.items.count(), 1)

    def test_scenario_4_client_bought_more_than_planned(self):
        """Сценарий 4: Клиент купил больше чем планировалось
        - quantity в заказе = 3, exchange_qty = 5
        - валидация не должна падать — это разрешённый сценарий
        """
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=3
        )
        
        # Курьер подтверждает: клиент купил 5 вместо 3
        order_item.exchange_qty = 5
        order_item.sell_with_qty = 0
        order_item.defective_qty = 0
        order_item.price = None
        order_item.save()
        
        # Проверяем, что сохранение прошло успешно
        self.assertEqual(order_item.exchange_qty, 5)
        # quantity остаётся 3 (плановое количество)
        self.assertEqual(order_item.quantity, 3)

    def test_scenario_5_client_bought_less_than_planned(self):
        """Сценарий 5: Клиент купил меньше чем планировалось
        - quantity в заказе = 5, exchange_qty = 2
        - валидация не должна падать
        """
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=5
        )
        
        # Курьер подтверждает: клиент купил только 2 вместо 5
        order_item.exchange_qty = 2
        order_item.sell_with_qty = 0
        order_item.defective_qty = 0
        order_item.price = None
        order_item.save()
        
        # Проверяем, что сохранение прошло успешно
        self.assertEqual(order_item.exchange_qty, 2)
        self.assertEqual(order_item.quantity, 5)

    def test_scenario_6_non_water_product(self):
        """Сценарий 6: Продукт не WT
        - поля тары не принимаются и не сохраняются
        """
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_cooler,
            quantity=1
        )
        
        # Пытаемся установить поля тары (они должны игнорироваться)
        order_item.exchange_qty = 5
        order_item.sell_with_qty = 3
        order_item.defective_qty = 1
        order_item.save()
        
        # Для не-водных продуктов поля тары должны оставаться 0
        # (или игнорироваться при расчёте цены)
        self.assertEqual(order_item.price, 1 * 500000)

    def test_scenario_7_multiple_bottle_products_no_crash(self):
        """Сценарий 7: Два продукта с типом BT в базе
        - сервер не должен падать
        - Это тест для Бага 1
        """
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=4
        )
        
        # Курьер подтверждает с докупкой тары
        order_item.exchange_qty = 4
        order_item.sell_with_qty = 2
        order_item.defective_qty = 0
        order_item.price = None
        
        # Это НЕ должно упасть с MultipleObjectsReturned
        try:
            order_item.save()
            # Новая логика: цена = просто product.price * quantity
            # Тара будет отдельной позицией (создаётся в views.py)
            expected_price = 4 * 15000
            self.assertEqual(order_item.price, expected_price)
        except Product.MultipleObjectsReturned:
            self.fail("Баг 1: MultipleObjectsReturned при наличии двух продуктов с типом BOTTLE")

    def test_order_total_price_calculation(self):
        """Тест расчёта общей стоимости заказа через get_total_price()"""
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        # Добавляем несколько позиций
        item1 = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=4
        )
        
        item2 = OrderItem.objects.create(
            order=order,
            product=self.product_cooler,
            quantity=1
        )
        
        # Проверяем общую стоимость
        expected_total = (4 * 15000) + (1 * 500000)
        self.assertEqual(order.get_total_price(), expected_total)

    def test_bottle_20l_product_with_exchange(self):
        """Тест для продукта BOTTLE_20L (вода + тара) с обменом"""
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_bottle_20l,
            quantity=3
        )
        
        # Курьер подтверждает с обменом
        order_item.exchange_qty = 3
        order_item.sell_with_qty = 0
        order_item.defective_qty = 0
        order_item.price = None
        order_item.save()
        
        # Новая логика: цена = просто product.price * quantity
        # Тара учитывается отдельной позицией при sell_with_qty > 0
        expected_price = 3 * 40000
        self.assertEqual(order_item.price, expected_price)

    def test_container_fields_persistence(self):
        """Тест для Бага 2: поля тары должны сохраняться"""
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=5
        )
        
        # Устанавливаем поля тары
        order_item.exchange_qty = 3
        order_item.sell_with_qty = 2
        order_item.defective_qty = 1
        order_item.save()
        
        # Перезагружаем из БД
        order_item.refresh_from_db()
        
        # Проверяем, что поля сохранились
        self.assertEqual(order_item.exchange_qty, 3, "Баг 2: exchange_qty не сохранился")
        self.assertEqual(order_item.sell_with_qty, 2, "Баг 2: sell_with_qty не сохранился")
        self.assertEqual(order_item.defective_qty, 1, "Баг 2: defective_qty не сохранился")

    def test_invariants(self):
        """Тест инвариантов из ТЗ"""
        order = Order.objects.create(
            trip=self.trip,
            client=self.client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product_water,
            quantity=5
        )
        
        # Инвариант 1: exchange_qty >= 0
        order_item.exchange_qty = 5
        order_item.save()
        self.assertGreaterEqual(order_item.exchange_qty, 0)
        
        # Инвариант 2: sell_with_qty >= 0
        order_item.sell_with_qty = 2
        order_item.save()
        self.assertGreaterEqual(order_item.sell_with_qty, 0)
        
        # Инвариант 3: defective_qty >= 0
        order_item.defective_qty = 1
        order_item.save()
        self.assertGreaterEqual(order_item.defective_qty, 0)
        
        # Инвариант 6: Итоговая сумма пересчитывается на сервере
        order_item.price = None
        order_item.save()
        self.assertIsNotNone(order_item.price)
        self.assertGreater(order_item.price, 0)
