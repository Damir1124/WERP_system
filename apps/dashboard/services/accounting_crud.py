"""
Сервисный слой CRUD для финансовых сущностей дашборда.

Содержит функции для работы с моделями:
- SalaryPeriod (зарплатные периоды);
- Contract (контракты);
- Installment (рассрочки).

ORM-логика вынесена сюда, чтобы вьюхи оставались тонкими.
"""
import logging

from django.shortcuts import get_object_or_404

from apps.accounting.models import SalaryPeriod, Contract, Installment
from apps.dashboard.forms import SalaryPeriodForm, ContractForm, InstallmentForm

logger = logging.getLogger(__name__)


# ─── Зарплатные периоды ─────────────────────────────────────────────────────


def get_salary_period_list():
    """Список зарплатных периодов (новые сначала)."""
    return SalaryPeriod.objects.select_related('worker').order_by('-month', '-id')


def get_salary_period_form(instance=None, data=None, files=None):
    """Форма зарплатного периода (создание или редактирование)."""
    return SalaryPeriodForm(data, files, instance=instance)


def save_salary_period(form):
    """Сохраняет зарплатный период из формы."""
    return form.save()


def delete_salary_period(pk):
    """Удаляет зарплатный период по pk."""
    obj = get_object_or_404(SalaryPeriod, pk=pk)
    obj.delete()


# ─── Контракты ──────────────────────────────────────────────────────────────


def get_contract_list():
    """Список контрактов (новые сначала)."""
    return Contract.objects.select_related('client').order_by('-date', '-id')


def get_contract_form(instance=None, data=None, files=None):
    """Форма контракта (создание или редактирование)."""
    return ContractForm(data, files, instance=instance)


def save_contract(form):
    """Сохраняет контракт из формы."""
    return form.save()


def delete_contract(pk):
    """Удаляет контракт по pk."""
    obj = get_object_or_404(Contract, pk=pk)
    obj.delete()


# ─── Рассрочки ──────────────────────────────────────────────────────────────


def get_installment_list():
    """Список рассрочек (новые сначала)."""
    return Installment.objects.select_related('client', 'issued_by').order_by('-created_at', '-id')


def get_installment_form(instance=None, data=None, files=None):
    """Форма рассрочки (создание или редактирование)."""
    return InstallmentForm(data, files, instance=instance)


def save_installment(form):
    """Сохраняет рассрочку из формы."""
    return form.save()


def delete_installment(pk):
    """Удаляет рассрочку по pk."""
    obj = get_object_or_404(Installment, pk=pk)
    obj.delete()