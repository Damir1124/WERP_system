from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.db import models

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
from apps.bot_bridge.permissions import IsCourier, IsAdmin
from apps.logistics.models import CourierShift, CourierTrip, Order
from apps.products.models import Product
from apps.clients.models import Client
from apps.workers.models import Worker
from apps.accounting.models import Finance
from apps.warehouse.models import StockBalance


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
        courier = Worker.objects.filter(worker_type='COURIER').first()

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


class IdentifyView(APIView):
    """
    Идентификация пользователя по Telegram ID.
    GET /api/bot/identify/?tg_id=<id>
    Возвращает роль (courier, client, admin, unknown) и данные пользователя.
    """
    permission_classes = []  # публичный endpoint

    def get(self, request):
        tg_id = request.query_params.get('tg_id')
        if not tg_id:
            return Response(
                {'error': 'Параметр tg_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            tg_id_int = int(tg_id)
        except ValueError:
            return Response(
                {'error': 'tg_id должен быть числом'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем Worker (курьер или администратор)
        from apps.workers.models import Worker
        from apps.clients.models import Client
        
        worker = Worker.objects.filter(tg_id=tg_id_int).first()
        if worker:
            role = 'admin' if worker.is_admin else 'courier'
            return Response({
                'role': role,
                'name': worker.full_name,
                'id': worker.id,
                'worker_type': worker.worker_type,
            })
        
        # Проверяем Client
        client = Client.objects.filter(tg_id=tg_id_int).first()
        if client:
            return Response({
                'role': 'client',
                'name': client.name,
                'id': client.id,
                'phone': client.phone,
            })
        
        # Не найден
        return Response({
            'role': 'unknown',
            'message': 'Пользователь не зарегистрирован в системе'
        })


# Новые API endpoints для курьерского Mini App (3.2)

class CourierPoolView(APIView):
    """Получение пула заказов (PENDING заказы без назначенного курьера или все рейса)"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        # Получаем заказы со статусом PENDING, которые не назначены курьеру
        # или все заказы активного рейса курьера
        active_shift = CourierShift.objects.filter(
            courier=courier,
            status=CourierShift.Status.OPEN
        ).first()
        
        if active_shift:
            # Получаем заказы активного рейса
            orders_in_trip = Order.objects.filter(
                trip__shift=active_shift,
                status=Order.Status.PENDING
            ).select_related('client', 'product')
            
            # Получаем свободные заказы (не назначены никому)
            free_orders = Order.objects.filter(
                status=Order.Status.PENDING,
                assigned_courier=None
            ).select_related('client', 'product')
            
            # Объединяем заказы
            orders = orders_in_trip.union(free_orders)
        else:
            # Если нет активной смены, показываем только свободные заказы
            orders = Order.objects.filter(
                status=Order.Status.PENDING,
                assigned_courier=None
            ).select_related('client', 'product')
        
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    def post(self, request, order_id):
        """Взять заказ (добавить в свой активный trip)"""
        courier = request.courier
        order = get_object_or_404(Order, id=order_id, status=Order.Status.PENDING)
        
        # Проверяем, что заказ еще не назначен другому курьеру
        if order.assigned_courier and order.assigned_courier != courier:
            return Response(
                {'error': 'Заказ уже назначен другому курьеру'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем или создаем активную смену
        shift, created = CourierShift.objects.get_or_create(
            courier=courier,
            status=CourierShift.Status.OPEN
        )
        
        # Получаем или создаем активный рейс
        trip = CourierTrip.objects.filter(
            shift=shift,
            status=CourierTrip.Status.ACTIVE
        ).first()
        
        if not trip:
            # Создаем новый рейс, если нет активного
            trip = CourierTrip.objects.create(
                shift=shift,
                full_loaded=0,  # Будет обновлено при необходимости
                status=CourierTrip.Status.ACTIVE
            )
        
        # Назначаем заказ курьеру и в рейс
        order.assigned_courier = courier
        order.trip = trip
        order.save(update_fields=['assigned_courier', 'trip'])
        
        return Response({
            'status': 'assigned',
            'message': f'Заказ #{order.id} назначен вам',
            'order_id': order.id
        })


class CourierCurrentTripView(APIView):
    """Получение активного CourierTrip + его заказы + summary"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        # Получаем активную смену
        active_shift = CourierShift.objects.filter(
            courier=courier,
            status=CourierShift.Status.OPEN
        ).first()
        
        if not active_shift:
            return Response({
                'active_shift': False,
                'message': 'Нет активной смены'
            })
        
        # Получаем активный рейс
        active_trip = CourierTrip.objects.filter(
            shift=active_shift,
            status=CourierTrip.Status.ACTIVE
        ).prefetch_related('orders__client', 'orders__product').first()
        
        if not active_trip:
            return Response({
                'active_trip': False,
                'message': 'Нет активного рейса'
            })
        
        # Сериализуем рейс с заказами
        trip_serializer = CourierTripSerializer(active_trip)
        
        # Расчетные поля
        orders_delivered_cash = active_trip.orders.filter(
            status=Order.Status.DELIVERED,
            payment_type=Order.PaymentType.CASH
        ).aggregate(total=Sum('price'))['total'] or 0
        
        orders_delivered_card = active_trip.orders.filter(
            status=Order.Status.DELIVERED,
            payment_type=Order.PaymentType.CARD
        ).aggregate(total=Sum('price'))['total'] or 0
        
        exchange_orders_count = active_trip.orders.filter(
            status=Order.Status.DELIVERED,
            container_op=Order.ContainerOp.EXCHANGE
        ).count()
        
        # Суммируем delivered, full_returned из всех заказов
        delivered_total = active_trip.orders.filter(status=Order.Status.DELIVERED).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        full_returned_total = active_trip.orders.filter(status=Order.Status.DELIVERED).aggregate(
            total=Sum('full_returned')
        )['total'] or 0
        
        # Получаем full_loaded из рейса
        full_loaded = active_trip.full_loaded
        
        full_remain = full_loaded - delivered_total - full_returned_total
        
        summary = {
            'full_loaded': full_loaded,
            'delivered': delivered_total,
            'full_returned': full_returned_total,
            'full_remain': full_remain,
            'empty_expected': exchange_orders_count,
            'cash_expected': orders_delivered_cash,
            'card_expected': orders_delivered_card,
        }
        
        return Response({
            'trip': trip_serializer.data,
            'summary': summary
        })


class CourierColleaguesView(APIView):
    """Получение курьеров с открытой сменой сегодня"""
    permission_classes = [IsCourier]

    def get(self, request):
        today = timezone.now().date()
        # Получаем курьеров с открытыми сменами сегодня
        colleagues = Worker.objects.filter(
            worker_type=Worker.WorkerType.COURIER,
            couriershift__status=CourierShift.Status.OPEN,
            couriershift__date=today
        ).annotate(
            delivered_today=Count(
                'couriershift__trips__orders',
                filter=Q(couriershift__trips__orders__status=Order.Status.DELIVERED)
            ),
            cash_total=Sum(
                'couriershift__trips__orders__price',
                filter=Q(couriershift__trips__orders__status=Order.Status.DELIVERED,
                        couriershift__trips__orders__payment_type=Order.PaymentType.CASH)
            ),
            card_total=Sum(
                'couriershift__trips__orders__price',
                filter=Q(couriershift__trips__orders__status=Order.Status.DELIVERED,
                        couriershift__trips__orders__payment_type=Order.PaymentType.CARD)
            )
        ).distinct()
        
        # Сериализуем данные
        data = []
        for colleague in colleagues:
            data.append({
                'id': colleague.id,
                'full_name': colleague.full_name,
                'delivered_today': colleague.delivered_today,
                'cash_total': colleague.cash_total or 0,
                'card_total': colleague.card_total or 0,
                'phone': getattr(colleague, 'phone', None)  # Предполагаем, что у Worker есть поле phone
            })
        
        return Response(data)


# Новые API endpoints для клиентского Mini App (3.3)

class ClientProductListView(APIView):
    """Каталог товаров для клиентов (только WATER, BOTTLE_20L)"""
    permission_classes = []  # публичный доступ

    def get(self, request):
        from apps.products.models import Product
        # Фильтруем только товары для продажи клиентам (вода с тарой и без)
        products = Product.objects.filter(
            type_product__in=[Product.TypeProduct.WATER, Product.TypeProduct.BOTTLE_20L]
        ).order_by('type_product', 'name')
        
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ClientOrderCreateView(APIView):
    """Создание заказа клиентом (status=PENDING, trip=None до назначения)"""
    permission_classes = []  # авторизация по tg_id в теле запроса

    def post(self, request):
        from apps.clients.models import Client
        from apps.products.models import Product
        from apps.logistics.models import Order
        from django.utils import timezone

        # Получаем tg_id из заголовка или тела запроса
        tg_id = request.data.get('client_tg_id') or request.headers.get('X-Telegram-ID')
        if not tg_id:
            return Response(
                {'error': 'Не указан client_tg_id (Telegram ID клиента)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = Client.objects.get(tg_id=tg_id)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Клиент не найден. Пожалуйста, зарегистрируйтесь в системе.'},
                status=status.HTTP_404_NOT_FOUND
            )

        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        payment_type = request.data.get('payment_type', Order.PaymentType.CASH)
        address = request.data.get('address', client.address)
        note = request.data.get('note', '')

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Продукт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Создаём заказ без привязки к рейсу (trip=None)
        order = Order.objects.create(
            trip=None,
            client=client,
            product=product,
            quantity=quantity,
            payment_type=payment_type,
            status=Order.Status.PENDING,
            note=note,
        )

        # Если есть адрес, обновляем адрес клиента (опционально)
        if address and address != client.address:
            client.address = address
            client.save(update_fields=['address'])

        return Response({
            'status': 'created',
            'message': 'Заказ успешно создан и ожидает назначения курьера',
            'order_id': order.id,
            'product': product.name,
            'quantity': order.quantity,
            'price': order.price,
            'estimated_date': timezone.now().date().isoformat(),
        }, status=status.HTTP_201_CREATED)


class ClientOrderHistoryView(APIView):
    """История заказов клиента (по tg_id)"""
    permission_classes = []  # авторизация по tg_id в заголовке

    def get(self, request):
        from apps.clients.models import Client
        from apps.logistics.models import Order

        tg_id = request.query_params.get('tg_id') or request.headers.get('X-Telegram-ID')
        if not tg_id:
            return Response(
                {'error': 'Не указан tg_id (Telegram ID клиента)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = Client.objects.get(tg_id=tg_id)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Клиент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        orders = Order.objects.filter(client=client).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class ClientOrderStatusView(APIView):
    """Текущий статус заказа + информация о курьере если DELIVERED"""
    permission_classes = []  # публичный доступ, но проверяем принадлежность заказа клиенту

    def get(self, request, order_id):
        from apps.clients.models import Client
        from apps.logistics.models import Order

        tg_id = request.query_params.get('tg_id') or request.headers.get('X-Telegram-ID')
        if not tg_id:
            return Response(
                {'error': 'Не указан tg_id (Telegram ID клиента)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = Client.objects.get(tg_id=tg_id)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Клиент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            order = Order.objects.get(id=order_id, client=client)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден или не принадлежит вам'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Собираем информацию о курьере, если заказ доставлен и есть assigned_courier
        courier_info = None
        if order.status == Order.Status.DELIVERED and order.assigned_courier:
            courier = order.assigned_courier
            courier_info = {
                'id': courier.id,
                'full_name': courier.full_name,
                'phone': getattr(courier, 'phone', None),
            }

        response_data = {
            'order_id': order.id,
            'status': order.status,
            'status_display': order.get_status_display(),
            'product': order.product.name,
            'quantity': order.quantity,
            'price': order.price,
            'payment_type': order.payment_type,
            'created_at': order.created_at,
            'delivered_at': order.delivered_at,
            'courier': courier_info,
        }

        return Response(response_data)


# Новые API endpoints для admin-профиля (3.4)

class AdminStatsTodayView(APIView):
    """
    GET /api/bot/admin/stats/today/
    Finance за сегодня + кол-во активных смен + заказов
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        
        # Получаем Finance за сегодня
        finance = Finance.objects.filter(date=today).first()
        
        # Количество активных смен сегодня
        active_shifts_count = CourierShift.objects.filter(
            date=today,
            status=CourierShift.Status.OPEN
        ).count()
        
        # Количество заказов сегодня (любого статуса)
        orders_today = Order.objects.filter(
            created_at__date=today
        ).count()
        
        # Количество доставленных заказов сегодня
        delivered_today = Order.objects.filter(
            delivered_at__date=today,
            status=Order.Status.DELIVERED
        ).count()
        
        response_data = {
            'date': today.isoformat(),
            'finance': {
                'income': finance.income if finance else 0,
                'consumption': finance.consumption if finance else 0,
                'profit': finance.profit if finance else 0,
                'card_profit': finance.card_profit if finance else 0,
            } if finance else None,
            'active_shifts': active_shifts_count,
            'orders_today': orders_today,
            'delivered_today': delivered_today,
        }
        return Response(response_data)


class AdminShiftsView(APIView):
    """
    GET /api/bot/admin/shifts/
    Активные CourierShift с courier, cash_total, card_total
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        shifts = CourierShift.objects.filter(
            date=today,
            status=CourierShift.Status.OPEN
        ).select_related('courier').order_by('courier__full_name')
        
        data = []
        for shift in shifts:
            # Количество заказов в смене (сумма по всем рейсам)
            orders_count = Order.objects.filter(
                trip__shift=shift
            ).count()
            
            data.append({
                'id': shift.id,
                'courier_id': shift.courier.id,
                'courier_name': shift.courier.full_name,
                'cash_total': shift.cash_total,
                'card_total': shift.card_total,
                'total': shift.cash_total + shift.card_total,
                'opened_at': shift.opened_at,
                'orders_count': orders_count,
            })
        
        return Response(data)


class AdminStockAlertsView(APIView):
    """
    GET /api/bot/admin/stock/alerts/
    StockBalance где quantity < 10
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        alerts = StockBalance.objects.filter(
            quantity__lt=10
        ).select_related('product').order_by('quantity')
        
        data = []
        for alert in alerts:
            data.append({
                'product_id': alert.product.id,
                'product_name': alert.product.name,
                'product_type': alert.product.type_product,
                'quantity': alert.quantity,
                'last_received_date': alert.last_received_date,
                'last_departure_date': alert.last_departure_date,
            })
        
        return Response(data)


class AdminOrdersRecentView(APIView):
    """
    GET /api/bot/admin/orders/recent/
    Последние N заказов (по умолчанию 10)
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        orders = Order.objects.select_related(
            'client', 'product', 'assigned_courier', 'trip__shift__courier'
        ).order_by('-created_at')[:limit]
        
        data = []
        for order in orders:
            data.append({
                'id': order.id,
                'client_name': order.client.name if order.client else None,
                'client_phone': order.client.phone if order.client else None,
                'product_name': order.product.name,
                'quantity': order.quantity,
                'price': order.price,
                'payment_type': order.payment_type,
                'payment_type_display': order.get_payment_type_display(),
                'status': order.status,
                'status_display': order.get_status_display(),
                'container_op': order.container_op,
                'container_op_display': order.get_container_op_display(),
                'assigned_courier_name': order.assigned_courier.full_name if order.assigned_courier else None,
                'courier_name': order.trip.shift.courier.full_name if order.trip and order.trip.shift else None,
                'created_at': order.created_at,
                'delivered_at': order.delivered_at,
            })
        
        return Response(data)
