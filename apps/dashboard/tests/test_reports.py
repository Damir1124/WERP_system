"""
Тесты отчётов по сменам (apps/dashboard/services/reports.py).

Проверяют:
- сводку смены (вода, рейсы, наличные, карта);
- данные рейса (взято воды, пустых, остаток);
- разбивку оплаты по рейсу;
- детали заказов (номер, адрес, оплата, сумма, позиции);
- edge cases: нет рейсов, нет заказов, смешанные оплаты, BONUS;
- рендер страницы /dashboard/reports/ для is_staff.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse

from apps.clients.models import Client
from apps.logistics.models import CourierShift, CourierTrip, Order, OrderItem
from apps.products.models import Product
from apps.workers.models import Worker
from apps.dashboard.services.reports import get_shift_report, get_reports_for_date
from apps.dashboard.views import DashboardReportsView


class ReportBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.courier = Worker.objects.create(
            full_name='Курьер Отчёт',
            worker_type=Worker.WorkerType.COURIER,
        )
        cls.water = Product.objects.create(
            name='Вода 19 (тест)',
            type_product=Product.TypeProduct.WATER,
            price=20000,
        )
        cls.bottle = Product.objects.create(
            name='Тара (тест)',
            type_product=Product.TypeProduct.BOTTLE,
            price=5000,
        )
        cls.client_obj = Client.objects.create(
            name='Клиент Отчёт',
            phone='+998900000010',
        )
        cls.shift = CourierShift.objects.create(courier=cls.courier)
        cls.trip = CourierTrip.objects.create(shift=cls.shift, full_loaded=10)

    def _delivered_order(self, trip, payment_type, items):
        """Создать доставленный заказ с позициями и пересчитать итоги смены."""
        order = Order.objects.create(
            trip=trip,
            client=self.client_obj,
            payment_type=payment_type,
            status=Order.Status.DELIVERED,
            delivery_address_text='ул. Тестовая, 1',
        )
        for product, quantity in items:
            OrderItem.objects.create(order=order, product=product, quantity=quantity)
        # Повторный save триггерит post_save-сигнал пересчёта cash_total/card_total
        order.save(update_fields=['status'])
        return order


class ShiftSummaryTests(ReportBase):
    def test_shift_summary_totals(self):
        """Сводка смены: вода, рейсы, наличные, карта."""
        self._delivered_order(self.trip, Order.PaymentType.CASH, [(self.water, 2)])
        self._delivered_order(self.trip, Order.PaymentType.CARD, [(self.water, 1)])

        report = get_shift_report(self.shift)

        self.assertEqual(report.total_water_sold, 3)
        self.assertEqual(report.total_trips, 1)
        # 2 бутылки наличными (2*20000) + 1 картой (1*20000)
        self.assertEqual(report.total_cash, 40000)
        self.assertEqual(report.total_card, 20000)
        self.assertEqual(report.total_amount, 60000)

    def test_water_sold_counts_only_water_type(self):
        """Вода считается только по типу WATER (тара не входит)."""
        self._delivered_order(self.trip, Order.PaymentType.CASH, [
            (self.water, 2),
            (self.bottle, 3),
        ])
        report = get_shift_report(self.shift)
        self.assertEqual(report.total_water_sold, 2)


class TripDetailsTests(ReportBase):
    def test_trip_details_and_remaining(self):
        """Данные рейса: взято, пустых, остаток (формат mini-app)."""
        self._delivered_order(self.trip, Order.PaymentType.CASH, [(self.water, 2)])

        report = get_shift_report(self.shift)
        trip = report.trips[0]

        self.assertEqual(trip.water_taken, 10)      # full_loaded
        self.assertEqual(trip.empty_returned, 2)    # exchange_qty (2) - sell_with_qty (0)
        self.assertEqual(trip.remaining, 8)         # full_loaded - delivered

    def test_per_trip_payment_breakdown(self):
        """Разбивка оплаты по рейсу."""
        self._delivered_order(self.trip, Order.PaymentType.CASH, [(self.water, 2)])
        self._delivered_order(self.trip, Order.PaymentType.CARD, [(self.water, 1)])

        report = get_shift_report(self.shift)
        trip = report.trips[0]

        self.assertEqual(trip.cash_amount, 40000)
        self.assertEqual(trip.card_amount, 20000)


class OrderDetailsTests(ReportBase):
    def test_order_details_and_items(self):
        """Детали заказа: номер, адрес, оплата, сумма, позиции."""
        order = self._delivered_order(self.trip, Order.PaymentType.CASH, [
            (self.water, 2),
            (self.bottle, 1),
        ])

        report = get_shift_report(self.shift)
        report_order = report.trips[0].orders[0]

        self.assertEqual(report_order.id, order.id)
        self.assertEqual(report_order.display_number, order.human_number)
        self.assertEqual(report_order.address, 'ул. Тестовая, 1')
        self.assertEqual(report_order.payment_type_display, 'Наличные')
        # 2*20000 + 1*5000
        self.assertEqual(report_order.total_amount, 45000)

        names = {i.product_name for i in report_order.items}
        self.assertEqual(names, {'Вода 19 (тест)', 'Тара (тест)'})
        water_item = next(i for i in report_order.items if i.product_name == 'Вода 19 (тест)')
        self.assertEqual(water_item.quantity, 2)
        self.assertEqual(water_item.sum, 40000)


class EdgeCaseTests(ReportBase):
    def test_shift_without_trips(self):
        """Смена без рейсов."""
        empty_shift = CourierShift.objects.create(courier=self.courier)
        report = get_shift_report(empty_shift)
        self.assertEqual(report.total_trips, 0)
        self.assertEqual(report.trips, [])
        self.assertEqual(report.total_water_sold, 0)

    def test_trip_without_orders(self):
        """Рейс без заказов."""
        empty_trip = CourierTrip.objects.create(shift=self.shift, full_loaded=5)
        report = get_shift_report(self.shift)
        trip = next(t for t in report.trips if t.id == empty_trip.id)
        self.assertEqual(trip.orders, [])
        self.assertEqual(trip.cash_amount, 0)
        self.assertEqual(trip.card_amount, 0)

    def test_bonus_not_counted_in_cash_or_card(self):
        """BONUS-заказы не входят в наличные/карту."""
        self._delivered_order(self.trip, Order.PaymentType.BONUS, [(self.water, 2)])

        report = get_shift_report(self.shift)
        trip = report.trips[0]

        self.assertEqual(trip.cash_amount, 0)
        self.assertEqual(trip.card_amount, 0)
        self.assertEqual(report.total_cash, 0)
        self.assertEqual(report.total_card, 0)
        # Вода всё равно учитывается
        self.assertEqual(report.total_water_sold, 2)

    def test_get_reports_for_date_filters_by_date(self):
        """get_reports_for_date возвращает смены только за указанную дату."""
        from datetime import date
        today = self.shift.date
        other_day = date(2020, 1, 1)

        other_shift = CourierShift.objects.create(courier=self.courier)
        other_shift.date = other_day
        other_shift.save(update_fields=['date'])

        reports = get_reports_for_date(today)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].id, self.shift.id)

        reports_other = get_reports_for_date(other_day)
        self.assertEqual(len(reports_other), 1)
        self.assertEqual(reports_other[0].id, other_shift.id)


class ReportsViewTests(TestCase):
    """Тесты страницы /dashboard/reports/."""

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(
            username='staff', password='pass123', is_staff=True,
        )
        cls.courier = Worker.objects.create(
            full_name='Курьер View',
            worker_type=Worker.WorkerType.COURIER,
        )
        cls.water = Product.objects.create(
            name='Вода 19 (view)',
            type_product=Product.TypeProduct.WATER,
            price=20000,
        )
        cls.client_obj = Client.objects.create(
            name='Клиент View',
            phone='+998900000011',
        )
        cls.shift = CourierShift.objects.create(courier=cls.courier)
        cls.trip = CourierTrip.objects.create(shift=cls.shift, full_loaded=10)
        order = Order.objects.create(
            trip=cls.trip,
            client=cls.client_obj,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.DELIVERED,
            delivery_address_text='ул. View, 5',
        )
        OrderItem.objects.create(order=order, product=cls.water, quantity=2)

    def setUp(self):
        self.factory = RequestFactory()

    def test_reports_page_renders_for_staff(self):
        """Страница отчётов доступна is_staff и содержит данные смены."""
        url = reverse('dashboard:reports') + f'?date={self.shift.date.isoformat()}'
        request = self.factory.get(url)
        request.user = self.staff_user
        response = DashboardReportsView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Курьер View')
        self.assertContains(response, 'Вода 19 (view)')
        self.assertContains(response, 'ул. View, 5')

    def test_reports_page_empty_date(self):
        """Без параметра date страница рендерится (по умолчанию — сегодня)."""
        request = self.factory.get(reverse('dashboard:reports'))
        request.user = self.staff_user
        response = DashboardReportsView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_reports_page_invalid_date(self):
        """Некорректная дата → страница рендерится с ошибкой, без падения."""
        request = self.factory.get(reverse('dashboard:reports') + '?date=not-a-date')
        request.user = self.staff_user
        response = DashboardReportsView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Некорректный формат даты')
