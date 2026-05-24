from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import StockBalance, StockMovement, Garage, InventoryAdjustment


class StockBalanceListView(APIView):
    """Список остатков на складе"""
    def get(self, request):
        stock = StockBalance.objects.select_related('product')[:10]
        data = [{"id": s.id, "product": s.product.name if s.product else None,
                 "quantity": s.quantity, "last_received_date": s.last_received_date} for s in stock]
        return Response(data)


class StockBalanceDetailView(APIView):
    """Детали остатка"""
    def get(self, request, pk):
        try:
            stock = StockBalance.objects.get(pk=pk)
            data = {
                "id": stock.id,
                "product": stock.product.name if stock.product else None,
                "quantity": stock.quantity,
                "last_received_date": stock.last_received_date,
                "last_departure_date": stock.last_departure_date,
            }
            return Response(data)
        except StockBalance.DoesNotExist:
            return Response({"error": "Остаток не найден"}, status=status.HTTP_404_NOT_FOUND)


class StockMovementListView(APIView):
    """Список движений склада"""
    def get(self, request):
        movements = StockMovement.objects.select_related('sold_product')[:10]
        data = [{"id": m.id, "product": m.sold_product.name if m.sold_product else None,
                 "operation_type": m.operation_type, "quantity": m.quantity} for m in movements]
        return Response(data)


class GarageListView(APIView):
    """Список автомобилей"""
    def get(self, request):
        garage = Garage.objects.select_related('courier')[:10]
        data = [{"id": g.id, "vehicle_name": g.vehicle_name, "plate_number": g.plate_number,
                 "courier": g.courier.full_name if g.courier else None} for g in garage]
        return Response(data)


class InventoryAdjustmentListView(APIView):
    """Список корректировок инвентаря"""
    def get(self, request):
        adjustments = InventoryAdjustment.objects.select_related('product', 'adjusted_by')[:10]
        data = [{"id": a.id, "product": a.product.name if a.product else None,
                 "adjustment_type": a.adjustment_type, "quantity": a.quantity,
                 "reason": a.reason} for a in adjustments]
        return Response(data)


class WaybillGenerateView(APIView):
    """Генерация путевого листа"""
    def get(self, request, courier_id):
        # Заглушка для генерации путевого листа
        return Response({"message": "Путевой лист будет сгенерирован для курьера",
                         "courier_id": courier_id})
