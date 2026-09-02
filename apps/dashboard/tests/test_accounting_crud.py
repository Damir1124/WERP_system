"""
Тесты CRUD для финансовых сущностей дашборда.

Проверяют:
- доступ к спискам (is_staff → 200, аноним → редирект);
- создание, редактирование и удаление SalaryPeriod, Contract, Installment.

ВНИМАНИЕ: GET-запросы с шаблонами (200 OK) используют RequestFactory
из-за бага Python 3.14 + Django Context.__copy__ (как в test_access.py).
"""
from datetime import date

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse

from apps.accounting.models import SalaryPeriod, Contract, Installment
from apps.clients.models import Client
from apps.workers.models import Worker
from apps.dashboard.views import (
    SalaryPeriodListView, ContractListView, InstallmentListView,
)


class AccountingCrudBaseTests(TestCase):
    """Общая подготовка данных для CRUD-тестов."""

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(
            username='staff', password='pass123', is_staff=True,
        )
        cls.regular_user = User.objects.create_user(
            username='user', password='pass123', is_staff=False,
        )
        cls.worker = Worker.objects.create(
            full_name='Иван Иванов',
            phone='+998901234567',
            worker_type=Worker.WorkerType.COURIER,
            salary_amount=2000000,
        )
        cls.customer = Client.objects.create(
            name='Пётр Петров',
            phone='+998901234568',
        )

    def setUp(self):
        self.factory = RequestFactory()


class SalaryPeriodCrudTests(AccountingCrudBaseTests):
    """CRUD зарплатных периодов."""

    def test_list_staff_200(self):
        request = self.factory.get(reverse('dashboard:salary_period_list'))
        request.user = self.staff_user
        response = SalaryPeriodListView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirects(self):
        response = self.client.get(reverse('dashboard:salary_period_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_create(self):
        self.client.force_login(self.staff_user)
        url = reverse('dashboard:salary_period_create')
        response = self.client.post(url, {
            'worker': self.worker.pk,
            'month': '2026-08-01',
            'salary_amount': 2000000,
            'bonuses': 100000,
            'fines': 0,
            'advances': 500000,
            'paid_salary': 0,
            'salary_date': '2026-08-31',
            'status': SalaryPeriod.PeriodStatus.OPEN,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SalaryPeriod.objects.filter(worker=self.worker).exists())

    def test_update(self):
        period = SalaryPeriod.objects.create(
            worker=self.worker,
            month=date(2026, 8, 1),
            salary_amount=2000000,
            status=SalaryPeriod.PeriodStatus.OPEN,
        )
        self.client.force_login(self.staff_user)
        url = reverse('dashboard:salary_period_update', args=[period.pk])
        response = self.client.post(url, {
            'worker': self.worker.pk,
            'month': '2026-08-01',
            'salary_amount': 2500000,
            'bonuses': 0,
            'fines': 0,
            'advances': 0,
            'paid_salary': 0,
            'salary_date': '2026-08-31',
            'status': SalaryPeriod.PeriodStatus.OPEN,
        })
        self.assertEqual(response.status_code, 302)
        period.refresh_from_db()
        self.assertEqual(period.salary_amount, 2500000)

    def test_delete(self):
        period = SalaryPeriod.objects.create(
            worker=self.worker,
            month=date(2026, 8, 1),
            salary_amount=2000000,
            status=SalaryPeriod.PeriodStatus.OPEN,
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('dashboard:salary_period_delete', args=[period.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SalaryPeriod.objects.filter(pk=period.pk).exists())


class ContractCrudTests(AccountingCrudBaseTests):
    """CRUD контрактов."""

    def test_list_staff_200(self):
        request = self.factory.get(reverse('dashboard:contract_list'))
        request.user = self.staff_user
        response = ContractListView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirects(self):
        response = self.client.get(reverse('dashboard:contract_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_create(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('dashboard:contract_create'), {
            'description': 'Поставка воды',
            'client': self.customer.pk,
            'date': '2026-08-01',
            'contract_type': Contract.ContractType.SELL,
            'amount': 100000,
            'note': 'Тест',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Contract.objects.filter(description='Поставка воды').exists())

    def test_update(self):
        contract = Contract.objects.create(
            description='Старый контракт',
            client=self.customer,
            date=date(2026, 8, 1),
            contract_type=Contract.ContractType.SELL,
            amount=100000,
            note='',
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('dashboard:contract_update', args=[contract.pk]),
            {
                'description': 'Новый контракт',
                'client': self.customer.pk,
                'date': '2026-08-01',
                'contract_type': Contract.ContractType.SELL,
                'amount': 150000,
                'note': 'обновлено',
            },
        )
        self.assertEqual(response.status_code, 302)
        contract.refresh_from_db()
        self.assertEqual(contract.amount, 150000)

    def test_delete(self):
        contract = Contract.objects.create(
            description='Удаляемый контракт',
            client=self.customer,
            date=date(2026, 8, 1),
            contract_type=Contract.ContractType.SELL,
            amount=100000,
            note='',
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('dashboard:contract_delete', args=[contract.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Contract.objects.filter(pk=contract.pk).exists())


class InstallmentCrudTests(AccountingCrudBaseTests):
    """CRUD рассрочек."""

    def test_list_staff_200(self):
        request = self.factory.get(reverse('dashboard:installment_list'))
        request.user = self.staff_user
        response = InstallmentListView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirects(self):
        response = self.client.get(reverse('dashboard:installment_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_create(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('dashboard:installment_create'), {
            'client': self.customer.pk,
            'amount': 500000,
            'paid_amount': 0,
            'due_date': '2026-09-01',
            'status': Installment.InstallmentStatus.ACTIVE,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Installment.objects.filter(client=self.customer).exists())

    def test_update(self):
        installment = Installment.objects.create(
            client=self.customer,
            amount=500000,
            paid_amount=0,
            due_date=date(2026, 9, 1),
            status=Installment.InstallmentStatus.ACTIVE,
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('dashboard:installment_update', args=[installment.pk]),
            {
                'client': self.customer.pk,
                'amount': 600000,
                'paid_amount': 100000,
                'due_date': '2026-09-01',
                'status': Installment.InstallmentStatus.ACTIVE,
            },
        )
        self.assertEqual(response.status_code, 302)
        installment.refresh_from_db()
        self.assertEqual(installment.amount, 600000)

    def test_delete(self):
        installment = Installment.objects.create(
            client=self.customer,
            amount=500000,
            paid_amount=0,
            due_date=date(2026, 9, 1),
            status=Installment.InstallmentStatus.ACTIVE,
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('dashboard:installment_delete', args=[installment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Installment.objects.filter(pk=installment.pk).exists())