from django.contrib import admin
from .models import DeliveryJournal, DeliveryJournalProducts

class DeliveryJournalProductsInline(admin.TabularInline):
    model = DeliveryJournalProducts
    extra = 1  # Количество пустых форм для добавления новых продуктов

class DeliveryJournalAdmin(admin.ModelAdmin):
    list_display = ('courier', 'date', 'total_price', 'payment_type')  # Поля, которые будут отображаться в списке
    list_filter = ('courier', 'date', 'payment_type')  # Фильтры по полям
    inlines = [DeliveryJournalProductsInline]  # Встраиваемые продукты в журнале

class DeliveryJournalProductsAdmin(admin.ModelAdmin):
    list_display = ('delivery_journal', 'product', 'quantity', 'note')  # Добавлено поле note
    list_filter = ('product',)  # Фильтры по полям
    search_fields = ('product__name', 'note')  # Поиск по имени продукта и заметке

# Регистрация моделей в админке
admin.site.register(DeliveryJournal, DeliveryJournalAdmin)
admin.site.register(DeliveryJournalProducts, DeliveryJournalProductsAdmin)
