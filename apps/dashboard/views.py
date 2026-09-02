"""
Dashboard — веб-интерфейс диспетчера и владельца.

Все страницы доступны только авторизованным сотрудникам (is_staff=True).
ORM-логика вынесена в сервисный слой apps/dashboard/services/.
"""
import logging

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from apps.dashboard.services.filters import parse_period
from apps.dashboard.services.overview import get_overview
from apps.dashboard.services.orders import get_orders_page
from apps.dashboard.services.products import get_products_page
from apps.products.models import Product

logger = logging.getLogger(__name__)


def _is_staff(user):
    """Проверка доступа: is_staff или суперпользователь."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


class StaffRequiredMixin(View):
    """Mixin: доступ только для is_staff. Редирект на /admin/login/."""

    @method_decorator(user_passes_test(_is_staff, login_url='/admin/login/'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


# ─── Главная страница ────────────────────────────────────────────────────────


class DashboardIndexView(StaffRequiredMixin):
    """GET /dashboard/ — главная сводка."""

    template_name = 'dashboard/index.html'

    def get(self, request):
        period = parse_period(dict(request.GET.items()))

        if period.has_errors:
            context = {
                'period': period,
                'page_title': 'Главная',
                'section': 'overview',
                'kpi': {},
                'active_shifts': [],
                'recent_orders': [],
                'top_products': [],
                'top_couriers': [],
                'stock_alerts': [],
            }
            return render(request, self.template_name, context)

        data = get_overview(period)

        context = {
            'period': period,
            'page_title': 'Главная',
            'section': 'overview',
            'kpi': {
                'income': data.income,
                'consumption': data.consumption,
                'profit': data.profit,
                'card_profit': data.card_profit,
                'cash_deliveries': data.cash_deliveries,
                'orders_created': data.orders_created,
                'orders_delivered': data.orders_delivered,
                'orders_pending': data.orders_pending,
                'orders_cancelled': data.orders_cancelled,
                'units_sold': data.units_sold,
            },
            'active_shifts': data.active_shifts,
            'active_shifts_count': data.active_shifts_count,
            'active_trips_count': data.active_trips_count,
            'unassigned_orders_count': data.unassigned_orders_count,
            'critical_stock_count': data.critical_stock_count,
            'recent_orders': data.recent_orders,
            'top_products': data.top_products,
            'top_couriers': data.top_couriers,
            'stock_alerts': data.stock_alerts,
        }
        return render(request, self.template_name, context)


# ─── Заказы и продажи ────────────────────────────────────────────────────────


class DashboardOrdersView(StaffRequiredMixin):
    """GET /dashboard/orders/ — заказы и продажи."""

    template_name = 'dashboard/orders.html'

    def get(self, request):
        period = parse_period(dict(request.GET.items()))

        filters = {
            'status': request.GET.get('status', ''),
            'payment': request.GET.get('payment', ''),
            'courier': request.GET.get('courier', ''),
            'search': request.GET.get('search', ''),
        }
        page_num = int(request.GET.get('page', 1))

        data = get_orders_page(period, filters, page_num)

        context = {
            'period': period,
            'page_title': 'Заказы и продажи',
            'section': 'orders',
            'kpi': {
                'orders_created': data.orders_created,
                'orders_delivered': data.orders_delivered,
                'orders_cancelled': data.orders_cancelled,
                'orders_pending': data.orders_pending,
                'avg_check': data.avg_check,
                'units_sold': data.units_sold,
            },
            'filters': filters,
            'courier_choices': data.courier_choices,
            'orders_page': data.orders_page,
            'total_count': data.total_count,
        }
        return render(request, self.template_name, context)


# ─── Товары и тара ───────────────────────────────────────────────────────────


class DashboardProductsView(StaffRequiredMixin):
    """GET /dashboard/products/ — товары и тара."""

    template_name = 'dashboard/products.html'

    def get(self, request):
        period = parse_period(dict(request.GET.items()))
        type_filter = request.GET.get('type', '')
        sort_by = request.GET.get('sort', '-sold')

        data = get_products_page(period, type_filter, sort_by)

        context = {
            'period': period,
            'page_title': 'Товары и тара',
            'section': 'products',
            'sales': data.sales,
            'type_filter': data.type_filter,
            'sort_by': data.sort_by,
            'type_choices': Product.TypeProduct.choices,
        }
        return render(request, self.template_name, context)


class DashboardCouriersView(StaffRequiredMixin):
    """GET /dashboard/couriers/ — курьеры, смены и рейсы."""

    template_name = 'dashboard/couriers.html'

    def get(self, request):
        period = parse_period(dict(request.GET.items()))
        courier_filter = request.GET.get('courier', '')
        status_filter = request.GET.get('shift_status', '')

        from apps.dashboard.services.couriers import (
            get_courier_stats, get_shifts_list, get_courier_choices,
        )

        courier_stats = get_courier_stats(period)
        shifts = get_shifts_list(period, courier_filter, status_filter)
        courier_choices = get_courier_choices()

        context = {
            'period': period,
            'page_title': 'Курьеры, смены и рейсы',
            'section': 'couriers',
            'courier_stats': courier_stats,
            'shifts': shifts,
            'courier_choices': courier_choices,
            'courier_filter': courier_filter,
            'status_filter': status_filter,
        }
        return render(request, self.template_name, context)


class ShiftDetailView(StaffRequiredMixin):
    """GET /dashboard/shifts/<id>/ — детали смены."""

    template_name = 'dashboard/shift_detail.html'

    def get(self, request, shift_id):
        from apps.dashboard.services.couriers import get_shift_detail
        from django.http import Http404

        shift = get_shift_detail(shift_id)
        if shift is None:
            raise Http404('Смена не найдена')

        context = {
            'page_title': f'Смена №{shift.id}',
            'section': 'couriers',
            'shift': shift,
        }
        return render(request, self.template_name, context)


class DashboardStockView(StaffRequiredMixin):
    """GET /dashboard/stock/ — склад."""

    template_name = 'dashboard/stock.html'

    def get(self, request):
        from apps.dashboard.services.stock import get_stock_balances, get_recent_movements

        balances = get_stock_balances()
        movements = get_recent_movements()

        context = {
            'page_title': 'Склад',
            'section': 'stock',
            'balances': balances,
            'movements': movements,
        }
        return render(request, self.template_name, context)


class DashboardReportsView(StaffRequiredMixin):
    """GET /dashboard/reports/?date=YYYY-MM-DD — отчёты по сменам за дату.

    Выбирается любая дата; для каждой смены этого дня строится иерархический
    отчёт «смена → рейсы → заказы → позиции».
    """

    template_name = 'dashboard/reports.html'

    def get(self, request):
        from datetime import date as date_cls
        from django.utils import timezone

        raw_date = request.GET.get('date', '')
        selected_date = None
        date_error = ''

        if raw_date:
            try:
                selected_date = date_cls.fromisoformat(raw_date)
            except ValueError:
                date_error = 'Некорректный формат даты. Используйте ГГГГ-ММ-ДД.'
        else:
            selected_date = timezone.localdate()

        reports = []
        if selected_date and not date_error:
            from apps.dashboard.services.reports import get_reports_for_date
            reports = get_reports_for_date(selected_date)

        context = {
            'page_title': 'Отчёты по сменам',
            'section': 'reports',
            'selected_date': selected_date,
            'date_error': date_error,
            'reports': reports,
        }
        return render(request, self.template_name, context)


class DashboardFinanceView(StaffRequiredMixin):
    """GET /dashboard/finance/ — финансы."""

    template_name = 'dashboard/finance.html'

    def get(self, request):
        period = parse_period(dict(request.GET.items()))
        from apps.dashboard.services.finance import get_finance_by_day, get_transactions

        finance_days, totals = get_finance_by_day(period)

        filters = {
            'type': request.GET.get('type', ''),
            'payment': request.GET.get('payment', ''),
            'source': request.GET.get('source', ''),
        }
        page_num = int(request.GET.get('page', 1))
        transactions = get_transactions(period, filters, page_num)

        context = {
            'period': period,
            'page_title': 'Финансы',
            'section': 'finance',
            'finance_days': finance_days,
            'totals': totals,
            'transactions': transactions,
            'filters': filters,
        }
        return render(request, self.template_name, context)


# ─── CRUD: Зарплатные периоды ───────────────────────────────────────────────


class SalaryPeriodListView(StaffRequiredMixin):
    """GET /dashboard/salary-periods/ — список зарплатных периодов."""

    template_name = 'dashboard/salary_period_list.html'

    def get(self, request):
        from apps.dashboard.services.accounting_crud import get_salary_period_list
        periods = get_salary_period_list()
        context = {
            'page_title': 'Зарплаты',
            'section': 'salary_periods',
            'periods': periods,
        }
        return render(request, self.template_name, context)


class SalaryPeriodCreateView(StaffRequiredMixin):
    """GET/POST /dashboard/salary-periods/new/ — создание зарплатного периода."""

    template_name = 'dashboard/salary_period_form.html'

    def get(self, request):
        from apps.dashboard.services.accounting_crud import get_salary_period_form
        form = get_salary_period_form()
        context = {
            'page_title': 'Новый зарплатный период',
            'section': 'salary_periods',
            'form': form,
            'form_title': 'Новый зарплатный период',
            'submit_label': 'Создать',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        from apps.dashboard.services.accounting_crud import get_salary_period_form, save_salary_period
        form = get_salary_period_form(data=request.POST)
        if form.is_valid():
            save_salary_period(form)
            return redirect('dashboard:salary_period_list')
        context = {
            'page_title': 'Новый зарплатный период',
            'section': 'salary_periods',
            'form': form,
            'form_title': 'Новый зарплатный период',
            'submit_url': 'dashboard:salary_period_create',
        }
        return render(request, self.template_name, context)


class SalaryPeriodUpdateView(StaffRequiredMixin):
    """GET/POST /dashboard/salary-periods/<pk>/edit/ — редактирование."""

    template_name = 'dashboard/salary_period_form.html'

    def get(self, request, pk):
        from apps.dashboard.services.accounting_crud import get_salary_period_form
        from django.shortcuts import get_object_or_404
        from apps.accounting.models import SalaryPeriod
        period = get_object_or_404(SalaryPeriod, pk=pk)
        form = get_salary_period_form(instance=period)
        context = {
            'page_title': f'Редактирование периода — {period}',
            'section': 'salary_periods',
            'form': form,
            'form_title': 'Редактирование зарплатного периода',
            'submit_url': 'dashboard:salary_period_update',
            'submit_pk': pk,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        from apps.dashboard.services.accounting_crud import get_salary_period_form, save_salary_period
        from django.shortcuts import get_object_or_404
        from apps.accounting.models import SalaryPeriod
        period = get_object_or_404(SalaryPeriod, pk=pk)
        form = get_salary_period_form(instance=period, data=request.POST)
        if form.is_valid():
            save_salary_period(form)
            return redirect('dashboard:salary_period_list')
        context = {
            'page_title': f'Редактирование периода — {period}',
            'section': 'salary_periods',
            'form': form,
            'form_title': 'Редактирование зарплатного периода',
            'submit_url': 'dashboard:salary_period_update',
            'submit_pk': pk,
        }
        return render(request, self.template_name, context)


class SalaryPeriodDeleteView(StaffRequiredMixin):
    """POST /dashboard/salary-periods/<pk>/delete/ — удаление."""

    def post(self, request, pk):
        from apps.dashboard.services.accounting_crud import delete_salary_period
        delete_salary_period(pk)
        return redirect('dashboard:salary_period_list')


# ─── CRUD: Контракты ────────────────────────────────────────────────────────


class ContractListView(StaffRequiredMixin):
    """GET /dashboard/contracts/ — список контрактов."""

    template_name = 'dashboard/contract_list.html'

    def get(self, request):
        from apps.dashboard.services.accounting_crud import get_contract_list
        contracts = get_contract_list()
        context = {
            'page_title': 'Контракты',
            'section': 'contracts',
            'contracts': contracts,
        }
        return render(request, self.template_name, context)


class ContractCreateView(StaffRequiredMixin):
    """GET/POST /dashboard/contracts/new/ — создание контракта."""

    template_name = 'dashboard/contract_form.html'

    def get(self, request):
        from apps.dashboard.services.accounting_crud import get_contract_form
        form = get_contract_form()
        context = {
            'page_title': 'Новый контракт',
            'section': 'contracts',
            'form': form,
            'form_title': 'Новый контракт',
            'submit_url': 'dashboard:contract_create',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        from apps.dashboard.services.accounting_crud import get_contract_form, save_contract
        form = get_contract_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            save_contract(form)
            return redirect('dashboard:contract_list')
        context = {
            'page_title': 'Новый контракт',
            'section': 'contracts',
            'form': form,
            'form_title': 'Новый контракт',
            'submit_url': 'dashboard:contract_create',
        }
        return render(request, self.template_name, context)


class ContractUpdateView(StaffRequiredMixin):
    """GET/POST /dashboard/contracts/<pk>/edit/ — редактирование."""

    template_name = 'dashboard/contract_form.html'

    def get(self, request, pk):
        from apps.dashboard.services.accounting_crud import get_contract_form
        from django.shortcuts import get_object_or_404
        from apps.accounting.models import Contract
        contract = get_object_or_404(Contract, pk=pk)
        form = get_contract_form(instance=contract)
        context = {
            'page_title': f'Редактирование контракта — {contract}',
            'section': 'contracts',
            'form': form,
            'form_title': 'Редактирование контракта',
            'submit_url': 'dashboard:contract_update',
            'submit_pk': pk,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        from apps.dashboard.services.accounting_crud import get_contract_form, save_contract
        from django.shortcuts import get_object_or_404
        from apps.accounting.models import Contract
        contract = get_object_or_404(Contract, pk=pk)
        form = get_contract_form(instance=contract, data=request.POST, files=request.FILES)
        if form.is_valid():
            save_contract(form)
            return redirect('dashboard:contract_list')
        context = {
            'page_title': f'Редактирование контракта — {contract}',
            'section': 'contracts',
            'form': form,
            'form_title': 'Редактирование контракта',
            'submit_url': 'dashboard:contract_update',
            'submit_pk': pk,
        }
        return render(request, self.template_name, context)


class ContractDeleteView(StaffRequiredMixin):
    """POST /dashboard/contracts/<pk>/delete/ — удаление."""

    def post(self, request, pk):
        from apps.dashboard.services.accounting_crud import delete_contract
        delete_contract(pk)
        return redirect('dashboard:contract_list')


# ─── CRUD: Рассрочки ────────────────────────────────────────────────────────


class InstallmentListView(StaffRequiredMixin):
    """GET /dashboard/installments/ — список рассрочек."""

    template_name = 'dashboard/installment_list.html'

    def get(self, request):
        from apps.dashboard.services.accounting_crud import get_installment_list
        installments = get_installment_list()
        context = {
            'page_title': 'Рассрочки',
            'section': 'installments',
            'installments': installments,
        }
        return render(request, self.template_name, context)


class InstallmentCreateView(StaffRequiredMixin):
    """GET/POST /dashboard/installments/new/ — создание рассрочки."""

    template_name = 'dashboard/installment_form.html'

    def get(self, request):
        from apps.dashboard.services.accounting_crud import get_installment_form
        form = get_installment_form()
        context = {
            'page_title': 'Новая рассрочка',
            'section': 'installments',
            'form': form,
            'form_title': 'Новая рассрочка',
            'submit_url': 'dashboard:installment_create',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        from apps.dashboard.services.accounting_crud import get_installment_form, save_installment
        form = get_installment_form(data=request.POST)
        if form.is_valid():
            save_installment(form)
            return redirect('dashboard:installment_list')
        context = {
            'page_title': 'Новая рассрочка',
            'section': 'installments',
            'form': form,
            'form_title': 'Новая рассрочка',
            'submit_url': 'dashboard:installment_create',
        }
        return render(request, self.template_name, context)


class InstallmentUpdateView(StaffRequiredMixin):
    """GET/POST /dashboard/installments/<pk>/edit/ — редактирование."""

    template_name = 'dashboard/installment_form.html'

    def get(self, request, pk):
        from apps.dashboard.services.accounting_crud import get_installment_form
        from django.shortcuts import get_object_or_404
        from apps.accounting.models import Installment
        installment = get_object_or_404(Installment, pk=pk)
        form = get_installment_form(instance=installment)
        context = {
            'page_title': f'Редактирование рассрочки — {installment}',
            'section': 'installments',
            'form': form,
            'form_title': 'Редактирование рассрочки',
            'submit_url': 'dashboard:installment_update',
            'submit_pk': pk,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        from apps.dashboard.services.accounting_crud import get_installment_form, save_installment
        from django.shortcuts import get_object_or_404
        from apps.accounting.models import Installment
        installment = get_object_or_404(Installment, pk=pk)
        form = get_installment_form(instance=installment, data=request.POST)
        if form.is_valid():
            save_installment(form)
            return redirect('dashboard:installment_list')
        context = {
            'page_title': f'Редактирование рассрочки — {installment}',
            'section': 'installments',
            'form': form,
            'form_title': 'Редактирование рассрочки',
            'submit_url': 'dashboard:installment_update',
            'submit_pk': pk,
        }
        return render(request, self.template_name, context)


class InstallmentDeleteView(StaffRequiredMixin):
    """POST /dashboard/installments/<pk>/delete/ — удаление."""

    def post(self, request, pk):
        from apps.dashboard.services.accounting_crud import delete_installment
        delete_installment(pk)
        return redirect('dashboard:installment_list')