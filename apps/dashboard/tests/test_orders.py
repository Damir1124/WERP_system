"""
Бизнес-тесты статистики заказов (apps/dashboard/services/orders.py).

Проверяют ключевые сценарии ТЗ P6.6:
- заказ, созданный в один день, доставленный в другой (разные метрики);
- отменённые заказы;
- средний чек без деления на ноль;
- отсутствие N+1 запросов в таблице заказов.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.clients.models import Client
from apps.logistics.models import (
    CourierShift, CourierTrip, Order, OrderItem,
)
from apps.products.models import Product
from apps.workers.models import Worker
from apps.dashboard.services.filters import Period, today_local
from apps.dashboard.services.orders import _orders_kpi, get_orders_page, _get_orders_queryset


class OrdersKpiTests(TestCase):
    """Тесты KPI заказов: созданные/доставленные в разные дни."""

    @classmethod
    def setUpTestData(cls):
        cls.today = today_local()

        cls.courier = Worker.objects.create(
            full_name='Тестовый Курьер',
            worker_type=Worker.WorkerType.COURIER,
        )
        cls.product = Product.objects.create(
            name='Вода 20л (тест)',
            type_product=Product.TypeProduct.WATER,
            price=20000,
        )
        cls.client_obj = Client.objects.create(
            name='Тестовый Клиент',
            phone='+998900000001',
        )

        # Смена и рейс на сегодня
        cls.shift = CourierShift.objects.create(courier=cls.courier)
        cls.trip = CourierTrip.objects.create(shift=cls.shift, full_loaded=10)

        # Заказ создан вчера, доставлен сегодня
        cls.order_delivered_today = Order.objects.create(
            trip=cls.trip,
            client=cls.client_obj,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.DELIVERED,
        )
        cls.order_delivered_today.created_at = cls.today - timedelta(days=1)
        cls.order_delivered_today.delivered_at = cls.today
        cls.order_delivered_today.save()

        OrderItem.objects.create(
            order=cls.order_delivered_today,
            product=cls.product,
            quantity=2,
        )

        # Заказ создан сегодня, ещё в ожидании
        cls.order_pending = Order.objects.create(
            trip=cls.trip,
            client=cls.client_obj,
            payment_type=Order.PaymentType.CARD,
            status=Order.Status.PENDING,
        )
        OrderItem.objects.create(
            order=cls.order_pending,
            product=cls.product,
            quantity=1,
        )

        # Заказ создан сегодня, отменён
        cls.order_cancelled = Order.objects.create(
            trip=cls.trip,
            client=cls.client_obj,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.CANCELLED,
        )
        OrderItem.objects.create(
            order=cls.order_cancelled,
            product=cls.product,
            quantity=1,
        )

    def test_delivered_count_by_delivered_at(self):
        """Доставленные считаются по delivered_at, а не created_at."""
        period = Period(mode='today', date_from=self.today, date_to=self.today, errors=[])
        kpi = _orders_kpi(period)

        # order_delivered_today доставлен сегодня (хотя создан вчера)
        self.assertEqual(kpi['orders_delivered'], 1)
        # order_pending и order_cancelled не доставлены
        self.assertLessEqual(kpi['orders_delivered'], 2)

    def test_created_count_by_created_at(self):
        """Созданные считаются по created_at (не включая созданный вчера)."""
        period = Period(mode='today', date_from=self.today, date_to=self.today, errors=[])
        kpi = _orders_kpi(period)

        # Сегодня созданы: pending + cancelled = 2
        # (delivered_today создан вчера и не входит в созданные за сегодня)
        self.assertEqual(kpi['orders_created'], 2)

    def test_pending_count_without_period(self):
        """Ожидающие считаются без периода (текущее состояние)."""
        period = Period(mode='today', date_from=self.today, date_to=self.today, errors=[])
        kpi = _orders_kpi(period)
        self.assertEqual(kpi['orders_pending'], 1)

    def test_cancelled_count(self):
        """Отменённые считаются по created_at."""
        period = Period(mode='today', date_from=self.today, date_to=self.today, errors=[])
        kpi = _orders_kpi(period)
        self.assertEqual(kpi['orders_cancelled'], 1)

    def test_units_sold(self):
        """Продано единиц = сумма quantity доставленных заказов."""
        period = Period(mode='today', date_from=self.today, date_to=self.today, errors=[])
        kpi = _orders_kpi(period)
        # Доставленный заказ: quantity=2
        self.assertEqual(kpi['units_sold'], 2)

    def test_avg_check_no_division_by_zero(self):
        """Средний чек без доставленных заказов = 0, без ошибки деления."""
        yesterday = self.today - timedelta(days=5)
        period = Period(
            mode='custom', date_from=yesterday, date_to=yesterday, errors=[],
        )
        # Вчера-5 не было доставленных
        kpi = _orders_kpi(period)
        self.assertEqual(kpi['avg_check'], 0)


class OrdersPageDataTests(TestCase):
    """Тесты страницы заказов и N+1."""

    @classmethod
    def setUpTestData(cls):
        cls.today = today_local()
        cls.courier = Worker.objects.create(
            full_name='Курьер N+1',
            worker_type=Worker.WorkerType.COURIER,
        )
        cls.product = Product.objects.create(
            name='Продукт N+1',
            type_product=Product.TypeProduct.WATER,
            price=15000,
        )
        cls.client_obj = Client.objects.create(
            name='Клиент Тестовый',
            phone='+998900000002',
        )
        cls.shift = CourierShift.objects.create(courier=cls.courier)
        cls.trip = CourierTrip.objects.create(shift=cls.shift, full_loaded=5)

        # Создаём несколько заказов
        for i in range(5):
            order = Order.objects.create(
                trip=cls.trip,
                client=cls.client_obj,
                payment_type=Order.PaymentType.CASH,
                status=Order.Status.DELIVERED,
                delivered_at=cls.today,
            )
            OrderItem.objects.create(
                order=order,
                product=cls.product,
                quantity=1,
            )

    def test_orders_page_structure(self):
        """get_orders_page возвращает страницу с пагинацией."""
        period = Period(mode='today', date_from=self.today, date_to=self.today, errors=[])
        data = get_orders_page(period, {}, page_num=1, per_page=25)

        self.assertEqual(data.total_count, 5)
        self.assertEqual(data.orders_created, 5)
        self.assertIsNotNone(data.orders_page)
        self.assertEqual(len(data.orders_page.object_list), 5)

    def test_no_n1_queries(self):
        """Проверка отсутствия N+1: запросы к БД не растут линейно с числом заказов."""
        period = Period(mode='today', date_from=self.today, date_to=self.today, errors=[])

        with CaptureQueriesContext(connection) as ctx:
            qs = _get_orders_queryset(period, {})
            list(qs)
            for o in qs[:5]:
                _ = o.get_total_price()
                _ = o.items.all()
            query_count = len(ctx)

        # select_related(client, trip__shift__courier) + prefetch_related(items)
        # Должно быть не более ~10 запросов даже для 5+ заказов
        self.assertLessEqual(query_count, 10)

    def test_search_by_id(self):
        """Поиск по ID заказа находит только его (не затрагивая другие)."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        # Берём ID, который точно не содержится в имени клиента
        orders = Order.objects.filter(client=self.client_obj).order_by('id')
        target = orders[0]
        # ID заказа — уникальный, поиск по нему должен вернуть 1 результат
        data = get_orders_page(period, {'search': str(target.id)}, page_num=1)
        self.assertEqual(data.total_count, 1)
        self.assertEqual(data.orders_page.object_list[0].id, target.id)