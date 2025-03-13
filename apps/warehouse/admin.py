from django.contrib import admin
from apps.warehouse.models import StockBalance, StockMovement, Garage
from apps.workers.models import Worker, WorkerType

@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantitly', 'last_received_date', 'last_departure_date')
    search_fields = ('product__name',)
    list_filter = ('last_received_date', 'last_departure_date')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('sold_product', 'operation_type', 'quantity', 'data', 'note')
    search_fields = ('sold_product__name', 'note')
    list_filter = ('operation_type', 'data')
    ordering = ('-data',)
    list_editable = ('quantity', 'note')


@admin.register(Garage)
class GarageAdmin(admin.ModelAdmin):
    list_display = ('vehicle_name', 'milage', 'year', 'courier')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "courier":
            kwargs["queryset"] = Worker.objects.filter(worker_type=WorkerType.COURIER)  # Фильтруем по типу курьер
        return super().formfield_for_foreignkey(db_field, request, **kwargs)