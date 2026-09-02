"""
Тесты сервиса фильтра периода (apps/dashboard/services/filters.py).
"""
from datetime import date, timedelta

from django.test import SimpleTestCase

from apps.dashboard.services.filters import (
    parse_period, today_local, _week_boundaries, _month_boundaries,
)


class PeriodTests(SimpleTestCase):
    """Тесты parse_period для всех режимов."""

    def test_today_mode(self):
        """period=today возвращает сегодняшний день."""
        period = parse_period({'period': 'today'})
        today = today_local()
        self.assertEqual(period.mode, 'today')
        self.assertEqual(period.date_from, today)
        self.assertEqual(period.date_to, today)
        self.assertFalse(period.has_errors)

    def test_yesterday_mode(self):
        """period=yesterday возвращает вчерашний день."""
        period = parse_period({'period': 'yesterday'})
        yesterday = today_local() - timedelta(days=1)
        self.assertEqual(period.mode, 'yesterday')
        self.assertEqual(period.date_from, yesterday)
        self.assertEqual(period.date_to, yesterday)
        self.assertFalse(period.has_errors)

    def test_week_mode(self):
        """period=week возвращает понедельник-воскресенье текущей недели."""
        period = parse_period({'period': 'week'})
        monday, sunday = _week_boundaries(today_local())
        self.assertEqual(period.mode, 'week')
        self.assertEqual(period.date_from, monday)
        self.assertEqual(period.date_to, sunday)

    def test_month_mode(self):
        """period=month возвращает первый-последний день месяца."""
        period = parse_period({'period': 'month'})
        first, last = _month_boundaries(today_local())
        self.assertEqual(period.mode, 'month')
        self.assertEqual(period.date_from, first)
        self.assertEqual(period.date_to, last)

    def test_all_mode(self):
        """period=all возвращает date_from=None, date_to=None."""
        period = parse_period({'period': 'all'})
        self.assertEqual(period.mode, 'all')
        self.assertIsNone(period.date_from)
        self.assertIsNone(period.date_to)
        self.assertTrue(period.is_empty)

    def test_custom_valid_dates(self):
        """Ручной диапазон с корректными датами."""
        period = parse_period({
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
        })
        self.assertEqual(period.mode, 'custom')
        self.assertEqual(period.date_from, date(2026, 1, 1))
        self.assertEqual(period.date_to, date(2026, 1, 31))
        self.assertFalse(period.has_errors)

    def test_custom_date_from_gt_date_to(self):
        """date_from > date_to — ошибка, period возвращается с errors."""
        period = parse_period({
            'date_from': '2026-06-01',
            'date_to': '2026-01-01',
        })
        self.assertTrue(period.has_errors)
        self.assertIsNone(period.date_from)
        self.assertIsNone(period.date_to)
        self.assertIn('больше даты «до»', period.errors[0])

    def test_custom_invalid_date_format(self):
        """Неверный формат даты — ошибка."""
        period = parse_period({
            'date_from': '01-01-2026',
            'date_to': '31-01-2026',
        })
        self.assertTrue(period.has_errors)

    def test_default_mode_is_today(self):
        """Без параметра period по умолчанию today."""
        period = parse_period({})
        self.assertEqual(period.mode, 'today')

    def test_week_boundaries_monday(self):
        """_week_boundaries: понедельник — правильный день недели."""
        d = date(2026, 8, 3)  # понедельник
        monday, sunday = _week_boundaries(d)
        self.assertEqual(monday, d)
        self.assertEqual(sunday, date(2026, 8, 9))

    def test_week_boundaries_wednesday(self):
        """_week_boundaries: среда — возвращает понедельник и воскресенье той же недели."""
        d = date(2026, 8, 5)  # среда
        monday, sunday = _week_boundaries(d)
        self.assertEqual(monday, date(2026, 8, 3))
        self.assertEqual(sunday, date(2026, 8, 9))

    def test_month_boundaries(self):
        """_month_boundaries: первый и последний день месяца."""
        d = date(2026, 8, 15)
        first, last = _month_boundaries(d)
        self.assertEqual(first, date(2026, 8, 1))
        self.assertEqual(last, date(2026, 8, 31))

    def test_month_boundaries_december(self):
        """_month_boundaries: декабрь — переход года."""
        d = date(2026, 12, 15)
        first, last = _month_boundaries(d)
        self.assertEqual(first, date(2026, 12, 1))
        self.assertEqual(last, date(2026, 12, 31))