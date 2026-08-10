from django.contrib import admin
from django.utils.html import format_html
from apps.warehouse.models import StockBalance, StockMovement, Garage, InventoryAdjustment
from apps.workers.models import Worker
from apps.dashboard.services.export_placeholder import ExportPlaceholderMixin


# ─── Остатки склада ──────────────────────────────────────────────────────────


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    """Остатки товаров на складе (только просмотр, редактирование через InventoryAdjustment)"""
    list_display = ('product', 'quantity_colored', 'last_received_date', 'last_departure_date')
    list_filter = ('product__type_product', 'last_received_date', 'last_departure_date')
    search_fields = ('product__name',)
    readonly_fields = ['product', 'quantity', 'last_departure_date', 'last_received_date']
    list_per_page = 20
    ordering = ('product__type_product', 'product__name')

    fieldsets = [
        ('Информация об остатке', {
            'fields': ['product', 'quantity'],
        }),
        ('Даты', {
            'fields': ['last_received_date', 'last_departure_date'],
            'classes': ['collapse'],
        }),
    ]

    @admin.display(description='Остаток')
    def quantity_colored(self, obj):
        """Цветовая индикация остатка"""
        if obj.quantity <= 0:
            color = '#d63031'
        elif obj.quantity < 10:
            color = '#fdcb6e'
        else:
            color = '#00b894'
        return format_html('<span style="color:{}; font-weight:bold">{}</span>', color, obj.quantity)

    def has_add_permission(self, request):
        """Запрещаем ручное создание остатков (создаются автоматически)"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление остатков"""
        return False


# ─── Движения склада ─────────────────────────────────────────────────────────


@admin.register(StockMovement)
class StockMovementAdmin(ExportPlaceholderMixin, admin.ModelAdmin):
    """Лог всех движений на складе (только просмотр)"""
    list_display = ('sold_product', 'operation_type', 'quantity', 'data', 'contract_link', 'note')
    list_filter = ('operation_type', 'data')
    search_fields = ('sold_product__name', 'note')
    ordering = ('-data',)
    date_hierarchy = 'data'
    list_per_page = 25
    readonly_fields = ['sold_product', 'operation_type', 'quantity', 'contract', 'note']

    fieldsets = [
        ('Информация о движении', {
            'fields': ['sold_product', 'operation_type', 'quantity'],
        }),
        ('Основание', {
            'fields': ['contract', 'note'],
            'classes': ['collapse'],
        }),
    ]

    @admin.display(description='Контракт')
    def contract_link(self, obj):
        if obj.contract:
            return format_html(
                '<a href="{}">{}</a>',
                f'/admin/accounting/contract/{obj.contract.id}/change/',
                obj.contract.description[:50]
            )
        return '—'

    def has_add_permission(self, request):
        """Запрещаем ручное создание движений (создаются бизнес-логикой)"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление движений"""
        return False


# ─── Автомобили ──────────────────────────────────────────────────────────────


@admin.register(Garage)
class GarageAdmin(admin.ModelAdmin):
    """Учёт транспортных средств"""
    list_display = ('vehicle_name', 'plate_number', 'milage', 'year', 'courier')
    search_fields = ('vehicle_name', 'plate_number', 'courier__full_name')
    list_per_page = 20
    ordering = ('vehicle_name',)

    fieldsets = [
        ('Информация об автомобиле', {
            'fields': ['vehicle_name', 'plate_number', 'milage', 'year'],
        }),
        ('Привязка к курьеру', {
            'fields': ['courier'],
        }),
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'courier':
            kwargs['queryset'] = Worker.objects.filter(worker_type=Worker.WorkerType.COURIER)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ─── Корректировки инвентаря ─────────────────────────────────────────────────


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    """Ручная корректировка остатков склада"""
    list_display = ('product', 'adjustment_type', 'quantity', 'adjusted_by', 'created_at', 'reason_short')
    list_filter = ('adjustment_type', 'created_at', 'product__type_product')
    search_fields = ('product__name', 'reason', 'note')
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    list_per_page = 20
    ordering = ('-created_at',)

    fieldsets = [
        ('Корректировка', {
            'fields': ['product', 'adjustment_type', 'quantity'],
        }),
        ('Обоснование', {
            'fields': ['reason', 'note', 'adjusted_by'],
        }),
        ('Служебное', {
            'fields': ['created_at'],
            'classes': ['collapse'],
        }),
    ]

    @admin.display(description='Причина')
    def reason_short(self, obj):
        return obj.reason[:75] + '...' if len(obj.reason) > 75 else obj.reason