from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Удобное управление товарами"""
    list_display = ('name', 'type_product', 'price', 'image_preview', 'is_visible_in_catalog', 'track_inventory', 'created_at', 'updated_at')
    list_filter = ('type_product', 'is_visible_in_catalog', 'track_inventory', 'created_at')
    search_fields = ('name',)
    list_display_links = ('name',)
    list_editable = ('price', 'is_visible_in_catalog', 'track_inventory')
    ordering = ('type_product', 'name')
    list_per_page = 20
    save_on_top = True
    readonly_fields = ('created_at', 'updated_at', 'image_preview')

    fieldsets = [
        ('Основная информация', {
            'fields': ['name', 'type_product', 'price'],
        }),
        ('Фото товара', {
            'fields': ['image', 'image_url', 'image_preview'],
        }),
        ('Каталог', {
            'fields': ['is_visible_in_catalog'],
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

    def image_preview(self, obj):
        """Миниатюра фото товара в списке и на форме."""
        url = None
        if obj.image:
            url = obj.image.url
        elif obj.image_url:
            url = obj.image_url
        if not url:
            return '—'
        return f'<img src="{url}" style="max-height:50px;max-width:50px;border-radius:6px;object-fit:cover;" />'
    image_preview.short_description = 'Фото'
    image_preview.allow_tags = True

    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление товаров, которые были в заказах (ломает историю)."""
        if obj is not None:
            from apps.logistics.models import OrderItem
            if OrderItem.objects.filter(product=obj).exists():
                return False
        return super().has_delete_permission(request, obj)
