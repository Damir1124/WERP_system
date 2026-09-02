from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounting.models import Salary, SalaryPeriod, SalaryPayment, Installment, PaymentsInstallment
from apps.accounting.serializers import (
    SalaryDetailSerializer, SalaryPeriodSerializer, SalaryPaymentSerializer,
    InstallmentSerializer, PaymentsInstallmentSerializer,
)
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

    Отвечает на главные вопросы владельца:
    - сколько начислено (оклад + бонусы - штрафы);
    - сколько уже выплачено (авансы + зарплата);
    - сколько осталось к выдаче;
    - в какую дату зарплата.
    """
    permission_classes = [IsCourier]

    def get(self, request):
        """Получить сводку по зарплате за текущий месяц"""
        courier = request.courier
        salary, _ = Salary.objects.get_or_create(worker=courier)

        from django.utils import timezone
        now = timezone.now().date()
        month = now.replace(day=1)

        # Получаем или создаём текущий зарплатный период
        period, _ = SalaryPeriod.objects.get_or_create(
            worker=courier,
            month=month,
            defaults={'salary_amount': courier.salary_amount or 0},
        )

        return Response({
            'worker_name': courier.full_name,
            'current_balance': salary.balance,
            'current_period': SalaryPeriodSerializer(period).data,
            'last_payment_date': salary.last_payment,
        })


class SalaryPeriodsListView(APIView):
    """
    API endpoint для получения списка зарплатных периодов курьера.
    """
    permission_classes = [IsCourier]

    def get(self, request):
        """Получить все зарплатные периоды курьера (новые сначала)"""
        courier = request.courier
        periods = SalaryPeriod.objects.filter(worker=courier).order_by('-month')
        serializer = SalaryPeriodSerializer(periods, many=True)
        return Response(serializer.data)


# =============================================================================
# Рассрочки
# =============================================================================


class InstallmentListView(APIView):
    """Список рассрочек клиента"""

    def get(self, request):
        client_id = request.query_params.get('client')
        if not client_id:
            return Response(
                {'error': 'Параметр client обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        installments = Installment.objects.filter(client_id=client_id).order_by('-created_at')
        serializer = InstallmentSerializer(installments, many=True)
        return Response(serializer.data)


class InstallmentDetailView(APIView):
    """Детальная информация о рассрочке"""

    def get(self, request, pk):
        installment = get_object_or_404(Installment, pk=pk)
        serializer = InstallmentSerializer(installment)
        return Response(serializer.data)


class InstallmentPaymentCreateView(APIView):
    """Создание платежа по рассрочке"""

    def post(self, request, pk):
        installment = get_object_or_404(Installment, pk=pk)
        amount = request.data.get('amount')
        payment_date = request.data.get('payment_date')

        if not amount or int(amount) <= 0:
            return Response(
                {'error': 'Сумма платежа обязательна и должна быть больше 0'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = PaymentsInstallment.objects.create(
            installment=installment,
            amount=int(amount),
            payment_date=payment_date or timezone.now().date(),
        )
        serializer = PaymentsInstallmentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
