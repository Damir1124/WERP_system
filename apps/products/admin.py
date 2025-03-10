from django.contrib import admin
from .models import Product

class ProductAdmin(admin.ModelAdmin):
    """Отображение модели Product"""
    list_display = ('name', 'type_product')
    list_filter = ('type_product',)
    search_fields = ('name',)
    ordering = ('name',)
    list_editable = ('type_product',)

admin.site.register(Product, ProductAdmin)
