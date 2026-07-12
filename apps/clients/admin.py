from django.contrib import admin
from .models import Client, ClientAddress


class ClientAddressInline(admin.TabularInline):
    """Inline для отображения адресов клиента"""
    model = ClientAddress
    extra = 0
    max_num = 3
    fields = ['address_text', 'latitude', 'longitude', 'last_used_at']
    readonly_fields = ['last_used_at']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Оптимизация вида тб"""
    search_fields = ['name', 'phone', 'address']
    list_display = ['name', 'phone', 'address', 'balans', 'created_at']
    list_filter = ['created_at', 'balans']
    fields = ['name', 'phone', 'address', 'balans', 'note', 'latitude', 'longitude', 'tg_id']
    list_per_page = 20
    ordering = ['created_at']
    inlines = [ClientAddressInline]


@admin.register(ClientAddress)
class ClientAddressAdmin(admin.ModelAdmin):
    """Админка для адресов клиентов"""
    list_display = ['client', 'address_text', 'latitude', 'longitude', 'last_used_at', 'created_at']
    list_filter = ['last_used_at', 'created_at']
    search_fields = ['client__name', 'client__phone', 'address_text']
    readonly_fields = ['created_at']
    list_per_page = 20
    ordering = ['-last_used_at', '-created_at']
