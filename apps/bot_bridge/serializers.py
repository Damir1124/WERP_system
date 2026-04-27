from rest_framework import serializers
from apps.logistics.models import DeliveryJournal, DeliveryJournalProducts
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


class DeliveryJournalProductsSerializer(serializers.ModelSerializer):
    """Сериализатор для строки продукта в журнале доставки"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)

    class Meta:
        model = DeliveryJournalProducts
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 
                  'payment_type', 'payment_type_display', 'note']
        read_only_fields = ['price']  # цена рассчитывается автоматически


class DeliveryJournalSerializer(serializers.ModelSerializer):
    """Сериализатор для журнала доставки"""
    courier_name = serializers.CharField(source='courier.full_name', read_only=True)
    products = DeliveryJournalProductsSerializer(many=True, read_only=True)
    
    class Meta:
        model = DeliveryJournal
        fields = ['id', 'courier', 'courier_name', 'date', 'card_price', 
                  'total_price', 'products', 'created_at']
        read_only_fields = ['card_price', 'total_price', 'created_at']


class DeliveryJournalUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления журнала доставки (подтверждение доставки)"""
    class Meta:
        model = DeliveryJournal
        fields = ['id', 'date', 'card_price', 'total_price']
        read_only_fields = ['id', 'date', 'card_price', 'total_price']


class WorkerSerializer(serializers.ModelSerializer):
    """Сериализатор для сотрудника (курьера)"""
    class Meta:
        model = Worker
        fields = ['id', 'full_name', 'type_worker', 'date_for_payed', 'tg_id']


class DeliveryConfirmationSerializer(serializers.Serializer):
    """Сериализатор для подтверждения доставки"""
    delivery_journal_id = serializers.IntegerField()
    confirmed = serializers.BooleanField(default=True)
    actual_quantity = serializers.IntegerField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)


class QuantityUpdateSerializer(serializers.Serializer):
    """Сериализатор для изменения количества в строке журнала"""
    product_line_id = serializers.IntegerField()
    new_quantity = serializers.IntegerField(min_value=1)