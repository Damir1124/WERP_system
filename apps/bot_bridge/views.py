from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.bot_bridge.serializers import (
    ProductSerializer,
    ClientSerializer,
    WorkerSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    CourierTripSerializer,
    CourierShiftSerializer,
    OrderConfirmationSerializer,
    OrderQuantityUpdateSerializer,
    OrderCreateModelSerializer,
)
from apps.bot_bridge.permissions import IsCourier
from apps.logistics.models import CourierShift, CourierTrip, Order
from apps.products.models import Product
from apps.clients.models import Client
from apps.workers.models import Worker


class CourierDeliveryListView(APIView):
    """Получение списка доставок для курьера"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        today = timezone.now().date()
        
        # Возвращаем активные смены и заказы P0
        shifts = CourierShift.objects.filter(courier=courier, status=CourierShift.Status.OPEN)
        serializer = CourierShiftSerializer(shifts, many=True)
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

        # Для P0 работа происходит через Order; оставляем проверку на существование заказа
        # но сохраняем совместимость: если пришёл id старого журнала — возвращаем 404
        return Response({'error': 'Deprecated endpoint for DeliveryJournal'}, status=status.HTTP_410_GONE)

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
        # Старый endpoint — вернуть код 410 (Gone)
        return Response({'error': 'Deprecated endpoint for DeliveryJournalProducts'}, status=status.HTTP_410_GONE)


class ProductListView(APIView):
    """Получение списка продуктов (каталог)"""
    permission_classes = [IsCourier]

    def get(self, request):
        products = Product.objects.all().order_by('type_product', 'name')
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class PublicProductListView(APIView):
    """Публичный список продуктов для Telegram Mini App (без авторизации)"""
    permission_classes = []  # Без авторизации

    def get(self, request):
        # Фильтруем только товары для продажи (вода, тара, кулеры)
        products = Product.objects.filter(
            type_product__in=['WE', 'B20L', 'BT', 'CL', 'AR']
        ).order_by('type_product', 'name')
        
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
        
        # Возвращаем заказы на сегодня из P0
        active_shift = CourierShift.objects.filter(courier=courier, status=CourierShift.Status.OPEN).first()
        if not active_shift:
            return Response({'orders': []})
        orders = Order.objects.filter(trip__shift=active_shift).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class MarkAsDeliveredView(APIView):
    """Пометить доставку как выполненную (альтернатива подтверждению)"""
    permission_classes = [IsCourier]

    def post(self, request, delivery_id):
        return Response({'error': 'Deprecated endpoint for DeliveryJournal'}, status=status.HTTP_410_GONE)


class ClientOrderView(APIView):
    """Создание заказа через Telegram Mini App (для клиентов)"""
    permission_classes = []  # Без авторизации, но проверка по tg_id
    
    def post(self, request):
        from apps.clients.models import Client
        from apps.products.models import Product
        from django.utils import timezone
        
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Получаем клиента по tg_id
            client = Client.objects.get(tg_id=data['client_tg_id'])
        except Client.DoesNotExist:
            return Response(
                {'error': 'Клиент не найден. Пожалуйста, зарегистрируйтесь в системе.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            product = Product.objects.get(id=data['product_id'])
        except Product.DoesNotExist:
            return Response(
                {'error': 'Продукт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Создаём запись P0: создаём (или назначаем) смену/рейс и Order
        today = timezone.now().date()

        from apps.workers.models import Worker
        courier = Worker.objects.filter(type_worker='COURIER').first()

        # Находим/создаём открытую смену
        shift, _ = CourierShift.objects.get_or_create(courier=courier, status=CourierShift.Status.OPEN)

        # Создаём рейс (упрощённо одна запись)
        trip = CourierTrip.objects.create(shift=shift, full_loaded=0)

        # Создаём заказ
        order = Order.objects.create(
            trip=trip,
            client=client,
            product=product,
            quantity=data['quantity'],
            payment_type=Order.PaymentType.CASH,
        )

        return Response({
            'status': 'created',
            'message': 'Заказ успешно создан (P0)',
            'order_id': order.id,
            'product': product.name,
            'quantity': order.quantity,
            'price': order.price,
            'estimated_date': today.isoformat(),
            'courier': courier.full_name if courier else 'Будет назначен'
        }, status=status.HTTP_201_CREATED)


# Новые представления для моделей P0

class CourierShiftListView(APIView):
    """Получение списка смен курьера"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        shifts = CourierShift.objects.filter(courier=courier).order_by('-date')
        serializer = CourierShiftSerializer(shifts, many=True)
        return Response(serializer.data)


class CourierTripListView(APIView):
    """Получение списка рейсов для активной смены"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        # Получаем активную смену (открытую)
        active_shift = CourierShift.objects.filter(
            courier=courier,
            status=CourierShift.Status.OPEN
        ).first()
        
        if not active_shift:
            return Response({
                'active_shift': False,
                'message': 'Нет активной смены'
            })
        
        trips = CourierTrip.objects.filter(shift=active_shift).order_by('-started_at')
        serializer = CourierTripSerializer(trips, many=True)
        return Response({
            'active_shift': True,
            'shift_id': active_shift.id,
            'trips': serializer.data
        })


class OrderListView(APIView):
    """Получение списка заказов для рейса"""
    permission_classes = [IsCourier]

    def get(self, request, trip_id):
        courier = request.courier
        trip = get_object_or_404(CourierTrip, id=trip_id)
        
        # Проверяем, что рейс принадлежит курьеру
        if trip.shift.courier != courier:
            return Response(
                {'error': 'Недостаточно прав для просмотра заказов этого рейса'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        orders = Order.objects.filter(trip=trip).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class OrderConfirmationView(APIView):
    """Подтверждение заказа (доставки) курьером"""
    permission_classes = [IsCourier]

    def post(self, request):
        serializer = OrderConfirmationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        order_id = data['order_id']
        confirmed = data['confirmed']
        container_op = data.get('container_op')
        note = data.get('note', '')
        
        order = get_object_or_404(Order, id=order_id)
        
        # Проверяем, что заказ принадлежит курьеру
        if order.trip.shift.courier != request.courier:
            return Response(
                {'error': 'Недостаточно прав для подтверждения этого заказа'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if confirmed:
            # Обновляем статус заказа
            order.status = Order.Status.DELIVERED
            order.delivered_at = timezone.now()
            if container_op:
                order.container_op = container_op
            if note:
                order.note = note
            order.save()
            
            # Здесь можно добавить логику списания со склада и т.д.
            
            return Response({
                'status': 'confirmed',
                'message': f'Заказ #{order.id} подтвержден',
                'order_id': order.id,
                'delivered_at': order.delivered_at
            })
        else:
            # Отмена заказа
            order.status = Order.Status.CANCELLED
            order.save()
            return Response({
                'status': 'cancelled',
                'message': f'Заказ #{order.id} отменен',
                'order_id': order.id
            })


class OrderQuantityUpdateView(APIView):
    """Изменение количества в заказе"""
    permission_classes = [IsCourier]

    def post(self, request):
        serializer = OrderQuantityUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        order_id = data['order_id']
        new_quantity = data['new_quantity']
        
        order = get_object_or_404(Order, id=order_id)
        
        # Проверяем, что заказ принадлежит курьеру
        if order.trip.shift.courier != request.courier:
            return Response(
                {'error': 'Недостаточно прав для изменения этого заказа'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Обновляем количество (цена пересчитается автоматически в save())
        order.quantity = new_quantity
        order.save()
        
        return Response({
            'status': 'updated',
            'order_id': order.id,
            'new_quantity': new_quantity,
            'new_price': order.price
        })


class CreateOrderView(APIView):
    """Создание нового заказа в рейсе (для курьера)"""
    permission_classes = [IsCourier]

    def post(self, request):
        from apps.bot_bridge.serializers import OrderCreateSerializer as OrderCreateModelSerializer
        
        serializer = OrderCreateModelSerializer(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order = serializer.save()
        
        return Response({
            'status': 'created',
            'message': 'Заказ успешно создан',
            'order_id': order.id,
            'product': order.product.name,
            'quantity': order.quantity,
            'price': order.price
        }, status=status.HTTP_201_CREATED)
