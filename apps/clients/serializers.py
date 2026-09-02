from rest_framework import serializers
from .models import Client, ClientAddress


class ClientAddressSerializer(serializers.ModelSerializer):
    """Сериализатор для адресов клиента"""
    
    class Meta:
        model = ClientAddress
        fields = ['id', 'label', 'address_text', 'latitude', 'longitude', 'last_used_at', 'created_at']
        read_only_fields = ['id', 'created_at']


class ClientSerializer(serializers.ModelSerializer):
    """Сериализатор для клиента с адресами"""
    addresses = ClientAddressSerializer(many=True, read_only=True)
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'phone', 'balans', 'note',
            'latitude', 'longitude', 'tg_id',
            'created_at', 'updated_at', 'addresses'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
