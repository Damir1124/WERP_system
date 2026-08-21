from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.products.models import Product
from .models import (
    Garage,
    WarehouseProduct, WarehouseStockBalance, WarehouseStockMovement,
    WarehouseInventoryAdjustment, ProductWarehouseMapping,
)


class GarageListView(APIView):
    """Список автомобилей"""
    def get(self, request):
        garage = Garage.objects.select_related('courier')[:10]
        data = [{"id": g.id, "vehicle_name": g.vehicle_name, "plate_number": g.plate_number,
                 "courier": g.courier.full_name if g.courier else None} for g in garage]
        return Response(data)


class WaybillGenerateView(APIView):
    """Генерация путевого листа"""
    def get(self, request, courier_id):
        # Заглушка для генерации путевого листа
        return Response({"message": "Путевой лист будет сгенерирован для курьера",
                         "courier_id": courier_id})


# ═══════════════════════════════════════════════════════════════════════════════
#  API АВТОНОМНОГО КОНТУРА СКЛАДСКИХ ПРОДУКТОВ
# ═══════════════════════════════════════════════════════════════════════════════


class WarehouseProductListView(APIView):
    """Список и создание складских продуктов"""
    def get(self, request):
        products = WarehouseProduct.objects.select_related('balance').all()
        data = [{
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "unit": p.unit,
            "is_active": p.is_active,
            "quantity": p.balance.quantity if hasattr(p, 'balance') else 0,
        } for p in products]
        return Response(data)

    def post(self, request):
        name = request.data.get('name')
        if not name:
            return Response({"error": "Поле name обязательно"}, status=status.HTTP_400_BAD_REQUEST)
        product = WarehouseProduct.objects.create(
            name=name,
            sku=request.data.get('sku', ''),
            unit=request.data.get('unit', 'шт'),
            is_active=request.data.get('is_active', True),
        )
        return Response({"id": product.id, "name": product.name}, status=status.HTTP_201_CREATED)


class WarehouseProductDetailView(APIView):
    """Детали, изменение и удаление складского продукта"""
    def get_object(self, pk):
        try:
            return WarehouseProduct.objects.get(pk=pk)
        except WarehouseProduct.DoesNotExist:
            return None

    def get(self, request, pk):
        product = self.get_object(pk)
        if not product:
            return Response({"error": "Складской продукт не найден"}, status=status.HTTP_404_NOT_FOUND)
        balance = getattr(product, 'balance', None)
        data = {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "unit": product.unit,
            "is_active": product.is_active,
            "quantity": balance.quantity if balance else 0,
            "last_received_date": balance.last_received_date if balance else None,
            "last_departure_date": balance.last_departure_date if balance else None,
        }
        return Response(data)

    def put(self, request, pk):
        product = self.get_object(pk)
        if not product:
            return Response({"error": "Складской продукт не найден"}, status=status.HTTP_404_NOT_FOUND)
        product.name = request.data.get('name', product.name)
        product.sku = request.data.get('sku', product.sku)
        product.unit = request.data.get('unit', product.unit)
        product.is_active = request.data.get('is_active', product.is_active)
        product.save()
        return Response({"id": product.id, "name": product.name})

    def delete(self, request, pk):
        product = self.get_object(pk)
        if not product:
            return Response({"error": "Складской продукт не найден"}, status=status.HTTP_404_NOT_FOUND)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WarehouseStockListView(APIView):
    """Список остатков складских продуктов"""
    def get(self, request):
        stock = WarehouseStockBalance.objects.select_related('warehouse_product').all()
        data = [{
            "id": s.id,
            "warehouse_product": s.warehouse_product.name,
            "quantity": s.quantity,
            "last_received_date": s.last_received_date,
            "last_departure_date": s.last_departure_date,
        } for s in stock]
        return Response(data)


class WarehouseMovementListView(APIView):
    """Журнал движений + создание прихода/расхода"""
    def get(self, request):
        movements = WarehouseStockMovement.objects.select_related('warehouse_product').all()
        data = [{
            "id": m.id,
            "warehouse_product": m.warehouse_product.name,
            "operation_type": m.operation_type,
            "quantity": m.quantity,
            "note": m.note,
            "created_at": m.created_at,
        } for m in movements]
        return Response(data)

    def post(self, request):
        warehouse_product_id = request.data.get('warehouse_product')
        operation_type = request.data.get('operation_type')
        quantity = request.data.get('quantity')

        if not warehouse_product_id or not operation_type or not quantity:
            return Response({"error": "Поля warehouse_product, operation_type, quantity обязательны"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            wp = WarehouseProduct.objects.get(pk=warehouse_product_id)
        except WarehouseProduct.DoesNotExist:
            return Response({"error": "Складской продукт не найден"}, status=status.HTTP_404_NOT_FOUND)

        if operation_type not in [WarehouseStockMovement.OperationType.INCOME,
                                  WarehouseStockMovement.OperationType.EXPENSE]:
            return Response({"error": "operation_type должен быть IN или OUT"},
                            status=status.HTTP_400_BAD_REQUEST)

        movement = WarehouseStockMovement.objects.create(
            warehouse_product=wp,
            operation_type=operation_type,
            quantity=int(quantity),
            note=request.data.get('note', ''),
        )
        return Response({"id": movement.id, "operation_type": movement.operation_type},
                        status=status.HTTP_201_CREATED)


class WarehouseAdjustmentListView(APIView):
    """Список и создание корректировок складских продуктов"""
    def get(self, request):
        adjustments = WarehouseInventoryAdjustment.objects.select_related('warehouse_product', 'adjusted_by').all()
        data = [{
            "id": a.id,
            "warehouse_product": a.warehouse_product.name,
            "adjustment_type": a.adjustment_type,
            "quantity": a.quantity,
            "reason": a.reason,
            "adjusted_by": a.adjusted_by.full_name if a.adjusted_by else None,
            "created_at": a.created_at,
        } for a in adjustments]
        return Response(data)

    def post(self, request):
        warehouse_product_id = request.data.get('warehouse_product')
        adjustment_type = request.data.get('adjustment_type')
        quantity = request.data.get('quantity')
        reason = request.data.get('reason')

        if not warehouse_product_id or not adjustment_type or not quantity or not reason:
            return Response({"error": "Поля warehouse_product, adjustment_type, quantity, reason обязательны"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            wp = WarehouseProduct.objects.get(pk=warehouse_product_id)
        except WarehouseProduct.DoesNotExist:
            return Response({"error": "Складской продукт не найден"}, status=status.HTTP_404_NOT_FOUND)

        if adjustment_type not in [WarehouseInventoryAdjustment.AdjustmentType.INCREASE,
                                   WarehouseInventoryAdjustment.AdjustmentType.DECREASE,
                                   WarehouseInventoryAdjustment.AdjustmentType.SET]:
            return Response({"error": "adjustment_type должен быть INC, DEC или SET"},
                            status=status.HTTP_400_BAD_REQUEST)

        adjustment = WarehouseInventoryAdjustment.objects.create(
            warehouse_product=wp,
            adjustment_type=adjustment_type,
            quantity=int(quantity),
            reason=reason,
            note=request.data.get('note', ''),
        )
        return Response({"id": adjustment.id, "adjustment_type": adjustment.adjustment_type},
                        status=status.HTTP_201_CREATED)


class WarehouseMappingListView(APIView):
    """Список и создание связей Product ↔ WarehouseProduct"""
    def get(self, request):
        mappings = ProductWarehouseMapping.objects.select_related('product', 'warehouse_product').all()
        data = [{
            "id": m.id,
            "product": m.product.name,
            "product_id": m.product.id,
            "warehouse_product": m.warehouse_product.name,
            "warehouse_product_id": m.warehouse_product.id,
            "coefficient": m.coefficient,
        } for m in mappings]
        return Response(data)

    def post(self, request):
        product_id = request.data.get('product')
        warehouse_product_id = request.data.get('warehouse_product')
        coefficient = request.data.get('coefficient', 1)

        if not product_id or not warehouse_product_id:
            return Response({"error": "Поля product и warehouse_product обязательны"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
            wp = WarehouseProduct.objects.get(pk=warehouse_product_id)
        except (Product.DoesNotExist, WarehouseProduct.DoesNotExist):
            return Response({"error": "Продукт или складской продукт не найден"},
                            status=status.HTTP_404_NOT_FOUND)

        mapping, created = ProductWarehouseMapping.objects.get_or_create(
            product=product,
            warehouse_product=wp,
            defaults={'coefficient': int(coefficient)},
        )
        return Response({"id": mapping.id, "created": created}, status=status.HTTP_201_CREATED)
