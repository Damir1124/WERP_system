from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.bot_bridge.serializers import (
    DeliveryJournalSerializer,
    DeliveryConfirmationSerializer,
    QuantityUpdateSerializer,
    ProductSerializer,
    ClientSerializer,
    WorkerSerializer,
)
from apps.bot_bridge.permissions import IsCourier
from apps.logistics.models import DeliveryJournal, DeliveryJournalProducts
from apps.products.models import Product
from apps.clients.models import Client
from apps.workers.models import Worker


class CourierDeliveryListView(APIView):
    """Получение списка доставок для курьера"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        today = timezone.now().date()
        
        # Получаем доставки на сегодня и будущие даты
        deliveries = DeliveryJournal.objects.filter(
            courier=courier,
            date__gte=today
        ).order_by('date')
        
        serializer = DeliveryJournalSerializer(deliveries, many=True)
        return Response(serializer.data)


class DeliveryConfirmationView(APIView):
    """Подтверждение доставки курьером"""
    permission_classes = [IsCourier]

    def post(self, request):
        serializer = DeliveryConfirmationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        delivery_journal_id = data['delivery_journal_id']
        confirmed = data['confirmed']
        actual_quantity = data.get('actual_quantity')
        note = data.get('note', '')

        delivery = get_object_or_404(
            DeliveryJournal, 
            id=delivery_journal_id,
            courier=request.courier
        )

        if confirmed:
            # Если указано фактическое количество, обновляем строки продуктов
            if actual_quantity is not None:
                # Логика обновления количества (упрощённая)
                # В реальности нужно обновлять конкретную строку продукта
                pass
            
            # Помечаем доставку как подтверждённую
            # Можно добавить поле confirmed в модель DeliveryJournal
            # delivery.confirmed = True
            # delivery.save()
            
            return Response({
                'status': 'confirmed',
                'message': f'Доставка #{delivery.id} подтверждена',
                'delivery_id': delivery.id
            })
        else:
            # Отмена доставки (например, клиент отказался)
            return Response({
                'status': 'cancelled',
                'message': f'Доставка #{delivery.id} отменена',
                'delivery_id': delivery.id
            })


class UpdateQuantityView(APIView):
    """Изменение количества продукта в доставке"""
    permission_classes = [IsCourier]

    def post(self, request):
        serializer = QuantityUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        product_line_id = data['product_line_id']
        new_quantity = data['new_quantity']

        # Проверяем, что строка принадлежит доставке курьера
        product_line = get_object_or_404(DeliveryJournalProducts, id=product_line_id)
        delivery = product_line.delivery_journal
        
        if delivery.courier != request.courier:
            return Response(
                {'error': 'Недостаточно прав для изменения этой доставки'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Обновляем количество
        product_line.quantity = new_quantity
        product_line.save()  # save() автоматически пересчитает цену и обновит delivery_journal

        return Response({
            'status': 'updated',
            'product_line_id': product_line.id,
            'new_quantity': new_quantity,
            'new_price': product_line.price
        })


class ProductListView(APIView):
    """Получение списка продуктов (каталог)"""
    permission_classes = [IsCourier]

    def get(self, request):
        products = Product.objects.all().order_by('type_product', 'name')
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ClientInfoView(APIView):
    """Получение информации о клиенте по адресу или телефону"""
    permission_classes = [IsCourier]

    def get(self, request):
        phone = request.query_params.get('phone', '')
        address = request.query_params.get('address', '')
        
        clients = Client.objects.all()
        if phone:
            clients = clients.filter(phone__icontains=phone)
        if address:
            clients = clients.filter(address__icontains=address)
        
        clients = clients[:10]  # Ограничиваем результаты
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data)


class CourierProfileView(APIView):
    """Получение профиля курьера"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        serializer = WorkerSerializer(courier)
        return Response(serializer.data)


class TodayDeliveriesView(APIView):
    """Получение доставок на сегодня"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        today = timezone.now().date()
        
        deliveries = DeliveryJournal.objects.filter(
            courier=courier,
            date=today
        ).order_by('-id')
        
        serializer = DeliveryJournalSerializer(deliveries, many=True)
        return Response(serializer.data)


class MarkAsDeliveredView(APIView):
    """Пометить доставку как выполненную (альтернатива подтверждению)"""
    permission_classes = [IsCourier]

    def post(self, request, delivery_id):
        delivery = get_object_or_404(
            DeliveryJournal, 
            id=delivery_id,
            courier=request.courier
        )
        
        # Здесь можно добавить логику пометки доставки как выполненной
        # Например, установить поле delivered = True
        # delivery.delivered = True
        # delivery.delivered_at = timezone.now()
        # delivery.save()
        
        return Response({
            'status': 'delivered',
            'message': f'Доставка #{delivery.id} помечена как выполненная',
            'delivery_id': delivery.id
        })