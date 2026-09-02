"""
Тесты сервиса главной сводки Dashboard (apps/dashboard/services/overview.py).

Проверяют:
- работу с пустым периодом (all mode)
- корректность структуры возвращаемых данных
- отсутствие ошибок при пустой БД
"""
from django.test import TestCase

from apps.dashboard.services.filters import Period
from apps.dashboard.services.overview import (
    get_overview, _finance_kpi, _orders_kpi, _active_work,
    _active_shifts_table, _recent_orders, _top_products, _top_couriers,
    _stock_alerts, OverviewData,
)


class OverviewServiceTests(TestCase):
    """Тесты get_overview и вспомогательных функций."""

    def test_get_overview_all_mode(self):
        """get_overview с period=all возвращает OverviewData с нулями."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        data = get_overview(period)
        self.assertIsInstance(data, OverviewData)
        self.assertEqual(data.income, 0)
        self.assertEqual(data.orders_created, 0)
        self.assertEqual(data.orders_delivered, 0)
        self.assertEqual(data.active_shifts_count, 0)
        self.assertEqual(data.active_trips_count, 0)
        self.assertIsInstance(data.active_shifts, list)
        self.assertIsInstance(data.recent_orders, list)
        self.assertIsInstance(data.top_products, list)
        self.assertIsInstance(data.top_couriers, list)
        self.assertIsInstance(data.stock_alerts, list)

    def test_finance_kpi_empty(self):
        """_finance_kpi с пустым периодом возвращает нули."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        result = _finance_kpi(period)
        self.assertEqual(result['income'], 0)
        self.assertEqual(result['consumption'], 0)
        self.assertEqual(result['profit'], 0)
        self.assertEqual(result['card_profit'], 0)
        self.assertEqual(result['cash_deliveries'], 0)

    def test_orders_kpi_empty(self):
        """_orders_kpi с пустым периодом возвращает нули."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        result = _orders_kpi(period)
        self.assertEqual(result['orders_created'], 0)
        self.assertEqual(result['orders_delivered'], 0)
        self.assertEqual(result['orders_cancelled'], 0)
        self.assertEqual(result['orders_pending'], 0)
        self.assertEqual(result['units_sold'], 0)

    def test_active_work_returns_ints(self):
        """_active_work возвращает корректные целые числа."""
        result = _active_work()
        self.assertIsInstance(result['active_shifts_count'], int)
        self.assertIsInstance(result['active_trips_count'], int)
        self.assertIsInstance(result['orders_pending'], int)
        self.assertIsInstance(result['unassigned_orders_count'], int)
        self.assertIsInstance(result['critical_stock_count'], int)
        self.assertGreaterEqual(result['active_shifts_count'], 0)
        self.assertGreaterEqual(result['active_trips_count'], 0)

    def test_active_shifts_table_empty(self):
        """_active_shifts_table возвращает пустой список (нет данных в тестовой БД)."""
        result = _active_shifts_table()
        self.assertIsInstance(result, list)
        # В тестовой БД нет курьеров/смен, поэтому список пуст
        self.assertEqual(len(result), 0)

    def test_recent_orders_empty(self):
        """_recent_orders возвращает пустой список при отсутствии заказов."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        result = _recent_orders(period)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_top_products_empty(self):
        """_top_products возвращает пустой список при отсутствии данных."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        result = _top_products(period)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_top_couriers_empty(self):
        """_top_couriers возвращает пустой список при отсутствии данных."""
        period = Period(mode='all', date_from=None, date_to=None, errors=[])
        result = _top_couriers(period)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_stock_alerts_empty(self):
        """_stock_alerts возвращает список (пустой, т.к. в тестовой БД нет StockBalance)."""
        result = _stock_alerts()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_overview_today_returns_structure(self):
        """get_overview с today возвращает OverviewData с корректной структурой."""
        from apps.dashboard.services.filters import today_local
        today = today_local()
        period = Period(mode='today', date_from=today, date_to=today, errors=[])
        data = get_overview(period)
        self.assertIsInstance(data, OverviewData)
        # Все поля должны быть int (не None)
        self.assertIsNotNone(data.income)
        self.assertIsNotNone(data.orders_created)
        self.assertIsNotNone(data.active_shifts_count)