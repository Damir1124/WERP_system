"""
Формы CRUD для финансовых сущностей дашборда.

Используются вьюхами apps/dashboard/views.py через сервисный слой.
Все поля получают Bootstrap-класс form-control для единообразного вида.
"""
from django import forms

from apps.accounting.models import SalaryPeriod, Contract, Installment


class _BaseForm(forms.ModelForm):
    """Базовый класс: добавляет Bootstrap-классы всем полям."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get('class', '')
            if 'form-control' not in css and 'form-select' not in css:
                if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'


class SalaryPeriodForm(_BaseForm):
    """Форма зарплатного периода."""

    class Meta:
        model = SalaryPeriod
        fields = [
            'worker', 'month', 'salary_amount', 'bonuses', 'fines',
            'advances', 'paid_salary', 'salary_date', 'status',
        ]
        widgets = {
            'month': forms.DateInput(attrs={'type': 'date'}),
            'salary_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ContractForm(_BaseForm):
    """Форма контракта."""

    class Meta:
        model = Contract
        fields = [
            'description', 'client', 'date', 'file',
            'contract_type', 'amount', 'note',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class InstallmentForm(_BaseForm):
    """Форма рассрочки."""

    class Meta:
        model = Installment
        fields = [
            'client', 'order', 'issued_by', 'amount',
            'paid_amount', 'due_date', 'status',
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }