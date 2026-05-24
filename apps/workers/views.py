from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Worker
from apps.accounting.models import Salary


class WorkerListView(APIView):
    """Список сотрудников"""
    def get(self, request):
        workers = Worker.objects.all()[:10]
        data = [{"id": w.id, "full_name": w.full_name, "worker_type": w.worker_type,
                 "date_for_payed": w.date_for_payed, "tg_id": w.tg_id} for w in workers]
        return Response(data)


class WorkerDetailView(APIView):
    """Детали сотрудника"""
    def get(self, request, pk):
        try:
            worker = Worker.objects.get(pk=pk)
            data = {
                "id": worker.id,
                "full_name": worker.full_name,
                "worker_type": worker.worker_type,
                "date_for_payed": worker.date_for_payed,
                "tg_id": worker.tg_id,
                "is_admin": worker.is_admin,
            }
            return Response(data)
        except Worker.DoesNotExist:
            return Response({"error": "Сотрудник не найден"}, status=status.HTTP_404_NOT_FOUND)


class WorkerSalaryView(APIView):
    """Зарплата сотрудника"""
    def get(self, request, pk):
        try:
            worker = Worker.objects.get(pk=pk)
            salary, created = Salary.objects.get_or_create(worker=worker)
            data = {
                "worker": worker.full_name,
                "balance": salary.balance,
                "last_payment": salary.last_payment,
            }
            return Response(data)
        except Worker.DoesNotExist:
            return Response({"error": "Сотрудник не найден"}, status=status.HTTP_404_NOT_FOUND)
