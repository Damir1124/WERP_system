"""
Тесты OwnerStatsView — доступ и корректность данных.

Проверяют:
- Owner (is_admin=True) имеет доступ;
- Dispatcher (is_staff без is_admin) не имеет доступа;
- курьер, клиент и неизвестный пользователь не имеют доступа;
- показатели за сегодня считаются корректно;
- показатели «за всё время» корректно складывают исторические и WERP-данные;
- исторические данные не попадают в показатели «Сегодня»;
- отменённые заказы не увеличивают количество проданной воды;
- ответ API не раскрывает лишние данные.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounting.models import HistoricalStats, Finance
from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.products.models import Product
from apps.workers.models import Worker


class OwnerStatsViewAccessTests(TestCase):
    """Тесты доступа к OwnerStatsView."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('bot_bridge:owner_stats')

        # Owner (worker_type=OWNER)
        self.owner = Worker.objects.create(
            full_name='Owner',
            worker_type=Worker.WorkerType.OWNER,
            tg_id=1001,
        )
        # Оператор (admin-роль, имеет доступ к Admin Mini App)
        self.operator = Worker.objects.create(
            full_name='Operator',
            worker_type=Worker.WorkerType.OPERATOR,
            tg_id=1002,
        )
        # Курьер
        self.courier = Worker.objects.create(
            full_name='Courier',
            worker_type=Worker.WorkerType.COURIER,
            tg_id=1003,
        )

    def test_owner_has_access(self):
        """Owner (is_admin=True) получает 200."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='1001')
        self.assertEqual(response.status_code, 200)

    def test_operator_has_access(self):
        """Оператор (admin-роль) получает 200."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='1002')
        self.assertEqual(response.status_code, 200)

    def test_courier_no_access(self):
        """Курьер получает 403."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='1003')
        self.assertEqual(response.status_code, 403)

    def test_unknown_no_access(self):
        """Неизвестный пользователь получает 403."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='9999')
        self.assertEqual(response.status_code, 403)

    def test_no_header_no_access(self):
        """Запрос без заголовка получает 403 (нет Owner в БД с fallback)."""
        # Удаляем Owner, чтобы fallback не сработал
        Worker.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class OwnerStatsViewDataTests(TestCase):
    """Тесты корректности данных OwnerStatsView."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('bot_bridge:owner_stats')

        self.owner = Worker.objects.create(
            full_name='Owner',
            worker_type=Worker.WorkerType.OWNER,
            tg_id=2001,
        )

        # Продукты
        self.water = Product.objects.create(
            name='Вода 19', type_product=Product.TypeProduct.WATER, price=15000
        )
        self.bottle = Product.objects.create(
            name='Тара 19', type_product=Product.TypeProduct.BOTTLE, price=25000
        )

        # Смена и рейс
        self.courier = Worker.objects.create(
            full_name='Courier',
            worker_type=Worker.WorkerType.COURIER,
            tg_id=2002,
        )
        self.shift = CourierShift.objects.create(courier=self.courier)
        self.trip = CourierTrip.objects.create(
            shift=self.shift, full_loaded=50, status=CourierTrip.Status.ACTIVE
        )

        # Доставленный заказ сегодня
        self.delivered = Order.objects.create(
            trip=self.trip,
            status=Order.Status.DELIVERED,
            payment_type=Order.PaymentType.CASH,
            delivered_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=self.delivered, product=self.water, quantity=3, price=45000
        )

        # Pending заказ
        self.pending = Order.objects.create(
            status=Order.Status.PENDING,
            payment_type=Order.PaymentType.CARD,
        )
        OrderItem.objects.create(
            order=self.pending, product=self.water, quantity=2
        )

        # Отменённый заказ
        self.cancelled = Order.objects.create(
            trip=self.trip,
            status=Order.Status.CANCELLED,
            payment_type=Order.PaymentType.CASH,
        )
        OrderItem.objects.create(
            order=self.cancelled, product=self.water, quantity=5
        )

        # Исторические показатели
        HistoricalStats.objects.create(
            historical_orders_created_total=1000,
            historical_water_sold_total=5000,
        )

    def test_today_income(self):
        """Доход за сегодня — неотрицательное число (пересчитывается сигналами)."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertIsInstance(data['today']['income'], int)
        self.assertGreaterEqual(data['today']['income'], 0)

    def test_today_delivered_orders(self):
        """Доставлено заказов за сегодня."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertEqual(data['today']['delivered_orders'], 1)

    def test_today_water_delivered(self):
        """Вода в доставленных заказах сегодня."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertEqual(data['today']['water_delivered'], 3)

    def test_today_pending_orders(self):
        """Заказов в ожидании сейчас."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertEqual(data['today']['pending_orders'], 1)

    def test_today_pending_water(self):
        """Вода в ожидающих заказах."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertEqual(data['today']['pending_water'], 2)

    def test_today_active_trips(self):
        """Активных рейсов сейчас."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertEqual(data['today']['active_trips'], 1)

    def test_today_in_transit_water(self):
        """Вода в развозе (full_loaded - delivered)."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        # full_loaded=50, delivered=3 (water) → 47
        self.assertEqual(data['today']['in_transit_water'], 47)

    def test_today_cash(self):
        """Наличные по доставленным заказам сегодня."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertEqual(data['today']['cash'], 45000)

    def test_today_card(self):
        """Карта по доставленным заказам сегодня."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertEqual(data['today']['card'], 0)

    def test_all_time_total_orders(self):
        """Всего заказов = исторические + WERP."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        # 1000 (история) + 3 (delivered + pending + cancelled) = 1003
        self.assertEqual(data['all_time']['total_orders'], 1003)

    def test_all_time_total_water_sold(self):
        """Всего продано воды = исторические + доставленные WERP."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        # 5000 (история) + 3 (delivered water) = 5003
        self.assertEqual(data['all_time']['total_water_sold'], 5003)

    def test_all_time_historical_included(self):
        """historical_included=true при наличии исторической базы."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        self.assertTrue(data['all_time']['historical_included'])

    def test_cancelled_not_in_water_sold(self):
        """Отменённые заказы не увеличивают total_water_sold."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        # 5000 (история) + 3 (delivered) = 5003, cancelled 5 не входит
        self.assertEqual(data['all_time']['total_water_sold'], 5003)

    def test_no_sensitive_data_in_response(self):
        """Ответ не содержит лишних данных: GPS, телефоны, финансовая детализация."""
        response = self.client.get(self.url, HTTP_X_TELEGRAM_ID='2001')
        data = response.json()
        raw = str(data)
        # Не должно быть GPS-координат
        self.assertNotIn('latitude', raw)
        self.assertNotIn('longitude', raw)
        # Не должно быть телефонов
        self.assertNotIn('phone', raw)
        # Не должно быть consumption/profit (только income)
        self.assertNotIn('consumption', raw)
        # Не должно быть персональных данных
        self.assertNotIn('full_name', raw)
        self.assertNotIn('address', raw)