from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Оптимизация вида тб"""
    search_fields = ['name', 'phone', 'address']
    list_display = ['name', 'phone', 'address', 'balans', 'created_at']
    list_filter = ['created_at', 'balans']
    fields = ['name', 'phone', 'address', 'balans', 'note']
    # Опционально: добавьте возможность редактирования в виде инлайнов
    # inlines = [YourInlineModelAdmin]  # Если у вас есть связанные модели
    list_per_page = 20
    ordering = ['created_at']
