"""
Тесты автоматических отчётов о закрытии рейсов и смен курьеров
(apps/bot_bridge/reports.py).

Проверяют:
- построение HTML-текста отчёта по рейсу (событие, время, финансы, тара, авто);
- построение HTML-текста отчёта по смене (агрегация тары по рейсам);
- отправку всем владельцам (worker_type=OWNER) + в ADMIN_CHAT_ID;
- возврат False, если получателей нет.
"""
from datetime import date

from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch

from apps.clients.models import Client
from apps.logistics.models import CourierShift, CourierTrip, Order, OrderItem
from apps.products.models import Product
from apps.workers.models import Worker
from apps.warehouse.models import Garage

from apps.bot_bridge.reports import (
    _resolve_admin_chat_ids,
    build_shift_report_text,
    build_trip_report_text,
    notify_shift_closed,
    notify_trip_closed,
)


class ReportBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.courier = Worker.objects.create(
            full_name='Курьер Отчёт',
            worker_type=Worker.WorkerType.COURIER,
            tg_id=1001,
        )
        cls.water = Product.objects.create(
            name='Вода 19 (тест)',
            type_product=Product.TypeProduct.WATER,
            price=20000,
        )
        cls.client_obj = Client.objects.create(
            name='Клиент Отчёт',
            phone='+998900000010',
        )
        cls.shift = CourierShift.objects.create(courier=cls.courier)
        cls.trip = CourierTrip.objects.create(shift=cls.shift, full_loaded=10)

    def _delivered_order(self, trip, payment_type, quantity):
        """Создать доставленный заказ с одной WATER-позицией."""
        order = Order.objects.create(
            trip=trip,
            client=self.client_obj,
            payment_type=payment_type,
            status=Order.Status.DELIVERED,
            delivery_address_text='ул. Тестовая, 1',
        )
        OrderItem.objects.create(order=order, product=self.water, quantity=quantity)
        return order


class TripReportTests(ReportBase):
    def test_trip_report_contains_all_sections(self):
        """Отчёт по рейсу: событие, время, финансы, тара, контекст."""
        self._delivered_order(self.trip, Order.PaymentType.CASH, 2)
        self._delivered_order(self.trip, Order.PaymentType.CARD, 1)
        self.trip.finished_at = timezone.now()
        self.trip.save(update_fields=['finished_at'])

        text = build_trip_report_text(self.trip)

        # Событие и время
        self.assertIn('Рейс закрыт', text)
        self.assertIn('Время закрытия', text)
        # Контекст
        self.assertIn(f'Рейс: #{self.trip.id}', text)
        self.assertIn('Курьер: Курьер Отчёт', text)
        # Финансы (2*20000 наличными + 1*20000 картой)
        self.assertIn('Наличные: 40 000 сум', text)
        self.assertIn('Карта: 20 000 сум', text)
        self.assertIn('Итого: 60 000 сум', text)
        self.assertIn('Продано воды: 3 бак', text)
        # Тара
        self.assertIn('Взято: 10 бак', text)
        self.assertIn('Возвращено пустых: 3 шт', text)
        self.assertIn('Осталось в машине: 7 бак', text)

    def test_trip_report_includes_vehicle(self):
        """Номер и название авто из Garage попадают в отчёт."""
        Garage.objects.create(
            courier=self.courier,
            vehicle_name='Газель',
            plate_number='123ABC',
            milage=1000,
            year=date(2020, 1, 1),
        )
        text = build_trip_report_text(self.trip)
        self.assertIn('Авто: 123ABC Газель', text)

    def test_trip_report_without_vehicle(self):
        """Если авто не привязано, строка про авто отсутствует."""
        text = build_trip_report_text(self.trip)
        self.assertNotIn('Авто:', text)


class ShiftReportTests(ReportBase):
    def test_shift_report_contains_all_sections(self):
        """Отчёт по смене: событие, время, финансы, тара (по всем рейсам)."""
        self._delivered_order(self.trip, Order.PaymentType.CASH, 2)
        self._delivered_order(self.trip, Order.PaymentType.CARD, 1)
        self.shift.closed_at = timezone.now()
        self.shift.save(update_fields=['closed_at'])

        text = build_shift_report_text(self.shift)

        self.assertIn('Смена закрыта', text)
        self.assertIn('Время закрытия', text)
        self.assertIn(f'Смена: #{self.shift.id}', text)
        self.assertIn('Курьер: Курьер Отчёт', text)
        # Финансы
        self.assertIn('Наличные: 40 000 сум', text)
        self.assertIn('Карта: 20 000 сум', text)
        self.assertIn('Итого: 60 000 сум', text)
        self.assertIn('Продано воды: 3 бак', text)
        self.assertIn('Заказов выполнено: 2', text)
        self.assertIn('Рейсов: 1', text)
        # Тара агрегируется по всем рейсам
        self.assertIn('Взято: 10 бак', text)
        self.assertIn('Возвращено пустых: 3 шт', text)
        self.assertIn('Осталось в машине: 7 бак', text)

    def test_shift_report_aggregates_water_across_trips(self):
        """Тара по смене суммируется по всем рейсам."""
        self._delivered_order(self.trip, Order.PaymentType.CASH, 2)
        second_trip = CourierTrip.objects.create(shift=self.shift, full_loaded=5)
        self._delivered_order(second_trip, Order.PaymentType.CASH, 1)

        text = build_shift_report_text(self.shift)

        # Взято: 10 + 5 = 15; пустых: 2 + 1 = 3; остаток: (10-2)+(5-1) = 12
        self.assertIn('Взято: 15 бак', text)
        self.assertIn('Возвращено пустых: 3 шт', text)
        self.assertIn('Осталось в машине: 12 бак', text)


class NotifyTests(ReportBase):
    @override_settings(ADMIN_CHAT_ID='123456789')
    @patch('apps.bot_bridge.notify.send_telegram_message', return_value=True)
    def test_notify_trip_closed_sends_to_admin_chat(self, mock_send):
        """Отчёт о рейсе уходит в ADMIN_CHAT_ID."""
        result = notify_trip_closed(self.trip)
        self.assertTrue(result)
        mock_send.assert_called_once()
        chat_id, text = mock_send.call_args[0]
        self.assertEqual(chat_id, 123456789)
        self.assertIn('Рейс закрыт', text)

    @override_settings(ADMIN_CHAT_ID='123456789')
    @patch('apps.bot_bridge.notify.send_telegram_message', return_value=True)
    def test_notify_shift_closed_sends_to_admin_chat(self, mock_send):
        """Отчёт о смене уходит в ADMIN_CHAT_ID."""
        result = notify_shift_closed(self.shift)
        self.assertTrue(result)
        mock_send.assert_called_once()
        chat_id, text = mock_send.call_args[0]
        self.assertEqual(chat_id, 123456789)
        self.assertIn('Смена закрыта', text)

    def test_resolve_admin_chat_ids_includes_all_owners(self):
        """Собираются все владельцы (worker_type=OWNER) с tg_id."""
        Worker.objects.create(
            full_name='Владелец 1',
            worker_type=Worker.WorkerType.OWNER,
            tg_id=999,
        )
        Worker.objects.create(
            full_name='Владелец 2',
            worker_type=Worker.WorkerType.OWNER,
            tg_id=888,
        )
        with override_settings(ADMIN_CHAT_ID=None):
            chat_ids = _resolve_admin_chat_ids()
        self.assertEqual(sorted(chat_ids), [888, 999])

    def test_resolve_admin_chat_ids_includes_admin_chat_id(self):
        """ADMIN_CHAT_ID добавляется к списку владельцев."""
        Worker.objects.create(
            full_name='Владелец',
            worker_type=Worker.WorkerType.OWNER,
            tg_id=999,
        )
        with override_settings(ADMIN_CHAT_ID='123456789'):
            chat_ids = _resolve_admin_chat_ids()
        self.assertEqual(sorted(chat_ids), [999, 123456789])

    @override_settings(ADMIN_CHAT_ID='123456789')
    @patch('apps.bot_bridge.notify.send_telegram_message', return_value=True)
    def test_notify_sends_to_each_owner(self, mock_send):
        """Отчёт уходит каждому владельцу."""
        Worker.objects.create(
            full_name='Владелец 1',
            worker_type=Worker.WorkerType.OWNER,
            tg_id=999,
        )
        Worker.objects.create(
            full_name='Владелец 2',
            worker_type=Worker.WorkerType.OWNER,
            tg_id=888,
        )
        result = notify_trip_closed(self.trip)
        self.assertTrue(result)
        # 2 владельца + ADMIN_CHAT_ID = 3 получателя
        self.assertEqual(mock_send.call_count, 3)
        sent_chats = {call.args[0] for call in mock_send.call_args_list}
        self.assertEqual(sent_chats, {999, 888, 123456789})

    @override_settings(ADMIN_CHAT_ID=None)
    @patch('apps.bot_bridge.notify.send_telegram_message', return_value=True)
    def test_notify_returns_false_without_recipients(self, mock_send):
        """Если получателей нет (нет владельцев и ADMIN_CHAT_ID), уведомление не отправляется."""
        result = notify_trip_closed(self.trip)
        self.assertFalse(result)
        mock_send.assert_not_called()