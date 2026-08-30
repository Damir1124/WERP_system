from rest_framework import serializers
from apps.accounting.models import (
    Salary, SalaryPeriod, SalaryPayment, Installment, InstallmentItem, PaymentsInstallment,
)
from apps.workers.models import Worker


class SalaryPaymentSerializer(serializers.ModelSerializer):
    """Сериализатор для платежей по зарплате"""
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    period_month = serializers.DateField(source='period.month', read_only=True)

    class Meta:
        model = SalaryPayment
        fields = ['id', 'amount', 'payment_type', 'payment_type_display', 'date', 'note', 'period', 'period_month']
        read_only_fields = ['date', 'period']


class SalaryPeriodSerializer(serializers.ModelSerializer):
    """Сериализатор зарплатного периода (месяца) с итогами."""
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    accrued = serializers.IntegerField(read_only=True)
    paid_total = serializers.IntegerField(read_only=True)
    remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = SalaryPeriod
        fields = [
            'id', 'worker', 'worker_name', 'month', 'salary_amount',
            'bonuses', 'fines', 'advances', 'paid_salary',
            'accrued', 'paid_total', 'remaining',
            'salary_date', 'status', 'status_display',
        ]
        read_only_fields = [
            'salary_amount', 'bonuses', 'fines', 'advances', 'paid_salary',
            'accrued', 'paid_total', 'remaining', 'status',
        ]


class SalarySerializer(serializers.ModelSerializer):
    """Сериализатор для баланса зарплаты сотрудника"""
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    payments = SalaryPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Salary
        fields = ['id', 'worker', 'worker_name', 'balance', 'last_payment', 'payments']
        read_only_fields = ['balance', 'last_payment']


class SalaryDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор зарплаты с расширенной информацией"""
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    payments = SalaryPaymentSerializer(many=True, read_only=True)
    current_period = serializers.SerializerMethodField()
    total_bonuses = serializers.SerializerMethodField()
    total_fines = serializers.SerializerMethodField()
    total_salary = serializers.SerializerMethodField()

    class Meta:
        model = Salary
        fields = [
            'id', 'worker', 'worker_name', 'balance', 'last_payment',
            'current_period', 'total_bonuses', 'total_fines', 'total_salary', 'payments'
        ]
        read_only_fields = ['balance', 'last_payment']

    def get_current_period(self, obj):
        """Текущий зарплатный период с итогами (начислено, выплачено, остаток)."""
        from django.utils import timezone
        now = timezone.now().date()
        month = now.replace(day=1)
        period = SalaryPeriod.objects.filter(worker=obj.worker, month=month).first()
        if period:
            return SalaryPeriodSerializer(period).data
        return None

    def get_total_bonuses(self, obj):
        """Сумма всех бонусов за текущий месяц"""
        from django.utils import timezone
        now = timezone.now().date()
        month_start = now.replace(day=1)
        bonuses = SalaryPayment.objects.filter(
            salary=obj,
            payment_type=SalaryPayment.PaymentType.BONUS,
            date__gte=month_start
        ).aggregate(total=serializers.Sum('amount'))['total']
        return bonuses or 0

    def get_total_fines(self, obj):
        """Сумма всех штрафов за текущий месяц"""
        from django.utils import timezone
        now = timezone.now().date()
        month_start = now.replace(day=1)
        fines = SalaryPayment.objects.filter(
            salary=obj,
            payment_type=SalaryPayment.PaymentType.FINE,
            date__gte=month_start
        ).aggregate(total=serializers.Sum('amount'))['total']
        return fines or 0

    def get_total_salary(self, obj):
        """Сумма всех зарплатных выплат за текущий месяц"""
        from django.utils import timezone
        now = timezone.now().date()
        month_start = now.replace(day=1)
        salary_payments = SalaryPayment.objects.filter(
            salary=obj,
            payment_type=SalaryPayment.PaymentType.SALARY,
            date__gte=month_start
        ).aggregate(total=serializers.Sum('amount'))['total']
        return salary_payments or 0


# =============================================================================
# Рассрочки
# =============================================================================


class InstallmentItemSerializer(serializers.ModelSerializer):
    """Сериализатор позиции рассрочки"""
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = InstallmentItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price_per_unit', 'subtotal']
        read_only_fields = ['subtotal']


class PaymentsInstallmentSerializer(serializers.ModelSerializer):
    """Сериализатор платежа по рассрочке"""

    class Meta:
        model = PaymentsInstallment
        fields = ['id', 'amount', 'payment_date', 'created_at']


class InstallmentSerializer(serializers.ModelSerializer):
    """Сериализатор рассрочки (шапка + позиции + платежи)"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.full_name', read_only=True)
    order_number = serializers.SerializerMethodField()
    items = InstallmentItemSerializer(many=True, read_only=True)
    payments = PaymentsInstallmentSerializer(many=True, read_only=True)
    debt = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Installment
        fields = [
            'id', 'client', 'client_name', 'order', 'order_number',
            'issued_by', 'issued_by_name', 'amount', 'paid_amount', 'debt',
            'due_date', 'status', 'status_display', 'items', 'payments',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['amount', 'paid_amount', 'status', 'created_at', 'updated_at']

    def get_order_number(self, obj):
        """Декоративный номер заказа, если рассрочка по заказу"""
        if obj.order:
            return obj.order.human_number
        return None