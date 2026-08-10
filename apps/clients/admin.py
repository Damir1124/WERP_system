from django.contrib import admin
from .models import Client, ClientAddress


class ClientAddressInline(admin.TabularInline):
    """Inline для отображения адресов клиента"""
    model = ClientAddress
    extra = 0
    max_num = 3
    fields = ['address_text', 'latitude', 'longitude', 'last_used_at']
    readonly_fields = ['last_used_at']
    verbose_name = 'Адрес'
    verbose_name_plural = 'Адреса клиента'


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Удобное управление клиентами"""
    search_fields = ['name', 'phone', 'address', 'tg_id']
    list_display = [
        'name', 'phone', 'address', 'balans', 'orders_count',
        'tg_id', 'created_at', 'orders_link',
    ]
    list_filter = ['created_at', 'balans']
    list_per_page = 20
    ordering = ['-created_at']
    inlines = [ClientAddressInline]
    readonly_fields = ['created_at', 'updated_at', 'orders_link_inline']
    save_on_top = True

    fieldsets = [
        ('Основная информация', {
            'fields': ['name', 'phone', 'address', 'balans', 'note'],
        }),
        ('Геолокация', {
            'fields': ['latitude', 'longitude'],
            'classes': ['collapse'],
        }),
        ('Telegram', {
            'fields': ['tg_id'],
            'classes': ['collapse'],
        }),
        ('История заказов', {
            'fields': ['orders_link_inline'],
            'classes': ['collapse'],
        }),
        ('Служебное', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    @admin.display(description='Заказов')
    def orders_count(self, obj):
        from apps.logistics.models import Order
        return Order.objects.filter(client=obj).count()

    @admin.display(description='Заказы')
    def orders_link(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<a href="{}?client__id__exact={}" target="_blank">📋 Открыть</a>',
            '/admin/logistics/order/',
            obj.pk
        )

    @admin.display(description='История заказов')
    def orders_link_inline(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<a href="{}?client__id__exact={}" target="_blank" '
            'style="font-weight:600;">'
            'Открыть все заказы клиента →</a>',
            '/admin/logistics/order/',
            obj.pk
        )


@admin.register(ClientAddress)
class ClientAddressAdmin(admin.ModelAdmin):
    """Админка для адресов клиентов"""
    list_display = ['client', 'address_text', 'latitude', 'longitude', 'last_used_at', 'created_at']
    list_filter = ['last_used_at', 'created_at']
    search_fields = ['client__name', 'client__phone', 'address_text']
    readonly_fields = ['created_at']
    list_per_page = 20
    ordering = ['-last_used_at', '-created_at']
