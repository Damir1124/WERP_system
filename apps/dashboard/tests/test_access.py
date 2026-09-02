"""
Тесты доступа к Dashboard.

Проверяют, что:
- неавторизованные пользователи перенаправляются на /admin/login/
- is_staff=True имеют доступ
- is_staff=False получают 302 редирект

ВНИМАНИЕ: Тесты с шаблонами (200 OK) используют RequestFactory вместо
клиента из-за бага Python 3.14 + Django Context.__copy__.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse

from apps.dashboard.views import (
    DashboardIndexView, DashboardOrdersView, DashboardProductsView,
    DashboardCouriersView, DashboardStockView, DashboardFinanceView,
)


class DashboardAccessTests(TestCase):
    """Тесты авторизации для /dashboard/."""

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(
            username='staff', password='pass123', is_staff=True,
        )
        cls.regular_user = User.objects.create_user(
            username='user', password='pass123', is_staff=False,
        )
        cls.superuser = User.objects.create_superuser(
            username='admin', password='pass123',
        )

    def setUp(self):
        self.factory = RequestFactory()

    def test_anonymous_redirects_to_login(self):
        """Неавторизованный пользователь → редирект на /admin/login/."""
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_staff_gets_200(self):
        """is_staff=True → 200 OK."""
        request = self.factory.get(reverse('dashboard:index'))
        request.user = self.staff_user
        response = DashboardIndexView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_superuser_gets_200(self):
        """Суперпользователь → 200 OK."""
        request = self.factory.get(reverse('dashboard:index'))
        request.user = self.superuser
        response = DashboardIndexView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirects(self):
        """is_staff=False → редирект на /admin/login/."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_orders_page_staff(self):
        """/dashboard/orders/ доступен для is_staff."""
        request = self.factory.get(reverse('dashboard:orders'))
        request.user = self.staff_user
        response = DashboardOrdersView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_products_page_staff(self):
        """/dashboard/products/ доступен для is_staff."""
        request = self.factory.get(reverse('dashboard:products'))
        request.user = self.staff_user
        response = DashboardProductsView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_couriers_page_staff(self):
        """/dashboard/couriers/ доступен для is_staff."""
        request = self.factory.get(reverse('dashboard:couriers'))
        request.user = self.staff_user
        response = DashboardCouriersView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_stock_page_staff(self):
        """/dashboard/stock/ доступен для is_staff."""
        request = self.factory.get(reverse('dashboard:stock'))
        request.user = self.staff_user
        response = DashboardStockView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_finance_page_staff(self):
        """/dashboard/finance/ доступен для is_staff."""
        request = self.factory.get(reverse('dashboard:finance'))
        request.user = self.staff_user
        response = DashboardFinanceView.as_view()(request)
        self.assertEqual(response.status_code, 200)