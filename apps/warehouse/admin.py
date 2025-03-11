from django.contrib import admin
from apps.warehouse.models import StockBalance


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantitly', 'last_received_date', 'last_departure_date')
    search_fields = ('product__name',)
    list_filter = ('last_received_date', 'last_departure_date')
