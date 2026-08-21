from django.contrib import admin
from django.utils.html import format_html
from apps.warehouse.models import (
    Garage,
    WarehouseProduct, WarehouseStockBalance, WarehouseStockMovement,
    WarehouseInventoryAdjustment, ProductWarehouseMapping,
)
from apps.workers.models import Worker
from apps.dashboard.services.export_placeholder import ExportPlaceholderMixin


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


# ═══════════════════════════════════════════════════════════════════════════════
#  АВТОНОМНЫЙ КОНТУР СКЛАДСКИХ ПРОДУКТОВ
# ═══════════════════════════════════════════════════════════════════════════════


class ProductWarehouseMappingInline(admin.TabularInline):
    """Связь складского продукта с продуктами ассортимента (M2M с коэффициентом)"""
    model = ProductWarehouseMapping
    extra = 1
    fk_name = 'warehouse_product'
    verbose_name = 'Связь с продуктом ассортимента'
    verbose_name_plural = 'Связи с продуктами ассортимента'


@admin.register(WarehouseProduct)
class WarehouseProductAdmin(admin.ModelAdmin):
    """Административные продукты (автономный контур учёта)"""
    list_display = ('name', 'sku', 'unit', 'balance_quantity', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'sku')
    list_per_page = 20
    ordering = ('name',)
    inlines = [ProductWarehouseMappingInline]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = [
        ('Основная информация', {
            'fields': ['name', 'sku', 'unit'],
        }),
        ('Статус', {
            'fields': ['is_active'],
        }),
        ('Служебное', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    @admin.display(description='Остаток')
    def balance_quantity(self, obj):
        balance = getattr(obj, 'balance', None)
        if balance is None:
            return '—'
        if balance.quantity <= 0:
            color = '#d63031'
        elif balance.quantity < 10:
            color = '#fdcb6e'
        else:
            color = '#00b894'
        return format_html('<span style="color:{}; font-weight:bold">{}</span>', color, balance.quantity)


@admin.register(WarehouseStockBalance)
class WarehouseStockBalanceAdmin(admin.ModelAdmin):
    """Остатки складских продуктов (только просмотр)"""
    list_display = ('warehouse_product', 'quantity_colored', 'last_received_date', 'last_departure_date')
    search_fields = ('warehouse_product__name',)
    readonly_fields = ['warehouse_product', 'quantity', 'last_received_date', 'last_departure_date']
    list_per_page = 20
    ordering = ('warehouse_product__name',)

    @admin.display(description='Остаток')
    def quantity_colored(self, obj):
        if obj.quantity <= 0:
            color = '#d63031'
        elif obj.quantity < 10:
            color = '#fdcb6e'
        else:
            color = '#00b894'
        return format_html('<span style="color:{}; font-weight:bold">{}</span>', color, obj.quantity)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WarehouseStockMovement)
class WarehouseStockMovementAdmin(admin.ModelAdmin):
    """Журнал движений складских продуктов (только просмотр)"""
    list_display = ('warehouse_product', 'operation_type', 'quantity', 'created_at', 'note')
    list_filter = ('operation_type', 'created_at')
    search_fields = ('warehouse_product__name', 'note')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 25
    readonly_fields = ['warehouse_product', 'operation_type', 'quantity', 'note']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WarehouseInventoryAdjustment)
class WarehouseInventoryAdjustmentAdmin(admin.ModelAdmin):
    """Ручная корректировка остатков складских продуктов"""
    list_display = ('warehouse_product', 'adjustment_type', 'quantity', 'adjusted_by', 'created_at', 'reason_short')
    list_filter = ('adjustment_type', 'created_at')
    search_fields = ('warehouse_product__name', 'reason', 'note')
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    list_per_page = 20
    ordering = ('-created_at',)

    fieldsets = [
        ('Корректировка', {
            'fields': ['warehouse_product', 'adjustment_type', 'quantity'],
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


@admin.register(ProductWarehouseMapping)
class ProductWarehouseMappingAdmin(admin.ModelAdmin):
    """Связи продуктов ассортимента со складскими продуктами"""
    list_display = ('product', 'warehouse_product', 'coefficient')
    list_filter = ('product__type_product',)
    search_fields = ('product__name', 'warehouse_product__name')
    list_per_page = 20
    ordering = ('product__name',)