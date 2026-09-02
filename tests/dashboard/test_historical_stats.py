"""
Тесты модели HistoricalStats и сервиса исторических показателей.

Проверяют:
- singleton: нельзя создать вторую запись;
- historical показатели складываются с WERP-данными в режиме 'all';
- today / week / month / custom не включают историю;
- отменённый заказ не увеличивает новую воду;
- historical данные не меняют отчёты смен/рейсов/кассы.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounting.models import HistoricalStats
from apps.dashboard.services.filters import Period
from apps.dashboard.services.historical import (
    get_historical_totals, should_include_historical,
)
from apps.dashboard.services.overview import get_overview, OverviewData
from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.products.models import Product
from apps.workers.models import Worker


class HistoricalStatsSingletonTests(TestCase):
    """Тесты singleton-ограничения модели HistoricalStats."""

    def setUp(self):
        self.stats = HistoricalStats.objects.create(
            historical_orders_created_total=1000,
            historical_water_sold_total=5000,
        )

    def test_singleton_prevents_second_record(self):
        """Попытка создать вторую запись вызывает ValidationError."""
        with self.assertRaises(ValidationError):
            HistoricalStats.objects.create(
                historical_orders_created_total=2000,
                historical_water_sold_total=8000,
            )

    def test_singleton_prevents_second_record_via_save(self):
        """Попытка сохранить вторую запись вызывает ValidationError."""
        second = HistoricalStats(
            historical_orders_created_total=2000,
            historical_water_sold_total=8000,
        )
        with self.assertRaises(ValidationError):
            second.save()

    def test_get_historical_totals_returns_values(self):
        """get_historical_totals возвращает корректные значения."""
        totals = get_historical_totals()
        self.assertTrue(totals.exists)
        self.assertEqual(totals.orders_created_total, 1000)
        self.assertEqual(totals.water_sold_total, 5000)

    def test_get_historical_totals_no_record(self):
        """get_historical_totals при отсутствии записи возвращает exists=False."""
        self.stats.delete()
        totals = get_historical_totals()
        self.assertFalse(totals.exists)
        self.assertEqual(totals.orders_created_total, 0)
        self.assertEqual(totals.water_sold_total, 0)

    def test_should_include_historical_all(self):
        """should_include_historical возвращает True только для mode='all'."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        self.assertTrue(should_include_historical(period))

    def test_should_include_historical_today(self):
        period = Period(
            mode='today',
            date_from=timezone.localdate(),
            date_to=timezone.localdate(),
            errors=[]
        )
        self.assertFalse(should_include_historical(period))

    def test_should_include_historical_week(self):
        period = Period(
            mode='week',
            date_from=timezone.localdate(),
            date_to=timezone.localdate(),
            errors=[]
        )
        self.assertFalse(should_include_historical(period))

    def test_should_include_historical_month(self):
        period = Period(
            mode='month',
            date_from=timezone.localdate(),
            date_to=timezone.localdate(),
            errors=[]
        )
        self.assertFalse(should_include_historical(period))

    def test_should_include_historical_custom(self):
        period = Period(
            mode='custom',
            date_from=timezone.localdate(),
            date_to=timezone.localdate(),
            errors=[]
        )
        self.assertFalse(should_include_historical(period))


class HistoricalStatsOverviewTests(TestCase):
    """Тесты добавления исторических показателей в get_overview."""

    def setUp(self):
        self.hist = HistoricalStats.objects.create(
            historical_orders_created_total=350249,
            historical_water_sold_total=1250000,
        )

    def test_all_mode_includes_historical(self):
        """get_overview в режиме 'all' включает исторические показатели."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        data = get_overview(period)
        self.assertIsInstance(data, OverviewData)
        self.assertTrue(data.historical_included)
        self.assertEqual(data.historical_orders_created_total, 350249)
        self.assertEqual(data.historical_water_sold_total, 1250000)
        self.assertEqual(data.orders_created, 350249)
        self.assertEqual(data.units_sold, 1250000)

    def test_today_mode_excludes_historical(self):
        """get_overview в режиме 'today' НЕ включает исторические показатели."""
        today = timezone.localdate()
        period = Period(
            mode='today',
            date_from=today,
            date_to=today,
            errors=[]
        )
        data = get_overview(period)
        self.assertFalse(data.historical_included)
        self.assertEqual(data.historical_orders_created_total, 0)
        self.assertEqual(data.historical_water_sold_total, 0)
        self.assertEqual(data.orders_created, 0)

    def test_week_mode_excludes_historical(self):
        """get_overview в режиме 'week' НЕ включает исторические показатели."""
        period = Period(
            mode='week',
            date_from=timezone.localdate(),
            date_to=timezone.localdate(),
            errors=[]
        )
        data = get_overview(period)
        self.assertFalse(data.historical_included)

    def test_cancelled_orders_dont_increase_water_sold(self):
        """
        Отменённые заказы не увеличивают units_sold.
        units_sold считается только по DELIVERED-заказам.
        """
        worker = Worker.objects.create(
            full_name='Test Courier',
            worker_type=Worker.WorkerType.COURIER,
        )
        shift = CourierShift.objects.create(courier=worker)
        trip = CourierTrip.objects.create(shift=shift, full_loaded=10)

        product = Product.objects.create(
            name='Water 19', type_product=Product.TypeProduct.WATER, price=15000
        )

        # Отменённый заказ — не должен влиять на units_sold
        cancelled = Order.objects.create(
            trip=trip,
            status=Order.Status.CANCELLED,
            payment_type=Order.PaymentType.CASH,
        )
        OrderItem.objects.create(order=cancelled, product=product, quantity=5)

        # Доставленный заказ — должен увеличить units_sold
        delivered = Order.objects.create(
            trip=trip,
            status=Order.Status.DELIVERED,
            payment_type=Order.PaymentType.CASH,
            delivered_at=timezone.now(),
        )
        OrderItem.objects.create(order=delivered, product=product, quantity=3)

        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        data = get_overview(period)

        # 3 (доставленные) + 1250000 (исторические) = 1250003
        self.assertEqual(data.units_sold, 1250003)

    def test_historical_not_in_shifts_and_trips(self):
        """
        Исторические показатели не влияют на активные смены, рейсы и pending.
        """
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        data = get_overview(period)

        self.assertEqual(data.active_shifts_count, 0)
        self.assertEqual(data.active_trips_count, 0)
        self.assertEqual(data.orders_pending, 0)
        self.assertEqual(data.cash_deliveries, 0)
        self.assertEqual(data.income, 0)
        self.assertEqual(data.profit, 0)