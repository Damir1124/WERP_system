from rest_framework import serializers
from apps.logistics.models import CourierShift, CourierTrip, Order
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

class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор для заказа (модель Order)"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    container_op_display = serializers.CharField(source='get_container_op_display', read_only=True)
    assigned_courier_name = serializers.CharField(source='assigned_courier.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Order
        fields = ['id', 'trip', 'client', 'client_name', 'product', 'product_name',
                  'quantity', 'price', 'payment_type', 'payment_type_display',
                  'status', 'status_display', 'container_op', 'container_op_display',
                  'assigned_courier', 'assigned_courier_name', 'note', 'created_at', 'delivered_at']
        read_only_fields = ['price', 'created_at', 'delivered_at']


class OrderCreateModelSerializer(serializers.ModelSerializer):
    """Сериализатор для создания заказа (для курьера)"""
    class Meta:
        model = Order
        fields = ['trip', 'client', 'product', 'quantity', 'payment_type', 'container_op', 'note']
        extra_kwargs = {
            'trip': {'required': True},
            'client': {'required': True},
            'product': {'required': True},
            'quantity': {'required': True, 'min_value': 1},
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
    
    def validate_container_op(self, value):
        if not value:
            return value
        const_to_value = {
            'EXCHANGE': 'EX',
            'SELL_WITH': 'SW',
            'DEFECTIVE': 'DF',
        }
        if value in Order.ContainerOp.values:
            return value
        if value in const_to_value:
            return const_to_value[value]
        raise serializers.ValidationError(
            f"Недопустимая операция с тарой '{value}'. Допустимые значения: {list(Order.ContainerOp.values)} "
            f"или имена констант: {list(const_to_value.keys())}"
        )
    
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
    """Сериализатор для подтверждения заказа (новый, для P0)"""
    order_id = serializers.IntegerField()
    confirmed = serializers.BooleanField(default=True)
    container_op = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_container_op(self, value):
        if not value:
            return None
        # Маппинг имен констант на значения
        const_to_value = {
            'EXCHANGE': 'EX',
            'SELL_WITH': 'SW',
            'DEFECTIVE': 'DF',
        }
        # Если значение уже является допустимым (EX, SW, DF), оставляем как есть
        if value in Order.ContainerOp.values:
            return value
        # Если это имя константы, преобразуем
        if value in const_to_value:
            return const_to_value[value]
        # Иначе ошибка
        raise serializers.ValidationError(
            f"Значение '{value}' недопустимо. Допустимые значения: {list(Order.ContainerOp.values)} "
            f"или имена констант: {list(const_to_value.keys())}"
        )


class QuantityUpdateSerializer(serializers.Serializer):
    """Сериализатор для изменения количества в строке журнала (старый)"""
    product_line_id = serializers.IntegerField()
    new_quantity = serializers.IntegerField(min_value=1)


class OrderQuantityUpdateSerializer(serializers.Serializer):
    """Сериализатор для изменения количества в заказе (новый)"""
    order_id = serializers.IntegerField()
    new_quantity = serializers.IntegerField(min_value=1)


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
