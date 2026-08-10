from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Удобное управление товарами"""
    list_display = ('name', 'type_product', 'price', 'track_inventory', 'created_at', 'updated_at')
    list_filter = ('type_product', 'track_inventory', 'created_at')
    search_fields = ('name',)
    list_editable = ('track_inventory',)  # цена не редактируется из списка (опасно массово)
    ordering = ('type_product', 'name')
    list_per_page = 20
    save_on_top = True
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = [
        ('Основная информация', {
            'fields': ['name', 'type_product', 'price'],
        }),
        ('Учёт', {
            'fields': ['track_inventory'],
            'classes': ['collapse'],
        }),
        ('Служебное', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление товаров, которые были в заказах (ломает историю)."""
        if obj is not None:
            from apps.logistics.models import OrderItem
            if OrderItem.objects.filter(product=obj).exists():
                return False
        return super().has_delete_permission(request, obj)
