from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count

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
from apps.logistics.models import CourierShift, CourierTrip, Order, OrderItem
from apps.products.models import Product
from apps.clients.models import Client
from apps.workers.models import Worker
from apps.accounting.models import Finance
from apps.warehouse.models import StockBalance


class APIRootView(APIView):
    """Корневой эндпоинт API для бота."""
    permission_classes = []

    def get(self, request):
        return Response({
            'message': 'WERP Bot Bridge API v2',
            'endpoints': {
                'identify':             '/api/bot/identify/?tg_id=<id>',
                'courier_profile':      '/api/bot/courier/profile/',
                'courier_shifts':       '/api/bot/courier/shifts/',
                'courier_trips':        '/api/bot/courier/trips/',
                'courier_pool':         '/api/bot/courier/pool/',
                'courier_current_trip': '/api/bot/courier/trip/current/',
                'courier_colleagues':   '/api/bot/courier/colleagues/',
                'order_confirm':        '/api/bot/courier/orders/confirm/',
                'client_products':      '/api/bot/client/products/',
                'client_order_create':  '/api/bot/client/order/',
                'client_orders':        '/api/bot/client/orders/',
                'admin_stats':          '/api/bot/admin/stats/today/',
            }
        })


# ─── Идентификация ────────────────────────────────────────────────────────────

class IdentifyView(APIView):
    """
    GET /api/bot/identify/?tg_id=<id>
    Возвращает роль: courier / client / admin / unknown
    """
    permission_classes = []

    def get(self, request):
        init_data = request.headers.get('X-Telegram-Init-Data')
        tg_id_param = request.query_params.get('tg_id')

        tg_id_int = None

        if init_data:
            from apps.bot_bridge.utils import verify_telegram_init_data, extract_user_id_from_init_data
            if not verify_telegram_init_data(init_data):
                return Response({'error': 'Неверная подпись initData'}, status=status.HTTP_401_UNAUTHORIZED)
            tg_id_int = extract_user_id_from_init_data(init_data)
            if not tg_id_int:
                return Response({'error': 'Не удалось извлечь Telegram ID из initData'}, status=status.HTTP_400_BAD_REQUEST)
        elif tg_id_param:
            try:
                tg_id_int = int(tg_id_param)
            except ValueError:
                return Response({'error': 'tg_id должен быть числом'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Необходим параметр tg_id или заголовок X-Telegram-Init-Data'}, status=status.HTTP_400_BAD_REQUEST)

        worker = Worker.objects.filter(tg_id=tg_id_int).first()
        if worker:
            role = 'admin' if worker.is_admin else 'courier'
            return Response({
                'role': role,
                'name': worker.full_name,
                'id': worker.id,
                'worker_type': worker.worker_type,
            })

        client = Client.objects.filter(tg_id=tg_id_int).first()
        if client:
            return Response({
                'role': 'client',
                'name': client.name,
                'id': client.id,
                'phone': client.phone,
                'address': client.address,
            })

        return Response({'role': 'unknown', 'message': 'Пользователь не зарегистрирован'})


# ─── Профиль курьера ──────────────────────────────────────────────────────────

class CourierProfileView(APIView):
    """GET /api/bot/courier/profile/"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        serializer = WorkerSerializer(courier)
        return Response(serializer.data)


# ─── Смены ────────────────────────────────────────────────────────────────────

class CourierShiftListView(APIView):
    """
    GET  /api/bot/courier/shifts/  — история смен курьера
    POST /api/bot/courier/shifts/  — открыть новую смену
    """
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        shifts = CourierShift.objects.filter(courier=courier).order_by('-date')
        serializer = CourierShiftSerializer(shifts, many=True)
        return Response(serializer.data)

    def post(self, request):
        courier = request.courier
        # Проверяем, нет ли уже открытой смены
        existing = CourierShift.objects.filter(
            courier=courier,
            status=CourierShift.Status.OPEN
        ).first()
        if existing:
            serializer = CourierShiftSerializer(existing)
            return Response({
                'message': 'Смена уже открыта',
                'shift': serializer.data
            }, status=status.HTTP_200_OK)

        shift = CourierShift.objects.create(courier=courier)
        serializer = CourierShiftSerializer(shift)
        return Response({
            'message': 'Смена открыта',
            'shift': serializer.data
        }, status=status.HTTP_201_CREATED)


class CourierShiftCloseView(APIView):
    """POST /api/bot/courier/shifts/<shift_id>/close/"""
    permission_classes = [IsCourier]

    def post(self, request, shift_id):
        courier = request.courier
        shift = get_object_or_404(CourierShift, id=shift_id, courier=courier)
        if shift.status == CourierShift.Status.CLOSED:
            return Response({'error': 'Смена уже закрыта'}, status=status.HTTP_400_BAD_REQUEST)
        shift.close()
        return Response({'message': f'Смена #{shift.id} закрыта', 'shift_id': shift.id})


# ─── Рейсы ────────────────────────────────────────────────────────────────────

class CourierTripListView(APIView):
    """
    GET  /api/bot/courier/trips/  — рейсы активной смены
    POST /api/bot/courier/trips/  — открыть новый рейс
    """
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        active_shift = CourierShift.objects.filter(
            courier=courier,
            status=CourierShift.Status.OPEN
        ).first()

        if not active_shift:
            return Response({'active_shift': False, 'message': 'Нет активной смены', 'trips': []})

        trips = CourierTrip.objects.filter(shift=active_shift).order_by('-started_at')
        serializer = CourierTripSerializer(trips, many=True)
        return Response({
            'active_shift': True,
            'shift_id': active_shift.id,
            'trips': serializer.data
        })

    def post(self, request):
        courier = request.courier
        active_shift = CourierShift.objects.filter(
            courier=courier,
            status=CourierShift.Status.OPEN
        ).first()

        if not active_shift:
            return Response({'error': 'Сначала откройте смену'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, нет ли уже активного рейса
        existing_trip = CourierTrip.objects.filter(
            shift=active_shift,
            status=CourierTrip.Status.ACTIVE
        ).first()
        if existing_trip:
            serializer = CourierTripSerializer(existing_trip)
            return Response({'message': 'Рейс уже активен', 'trip': serializer.data}, status=status.HTTP_200_OK)

        full_loaded = request.data.get('full_loaded', 0)
        trip = CourierTrip.objects.create(
            shift=active_shift,
            full_loaded=full_loaded,
            status=CourierTrip.Status.ACTIVE
        )
        serializer = CourierTripSerializer(trip)
        return Response({'message': 'Рейс открыт', 'trip': serializer.data}, status=status.HTTP_201_CREATED)


class CourierCurrentTripView(APIView):
    """GET /api/bot/courier/trip/current/ — активный рейс + заказы + summary"""
    permission_classes = [IsCourier]

    def get(self, request):
        courier = request.courier
        active_shift = CourierShift.objects.filter(
            courier=courier,
            status=CourierShift.Status.OPEN
        ).first()

        if not active_shift:
            return Response({'active_shift': False, 'message': 'Нет активной смены'})

        active_trip = CourierTrip.objects.filter(
            shift=active_shift,
            status=CourierTrip.Status.ACTIVE
        ).prefetch_related('orders__client', 'orders__items__product').first()

        if not active_trip:
            return Response({
                'active_shift': True,
                'shift_id': active_shift.id,
                'active_trip': False,
                'message': 'Нет активного рейса'
            })

        trip_serializer = CourierTripSerializer(active_trip)

        # Расчётные поля через OrderItem (поля quantity/price/product перенесены в OrderItem)
        from apps.logistics.models import OrderItem
        from django.db.models import Sum as DSum

        cash_expected = OrderItem.objects.filter(
            order__trip=active_trip,
            order__status=Order.Status.DELIVERED,
            order__payment_type=Order.PaymentType.CASH
        ).aggregate(total=DSum('price'))['total'] or 0

        card_expected = OrderItem.objects.filter(
            order__trip=active_trip,
            order__status=Order.Status.DELIVERED,
            order__payment_type=Order.PaymentType.CARD
        ).aggregate(total=DSum('price'))['total'] or 0

        # exchange_count — заказы с хотя бы одной позицией exchange_qty > 0
        exchange_count = active_trip.orders.filter(
            status=Order.Status.DELIVERED,
            items__exchange_qty__gt=0
        ).distinct().count()

        delivered_qty = OrderItem.objects.filter(
            order__trip=active_trip,
            order__status=Order.Status.DELIVERED
        ).aggregate(total=DSum('quantity'))['total'] or 0

        summary = {
            'full_loaded': active_trip.full_loaded,
            'delivered': delivered_qty,
            'full_returned': active_trip.full_returned,
            'full_remain': active_trip.full_loaded - delivered_qty - active_trip.full_returned,
            'empty_expected': exchange_count,
            'cash_expected': cash_expected,
            'card_expected': card_expected,
        }

        return Response({
            'active_shift': True,
            'shift_id': active_shift.id,
            'active_trip': True,
            'trip': trip_serializer.data,
            'summary': summary,
        })


# ─── Заказы ───────────────────────────────────────────────────────────────────

class OrderListView(APIView):
    """GET /api/bot/courier/trips/<trip_id>/orders/"""
    permission_classes = [IsCourier]

    def get(self, request, trip_id):
        courier = request.courier
        trip = get_object_or_404(CourierTrip, id=trip_id)
        if trip.shift.courier != courier:
            return Response({'error': 'Нет доступа к этому рейсу'}, status=status.HTTP_403_FORBIDDEN)
        orders = Order.objects.filter(trip=trip).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class OrderConfirmationView(APIView):
    """POST /api/bot/courier/orders/confirm/ — подтверждение доставки с поддержкой многопозиционных данных о таре"""
    permission_classes = [IsCourier]

    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Order confirmation request data: {request.data}")
        
        serializer = OrderConfirmationSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Serializer validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        order_id = data['order_id']
        confirmed = data['confirmed']
        note = data.get('note', '')
        items_data = data.get('items', [])
        logger.info(f"Validated data: order_id={order_id}, confirmed={confirmed}, items count={len(items_data)}")
        for idx, item in enumerate(items_data):
            logger.info(f"Item {idx}: {item}")

        order = get_object_or_404(Order, id=order_id)

        # Проверяем принадлежность заказа курьеру
        if order.trip and order.trip.shift.courier != request.courier:
            return Response({'error': 'Нет доступа к этому заказу'}, status=status.HTTP_403_FORBIDDEN)

        if confirmed:
            # Проверка инвариантов для продуктов BOTTLE_20L
            from apps.products.models import Product
            for item_data in items_data:
                item_id = item_data['item_id']
                try:
                    order_item = OrderItem.objects.get(id=item_id, order=order)
                except OrderItem.DoesNotExist:
                    return Response(
                        {'error': f'Позиция с ID {item_id} не найдена в заказе #{order.id}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if order_item.product.type_product in (Product.TypeProduct.BOTTLE_20L, Product.TypeProduct.WATER):
                    exchange_qty = item_data.get('exchange_qty', 0)
                    if exchange_qty == 0:
                        return Response(
                            {'error': f'Для продукта "{order_item.product.name}" обмен тары не может быть нулевым при подтверждении доставки'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            # Обновляем данные о таре и количестве для каждой позиции
            updated_items = []
            bottle_items_created = []
            for item_data in items_data:
                item_id = item_data['item_id']
                try:
                    order_item = OrderItem.objects.get(id=item_id, order=order)
                except OrderItem.DoesNotExist:
                    return Response(
                        {'error': f'Позиция с ID {item_id} не найдена в заказе #{order.id}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Обновляем количество, если передано
                new_quantity = item_data.get('quantity')
                if new_quantity is not None:
                    order_item.quantity = new_quantity
                    order_item.price = None  # сброс для пересчёта в save()
                
                # Обновляем поля операций с тарой
                exchange_qty = item_data.get('exchange_qty', 0)
                sell_with_qty = item_data.get('sell_with_qty', 0)
                defective_qty = item_data.get('defective_qty', 0)
                logger.info(f"Updating item {item_id}: exchange_qty={exchange_qty}, sell_with_qty={sell_with_qty}, defective_qty={defective_qty}")
                
                # ВАЖНО: exchange_qty перезаписывает quantity при подтверждении
                # Это фактическое количество проданной воды
                if order_item.product.type_product in (Product.TypeProduct.BOTTLE_20L, Product.TypeProduct.WATER):
                    order_item.quantity = exchange_qty
                    logger.info(f"Updated quantity to {exchange_qty} for water product")
                
                order_item.exchange_qty = exchange_qty
                order_item.sell_with_qty = sell_with_qty
                order_item.defective_qty = defective_qty
                
                # ВАЖНО: При подтверждении заказа мы не должны пересчитывать quantity как сумму
                # exchange_qty + sell_with_qty + defective_qty, если это приведет к увеличению
                # количества воды. Вода (WATER/BOTTLE_20L) уже имеет quantity.
                # Если мы продаем с тарой (sell_with_qty), это означает, что часть из заказанной
                # воды продается с тарой, а не то, что мы добавляем еще воду.
                # Поэтому мы временно отключаем авто-пересчет quantity в save() для этого случая,
                # или корректируем логику.
                # В models.py OrderItem.save() пересчитывает quantity = exchange_qty + sell_with_qty + defective_qty
                # Значит, если клиент заказал 1 воду, и мы ставим exchange=1, sell_with=1,
                # то quantity станет 2. Это неверно.
                # Правильно: сумма (exchange_qty + sell_with_qty + defective_qty) должна быть равна quantity.
                # Если клиент заказал 1 воду, он может либо обменять тару (exchange=1), либо купить с тарой (sell_with=1).
                # Нельзя для одной бутылки воды сделать и то, и другое.
                # Но если фронтенд присылает такие данные, мы должны их сохранить.
                
                order_item.save()
                logger.info(f"Saved item {item_id}: quantity={order_item.quantity}, exchange_qty={order_item.exchange_qty}, sell_with_qty={order_item.sell_with_qty}, defective_qty={order_item.defective_qty}")
                
                updated_items.append({
                    'item_id': item_id,
                    'product': order_item.product.name,
                    'quantity': order_item.quantity,
                    'price': order_item.price,
                    'exchange_qty': order_item.exchange_qty,
                    'sell_with_qty': order_item.sell_with_qty,
                    'defective_qty': order_item.defective_qty,
                })
                
                # Создаём отдельную позицию для тары при sell_with_qty > 0
                if sell_with_qty > 0:
                    try:
                        # Используем продукт с ID=9 (основная тара)
                        bottle_product = Product.objects.get(id=9, type_product=Product.TypeProduct.BOTTLE)
                        bottle_item = OrderItem.objects.create(
                            order=order,
                            product=bottle_product,
                            quantity=sell_with_qty
                        )
                        logger.info(f"Created bottle item: id={bottle_item.id}, quantity={sell_with_qty}, price={bottle_item.price}")
                        bottle_items_created.append({
                            'item_id': bottle_item.id,
                            'product': bottle_product.name,
                            'quantity': sell_with_qty,
                            'price': bottle_item.price
                        })
                    except Product.DoesNotExist:
                        logger.error(f"Продукт BOTTLE с ID=9 не найден")
                        return Response(
                            {'error': 'Продукт тары (ID=9) не найден в системе'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
            
            # Обновляем статус заказа
            # Складской сигнал update_stock_on_order списывает exchange_qty + sell_with_qty
            # для BOTTLE_20L (подменяет на BOTTLE). Созданная BOTTLE OrderItem не списывается
            # повторно, т.к. её product.type_product == BOTTLE (не подменяется).
            order.status = Order.Status.DELIVERED
            order.delivered_at = timezone.now()
            if note:
                order.note = note
            order.save()

            # Уведомление клиенту
            try:
                from apps.bot_bridge.notify import notify_client_order_delivered
                notify_client_order_delivered(order)
            except Exception:
                pass

            return Response({
                'status': 'confirmed',
                'message': f'Заказ #{order.id} подтверждён',
                'order_id': order.id,
                'delivered_at': order.delivered_at,
                'updated_items': updated_items,
            })
        else:
            order.status = Order.Status.CANCELLED
            order.save()
            return Response({
                'status': 'cancelled',
                'message': f'Заказ #{order.id} отменён',
                'order_id': order.id,
            })


class OrderQuantityUpdateView(APIView):
    """POST /api/bot/courier/orders/update-quantity/ — изменение количества с поддержкой многопозиционной структуры"""
    permission_classes = [IsCourier]

    def post(self, request):
        serializer = OrderQuantityUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        item_id = data['item_id']
        new_quantity = data['new_quantity']
        container_data = data.get('container_data', {})

        # Получаем позицию заказа
        order_item = get_object_or_404(OrderItem, id=item_id)
        order = order_item.order

        # Проверяем принадлежность заказа курьеру
        if order.trip and order.trip.shift.courier != request.courier:
            return Response({'error': 'Нет доступа к этому заказу'}, status=status.HTTP_403_FORBIDDEN)

        # Проверяем, что заказ еще не доставлен
        if order.status == Order.Status.DELIVERED:
            return Response({'error': 'Нельзя изменить количество в доставленном заказе'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Обновляем количество
        order_item.quantity = new_quantity
        order_item.price = None  # сбросить, чтобы пересчиталось в save()
        
        # Обновляем данные о таре, если они предоставлены
        if container_data:
            order_item.exchange_qty = container_data.get('exchange_qty', order_item.exchange_qty)
            order_item.sell_with_qty = container_data.get('sell_with_qty', order_item.sell_with_qty)
            order_item.defective_qty = container_data.get('defective_qty', order_item.defective_qty)
        
        order_item.save()

        # Пересчитываем общую стоимость заказа
        total_price = order.get_total_price()

        return Response({
            'status': 'updated',
            'order_id': order.id,
            'order_item_id': order_item.id,
            'product': order_item.product.name,
            'new_quantity': order_item.quantity,
            'new_price': order_item.price,
            'container_data': {
                'exchange_qty': order_item.exchange_qty,
                'sell_with_qty': order_item.sell_with_qty,
                'defective_qty': order_item.defective_qty,
            },
            'total_price': total_price,
        })


class CreateOrderView(APIView):
    """POST /api/bot/courier/orders/create/ — создание заказа курьером"""
    permission_classes = [IsCourier]

    def post(self, request):
        serializer = OrderCreateModelSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order = serializer.save()
        # Сериализуем созданный заказ для ответа
        order_serializer = OrderSerializer(order, context={'request': request})
        return Response({
            'status': 'created',
            'message': 'Заказ создан',
            'order': order_serializer.data,
        }, status=status.HTTP_201_CREATED)


# ─── Пул заказов ─────────────────────────────────────────────────────────────

class CourierPoolView(APIView):
    """
    GET  /api/bot/courier/pool/              — список PENDING заказов без курьера
    POST /api/bot/courier/pool/<order_id>/assign/ — взять заказ
    """
    permission_classes = [IsCourier]

    def get(self, request):
        # Свободные заказы (без рейса или без назначенного курьера)
        free_orders = Order.objects.filter(
            status=Order.Status.PENDING,
            assigned_courier__isnull=True,
        ).select_related('client', 'trip', 'assigned_courier').prefetch_related('items__product').order_by('-created_at')

        serializer = OrderSerializer(free_orders, many=True)
        return Response(serializer.data)


class CourierAssignOrderView(APIView):
    """POST /api/bot/courier/pool/<order_id>/assign/"""
    permission_classes = [IsCourier]

    def post(self, request, order_id):
        courier = request.courier
        order = get_object_or_404(Order, id=order_id, status=Order.Status.PENDING)

        if order.assigned_courier and order.assigned_courier != courier:
            return Response({'error': 'Заказ уже назначен другому курьеру'}, status=status.HTTP_400_BAD_REQUEST)

        # Получаем или создаём активную смену
        shift, _ = CourierShift.objects.get_or_create(
            courier=courier,
            status=CourierShift.Status.OPEN,
            defaults={'courier': courier}
        )

        # Получаем или создаём активный рейс
        trip = CourierTrip.objects.filter(
            shift=shift,
            status=CourierTrip.Status.ACTIVE
        ).first()

        if not trip:
            trip = CourierTrip.objects.create(
                shift=shift,
                full_loaded=0,
                status=CourierTrip.Status.ACTIVE
            )

        order.assigned_courier = courier
        order.trip = trip
        order.save(update_fields=['assigned_courier', 'trip'])

        # Уведомление клиенту
        try:
            from apps.bot_bridge.notify import notify_client_order_accepted
            notify_client_order_accepted(order)
        except Exception:
            pass

        return Response({
            'status': 'assigned',
            'message': f'Заказ #{order.id} взят в работу',
            'order_id': order.id,
            'trip_id': trip.id,
        })


# ─── Коллеги ──────────────────────────────────────────────────────────────────

class CourierColleaguesView(APIView):
    """GET /api/bot/courier/colleagues/"""
    permission_classes = [IsCourier]

    def get(self, request):
        today = timezone.now().date()
        colleagues = Worker.objects.filter(
            worker_type=Worker.WorkerType.COURIER,
            couriershift__status=CourierShift.Status.OPEN,
            couriershift__date=today
        ).annotate(
            delivered_today=Count(
                'couriershift__trips__orders',
                filter=Q(couriershift__trips__orders__status=Order.Status.DELIVERED)
            )
        ).distinct()

        # price теперь в OrderItem — считаем через отдельные запросы
        from apps.logistics.models import OrderItem
        data = []
        for c in colleagues:
            cash_total = OrderItem.objects.filter(
                order__trip__shift__courier=c,
                order__trip__shift__date=today,
                order__status=Order.Status.DELIVERED,
                order__payment_type=Order.PaymentType.CASH,
            ).aggregate(total=Sum('price'))['total'] or 0

            card_total = OrderItem.objects.filter(
                order__trip__shift__courier=c,
                order__trip__shift__date=today,
                order__status=Order.Status.DELIVERED,
                order__payment_type=Order.PaymentType.CARD,
            ).aggregate(total=Sum('price'))['total'] or 0

            data.append({
                'id': c.id,
                'full_name': c.full_name,
                'delivered_today': c.delivered_today or 0,
                'cash_total': cash_total,
                'card_total': card_total,
            })

        return Response(data)


# ─── Продукты и клиенты (для курьера) ────────────────────────────────────────

class ProductListView(APIView):
    """GET /api/bot/products/ — все продукты (для курьера)"""
    permission_classes = [IsCourier]

    def get(self, request):
        # Возвращаем воду и тару, так как фронтенд ищет тару (BT) для расчета стоимости
        products = Product.objects.filter(
            type_product__in=[Product.TypeProduct.WATER, Product.TypeProduct.BOTTLE]
        ).order_by('name')
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ClientInfoView(APIView):
    """GET /api/bot/clients/?phone=&address= — поиск клиентов"""
    permission_classes = [IsCourier]

    def get(self, request):
        phone = request.query_params.get('phone', '')
        address = request.query_params.get('address', '')
        clients = Client.objects.all()
        if phone:
            clients = clients.filter(phone__icontains=phone)
        if address:
            clients = clients.filter(address__icontains=address)
        serializer = ClientSerializer(clients[:10], many=True)
        return Response(serializer.data)


# ─── Клиентский Mini App ──────────────────────────────────────────────────────

class ClientProductListView(APIView):
    """GET /api/bot/client/products/ — каталог для клиентов"""
    permission_classes = []

    def get(self, request):
        products = Product.objects.filter(
            type_product=Product.TypeProduct.WATER
        ).order_by('name')
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ClientOrderCreateView(APIView):
    """POST /api/bot/client/order/ — создать заказ от клиента"""
    permission_classes = []

    def post(self, request):
        # tg_id из заголовка или тела
        tg_id = request.data.get('client_tg_id') or request.headers.get('X-Telegram-ID')
        if not tg_id:
            return Response({'error': 'Не указан client_tg_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = Client.objects.get(tg_id=int(tg_id))
        except (Client.DoesNotExist, ValueError):
            return Response({'error': 'Клиент не найден. Зарегистрируйтесь в системе.'}, status=status.HTTP_404_NOT_FOUND)

        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        payment_type_raw = request.data.get('payment_type', 'CASH')
        note = request.data.get('note', '')
        address = request.data.get('address', '')

        # Маппинг строковых значений в choices модели
        payment_map = {
            'CASH': Order.PaymentType.CASH,
            'CARD': Order.PaymentType.CARD,
            'BONUS': Order.PaymentType.BONUS,
            # Уже правильные значения
            Order.PaymentType.CASH: Order.PaymentType.CASH,
            Order.PaymentType.CARD: Order.PaymentType.CARD,
            Order.PaymentType.BONUS: Order.PaymentType.BONUS,
        }
        payment_type = payment_map.get(payment_type_raw, Order.PaymentType.CASH)

        try:
            product = Product.objects.get(id=product_id)
        except (Product.DoesNotExist, TypeError):
            return Response({'error': 'Продукт не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Создаём заказ без рейса (trip=None — ждёт назначения курьера)
        from apps.logistics.models import OrderItem
        order = Order.objects.create(
            trip=None,
            client=client,
            payment_type=payment_type,
            status=Order.Status.PENDING,
            note=note,
        )
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
        )

        if address and address != client.address:
            client.address = address
            client.save(update_fields=['address'])

        return Response({
            'status': 'created',
            'message': 'Заказ создан и ожидает назначения курьера',
            'order_id': order.id,
            'product': product.name,
            'quantity': item.quantity,
            'price': item.price,
            'estimated_date': timezone.now().date().isoformat(),
        }, status=status.HTTP_201_CREATED)


class ClientOrderHistoryView(APIView):
    """GET /api/bot/client/orders/?tg_id=<id> — история заказов клиента"""
    permission_classes = []

    def get(self, request):
        tg_id = request.query_params.get('tg_id') or request.headers.get('X-Telegram-ID')
        if not tg_id:
            return Response({'error': 'Не указан tg_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = Client.objects.get(tg_id=int(tg_id))
        except (Client.DoesNotExist, ValueError):
            return Response({'error': 'Клиент не найден'}, status=status.HTTP_404_NOT_FOUND)

        orders = Order.objects.filter(client=client).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class ClientOrderStatusView(APIView):
    """GET /api/bot/client/order/<order_id>/status/"""
    permission_classes = []

    def get(self, request, order_id):
        tg_id = request.query_params.get('tg_id') or request.headers.get('X-Telegram-ID')
        if not tg_id:
            return Response({'error': 'Не указан tg_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = Client.objects.get(tg_id=int(tg_id))
        except (Client.DoesNotExist, ValueError):
            return Response({'error': 'Клиент не найден'}, status=status.HTTP_404_NOT_FOUND)

        try:
            order = Order.objects.get(id=order_id, client=client)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        courier_info = None
        if order.status == Order.Status.DELIVERED and order.assigned_courier:
            c = order.assigned_courier
            courier_info = {'id': c.id, 'full_name': c.full_name}

        # Собираем позиции заказа (поля product/quantity/price перенесены в OrderItem)
        items_data = [
            {
                'product': item.product.name,
                'quantity': item.quantity,
                'price': item.price,
            }
            for item in order.items.select_related('product').all()
        ]
        total_price = order.get_total_price()

        return Response({
            'order_id': order.id,
            'status': order.status,
            'status_display': order.get_status_display(),
            'items': items_data,
            'total_price': total_price,
            'payment_type': order.payment_type,
            'created_at': order.created_at,
            'delivered_at': order.delivered_at,
            'courier': courier_info,
        })


# ─── Регистрация клиента ──────────────────────────────────────────────────────

class ClientRegisterView(APIView):
    """POST /api/bot/client/register/ — регистрация нового клиента"""
    permission_classes = []

    def post(self, request):
        tg_id = request.data.get('tg_id') or request.headers.get('X-Telegram-ID')
        name = request.data.get('name', '')
        phone = request.data.get('phone', '')
        address = request.data.get('address', '')

        if not tg_id or not name or not phone:
            return Response({'error': 'Обязательные поля: tg_id, name, phone'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tg_id = int(tg_id)
        except ValueError:
            return Response({'error': 'tg_id должен быть числом'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, не зарегистрирован ли уже
        if Client.objects.filter(tg_id=tg_id).exists():
            client = Client.objects.get(tg_id=tg_id)
            return Response({
                'status': 'exists',
                'message': 'Клиент уже зарегистрирован',
                'client_id': client.id,
                'name': client.name,
            })

        if Client.objects.filter(phone=phone).exists():
            return Response({'error': 'Телефон уже используется'}, status=status.HTTP_400_BAD_REQUEST)

        client = Client.objects.create(
            tg_id=tg_id,
            name=name,
            phone=phone,
            address=address,
        )

        return Response({
            'status': 'created',
            'message': 'Клиент зарегистрирован',
            'client_id': client.id,
            'name': client.name,
        }, status=status.HTTP_201_CREATED)


# ─── Профиль клиента ──────────────────────────────────────────────────────────

class ClientProfileView(APIView):
    """GET /api/bot/client/profile/?tg_id=<id>"""
    permission_classes = []

    def get(self, request):
        tg_id = request.query_params.get('tg_id') or request.headers.get('X-Telegram-ID')
        if not tg_id:
            return Response({'error': 'Не указан tg_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = Client.objects.get(tg_id=int(tg_id))
        except (Client.DoesNotExist, ValueError):
            return Response({'error': 'Клиент не найден', 'registered': False}, status=status.HTTP_404_NOT_FOUND)

        serializer = ClientSerializer(client)
        return Response({'registered': True, **serializer.data})


# ─── Admin endpoints ──────────────────────────────────────────────────────────

class AdminStatsTodayView(APIView):
    """GET /api/bot/admin/stats/today/"""
    permission_classes = [IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        finance = Finance.objects.filter(date=today).first()
        active_shifts_count = CourierShift.objects.filter(
            date=today, status=CourierShift.Status.OPEN
        ).count()
        orders_today = Order.objects.filter(created_at__date=today).count()
        delivered_today = Order.objects.filter(
            delivered_at__date=today, status=Order.Status.DELIVERED
        ).count()

        return Response({
            'date': today.isoformat(),
            'finance': {
                'income': finance.income if finance else 0,
                'consumption': finance.consumption if finance else 0,
                'profit': finance.profit if finance else 0,
                'card_profit': finance.card_profit if finance else 0,
            },
            'active_shifts': active_shifts_count,
            'orders_today': orders_today,
            'delivered_today': delivered_today,
        })


class AdminShiftsView(APIView):
    """GET /api/bot/admin/shifts/"""
    permission_classes = [IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        shifts = CourierShift.objects.filter(
            date=today, status=CourierShift.Status.OPEN
        ).select_related('courier').order_by('courier__full_name')

        data = []
        for shift in shifts:
            orders_count = Order.objects.filter(trip__shift=shift).count()
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
    """GET /api/bot/admin/stock/alerts/"""
    permission_classes = [IsAdmin]

    def get(self, request):
        alerts = StockBalance.objects.filter(
            quantity__lt=10
        ).select_related('product').order_by('quantity')

        data = [{
            'product_id': a.product.id,
            'product_name': a.product.name,
            'product_type': a.product.type_product,
            'quantity': a.quantity,
            'last_received_date': a.last_received_date,
            'last_departure_date': a.last_departure_date,
        } for a in alerts]
        return Response(data)


class AdminOrdersRecentView(APIView):
    """GET /api/bot/admin/orders/recent/?limit=10"""
    permission_classes = [IsAdmin]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        orders = Order.objects.select_related(
            'client', 'assigned_courier', 'trip__shift__courier'
        ).prefetch_related('items__product').order_by('-created_at')[:limit]

        data = []
        for o in orders:
            items_data = [
                {
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'price': item.price,
                }
                for item in o.items.select_related('product').all()
            ]
            data.append({
                'id': o.id,
                'client_name': o.client.name if o.client else None,
                'client_phone': o.client.phone if o.client else None,
                'items': items_data,
                'total_price': o.get_total_price(),
                'payment_type': o.payment_type,
                'payment_type_display': o.get_payment_type_display(),
                'status': o.status,
                'status_display': o.get_status_display(),
                'assigned_courier_name': o.assigned_courier.full_name if o.assigned_courier else None,
                'courier_name': o.trip.shift.courier.full_name if o.trip and o.trip.shift else None,
                'created_at': o.created_at,
                'delivered_at': o.delivered_at,
            })
        return Response(data)


# ─── Устаревшие endpoints (410 Gone) ─────────────────────────────────────────

class CourierDeliveryListView(APIView):
    permission_classes = [IsCourier]
    def get(self, request):
        return Response({'error': 'Deprecated'}, status=status.HTTP_410_GONE)


class DeliveryConfirmationView(APIView):
    permission_classes = [IsCourier]
    def post(self, request):
        return Response({'error': 'Deprecated. Use /courier/orders/confirm/'}, status=status.HTTP_410_GONE)


class UpdateQuantityView(APIView):
    permission_classes = [IsCourier]
    def post(self, request):
        return Response({'error': 'Deprecated. Use /courier/orders/update-quantity/'}, status=status.HTTP_410_GONE)


class TodayDeliveriesView(APIView):
    permission_classes = [IsCourier]
    def get(self, request):
        return Response({'error': 'Deprecated'}, status=status.HTTP_410_GONE)


class MarkAsDeliveredView(APIView):
    permission_classes = [IsCourier]
    def post(self, request, delivery_id):
        return Response({'error': 'Deprecated'}, status=status.HTTP_410_GONE)


class PublicProductListView(APIView):
    permission_classes = []
    def get(self, request):
        products = Product.objects.all().order_by('type_product', 'name')
        return Response(ProductSerializer(products, many=True).data)


class ClientOrderView(APIView):
    permission_classes = []
    def post(self, request):
        return Response({'error': 'Deprecated. Use /client/order/'}, status=status.HTTP_410_GONE)
