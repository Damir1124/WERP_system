from django.contrib import admin
from .models import Product


from django.contrib import admin
from .models import Product

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'type_product', 'price', 'created_at', 'updated_at')  # Поля, которые будут отображаться в списке
    list_filter = ('type_product',)  # Фильтры по типу продукта
    search_fields = ('name',)  # Поиск по имени продукта
    ordering = ('name',)  # Сортировка по имени продукта

    class Meta:
        model = Product

# Регистрация модели в админке
admin.site.register(Product, ProductAdmin)

