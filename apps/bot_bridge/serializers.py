from rest_framework import serializers
from apps.logistics.models import CourierShift, CourierTrip, Order, OrderItem
from apps.clients.models import Client
from apps.products.models import Product
from apps.workers.models import Worker


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор для продукта"""
    type_product_display = serializers.CharField(source='get_type_product_display', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'type_product', 'type_product_display', 'price', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ClientSerializer(serializers.ModelSerializer):
    """Сериализатор для клиента"""
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone', 'address', 'balans', 'note', 
                  'latitude', 'longitude', 'tg_id', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# Устаревшие сериализаторы DeliveryJournal/DeliveryJournalProducts удалены.
# Внешние интерфейсы теперь оперируют с моделями P0: Order / CourierTrip / CourierShift.


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
    client_name = serializers.CharField(source='client.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    assigned_courier_name = serializers.CharField(source='assigned_courier.full_name', read_only=True, allow_null=True)
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj):
        return obj.get_total_price()

    class Meta:
        model = Order
        fields = ['id', 'trip', 'client', 'client_name',
                  'payment_type', 'payment_type_display',
                  'status', 'status_display',
                  'assigned_courier', 'assigned_courier_name', 'note', 'created_at', 'delivered_at',
                  'items', 'total_price']
        read_only_fields = ['created_at', 'delivered_at']


class OrderCreateModelSerializer(serializers.ModelSerializer):
    """Сериализатор для создания заказа (для курьера) с поддержкой многопозиционной структуры"""
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        write_only=True,
        help_text="Список позиций заказа. Каждая позиция: {'product': id, 'quantity': int, 'exchange_qty': int, 'sell_with_qty': int, 'defective_qty': int}"
    )
    
    class Meta:
        model = Order
        fields = ['trip', 'client', 'payment_type', 'note', 'items']
        extra_kwargs = {
            'trip': {'required': True},
            'client': {'required': True},
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
            if 'product' not in item:
                raise serializers.ValidationError(f"Позиция {idx}: отсутствует поле 'product'")
            if 'quantity' not in item or item['quantity'] < 1:
                raise serializers.ValidationError(f"Позиция {idx}: поле 'quantity' должно быть положительным числом")
            
            # Устанавливаем значения по умолчанию для контейнерных операций
            # По умолчанию весь quantity считается обменом (exchange_qty)
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
            if trip and trip.shift.courier != courier:
                raise serializers.ValidationError(
                    "Рейс не принадлежит текущему курьеру"
                )
        return data
    
    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Creating order with validated_data: {validated_data}")
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        logger.info(f"Created order id={order.id}")
        for idx, item_data in enumerate(items_data):
            # item_data['product'] приходит как int (ID) — нужно получить объект
            product_id = item_data.pop('product')
            product = Product.objects.get(id=product_id)
            logger.info(f"Creating order item {idx}: product={product_id}, quantity={item_data.get('quantity')}, exchange_qty={item_data.get('exchange_qty')}, sell_with_qty={item_data.get('sell_with_qty')}, defective_qty={item_data.get('defective_qty')}")
            order_item = OrderItem.objects.create(order=order, product=product, **item_data)
            logger.info(f"Created order item id={order_item.id}, quantity={order_item.quantity}, exchange_qty={order_item.exchange_qty}")
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

class DeliveryConfirmationSerializer(serializers.Serializer):
    """Сериализатор для подтверждения доставки (старый, для обратной совместимости)"""
    delivery_journal_id = serializers.IntegerField()
    confirmed = serializers.BooleanField(default=True)
    actual_quantity = serializers.IntegerField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)


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
                
                # Для BOTTLE_20L и WATER quantity не передается, а вычисляется как сумма контейнерных операций
                # Игнорируем переданное quantity, если есть
                quantity = exchange_qty + sell_with_qty + defective_qty
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
                'quantity': quantity if not (is_bottle20l or is_water) else None,
                'is_bottle20l': is_bottle20l,
                'is_water': is_water,
                'product_type': order_item.product.type_product,
            }
            
            validated_items.append(validated_item)
        
        return validated_items


class QuantityUpdateSerializer(serializers.Serializer):
    """Сериализатор для изменения количества в строке журнала (старый)"""
    product_line_id = serializers.IntegerField()
    new_quantity = serializers.IntegerField(min_value=1)


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


class OrderCreateSerializer(serializers.Serializer):
    """Сериализатор для создания заказа через Telegram Mini App"""
    client_tg_id = serializers.IntegerField(required=True, help_text="Telegram ID клиента")
    product_id = serializers.IntegerField(required=True, help_text="ID продукта")
    quantity = serializers.IntegerField(min_value=1, default=1, help_text="Количество")
    address = serializers.CharField(required=False, allow_blank=True, help_text="Адрес доставки (если отличается от сохраненного)")
    note = serializers.CharField(required=False, allow_blank=True, help_text="Примечание к заказу")
    
    def validate_client_tg_id(self, value):
        """Проверяем, что клиент с таким tg_id существует"""
        from apps.clients.models import Client
        try:
            client = Client.objects.get(tg_id=value)
        except Client.DoesNotExist:
            raise serializers.ValidationError("Клиент с указанным Telegram ID не найден")
        return value
    
    def validate_product_id(self, value):
        """Проверяем, что продукт существует"""
        from apps.products.models import Product
        try:
            product = Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Продукт не найден")
        return value
