from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.accounting.models import Salary, SalaryPayment
from apps.accounting.serializers import SalaryDetailSerializer, SalaryPaymentSerializer
from apps.bot_bridge.permissions import IsCourier


class SalaryDetailView(APIView):
    """
    API endpoint для получения курьером информации о своей зарплате,
    бонусах и штрафах.
    """
    permission_classes = [IsCourier]
    
    def get(self, request):
        """Получить детальную информацию о зарплате курьера"""
        courier = request.courier
        
        # Получаем или создаем запись Salary для курьера
        salary, created = Salary.objects.get_or_create(worker=courier)
        
        serializer = SalaryDetailSerializer(salary)
        return Response(serializer.data)


class SalaryPaymentsListView(APIView):
    """
    API endpoint для получения списка платежей по зарплате курьера.
    """
    permission_classes = [IsCourier]
    
    def get(self, request):
        """Получить список всех платежей по зарплате"""
        courier = request.courier
        salary = get_object_or_404(Salary, worker=courier)
        
        # Получаем платежи, отсортированные по дате (новые сначала)
        payments = SalaryPayment.objects.filter(salary=salary).order_by('-date')
        
        serializer = SalaryPaymentSerializer(payments, many=True)
        return Response(serializer.data)


class RecentBonusesView(APIView):
    """
    API endpoint для получения последних бонусов курьера.
    """
    permission_classes = [IsCourier]
    
    def get(self, request):
        """Получить последние бонусы (за последние 30 дней)"""
        courier = request.courier
        salary = get_object_or_404(Salary, worker=courier)
        
        from django.utils import timezone
        from datetime import timedelta
        
        month_ago = timezone.now() - timedelta(days=30)
        
        bonuses = SalaryPayment.objects.filter(
            salary=salary,
            payment_type=SalaryPayment.PaymentType.BONUS,
            date__gte=month_ago
        ).order_by('-date')
        
        serializer = SalaryPaymentSerializer(bonuses, many=True)
        return Response({
            'total_bonuses': sum(b.amount for b in bonuses),
            'bonuses': serializer.data
        })


class RecentFinesView(APIView):
    """
    API endpoint для получения последних штрафов курьера.
    """
    permission_classes = [IsCourier]
    
    def get(self, request):
        """Получить последние штрафы (за последние 30 дней)"""
        courier = request.courier
        salary = get_object_or_404(Salary, worker=courier)
        
        from django.utils import timezone
        from datetime import timedelta
        
        month_ago = timezone.now() - timedelta(days=30)
        
        fines = SalaryPayment.objects.filter(
            salary=salary,
            payment_type=SalaryPayment.PaymentType.FINE,
            date__gte=month_ago
        ).order_by('-date')
        
        serializer = SalaryPaymentSerializer(fines, many=True)
        return Response({
            'total_fines': sum(f.amount for f in fines),
            'fines': serializer.data
        })


class SalarySummaryView(APIView):
    """
    API endpoint для получения сводки по зарплате за текущий месяц.
    """
    permission_classes = [IsCourier]
    
    def get(self, request):
        """Получить сводку по зарплате за текущий месяц"""
        courier = request.courier
        salary = get_object_or_404(Salary, worker=courier)
        
        from django.utils import timezone
        from datetime import datetime
        
        now = timezone.now()
        first_day_of_month = datetime(now.year, now.month, 1)
        
        # Получаем платежи за текущий месяц
        payments = SalaryPayment.objects.filter(
            salary=salary,
            date__gte=first_day_of_month
        )
        
        # Рассчитываем суммы по типам
        total_bonuses = sum(p.amount for p in payments if p.payment_type == SalaryPayment.PaymentType.BONUS)
        total_fines = sum(p.amount for p in payments if p.payment_type == SalaryPayment.PaymentType.FINE)
        total_salary = sum(p.amount for p in payments if p.payment_type == SalaryPayment.PaymentType.SALARY)
        
        return Response({
            'current_balance': salary.balance,
            'monthly_summary': {
                'bonuses': total_bonuses,
                'fines': total_fines,
                'salary_payments': total_salary,
                'net_income': total_salary + total_bonuses - total_fines
            },
            'last_payment_date': salary.last_payment,
            'worker_name': courier.full_name
        })
