from django.contrib import admin
from .models import DeliveryLogMove, DeliveryLog


class DeliveryLogMoveInline(admin.TabularInline):
    model = DeliveryLogMove
    extra = 1
    verbose_name = "Движение доставки"
    verbose_name_plural = "Движения доставки"


class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('courier', 'total_quantity', "total_sold", 'date')
    list_filter = ('courier', 'date')
    search_fields = ('courier__full_name',)
    ordering = ('-date',)
    date_hierarchy = 'date'
    inlines = [DeliveryLogMoveInline]
    readonly_fields = ('total_quantity', 'total_sold')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.check_total_quantity()


class DeliveryLogMoveAdmin(admin.ModelAdmin):
    list_display = ('delivery_log', 'action', 'quantity', 'date')
    list_filter = ('action', 'delivery_log__courier', 'date')
    search_fields = ('delivery_log__courier__full_name',)
    ordering = ('-date',)
    date_hierarchy = 'date'


admin.site.register(DeliveryLog, DeliveryLogAdmin)
admin.site.register(DeliveryLogMove, DeliveryLogMoveAdmin)

