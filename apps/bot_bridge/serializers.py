from rest_framework import serializers
from apps.logistics.models import CourierShift, CourierTrip, Order, OrderItem
from apps.clients.models import Client
from apps.products.models import Product
from apps.workers.models import Worker


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор для продукта"""
    type_product_display = serializers.CharField(source='get_type_product_display', read_only=True)
    # image_url: приоритет у загруженного файла (image), иначе внешний URL
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if obj.image:
            try:
                return obj.image.url
            except Exception:
                pass
        return obj.image_url or ''

    class Meta:
        model = Product
        fields = ['id', 'name', 'type_product', 'type_product_display', 'price',
                  'image_url', 'is_visible_in_catalog',
                  'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ClientSerializer(serializers.ModelSerializer):
    """Сериализатор для клиента"""
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone', 'balans', 'note',
                  'latitude', 'longitude', 'tg_id', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# Устаревшие сериализаторы DeliveryJournal/DeliveryJournalProducts удалены
# вместе с моделями. Внешние интерфейсы оперируют с моделями P0:
# Order / CourierTrip / CourierShift.


class WorkerSerializer(serializers.ModelSerializer):
    """Сериализатор для сотрудника (курьера)"""
    class Meta:
        model = Worker
        fields = ['id', 'full_name', 'worker_type', 'date_for_payed', 'tg_id', 'is_admin']


# Новые сериализаторы для моделей P0

class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор для позиции заказа (модель OrderItem)"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_type = serializers.CharField(source='product.type_product', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'product_name', 'product_type', 'quantity', 'price',
                  'exchange_qty', 'sell_with_qty', 'defective_qty']
        read_only_fields = ['price']

class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор для заказа (модель Order)"""
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    client_address = serializers.SerializerMethodField()
    delivery_address_display = serializers.SerializerMethodField()
    client_phone = serializers.CharField(source='client.phone', read_only=True, allow_null=True)
    latitude = serializers.DecimalField(source='delivery_latitude', max_digits=10, decimal_places=6, read_only=True, allow_null=True)
    longitude = serializers.DecimalField(source='delivery_longitude', max_digits=10, decimal_places=6, read_only=True, allow_null=True)
    delivery_address_text = serializers.CharField(read_only=True, allow_null=True)
    delivery_latitude = serializers.DecimalField(max_digits=10, decimal_places=6, read_only=True, allow_null=True)
    delivery_longitude = serializers.DecimalField(max_digits=10, decimal_places=6, read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    assigned_courier_name = serializers.CharField(source='assigned_courier.full_name', read_only=True, allow_null=True)
    created_by = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    minutes_ago = serializers.SerializerMethodField()

    def get_total_price(self, obj):
        return obj.get_total_price()
    
    def get_minutes_ago(self, obj):
        """Возвращает количество минут с момента создания заказа"""
        from django.utils import timezone
        if obj.created_at:
            delta = timezone.now() - obj.created_at
            return int(delta.total_seconds() / 60)
        return 0
    
    def get_created_by(self, obj):
        """Возвращает имя создателя заказа (курьер или система)"""
        # Если есть поле created_by_worker, используем его
        if obj.created_by_worker:
            return obj.created_by_worker.full_name
        # Если заказ в рейсе, значит его создал курьер этого рейса
        if obj.trip and obj.trip.shift and obj.trip.shift.courier:
            return obj.trip.shift.courier.full_name
        # Если заказ создан клиентом через Mini App (нет рейса)
        if not obj.trip and obj.client:
            return f"Клиент {obj.client.name}"
        # Если есть назначенный курьер (но нет рейса)
        if obj.assigned_courier:
            return obj.assigned_courier.full_name
        return "Система"

    def get_client_address(self, obj):
        """Человекочитаемый адрес: текст, Location или 'Адрес не указан'."""
        return obj.display_address()

    def get_delivery_address_display(self, obj):
        """Алиас display_address для совместимости."""
        return obj.display_address()

    class Meta:
        model = Order
        fields = ['id', 'display_number', 'human_number', 'trip', 'client', 'client_name', 'client_address', 'client_phone',
                  'latitude', 'longitude',
                  'delivery_address_text', 'delivery_address_display',
                  'delivery_latitude', 'delivery_longitude',
                  'payment_type', 'payment_type_display',
                  'status', 'status_display',
                  'assigned_courier', 'assigned_courier_name', 'created_by', 'note', 'created_at', 'delivered_at',
                  'items', 'total_price', 'minutes_ago']
        read_only_fields = ['created_at', 'delivered_at']


class OrderCreateModelSerializer(serializers.ModelSerializer):
    """Сериализатор для создания заказа (для курьера) с поддержкой многопозиционной структуры"""
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        write_only=True,
        help_text="Список позиций заказа. Каждая позиция: {'product_id': id, 'quantity': int}"
    )
    
    # Поля для создания/поиска клиента
    client_id = serializers.IntegerField(required=False, write_only=True, help_text="ID клиента (если найден)")
    client_phone = serializers.CharField(required=False, write_only=True, help_text="Номер телефона клиента")
    client_address = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True, help_text="Адрес доставки")
    client_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True, help_text="ФИО клиента")
    client_lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True, write_only=True, help_text="Широта")
    client_lon = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True, write_only=True, help_text="Долгота")
    
    class Meta:
        model = Order
        fields = ['trip', 'client', 'client_id', 'client_phone', 'client_address', 'client_name',
                  'client_lat', 'client_lon', 'payment_type', 'note', 'items']
        extra_kwargs = {
            'trip': {'required': False},  # Рейс опционален (может быть создан без рейса)
            'client': {'required': False},  # Опционально, т.к. можем создать по телефону
            'payment_type': {'required': True},
        }
    
    def validate_payment_type(self, value):
        if not value:
            return value
        const_to_value = {
            'CASH': 'CH',
            'CARD': 'CD',
            'BONUS': 'BS',
        }
        if value in Order.PaymentType.values:
            return value
        if value in const_to_value:
            return const_to_value[value]
        raise serializers.ValidationError(
            f"Недопустимый тип оплаты '{value}'. Допустимые значения: {list(Order.PaymentType.values)} "
            f"или имена констант: {list(const_to_value.keys())}"
        )
    
    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Заказ должен содержать хотя бы одну позицию")
        for idx, item in enumerate(items):
            # Поддержка обоих форматов: 'product' и 'product_id'
            product_id = item.get('product_id') or item.get('product')
            if not product_id:
                raise serializers.ValidationError(f"Позиция {idx}: отсутствует поле 'product_id' или 'product'")
            
            # Нормализуем к 'product'
            item['product'] = product_id
            if 'product_id' in item:
                del item['product_id']
            
            if 'quantity' not in item or item['quantity'] < 1:
                raise serializers.ValidationError(f"Позиция {idx}: поле 'quantity' должно быть положительным числом")
            
            # Устанавливаем значения по умолчанию для контейнерных операций
            quantity = item['quantity']
            item.setdefault('exchange_qty', quantity)
            item.setdefault('sell_with_qty', 0)
            item.setdefault('defective_qty', 0)
            
            # Проверяем существование продукта
            from apps.products.models import Product
            try:
                Product.objects.get(id=item['product'])
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Позиция {idx}: продукт с id {item['product']} не найден")
        return items
    
    def validate(self, data):
        """Проверка, что рейс принадлежит текущему курьеру"""
        request = self.context.get('request')
        if request and hasattr(request, 'courier'):
            courier = request.courier
            trip = data.get('trip')
            if trip and trip.shift.courier and trip.shift.courier != courier:
                raise serializers.ValidationError(
                    "Рейс не принадлежит текущему курьеру"
                )
        return data
    
    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Creating order with validated_data: {validated_data}")
        
        items_data = validated_data.pop('items')
        
        # Обработка данных клиента
        client_id = validated_data.pop('client_id', None)
        client_phone = validated_data.pop('client_phone', None)
        client_address = validated_data.pop('client_address', None)
        client_name = validated_data.pop('client_name', None)
        client_lat = validated_data.pop('client_lat', None)
        client_lon = validated_data.pop('client_lon', None)
        
        client = None
        from apps.clients.models import Client
        
        # Логика клиента
        if client_id:
            # Клиент найден на фронте
            try:
                client = Client.objects.get(id=client_id)
                logger.info(f"Client found by ID: {client_id}")
                # НЕ обновляем client.address - используем ClientAddress
                    
            except Client.DoesNotExist:
                logger.error(f"Client with ID {client_id} not found")
                raise serializers.ValidationError(f"Клиент с ID {client_id} не найден")
                
            validated_data['client'] = client
            
        elif client_phone:
            # Новый клиент или поиск по телефону
            # Нормализация телефона
            phone = client_phone.replace(' ', '').replace('-', '').replace('+', '')
            
            # Приводим к формату 998XXXXXXXXX (12 символов)
            if len(phone) == 9:
                phone = '998' + phone
            elif phone.startswith('998') and len(phone) == 12:
                pass
            elif phone.startswith('8') and len(phone) == 10:
                phone = '998' + phone[1:]
            
            phone = phone[:12]
            logger.info(f"Normalized phone: {client_phone} -> {phone}")
            
            # Поиск или создание клиента
            client, created = Client.objects.get_or_create(
                phone=phone,
                defaults={
                    'name': client_name or f'Клиент {phone[-4:]}',
                }
            )
            
            # НЕ обновляем latitude, longitude
            # Адреса управляются через ClientAddress API
            
            validated_data['client'] = client
            logger.info(f"Client {'created' if created else 'found'}: id={client.id}, phone={client.phone}")
        
        # --- Привязка адреса доставки (ClientAddress) ---
        from apps.clients.models import ClientAddress
        from django.utils import timezone

        delivery_address = None
        address_text = (client_address or '').strip()
        if client and (address_text or client_lat or client_lon):
            # Ищем существующий подходящий адрес (по тексту, затем по координатам)
            existing = None
            if address_text:
                existing = client.addresses.filter(address_text=address_text).first()
            if not existing and client_lat and client_lon:
                existing = client.addresses.filter(
                    latitude=client_lat, longitude=client_lon
                ).first()
            if existing:
                delivery_address = existing
                changed = False
                if address_text and existing.address_text != address_text:
                    existing.address_text = address_text
                    changed = True
                if client_lat and existing.latitude != client_lat:
                    existing.latitude = client_lat
                    changed = True
                if client_lon and existing.longitude != client_lon:
                    existing.longitude = client_lon
                    changed = True
                if changed or not existing.last_used_at:
                    existing.last_used_at = timezone.now()
                    existing.save()
            else:
                delivery_address = ClientAddress.objects.create(
                    client=client,
                    address_text=address_text,
                    latitude=client_lat,
                    longitude=client_lon,
                    last_used_at=timezone.now(),
                )
                # Ограничиваем количество адресов клиента тремя (не трогая привязанные к заказам)
                extra = client.addresses.count()
                if extra > 3:
                    old_ids = list(
                        client.addresses
                        .exclude(id=delivery_address.id)  # не удаляем только что созданный/привязанный
                        .filter(orders__isnull=True)
                        .order_by('last_used_at', 'created_at')
                        .values_list('id', flat=True)[:extra - 3]
                    )
                    if old_ids:
                        ClientAddress.objects.filter(id__in=old_ids).delete()

        validated_data['delivery_address'] = delivery_address

        # --- Снимок адреса прямо в заказ (история доставки не зависит от ClientAddress) ---
        if delivery_address:
            validated_data['delivery_address_text'] = delivery_address.address_text
            validated_data['delivery_latitude'] = delivery_address.latitude
            validated_data['delivery_longitude'] = delivery_address.longitude
        else:
            # Адрес не привязан к ClientAddress — сохраняем хотя бы сырые данные из запроса
            validated_data['delivery_address_text'] = address_text
            validated_data['delivery_latitude'] = client_lat
            validated_data['delivery_longitude'] = client_lon

        # НЕ назначаем курьера автоматически - заказ должен попасть в пул
        # Курьер возьмёт его из пула вручную
        
        # Получаем курьера из контекста
        request = self.context.get('request')
        courier = request.courier if request and hasattr(request, 'courier') else None
        
        # Добавляем создателя заказа
        if courier:
            validated_data['created_by_worker'] = courier
        
        # Создаём заказ через сервис (автоматически проставляет display_number)
        from apps.logistics.services import create_order_with_display_number
        order = create_order_with_display_number(**validated_data)
        logger.info(f"Created order id={order.id}, display_number={order.display_number}, created_by={courier.full_name if courier else 'Unknown'}")
        
        # Создаём позиции заказа
        for idx, item_data in enumerate(items_data):
            product_id = item_data.pop('product')
            product = Product.objects.get(id=product_id)
            logger.info(f"Creating order item {idx}: product={product_id}, quantity={item_data.get('quantity')}")
            order_item = OrderItem.objects.create(order=order, product=product, **item_data)
            logger.info(f"Created order item id={order_item.id}, quantity={order_item.quantity}")
        
        return order


class CourierTripSerializer(serializers.ModelSerializer):
    """Сериализатор для рейса курьера"""
    shift_id = serializers.IntegerField(source='shift.id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    orders = OrderSerializer(many=True, read_only=True)
    
    class Meta:
        model = CourierTrip
        fields = ['id', 'shift', 'shift_id', 'full_loaded', 'full_returned', 
                  'status', 'status_display', 'started_at', 'finished_at', 'orders']
        read_only_fields = ['started_at', 'finished_at']


class CourierShiftSerializer(serializers.ModelSerializer):
    """Сериализатор для смены курьера"""
    courier_name = serializers.CharField(source='courier.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    trips = CourierTripSerializer(many=True, read_only=True)
    
    class Meta:
        model = CourierShift
        fields = ['id', 'courier', 'courier_name', 'date', 'status', 'status_display',
                  'cash_total', 'card_total', 'opened_at', 'closed_at', 'trips']
        read_only_fields = ['opened_at', 'closed_at']


# Сериализаторы для действий (подтверждение, изменение количества и т.д.)

class OrderConfirmationSerializer(serializers.Serializer):
    """Сериализатор для подтверждения заказа (новый, для P0) с поддержкой многопозиционных данных о таре"""
    order_id = serializers.IntegerField()
    confirmed = serializers.BooleanField(default=True)
    note = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Массив позиций с данными о таре: [{'item_id': int, 'exchange_qty': int, 'sell_with_qty': int, 'defective_qty': int}]"
    )
    new_items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Новые позиции, добавленные курьером: [{'product_id': int, 'quantity': int}]"
    )

    def validate_items(self, value):
        """Валидация массива позиций с данными о таре и количестве"""
        if not value:
            return []
        
        validated_items = []
        for item in value:
            if 'item_id' not in item:
                raise serializers.ValidationError("Каждая позиция должна содержать 'item_id'")
            
            # Проверяем, что позиция существует
            try:
                order_item = OrderItem.objects.get(id=item['item_id'])
            except OrderItem.DoesNotExist:
                raise serializers.ValidationError(f"Позиция с ID {item['item_id']} не найдена")
            
            # Определяем тип продукта
            from apps.products.models import Product
            is_bottle20l = order_item.product.type_product == Product.TypeProduct.BOTTLE_20L
            is_water = order_item.product.type_product == Product.TypeProduct.WATER
            
            # Для продуктов BOTTLE_20L и WATER поля тары обязательны, для остальных игнорируем
            if is_bottle20l or is_water:
                # Проверяем, что переданы поля тары (опционально, но если не переданы, будут 0)
                exchange_qty = item.get('exchange_qty', 0)
                sell_with_qty = item.get('sell_with_qty', 0)
                defective_qty = item.get('defective_qty', 0)
                
                # Инварианты согласно ТЗ
                if exchange_qty < 0:
                    raise serializers.ValidationError(f"Позиция {item['item_id']}: exchange_qty не может быть отрицательным")
                if sell_with_qty < 0:
                    raise serializers.ValidationError(f"Позиция {item['item_id']}: sell_with_qty не может быть отрицательным")
                if defective_qty < 0:
                    raise serializers.ValidationError(f"Позиция {item['item_id']}: defective_qty не может быть отрицательным")
                
                # Проверяем, что продажа с тарой не превышает обмен
                if sell_with_qty > exchange_qty:
                    raise serializers.ValidationError(
                        f"Позиция {item['item_id']}: продажа с тарой ({sell_with_qty}) "
                        f"не может превышать обмен ({exchange_qty})"
                    )
                
                # ВАЖНО: quantity - это плановое количество, оно НЕ пересчитывается!
                # exchange_qty, sell_with_qty, defective_qty - это детализация операций с тарой,
                # но они НЕ влияют на quantity (плановое количество воды в заказе).
                # Проверка exchange_qty != 0 будет выполнена во вью при confirmed=True
            else:
                # Для остальных продуктов поля тары игнорируются (устанавливаем в 0)
                exchange_qty = 0
                sell_with_qty = 0
                defective_qty = 0
                # Количество может быть изменено через quantity
                new_quantity = item.get('quantity')
                if new_quantity is not None:
                    if new_quantity < 1:
                        raise serializers.ValidationError(f"Позиция {item['item_id']}: количество должно быть >= 1")
                    quantity = new_quantity
                else:
                    quantity = order_item.quantity
            
            validated_item = {
                'item_id': item['item_id'],
                'exchange_qty': exchange_qty,
                'sell_with_qty': sell_with_qty,
                'defective_qty': defective_qty,
                'is_bottle20l': is_bottle20l,
                'is_water': is_water,
                'product_type': order_item.product.type_product,
            }
            
            # Для не-водных продуктов можем передать quantity если оно изменилось
            if not (is_bottle20l or is_water):
                new_quantity = item.get('quantity')
                if new_quantity is not None and new_quantity >= 1:
                    validated_item['quantity'] = new_quantity
            
            validated_items.append(validated_item)
        
        return validated_items

    def validate_new_items(self, value):
        """Валидация массива новых позиций, добавленных курьером"""
        if not value:
            return []
        
        from apps.products.models import Product
        
        validated_new_items = []
        for idx, item in enumerate(value):
            product_id = item.get('product_id')
            if not product_id:
                raise serializers.ValidationError(f"new_items[{idx}]: 'product_id' обязателен")
            
            # Проверяем, что продукт существует
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"new_items[{idx}]: продукт с ID {product_id} не найден")
            
            # Проверяем количество
            quantity = item.get('quantity', 1)
            if not isinstance(quantity, int) or quantity < 1:
                raise serializers.ValidationError(
                    f"new_items[{idx}]: quantity должен быть целым числом >= 1"
                )
            
            validated_new_items.append({
                'product_id': product_id,
                'product': product,
                'quantity': quantity,
                'price': product.price,
            })
        
        return validated_new_items


class OrderQuantityUpdateSerializer(serializers.Serializer):
    """Сериализатор для изменения количества в заказе (новый) с поддержкой многопозиционной структуры"""
    item_id = serializers.IntegerField(help_text="ID позиции заказа (OrderItem)")
    new_quantity = serializers.IntegerField(min_value=1)
    container_data = serializers.DictField(
        required=False,
        default=dict,
        help_text="Данные о таре для позиции: {'exchange_qty': int, 'sell_with_qty': int, 'defective_qty': int}"
    )

    def validate(self, data):
        """Валидация данных с проверкой позиции и операций с тарой"""
        item_id = data.get('item_id')
        new_quantity = data.get('new_quantity')
        container_data = data.get('container_data', {})
        
        # Проверяем, что позиция существует
        try:
            order_item = OrderItem.objects.get(id=item_id)
        except OrderItem.DoesNotExist:
            raise serializers.ValidationError(f"Позиция с ID {item_id} не найдена")
        
        # Проверяем, что заказ еще не доставлен
        if order_item.order.status == Order.Status.DELIVERED:
            raise serializers.ValidationError("Нельзя изменить количество в доставленном заказе")
        
        # Валидируем данные о таре
        exchange_qty = max(0, container_data.get('exchange_qty', 0))
        sell_with_qty = max(0, container_data.get('sell_with_qty', 0))
        defective_qty = max(0, container_data.get('defective_qty', 0))
        
        # Проверяем, что сумма операций с тарой не превышает новое количество
        total_container_qty = exchange_qty + sell_with_qty + defective_qty
        if total_container_qty > new_quantity:
            raise serializers.ValidationError(
                f"Сумма операций с тарой ({total_container_qty}) превышает новое количество ({new_quantity})"
            )
        
        # Проверяем, что продажа с тарой не превышает обмен
        if sell_with_qty > exchange_qty:
            raise serializers.ValidationError(
                f"Продажа с тарой ({sell_with_qty}) не может превышать обмен ({exchange_qty})"
            )
        
        # Добавляем валидированные данные о таре
        data['container_data'] = {
            'exchange_qty': exchange_qty,
            'sell_with_qty': sell_with_qty,
            'defective_qty': defective_qty
        }
        
        return data


