from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Client


class ClientListView(APIView):
    """Список клиентов"""
    def get(self, request):
        clients = Client.objects.all()[:10]
        data = [{"id": c.id, "name": c.name, "phone": c.phone,
                 "address": c.address, "balans": c.balans} for c in clients]
        return Response(data)


class ClientDetailView(APIView):
    """Детали клиента"""
    def get(self, request, pk):
        try:
            client = Client.objects.get(pk=pk)
            data = {
                "id": client.id,
                "name": client.name,
                "phone": client.phone,
                "address": client.address,
                "balans": client.balans,
                "latitude": client.latitude,
                "longitude": client.longitude,
                "tg_id": client.tg_id,
            }
            return Response(data)
        except Client.DoesNotExist:
            return Response({"error": "Клиент не найден"}, status=status.HTTP_404_NOT_FOUND)


class ClientOrderHistoryView(APIView):
    """История заказов клиента"""
    def get(self, request, pk):
        try:
            client = Client.objects.get(pk=pk)
            # Используем связанные заказы через ForeignKey
            orders = client.order_set.all()[:10]
            data = [{"id": o.id, "status": o.status, "payment_type": o.payment_type,
                     "created_at": o.created_at} for o in orders]
            return Response({"client": client.name, "orders": data})
        except Client.DoesNotExist:
            return Response({"error": "Клиент не найден"}, status=status.HTTP_404_NOT_FOUND)
