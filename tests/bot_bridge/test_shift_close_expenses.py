"""
Тесты закрытия смены с расходами (apps/bot_bridge/views.py → CourierShiftCloseView).

Проверяют:
- запись нескольких расходов (shift expenses) с причиной и стоимостью;
- закрытие смены (status=CLOSED);
- авто-запись расходов в финансовые транзакции как РАСХОД (MINUS) с причиной;
- идемпотентность: повторное закрытие не дублирует транзакции;
- сумма к сдаче = наличные − Σ расходов;
- расходы попадают в отчёт owner-у;
- негативный кейс: корректная валидация (не список / отрицательная сумма).
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from rest_framework.test import APIClient

from apps.accounting.models import FinancialTransactions
from apps.logistics.models import CourierShift, CourierTrip, Order, OrderItem, ShiftExpense
from apps.products.models import Product
from apps.workers.models import Worker


class ShiftCloseExpensesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.courier = Worker.objects.create(
            full_name='Курьер Расходы',
            worker_type=Worker.WorkerType.COURIER,
            tg_id=1001,
        )
        self.shift = CourierShift.objects.create(courier=self.courier)
        self.url = reverse('bot_bridge:courier_shift_close', args=[self.shift.id])

        # Доставляем заказ наличными, чтобы cash_total был ненулевым
        water = Product.objects.create(
            name='Вода 19 (тест)',
            type_product=Product.TypeProduct.WATER,
            price=20000,
        )
        trip = CourierTrip.objects.create(shift=self.shift, full_loaded=2)
        order = Order.objects.create(
            trip=trip,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.DELIVERED,
            delivered_at=timezone.now(),
        )
        OrderItem.objects.create(order=order, product=water, quantity=2)  # 40 000
        CourierShift.objects.filter(pk=self.shift.pk).update(cash_total=40000)
        self.shift.refresh_from_db()

    def _close(self, expenses):
        with patch('apps.bot_bridge.tasks.notify_shift_closed_task') as mock_task:
            resp = self.client.post(
                self.url,
                data={'expenses': expenses},
                format='json',
                HTTP_X_TELEGRAM_ID='1001',
            )
            return resp, mock_task

    def test_close_with_expenses_creates_expenses_and_closes_shift(self):
        resp, mock_task = self._close([
            {'reason': 'Топливо', 'amount': 5000},
            {'reason': 'Тара', 'amount': 3000},
        ])
        self.assertEqual(resp.status_code, 200)

        self.shift.refresh_from_db()
        self.assertEqual(self.shift.status, CourierShift.Status.CLOSED)
        self.assertIsNotNone(self.shift.closed_at)

        expenses = list(self.shift.expenses.values_list('reason', 'amount'))
        self.assertEqual(expenses, [('Топливо', 5000), ('Тара', 3000)])
        self.assertEqual(self.shift.expenses_total, 8000)
        self.assertEqual(self.shift.cash_to_hand, 32000)
        # Отчёт owner-у отправлен
        mock_task.delay.assert_called_once_with(self.shift.id)

    def test_expenses_written_to_finance_as_expense(self):
        self._close([{'reason': 'Топливо', 'amount': 5000}])

        txs = FinancialTransactions.objects.filter(
            transaction_type=FinancialTransactions.TransactionsType.MINUS,
        )
        self.assertEqual(txs.count(), 1)
        tx = txs.first()
        self.assertEqual(tx.amount, 5000)
        self.assertEqual(tx.description, 'Топливо')
        self.assertIn('Топливо', tx.source)
        self.assertEqual(tx.card_amount, 0)

    def test_no_expenses_no_finance_tx(self):
        resp, _ = self._close([])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            FinancialTransactions.objects.filter(
                transaction_type=FinancialTransactions.TransactionsType.MINUS
            ).count(),
            0,
        )

    def test_register_shift_expenses_is_idempotent(self):
        """Повторный вызов не дублирует финансовые транзакции."""
        self._close([{'reason': 'Топливо', 'amount': 5000}])
        self.shift.refresh_from_db()

        from apps.bot_bridge.services import register_shift_expenses
        date = self.shift.closed_at.date() if self.shift.closed_at else self.shift.date
        created = register_shift_expenses(self.shift, date=date)
        self.assertEqual(created, 0)
        self.assertEqual(
            FinancialTransactions.objects.filter(
                transaction_type=FinancialTransactions.TransactionsType.MINUS,
                date=date,
                amount=5000,
            ).count(),
            1,
        )

    def test_invalid_expenses_not_a_list(self):
        resp, _ = self.client.post(
            self.url,
            data={'expenses': 'not-a-list'},
            format='json',
            HTTP_X_TELEGRAM_ID='1001',
        )
        self.assertEqual(resp.status_code, 400)

    def test_negative_amount_rejected(self):
        resp, _ = self._close([{'reason': 'Топливо', 'amount': -100}])
        self.assertEqual(resp.status_code, 400)
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.status, CourierShift.Status.OPEN)