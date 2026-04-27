from rest_framework import serializers
from apps.accounting.models import Salary, SalaryPayment
from apps.workers.models import Worker


class SalaryPaymentSerializer(serializers.ModelSerializer):
    """Сериализатор для платежей по зарплате"""
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    
    class Meta:
        model = SalaryPayment
        fields = ['id', 'amount', 'payment_type', 'payment_type_display', 'date', 'note']
        read_only_fields = ['date']


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
    total_bonuses = serializers.SerializerMethodField()
    total_fines = serializers.SerializerMethodField()
    total_salary = serializers.SerializerMethodField()
    
    class Meta:
        model = Salary
        fields = [
            'id', 'worker', 'worker_name', 'balance', 'last_payment',
            'total_bonuses', 'total_fines', 'total_salary', 'payments'
        ]
        read_only_fields = ['balance', 'last_payment']
    
    def get_total_bonuses(self, obj):
        """Сумма всех бонусов за последний месяц"""
        from django.utils import timezone
        from datetime import timedelta
        
        month_ago = timezone.now() - timedelta(days=30)
        bonuses = SalaryPayment.objects.filter(
            salary=obj,
            payment_type=SalaryPayment.PaymentType.BONUS,
            date__gte=month_ago
        ).aggregate(total=serializers.Sum('amount'))['total']
        return bonuses or 0
    
    def get_total_fines(self, obj):
        """Сумма всех штрафов за последний месяц"""
        from django.utils import timezone
        from datetime import timedelta
        
        month_ago = timezone.now() - timedelta(days=30)
        fines = SalaryPayment.objects.filter(
            salary=obj,
            payment_type=SalaryPayment.PaymentType.FINE,
            date__gte=month_ago
        ).aggregate(total=serializers.Sum('amount'))['total']
        return fines or 0
    
    def get_total_salary(self, obj):
        """Сумма всех зарплатных выплат за последний месяц"""
        from django.utils import timezone
        from datetime import timedelta
        
        month_ago = timezone.now() - timedelta(days=30)
        salary_payments = SalaryPayment.objects.filter(
            salary=obj,
            payment_type=SalaryPayment.PaymentType.SALARY,
            date__gte=month_ago
        ).aggregate(total=serializers.Sum('amount'))['total']
        return salary_payments or 0