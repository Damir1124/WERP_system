from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import CourierShift, CourierTrip, Order


class ShiftListView(APIView):
    """Список смен курьеров"""
    def get(self, request):
        shifts = CourierShift.objects.all()[:10]
        data = [{"id": s.id, "courier": s.courier.full_name if s.courier else None, 
                 "date": s.date, "status": s.status} for s in shifts]
        return Response(data)


class ShiftDetailView(APIView):
    """Детали смены"""
    def get(self, request, pk):
        try:
            shift = CourierShift.objects.get(pk=pk)
            data = {
                "id": shift.id,
                "courier": shift.courier.full_name if shift.courier else None,
                "date": shift.date,
                "status": shift.status,
                "cash_total": shift.cash_total,
                "card_total": shift.card_total,
            }
            return Response(data)
        except CourierShift.DoesNotExist:
            return Response({"error": "Смена не найдена"}, status=status.HTTP_404_NOT_FOUND)


class ShiftCloseView(APIView):
    """Закрытие смены"""
    def post(self, request, pk):
        try:
            shift = CourierShift.objects.get(pk=pk)
            shift.close()
            return Response({"message": "Смена закрыта", "status": shift.status})
        except CourierShift.DoesNotExist:
            return Response({"error": "Смена не найдена"}, status=status.HTTP_404_NOT_FOUND)


class TripListView(APIView):
    """Список рейсов"""
    def get(self, request):
        trips = CourierTrip.objects.all()[:10]
        data = [{"id": t.id, "shift": t.shift.id if t.shift else None,
                 "status": t.status, "full_loaded": t.full_loaded} for t in trips]
        return Response(data)


class TripDetailView(APIView):
    """Детали рейса"""
    def get(self, request, pk):
        try:
            trip = CourierTrip.objects.get(pk=pk)
            data = {
                "id": trip.id,
                "shift": trip.shift.id if trip.shift else None,
                "status": trip.status,
                "full_loaded": trip.full_loaded,
                "full_returned": trip.full_returned,
            }
            return Response(data)
        except CourierTrip.DoesNotExist:
            return Response({"error": "Рейс не найдена"}, status=status.HTTP_404_NOT_FOUND)


class TripSummaryView(APIView):
    """Сводка по рейсу"""
    def get(self, request, pk):
        try:
            trip = CourierTrip.objects.get(pk=pk)
            summary = trip.get_trip_summary()
            return Response(summary)
        except CourierTrip.DoesNotExist:
            return Response({"error": "Рейс не найдена"}, status=status.HTTP_404_NOT_FOUND)


class TripCloseView(APIView):
    """Закрытие рейса"""
    def post(self, request, pk):
        try:
            trip = CourierTrip.objects.get(pk=pk)
            trip.status = 'DONE'
            trip.finished_at = timezone.now()
            trip.save()
            return Response({"message": "Рейс закрыт", "status": trip.status})
        except CourierTrip.DoesNotExist:
            return Response({"error": "Рейс не найдена"}, status=status.HTTP_404_NOT_FOUND)


class OrderListView(APIView):
    """Список заказов"""
    def get(self, request):
        orders = Order.objects.all()[:10]
        data = [{"id": o.id, "client": o.client.name if o.client else None,
                 "status": o.status, "payment_type": o.payment_type} for o in orders]
        return Response(data)


class OrderDetailView(APIView):
    """Детали заказа"""
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            data = {
                "id": order.id,
                "client": order.client.name if order.client else None,
                "status": order.status,
                "payment_type": order.payment_type,
                "total_price": order.get_total_price(),
            }
            return Response(data)
        except Order.DoesNotExist:
            return Response({"error": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)


class OrderDeliverView(APIView):
    """Подтверждение доставки заказа"""
    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            order.status = 'DELIVERED'
            order.delivered_at = timezone.now()
            order.save()
            return Response({"message": "Заказ доставлен", "status": order.status})
        except Order.DoesNotExist:
            return Response({"error": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)
